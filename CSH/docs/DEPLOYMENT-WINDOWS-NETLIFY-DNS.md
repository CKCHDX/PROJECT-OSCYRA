# Deployment Guide — Windows + Netlify DNS + Caddy

## Architecture Overview

```
Internet
    │
    │  DNS: *.oscyra.solutions → A record → your server IP
    v
┌────────────────────┐
│  Caddy (HTTPS)     │  :443
│  Auto TLS via ACME │
│  Reverse proxy     │
└────────┬───────────┘
         │  HTTP → 127.0.0.1:5000
         v
┌────────────────────┐
│  CSH (FastAPI)     │  127.0.0.1:5000
│  Host-header proxy │
└────────────────────┘
```

## 1. DNS Setup in Netlify

Netlify manages the root domain (`oscyra.solutions`) for static hosting.
Subdomains point to your Windows server via A records.

### Add A Records

In Netlify DNS (Domains → oscyra.solutions → DNS settings), add:

| Type | Name     | Value           | TTL  |
|------|----------|-----------------|------|
| A    | csh      | YOUR_SERVER_IP  | 3600 |
| A    | klar     | YOUR_SERVER_IP  | 3600 |
| A    | sverkan  | YOUR_SERVER_IP  | 3600 |
| A    | upsum    | YOUR_SERVER_IP  | 3600 |

The root domain (`oscyra.solutions`) stays pointed at Netlify for static hosting.

### Verify DNS

```bash
nslookup klar.oscyra.solutions
# Should resolve to YOUR_SERVER_IP
```

## 2. Caddy Installation (Windows)

### Download

1. Visit https://caddyserver.com/download
2. Select Windows amd64
3. Extract `caddy.exe` to `C:\Caddy\`

### Caddyfile

Create `C:\Caddy\Caddyfile`:

```
{
    email admin@oscyra.solutions
}

csh.oscyra.solutions {
    reverse_proxy 127.0.0.1:5000
}

klar.oscyra.solutions {
    reverse_proxy 127.0.0.1:5000
}

sverkan.oscyra.solutions {
    reverse_proxy 127.0.0.1:5000
}

upsum.oscyra.solutions {
    reverse_proxy 127.0.0.1:5000
}
```

All subdomains proxy to CSH on port 5000. CSH uses Host-header routing to
dispatch to the correct backend service.

### Start Caddy

```powershell
cd C:\Caddy
.\caddy.exe run
```

Caddy automatically provisions TLS certificates via Let's Encrypt.

### Install as Windows Service

```powershell
sc.exe create Caddy binPath="C:\Caddy\caddy.exe run --config C:\Caddy\Caddyfile" start=auto
sc.exe start Caddy
```

## 3. Windows Firewall Rules

Open PowerShell as Administrator:

```powershell
# Allow HTTPS (Caddy)
New-NetFirewallRule -DisplayName "Caddy HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow

# Allow HTTP for ACME challenge (Caddy redirects to HTTPS)
New-NetFirewallRule -DisplayName "Caddy HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow

# Block direct access to service ports from outside
# (Services bind 127.0.0.1, but this is defense in depth)
New-NetFirewallRule -DisplayName "Block External 4270-4274" -Direction Inbound -Protocol TCP -LocalPort 4270-4274 -RemoteAddress Any -Action Block
New-NetFirewallRule -DisplayName "Block External 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -RemoteAddress Any -Action Block

# Allow loopback (always allowed by default on Windows, but explicit)
New-NetFirewallRule -DisplayName "Allow Loopback" -Direction Inbound -InterfaceAlias "Loopback" -Action Allow
```

## 4. CSH Startup

### Prerequisites

```powershell
cd C:\path\to\CSH
pip install -r requirements.txt
```

Required packages: `fastapi`, `uvicorn`, `psutil`, `cryptography`, `pyyaml`, `httpx`

### Start CSH

```powershell
python main.py
```

This will:
1. Generate cryptographic keys if they don't exist (in `CSH/keys/`)
2. Start the SLP gateway on UDP 127.0.0.1:14270
3. Start the HTTP server on 127.0.0.1:5000
4. Begin accepting service registrations

### Install as Windows Service (NSSM)

1. Download NSSM from https://nssm.cc/
2. Install:

```powershell
nssm install CSH "C:\Python311\python.exe" "C:\path\to\CSH\main.py"
nssm set CSH AppDirectory "C:\path\to\CSH"
nssm set CSH Description "SLP Central Server Hub"
nssm set CSH Start SERVICE_AUTO_START
nssm start CSH
```

## 5. Starting Services

Services are managed through the CSH dashboard or the Python launcher:

```powershell
# Start all services
python -m CSH.launcher start --all

# Start a specific service
python -m CSH.launcher start klar

# Stop a service
python -m CSH.launcher stop klar

# Check status
python -m CSH.launcher status
```

Each service is launched via the SLP service wrapper, which:
1. Generates a keypair if needed
2. Connects to CSH via SLP
3. Starts the actual service process
4. Forwards logs and heartbeats

## 6. Troubleshooting

### DNS not resolving

- Verify A records in Netlify DNS dashboard
- Wait up to 48 hours for DNS propagation (usually < 5 minutes)
- Check with `nslookup subdomain.oscyra.solutions`

### Caddy TLS errors

- Ensure ports 80 and 443 are open in Windows Firewall
- Ensure no other service is using port 443 (e.g., IIS)
- Check Caddy logs: `caddy.exe run --config Caddyfile`

### CSH won't start

- Check Python version: `python --version` (requires 3.11+)
- Check dependencies: `pip install -r requirements.txt`
- Check port availability: `netstat -an | findstr 5000`

### Service not connecting via SLP

- Verify keys exist in `CSH/keys/`
- Check SLP gateway is listening: `netstat -an | findstr 14270`
- Check service logs in CSH dashboard
- Verify service public key is in gateway allow-list

### Dashboard shows service offline

- Heartbeat timeout is 30 seconds — wait and check again
- Verify service process is running: `tasklist | findstr python`
- Check if service crashed: review log panel in dashboard
