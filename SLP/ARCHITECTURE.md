# SL Protocol Architecture

## System Overview

The Secure Line Protocol (SL) operates through a **Central Server Hub (CSH)** that manages all Oscyra.solutions services (Klar, Sverkan, Upsum) under a unified infrastructure with military-grade encryption.

## Architecture Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CENTRAL SERVER HUB (CSH)                         │
│                     [Core SLP Repository]                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Dynamic Control Center (DCC)                              │   │
│  │  - Start/Stop/Restart services                             │   │
│  │  - Configure SL protocol settings                          │   │
│  │  - Manage SL-IDs and routing                               │   │
│  │  - Web-based interface (localhost only)                    │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Status Log Center (SLC)                                   │   │
│  │  - Real-time service status (Online/Offline/Error)         │   │
│  │  - Live CLI output monitoring per service                  │   │
│  │  - Performance metrics (latency, requests/sec)             │   │
│  │  - Error logs and debugging                                │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  SL Protocol Core                                          │   │
│  │  - UDP packet routing                                      │   │
│  │  - Triple-layer encryption (TLS+DTLS+Noise)               │   │
│  │  - SL-ID resolver                                          │   │
│  │  - Local proxy manager (for desktop apps)                 │   │
│  │  - Gateway hub connector (for browser users)              │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
                                ↓ SL Protocol (UDP 4271-4273)
                                ↓
    ┌──────────────────────────┬────────────────┬──────────────────┐
    ↓                          ↓                ↓                  ↓
┌────────┐              ┌─────────┐        ┌────────┐      ┌──────────┐
│ Klar   │              │ Sverkan │        │ Upsum  │      │ Gateway  │
│ Server │              │ Server  │        │ Server │      │ Hub      │
│ :4271  │              │ :4272   │        │ :4273  │      │ :443     │
└────────┘              └─────────┘        └────────┘      └──────────┘
 SL-ID:                 SL-ID:             SL-ID:          (Browser
 klar-001               sverkan-001        upsum-001       Users)
```

## Central Server Hub (CSH)

### Purpose
The CSH is the **single unified server** that:
1. Runs the SL Protocol core
2. Manages all backend services (Klar, Sverkan, Upsum)
3. Provides web-based control interface (localhost only)
4. Routes requests between services using SL protocol
5. Acts as local proxy for desktop apps
6. Connects to gateway hub for browser users

### Location
**The CSH lives in the SLP repository** - it IS the core implementation of SL Protocol.

### Why CSH?
- **Unified management**: One server controls all services
- **Shared SL Protocol**: All services use same encryption layer
- **Centralized monitoring**: Single dashboard for all services
- **Resource efficiency**: Share memory, CPU, encryption keys
- **Easy deployment**: One process, one configuration

## Dynamic Control Center (DCC)

### Purpose
Web-based control panel for managing CSH and all services.

### Features

#### Service Management
- **Start Service**: Launch Klar/Sverkan/Upsum backend
- **Stop Service**: Gracefully shutdown service
- **Restart Service**: Quick restart with zero downtime
- **Auto-restart**: Enable automatic restart on crash

#### SL Protocol Configuration
- **SL-ID Assignment**: Assign unique IDs to services
- **Port Configuration**: Set UDP ports for each service
- **Encryption Settings**: Configure DTLS/Noise parameters
- **Routing Rules**: Define domain → SL-ID mappings

#### Network Settings
- **Backend IPs**: Configure service server addresses
- **Gateway Hub**: Connect to remote gateway for browsers
- **Firewall Rules**: Manage allowed connections
- **SSL Certificates**: Upload/generate certificates

### Access
- **URL**: `http://localhost:9000/dcc`
- **Authentication**: Local-only (no external access)
- **Interface**: Modern web UI (React/Vue or plain HTML5)

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│  DYNAMIC CONTROL CENTER                                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Services                                                   │
│  ┌──────────┬─────────┬─────────┬─────────────────────┐   │
│  │ Klar     │ Running │ 4271    │ [Stop] [Restart]    │   │
│  │ Sverkan  │ Running │ 4272    │ [Stop] [Restart]    │   │
│  │ Upsum    │ Stopped │ 4273    │ [Start] [Settings]  │   │
│  └──────────┴─────────┴─────────┴─────────────────────┘   │
│                                                              │
│  SL Protocol Status                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Core: Active   │ Encryption: DTLS 1.3 + Noise      │   │
│  │ Port: 4270     │ Active Connections: 3             │   │
│  │ Gateway: Connected to klar.oscyra.solutions        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  [Go to Status Log Center →]                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Status Log Center (SLC)

### Purpose
Real-time monitoring dashboard for service health and debugging.

### Features

#### Service Status Overview
- **Online**: Service running and responding
- **Offline**: Service stopped or crashed
- **Error**: Service running but experiencing issues
- **Starting**: Service in startup phase
- **Stopping**: Service gracefully shutting down

