# PoRW Blockchain Azure Deployment

This directory contains Azure Resource Manager (ARM) templates for deploying the PoRW blockchain system on Microsoft Azure.

## Architecture

The ARM template deploys the following resources:

- Virtual Network and Subnet
- Network Security Group with required firewall rules
- Virtual Machines for blockchain node, mining node, and storage node
- Managed Disk for the storage node
- Custom Script Extensions to install Docker and configure the nodes

## Prerequisites

- Microsoft Azure account
- Azure CLI installed and configured
- SSH key pair for authentication (recommended)

## Deployment

1. Create a resource group:

```bash
az group create --name porw-blockchain-rg --location eastus
```

2. Deploy the ARM template:

```bash
az deployment group create \
  --resource-group porw-blockchain-rg \
  --template-file arm-template.json \
  --parameters \
    environmentName=dev \
    adminUsername=azureuser \
    adminPasswordOrKey="$(cat ~/.ssh/id_rsa.pub)" \
    authenticationType=sshPublicKey \
    blockchainNodeVmSize=Standard_D2s_v3 \
    miningNodeVmSize=Standard_F8s_v2 \
    storageNodeVmSize=Standard_D4s_v3 \
    storageDiskSizeGB=100
```

3. Monitor the deployment:

```bash
az deployment group show \
  --resource-group porw-blockchain-rg \
  --name arm-template \
  --query properties.outputs
```

## Accessing the Web Interface

Use the `webInterfaceURL` from the deployment outputs to access the web interface.

## SSH Access

You can SSH into the virtual machines using the key pair you specified:

```bash
ssh azureuser@<vm-fqdn>
```

## Cleanup

To delete all resources:

```bash
az group delete --name porw-blockchain-rg --yes
```
