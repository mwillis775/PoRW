# PoRW Blockchain Cloud Deployment Templates

This directory contains cloud deployment templates for deploying the PoRW blockchain system on various cloud platforms.

## Supported Cloud Platforms

- [AWS](aws/): Amazon Web Services CloudFormation templates
- [GCP](gcp/): Google Cloud Platform Deployment Manager templates
- [Azure](azure/): Microsoft Azure Resource Manager (ARM) templates

## Architecture

Each cloud deployment template creates the following resources:

1. **Blockchain Node**: The main blockchain node that maintains the blockchain state and provides the web interface
2. **Mining Node**: A node dedicated to protein folding mining
3. **Storage Node**: A node dedicated to storing blockchain data
4. **Networking**: VPC/VNet, subnets, security groups, and other networking resources
5. **Storage**: Persistent storage for the blockchain data and protein folding results

## Prerequisites

- Account on the cloud platform of your choice
- Command-line tools for the respective cloud platform
- Docker images for the PoRW blockchain components

## General Deployment Steps

1. Choose the cloud platform you want to use
2. Navigate to the corresponding directory
3. Follow the instructions in the README.md file for that platform

## Docker Images

The deployment templates assume the following Docker images are available:

- `porwblockchain/porw-node:latest`: The main blockchain node
- `porwblockchain/porw-mining-node:latest`: The mining node
- `porwblockchain/porw-storage-node:latest`: The storage node
- `porwblockchain/porw-web-interface:latest`: The web interface (used in Kubernetes deployment)

## Customization

Each deployment template can be customized to meet your specific requirements:

- Instance/VM types and sizes
- Storage capacity
- Network configuration
- Number of nodes

Refer to the README.md file in each cloud platform directory for specific customization options.
