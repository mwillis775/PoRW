# PoRW Blockchain GCP Deployment

This directory contains Google Cloud Platform (GCP) Deployment Manager templates for deploying the PoRW blockchain system on GCP.

## Architecture

The Deployment Manager template deploys the following resources:

- VPC network and subnet
- Firewall rules for the required ports
- Compute Engine instances for blockchain node, mining node, and storage node
- Persistent disk for the storage node
- Docker and Docker Compose for running the containers

## Prerequisites

- Google Cloud Platform account
- Google Cloud SDK (gcloud) installed and configured
- Project with billing enabled

## Deployment

1. Set your GCP project:

```bash
gcloud config set project YOUR_PROJECT_ID
```

2. Deploy the Deployment Manager configuration:

```bash
gcloud deployment-manager deployments create porw-blockchain --config deployment-manager.yaml
```

3. Monitor the deployment:

```bash
gcloud deployment-manager deployments describe porw-blockchain
```

4. Once the deployment is complete, get the outputs:

```bash
gcloud deployment-manager deployments describe porw-blockchain --format="yaml(outputs)"
```

## Accessing the Web Interface

Use the `web_interface_url` from the deployment outputs to access the web interface.

## SSH Access

You can SSH into the instances using the gcloud command:

```bash
gcloud compute ssh porw-blockchain-node --zone=us-central1-a
gcloud compute ssh porw-mining-node --zone=us-central1-a
gcloud compute ssh porw-storage-node --zone=us-central1-a
```

## Cleanup

To delete all resources:

```bash
gcloud deployment-manager deployments delete porw-blockchain
```
