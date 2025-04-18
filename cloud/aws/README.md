# PoRW Blockchain AWS Deployment

This directory contains AWS CloudFormation templates for deploying the PoRW blockchain system on AWS.

## Architecture

The CloudFormation template deploys the following resources:

- VPC with public subnet, internet gateway, and route table
- Security groups for each node type
- EC2 instances for blockchain node, mining node, and storage node
- EBS volume for the storage node
- Docker and Docker Compose for running the containers

## Prerequisites

- AWS account
- AWS CLI installed and configured
- SSH key pair created in AWS

## Deployment

1. Deploy the CloudFormation stack:

```bash
aws cloudformation create-stack \
  --stack-name porw-blockchain \
  --template-body file://cloudformation.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=dev \
    ParameterKey=KeyName,ParameterValue=your-key-name \
    ParameterKey=InstanceType,ParameterValue=t3.medium \
    ParameterKey=MiningInstanceType,ParameterValue=c5.2xlarge \
    ParameterKey=StorageInstanceType,ParameterValue=m5.large \
    ParameterKey=StorageSize,ParameterValue=100 \
  --capabilities CAPABILITY_IAM
```

2. Monitor the stack creation:

```bash
aws cloudformation describe-stacks --stack-name porw-blockchain
```

3. Once the stack is created, get the outputs:

```bash
aws cloudformation describe-stacks --stack-name porw-blockchain --query "Stacks[0].Outputs"
```

## Accessing the Web Interface

Use the `WebInterfaceURL` from the stack outputs to access the web interface.

## SSH Access

You can SSH into the instances using the key pair you specified:

```bash
ssh -i your-key.pem ec2-user@<instance-public-ip>
```

## Cleanup

To delete all resources:

```bash
aws cloudformation delete-stack --stack-name porw-blockchain
```
