# Implementation Plan for Audit Log API

## Technology Stack Selection

### Core Technologies:
- **Framework**: FastAPI
- **Database**: MongoDB
- **API Gateway**: AWS API Gateway
- **Message Queue**: AWS SQS
- **Search Engine**: OpenSearch
- **Authentication**: JWT with FastAPI security

### Justification:
1. **FastAPI**: 
   - High performance (built on Starlite)
   - Native async/await support for handling high throughput
   - Automatic OpenAPI documentation

2. **MongoDB**:
   - Flexible schema for varied log structures
   - Native support for JSON-like documents
   - Built-in time-series collections for efficient log storage
   - Strong indexing capabilities for search operations

3. **AWS API Gateway**:
   - Managed service with built-in rate limiting
   - Authentication integration
   - Scales automatically with traffic

## Project Structure

```
ocelot-log-service/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── logs.py
│   │   │   │   ├── tenants.py
│   │   │   │   └── stats.py
│   │   │   └── router.py
│   │   └── deps.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── events.py
│   ├── db/
│   │   ├── mongodb.py
│   │   └── opensearch.py
│   ├── models/
│   │   ├── log.py
│   │   ├── tenant.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── log.py
│   │   ├── tenant.py
│   │   └── user.py
│   ├── services/
│   │   ├── log_service.py
│   │   ├── search_service.py
│   │   ├── export_service.py
│   │   └── stream_service.py
│   └── workers/
│       ├── sqs_consumer.py
│       ├── archival_worker.py
│       ├── cleanup_worker.py
│       └── search_indexer.py
├── tests/
│   ├── api/
│   ├── services/
│   └── workers/
├── infrastructure/
│   ├── terraform/
│   ├── docker-compose.yml
│   └── Dockerfile
├── .env.example
├── main.py
├── requirements.txt
└── README.md
```

## Implementation Phases

### Phase 1: Core Infrastructure Setup (Day 1)

1. **Project Initialization**:
   - Set up FastAPI project structure
   - Configure MongoDB connection with motor (async driver)
   - Set up basic authentication with JWT
   - Configure environment variables

2. **Database Design**:
   - Create MongoDB collections with appropriate indexes
   - Design tenant isolation strategy (single collection with tenant IDs, cheap and simple, fits the use case)
   - Set up time-based partitioning for logs

3. **API Gateway Setup**:
   - Configure AWS API Gateway
   - Set up basic routes
   - Configure rate limiting

### Phase 2: Core API Development (Day 1-2)

1. **Log Entry Creation**:
   - Implement log creation endpoint
   - Add validation for log structure
   - Implement tenant isolation
   - Add bulk creation endpoint

2. **Log Retrieval**:
   - Implement basic search and filtering
   - Add pagination
   - Ensure tenant-scoped queries

3. **Authentication & Authorization**:
   - Implement JWT authentication
   - Add role-based access control
   - Implement tenant-based access control

### Phase 3: Advanced Features (Day 2-3)

1. **SQS Integration**:
   - Set up SQS queues for background processing
   - Implement SQS producer in log service
   - Create SQS consumer workers

2. **OpenSearch Integration**:
   - Configure OpenSearch with tenant indices
   - Implement search indexing worker
   - Add advanced search capabilities

3. **Real-time Streaming**:
   - Implement WebSocket endpoint
   - Add tenant-scoped streaming
   - Configure connection management

### Phase 4: Data Management (Day 3-4)

1. **Data Retention & Archival**:
   - Implement retention policy configuration
   - Create archival worker
   - Add cleanup worker

2. **Export Functionality**:
   - Implement JSON and CSV export
   - Add background processing for large exports
   - Configure tenant-scoped exports

### Phase 5: Testing & Documentation (Day 4-5)

1. **Testing**:
   - Write unit tests for core services
   - Add integration tests for API endpoints
   - Perform load testing

2. **Documentation**:
   - Complete API documentation with FastAPI's built-in Swagger
   - Create architecture diagrams
   - Write comprehensive README
   - Create Postman collection

## Detailed Technical Design

### MongoDB Schema Design

#### Tenant Collection
```
{
    "_id": ObjectId,
    "tenant_id": str,  # Unique identifier
    "name": str,
    "created_at": datetime,
    "settings": {
        "retention_days": int,
        "log_levels": list[str]
    },
    "api_keys": list[str]  # Hashed API keys
}
```

#### Log Collection (per tenant)
```
{
    "_id": ObjectId,
    "user_id": str,
    "session_id": str,
    "action": str,  # CREATE, UPDATE, DELETE, VIEW
    "resource_type": str,  # user, order, product
    "resource_id": str,
    "timestamp": datetime,
    "ip_address": str,
    "user_agent": str,
    "before_state": dict,  # For modifications
    "after_state": dict,   # For modifications
    "metadata": dict,      # Custom fields
    "severity": str,       # INFO, WARNING, ERROR, CRITICAL
    "message": str,        # Log message
    "request_id": str      # For correlation
}
```

### Indexing Strategy

For each tenant's log collection:
- `timestamp` index (for time-based queries and TTL)
- `user_id` index (for user-based filtering)
- Compound index on `action` + `resource_type` (for common filtering)
- `severity` index (for filtering by severity)
- `resource_id` index (for resource-specific queries)
- Text index on `message` field (for full-text search)
- TTL index on `timestamp` for automatic data expiration

### API Endpoints Implementation

