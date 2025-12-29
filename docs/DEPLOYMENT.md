# Genesis AGI - Deployment Guide

Complete guide for deploying Genesis in production.

## Quick Deploy with Docker

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- API keys (at least Groq for free option)

### Steps

1. **Clone repository**
```bash
git clone https://github.com/sshaik37/Genesis-AGI.git
cd Genesis-AGI
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. **Start services**
```bash
docker-compose up -d
```

4. **Access**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Playground: http://localhost:3000

## Manual Deployment

### System Requirements

**Minimum**:
- CPU: 2 cores
- RAM: 4 GB
- Storage: 20 GB SSD
- OS: Linux (Ubuntu 22.04+ recommended)

**Recommended**:
- CPU: 4+ cores
- RAM: 8+ GB
- Storage: 50+ GB SSD
- OS: Ubuntu 22.04 LTS

### Installation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Genesis
git clone https://github.com/sshaik37/Genesis-AGI.git
cd Genesis-AGI
python3.11 -m venv venv
source venv/bin/activate
pip install -e .

# Configure
genesis init
# Edit .env with your API keys
```

### Running as Service

#### API Server Service

Create `/etc/systemd/system/genesis-api.service`:

```ini
[Unit]
Description=Genesis AGI API Server
After=network.target redis.service

[Service]
Type=simple
User=genesis
WorkingDirectory=/opt/genesis-agi
Environment="PATH=/opt/genesis-agi/venv/bin"
ExecStart=/opt/genesis-agi/venv/bin/genesis server --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable genesis-api
sudo systemctl start genesis-api
sudo systemctl status genesis-api
```

#### Mind Daemon Service (24/7 Operation)

For continuous 24/7 Mind operation, use the Mind daemon template.

Create `/etc/systemd/system/genesis-mind@.service`:

```ini
[Unit]
Description=Genesis Mind Daemon - %i
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=genesis
WorkingDirectory=/opt/genesis-agi
Environment="PATH=/opt/genesis-agi/venv/bin"
ExecStart=/opt/genesis-agi/venv/bin/genesis daemon start %i --save-interval 300
ExecStop=/opt/genesis-agi/venv/bin/genesis daemon stop %i --graceful
Restart=always
RestartSec=30

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/genesis-agi/data /var/log/genesis

# Resource limits
LimitNOFILE=65536
CPUQuota=80%
MemoryMax=2G

[Install]
WantedBy=multi-user.target
```

Deploy a specific Mind as daemon:
```bash
# Enable and start Mind daemon for "atlas"
sudo systemctl enable genesis-mind@atlas
sudo systemctl start genesis-mind@atlas

# Check status
sudo systemctl status genesis-mind@atlas

# View logs
sudo journalctl -u genesis-mind@atlas -f

# Stop gracefully
sudo systemctl stop genesis-mind@atlas
```

Multiple Minds can run simultaneously:
```bash
sudo systemctl start genesis-mind@atlas
sudo systemctl start genesis-mind@nova
sudo systemctl start genesis-mind@echo
```

## Cloud Platforms

### AWS Deployment

**EC2 + ECS**:

1. Launch EC2 instance (t3.medium or larger)
2. Install Docker
3. Deploy using Docker Compose
4. Configure security groups (ports 8000, 3000)
5. Set up Elastic IP
6. Configure CloudWatch for monitoring

### Google Cloud Platform

**Cloud Run**:

```bash
# Build and push container
gcloud builds submit --tag gcr.io/PROJECT_ID/genesis-api

# Deploy
gcloud run deploy genesis-api \
  --image gcr.io/PROJECT_ID/genesis-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GROQ_API_KEY=$GROQ_API_KEY
```

### DigitalOcean

**App Platform**:

1. Connect GitHub repository
2. Configure build settings
3. Add environment variables
4. Deploy

### Heroku

```bash
# Login
heroku login

# Create app
heroku create genesis-agi-app

# Add buildpack
heroku buildpacks:add --index 1 heroku/python

# Configure env vars
heroku config:set GROQ_API_KEY=your-key

# Deploy
git push heroku main

# Scale
heroku ps:scale web=1
```

## Production Configuration

### Redis Setup (Required for v0.3.0+)

Redis is required for LLM response caching (90% cost reduction).

**Install Redis**:
```bash
# Ubuntu/Debian
sudo apt install redis-server -y

# Start Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Verify
redis-cli ping  # Should return "PONG"
```

**Docker Redis**:
```yaml
# Already included in docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
```

