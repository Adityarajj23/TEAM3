# Production Deployment Guide — TraceTest AI

## 1. Overview

TraceTest AI is designed for streamlined deployment on Linux environments. The application requires Python 3.11+ and Node.js 18+ and operates with zero external service dependencies (embedded SQLite WAL database and local POSIX sandbox execution).

---

## 2. System Prerequisites

- **Operating System**: Linux (Ubuntu 22.04+, Debian 12+, Arch Linux, or RHEL 9+)
- **CPU**: 2+ cores (4+ cores recommended for concurrent sandbox runs)
- **Memory**: 4GB RAM minimum (8GB recommended for Playwright browser automation)
- **Disk**: 10GB free storage for SQLite databases and execution artifacts
- **Software**:
  - Python 3.11 or higher
  - Node.js 18+ and npm
  - Chromium browser (`/usr/bin/chromium` or Google Chrome)

---

## 3. Production Deployment Architecture

```
[ Incoming HTTPS:443 ]
           |
           v
[ Nginx Reverse Proxy ]
     |             |
     | /api/v1     | / (Static Assets)
     v             v
[ Uvicorn 8000 ]  [ Built SPA /dist ]
     |
[ SQLite WAL ]
```

---

## 4. Step-by-Step Installation

### Step 1: Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/sohan10012/TEAM3.git /opt/tracetest-ai
cd /opt/tracetest-ai

python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### Step 2: Build Frontend Assets
```bash
cd frontend
npm install
npm run build
cd ..
```
Static assets will be generated in `frontend/dist`.

### Step 3: Configure Environment
Create production `.env`:
```ini
TRACETEST_ENV=production
TRACETEST_DATA_DIR=/opt/tracetest-ai/var
TRACETEST_SECRET_KEY=generate-a-strong-random-64-char-hex-secret
TRACETEST_CORS_ORIGINS=https://tracetest.example.com
TRACETEST_SINGLE_OPERATOR=true
TRACETEST_CHROMIUM_EXECUTABLE=/usr/bin/chromium

# API Keys
GROQ_KEY=gsk_...
GROQ_KEY2=gsk_...
GROQ_MODEL=openai/gpt-oss-120b

GEMINI_KEY=AQ.Ab8RN6...
GEMINI_KEY2=AQ.Ab8RN6...
GEMINI_MODEL=gemini-2.5-flash
```

### Step 4: Systemd Service Configuration
Create `/etc/systemd/system/tracetest.service`:
```ini
[Unit]
Description=TraceTest AI Quality Engineering Platform
After=network.target

[Service]
Type=simple
User=sohan
WorkingDirectory=/opt/tracetest-ai
EnvironmentFile=/opt/tracetest-ai/.env
ExecStart=/opt/tracetest-ai/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tracetest
```

### Step 5: Nginx Configuration
```nginx
server {
    listen 80;
    server_name tracetest.example.com;

    # Frontend SPA
    location / {
        root /opt/tracetest-ai/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API Reverse Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 5. Backup & Maintenance

- **Database Backup**: The SQLite database (`var/tracetest.db`) can be safely backed up online using SQLite's backup API or CLI:
  ```bash
  sqlite3 var/tracetest.db ".backup var/backups/tracetest-$(date +%F).db"
  ```
- **Artifacts Retention**: Clean old temporary execution logs older than 30 days:
  ```bash
  find var/artifacts/executions -type f -mtime +30 -delete
  ```
