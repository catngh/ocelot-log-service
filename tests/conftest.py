import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.collection import Collection
from pymongo.database import Database
from datetime import datetime, timedelta

from app.api.deps import get_db, get_logs_collection, get_tenant_collection
from app.models.token import TokenData, UserRole
from app.api.v1.router import api_router

# Create test app
@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    return app

@pytest.fixture
def client(app):
    return TestClient(app)

# Mock MongoDB database
@pytest.fixture
def mock_db():
    return MagicMock(spec=Database)

# Mock MongoDB collection
@pytest.fixture
def mock_logs_collection():
    collection = MagicMock(spec=Collection)
    return collection

@pytest.fixture
def mock_tenant_collection():
    collection = MagicMock(spec=Collection)
    return collection

# Mock MongoDB dependency
@pytest.fixture
def override_get_db(mock_db):
    def _override_get_db():
        return mock_db
    return _override_get_db

@pytest.fixture
def override_get_logs_collection(mock_logs_collection):
    def _override_get_logs_collection():
        return mock_logs_collection
    return _override_get_logs_collection

@pytest.fixture
def override_get_tenant_collection(mock_tenant_collection):
    def _override_get_tenant_collection():
        return mock_tenant_collection
    return _override_get_tenant_collection

# Mock token data
@pytest.fixture
def admin_token_data():
    return TokenData(
        tenant_ids=["test-tenant-1", "test-tenant-2"],
        roles=[UserRole.ADMIN]
    )

@pytest.fixture
def writer_token_data():
    return TokenData(
        tenant_ids=["test-tenant-1"],
        roles=[UserRole.WRITER]
    )

@pytest.fixture
def reader_token_data():
    return TokenData(
        tenant_ids=["test-tenant-1"],
        roles=[UserRole.READER]
    )

# Mock JWT token
@pytest.fixture
def valid_jwt_token():
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJ0ZW5hbnRfaWRzIjpbInRlc3QtdGVuYW50LTEiXSwicm9sZXMiOlsicmVhZGVyIl0sImp0aSI6InRlc3QtanRpIiwiZXhwIjoxNjkzNjU0NTgxfQ.signature"

# Mock SQS service
@pytest.fixture
def mock_sqs_service():
    mock_service = MagicMock()
    mock_service.send_message.return_value = {"MessageId": "test-message-id"}
    mock_service.receive_messages.return_value = []
    return mock_service

# Mock OpenSearch service
@pytest.fixture
def mock_opensearch_service():
    mock_service = MagicMock()
    return mock_service

# Sample log data
@pytest.fixture
def sample_log_data():
    return {
        "_id": "507f1f77bcf86cd799439011",
        "session_id": "session456",
        "action": "CREATE",
        "resource_type": "user",
        "resource_id": "user789",
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0...",
        "before_state": None,
        "after_state": {"name": "John Doe", "email": "john@example.com"},
        "metadata": {"source": "web"},
        "severity": "INFO",
        "message": "User created",
        "request_id": "req123",
        "timestamp": datetime.utcnow(),
        "tenant_id": "test-tenant-1"
    } 