#### Live CLI Output
- **Real-time logs**: Stream stdout/stderr from each service
- **Clickable services**: Click service to view its output
- **Log filtering**: Search/filter by keyword or log level
- **Auto-scroll**: Automatically scroll to latest logs
- **Export logs**: Download logs as text file

#### Performance Metrics
- **Requests/second**: Current throughput per service
- **Average latency**: Response time in milliseconds
- **Error rate**: Percentage of failed requests
- **Memory usage**: RAM consumption per service
- **CPU usage**: Processor utilization
- **Uptime**: How long service has been running

### Access
- **URL**: `http://localhost:9000/slc`
- **Real-time updates**: WebSocket connection for live data
- **History**: View logs from past 7 days

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│  STATUS LOG CENTER                                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Service Health                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ● Klar     [ONLINE]   ↑234 req/s   ⏱ 45ms   ⚠ 0%  │   │
│  │ ● Sverkan  [ONLINE]   ↑87 req/s    ⏱ 89ms   ⚠ 0%  │   │
│  │ ○ Upsum    [OFFLINE]  ↑0 req/s     ⏱ --     ⚠ --   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  Live Output - [Klar Service] ▼                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [09:15:23] INFO: Search request received            │   │
│  │ [09:15:23] DEBUG: Query: "quantum computing"        │   │
│  │ [09:15:23] INFO: Results: 1247 documents            │   │
│  │ [09:15:23] PERF: Response time: 43ms                │   │
│  │ [09:15:24] INFO: Connection from 127.0.0.1:52341   │   │
│  │ [09:15:24] DEBUG: SL Protocol v1, encrypted        │   │
│  │ █                                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  [← Back to Control Center]  [Export Logs]                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## How It Works Together

### Startup Sequence

1. **User starts CSH**
   - Run: `python csh.py` or `csh.exe`
   - CSH loads SL Protocol core
   - DCC web interface starts on localhost:9000

2. **CSH initializes**
   - Load configuration from `config/csh.yaml`
   - Generate/load encryption keys
   - Initialize SL Protocol listeners (UDP 4270-4273)
   - Start web dashboard (DCC + SLC)

3. **User accesses DCC**
   - Open browser: `http://localhost:9000/dcc`
   - See all services (Klar, Sverkan, Upsum)
   - Click "Start" on desired services

4. **Services start**
   - CSH launches service processes
   - Each service gets SL-ID (klar-001, sverkan-001, etc.)
   - Services bind to UDP ports (4271, 4272, 4273)
   - SL Protocol handles encryption automatically

5. **Monitoring**
   - Switch to SLC tab
   - View real-time status of all services
   - Click service to see live CLI output

### Request Flow (Desktop App)

```
[klar.exe]
    ↓
[QtWebEngine loads https://localhost:8443]
    ↓
[CSH Local Proxy] (inside CSH)
    ↓ Translates HTTPS → SL Protocol
[CSH SL Router]
    ↓ Routes to SL-ID: klar-001
[Klar Backend Server] (managed by CSH)
    ↓ Processes request
[CSH SL Router]
    ↓ Routes response back
[CSH Local Proxy]
    ↓ Translates SL → HTTPS
[QtWebEngine receives response]
```

### Request Flow (Browser User)

```
[Browser: https://klar.oscyra.solutions]
    ↓
[Gateway Hub VPS] (separate server)
    ↓ Translates HTTPS → SL Protocol
[CSH on Your Server]
    ↓ Routes to SL-ID: klar-001
[Klar Backend Server] (managed by CSH)
    ↓ Processes request
[CSH]
    ↓ Routes response back via SL
[Gateway Hub VPS]
    ↓ Translates SL → HTTPS
[Browser receives response]
```

## Configuration

### CSH Configuration File
**Location**: `config/csh.yaml`

```yaml
csh:
  name: "Oscyra Central Server Hub"
  version: "1.0.0"
  bind_ip: "0.0.0.0"
  base_port: 4270
  
services:
  klar:
    enabled: true
    sl_id: "klar-001"
    port: 4271
    executable: "../klar/server.py"
    auto_restart: true
    domain: "klar.oscyra.solutions"
    
  sverkan:
    enabled: true
    sl_id: "sverkan-001"
    port: 4272
    executable: "../sverkan/server.py"
    auto_restart: true
    domain: "sverkan.oscyra.solutions"
    
  upsum:
    enabled: true
    sl_id: "upsum-001"
    port: 4273
    executable: "../upsum/server.py"
    auto_restart: true
    domain: "upsum.oscyra.solutions"

sl_protocol:
  encryption: "DTLS_1_3_AES_256_GCM"
  noise_protocol: true
  forward_secrecy: true
  
local_proxy:
  enabled: true
  port: 8443
  ssl_cert: "certs/localhost.crt"
  ssl_key: "certs/localhost.key"
  
gateway:
  enabled: true
  hub_url: "klar.oscyra.solutions"
  hub_port: 443
  
dashboard:
  enabled: true
  port: 9000
  allowed_ips:
    - "127.0.0.1"
    - "::1"
```

