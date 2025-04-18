#!/bin/bash

# Get blockchain node IP and storage size from parameters
BLOCKCHAIN_NODE_IP=$1
STORAGE_SIZE_GB=$2

# Update and install dependencies
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

# Format and mount the data disk
mkfs.ext4 /dev/sdc
mkdir -p /data/porw-storage/storage
mount /dev/sdc /data/porw-storage/storage
echo "/dev/sdc /data/porw-storage/storage ext4 defaults 0 2" >> /etc/fstab

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Calculate max storage in MB
MAX_STORAGE=$((STORAGE_SIZE_GB * 1024))

# Create docker-compose.yml
cat > /data/porw-storage/docker-compose.yml << EOF
version: '3'
services:
  porw-storage-node:
    image: porwblockchain/porw-storage-node:latest
    container_name: porw-storage-node
    ports:
      - "3500:3500"
    volumes:
      - /data/porw-storage/storage:/data/storage
    restart: unless-stopped
    environment:
      - NODE_HOST=${BLOCKCHAIN_NODE_IP}
      - NODE_PORT=8333
      - STORAGE_PORT=3500
      - MAX_STORAGE=${MAX_STORAGE}
      - MIN_REPLICATION=3
EOF

# Start the storage node
cd /data/porw-storage
docker-compose up -d
