# CloudBox — Production Cloud Deployment Guide

This guide provides step-by-step instructions for deploying CloudBox on a standard Linux Cloud VM (Ubuntu 22.04 / 24.04 LTS on AWS EC2, DigitalOcean, Hetzner, GCP Compute Engine, or Azure VM).

---

## 1. Cloud Virtual Machine Prerequisites

* **OS**: Ubuntu 22.04 LTS or 24.04 LTS (x86_64).
* **Hardware**:
  * Minimum: 2 vCPUs, 2 GB RAM, 20 GB NVMe/SSD.
  * Recommended: 2-4 vCPUs, 4 GB RAM, 50+ GB NVMe/SSD.
* **Network & Firewall (Security Groups / UFW)**:
  * Port `80/tcp` (HTTP / ACME Challenge).
  * Port `443/tcp` (HTTPS TLS).
  * Port `22/tcp` (SSH management - restricted to admin IP).
  * *All other ports (5432, 6379, 9000, 9001, 5000, 5173, 9090, 3000) MUST remain closed to the public internet.*

---

## 2. Server Provisioning & Docker Setup

```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade -y

# 2. Install essential dependencies
sudo apt install -y curl git ufw fail2ban ca-certificates gnupg lsb-release

# 3. Configure UFW Firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# 4. Install official Docker Engine & Docker Compose Plugin
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. Enable and start Docker service
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

---

## 3. Cloning Repository & Configuring Environment

```bash
# 1. Clone repository
git clone https://github.com/Karthikchakala/hospital-mgmt.git /opt/cloudbox
cd /opt/cloudbox

# 2. Prepare production .env
cp .env.example .env
nano .env
```

### Essential Production Values in `.env`
```ini
APP_ENV=production
FLASK_ENV=production
FLASK_DEBUG=0
SECRET_KEY=<generate_secure_random_64_char_key>
JWT_SECRET_KEY=<generate_secure_random_64_char_key>

DOMAIN_NAME=cloudbox.yourdomain.com
ACME_EMAIL=admin@yourdomain.com
ENABLE_HTTPS=true

POSTGRES_PASSWORD=<strong_unique_db_password>
MINIO_ROOT_PASSWORD=<strong_unique_minio_password>
REDIS_PASSWORD=<strong_unique_redis_password>
GRAFANA_ADMIN_PASSWORD=<strong_unique_grafana_password>
```

---

## 4. Let's Encrypt TLS Certificate Provisioning

If a public domain name points to your VM's public IP address via DNS A Record (`cloudbox.yourdomain.com -> VM_PUBLIC_IP`):

```bash
# 1. Start Nginx reverse proxy to serve ACME challenge
docker compose up -d nginx

# 2. Run Certbot to request certificates
docker run -it --rm \
  -v /opt/cloudbox/certbot/www:/var/www/certbot \
  -v /opt/cloudbox/certbot/conf:/etc/letsencrypt \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d cloudbox.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos \
  --no-eff-email

# 3. Reload Nginx with new certificate
docker compose restart nginx
```

---

## 5. Starting CloudBox in Production Mode

```bash
# Launch application with production resource limits & restart policies
docker compose -f compose.yaml -f compose.prod.yaml up -d --build

# Verify all containers are healthy
docker compose ps
```

---

## 6. Automated Certificate Renewal Cron Job

Add a cron job to automatically renew certificates and reload Nginx:

```bash
sudo crontab -e
```
Add the line:
```cron
0 3 * * * docker run --rm -v /opt/cloudbox/certbot/www:/var/www/certbot -v /opt/cloudbox/certbot/conf:/etc/letsencrypt certbot/certbot renew --quiet && cd /opt/cloudbox && docker compose exec nginx nginx -s reload
```
