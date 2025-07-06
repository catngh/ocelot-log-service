# Ocelot Log Service

A high-performance, multi-tenant audit log API service built with FastAPI and MongoDB.

## Features

- **High-performance** audit log creation and retrieval
- **Multi-tenant** architecture with complete data isolation
- **Flexible schema** for varied log structures
- **Advanced filtering** and search capabilities
- **Statistics** and aggregation endpoints
- **JWT authentication** with role-based access control
- **Asynchronous processing** with AWS SQS for high-throughput logging
- **Full-text search** with Amazon OpenSearch for powerful log querying

## Technology Stack

- **Framework**: FastAPI
- **Database**: MongoDB
- **Gateway**: AWS ALB
- **Message Queue**: AWS SQS
- **Search Engine**: Amazon OpenSearch
- **Authentication**: JWT with FastAPI security

## Getting Started

### Prerequisites

- Python 3.8+
- MongoDB
- AWS Account with SQS configured
- Amazon OpenSearch Service domain
- Docker

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ocelot-log-service.git
   cd ocelot-log-service
   ```

2. Set up the environment:
   ```bash
   make setup
   ```

3. Create a `.env` file with your configuration (see `.env.example`).

### Running in Development Mode

This codebase consists of two separate services that need to be run simultaneously:

1. **API Service** - Handles HTTP requests, queries, and WebSocket connections
2. **Consumer Service** - Processes messages from SQS asynchronously 

To run both services in development mode:

1. Start the API development server:
   ```bash
   make dev
   ```

2. In a separate terminal, start the Consumer service:
   ```bash
   make dev-consumer
   ```

### Docker Deployment

The project includes separate Docker images for both services:

1. Build the Docker images:
   ```bash
   # Build both images
   make docker-build-all
   
   # Or build them separately
   make docker-build-api
   make docker-build-consumer
   ```

2. Run the Docker containers:
   ```bash
   # Run the API service
   make docker-run-api
   
   # In a separate terminal, run the Consumer service
   make docker-run-consumer
   ```

## API Documentation

Once the service is running, access the OpenAPI documentation at:
- http://localhost:8000/api/v1/docs

### Log Creation Endpoints

- `POST /api/v1/logs` - Send a log entry to SQS for asynchronous processing
- `POST /api/v1/logs/bulk` - Send multiple log entries to SQS for asynchronous processing

### Log Search Endpoints

- `GET /api/v1/logs` - Search logs with OpenSearch
- `POST /api/v1/logs/index/bulk` - Bulk index logs in OpenSearch

## Configuration

All configuration is done via environment variables. See `.env.example` for available options.

### AWS SQS Configuration

To use the SQS producer/consumer functionality, you need to set up the following environment variables:

```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/ocelot-logs-queue
```

### OpenSearch Configuration

To enable the OpenSearch integration, set up the following environment variables:

```
# OpenSearch Configuration
OPENSEARCH_URL=https://your-opensearch-domain.us-east-1.es.amazonaws.com
```

## Development

The project includes a Makefile with several useful commands:
- `make setup` - Set up the development environment
- `make dev` - Run the API development server
- `make dev-consumer` - Run the Consumer service
- `make test` - Run tests
- `make lint` - Run linters
- `make docker-build-api` - Build the API service Docker image
- `make docker-build-consumer` - Build the Consumer service Docker image
- `make docker-build-all` - Build both Docker images
- `make docker-run-api` - Run the API service Docker container
- `make docker-run-consumer` - Run the Consumer service Docker container
- `make deploy` - Deploy to AWS (requires AWS CLI setup)

## Project Structure

```
ocelot-log-service/
├── app/                  # Application code
│   ├── api/              # API endpoints
│   ├── core/             # Core configuration
│   ├── db/               # Database connections
│   ├── models/           # Pydantic models
│   ├── schemas/          # Data schemas
│   ├── services/         # Business logic
│   │   ├── sqs_service.py       # SQS integration service
│   │   └── opensearch_service.py # OpenSearch integration service
│   └── workers/          # Background workers
│       └── sqs_consumer.py # SQS consumer worker
├── tests/                # Unit and integration tests
├── infrastructure/       # Infrastructure as code
├── scripts/              # Utility scripts
│   └── run_sqs_worker.py # Script to run the SQS worker
├── main.py              # Application entry point
├── Dockerfile           # Docker configuration
├── requirements.txt     # Python dependencies
└── README.md
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## CI/CD Pipeline

This project uses GitHub Actions for continuous integration and deployment:

### Workflow Overview

1. **Testing**: Runs all tests on every push and pull request
2. **Build**: On successful merge to main branch, builds Docker images for both API and Consumer services
3. **Push**: Pushes the images to Amazon ECR with both the commit SHA and latest tags
4. **Deploy**: Updates the ECS services with the new images using EC2 launch type

### Deployment Environments

This project uses GitHub Environments for environment-specific configuration:

- **Development**: Deployed from the `develop` branch
- **Production**: Deployed from the `main` branch 

Each environment can have its own configuration variables and secrets:

1. Go to your repository → Settings → Environments → "New environment"
2. Create environments for `development` and `production`
3. Add environment variables for each:

#### Required Environment Variables (Variables)
- `AWS_REGION`: The AWS region where resources are deployed
- `ECS_CLUSTER`: Name of the ECS cluster
- `ECS_SERVICE_API`: Name of the ECS service for API
- `ECS_SERVICE_CONSUMER`: Name of the ECS service for Consumer

### Required Repository Secrets

The following secrets need to be set at the repository level:

- `AWS_ACCESS_KEY_ID`: AWS access key with permissions for ECR and ECS
- `AWS_SECRET_ACCESS_KEY`: Corresponding secret key

### AWS Resources

The workflow assumes the following AWS resources exist:

- ECR repositories: `ocelot-log-api` and `ocelot-log-consumer`
- ECS cluster: `ocelot-cluster` with EC2 instances
- ECS services: `ocelot-log-api-service` and `ocelot-log-consumer-service`
- EC2 instances with appropriate IAM roles and capacity
- Parameter Store values for secrets (see task definitions)

### Customization

To customize the workflow, edit the following files:

- `.github/workflows/ci-cd.yml`: The main workflow file
- `.aws/task-definition-api.json`: ECS task definition for the API service
- `.aws/task-definition-consumer.json`: ECS task definition for the Consumer service

### EC2 Configuration

The task definitions are configured for the EC2 launch type with the following settings:

- Network mode: bridge
- Dynamic host port mapping
- Memory and CPU limits at the container level
- Placement constraints for availability zone distribution 

## Deployment Architecture

The Ocelot Log Service consists of two separate deployable components:

1. **API Service** (`Dockerfile.api`):
   - Serves HTTP endpoints and WebSocket connections
   - Handles authentication and tenant isolation
   - Queries MongoDB and OpenSearch for log retrieval
   - Sends log creation messages to SQS
   - Stateless and horizontally scalable

2. **Consumer Service** (`Dockerfile.consumer`):
   - Processes messages from SQS queue
   - Stores logs in MongoDB
   - Indexes logs in OpenSearch
   - Runs as a background service
   - Can be scaled independently from the API service

### Production Deployment

In production, both services should be deployed and scaled independently:

- **API Service**: Deploy behind a load balancer with auto-scaling
- **Consumer Service**: Deploy as a scalable background service with no public access needed

When deploying with AWS ECS:
1. Create a task definition for each service
2. Create a service for the API with a target group attached to an ALB
3. Create a service for the Consumer with no load balancer
4. Configure appropriate scaling policies for each service 