## Deployment Models

### Model 1: All-in-One (Development)
```
[Your PC]
├── CSH (SLP Repository)
│   ├── Klar backend
│   ├── Sverkan backend
│   ├── Upsum backend
│   ├── Local proxy (port 8443)
│   └── Dashboard (port 9000)
└── Desktop Apps (klar.exe, sverkan.exe, upsum.exe)
```

### Model 2: Separated Backend (Production)
```
[Your PC]
├── CSH (SLP Repository)
│   ├── Local proxy (port 8443)
│   └── Dashboard (port 9000)
└── Desktop Apps

[VPS Server]
├── CSH (Production)
│   ├── Klar backend (port 4271)
│   ├── Sverkan backend (port 4272)
│   ├── Upsum backend (port 4273)
│   └── Gateway Hub (port 443)
```

### Model 3: Distributed (Enterprise)
```
[Your PC]
└── Desktop Apps + Local CSH

[VPS 1 - Gateway Hub]
└── HTTPS → SL translator

[VPS 2 - Services]
├── CSH
├── Klar backend
├── Sverkan backend
└── Upsum backend
```

## File Structure

### SLP Repository Layout
```
SLP/
├── README.md
├── ARCHITECTURE.md          # This file
├── csh.py                   # Central Server Hub entry point
├── requirements.txt
│
├── src/
│   ├── csh/                 # CSH Core
│   │   ├── __init__.py
│   │   ├── core.py          # Main CSH server
│   │   ├── service_manager.py  # Start/stop services
│   │   ├── router.py        # SL-ID routing
│   │   └── monitor.py       # Service health monitoring
│   │
│   ├── dcc/                 # Dynamic Control Center
│   │   ├── __init__.py
│   │   ├── web_server.py    # Web interface server
│   │   ├── api.py           # REST API for controls
│   │   └── static/          # HTML/CSS/JS files
│   │
│   ├── slc/                 # Status Log Center
│   │   ├── __init__.py
│   │   ├── logger.py        # Log aggregation
│   │   ├── metrics.py       # Performance metrics
│   │   └── websocket.py     # Real-time updates
│   │
│   ├── protocol/            # SL Protocol (from previous design)
│   ├── proxy/               # Local proxy (from previous design)
│   ├── gateway/             # Gateway hub (from previous design)
│   └── client/              # Client libraries
│
├── config/
│   ├── csh.yaml             # Main configuration
│   ├── services.yaml        # Service definitions
│   └── encryption.yaml      # Crypto settings
│
└── web/                     # Web dashboard files
    ├── dcc/
    │   ├── index.html
    │   ├── app.js
    │   └── style.css
    └── slc/
        ├── index.html
        ├── app.js
        └── style.css
```

## Benefits of CSH Architecture

### For Development
- **Single process**: Run one command to start everything
- **Unified logging**: All service logs in one place
- **Easy debugging**: Monitor all services from one dashboard
- **Fast iteration**: Restart individual services without affecting others

### For Production
- **Simplified deployment**: Deploy CSH once, manage all services
- **Centralized security**: All encryption handled by CSH core
- **Resource efficiency**: Shared memory, connection pooling
- **Easy scaling**: Add more services by updating config

### For Operations
- **Single monitoring point**: One dashboard for all services
- **Automated management**: Auto-restart failed services
- **Performance tracking**: Real-time metrics for all services
- **Troubleshooting**: Live CLI output for debugging

## Security Considerations

### Dashboard Access
- **Localhost only**: Dashboard not accessible from network
- **No authentication needed**: Already protected by localhost binding
- **Optional**: Add password protection for shared machines

### Service Isolation
- **Process separation**: Each service runs in separate process
- **Resource limits**: Configure CPU/memory limits per service
- **Crash isolation**: One service crash doesn't affect others

### SL Protocol Security
- **All inter-service communication encrypted**
- **Desktop apps get full encryption automatically**
- **Browser users get triple-layer encryption**
- **Keys managed centrally by CSH**

## Next Steps

1. **Implement CSH core** (src/csh/)
2. **Build DCC web interface** (src/dcc/)
3. **Create SLC monitoring** (src/slc/)
4. **Integrate with existing SL Protocol code**
5. **Test with Klar backend first**
6. **Expand to Sverkan and Upsum**
7. **Deploy to production VPS**

## Summary

**The Central Server Hub (CSH) is the heart of SL Protocol**:
- Lives in SLP repository
- Manages all backend services (Klar, Sverkan, Upsum)
- Provides web-based control via DCC
- Monitors services via SLC
- Handles all SL Protocol encryption
- Acts as local proxy for desktop apps
- Connects to gateway hub for browser users

**All visual interfaces are web-based and localhost-only** for security and ease of development.
