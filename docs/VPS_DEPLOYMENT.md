# Genesis Server - VPS Deployment Guide

Quick guide to deploy Genesis API server on a VPS with Docker and SSL.

## Prerequisites

- VPS with Ubuntu 22.04+ (minimum 2GB RAM, 2 CPU cores)
- Domain name with DNS access
- SSH access to VPS
- API keys (OpenRouter, Groq, or other LLM providers)

## Step 1: Initial VPS Setup

```bash
# SSH into your VPS
ssh root@your-vps-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install docker.io docker-compose -y
sudo systemctl start docker
sudo systemctl enable docker

# Create user (optional)
sudo useradd -m -s /bin/bash administrator
sudo usermod -aG sudo,docker administrator
```

## Step 2: Clone and Configure Genesis

```bash
# Clone repository
cd ~
git clone https://github.com/sshaik37/Genesis-AGI.git genesis-agi
cd genesis-agi

# Create .env file with your API keys
cat > .env << 'EOF'
# LLM Provider Keys (get from respective platforms)
OPENROUTER_API_KEY=your-key-here
GROQ_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here

# Model Configuration
DEFAULT_REASONING_MODEL=openrouter/deepseek/deepseek-r1-0528:free
DEFAULT_FAST_MODEL=openrouter/deepseek/deepseek-r1-0528:free

# Redis for caching
REDIS_URL=redis://redis:6379
ENABLE_LLM_CACHE=true

# Disable multimodal features in Docker (requires OpenCV libs)
DISABLE_MULTIMODAL=true

# CORS Origins (comma-separated, supports wildcards)
CORS_ORIGINS=https://*.yourdomain.com,https://your-frontend.vercel.app
EOF

# Edit .env with your actual keys
nano .env
```

## Step 3: Deploy with Docker

```bash
# Build and start services
sudo docker-compose up -d --build

# Check status
sudo docker-compose ps

# View logs
sudo docker-compose logs -f genesis-api

# Verify API is running
curl http://localhost:8000/health
```

## Step 4: Setup Domain and SSL

### Configure DNS

1. Go to your domain registrar/DNS provider
2. Add an A record:
   - Name: `api` (or your subdomain)
   - Type: `A`
   - Value: `your-vps-ip`
   - TTL: `300`

Wait 5-10 minutes for DNS propagation.

### Install Nginx and SSL

```bash
# Install nginx and certbot
sudo apt install nginx certbot python3-certbot-nginx -y

# Create nginx configuration
sudo tee /etc/nginx/sites-available/genesis-api << 'EOF'
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL managed by certbot
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        # Proxy to Genesis API
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        
        # Headers
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/genesis-api /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test nginx
sudo nginx -t

# Get SSL certificate (replace email and domain)
sudo certbot --nginx -d api.yourdomain.com \
  --non-interactive --agree-tos --email your@email.com --redirect

# Restart nginx
sudo systemctl restart nginx

# Test auto-renewal
sudo certbot renew --dry-run
```

## Step 5: Verify Deployment

```bash
# Test health endpoint
curl https://api.yourdomain.com/health

# Test CORS
curl -i https://api.yourdomain.com/health \
  -H "Origin: https://your-frontend.vercel.app"

# Check API docs
# Visit: https://api.yourdomain.com/docs
```

## Step 6: Update CORS for Frontend

Update your frontend environment variables:

```bash
# For Vercel deployment
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# For Hostinger or other hosting
# Set this in your hosting control panel
```

## Management Commands

```bash
# View logs
sudo docker-compose logs -f genesis-api

# Restart services
sudo docker-compose restart

# Stop services
sudo docker-compose down

# Update code and redeploy
cd ~/genesis-agi
git pull
sudo docker-compose down
sudo docker-compose up -d --build

# Update environment variables without rebuild
# Edit .env file
nano .env
# Restart to apply changes
sudo docker-compose down
sudo docker-compose up -d
```

## Firewall Configuration (Optional)

```bash
# Allow SSH, HTTP, HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

## Troubleshooting

### Container not starting

```bash
# Check logs
sudo docker-compose logs genesis-api

# Rebuild from scratch
sudo docker-compose down -v
sudo docker-compose build --no-cache
sudo docker-compose up -d
```

### CORS errors

```bash
# Verify CORS settings are loaded
sudo docker-compose exec genesis-api python -c \
  "from genesis.config import get_settings; \
   s = get_settings(); \
   print('CORS:', s.cors_origins_list)"

# If showing default, recreate container
sudo docker-compose down
sudo docker-compose up -d
```

### SSL certificate issues

```bash
# Check certificate status
sudo certbot certificates

# Renew manually
sudo certbot renew

# Check nginx configuration
sudo nginx -t
```

### API not accessible

```bash
# Check if API is running
curl http://localhost:8000/health

# Check nginx
sudo systemctl status nginx

# Check Docker
sudo docker-compose ps
```

## Production Recommendations

1. **Backups**: Set up automated backups for:
   - Database files (`.genesis/` directory)
   - Environment variables (.env file)
   - Docker volumes: `sudo docker-compose down && sudo tar -czf backup.tar.gz .`

2. **Monitoring**: Consider adding:
   - Uptime monitoring (UptimeRobot, Pingdom)
   - Log aggregation (Loki, ELK stack)
   - Resource monitoring (Prometheus, Grafana)

3. **Security**:
   - Keep system updated: `sudo apt update && sudo apt upgrade`
   - Use strong passwords
   - Configure fail2ban: `sudo apt install fail2ban`
   - Regular security audits

4. **Performance**:
   - Enable Redis caching (already configured)
   - Monitor memory usage: `docker stats`
   - Scale horizontally if needed

## Cost Optimization

- Use free LLM providers (OpenRouter free tier, Groq)
- Enable Redis caching to reduce API calls
- `DISABLE_MULTIMODAL=true` saves resources
- Monitor usage with `sudo docker-compose logs genesis-api | grep "LLM request"`

## Support

For issues or questions:
- GitHub Issues: https://github.com/sshaik37/Genesis-AGI/issues
- Documentation: https://github.com/sshaik37/Genesis-AGI/tree/main/docs

---

**Your Genesis API is now live at `https://api.yourdomain.com`!** 🚀
