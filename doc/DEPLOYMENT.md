# Ocelot Log Service Deployment Guide

This guide explains how to deploy the Ocelot Log Service to AWS ECS using different approaches.

## Architecture Overview

The Ocelot Log Service consists of two main components:

1. **API Service** - Handles HTTP requests and produces messages to SQS
2. **Consumer Service** - Consumes messages from SQS and processes them

These components are packaged into separate Docker images to allow independent scaling.

## Local Development

To build and run the services locally:

```bash
# Make the script executable
chmod +x build_and_run.sh

# Run both services
./build_and_run.sh

# Or run only the API service
./build_and_run.sh --api

# Or run only the consumer service
./build_and_run.sh --consumer

# Or just build the images without running them
./build_and_run.sh --build
```

You can also run the consumer service directly with Python:

```bash
# Make the script executable
chmod +x run_consumer.sh

# Run the consumer service
./run_consumer.sh
```

## AWS ECS Deployment Options

### Option 1: ECS with Fargate (Managed, Higher Cost)

To deploy using AWS Fargate (fully managed, no EC2 instances to manage):

```bash
# Make the script executable
chmod +x deploy_to_ecs.sh

# Run the script
./deploy_to_ecs.sh
```

This will:
- Create an ECR repository
- Build and push Docker images to ECR
- Create an ECS cluster
- Register task definitions for Fargate
- Output the next steps

### Option 2: ECS with EC2 (Self-managed, Lower Cost)

To deploy using ECS with EC2 instances (more cost-effective):

```bash
# Make the script executable
chmod +x deploy_to_ecs_ec2.sh

# Run the script
./deploy_to_ecs_ec2.sh
```

This will:
- Create an ECR repository
- Build and push Docker images to ECR
- Create an ECS cluster for EC2 instances
- Register task definitions for EC2
- Output the next steps

After running the script, you'll need to:
1. Create an EC2 Launch Template or Auto Scaling Group with the ECS-optimized AMI
2. Configure the EC2 instances to join your ECS cluster
3. Create ECS services using the AWS Console or CLI

### Cost-Saving Tips

1. **Use EC2 Spot Instances** - For the consumer service, consider using Spot Instances to reduce costs by up to 90%
2. **Right-size instances** - Start with smaller instances and scale up as needed
3. **Auto Scaling** - Configure auto-scaling based on SQS queue depth for the consumer service
4. **Reserved Instances** - For stable workloads, consider reserved instances for the API service

## Required AWS Resources

1. **ECR Repository** - For storing Docker images
2. **ECS Cluster** - For running containers
3. **SQS Queue** - For message passing between services
4. **IAM Roles** - For ECS task execution and service permissions
5. **CloudWatch Logs** - For logging
6. **Load Balancer** (optional) - For distributing traffic to the API service

## Required IAM Permissions

The IAM user or role used for deployment needs these permissions:

- ECR: CreateRepository, GetAuthorizationToken, BatchCheckLayerAvailability, BatchGetImage, CompleteLayerUpload, InitiateLayerUpload, PutImage, UploadLayerPart
- ECS: CreateCluster, RegisterTaskDefinition, CreateService, DescribeClusters, DescribeServices
- IAM: PassRole
- CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents
- EC2: DescribeSubnets, DescribeSecurityGroups (for networking configuration)

## Monitoring and Maintenance

After deployment:

1. Set up CloudWatch alarms for:
   - API service health
   - Consumer service health
   - SQS queue depth
   - Error rates

2. Configure log retention policies in CloudWatch Logs

3. Set up a CI/CD pipeline for automated deployments

## Scaling Recommendations

### API Service
- Scale based on CPU/Memory utilization
- Consider using Application Auto Scaling with target tracking policies

### Consumer Service
- Scale based on SQS queue depth
- Use CloudWatch alarms to trigger scaling actions when queue depth exceeds thresholds
- Consider implementing a custom metric for message processing lag