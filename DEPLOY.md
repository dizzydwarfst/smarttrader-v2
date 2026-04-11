# SmartTrader v2.0 — 24/7 Deployment Guide

## Option 1: Docker (Recommended)

The simplest way to run 24/7 on any server.

### Quick Start
```bash
# 1. Make sure your .env file has your OANDA credentials
# 2. Build and run
docker-compose up -d --build

# Check logs
docker-compose logs -f

# Stop
docker-compose down
```

The `restart: always` in docker-compose.yml means the bot auto-restarts on crash or server reboot.

Dashboard: `http://your-server-ip:8000`

---

## Option 2: VPS (DigitalOcean / Hetzner / AWS Lightsail)

Cheapest always-on option: ~$4-6/month.

### Setup on Ubuntu VPS
```bash
# SSH into your server
ssh root@your-server-ip

# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone/upload your project
git clone <your-repo> smarttrader-v2
cd smarttrader-v2

# Create .env with your credentials
cp env.example .env
nano .env  # paste your OANDA_API_KEY, OANDA_ACCOUNT_ID, etc.

# Run
docker-compose up -d --build

# Auto-starts on reboot thanks to restart: always
```

### Without Docker (systemd)
```bash
# Install Python
sudo apt update && sudo apt install python3 python3-pip python3-venv -y

cd smarttrader-v2
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create systemd service for 24/7
sudo tee /etc/systemd/system/smarttrader.service << 'EOF'
[Unit]
Description=SmartTrader Bot v2.0
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/smarttrader-v2
ExecStart=/root/smarttrader-v2/venv/bin/python bot.py
Restart=always
RestartSec=10
Environment=API_HOST=0.0.0.0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable smarttrader
sudo systemctl start smarttrader

# Check status
sudo systemctl status smarttrader
sudo journalctl -u smarttrader -f  # live logs
```

---

## Option 3: Railway / Render (Zero-config cloud)

### Railway.app
1. Push your code to GitHub
2. Go to [railway.app](https://railway.app), connect your repo
3. Add environment variables (OANDA_API_KEY, etc.)
4. Railway auto-deploys and keeps it running 24/7
5. Cost: ~$5/month

### Render.com
1. Push to GitHub
2. Create a "Background Worker" on [render.com](https://render.com)
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python bot.py`
5. Add env vars
6. Cost: ~$7/month

---

## Option 4: Local PC (Always-On)

If you want to keep running on your Windows machine:

```bash
# Use Windows Task Scheduler to auto-start on boot:
# Action: Start a program
# Program: python
# Arguments: bot.py
# Start in: C:\path\to\smarttrader-v2
```

Or use `nssm` (Non-Sucking Service Manager) to run as a Windows service:
```bash
nssm install SmartTrader python bot.py
nssm set SmartTrader AppDirectory C:\path\to\smarttrader-v2
nssm start SmartTrader
```

---

## Remote Access to Dashboard

Once deployed, access your dashboard from anywhere:

- **Direct**: `http://your-server-ip:8000`
- **With domain**: Point a domain to your server, use nginx as reverse proxy
- **Secure**: Add Cloudflare Tunnel for HTTPS without opening ports

### Nginx reverse proxy (optional)
```nginx
server {
    listen 80;
    server_name trader.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Controlling the Bot Remotely

Once deployed, use the dashboard control panel or call the API directly:

```bash
# Switch to aggressive mode
curl -X POST http://your-server:8000/api/profile/activate \
  -H "Content-Type: application/json" \
  -d '{"profile": "aggressive"}'

# Pause the bot
curl -X POST http://your-server:8000/api/bot/pause

# Resume
curl -X POST http://your-server:8000/api/bot/resume

# Change individual settings
curl -X POST http://your-server:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"poll_interval": 10, "max_positions": 5}'

# Close all positions
curl -X POST http://your-server:8000/api/bot/close-all

# Check status
curl http://your-server:8000/api/bot/control-status
```

---

## Security Note

The dashboard has **no authentication** by default. For production:
1. Use a firewall to restrict port 8000 to your IP only
2. Or put it behind a VPN (WireGuard/Tailscale)
3. Or add nginx with basic auth in front of it
