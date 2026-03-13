"""
SLP Central Server Hub — Main Entry Point (v2).

Serves the web-based control dashboard on port 5000.
Integrates SLP gateway for encrypted service communication.
"""

import asyncio
import json
import logging
import os
import struct
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import httpx
import psutil
import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from slp.gateway.slp_gateway import SLPGateway, ServiceInfo
from slp.keygen import ensure_keys, load_private_key, load_public_key_bytes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "services.yaml")

ALLOWED_ORIGINS = [
    "https://oscyra.solutions",
    "https://csh.oscyra.solutions",
    "https://klar.oscyra.solutions",
    "https://sverkan.oscyra.solutions",
    "https://upsum.oscyra.solutions",
    "https://testview.oscyra.solutions",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    return {"gateway": {"host": "127.0.0.1", "port": 14270, "keys_dir": "keys"}, "services": {}}


config = load_config()
gateway_cfg = config.get("gateway", {})
services_cfg = config.get("services", {})

# ── FastAPI App ────────────────────────────────────────────────────────

app = FastAPI(title="SLP Central Server Hub", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── Global State ───────────────────────────────────────────────────────

slp_gateway: Optional[SLPGateway] = None
active_connections: List[WebSocket] = []
ip_connections: List[WebSocket] = []
services_procs: Dict[str, subprocess.Popen] = {}
service_start_times: Dict[str, float] = {}
current_public_ip: str = "Loading..."
# Logs aggregated from SLP LOG_ENTRY messages.
LOG_STORE: Dict[str, List[str]] = {}


# ── SLP Gateway Callbacks ─────────────────────────────────────────────

async def _on_register(info: ServiceInfo):
    logger.info("Service registered via SLP: %s (%s)", info.service_id, info.service_name)
    await _broadcast_services()


async def _on_heartbeat(service_id: str, metrics: dict):
    await _broadcast_services()


async def _on_log(service_id: str, msg: dict):
    ts = datetime.now().strftime("%H:%M:%S")
    level = msg.get("level", "INFO")
    text = msg.get("message", "")
    entry = f"[{ts}] {level}: {text}"
    if service_id not in LOG_STORE:
        LOG_STORE[service_id] = []
    LOG_STORE[service_id].append(entry)
    if len(LOG_STORE[service_id]) > 500:
        LOG_STORE[service_id] = LOG_STORE[service_id][-500:]


async def _on_status_change(service_id: str, status: str):
    logger.info("Service %s status changed to %s", service_id, status)
    await _broadcast_services()


# ── Helper Functions ───────────────────────────────────────────────────

def _get_service_summary() -> dict:
    """Build service status from SLP gateway + config."""
    result = {}
    for key, svc_cfg in services_cfg.items():
        sid = svc_cfg.get("service_id", f"{key}-001")
        info = slp_gateway.services.get(sid) if slp_gateway else None
        status = "offline"
        uptime = None
        metrics = {}
        session_info = {}
        if info:
            status = info.status
            if info.metrics:
                metrics = info.metrics
                up_s = metrics.get("uptime_seconds", 0)
                hours = up_s // 3600
                mins = (up_s % 3600) // 60
                uptime = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
            if info.session:
                session_info = {
                    "session_id": f"0x{info.session.session_id:08X}",
                    "messages_sent": info.session.send_counter,
                    "state": info.session.state.name,
                }
        result[key] = {
            "name": svc_cfg.get("name", key),
            "service_id": sid,
            "port": svc_cfg.get("http_port", 0),
            "status": status,
            "auto_restart": svc_cfg.get("auto_restart", False),
            "domain": svc_cfg.get("domain", ""),
            "uptime": uptime,
            "metrics": metrics,
            "session": session_info,
        }
    return result


def add_log(service_key: str, message: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {level}: {message}"
    if service_key not in LOG_STORE:
        LOG_STORE[service_key] = []
    LOG_STORE[service_key].append(entry)
    if len(LOG_STORE[service_key]) > 500:
        LOG_STORE[service_key] = LOG_STORE[service_key][-500:]


async def _broadcast_services():
    data = {"type": "services", "data": _get_service_summary()}
    disconnected = []
    for ws in active_connections:
        try:
            await ws.send_json(data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        active_connections.remove(ws)


# ── IP Watcher ─────────────────────────────────────────────────────────

class IPConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for conn in self.active_connections:
            try:
                await conn.send_json({"ip": message})
            except Exception:
                pass


ip_manager = IPConnectionManager()


async def ip_watcher():
    global current_public_ip
    last_ip = None
    async with httpx.AsyncClient() as client:
        while True:
            try:
                resp = await client.get("https://jsonip.com", timeout=5)
                new_ip = resp.json().get("ip", "Unknown")
                if new_ip != last_ip:
                    current_public_ip = new_ip
                    last_ip = new_ip
                    await ip_manager.broadcast(new_ip)
            except Exception:
                pass
            await asyncio.sleep(30)


# ── Reverse Proxy Dispatcher ──────────────────────────────────────────

DOMAIN_TO_SERVICE: Dict[str, int] = {}
for _key, _svc in services_cfg.items():
    domain = _svc.get("domain", "")
    port = _svc.get("http_port", 0)
    if domain and port:
        DOMAIN_TO_SERVICE[domain] = port

CSH_DOMAINS = {"csh.oscyra.solutions", "localhost", "127.0.0.1"}


async def reverse_proxy(request: Request) -> Optional[Response]:
    """Proxy requests to backend services based on Host header."""
    host = request.headers.get("host", "").split(":")[0]
    port = DOMAIN_TO_SERVICE.get(host)
    if port is None:
        return None  # Not a service domain — let CSH handle it.
    # Build target URL.
    path = request.url.path
    query = str(request.url.query)
    target = f"http://127.0.0.1:{port}{path}"
    if query:
        target += f"?{query}"
    # Forward the request.
    async with httpx.AsyncClient() as client:
        try:
            body = await request.body()
            resp = await client.request(
                method=request.method,
                url=target,
                headers={k: v for k, v in request.headers.items()
                         if k.lower() not in ("host", "transfer-encoding")},
                content=body,
                timeout=30.0,
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
            )
        except httpx.ConnectError:
            return JSONResponse(
                {"error": f"Service on port {port} is not reachable"},
                status_code=502,
            )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)


@app.middleware("http")
async def host_router(request: Request, call_next):
    """Route based on Host header: service domains → reverse proxy, CSH domains → dashboard."""
    host = request.headers.get("host", "").split(":")[0]
    if host in DOMAIN_TO_SERVICE:
        result = await reverse_proxy(request)
        if result:
            return result
    return await call_next(request)


# ── Dashboard HTML ─────────────────────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SLP Control Hub</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
      color: #e0e0e0;
      min-height: 100vh;
      margin-top: 40px;
    }
    #ip-bar {
      position: fixed; top: 0; left: 0; right: 0; height: 40px;
      background: #333; border-bottom: 1px solid #444;
      display: flex; align-items: center; justify-content: center;
      color: white; z-index: 999; font-size: 0.9rem;
      font-family: 'Courier New', monospace;
    }
    #ip-bar .refresh-btn { cursor: pointer; margin-left: 1rem; color: #00e5ff; font-weight: bold; }
    #ip-bar .refresh-btn:hover { opacity: 0.8; }
    header {
      background: rgba(0,229,255,0.05); border-bottom: 1px solid rgba(0,229,255,0.2);
      padding: 1rem 2rem; display: flex; align-items: center; justify-content: space-between;
    }
    header h1 {
      font-size: 1.6rem;
      background: linear-gradient(135deg, #00e5ff, #00ffa3);
      -webkit-background-clip: text; background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .tabs { display: flex; gap: 1rem; }
    .tab-btn {
      background: transparent; border: 1px solid rgba(0,229,255,0.3);
      color: #00e5ff; padding: 0.5rem 1.5rem; border-radius: 50px;
      cursor: pointer; font-size: 0.9rem; transition: all 0.2s;
    }
    .tab-btn.active, .tab-btn:hover { background: rgba(0,229,255,0.15); }
    .tab-content { display: none; padding: 2rem; }
    .tab-content.active { display: block; }
    .section-title { font-size: 1.2rem; color: #00e5ff; margin-bottom: 1.5rem; font-weight: 600; }
    .services-table {
      width: 100%; border-collapse: collapse; background: rgba(255,255,255,0.03);
      border-radius: 8px; overflow: hidden;
    }
    .services-table th {
      background: rgba(0,229,255,0.1); color: #00e5ff; padding: 1rem;
      text-align: left; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;
    }
    .services-table td { padding: 1rem; border-bottom: 1px solid rgba(255,255,255,0.05); }
    .badge { display: inline-block; padding: 0.3rem 0.8rem; border-radius: 50px; font-size: 0.8rem; font-weight: 600; }
    .badge.healthy { background: rgba(0,255,163,0.2); color: #00ffa3; }
    .badge.offline { background: rgba(255,255,255,0.08); color: #888; }
    .badge.unhealthy { background: rgba(255,200,0,0.2); color: #ffc800; }
    .badge.error { background: rgba(255,68,68,0.2); color: #ff4444; }
    .btn-group { display: flex; gap: 0.5rem; }
    .btn {
      background: transparent; border: 1px solid rgba(0,229,255,0.4); color: #00e5ff;
      padding: 0.4rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; transition: all 0.2s;
    }
    .btn:hover { background: rgba(0,229,255,0.1); }
    .btn.danger { border-color: rgba(255,68,68,0.4); color: #ff4444; }
    .btn.danger:hover { background: rgba(255,68,68,0.1); }
    .protocol-card {
      background: rgba(0,229,255,0.05); border: 1px solid rgba(0,229,255,0.2);
      border-radius: 8px; padding: 1.5rem; margin-top: 2rem;
    }
    .protocol-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem; margin-top: 1rem;
    }
    .metric-card {
      background: rgba(255,255,255,0.03); border: 1px solid rgba(0,229,255,0.15);
      border-radius: 8px; padding: 1rem;
    }
    .metric-card .label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: #888; margin-bottom: 0.5rem; }
    .metric-card .value { font-size: 1.4rem; color: #00e5ff; font-weight: 600; }
    .log-panel {
      background: #050505; border: 1px solid rgba(0,229,255,0.15); border-radius: 8px;
      padding: 1rem; height: 350px; overflow-y: auto;
      font-family: 'Courier New', monospace; font-size: 0.85rem;
    }
    .log-panel .log-line { padding: 0.2rem 0; color: #00e5ff; }
    .log-panel .log-line.warn { color: #ffc800; }
    .log-panel .log-line.error { color: #ff4444; }
    .log-panel .log-line.success { color: #00ffa3; }
    .slc-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
    .slc-card {
      background: rgba(255,255,255,0.03); border: 1px solid rgba(0,229,255,0.15);
      border-radius: 8px; padding: 1.2rem;
    }
    .slc-card h3 { color: #00e5ff; margin-bottom: 1rem; font-size: 1rem; }
    .slc-stat { display: flex; justify-content: space-between; margin: 0.5rem 0; font-size: 0.9rem; }
    .slc-stat .k { color: #888; }
    .slc-stat .v { color: #e0e0e0; font-weight: 500; }
    .service-selector { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
    .ws-status { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; color: #888; }
    .ws-dot { width: 8px; height: 8px; border-radius: 50%; background: #ff4444; }
    .ws-dot.connected { background: #00ffa3; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    .service-row {
      display: flex; align-items: center; gap: 1rem; padding: 0.8rem;
      border-bottom: 1px solid rgba(0,229,255,0.1); font-size: 0.95rem;
    }
    .service-name { flex: 1; font-weight: 500; color: #e0e0e0; }
    .service-status-text { min-width: 80px; text-align: center; font-size: 0.85rem; font-weight: 600; }
    .service-status-text.healthy { color: #00ffa3; background: rgba(0,255,163,0.1); padding: 0.3rem 0.8rem; border-radius: 50px; }
    .service-status-text.offline { color: #888; background: rgba(255,255,255,0.05); padding: 0.3rem 0.8rem; border-radius: 50px; }
    .service-status-text.unhealthy { color: #ffc800; background: rgba(255,193,7,0.2); padding: 0.3rem 0.8rem; border-radius: 50px; }
    .service-actions { display: flex; gap: 0.5rem; }
    .service-action-btn {
      background: transparent; border: 1px solid rgba(0,229,255,0.3); color: #00e5ff;
      padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem; transition: all 0.2s;
    }
    .service-action-btn:hover { background: rgba(0,229,255,0.1); }
    .service-action-btn.stop { border-color: rgba(255,68,68,0.3); color: #ff4444; }
    .service-action-btn.stop:hover { background: rgba(255,68,68,0.1); }
    .session-info { font-size: 0.75rem; color: #666; font-family: 'Courier New', monospace; margin-top: 0.2rem; }
  </style>
</head>
<body>
  <div id="ip-bar">
    <span>Public IP: <span id="ip-text">Loading...</span></span>
    <span class="refresh-btn" onclick="refreshIP()">&#x1f504;</span>
  </div>
  <header>
    <h1>SLP Central Server Hub</h1>
    <div style="display:flex;align-items:center;gap:1.5rem;">
      <div class="ws-status">
        <div class="ws-dot" id="wsDot"></div>
        <span id="wsLabel">Connecting...</span>
      </div>
      <div class="tabs">
        <button class="tab-btn active" onclick="showTab('dcc', this)">Control Center</button>
        <button class="tab-btn" onclick="showTab('slc', this)">Status Logs</button>
      </div>
    </div>
  </header>

  <!-- DCC -->
  <div id="tab-dcc" class="tab-content active">
    <div class="section-title">Services</div>
    <div id="services-list"></div>

    <div class="protocol-card">
      <div class="section-title">SLP Gateway Status</div>
      <div class="protocol-grid">
        <div class="metric-card">
          <div class="label">Gateway Address</div>
          <div class="value" style="font-size:0.9rem;font-family:monospace;">udp://127.0.0.1:14270</div>
        </div>
        <div class="metric-card">
          <div class="label">Gateway Status</div>
          <div class="value" id="protoCore">Initializing</div>
        </div>
        <div class="metric-card">
          <div class="label">Encryption</div>
          <div class="value" style="font-size:0.85rem;">AES-GCM + ChaCha20 + Noise XX</div>
        </div>
        <div class="metric-card">
          <div class="label">Active Sessions</div>
          <div class="value" id="activeCount">0</div>
        </div>
        <div class="metric-card">
          <div class="label">Key Exchange</div>
          <div class="value" style="font-size:0.85rem;">X25519 ECDH (PFS)</div>
        </div>
        <div class="metric-card">
          <div class="label">Replay Protection</div>
          <div class="value" style="font-size:0.85rem;">2048-bit Window</div>
        </div>
      </div>
    </div>
  </div>

  <!-- SLC -->
  <div id="tab-slc" class="tab-content">
    <div class="slc-grid" id="slcGrid"></div>
    <div style="margin-top:2rem;">
      <div class="section-title">Live Log Output</div>
      <div class="service-selector" id="logSelector"></div>
      <div class="log-panel" id="logPanel">
        <div class="log-line">[system] Select a service to view logs</div>
      </div>
    </div>
  </div>

  <script>
    let services = {};
    let selectedLogService = null;

    function showTab(name, btn) {
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById('tab-' + name).classList.add('active');
      if (btn) btn.classList.add('active');
    }

    function renderServices(data) {
      const list = document.getElementById('services-list');
      if (!list) return;
      let html = '';
      let activeCount = 0;
      for (const [key, svc] of Object.entries(data)) {
        const status = svc.status || 'offline';
        const isOnline = status === 'healthy';
        if (isOnline) activeCount++;
        const metrics = svc.metrics || {};
        const session = svc.session || {};
        const uptime = svc.uptime || '—';
        const cpuPct = metrics.cpu_percent !== undefined ? metrics.cpu_percent.toFixed(1) + '%' : '—';
        const memMb = metrics.memory_mb !== undefined ? metrics.memory_mb.toFixed(1) + 'MB' : '—';
        const sessionId = session.session_id || '—';
        const msgCount = session.messages_sent !== undefined ? session.messages_sent : '—';
        const sessionState = session.state || '—';

        html += `
          <div class="service-row">
            <div style="flex:1;">
              <div class="service-name">${svc.name} <span style="font-size:0.75rem;color:#666;">(${svc.service_id})</span></div>
              <div style="font-size:0.8rem;color:#666;margin-top:0.3rem;">
                <span style="margin-right:1rem;">Port: ${svc.port}</span>
                <span style="margin-right:1rem;">Uptime: ${uptime}</span>
                <span style="margin-right:1rem;">CPU: ${cpuPct}</span>
                <span>Mem: ${memMb}</span>
              </div>
              <div class="session-info">Session: ${sessionId} | State: ${sessionState} | Msgs: ${msgCount}</div>
            </div>
            <span class="service-status-text ${status}">${status.toUpperCase()}</span>
            <div class="service-actions">
              ${!isOnline ? `<button class="service-action-btn" onclick="startSvc('${key}')">Start</button>` : ''}
              ${isOnline ? `<button class="service-action-btn stop" onclick="stopSvc('${key}')">Stop</button>` : ''}
            </div>
          </div>
        `;
      }
      list.innerHTML = html;
      const ac = document.getElementById('activeCount');
      if (ac) ac.textContent = activeCount;
      const pc = document.getElementById('protoCore');
      if (pc) pc.textContent = 'Active';
      if (pc) pc.style.color = '#00ffa3';
    }

    function renderSLC(data) {
      const grid = document.getElementById('slcGrid');
      const selector = document.getElementById('logSelector');
      if (!grid || !selector) return;
      let html = '';
      let selHtml = '';
      for (const [key, svc] of Object.entries(data)) {
        const status = svc.status || 'offline';
        const metrics = svc.metrics || {};
        const session = svc.session || {};
        html += `<div class="slc-card">
          <h3>${svc.name}</h3>
          <div class="slc-stat"><span class="k">Status</span><span class="v"><span class="badge ${status}">${status}</span></span></div>
          <div class="slc-stat"><span class="k">Service ID</span><span class="v">${svc.service_id}</span></div>
          <div class="slc-stat"><span class="k">Port</span><span class="v">${svc.port}</span></div>
          <div class="slc-stat"><span class="k">Domain</span><span class="v">${svc.domain || '—'}</span></div>
          <div class="slc-stat"><span class="k">Uptime</span><span class="v">${svc.uptime || '—'}</span></div>
          <div class="slc-stat"><span class="k">CPU</span><span class="v">${metrics.cpu_percent !== undefined ? metrics.cpu_percent.toFixed(1) + '%' : '—'}</span></div>
          <div class="slc-stat"><span class="k">Memory</span><span class="v">${metrics.memory_mb !== undefined ? metrics.memory_mb.toFixed(1) + ' MB' : '—'}</span></div>
          <div class="slc-stat"><span class="k">Session</span><span class="v">${session.session_id || '—'}</span></div>
          <div class="slc-stat"><span class="k">Messages</span><span class="v">${session.messages_sent !== undefined ? session.messages_sent : '—'}</span></div>
        </div>`;
        const active = selectedLogService === key ? 'active' : '';
        selHtml += `<button class="tab-btn ${active}" onclick="selectLog('${key}')">${svc.name}</button>`;
      }
      grid.innerHTML = html;
      selector.innerHTML = selHtml;
    }

    function selectLog(key) {
      selectedLogService = key;
      fetch('/api/logs/' + key).then(r => r.json()).then(data => {
        const panel = document.getElementById('logPanel');
        panel.innerHTML = '';
        for (const line of (data.logs || [])) {
          const div = document.createElement('div');
          div.className = 'log-line' +
            (line.includes('ERROR') ? ' error' : line.includes('WARN') ? ' warn' : line.includes('SUCCESS') ? ' success' : '');
          div.textContent = line;
          panel.appendChild(div);
        }
        panel.scrollTop = panel.scrollHeight;
      });
    }

    function startSvc(key) {
      fetch('/api/services/' + key + '/start', { method: 'POST' });
    }
    function stopSvc(key) {
      fetch('/api/services/' + key + '/stop', { method: 'POST' });
    }

    function initIPBar() {
      const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
      const ipWs = new WebSocket(protocol + '://' + location.host + '/ws/ip');
      ipWs.onmessage = (e) => {
        const data = JSON.parse(e.data);
        document.getElementById('ip-text').textContent = data.ip;
      };
      ipWs.onerror = () => {
        fetch('/api/public-ip').then(r => r.json()).then(d => {
          document.getElementById('ip-text').textContent = d.ip;
        });
      };
    }

    function refreshIP() {
      fetch('/api/public-ip').then(r => r.json()).then(d => {
        document.getElementById('ip-text').textContent = d.ip;
      });
    }

    let ws = null;
    function connectWS() {
      const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
      ws = new WebSocket(protocol + '://' + location.host + '/ws');
      ws.onopen = () => {
        document.getElementById('wsDot').classList.add('connected');
        document.getElementById('wsLabel').textContent = 'Live';
      };
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'services') {
          services = msg.data;
          renderServices(services);
          renderSLC(services);
        }
      };
      ws.onclose = () => {
        document.getElementById('wsDot').classList.remove('connected');
        document.getElementById('wsLabel').textContent = 'Disconnected';
        setTimeout(connectWS, 3000);
      };
    }

    connectWS();
    initIPBar();
  </script>
</body>
</html>"""


# ── Routes ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return DASHBOARD_HTML


@app.get("/dcc", response_class=HTMLResponse)
async def dcc():
    return DASHBOARD_HTML


@app.get("/slc", response_class=HTMLResponse)
async def slc():
    return DASHBOARD_HTML


@app.get("/api/public-ip")
async def get_public_ip():
    return JSONResponse({"ip": current_public_ip})


@app.get("/api/services")
async def get_services():
    return JSONResponse(_get_service_summary())


@app.get("/api/gateway")
async def get_gateway_status():
    if not slp_gateway:
        return JSONResponse({"status": "not started"})
    active = sum(1 for info in slp_gateway.services.values() if info.status == "healthy")
    return JSONResponse({
        "status": "active",
        "bind": f"{gateway_cfg.get('host', '127.0.0.1')}:{gateway_cfg.get('port', 14270)}",
        "active_sessions": active,
        "total_services": len(services_cfg),
    })


@app.get("/api/logs/{service_key}")
async def get_logs(service_key: str):
    # Accept both service key (e.g. "klar") and service_id (e.g. "klar-001").
    logs = LOG_STORE.get(service_key, [])
    if not logs:
        sid = services_cfg.get(service_key, {}).get("service_id", "")
        logs = LOG_STORE.get(sid, [])
    return JSONResponse({"logs": logs})


@app.post("/api/services/{service_key}/start")
async def start_service(service_key: str):
    svc_cfg = services_cfg.get(service_key)
    if not svc_cfg:
        return JSONResponse({"error": "Service not found"}, status_code=404)

    sid = svc_cfg.get("service_id", f"{service_key}-001")
    if service_key in services_procs:
        proc = services_procs[service_key]
        if proc.poll() is None:
            return JSONResponse({"message": "Already running"})

    launch = svc_cfg.get("launch", {})
    cmd = launch.get("command", "")
    cwd = launch.get("cwd", ".")
    if not cmd:
        return JSONResponse({"error": "No launch command configured"}, status_code=400)

    # Resolve cwd relative to CSH directory.
    csh_dir = os.path.dirname(os.path.abspath(__file__))
    abs_cwd = os.path.normpath(os.path.join(csh_dir, cwd))

    keys_dir = os.path.join(csh_dir, gateway_cfg.get("keys_dir", "keys"))
    priv_key_path = os.path.join(keys_dir, f"{service_key}_private.key")
    csh_pub_path = os.path.join(keys_dir, "csh_public.key")
    gw_host = gateway_cfg.get("host", "127.0.0.1")
    gw_port = gateway_cfg.get("port", 14270)

    # Launch via service_wrapper.
    wrapper_cmd = [
        sys.executable, "-m", "slp.agent.service_wrapper",
        "--service-id", sid,
        "--service-name", svc_cfg.get("name", service_key),
        "--version", svc_cfg.get("version", "1.0.0"),
        "--http-port", str(svc_cfg.get("http_port", 0)),
        "--domain", svc_cfg.get("domain", ""),
        "--csh-addr", f"{gw_host}:{gw_port}",
        "--private-key", priv_key_path,
        "--csh-public-key", csh_pub_path,
        "--launch-cmd", cmd,
        "--launch-cwd", abs_cwd,
    ]

    try:
        proc = subprocess.Popen(
            wrapper_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=csh_dir,
            start_new_session=True,
        )
        services_procs[service_key] = proc
        service_start_times[service_key] = time.time()
        add_log(service_key, f"Starting {svc_cfg.get('name', service_key)} via SLP wrapper (PID {proc.pid})", "SUCCESS")
        return JSONResponse({"message": f"{service_key} started", "pid": proc.pid})
    except Exception as exc:
        logger.error("Error starting service %s: %s", service_key, exc)
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/api/services/{service_key}/stop")
async def stop_service(service_key: str):
    svc_cfg = services_cfg.get(service_key)
    if not svc_cfg:
        return JSONResponse({"error": "Service not found"}, status_code=404)

    sid = svc_cfg.get("service_id", f"{service_key}-001")

    # Send GRACEFUL_STOP via SLP if connected.
    if slp_gateway:
        try:
            await slp_gateway.send_command(sid, "GRACEFUL_STOP")
        except Exception:
            pass

    # Also terminate the wrapper process.
    proc = services_procs.get(service_key)
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception:
            pass

    if service_key in service_start_times:
        del service_start_times[service_key]

    add_log(service_key, f"Stopped {svc_cfg.get('name', service_key)}", "WARN")
    return JSONResponse({"message": f"{service_key} stopped"})


# ── WebSocket Endpoints ────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        await websocket.send_json({
            "type": "services",
            "data": _get_service_summary(),
        })
        while True:
            await asyncio.sleep(5)
            await websocket.send_json({
                "type": "services",
                "data": _get_service_summary(),
            })
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)


@app.websocket("/ws/ip")
async def websocket_ip_endpoint(websocket: WebSocket):
    await ip_manager.connect(websocket)
    try:
        await websocket.send_json({"ip": current_public_ip})
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        ip_manager.disconnect(websocket)
    except Exception:
        pass
    finally:
        ip_manager.disconnect(websocket)


# ── Startup / Shutdown ─────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    global slp_gateway

    csh_dir = os.path.dirname(os.path.abspath(__file__))
    keys_dir = os.path.join(csh_dir, gateway_cfg.get("keys_dir", "keys"))

    # Generate keys on first run.
    key_names = ["csh"] + list(services_cfg.keys())
    generated = ensure_keys(keys_dir, key_names)
    if generated:
        logger.info("Generated keys for: %s", ", ".join(generated))

    # Load CSH private key and build allow-list.
    csh_priv = load_private_key(os.path.join(keys_dir, "csh_private.key"))
    allowed_keys: Dict[str, bytes] = {}
    for key, svc_cfg_item in services_cfg.items():
        sid = svc_cfg_item.get("service_id", f"{key}-001")
        pub_path = os.path.join(keys_dir, f"{key}_public.key")
        if os.path.exists(pub_path):
            allowed_keys[sid] = load_public_key_bytes(pub_path)

    # Start SLP gateway.
    slp_gateway = SLPGateway(
        bind_addr=gateway_cfg.get("host", "127.0.0.1"),
        bind_port=gateway_cfg.get("port", 14270),
        private_key=csh_priv,
        allowed_keys=allowed_keys,
    )
    slp_gateway.on_register = _on_register
    slp_gateway.on_heartbeat = _on_heartbeat
    slp_gateway.on_log = _on_log
    slp_gateway.on_status_change = _on_status_change
    await slp_gateway.start()

    # Start background tasks.
    asyncio.create_task(ip_watcher())

    logger.info("CSH started — dashboard on 127.0.0.1:5000, SLP gateway on %s:%d",
                gateway_cfg.get("host", "127.0.0.1"), gateway_cfg.get("port", 14270))


@app.on_event("shutdown")
async def shutdown_event():
    if slp_gateway:
        slp_gateway.stop()
    # Terminate any running service wrappers.
    for key, proc in services_procs.items():
        if proc.poll() is None:
            proc.terminate()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=5000,
        reload=False,
        log_level="info",
    )
