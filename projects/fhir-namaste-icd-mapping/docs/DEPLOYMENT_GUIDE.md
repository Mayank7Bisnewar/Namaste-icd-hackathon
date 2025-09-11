# FHIR NAMASTE-ICD Mapping Service - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the FHIR NAMASTE-ICD Mapping Service in various environments, from local development to production deployment.

## Prerequisites

### System Requirements

**Minimum Requirements:**
- OS: Ubuntu 20.04+, CentOS 8+, macOS 10.15+, or Windows 10+
- CPU: 2 cores
- RAM: 4GB
- Storage: 10GB available space
- Python: 3.10 or higher

**Recommended Production:**
- OS: Ubuntu 22.04 LTS
- CPU: 4 cores
- RAM: 8GB
- Storage: 50GB SSD
- Python: 3.11+

### Software Dependencies

- Python 3.10+
- Node.js 16+ (for some build tools)
- Git
- SQLite (development) or PostgreSQL (production)
- Nginx (production)
- Docker (optional)

## Local Development Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd fhir-namaste-icd-mapping
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Linux/macOS
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Database

```bash
python init_project.py
```

### 5. Start Services

**Option 1: Start services separately**
```bash
# Terminal 1 - Backend
./start_backend.sh

# Terminal 2 - Frontend
./start_frontend.sh
```

**Option 2: Start both services**
```bash
./start_services.sh
```

### 6. Access Application

- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Frontend GUI: http://localhost:8501

## Production Deployment

### Option 1: Traditional Server Deployment

#### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip nginx postgresql postgresql-contrib git

# Create application user
sudo adduser fhir-app
sudo usermod -aG sudo fhir-app
```

#### 2. Database Setup (PostgreSQL)

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE fhir_mapping;
CREATE USER fhir_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE fhir_mapping TO fhir_user;
\q
```

#### 3. Application Deployment

```bash
# Switch to application user
sudo su - fhir-app

# Clone repository
git clone <repository-url> /opt/fhir-mapping
cd /opt/fhir-mapping

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Create production environment file
cp .env.example .env
nano .env
```

#### 4. Environment Configuration

Update `.env` file for production:

```bash
# Application Configuration
APP_NAME="FHIR NAMASTE-ICD Mapping Service"
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql://fhir_user:secure_password_here@localhost/fhir_mapping
DATABASE_ECHO=false

# Security
SECRET_KEY=your-very-secure-secret-key-generate-new-one
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Production settings
ENABLE_AUDIT_LOGGING=true
LOG_LEVEL=INFO
```

#### 5. Initialize Production Database

```bash
python init_project.py
```

#### 6. Create Systemd Services

**Backend Service** (`/etc/systemd/system/fhir-backend.service`):
```ini
[Unit]
Description=FHIR NAMASTE-ICD Mapping Backend
After=network.target

[Service]
Type=exec
User=fhir-app
Group=fhir-app
WorkingDirectory=/opt/fhir-mapping
Environment=PATH=/opt/fhir-mapping/venv/bin
EnvironmentFile=/opt/fhir-mapping/.env
ExecStart=/opt/fhir-mapping/venv/bin/gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Frontend Service** (`/etc/systemd/system/fhir-frontend.service`):
```ini
[Unit]
Description=FHIR NAMASTE-ICD Mapping Frontend
After=network.target

[Service]
Type=exec
User=fhir-app
Group=fhir-app
WorkingDirectory=/opt/fhir-mapping
Environment=PATH=/opt/fhir-mapping/venv/bin
EnvironmentFile=/opt/fhir-mapping/.env
ExecStart=/opt/fhir-mapping/venv/bin/streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 7. Enable and Start Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable fhir-backend fhir-frontend
sudo systemctl start fhir-backend fhir-frontend
sudo systemctl status fhir-backend fhir-frontend
```

#### 8. Configure Nginx

**Nginx Configuration** (`/etc/nginx/sites-available/fhir-mapping`):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Frontend
    location / {
        proxy_pass http://localhost:8501/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket support for Streamlit
    location /_stcore/stream {
        proxy_pass http://localhost:8501/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Static files
    location /static/ {
        alias /opt/fhir-mapping/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

**Enable Site:**
```bash
sudo ln -s /etc/nginx/sites-available/fhir-mapping /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 9. SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Option 2: Docker Deployment

#### 1. Create Dockerfile

**Backend Dockerfile** (`Dockerfile.backend`):
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY init_project.py .
COPY .env .

# Create data directory
RUN mkdir -p data

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile** (`Dockerfile.frontend`):
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY frontend/ ./frontend/
COPY .env .

# Expose port
EXPOSE 8501

