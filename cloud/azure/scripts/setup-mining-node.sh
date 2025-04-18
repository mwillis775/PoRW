#!/bin/bash

# Get blockchain node IP from parameter
BLOCKCHAIN_NODE_IP=$1

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
mkdir -p /data/porw-mining
mkdir -p /data/porw-mining/protein_data

# Create docker-compose.yml
cat > /data/porw-mining/docker-compose.yml << EOF
version: '3'
services:
  porw-mining-node:
    image: porwblockchain/porw-mining-node:latest
    container_name: porw-mining-node
    ports:
      - "3000:3000"
    volumes:
      - porw-mining-data:/data
      - porw-protein-data:/data/protein_data
    restart: unless-stopped
    environment:
      - NODE_HOST=0.0.0.0
      - P2P_PORT=3000
      - ENABLE_MINING=true
      - MINING_THREADS=4
      - ENABLE_GPU=true
      - BOOTSTRAP_NODE=${BLOCKCHAIN_NODE_IP}:8333

volumes:
  porw-mining-data:
  porw-protein-data:
EOF

# Start the mining node
cd /data/porw-mining
docker-compose up -d