#### Log Management
- `POST /api/v1/logs`: Create a single log entry
- `POST /api/v1/logs/bulk`: Bulk create multiple log entries
- `GET /api/v1/logs`: Search/filter logs with pagination
- `GET /api/v1/logs/{id}`: Retrieve a specific log entry
- `GET /api/v1/logs/export`: Export logs to JSON/CSV
- `GET /api/v1/logs/stats`: Get statistics about logs
- `DELETE /api/v1/logs/cleanup`: Trigger cleanup of old logs
- `WS /api/v1/logs/stream`: WebSocket for real-time log streaming

#### Tenant Management
- `GET /api/v1/tenants`: List accessible tenants
- `POST /api/v1/tenants`: Create a new tenant
- `GET /api/v1/tenants/{id}`: Get tenant details
- `PUT /api/v1/tenants/{id}`: Update tenant settings
- `DELETE /api/v1/tenants/{id}`: Delete a tenant

### Multi-tenant Implementation

1. **API Level**:
   - JWT tokens include tenant access information
   - Required tenant header for all requests
   - Middleware validates tenant access for each request

2. **Database Level**:
   - All tenants share 1 collection with separate tenant id
   - Tenant-specific indexes and TTL settings
   - Tenant collection for managing tenant metadata

3. **Search Level**:
   - Separate OpenSearch index per tenant
   - Tenant-specific mapping and settings

4. **Message Queue Level**:
   - Tenant ID included in all messages
   - Workers process messages based on tenant context
   - Separate queues for high-volume tenants if needed

### Security Implementation

1. **Authentication**:
   - JWT-based authentication
   - Token validation middleware
   - Role-based access control

2. **Authorization**:
   - Tenant-based access control
   - Fine-grained permissions (Admin, Auditor, User)
   - Resource-level permissions

3. **Data Protection**:
   - Field-level encryption for sensitive data
   - Data masking for PII and sensitive information
   - HTTPS for all API endpoints
   - AWS KMS for encryption key management

4. **Tenant Isolation**:
   - Complete data isolation between tenants
   - Validation of tenant access on all requests
   - Separate database collections and search indices

### Performance Optimization

1. **Database Optimization**:
   - Strategic indexing for common query patterns
   - Time-based partitioning for large datasets
   - Connection pooling for efficient resource usage
   - Read preference configuration for replica sets

2. **API Optimization**:
   - Async processing for non-critical operations
   - Background tasks for long-running operations
   - Pagination for large result sets
   - Response compression

3. **Caching Strategy**:
   - In-memory caching for frequently accessed data
   - Redis for distributed caching if needed
   - Cache invalidation on data changes
   - Tenant-aware caching

4. **SQS Implementation**:
   - Batch processing for high-volume operations
   - Dead letter queues for failed messages
   - Message deduplication
   - Retry policies for transient failures

## AWS Infrastructure Setup

### AWS Resources

1. **API Gateway**:
   - REST API with custom domain
   - API key management
   - Usage plans for rate limiting
   - Request validation
   - CORS configuration

2. **SQS Queues**:
   - Main processing queue
   - Dead letter queue
   - High-priority queue (optional)
   - Archival queue

3. **OpenSearch Domain**:
   - Appropriate instance types based on volume
   - EBS storage with encryption
   - VPC access control
   - Fine-grained access control

4. **Security**:
   - IAM roles with least privilege
   - VPC for network isolation
   - Security groups for access control
   - AWS Secrets Manager for sensitive configuration

### Deployment Strategy

1. **Infrastructure as Code**:
   - Terraform for AWS resource provisioning
   - CloudFormation for AWS-specific resources
   - Environment-specific configurations

2. **CI/CD Pipeline**:
   - GitHub Actions for automated testing
   - AWS CodePipeline for deployment
   - Blue/green deployment for zero downtime

3. **Monitoring & Logging**:
   - CloudWatch for metrics and alarms
   - X-Ray for distributed tracing
   - Centralized logging with CloudWatch Logs
   - Custom dashboards for system health

## Testing Strategy

1. **Unit Testing**:
   - Test individual components in isolation
   - Mock external dependencies
   - >85% code coverage

2. **Integration Testing**:
   - Test API endpoints with real database
   - Test SQS integration
   - Test OpenSearch integration

3. **Performance Testing**:
   - Load testing with realistic data volumes
   - Benchmark database queries
   - Test throughput and latency under load

4. **Security Testing**:
   - Authentication and authorization testing
   - Input validation testing
   - Penetration testing

## Why This Implementation Plan Works

1. **Multi-tenant Architecture**:
   - MongoDB's flexible schema allows for efficient tenant isolation
   - Each tenant gets its own log collection for complete data separation
   - JWT tokens include tenant information for authorization

2. **High Performance**:
   - FastAPI's async support handles high throughput efficiently
   - MongoDB's indexing strategy optimizes common queries
   - Background processing with SQS reduces API response times
   - Connection pooling maximizes database efficiency

3. **Scalability**:
   - MongoDB can scale horizontally through sharding
   - SQS decouples log creation from processing
   - OpenSearch handles complex search operations

4. **Security**:
   - JWT authentication with role-based access
   - Tenant isolation at all levels (API, database, search)
   - Field-level encryption for sensitive data
   - Input validation with Pydantic models

This implementation plan addresses all the core requirements while leveraging the strengths of FastAPI and MongoDB. The multi-tenant design ensures complete data isolation, while the async architecture provides the performance needed to handle high log volumes. 