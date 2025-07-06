import pytest
from unittest.mock import MagicMock, patch
from fastapi import BackgroundTasks, Request, HTTPException
from bson import ObjectId

from app.api.v1.endpoints.logs import (
    get_logs,
    get_log,
    produce_log,
    produce_logs_bulk,
    bulk_index_logs,
    delete_old_logs
)
from app.models.log import Log, LogCreate, LogBulkCreate, LogQueryParams
from app.models.token import TokenData
from app.services.opensearch_service import OpenSearchService
from app.services.sqs_service import SQSService

class TestLogsEndpoints:
    @pytest.mark.asyncio
    @patch('app.api.v1.endpoints.logs.create_audit_log_task')
    async def test_get_logs_opensearch(self, mock_audit, mock_opensearch_service):
        # Configure OpenSearch service mock
        mock_opensearch_service.search_logs.return_value = {
            "data": [{"id": "test-log-id", "message": "Test log"}],
            "meta": {
                "pagination": {
                    "total": 1,
                    "page": 1,
                    "size": 10
                }
            }
        }
        
        # Create query parameters
        query_params = LogQueryParams(
            action="CREATE",
            resource_type="user",
            limit=10,
            skip=0
        )
        
        # Create token data
        token_data = TokenData(tenant_ids=["test-tenant"], roles=["reader"])
        
        # Call the endpoint
        response = await get_logs(
            query_params=query_params,
            opensearch_service=mock_opensearch_service,
            token_data=token_data,
            tenant_id="test-tenant",
            _=True,
            request=None,
            background_tasks=BackgroundTasks()
        )
        
        # Assertions
        assert mock_opensearch_service.search_logs.called
        assert mock_opensearch_service.search_logs.call_args[0][0] == "test-tenant"
        assert response.data[0]["id"] == "test-log-id"
        assert response.meta["pagination"]["total"] == 1
    
    @pytest.mark.asyncio
    @patch('app.api.v1.endpoints.logs.create_audit_log_task')
    async def test_get_log_valid_id(self, mock_audit, mock_opensearch_service):
        # Configure OpenSearch service mock
        mock_opensearch_service.get_log_by_id.return_value = {
            "id": "507f1f77bcf86cd799439011",
            "message": "Test log",
            "tenant_id": "test-tenant"
        }
        
        # Create token data
        token_data = TokenData(tenant_ids=["test-tenant"], roles=["reader"])
        
        # Call the endpoint
        response = await get_log(
            log_id="507f1f77bcf86cd799439011",
            opensearch_service=mock_opensearch_service,
            token_data=token_data,
            tenant_id="test-tenant",
            _=True
        )
        
        # Assertions
        assert mock_opensearch_service.get_log_by_id.called
        assert response.data["id"] == "507f1f77bcf86cd799439011"
        assert response.data["tenant_id"] == "test-tenant"
    
    @pytest.mark.asyncio
    async def test_get_log_invalid_id(self, mock_opensearch_service):
        # Create token data
        token_data = TokenData(tenant_ids=["test-tenant"], roles=["reader"])
        
        # Test with invalid ObjectId
        with pytest.raises(HTTPException) as excinfo:
            await get_log(
                log_id="invalid-id",
                opensearch_service=mock_opensearch_service,
                token_data=token_data,
                tenant_id="test-tenant",
                _=True
            )
        
        assert excinfo.value.status_code == 400
        assert "Invalid log ID" in excinfo.value.detail
    
    @pytest.mark.asyncio
    @patch('app.api.v1.endpoints.logs.broadcast_log')
    async def test_produce_log(self, mock_broadcast, mock_sqs_service):
        # Create log data
        log = LogCreate(
            action="CREATE",
            resource_type="user",
            resource_id="user123",
            message="User created"
        )
        
        # Create token data
        token_data = TokenData(tenant_ids=["test-tenant"], roles=["writer"])
        
        # Configure SQS mock
        mock_sqs_service.send_message.return_value = {"MessageId": "test-message-id"}
        
        # Call the endpoint
        response = await produce_log(
            log=log,
            sqs_service=mock_sqs_service,
            token_data=token_data,
            tenant_id="test-tenant",
            _=True
        )
        
        # Assertions
        assert mock_sqs_service.send_message.called
        assert mock_broadcast.called
        assert response.data["message_id"] == "test-message-id"
        assert response.data["status"] == "queued"
        
        # Check tenant isolation
        sent_message = mock_sqs_service.send_message.call_args[0][0]
        assert sent_message["tenant_id"] == "test-tenant"
    
    @pytest.mark.asyncio
    @patch('app.api.v1.endpoints.logs.broadcast_log')
    async def test_produce_logs_bulk(self, mock_broadcast, mock_sqs_service):
        # Create bulk log data
        logs_data = LogBulkCreate(logs=[
            LogCreate(
                action="CREATE",
                resource_type="user",
                resource_id="user1",
                message="User 1 created"
            ),
            LogCreate(
                action="CREATE",
                resource_type="user",
                resource_id="user2",
                message="User 2 created"
            )
        ])
        
        # Create token data
        token_data = TokenData(tenant_ids=["test-tenant"], roles=["writer"])
        
        # Configure SQS mock
        mock_sqs_service.send_message.return_value = {"MessageId": "test-message-id"}
        
        # Call the endpoint
        response = await produce_logs_bulk(
            logs_data=logs_data,
            sqs_service=mock_sqs_service,
            token_data=token_data,
            tenant_id="test-tenant",
            _=True
        )
        
        # Assertions
        assert mock_sqs_service.send_message.call_count == 2
        assert mock_broadcast.call_count == 2
        assert response.data["count"] == 2
        assert response.data["status"] == "queued"
    
    @pytest.mark.asyncio
    async def test_bulk_index_logs(self, mock_logs_collection, mock_opensearch_service):
        # Mock collection find
        mock_logs_collection.find.return_value.limit.return_value = [
            {"_id": ObjectId("507f1f77bcf86cd799439011"), "message": "Test log 1", "tenant_id": "test-tenant"},
            {"_id": ObjectId("507f1f77bcf86cd799439012"), "message": "Test log 2", "tenant_id": "test-tenant"}
        ]
        
        # Create token data
        token_data = TokenData(tenant_ids=["test-tenant"], roles=["admin"])
        
        # Call the endpoint
        response = await bulk_index_logs(
            start_time=None,
            end_time=None,
            limit=100,
            opensearch_service=mock_opensearch_service,
            token_data=token_data,
            tenant_id="test-tenant",
            _=True
        )
        
        # Assertions
        assert mock_logs_collection.find.called
        assert mock_opensearch_service.index_log.call_count == 2
        assert response.data["indexed"] == 2
    
    @pytest.mark.asyncio
    async def test_delete_old_logs(self, mock_logs_collection, mock_opensearch_service):
        # Mock collection delete_many
        mock_logs_collection.delete_many.return_value.deleted_count = 5
        
        # Mock OpenSearch delete
        mock_opensearch_service.delete_old_logs.return_value = 5
        
        # Create token data
        token_data = TokenData(tenant_ids=["test-tenant"], roles=["writer"])
        
        # Call the endpoint
        response = await delete_old_logs(
            days=30,
            opensearch_service=mock_opensearch_service,
            collection=mock_logs_collection,
            token_data=token_data,
            tenant_id="test-tenant",
            _=True
        )
        
        # Assertions
        assert mock_logs_collection.delete_many.called
        assert mock_opensearch_service.delete_old_logs.called
        assert response.data["deleted_count"] == 5
        assert response.data["opensearch_deleted"] == 5 