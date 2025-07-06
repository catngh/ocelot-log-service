import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from app.services.opensearch_service import OpenSearchService
from app.models.log import LogQueryParams

class TestOpenSearchService:
    
    @patch('app.services.opensearch_service.OpenSearch')
    @patch('app.services.opensearch_service.AWS4Auth')
    @patch('app.services.opensearch_service.boto3')
    def setup_service(self, mock_boto3, mock_aws4auth, mock_opensearch):
        # Setup boto3 mock
        mock_session = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.access_key = "test-access-key"
        mock_credentials.secret_key = "test-secret-key"
        mock_credentials.token = "test-token"
        mock_session.get_credentials.return_value = mock_credentials
        mock_boto3.Session.return_value = mock_session
        
        # Setup OpenSearch client mock
        mock_client = MagicMock()
        mock_client.info.return_value = {
            "cluster_name": "test-cluster",
            "version": {"number": "2.0.0"}
        }
        mock_opensearch.return_value = mock_client
        
        # Create service
        service = OpenSearchService()
        
        return service, mock_client
    
    def test_init(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Assertions
        assert service.client is mock_client
        assert mock_client.info.called
        assert service.index_name == "ocelot-log-index"
    
    def test_create_index_if_not_exists_new(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Configure mock
        mock_client.indices.exists.return_value = False
        mock_client.indices.create.return_value = {"acknowledged": True}
        
        # Call method
        result = service.create_index_if_not_exists()
        
        # Assertions
        assert result is True
        assert mock_client.indices.exists.called
        assert mock_client.indices.create.called
        
        # Check mapping
        create_args = mock_client.indices.create.call_args[1]
        assert "body" in create_args
        assert "mappings" in create_args["body"]
        assert "timestamp" in create_args["body"]["mappings"]["properties"]
        assert "tenant_id" in create_args["body"]["mappings"]["properties"]
    
    def test_create_index_if_not_exists_existing(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Configure mock
        mock_client.indices.exists.return_value = True
        
        # Call method
        result = service.create_index_if_not_exists()
        
        # Assertions
        assert result is False
        assert mock_client.indices.exists.called
        assert not mock_client.indices.create.called
    
    def test_index_log(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Mock index creation check
        service.create_index_if_not_exists = MagicMock(return_value=True)
        
        # Configure mock
        mock_client.index.return_value = {"_id": "test-id", "result": "created"}
        
        # Create test log
        log = {
            "_id": "test-id",
            "message": "Test log",
            "timestamp": datetime.utcnow(),
            "tenant_id": "test-tenant"
        }
        
        # Call method
        result = service.index_log(log)
        
        # Assertions
        assert service.create_index_if_not_exists.called
        assert mock_client.index.called
        assert result["_id"] == "test-id"
        assert result["result"] == "created"
        
        # Check index args
        index_args = mock_client.index.call_args[1]
        assert index_args["id"] == "test-id"
        assert index_args["refresh"] is True
        assert "_id" not in index_args["body"]  # _id should be removed
    
    def test_search_logs(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Configure mock
        mock_client.search.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_id": "log-1",
                        "_source": {"message": "Log 1", "tenant_id": "test-tenant"}
                    },
                    {
                        "_id": "log-2",
                        "_source": {"message": "Log 2", "tenant_id": "test-tenant"}
                    }
                ]
            }
        }
        
        # Create query params
        query_params = LogQueryParams(
            action="CREATE",
            resource_type="user",
            severity="INFO",
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow(),
            search="test query",
            limit=10,
            skip=0
        )
        
        # Call method
        result = service.search_logs("test-tenant", query_params)
        
        # Assertions
        assert mock_client.search.called
        assert len(result["data"]) == 2
        assert result["data"][0]["id"] == "log-1"
        assert result["data"][1]["id"] == "log-2"
        assert result["meta"]["pagination"]["total"] == 2
        
        # Check search query
        search_args = mock_client.search.call_args[1]
        assert "query" in search_args["body"]
        assert "bool" in search_args["body"]["query"]
        assert "must" in search_args["body"]["query"]["bool"]
        
        # Check tenant isolation
        must_clauses = search_args["body"]["query"]["bool"]["must"]
        tenant_clause = must_clauses[0]
        assert "term" in tenant_clause
        assert tenant_clause["term"]["tenant_id"] == "test-tenant"
    
    def test_get_log_by_id(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Configure mock
        mock_client.get.return_value = {
            "_id": "log-1",
            "_source": {"message": "Log 1", "tenant_id": "test-tenant"},
            "found": True
        }
        
        # Call method
        log = service.get_log_by_id("log-1", "test-tenant")
        
        # Assertions
        assert mock_client.get.called
        assert log["id"] == "log-1"
        assert log["message"] == "Log 1"
        assert log["tenant_id"] == "test-tenant"
        
        # Check get args
        get_args = mock_client.get.call_args[1]
        assert get_args["id"] == "log-1"
    
    def test_get_log_by_id_wrong_tenant(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Configure mock - return log from different tenant
        mock_client.get.return_value = {
            "_id": "log-1",
            "_source": {"message": "Log 1", "tenant_id": "wrong-tenant"},
            "found": True
        }
        
        # Call method with different tenant ID
        log = service.get_log_by_id("log-1", "test-tenant")
        
        # Assertions - should return None due to tenant isolation
        assert mock_client.get.called
        assert log is None
    
    def test_delete_log(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Configure mock
        mock_client.delete.return_value = {"result": "deleted"}
        
        # Call method
        result = service.delete_log("log-1")
        
        # Assertions
        assert mock_client.delete.called
        assert result is True
        
        # Check delete args
        delete_args = mock_client.delete.call_args[1]
        assert delete_args["id"] == "log-1"
        assert delete_args["refresh"] is True
    
    def test_delete_old_logs(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Configure mock
        mock_client.delete_by_query.return_value = {"deleted": 5}
        
        # Set cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Call method
        result = service.delete_old_logs("test-tenant", cutoff_date)
        
        # Assertions
        assert mock_client.delete_by_query.called
        assert result == 5
        
        # Check delete_by_query args
        delete_args = mock_client.delete_by_query.call_args[1]
        assert "query" in delete_args["body"]
        assert "bool" in delete_args["body"]["query"]
        assert "must" in delete_args["body"]["query"]["bool"]
        
        # Check tenant isolation
        must_clauses = delete_args["body"]["query"]["bool"]["must"]
        tenant_clause = must_clauses[0]
        assert tenant_clause["term"]["tenant_id"] == "test-tenant"
        
        # Check date range
        date_clause = must_clauses[1]
        assert "range" in date_clause
        assert "timestamp" in date_clause["range"]
        assert "lt" in date_clause["range"]["timestamp"] 