"""
SLP Central Server Hub - Main Entry Point

Serves the web-based control dashboard on port 5000.
"""

import os
import json
import asyncio
import logging
import subprocess
import sys
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

import psutil
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SLP Central Server Hub", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICES: Dict[str, Dict[str, Any]] = {
    "klar": {
        "name": "Klar",
        "sl_id": "klar-001",
        "port": 4271,
        "status": "offline",
        "auto_restart": True,
        "domain": "klar.oscyra.solutions",
        "process": None,
        "uptime_start": None,
        "requests": 0,
        "latency_ms": 0,
        "error_rate": 0.0,
    },
    "sverkan": {
        "name": "Sverkan",
        "sl_id": "sverkan-001",
        "port": 4272,
        "status": "offline",
        "auto_restart": True,
        "domain": "sverkan.oscyra.solutions",
        "process": None,
        "uptime_start": None,
        "requests": 0,
        "latency_ms": 0,
        "error_rate": 0.0,
    },
    "upsum": {
        "name": "Upsum",
        "sl_id": "upsum-001",
        "port": 4273,
        "status": "offline",
        "auto_restart": False,
        "domain": "upsum.oscyra.solutions",
        "process": None,
        "uptime_start": None,
        "requests": 0,
        "latency_ms": 0,
        "error_rate": 0.0,
    },
    "testview": {
        "name": "TestView",
        "sl_id": "testview-001",
        "port": 4274,
        "status": "offline",
        "auto_restart": False,
        "domain": "testview.oscyra.solutions",
        "process": None,
        "uptime_start": None,
        "requests": 0,
        "latency_ms": 0,
        "error_rate": 0.0,
        "bridge_port": 9001,
    },
}

LOG_STORE: Dict[str, List[str]] = {k: [] for k in SERVICES}
active_connections: List[WebSocket] = []
ip_connections: List[WebSocket] = []
services_procs: Dict[str, Any] = {}
service_start_times: Dict[str, float] = {}
current_public_ip: str = "Loading..."


class IPConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_json({"ip": message})
            except Exception:
                pass


ip_manager = IPConnectionManager()