**Configure Redis Connection**:
```env
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
CACHE_TTL=86400  # 24 hours
```

### Environment Variables

**Required**:
```env
# At least one model provider
GROQ_API_KEY=your-groq-key  # Free option!

# Or paid options
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Redis (strongly recommended)
REDIS_URL=redis://localhost:6379/0
```

**Optional**:
```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/genesis

# Security
SECRET_KEY=your-secret-key-change-this
CORS_ORIGINS=https://yourdomain.com

# Performance
MAX_AUTONOMOUS_ACTIONS_PER_HOUR=100
CONSCIOUSNESS_TICK_INTERVAL=3600

# Cache
CACHE_ENABLED=true
CACHE_TTL=86400

# Daemon
DAEMON_SAVE_INTERVAL=300
DAEMON_HEALTH_CHECK_INTERVAL=60

# Integrations
EMAIL_ADDRESS=mind@yourdomain.com
EMAIL_PASSWORD=app-password
SLACK_BOT_TOKEN=xoxb-your-token
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name genesis.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

### SSL/TLS (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d genesis.yourdomain.com
```

## 24/7 Daemon Deployment

### Docker Daemon Mode

**Using Docker Compose**:

```yaml
# docker-compose.yml
services:
  genesis-mind-atlas:
    build: .
    command: genesis daemon start atlas --save-interval 300
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - REDIS_URL=redis://redis:6379/0
      - EMAIL_ADDRESS=${EMAIL_ADDRESS}
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
    depends_on:
      - redis
    restart: unless-stopped
    volumes:
      - mind_data:/data/.genesis
```

Start:
```bash
docker-compose up -d genesis-mind-atlas
docker-compose logs -f genesis-mind-atlas
```

### CLI Daemon Mode

Start Mind daemon from command line:
```bash
# Start daemon
genesis daemon start atlas

# Check status
genesis daemon status atlas

# List all running daemons
genesis daemon list

# Stop gracefully
genesis daemon stop atlas
```

### Programmatic Daemon Mode

```python
from genesis.daemon import MindDaemon
import asyncio

async def main():
    daemon = MindDaemon(
        mind_id="atlas",
        save_interval=300,
        log_level="INFO"
    )

    await daemon.start()
    # Runs until SIGTERM or SIGINT

asyncio.run(main())
```

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# System status
curl http://localhost:8000/api/v1/system/status

# Daemon status
genesis daemon status atlas

# Cache statistics
curl http://localhost:8000/api/v1/cache/stats
```

### Logging

```python
# Configure in genesis/config/settings.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/genesis/api.log'),
        logging.StreamHandler()
    ]
)
```

### Monitoring Tools

- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **Sentry** - Error tracking
- **CloudWatch** - AWS monitoring

## Scaling

### Horizontal Scaling

- Deploy multiple API instances
- Use load balancer (nginx, AWS ALB)
- Shared database for Mind storage
- Redis for session management

### Database Scaling

- Move from SQLite to PostgreSQL
- Separate vector DB server
- Database replication
- Connection pooling

## Backup & Recovery

### Automated Backups

```bash
#!/bin/bash
# backup-minds.sh

BACKUP_DIR="/backups/genesis"
DATA_DIR="/data/.genesis"

# Create backup
tar -czf "$BACKUP_DIR/minds-$(date +%Y%m%d-%H%M%S).tar.gz" "$DATA_DIR/minds"

# Keep last 30 days
find "$BACKUP_DIR" -name "minds-*.tar.gz" -mtime +30 -delete
```

### Restore

```bash
tar -xzf minds-20250101-120000.tar.gz -C /data/.genesis/
```

## Security Best Practices

1. **API Keys**: Use environment variables, never commit
2. **HTTPS**: Always use SSL/TLS in production
3. **Firewall**: Restrict access to necessary ports
4. **Updates**: Keep dependencies updated
5. **Secrets**: Rotate keys regularly
6. **Backups**: Daily automated backups
7. **Monitoring**: Set up alerts for anomalies

## Troubleshooting

### Common Issues

**API won't start**:
```bash
# Check logs
sudo journalctl -u genesis-api -n 100

# Check port
sudo netstat -tlnp | grep 8000
```

**Out of memory**:
```bash
# Check memory
free -h

# Adjust swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**WebSocket connection fails**:
- Check CORS settings
- Verify WebSocket proxy configuration
- Check firewall rules

## Support

- GitHub Issues: https://github.com/sshaik37/Genesis-AGI/issues
- Documentation: https://shahansha.com

---

**Ready for production deployment!** 🚀
