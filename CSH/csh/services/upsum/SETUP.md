# Upsum Setup Guide

## Quick Start (Local Development)

### Windows

1. **Run the automated setup:**
   ```cmd
   RUNME.bat
   ```
   This will automatically:
   - Create Python virtual environment
   - Install all backend dependencies (FastAPI, uvicorn, wikipediaapi)
   - Install frontend dependencies (if using npm version)
   - Start backend on http://localhost:8000
   - Open frontend on http://localhost:5173

### Manual Setup

If you prefer to set up manually or troubleshoot:

#### Backend Setup

1. Navigate to backend directory:
   ```bash
   cd backend
   ```

2. Create virtual environment:
   ```bash
   python -m venv .venv
   ```

3. Activate virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Start backend:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Frontend Setup

The frontend is a standalone HTML file that can be:

1. **Served by backend** (automatic):
   - Access at http://localhost:8000/

2. **Opened directly**:
   - Open `frontend/frontend.html` in your browser
   - Note: CORS may require backend adjustments

---

## Production Deployment

### Option 1: Deploy to oscyra.solutions/upsum

For deployment on your domain with proper routing:

#### Backend Deployment

1. **Set up production server** (Ubuntu/Debian recommended):
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv nginx
   ```

2. **Clone repository**:
   ```bash
   cd /var/www
   git clone https://github.com/CKCHDX/upsum.git
   cd upsum/backend
   ```

3. **Set up Python environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn  # Production WSGI server
   ```

4. **Create systemd service** (`/etc/systemd/system/upsum.service`):
   ```ini
   [Unit]
   Description=Upsum Backend API
   After=network.target

   [Service]
   Type=notify
   User=www-data
   WorkingDirectory=/var/www/upsum/backend
   Environment="PATH=/var/www/upsum/backend/.venv/bin"
   ExecStart=/var/www/upsum/backend/.venv/bin/gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000 main:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

5. **Enable and start service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable upsum
   sudo systemctl start upsum
   ```

#### Nginx Configuration

Create `/etc/nginx/sites-available/upsum`:

```nginx
server {
    listen 80;
    server_name oscyra.solutions;

    location /upsum {
        alias /var/www/upsum/frontend;
        try_files $uri $uri/ /upsum/frontend.html;
        index frontend.html;
    }

    location /upsum/api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend routes (search, health)
    location ~ ^/(search|health) {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/upsum /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### SSL/TLS with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d oscyra.solutions
```

---

### Option 2: Docker Deployment

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t upsum .
docker run -d -p 8000:8000 --name upsum upsum
```

---

## Testing the Integration

### Test Backend API

1. **Health check**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Search test**:
   ```bash
   curl "http://localhost:8000/search?q=Stockholm"
   ```

3. **API Documentation**:
   - Visit http://localhost:8000/api/docs

### Test Frontend

1. Open http://localhost:8000 or http://localhost:5173
2. Try searching for:
   - "Stockholm"
   - "Gustav Vasa"
   - "Sveriges historia"
   - "Minecraft"

---

## Troubleshooting

### Backend won't start

- **Check Python version**: Requires Python 3.8+
  ```bash
  python --version
  ```

- **Reinstall dependencies**:
  ```bash
  pip install --upgrade -r requirements.txt
  ```

- **Check port availability**:
  ```bash
  netstat -ano | findstr :8000  # Windows
  lsof -i :8000                  # Linux/Mac
  ```

### No search results

- **Verify Wikipedia API access**:
  ```python
  import wikipediaapi
  wiki = wikipediaapi.Wikipedia('sv', 'test/1.0')
  page = wiki.page('Stockholm')
  print(page.exists())
  ```

- **Check internet connection**: Wikipedia API requires internet access

- **Review backend logs**: Look for error messages in terminal

### CORS errors

- Ensure `allow_origins` in `backend/main.py` includes your frontend URL
- For production, restrict to specific domains:
  ```python
  allow_origins=["https://oscyra.solutions"]
  ```

---

## Performance Optimization

### Caching (Future Enhancement)

Add Redis for caching frequent searches:

```python
import redis
from functools import lru_cache

redis_client = redis.Redis(host='localhost', port=6379, db=0)

@lru_cache(maxsize=100)
def cached_search(query: str):
    # Implementation
    pass
```

### Database Integration (Future)

For local Wikipedia mirror:

1. Download Swedish Wikipedia dump:
   ```bash
   wget https://dumps.wikimedia.org/svwiki/latest/svwiki-latest-pages-articles.xml.bz2
   ```

2. Parse and index with WikiExtractor or similar tools

3. Set up Elasticsearch or PostgreSQL with full-text search

---

## Contributing

See README.md for project vision and roadmap.

## License

Built upon Wikipedia data under Creative Commons Attribution-ShareAlike License.
