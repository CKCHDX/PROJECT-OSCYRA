# Upsum Deployment Guide

Deploy Upsum backend to be accessible at `https://upsum.oscyra.solutions`

## Network Setup

### Netlify DNS Configuration

1. **Get your PC's local IP**:
   ```cmd
   ipconfig
   ```
   Look for "IPv4 Address" (e.g., `192.168.1.100`)

2. **Get your public IP**:
   Visit https://whatismyipaddress.com/ or run:
   ```cmd
   curl ifconfig.me
   ```

3. **Configure DNS in Netlify**:
   - Go to Netlify DNS settings for `oscyra.solutions`
   - Add A record:
     - **Name**: `upsum`
     - **Value**: Your public IP address
     - **TTL**: 3600

4. **Port Forwarding** (on your router):
   - Forward port `8000` to your PC's local IP
   - Protocol: TCP
   - Internal port: `8000`
   - External port: `8000` (or `80`/`443` if you want standard HTTP/HTTPS)

## Backend Deployment Options

### Option 1: Local Development Server (Quick Test)

For testing with local network access:

```cmd
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Access via:
- Local: `http://localhost:8000`
- Network: `http://192.168.1.100:8000` (use your local IP)
- Public: `http://upsum.oscyra.solutions:8000` (after DNS propagates)

### Option 2: Production Server (Recommended)

#### Windows Service with NSSM

1. **Install NSSM** (Non-Sucking Service Manager):
   - Download from https://nssm.cc/download
   - Extract to `C:\nssm`

2. **Create Python script** (`C:\upsum\start_backend.bat`):
   ```batch
   @echo off
   cd C:\upsum\backend
   call .venv\Scripts\activate
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

3. **Install as Windows service**:
   ```cmd
   nssm install Upsum "C:\upsum\start_backend.bat"
   nssm set Upsum AppDirectory "C:\upsum\backend"
   nssm set Upsum DisplayName "Upsum Backend"
   nssm set Upsum Description "Upsum Swedish Knowledge Platform API"
   nssm set Upsum Start SERVICE_AUTO_START
   nssm start Upsum
   ```

4. **Manage service**:
   ```cmd
   nssm start Upsum
   nssm stop Upsum
   nssm restart Upsum
   nssm remove Upsum confirm
   ```

### Option 3: Linux VPS (Cloud Deployment)

For production cloud hosting:

#### Setup on Ubuntu/Debian

1. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv nginx
   ```

2. **Clone and setup**:
   ```bash
   cd /var/www
   git clone https://github.com/CKCHDX/upsum.git
   cd upsum/backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn
   ```

3. **Create systemd service** (`/etc/systemd/system/upsum.service`):
   ```ini
   [Unit]
   Description=Upsum Backend API
   After=network.target

   [Service]
   Type=notify
   User=www-data
   WorkingDirectory=/var/www/upsum/backend
   Environment="PATH=/var/www/upsum/backend/.venv/bin"
   ExecStart=/var/www/upsum/backend/.venv/bin/gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 main:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

4. **Enable and start**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable upsum
   sudo systemctl start upsum
   sudo systemctl status upsum
   ```

#### Nginx Configuration

Create `/etc/nginx/sites-available/upsum`:

```nginx
server {
    listen 80;
    server_name upsum.oscyra.solutions;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/upsum /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### SSL/TLS with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d upsum.oscyra.solutions
```

## Testing Deployment

### Health Check

```bash
curl https://upsum.oscyra.solutions/health
```

Expected response:
```json
{
  "status": "ok",
  "message": "Upsum backend is running.",
  "version": "1.0.0",
  "features": [
    "Swedish Wikipedia integration",
    "Natural Input Language (NIL)",
    "Definiteness normalization",
    "Compound word handling"
  ]
}
```

### Search Test

```bash
curl "https://upsum.oscyra.solutions/search?q=Stockholm"
```

### Browser Test

Open: `https://upsum.oscyra.solutions`

## Desktop Application

Once deployed, users can access via:

1. **Browser**: Navigate to `https://upsum.oscyra.solutions`
2. **Desktop App**: Run `desktop/upsum_desktop.py`

## Firewall Configuration

### Windows Firewall

```cmd
netsh advfirewall firewall add rule name="Upsum Backend" dir=in action=allow protocol=TCP localport=8000
```

### Linux UFW

```bash
sudo ufw allow 8000/tcp
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## Monitoring

### Check Logs (Linux)

```bash
sudo journalctl -u upsum -f
```

### Check Logs (Windows)

Check service logs in Event Viewer or use:
```cmd
nssm status Upsum
```

## Troubleshooting

### DNS Not Resolving

1. Check DNS propagation: `nslookup upsum.oscyra.solutions`
2. Wait 5-10 minutes for Netlify DNS to propagate
3. Clear DNS cache: `ipconfig /flushdns` (Windows)

### Cannot Connect Externally

1. Verify public IP: `curl ifconfig.me`
2. Check port forwarding on router
3. Verify firewall allows port 8000
4. Test from phone (mobile data, not WiFi)

### 403 Forbidden from Wikipedia

- The User-Agent header is now properly set
- If issues persist, check internet connectivity on server

### Desktop App Won't Connect

1. Verify backend is running: `curl https://upsum.oscyra.solutions/health`
2. Check CORS settings in `backend/main.py`
3. Ensure SSL certificate is valid (for HTTPS)

## Security Recommendations

1. **Use HTTPS**: Set up SSL with Let's Encrypt
2. **Restrict CORS**: Remove `"*"` from allowed origins in production
3. **Rate Limiting**: Add rate limiting to prevent abuse
4. **Firewall**: Only expose necessary ports
5. **Updates**: Keep dependencies updated regularly

## Maintenance

### Update Backend

```bash
cd /var/www/upsum
git pull origin main
sudo systemctl restart upsum
```

### Update Desktop App

Users should pull latest:
```cmd
git pull origin main
cd desktop
pip install -r requirements.txt
```

---

**Next Steps:**

1. Configure DNS in Netlify
2. Set up port forwarding on router
3. Deploy backend (choose option 1, 2, or 3)
4. Test with health check
5. Install and run desktop app

**Support:** https://github.com/CKCHDX/upsum/issues
