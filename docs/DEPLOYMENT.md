# TraceTest AI — Enterprise Production Deployment Guide

This guide describes how to deploy, configure, and maintain TraceTest AI in an enterprise production environment.

---

## 1. Prerequisites & System Requirements

### Operating System & Host Environment
- **Recommended OS**: Linux (Ubuntu 22.04 LTS / 24.04 LTS, Debian 12, RHEL 9).
- **Architecture**: `x86_64` or `aarch64`.
- **System Memory**: Minimum 4 GB RAM (8 GB recommended for concurrent sandboxed Playwright runs).
- **Disk Storage**: 20 GB SSD storage minimum (SQLite WAL and artifact capture).
- **Kernel Requirements**: Unprivileged user namespaces enabled (`kernel.unprivileged_userns_clone = 1`) for Linux network namespace isolation (`unshare -rn`).

### Software Dependencies
- **Python**: Version 3.11 or higher.
- **Node.js**: Version 20 LTS or higher (`npm` 10+).
- **SQLite**: Version 3.38+ with WAL support.
- **Chromium / Chrome**: Installed on the host system (e.g. `/usr/bin/chromium` or `/usr/bin/google-chrome-stable`).

---

## 2. Directory Architecture & File Structure

```
/opt/tracetest-ai/
├── backend/                  # FastAPI backend application
│   ├── app/                  # Application modules
│   ├── migrations/           # Alembic database migrations
│   └── requirements.txt      # Production Python dependencies
├── frontend/                 # React + TypeScript + Vite frontend
│   ├── dist/                 # Production compiled SPA bundle
│   └── package.json
├── reference_hcm/            # Reference HCM dual-build engines (v1.0 & v1.1)
├── scripts/                  # Operational utilities and health checks
├── var/                      # Persistent state directory (chmod 700)
│   ├── tracetest.db          # Primary SQLite database
│   ├── workflow_checkpoints.db # LangGraph persistent workflow state
│   ├── artifacts/            # Captured execution logs, JUnit XML, screenshots
│   └── backups/              # Automated SQLite hot backup target
└── .env                      # Production environment configuration (chmod 600)
```

---

## 3. Environment Configuration (`.env`)

Generate a production configuration file from the template:

```bash
cp .env.example .env
chmod 600 .env
```

### Required Configuration Directives

```ini
# Application Core
TRACETEST_ENV=production
TRACETEST_SECRET_KEY=94c8e76f2d5a1b0c93e4f8a2b5d6e7f1c2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7  # Generate with: openssl rand -hex 32
TRACETEST_DATA_DIR=/opt/tracetest-ai/var
TRACETEST_COOKIE_SECURE=true
TRACETEST_CORS_ORIGINS=https://tracetest.yourdomain.com

# Multi-Credential Groq Pool (Primary LLM Provider)
GROQ_API_KEY=gsk_your_primary_groq_key
GROQ_API_KEY2=gsk_your_secondary_groq_key
GROQ_API_KEY3=gsk_your_tertiary_groq_key
GROQ_MODEL=openai/gpt-oss-120b

# Multi-Credential Gemini Pool (Failover LLM Provider)
GEMINI_API_KEY=your_primary_gemini_key
GEMINI_API_KEY2=your_secondary_gemini_key
GEMINI_API_KEY3=your_tertiary_gemini_key
GEMINI_MODEL=gemini-2.5-flash

# Execution Sandbox Configuration
TRACETEST_CHROMIUM_EXECUTABLE=/usr/bin/chromium
TRACETEST_EXEC_MEMORY_MB=512
TRACETEST_EXEC_TIMEOUT=60
TRACETEST_EXEC_MAX_OUTPUT=5242880

# Seed Passwords (Mandatory for Account Activation)
TRACETEST_ADMIN_PASSWORD=ComplexEnterprisePassword1!
TRACETEST_LEAD_PASSWORD=ComplexEnterprisePassword2!
TRACETEST_AUTHOR_PASSWORD=ComplexEnterprisePassword3!
TRACETEST_REVIEWER_PASSWORD=ComplexEnterprisePassword4!
TRACETEST_AUDITOR_PASSWORD=ComplexEnterprisePassword5!
```

---

## 4. Installation & Database Initialization

```bash
# 1. Set up Python virtual environment
python3.11 -m venv /opt/tracetest-ai/.venv
source /opt/tracetest-ai/.venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

# 2. Run Alembic database migrations
cd /opt/tracetest-ai/backend
alembic upgrade head

# 3. Seed initial organizational data, roles, and Reference HCM suites
PYTHONPATH=. python -m app.seed.seed

# 4. Build frontend production assets
cd /opt/tracetest-ai/frontend
npm ci
npm run build
```

---

## 5. Process Supervision (Systemd)

Create a systemd unit file `/etc/systemd/system/tracetest.service`:

```ini
[Unit]
Description=TraceTest AI Backend Service
After=network.target

[Service]
User=tracetest
Group=tracetest
WorkingDirectory=/opt/tracetest-ai/backend
EnvironmentFile=/opt/tracetest-ai/.env
ExecStart=/opt/tracetest-ai/.venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips='127.0.0.1'
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

*Note on Workers*: TraceTest AI utilizes SQLite with in-process background worker threads. Running `--workers 1` ensures optimal serialized write coordination to SQLite WAL mode and eliminates multi-process file locking contention.

---

## 6. Reverse Proxy & TLS Configuration (NGINX)

Configure NGINX to terminate TLS, enforce HTTPS, serve frontend static assets, and proxy API calls to the FastAPI backend:

```nginx
server {
    listen 80;
    server_name tracetest.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tracetest.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/tracetest.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tracetest.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "same-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Frontend Static Bundle
    root /opt/tracetest-ai/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API & SSE Stream Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Disable buffering for Server-Sent Events (SSE)
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

---

## 7. Backup and Disaster Recovery

### Automated Daily Hot Backup (Cron)
Add the following entry to `/etc/cron.d/tracetest-backup`:

```bash
0 2 * * * tracetest sqlite3 /opt/tracetest-ai/var/tracetest.db "VACUUM INTO '/opt/tracetest-ai/var/backups/tracetest_\$(date +\%Y\%m\%d_\%H\%M\%S).db';" && find /opt/tracetest-ai/var/backups/ -name "*.db" -mtime +14 -delete
```

### Restoring from Backup
```bash
sudo systemctl stop tracetest
cp /opt/tracetest-ai/var/backups/tracetest_20261105_020000.db /opt/tracetest-ai/var/tracetest.db
sudo systemctl start tracetest
```

