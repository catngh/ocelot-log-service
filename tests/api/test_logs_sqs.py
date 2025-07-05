import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from app.models.log import LogAction, LogSeverity
from app.models.token import TokenData, UserRole

client = TestClient(app)

# Mock token data for testing
@pytest.fixture
def mock_token_data():
    return TokenData(
        tenant_ids=["test-tenant"],
        roles=[UserRole.WRITER]
    )

# Mock dependencies
@pytest.fixture
def mock_deps(monkeypatch, mock_token_data):
    # Mock get_current_token dependency
    async def mock_get_current_token():
        return mock_token_data
    
    # Mock get_tenant_id dependency
    async def mock_get_tenant_id():
        return "test-tenant"
    
    # Mock require_writer dependency
    async def mock_require_writer():
        return True
    
    # Mock SQS service
    mock_sqs = MagicMock()
    mock_sqs.send_message.return_value = {"MessageId": "test-message-id"}
    
    # Apply mocks
    with patch("app.api.deps.get_current_token", mock_get_current_token), \
         patch("app.api.deps.get_tenant_id", mock_get_tenant_id), \
         patch("app.api.deps.require_writer", mock_require_writer), \
         patch("app.services.sqs_service.get_sqs_service", return_value=mock_sqs):
        yield mock_sqs

def test_produce_log(mock_deps):
    """
    Test the /logs/produce endpoint.
    """
    # Test data
    log_data = {
        "action": LogAction.CREATE,
        "resource_type": "user",
        "resource_id": "user123",
        "message": "User created",
        "severity": LogSeverity.INFO
    }
    
    # Make request
    response = client.post(
        "/api/v1/logs/produce",
        json=log_data,
        headers={"X-Tenant-ID": "test-tenant"}
    )
    
    # Assertions
    assert response.status_code == 202
    assert "message_id" in response.json()["data"]
    assert response.json()["data"]["status"] == "queued"
    
    # Verify SQS service was called
    mock_deps.send_message.assert_called_once()
    # Extract the call arguments
    args, _ = mock_deps.send_message.call_args
    message = args[0]
    
    # Verify message content
    assert message["action"] == LogAction.CREATE
    assert message["resource_type"] == "user"
    assert message["resource_id"] == "user123"
    assert message["message"] == "User created"
    assert message["severity"] == LogSeverity.INFO
    assert "timestamp" in message
    assert message["tenant_id"] == "test-tenant"

def test_produce_logs_bulk(mock_deps):
    """
    Test the /logs/bulk/produce endpoint.
    """
    # Test data
    logs_data = {
        "logs": [
            {
                "action": LogAction.CREATE,
                "resource_type": "user",
                "resource_id": "user123",
                "message": "User created",
                "severity": LogSeverity.INFO
            },
            {
                "action": LogAction.UPDATE,
                "resource_type": "user",
                "resource_id": "user123",
                "message": "User updated",
                "severity": LogSeverity.INFO
            }
        ]
    }
    
    # Make request
    response = client.post(
        "/api/v1/logs/bulk/produce",
        json=logs_data,
        headers={"X-Tenant-ID": "test-tenant"}
    )
    
    # Assertions
    assert response.status_code == 202
    assert "message_ids" in response.json()["data"]
    assert response.json()["data"]["count"] == 2
    assert response.json()["data"]["status"] == "queued"
    
    # Verify SQS service was called twice
    assert mock_deps.send_message.call_count == 2 