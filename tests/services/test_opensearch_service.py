import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import json

from app.services.opensearch_service import OpenSearchService
from app.models.log import LogQueryParams

class TestOpenSearchService(unittest.TestCase):
    """
    Test cases for the OpenSearch service.
    """
    
    @patch('opensearchpy.OpenSearch')
    def setUp(self, mock_opensearch):
        """
        Set up test fixtures.
        """
        self.mock_client = MagicMock()
        mock_opensearch.return_value = self.mock_client
        self.opensearch_service = OpenSearchService()
        self.opensearch_service.index_name = "test-logs"
    
    def test_create_index_if_not_exists_new(self):
        """
        Test creating a new index when it doesn't exist.
        """
        # Mock index doesn't exist
        self.mock_client.indices.exists.return_value = False
        
        # Call the method
        result = self.opensearch_service.create_index_if_not_exists()
        
        # Assertions
        self.mock_client.indices.exists.assert_called_once_with(index=self.opensearch_service.index_name)
        self.mock_client.indices.create.assert_called_once()
        self.assertTrue(result)
    
    def test_create_index_if_not_exists_existing(self):
        """
        Test not creating an index when it already exists.
        """
        # Mock index exists
        self.mock_client.indices.exists.return_value = True
        
        # Call the method
        result = self.opensearch_service.create_index_if_not_exists()
        
        # Assertions
        self.mock_client.indices.exists.assert_called_once_with(index=self.opensearch_service.index_name)
        self.mock_client.indices.create.assert_not_called()
        self.assertFalse(result)
    
    def test_index_log(self):
        """
        Test indexing a log document.
        """
        # Mock response
        self.mock_client.index.return_value = {
            "_index": "test-logs",
            "_id": "test-id",
            "_version": 1,
            "result": "created",
            "_shards": {"total": 2, "successful": 2, "failed": 0},
            "_seq_no": 0,
            "_primary_term": 1
        }
        
        # Mock create_index_if_not_exists
        self.opensearch_service.create_index_if_not_exists = MagicMock(return_value=True)
        
        # Test data
        log = {
            "_id": "test-id",
            "action": "CREATE",
            "resource_type": "user",
            "resource_id": "user123",
            "message": "User created",
            "severity": "INFO",
            "timestamp": datetime.utcnow(),
            "tenant_id": "tenant1"
        }
        
        # Call the method
        response = self.opensearch_service.index_log(log)
        
        # Assertions
        self.opensearch_service.create_index_if_not_exists.assert_called_once()
        self.mock_client.index.assert_called_once()
        self.assertEqual(response["_id"], "test-id")
    
    def test_search_logs(self):
        """
        Test searching logs.
        """
        # Mock response
        self.mock_client.search.return_value = {
            "took": 5,
            "timed_out": False,
            "_shards": {"total": 1, "successful": 1, "skipped": 0, "failed": 0},
            "hits": {
                "total": {"value": 1, "relation": "eq"},
                "max_score": 1.0,
                "hits": [
                    {
                        "_index": "test-logs",
                        "_id": "test-id",
                        "_score": 1.0,
                        "_source": {
                            "action": "CREATE",
                            "resource_type": "user",
                            "resource_id": "user123",
                            "message": "User created",
                            "severity": "INFO",
                            "timestamp": "2023-01-01T00:00:00",
                            "tenant_id": "tenant1"
                        }
                    }
                ]
            }
        }
        
        # Test data
        tenant_id = "tenant1"
        query_params = LogQueryParams(
            search="user created",
            action="CREATE",
            resource_type="user",
            limit=10,
            skip=0
        )
        
        # Call the method
        result = self.opensearch_service.search_logs(tenant_id, query_params)
        
        # Assertions
        self.mock_client.search.assert_called_once()
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["action"], "CREATE")
        self.assertEqual(result["meta"]["pagination"]["total"], 1)
    
    def test_get_log_by_id(self):
        """
        Test getting a log by ID.
        """
        # Mock response
        self.mock_client.get.return_value = {
            "_index": "test-logs",
            "_id": "test-id",
            "_version": 1,
            "_seq_no": 0,
            "_primary_term": 1,
            "found": True,
            "_source": {
                "action": "CREATE",
                "resource_type": "user",
                "resource_id": "user123",
                "message": "User created",
                "severity": "INFO",
                "timestamp": "2023-01-01T00:00:00",
                "tenant_id": "tenant1"
            }
        }
        
        # Call the method
        log = self.opensearch_service.get_log_by_id("test-id", "tenant1")
        
        # Assertions
        self.mock_client.get.assert_called_once_with(
            index=self.opensearch_service.index_name,
            id="test-id"
        )
        self.assertIsNotNone(log)
        self.assertEqual(log["action"], "CREATE")
        self.assertEqual(log["id"], "test-id")
    
    def test_get_log_by_id_wrong_tenant(self):
        """
        Test getting a log by ID with wrong tenant (tenant isolation).
        """
        # Mock response
        self.mock_client.get.return_value = {
            "_index": "test-logs",
            "_id": "test-id",
            "_version": 1,
            "_seq_no": 0,
            "_primary_term": 1,
            "found": True,
            "_source": {
                "action": "CREATE",
                "resource_type": "user",
                "resource_id": "user123",
                "message": "User created",
                "severity": "INFO",
                "timestamp": "2023-01-01T00:00:00",
                "tenant_id": "tenant1"
            }
        }
        
        # Call the method with wrong tenant
        log = self.opensearch_service.get_log_by_id("test-id", "tenant2")
        
        # Assertions
        self.mock_client.get.assert_called_once()
        self.assertIsNone(log)  # Should return None due to tenant isolation
    
    def test_delete_log(self):
        """
        Test deleting a log.
        """
        # Mock response
        self.mock_client.delete.return_value = {
            "_index": "test-logs",
            "_id": "test-id",
            "_version": 2,
            "result": "deleted",
            "_shards": {"total": 2, "successful": 2, "failed": 0},
            "_seq_no": 1,
            "_primary_term": 1
        }
        
        # Call the method
        result = self.opensearch_service.delete_log("test-id")
        
        # Assertions
        self.mock_client.delete.assert_called_once_with(
            index=self.opensearch_service.index_name,
            id="test-id",
            refresh=True
        )
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main() 