# SLP - Secure Line Protocol

## Project Overview

**Secure Line Protocol (SLP)** is a Python library implementing a military-grade, UDP-based application protocol with triple-layer encryption (DTLS + TLS + Noise Protocol). It includes a **Central Server Hub (CSH)** for managing services (Klar, Sverkan, Upsum) under a unified control dashboard.

## Architecture

- **`slp/`** - Core SLP protocol library (encryption, client, protocol, transport, gateway, proxy)
- **`csh/`** - Central Server Hub (service manager, config, interfaces for DCC/SLC)
- **`main.py`** - FastAPI web application serving the control dashboard on port 5000
- **`frontend/`** - Static test HTML page for protocol testing
- **`examples/`** - Usage examples for the SLP library
- **`tests/`** - pytest test suite

## Running the Application

The main workflow starts `python main.py`, which launches a FastAPI/uvicorn server on `0.0.0.0:5000`.

The dashboard provides:
- **Control Center (DCC)** - Start/Stop/Restart virtual services (Klar, Sverkan, Upsum, TestView)
- **Status Log Center (SLC)** - Real-time service health metrics and live log output
- **WebSocket** at `/ws` for live updates

## TestView Service

TestView is a verification service that demonstrates HTTPS-to-SLP protocol bridging:
- **Access**: `/testview-001/` endpoint
- **SL-ID**: testview-001
- **UDP Port**: 4274
- **Bridge Port**: 9001
- **Purpose**: Verify SLP protocol integration with HTTPS gateway translation
- **Features**: Live protocol verification, latency testing, encryption verification, payload testing

## Dynamic Features (Enhanced Dashboard)

### Feature 1: Dynamic Public IP Display Bar
- Fixed top bar (height: 40px, position: fixed, z-index: 999)
- Displays: "Public IP: XX.XX.XX.XX" with refresh button
- Real-time updates via WebSocket `/ws/ip` (30s interval)
- IP fetched from `jsonip.com` API
- Refresh button for manual IP check
- Backend: `/api/public-ip` endpoint with background watcher task

### Feature 1b: Comprehensive SLP Protocol Status
- Shows 6 key metrics:
  - **SLP Address**: sl://localhost:4270 (protocol endpoint)
  - **Core Status**: Active/Inactive
  - **Encryption**: DTLS 1.3 + Noise Protocol
  - **Security Level**: Military Grade
  - **Active Connections**: Real-time count
  - **Base Port**: 4270

### Feature 1c: Empty Services Message
- When no .bat files exist, displays system status overview:
  - System Uptime: Running
  - SLP Core: Active
  - Security Status: Secure

### Feature 2: Dynamic Service Management - Any File Type
- Backend scans `csh/services/` for **ANY** file type and auto-detects:
  - `.py` files → Runs with `python3`
  - `.bat` files → Runs with `bash`
  - `.exe` files → Runs directly
  - No extension files → Auto-detects by content
- Services show real-time metrics:
  - **Uptime**: Hours/minutes elapsed (⏱)
  - **Memory**: RAM usage from process (💾)
  - **CPU**: Processor utilization percentage (📊)
  - **PID**: Process ID in green when running
- Each service row displays:
  - Service name with live metrics
  - Status badge: INITIALIZING (pulsing gold) → RUNNING (green) / STOPPED (gray)
  - Start/Stop button
- Services run independently in background sessions (survive dashboard restart)
- Dashboard auto-detects and refreshes every 5 seconds (2s when running)
- Backend: `/api/dynamic-services` GET/POST endpoints for lifecycle management
- Sample test service: `test-service.bat` (runs test_service.py indefinitely)

## Key Ports

- **5000** - Dashboard web UI (FastAPI/uvicorn)
- **4270** - SL Protocol base port (UDP)
- **4271** - Klar service (UDP)
- **4272** - Sverkan service (UDP)
- **4273** - Upsum service (UDP)
- **4274** - TestView service (UDP, verification/testing)
- **9001** - HTTPS-to-SLP bridge gateway (TestView)

## Dependencies

Python packages: fastapi, uvicorn, websockets, gunicorn, PyYAML, aiofiles, cryptography, pynacl, aiohttp, psutil, python-dotenv, click, colorama, python-multipart

## Deployment

Configured for autoscale deployment using:
```
gunicorn --bind=0.0.0.0:5000 --reuse-port --worker-class=uvicorn.workers.UvicornWorker main:app
```
