# Ocelot Log Service

A high-performance, multi-tenant audit log API service built with FastAPI and MongoDB.

## Features

- **High-performance** audit log creation and retrieval
- **Multi-tenant** architecture with complete data isolation
- **Flexible schema** for varied log structures
- **Advanced filtering** and search capabilities
- **Statistics** and aggregation endpoints
- **JWT authentication** with role-based access control

## Technology Stack

- **Framework**: FastAPI
- **Database**: MongoDB
- **API Gateway**: AWS API Gateway
- **Message Queue**: AWS SQS (planned)
- **Search Engine**: OpenSearch (planned)
- **Authentication**: JWT with FastAPI security

## Getting Started

### Prerequisites

- Python 3.8+
- MongoDB
- Docker and Docker Compose (optional)

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

3. Start the development server:
   ```bash
   make dev
   ```

### Docker Deployment

1. Build and run with Docker Compose:
   ```bash
   make docker-compose-up
   ```

2. To stop:
   ```bash
   make docker-compose-down
   ```

## API Documentation

Once the service is running, access the OpenAPI documentation at:
- http://localhost:8000/api/v1/docs

## Configuration

All configuration is done via environment variables. See `.env.example` for available options.

## Development

The project includes a Makefile with several useful commands:
- `make setup` - Set up the development environment
- `make dev` - Run the development server
- `make test` - Run tests
- `make lint` - Run linters
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
│   └── workers/          # Background workers
├── tests/                # Unit and integration tests
├── infrastructure/       # Infrastructure as code
├── main.py              # Application entry point
├── Dockerfile           # Docker configuration
├── requirements.txt     # Python dependencies
└── README.md
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 