#!/bin/bash

# Update and install dependencies
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create data directory
mkdir -p /data/porw

# Create docker-compose.yml
cat > /data/porw/docker-compose.yml << 'EOF'
version: '3'
services:
  porw-node:
    image: porwblockchain/porw-node:latest
    container_name: porw-node
    ports:
      - "8333:8333"
      - "8080:8080"
    volumes:
      - porw-data:/data
    restart: unless-stopped
    command: start

volumes:
  porw-data:
EOF

# Start the blockchain node
cd /data/porw
docker-compose up -d
