# PoRW Blockchain Kubernetes Deployment

This directory contains Kubernetes configuration files for deploying the PoRW blockchain system.

## Components

- **porw-node**: The main blockchain node that maintains the blockchain state
- **porw-mining-node**: A node dedicated to protein folding mining
- **porw-storage-node**: A node dedicated to storing blockchain data
- **porw-web-interface**: The web interface for interacting with the blockchain

## Prerequisites

- Kubernetes cluster (e.g., minikube, GKE, EKS, AKS)
- kubectl command-line tool
- Docker images for the PoRW blockchain components

## Deployment

1. Create the namespace:

```bash
kubectl create namespace porw-blockchain
```

2. Deploy the entire system using kustomize:

```bash
kubectl apply -k .
```

Alternatively, deploy individual components:

```bash
kubectl apply -f deployment.yaml -n porw-blockchain
kubectl apply -f mining-node.yaml -n porw-blockchain
kubectl apply -f storage-node.yaml -n porw-blockchain
kubectl apply -f web-interface.yaml -n porw-blockchain
```

## Accessing the Web Interface

The web interface is exposed as a LoadBalancer service. Get the external IP:

```bash
kubectl get svc porw-web-interface-service -n porw-blockchain
```

Then access the web interface at `http://<EXTERNAL-IP>`.

## Scaling

To scale the number of mining or storage nodes:

```bash
kubectl scale deployment porw-mining-node --replicas=3 -n porw-blockchain
kubectl scale deployment porw-storage-node --replicas=5 -n porw-blockchain
```

## Monitoring

You can monitor the pods using:

```bash
kubectl get pods -n porw-blockchain
kubectl logs -f <pod-name> -n porw-blockchain
```

## Cleanup

To remove all resources:

```bash
kubectl delete namespace porw-blockchain
```