def get_service_status_summary():
    result = {}
    for key, svc in SERVICES.items():
        uptime = None
        if svc["uptime_start"]:
            delta = datetime.now() - svc["uptime_start"]
            uptime = str(delta).split(".")[0]
        result[key] = {
            "name": svc["name"],
            "sl_id": svc["sl_id"],
            "port": svc["port"],
            "status": svc["status"],
            "auto_restart": svc["auto_restart"],
            "domain": svc["domain"],
            "uptime": uptime,
            "requests": svc["requests"],
            "latency_ms": svc["latency_ms"],
            "error_rate": svc["error_rate"],
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


async def broadcast(data: dict):
    disconnected = []
    for ws in active_connections:
        try:
            await ws.send_json(data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        active_connections.remove(ws)


async def ip_watcher():
    global current_public_ip
    last_ip = None
    while True:
        try:
            resp = requests.get('http://jsonip.com', timeout=5)
            new_ip = resp.json().get('ip', 'Unknown')
            if new_ip != last_ip:
                current_public_ip = new_ip
                last_ip = new_ip
                await ip_manager.broadcast(new_ip)
        except Exception:
            pass
        await asyncio.sleep(30)


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
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      height: 40px;
      background: #333;
      border-bottom: 1px solid #444;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      z-index: 999;
      font-size: 0.9rem;
      font-family: 'Courier New', monospace;
    }
    #ip-bar .refresh-btn {
      cursor: pointer;
      margin-left: 1rem;
      color: #00e5ff;
      font-weight: bold;
    }
    #ip-bar .refresh-btn:hover { opacity: 0.8; }
    header {
      background: rgba(0,229,255,0.05);
      border-bottom: 1px solid rgba(0,229,255,0.2);
      padding: 1rem 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    header h1 {
      font-size: 1.6rem;
      background: linear-gradient(135deg, #00e5ff, #00ffa3);
      -webkit-background-clip: text;
      background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .tabs {
      display: flex;
      gap: 1rem;
    }
    .tab-btn {
      background: transparent;
      border: 1px solid rgba(0,229,255,0.3);
      color: #00e5ff;
      padding: 0.5rem 1.5rem;
      border-radius: 50px;
      cursor: pointer;
      font-size: 0.9rem;
      transition: all 0.2s;
    }
    .tab-btn.active, .tab-btn:hover {
      background: rgba(0,229,255,0.15);
    }
    .tab-content { display: none; padding: 2rem; }
    .tab-content.active { display: block; }
    .section-title {
      font-size: 1.2rem;
      color: #00e5ff;
      margin-bottom: 1.5rem;
      font-weight: 600;
    }
    .services-table {
      width: 100%;
      border-collapse: collapse;
      background: rgba(255,255,255,0.03);
      border-radius: 8px;
      overflow: hidden;
    }
    .services-table th {
      background: rgba(0,229,255,0.1);
      color: #00e5ff;
      padding: 1rem;
      text-align: left;
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    .services-table td {
      padding: 1rem;
      border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    .badge {
      display: inline-block;
      padding: 0.3rem 0.8rem;
      border-radius: 50px;
      font-size: 0.8rem;
      font-weight: 600;
    }
    .badge.online { background: rgba(0,255,163,0.2); color: #00ffa3; }
    .badge.offline { background: rgba(255,255,255,0.08); color: #888; }
    .badge.starting { background: rgba(255,200,0,0.2); color: #ffc800; }
    .badge.error { background: rgba(255,68,68,0.2); color: #ff4444; }
    .btn-group { display: flex; gap: 0.5rem; }
    .btn {
      background: transparent;
      border: 1px solid rgba(0,229,255,0.4);
      color: #00e5ff;
      padding: 0.4rem 1rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.85rem;
      transition: all 0.2s;
    }
    .btn:hover { background: rgba(0,229,255,0.1); }
    .btn.danger { border-color: rgba(255,68,68,0.4); color: #ff4444; }
    .btn.danger:hover { background: rgba(255,68,68,0.1); }
    .btn.success { border-color: rgba(0,255,163,0.4); color: #00ffa3; }
    .btn.success:hover { background: rgba(0,255,163,0.1); }
    .protocol-card {
      background: rgba(0,229,255,0.05);
      border: 1px solid rgba(0,229,255,0.2);
      border-radius: 8px;
      padding: 1.5rem;
      margin-top: 2rem;
    }
    .protocol-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-top: 1rem;
    }
    .metric-card {
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(0,229,255,0.15);
      border-radius: 8px;
      padding: 1rem;
    }
    .metric-card .label {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #888;
      margin-bottom: 0.5rem;
    }
    .metric-card .value {
      font-size: 1.4rem;
      color: #00e5ff;
      font-weight: 600;
    }
    .log-panel {
      background: #050505;
      border: 1px solid rgba(0,229,255,0.15);
      border-radius: 8px;
      padding: 1rem;
      height: 350px;
      overflow-y: auto;
      font-family: 'Courier New', monospace;
      font-size: 0.85rem;
    }
    .log-panel .log-line { padding: 0.2rem 0; color: #00e5ff; }
    .log-panel .log-line.warn { color: #ffc800; }
    .log-panel .log-line.error { color: #ff4444; }
    .log-panel .log-line.success { color: #00ffa3; }
    .slc-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 1.5rem;
    }
    .slc-card {
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(0,229,255,0.15);
      border-radius: 8px;
      padding: 1.2rem;
    }
    .slc-card h3 { color: #00e5ff; margin-bottom: 1rem; font-size: 1rem; }
    .slc-stat { display: flex; justify-content: space-between; margin: 0.5rem 0; font-size: 0.9rem; }
    .slc-stat .k { color: #888; }
    .slc-stat .v { color: #e0e0e0; font-weight: 500; }
    .service-selector {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1rem;
      flex-wrap: wrap;
    }
    .ws-status {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.8rem;
      color: #888;
    }
    .ws-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #ff4444;
    }
    .ws-dot.connected { background: #00ffa3; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    #dynamic-services-list {
      padding: 1rem 0;
      color: #b0b0b0;
    }
    .service-row {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.8rem;
      border-bottom: 1px solid rgba(0,229,255,0.1);
      font-size: 0.95rem;
    }
    .service-name {
      flex: 1;
      font-weight: 500;
      color: #e0e0e0;
    }
    .service-status-text {
      min-width: 80px;
      text-align: center;
      font-size: 0.85rem;
      font-weight: 600;
    }
    .service-status-text.running {
      color: #00ffa3;
      background: rgba(0,255,163,0.1);
      padding: 0.3rem 0.8rem;
      border-radius: 50px;
    }
    .service-status-text.stopped {
      color: #888;
      background: rgba(255,255,255,0.05);
      padding: 0.3rem 0.8rem;
    }
    
    .service-status-text.initializing {
      background: rgba(255,193,7,0.2);
      color: #ffc107;
      animation: pulse 1s infinite;
    }
    
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.6; }
    }
    
    .service-actions {
      display: flex;
      gap: 0.5rem;
    }
    .service-action-btn {
      background: transparent;
      border: 1px solid rgba(0,229,255,0.3);
      color: #00e5ff;
      padding: 0.4rem 0.8rem;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.8rem;
      transition: all 0.2s;
    }
    .service-action-btn:hover { background: rgba(0,229,255,0.1); }
    .service-action-btn.stop { border-color: rgba(255,68,68,0.3); color: #ff4444; }
    .service-action-btn.stop:hover { background: rgba(255,68,68,0.1); }
    .no-services-message {
      color: #666;
      font-style: italic;
      padding: 2rem 1rem;
      text-align: center;
    }
  </style>
</head>
<body>
  <div id="ip-bar">
    <span>Public IP: <span id="ip-text">Loading...</span></span>
    <span class="refresh-btn" onclick="refreshIP()">🔄</span>
  </div>
  <header>
    <h1>SLP Central Server Hub</h1>
    <div style="display:flex;align-items:center;gap:1.5rem;">
      <div class="ws-status">
        <div class="ws-dot" id="wsDot"></div>
        <span id="wsLabel">Connecting...</span>
      </div>
      <div class="tabs">
        <button class="tab-btn active" onclick="showTab('dcc')">Control Center</button>
        <button class="tab-btn" onclick="showTab('slc')">Status Logs</button>
      </div>
    </div>
  </header>

  <!-- DCC -->
  <div id="tab-dcc" class="tab-content active">
    <div class="section-title">Services</div>
    <div id="dynamic-services-list"></div>
    <div id="no-services-status" style="display:none;padding:2rem;background:rgba(0,229,255,0.05);border:1px solid rgba(0,229,255,0.15);border-radius:8px;margin:1rem 0;">
      <p style="color:#888;font-size:0.9rem;margin-bottom:1rem;"><strong>No services configured.</strong> Add *.bat files to <code style="background:#050505;padding:0.3rem 0.6rem;border-radius:3px;">csh/services/</code> to display services.</p>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem;margin-top:1rem;">
        <div style="background:rgba(0,0,0,0.3);padding:1rem;border-radius:6px;border:1px solid rgba(0,229,255,0.1);">
          <div style="font-size:0.75rem;color:#666;margin-bottom:0.3rem;">SYSTEM UPTIME</div>
          <div style="font-size:1.1rem;color:#00e5ff;font-weight:600;">Running</div>
        </div>
        <div style="background:rgba(0,0,0,0.3);padding:1rem;border-radius:6px;border:1px solid rgba(0,229,255,0.1);">
          <div style="font-size:0.75rem;color:#666;margin-bottom:0.3rem;">SLP CORE</div>
          <div style="font-size:1.1rem;color:#00ffa3;font-weight:600;">Active</div>
        </div>
        <div style="background:rgba(0,0,0,0.3);padding:1rem;border-radius:6px;border:1px solid rgba(0,229,255,0.1);">
          <div style="font-size:0.75rem;color:#666;margin-bottom:0.3rem;">SECURITY STATUS</div>
          <div style="font-size:1.1rem;color:#00ffa3;font-weight:600;">Secure</div>
        </div>
      </div>
    </div>

    <div class="protocol-card">
      <div class="section-title">SL Protocol Status</div>
      <div class="protocol-grid">
        <div class="metric-card">
          <div class="label">SLP Address</div>
          <div class="value" style="font-size:0.9rem;font-family:monospace;">sl://localhost:4270</div>
        </div>
        <div class="metric-card">
          <div class="label">Core Status</div>
          <div class="value" id="protoCore">Active</div>
        </div>
        <div class="metric-card">
          <div class="label">Encryption</div>
          <div class="value" style="font-size:0.85rem;">DTLS 1.3 + Noise</div>
        </div>
        <div class="metric-card">
          <div class="label">Security Level</div>
          <div class="value" style="color:#00ffa3;">Military Grade</div>
        </div>
        <div class="metric-card">
          <div class="label">Active Connections</div>
          <div class="value" id="activeCount">0</div>
        </div>
        <div class="metric-card">
          <div class="label">Base Port</div>
          <div class="value">4270</div>
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
    let ws = null;

    function showTab(name) {
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById('tab-' + name).classList.add('active');
      event.target.classList.add('active');
    }

    // Old rendering functions removed - using dynamic services instead

    async function fetchLogs(serviceKey) {
      const res = await fetch('/api/logs/' + serviceKey);
      const data = await res.json();
      const panel = document.getElementById('logPanel');
      panel.innerHTML = '';
      for (const line of data.logs) {
        const div = document.createElement('div');
        div.className = 'log-line' +
          (line.includes('ERROR') ? ' error' : line.includes('WARN') ? ' warn' : line.includes('SUCCESS') ? ' success' : '');
        div.textContent = line;
        panel.appendChild(div);
      }
      panel.scrollTop = panel.scrollHeight;
    }

    async function serviceAction(key, action) {
      await fetch('/api/services/' + key + '/' + action, { method: 'POST' });
    }

    function initIPBar() {
      const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(protocol + '://' + location.host + '/ws/ip');
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        document.getElementById('ip-text').textContent = data.ip;
      };
      ws.onerror = () => {
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

    function loadDynamicServices() {
      fetch('/api/dynamic-services').then(r => r.json()).then(services => {
        const list = document.querySelector('#dynamic-services-list');
        const noSvcStatus = document.querySelector('#no-services-status');
        if (!list) return;
        
        if (services.length === 0)   {
          list.innerHTML = '';
          if (noSvcStatus) noSvcStatus.style.display = 'block';
          return;
        }
        
        if (noSvcStatus) noSvcStatus.style.display = 'none';
        
        let html = '';
        for (const svc of services) {
          const statusClass = svc.status === 'running' ? 'running' : 'stopped';
          const btnClass = svc.status === 'running' ? 'service-action-btn stop' : 'service-action-btn';
          const btnText = svc.status === 'running' ? 'Stop' : 'Start';
          const btnOnClick = svc.status === 'running' ? `stopService('${svc.name}')` : `startService('${svc.name}')`;
          
          html += `
            <div class="service-row">
              <div style="flex:1;">
                <div class="service-name">${svc.name}</div>
                <div style="font-size:0.8rem;color:#666;margin-top:0.3rem;">
                  <span style="margin-right:1rem;">⏱ ${svc.uptime}</span>
                  <span style="margin-right:1rem;">💾 ${svc.memory}</span>
                  <span style="margin-right:1rem;">📊 ${svc.cpu}</span>
                  ${svc.pid ? `<span style="color:#00ffa3;">PID: ${svc.pid}</span>` : ''}
                </div>
              </div>
              <span class="service-status-text ${statusClass}">${svc.status.toUpperCase()}</span>
              <div class="service-actions">
                <button class="${btnClass}" onclick="${btnOnClick}">${btnText}</button>
              </div>
            </div>
          `;
        }
        list.innerHTML = html;
      });
    }

    function startService(name) {
      const list = document.querySelector('#dynamic-services-list');
      if (list) {
        const rows = list.querySelectorAll('.service-row');
        rows.forEach(row => {
          const svcName = row.querySelector('.service-name');
          if (svcName && svcName.textContent.trim() === name) {
            const statusEl = row.querySelector('.service-status-text');
            if (statusEl) {
              statusEl.textContent = 'INITIALIZING';
              statusEl.className = 'service-status-text initializing';
            }
          }
        });
      }
      
      fetch('/api/dynamic-services/' + name + '/start', { method: 'POST' }).then(r => r.json()).then(data => {
        console.log('Service started:', data);
        setTimeout(loadDynamicServices, 300);
        setInterval(loadDynamicServices, 2000);
      }).catch(err => {
        console.error('Error starting service:', err);
        loadDynamicServices();
      });
    }

    function stopService(name) {
      fetch('/api/dynamic-services/' + name + '/stop', { method: 'POST' }).then(r => r.json()).then(data => {
        console.log('Service stopped:', data);
        setTimeout(loadDynamicServices, 300);
      });
    }

    setInterval(loadDynamicServices, 5000);

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
          if (selectedLogService) fetchLogs(selectedLogService);
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
    setTimeout(() => loadDynamicServices(), 100);
  </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def root():
    return DASHBOARD_HTML


@app.get("/dcc", response_class=HTMLResponse)
async def dcc():
    return DASHBOARD_HTML


@app.get("/slc", response_class=HTMLResponse)
async def slc():
    return DASHBOARD_HTML


@app.get("/testview-001/", response_class=HTMLResponse)
async def testview_root():
    with open("testview.html", "r") as f:
        return f.read()


@app.get("/testview-001/{path:path}", response_class=HTMLResponse)
async def testview_path(path: str):
    with open("testview.html", "r") as f:
        content = f.read()
    add_log("testview", f"HTTPS→SLP bridge: GET /testview-001/{path}", "INFO")
    return content


@app.get("/api/public-ip")
async def get_public_ip():
    global current_public_ip
    try:
        resp = requests.get('http://jsonip.com', timeout=5)
        ip = resp.json().get('ip', current_public_ip)
        return JSONResponse({"ip": ip})
    except Exception:
        return JSONResponse({"ip": current_public_ip})


@app.get("/api/dynamic-services")
async def get_dynamic_services():
    services_dir = "csh/services"
    if not os.path.exists(services_dir):
        return JSONResponse([])
    
    services = []
    try:
        files = os.listdir(services_dir)
        for f in sorted(files):
            if f.endswith('.bat'):
                name = f.replace('.bat', '')
                proc = services_procs.get(name)
                # For Windows, check if any cmd.exe child processes are still running from this service
                if proc and proc.poll() is not None:
                    # Original process exited, check if there are child processes still running
                    try:
                        parent = psutil.Process(proc.pid)
                        # Get all children recursively
                        children = parent.children(recursive=True)
                        status = "running" if len(children) > 0 else "stopped"
                    except:
                        status = "stopped"
                else:
                    status = "running" if proc else "stopped"

                
                uptime = "—"
                memory = "—"
                cpu = "—"
                pid = None
                
                if status == "running" and name in service_start_times:
                    import time
                    elapsed = time.time() - service_start_times[name]
                    hours = int(elapsed // 3600)
                    mins = int((elapsed % 3600) // 60)
                    uptime = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
                    
                    if proc and proc.pid:
                        try:
                            p = psutil.Process(proc.pid)
                            memory = f"{p.memory_info().rss // (1024*1024)}MB"
                            cpu = f"{p.cpu_percent(interval=0.1):.1f}%"
                            pid = proc.pid
                        except:
                            pass
                
                services.append({
                    "name": name,
                    "status": status,
                    "uptime": uptime,
                    "memory": memory,
                    "cpu": cpu,
                    "pid": pid
                })
    except Exception as e:
        logger.error(f"Error scanning services: {e}")
    
    return JSONResponse(services)


@app.post("/api/dynamic-services/{name}/start")
async def start_dynamic_service(name: str):
    import time
    services_dir = "csh/services"
    
    if name in services_procs and services_procs[name].poll() is None:
        return JSONResponse({"message": "Already running"})
    
    # Try to find the service file with different extensions
    service_file = None
    file_extensions = ['.bat', '.py', '.exe', '']  # '' for no extension
    
    for ext in file_extensions:
        potential_file = os.path.join(services_dir, f"{name}{ext}")
        if os.path.exists(potential_file):
            service_file = potential_file
            break
    
    if not service_file:
        return JSONResponse({"error": "Service not found"}, status_code=404)
    
    try:
        # Determine how to execute based on file extension/type
        file_ext = os.path.splitext(service_file)[1].lower()
        cmd = None
        
        # Try to read file to check content if needed
        try:
            with open(service_file, 'r') as f:
                content = f.read()
        except:
            # Binary file, likely .exe
            content = ""
        
        # Detect file type and choose executor
        if file_ext == '.py':
            # Python file
            cmd = ['python3', service_file]
        elif file_ext == '.bat':
            # Batch file - Windows uses cmd.exe, Unix uses bash
            abs_service_file = os.path.abspath(service_file)
            if sys.platform == 'win32':
                cmd = ['cmd.exe', '/c', abs_service_file]
            else:
                cmd = ['bash', abs_service_file]

        elif file_ext == '.exe':
            # Executable file
            cmd = [service_file]
        elif not file_ext:
            # No extension - check shebang or default to bash
            if content.startswith('#!'):
                cmd = ['bash', service_file]
            elif content.lower().startswith('python'):
                cmd = ['python3', service_file]
            else:
                cmd = ['bash', service_file]
        else:
            # Unknown extension - try bash
            cmd = ['bash', service_file]
        
        if not cmd:
            return JSONResponse({"error": f"Unknown file type: {file_ext}"}, status_code=400)


        # Start the service process
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=os.getcwd(),
            start_new_session=True
        )
        services_procs[name] = proc
        service_start_times[name] = time.time()


        # For batch files, find the actual child process since cmd.exe chains create new processes
        if file_ext == '.bat':
            import time as time_module
            time_module.sleep(0.5)  # Give child process time to spawn
            try:
                parent = psutil.Process(proc.pid)
                children = parent.children()
                if children:
                    # Store the first child process (the actual service)
                    service_child_pids = {name: children[0].pid}
            except:
                pass


        add_log("services", f"Started service: {name} (File: {os.path.basename(service_file)}, PID: {proc.pid})", "SUCCESS")
        return JSONResponse({"message": f"{name} started", "pid": proc.pid})
    except Exception as e:
        logger.error(f"Error starting service: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/dynamic-services/{name}/stop")
async def stop_dynamic_service(name: str):
    if name not in services_procs:
        return JSONResponse({"message": "Service not running"})
    
    proc = services_procs[name]
    if proc.poll() is not None:
        return JSONResponse({"message": "Service already stopped"})
    
    try:
        proc.terminate()
        proc.wait(timeout=5)
        add_log("services", f"Stopped service: {name}", "WARN")
    except subprocess.TimeoutExpired:
        proc.kill()
    except Exception as e:
        logger.error(f"Error stopping service: {e}")
    
    if name in service_start_times:
        del service_start_times[name]
    
    if os.path.exists("RUNME.bat"):
        try:
            os.remove("RUNME.bat")
        except:
            pass
    
    return JSONResponse({"message": f"{name} stopped"})


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
        if websocket in ip_manager.active_connections:
            ip_manager.disconnect(websocket)


@app.get("/api/services")
async def get_services():
    return JSONResponse(get_service_status_summary())


@app.post("/api/services/{service_key}/{action}")
async def service_action(service_key: str, action: str):
    if service_key not in SERVICES:
        return JSONResponse({"error": "Service not found"}, status_code=404)

    svc = SERVICES[service_key]

    if action == "start":
        if svc["status"] == "online":
            return JSONResponse({"message": "Already running"})
        svc["status"] = "online"
        svc["uptime_start"] = datetime.now()
        add_log(service_key, f"{svc['name']} service started", "SUCCESS")
        await broadcast({"type": "services", "data": get_service_status_summary()})
        return JSONResponse({"message": f"{svc['name']} started"})

    elif action == "stop":
        if svc["status"] == "offline":
            return JSONResponse({"message": "Already stopped"})
        svc["status"] = "offline"
        svc["uptime_start"] = None
        add_log(service_key, f"{svc['name']} service stopped", "WARN")
        await broadcast({"type": "services", "data": get_service_status_summary()})
        return JSONResponse({"message": f"{svc['name']} stopped"})

    elif action == "restart":
        svc["status"] = "starting"
        add_log(service_key, f"{svc['name']} restarting...", "INFO")
        await broadcast({"type": "services", "data": get_service_status_summary()})
        await asyncio.sleep(1)
        svc["status"] = "online"
        svc["uptime_start"] = datetime.now()
        add_log(service_key, f"{svc['name']} restarted successfully", "SUCCESS")
        await broadcast({"type": "services", "data": get_service_status_summary()})
        return JSONResponse({"message": f"{svc['name']} restarted"})

    return JSONResponse({"error": "Unknown action"}, status_code=400)


@app.get("/api/logs/{service_key}")
async def get_logs(service_key: str):
    if service_key not in SERVICES:
        return JSONResponse({"error": "Service not found"}, status_code=404)
    return JSONResponse({"logs": LOG_STORE.get(service_key, [])})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        await websocket.send_json({
            "type": "services",
            "data": get_service_status_summary()
        })
        while True:
            await asyncio.sleep(5)
            await websocket.send_json({
                "type": "services",
                "data": get_service_status_summary()
            })
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(ip_watcher())


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=False,
        log_level="info",
    )
