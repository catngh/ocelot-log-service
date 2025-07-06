import logging
import json
import traceback
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

from app.core.config import settings
from app.models.log import Log, LogQueryParams

logger = logging.getLogger(__name__)

class OpenSearchService:
    """
    Service for interacting with Amazon OpenSearch.
    """
    
    def __init__(self):
        """
        Initialize OpenSearch client with AWS IAM authentication for Amazon OpenSearch Service.
        """
        self.index_name = f"{settings.SERVICE_NAME_PREFIX}-log-index"
        
        # Get AWS credentials from boto3 session
        try:
            credentials = boto3.Session().get_credentials()
            
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                settings.AWS_REGION,
                'es',
                session_token=credentials.token
            )
            
            # Check for environment variable override
            opensearch_url = os.environ.get("OPENSEARCH_URL", settings.OPENSEARCH_URL)
            
            # Configure OpenSearch client with AWS auth
            if not opensearch_url:
                raise ValueError("OPENSEARCH_URL is required")
                
            logger.info(f"Connecting to OpenSearch at: {opensearch_url}")
            
            # Use the full URL directly
            self.client = OpenSearch(
                hosts=[opensearch_url],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection
            )
            
            # Test connection
            cluster_info = self.client.info()
            logger.info(f"Successfully connected to OpenSearch cluster: {cluster_info.get('cluster_name', 'unknown')}")
            logger.info(f"OpenSearch version: {cluster_info.get('version', {}).get('number', 'unknown')}")
            logger.info(f"OpenSearch client initialized for index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch client: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
            raise
        
    def create_index_if_not_exists(self):
        """
        Create the logs index if it doesn't exist.
        """
        try:
            logger.info(f"Checking if index exists: {self.index_name}")
            exists = self.client.indices.exists(index=self.index_name)
            logger.info(f"Index {self.index_name} exists: {exists}")
            
            if not exists:
                # Define mapping for log documents
                mapping = {
                    "mappings": {
                        "properties": {
                            "timestamp": {"type": "date"},
                            "tenant_id": {"type": "keyword"},
                            "session_id": {"type": "keyword"},
                            "action": {"type": "keyword"},
                            "resource_type": {"type": "keyword"},
                            "resource_id": {"type": "keyword"},
                            "ip_address": {"type": "ip"},
                            "user_agent": {"type": "text"},
                            "before_state": {"type": "object", "enabled": False},  # Not searchable
                            "after_state": {"type": "object", "enabled": False},   # Not searchable
                            "metadata": {"type": "object"},
                            "severity": {"type": "keyword"},
                            "message": {"type": "text", "analyzer": "standard"},
                            "request_id": {"type": "keyword"}
                        }
                    },
                    "settings": {
                        "index": {
                            "number_of_shards": 3,
                            "number_of_replicas": 1
                        }
                    }
                }
                
                logger.info(f"Creating index: {self.index_name} with mapping: {json.dumps(mapping)}")
                # Create the index with the mapping
                result = self.client.indices.create(index=self.index_name, body=mapping)
                logger.info(f"Created index: {self.index_name}, result: {result}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
            raise
    
    def index_log(self, log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Index a log document in OpenSearch.
        
        Args:
            log: Log document to index
            
        Returns:
            OpenSearch response
        """
        try:
            # Ensure the index exists
            self.create_index_if_not_exists()
            
            # Format timestamp if it's a datetime object
            if isinstance(log.get("timestamp"), datetime):
                log["timestamp"] = log["timestamp"].isoformat()
            
            # Use MongoDB _id as document ID if available, otherwise OpenSearch will generate one
            doc_id = str(log.get("_id", log.get("id", None)))
            
            # Create a copy of the log to avoid modifying the original
            log_copy = log.copy()
            
            # Remove _id field as it's a reserved metadata field in OpenSearch
            if "_id" in log_copy:
                del log_copy["_id"]
            
            # Index the document
            response = self.client.index(
                index=self.index_name,
                body=log_copy,
                id=doc_id,
                refresh=True  # Make the document immediately searchable
            )
            
            logger.info(f"Indexed log with ID: {response['_id']}")
            return response
        except Exception as e:
            logger.error(f"Error indexing log: {str(e)}")
            raise
    
    def search_logs(self, tenant_id: str, query_params: LogQueryParams) -> Dict[str, Any]:
        """
        Search logs in OpenSearch.
        
        Args:
            tenant_id: Tenant ID for tenant isolation
            query_params: Query parameters for filtering
            
        Returns:
            Search results with pagination metadata
        """
        try:
            # Build query
            must_clauses = [{"term": {"tenant_id": tenant_id}}]
            
            # Apply filters
            if query_params.action:
                must_clauses.append({"term": {"action": query_params.action}})
            
            if query_params.resource_type:
                must_clauses.append({"term": {"resource_type": query_params.resource_type}})
            
            if query_params.resource_id:
                must_clauses.append({"term": {"resource_id": query_params.resource_id}})
            
            if query_params.severity:
                must_clauses.append({"term": {"severity": query_params.severity}})
            
            # Additional filters
            if query_params.session_id:
                must_clauses.append({"term": {"session_id": query_params.session_id}})
            
            if query_params.ip_address:
                must_clauses.append({"term": {"ip_address": query_params.ip_address}})
            
            if query_params.request_id:
                must_clauses.append({"term": {"request_id": query_params.request_id}})
            
            # Handle user_id as a special case - it could be in metadata or directly in the document
            if query_params.user_id:
                should_clauses = [
                    {"term": {"metadata.user_id": query_params.user_id}},
                    {"term": {"user_id": query_params.user_id}}
                ]
                must_clauses.append({"bool": {"should": should_clauses, "minimum_should_match": 1}})
            
            # Date range filter
            if query_params.start_time or query_params.end_time:
                range_filter = {}
                if query_params.start_time:
                    range_filter["gte"] = query_params.start_time.isoformat()
                if query_params.end_time:
                    range_filter["lte"] = query_params.end_time.isoformat()
                must_clauses.append({"range": {"timestamp": range_filter}})
            
            # Full-text search
            if query_params.search:
                must_clauses.append({
                    "multi_match": {
                        "query": query_params.search,
                        "fields": ["message^2", "resource_type", "resource_id", "metadata.*"]
                    }
                })
            
            # Build the query
            query = {
                "bool": {
                    "must": must_clauses
                }
            }
            
            logger.debug(f"OpenSearch query: {json.dumps(query)}")
            
            # Execute search
            response = self.client.search(
                index=self.index_name,
                body={
                    "query": query,
                    "sort": [{"timestamp": {"order": "desc"}}],
                    "from": query_params.skip,
                    "size": query_params.limit
                }
            )
            
            # Format results
            hits = response["hits"]["hits"]
            total = response["hits"]["total"]["value"]
            
            logs = []
            for hit in hits:
                log = hit["_source"]
                log["id"] = hit["_id"]
                logs.append(log)
            
            # Calculate pagination metadata
            page = query_params.skip // query_params.limit + 1 if query_params.limit > 0 else 1
            
            return {
                "data": logs,
                "meta": {
                    "pagination": {
                        "total": total,
                        "page": page,
                        "size": query_params.limit
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error searching logs: {str(e)}")
            raise
    
    def get_log_by_id(self, log_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a log by ID from OpenSearch.
        
        Args:
            log_id: Log ID
            tenant_id: Tenant ID for tenant isolation
            
        Returns:
            Log document if found, None otherwise
        """
        try:
            response = self.client.get(
                index=self.index_name,
                id=log_id
            )
            
            if response["found"]:
                log = response["_source"]
                
                # Check tenant isolation
                if log.get("tenant_id") != tenant_id:
                    logger.warning(f"Tenant isolation violation: Log {log_id} belongs to tenant {log.get('tenant_id')}, not {tenant_id}")
                    return None
                
                log["id"] = response["_id"]
                return log
            return None
        except Exception as e:
            logger.error(f"Error getting log by ID: {str(e)}")
            return None
    
    def delete_log(self, log_id: str) -> bool:
        """
        Delete a specific log by ID.
        
        Args:
            log_id: ID of the log to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            response = self.client.delete(
                index=self.index_name,
                id=log_id,
                refresh=True  # Make the deletion immediately visible
            )
            logger.info(f"Deleted log with ID: {log_id}")
            return response["result"] == "deleted"
        except Exception as e:
            logger.error(f"Error deleting log: {str(e)}")
            return False
            
    def delete_old_logs(self, tenant_id: str, cutoff_date: datetime) -> int:
        """
        Delete logs older than the cutoff date for a specific tenant.
        
        Args:
            tenant_id: The tenant ID to restrict deletion to
            cutoff_date: Delete logs older than this date
            
        Returns:
            Number of logs deleted
        """
        try:
            # Build the query for old logs from this tenant
            query = {
                "bool": {
                    "must": [
                        {"term": {"tenant_id": tenant_id}},
                        {"range": {"timestamp": {"lt": cutoff_date.isoformat()}}}
                    ]
                }
            }
            
            logger.info(f"Deleting logs for tenant {tenant_id} older than {cutoff_date.isoformat()}")
            
            # Use delete by query API
            response = self.client.delete_by_query(
                index=self.index_name,
                body={"query": query},
                refresh=True  # Make the deletion immediately visible
            )
            
            deleted_count = response.get("deleted", 0)
            logger.info(f"Deleted {deleted_count} logs from OpenSearch")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting old logs: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
            raise

def get_opensearch_service() -> OpenSearchService:
    """
    Factory function to create a new OpenSearch service instance.
    """
    return OpenSearchService() 