# Run application
CMD ["streamlit", "run", "frontend/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

#### 2. Docker Compose

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: fhir_mapping
      POSTGRES_USER: fhir_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - fhir-network

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://fhir_user:secure_password@db:5432/fhir_mapping
    depends_on:
      - db
    networks:
      - fhir-network
    volumes:
      - ./data:/app/data

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "8501:8501"
    depends_on:
      - backend
    networks:
      - fhir-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
    depends_on:
      - backend
      - frontend
    networks:
      - fhir-network

volumes:
  postgres_data:

networks:
  fhir-network:
    driver: bridge
```

#### 3. Deploy with Docker

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale backend if needed
docker-compose up -d --scale backend=3
```

### Option 3: Kubernetes Deployment

#### 1. Create Kubernetes Manifests

**Namespace** (`k8s/namespace.yaml`):
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: fhir-mapping
```

**ConfigMap** (`k8s/configmap.yaml`):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fhir-config
  namespace: fhir-mapping
data:
  APP_NAME: "FHIR NAMASTE-ICD Mapping Service"
  DEBUG: "false"
  HOST: "0.0.0.0"
  PORT: "8000"
```

**Secret** (`k8s/secret.yaml`):
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: fhir-secrets
  namespace: fhir-mapping
type: Opaque
data:
  SECRET_KEY: <base64-encoded-secret>
  DATABASE_URL: <base64-encoded-database-url>
```

**Backend Deployment** (`k8s/backend-deployment.yaml`):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fhir-backend
  namespace: fhir-mapping
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fhir-backend
  template:
    metadata:
      labels:
        app: fhir-backend
    spec:
      containers:
      - name: backend
        image: fhir-mapping/backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: fhir-config
        - secretRef:
            name: fhir-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

**Service** (`k8s/service.yaml`):
```yaml
apiVersion: v1
kind: Service
metadata:
  name: fhir-backend-service
  namespace: fhir-mapping
spec:
  selector:
    app: fhir-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

#### 2. Deploy to Kubernetes

```bash
kubectl apply -f k8s/
kubectl get pods -n fhir-mapping
kubectl logs -f deployment/fhir-backend -n fhir-mapping
```

## Monitoring and Maintenance

### 1. Health Checks

```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend (manual browser test)
curl http://localhost:8501
```

### 2. Log Management

**Systemd Logs:**
```bash
sudo journalctl -u fhir-backend -f
sudo journalctl -u fhir-frontend -f
```

**Docker Logs:**
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 3. Database Maintenance

**PostgreSQL Backup:**
```bash
pg_dump -U fhir_user -h localhost fhir_mapping > backup_$(date +%Y%m%d_%H%M%S).sql
```

**SQLite Backup:**
```bash
cp data/fhir_mapping.db data/fhir_mapping_backup_$(date +%Y%m%d_%H%M%S).db
```

### 4. Updates and Patches

```bash
# Stop services
sudo systemctl stop fhir-backend fhir-frontend

# Update code
cd /opt/fhir-mapping
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations if needed
python init_project.py

# Start services
sudo systemctl start fhir-backend fhir-frontend
```

## Security Considerations

### 1. Environment Security

- Use strong passwords for database accounts
- Generate secure random SECRET_KEY
- Enable firewall and limit port access
- Keep system and dependencies updated
- Use HTTPS in production (SSL certificates)
- Implement rate limiting
- Regular security audits

### 2. Database Security

```sql
-- Create read-only user for analytics
CREATE USER analytics_user WITH PASSWORD 'analytics_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_user;
```

### 3. Application Security

- Implement proper input validation
- Use parameterized queries
- Enable CSRF protection
- Implement proper session management
- Regular dependency updates
- Security headers in Nginx

## Performance Optimization

### 1. Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_terminology_codes_system ON terminology_codes(system);
CREATE INDEX idx_terminology_codes_code ON terminology_codes(code);
CREATE INDEX idx_code_mappings_source ON code_mappings(source_code_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
```

### 2. Caching

- Enable Redis for caching (optional)
- Configure Nginx caching for static files
- Implement application-level caching

### 3. Load Balancing

**Nginx Load Balancing:**
```nginx
upstream backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    location /api/ {
        proxy_pass http://backend/;
    }
}
```

## Troubleshooting

### Common Issues

**1. Database Connection Error:**
```bash
# Check database status
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT version();"

# Check connection
python -c "
import os
from sqlalchemy import create_engine
engine = create_engine(os.getenv('DATABASE_URL'))
print('Database connection successful')
"
```

**2. Port Already in Use:**
```bash
# Find process using port
sudo lsof -i :8000
sudo lsof -i :8501

# Kill process if necessary
sudo kill -9 <PID>
```

**3. Permission Issues:**
```bash
# Fix file permissions
sudo chown -R fhir-app:fhir-app /opt/fhir-mapping
chmod +x start_*.sh
```

**4. Memory Issues:**
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Increase swap if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Log Analysis

**Common Log Locations:**
- Systemd: `sudo journalctl -u fhir-backend`
- Nginx: `/var/log/nginx/access.log` and `/var/log/nginx/error.log`
- Application: Check LOG_LEVEL in environment

## Backup and Recovery

### 1. Automated Backup Script

**backup.sh**:
```bash
#!/bin/bash

BACKUP_DIR="/opt/backups/fhir-mapping"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U fhir_user fhir_mapping > $BACKUP_DIR/db_backup_$DATE.sql

# Application files backup
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz -C /opt fhir-mapping

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### 2. Crontab Entry

```bash
# Add to crontab
sudo crontab -e

# Daily backup at 2 AM
0 2 * * * /opt/fhir-mapping/backup.sh
```

### 3. Recovery Procedure

```bash
# Stop services
sudo systemctl stop fhir-backend fhir-frontend

# Restore database
psql -U fhir_user -d fhir_mapping < /opt/backups/fhir-mapping/db_backup_YYYYMMDD_HHMMSS.sql

# Restore application (if needed)
cd /opt
sudo tar -xzf /opt/backups/fhir-mapping/app_backup_YYYYMMDD_HHMMSS.tar.gz

# Start services
sudo systemctl start fhir-backend fhir-frontend
```

## Scaling Considerations

### Horizontal Scaling

- Multiple backend instances behind load balancer
- Shared database (PostgreSQL with connection pooling)
- Redis for shared caching
- CDN for static assets

### Vertical Scaling

- Increase server resources (CPU, RAM)
- Optimize database queries
- Enable database query caching
- Use faster storage (SSD)

This deployment guide provides comprehensive instructions for setting up the FHIR NAMASTE-ICD Mapping Service in production environments. Choose the deployment method that best fits your infrastructure requirements and operational capabilities.
