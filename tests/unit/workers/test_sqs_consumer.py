import pytest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime
from bson import ObjectId

from app.workers.sqs_consumer import LogConsumerWorker

class TestLogConsumerWorker:
    @patch('app.workers.sqs_consumer.get_database')
    @patch('app.workers.sqs_consumer.get_sqs_service')
    @patch('app.workers.sqs_consumer.connect_to_mongo')
    def setup_worker(self, mock_connect_mongo, mock_get_sqs_service, mock_get_database):
        # Setup database mock
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_database.return_value = mock_db
        
        # Setup SQS service mock
        mock_sqs = MagicMock()
        mock_get_sqs_service.return_value = mock_sqs
        
        # Create worker
        worker = LogConsumerWorker()
        
        return worker, mock_db, mock_collection, mock_sqs
    
    def test_init(self):
        # Setup worker
        worker, mock_db, mock_collection, mock_sqs = self.setup_worker()
        
        # Assertions
        assert worker.db is mock_db
        assert worker.logs_collection is mock_collection
        assert worker.sqs_service is mock_sqs
    
    def test_process_message_success(self):
        # Setup worker
        worker, mock_db, mock_collection, mock_sqs = self.setup_worker()
        
        # Configure mocks
        mock_collection.insert_one.return_value = MagicMock(inserted_id=ObjectId("507f1f77bcf86cd799439011"))
        
        # Create test message
        timestamp_str = datetime.utcnow().isoformat()
        test_message = {
            "MessageId": "test-message-id",
            "ReceiptHandle": "test-receipt-handle",
            "Body": json.dumps({
                "action": "CREATE",
                "resource_type": "user",
                "resource_id": "user123",
                "message": "User created",
                "tenant_id": "test-tenant",
                "timestamp": timestamp_str
            })
        }
        
        # Call method
        result = worker.process_message(test_message)
        
        # Assertions
        assert result is True
        assert mock_collection.insert_one.called
        assert mock_sqs.delete_message.called
        
        # Check insert_one args - verify timestamp conversion
        insert_args = mock_collection.insert_one.call_args[0][0]
        assert isinstance(insert_args["timestamp"], datetime)
        assert insert_args["tenant_id"] == "test-tenant"
        
        # Check delete_message args
        delete_args = mock_sqs.delete_message.call_args[1]
        assert delete_args["ReceiptHandle"] == "test-receipt-handle"
    
    def test_process_message_missing_tenant(self):
        # Setup worker
        worker, mock_db, mock_collection, mock_sqs = self.setup_worker()
        
        # Create test message with missing tenant_id
        test_message = {
            "MessageId": "test-message-id",
            "ReceiptHandle": "test-receipt-handle",
            "Body": json.dumps({
                "action": "CREATE",
                "resource_type": "user",
                "resource_id": "user123",
                "message": "User created"
                # No tenant_id
            })
        }
        
        # Call method
        result = worker.process_message(test_message)
        
        # Assertions
        assert result is False
        assert not mock_collection.insert_one.called
        assert not mock_sqs.delete_message.called
    
    def test_process_message_exception(self):
        # Setup worker
        worker, mock_db, mock_collection, mock_sqs = self.setup_worker()
        
        # Configure mock to raise exception
        mock_collection.insert_one.side_effect = Exception("Database error")
        
        # Create test message
        test_message = {
            "MessageId": "test-message-id",
            "ReceiptHandle": "test-receipt-handle",
            "Body": json.dumps({
                "action": "CREATE",
                "resource_type": "user",
                "resource_id": "user123",
                "message": "User created",
                "tenant_id": "test-tenant",
                "timestamp": datetime.utcnow().isoformat()
            })
        }
        
        # Call method
        result = worker.process_message(test_message)
        
        # Assertions
        assert result is False
        assert mock_collection.insert_one.called
        assert not mock_sqs.delete_message.called
    
    @patch('app.workers.sqs_consumer.close_mongo_connection')
    @patch('app.workers.sqs_consumer.time.sleep')
    @patch('app.workers.sqs_consumer.running', False)  # Stop loop immediately
    def test_run(self, mock_sleep, mock_close_mongo):
        # Setup worker
        worker, mock_db, mock_collection, mock_sqs = self.setup_worker()
        
        # Mock process_message
        worker.process_message = MagicMock(return_value=True)
        
        # Configure SQS mock to return messages once then empty
        mock_sqs.receive_messages.side_effect = [
            [
                {"MessageId": "msg1", "Body": "{}"},
                {"MessageId": "msg2", "Body": "{}"}
            ],
            []  # Return empty on second call
        ]
        
        # Call run method - should exit due to running=False
        worker.run()
        
        # Assertions
        assert mock_close_mongo.called
        assert worker.process_message.call_count == 0  # Won't process any messages since running=False
        
    @patch('app.workers.sqs_consumer.running', True)  # Allow loop to run
    @patch('app.workers.sqs_consumer.running', new_callable=MagicMock)  # Make it writable
    @patch('app.workers.sqs_consumer.close_mongo_connection')
    def test_run_with_exception(self, mock_close_mongo, mock_running):
        # Setup worker
        worker, mock_db, mock_collection, mock_sqs = self.setup_worker()
        
        # Configure SQS mock to raise exception
        mock_sqs.receive_messages.side_effect = Exception("SQS error")
        
        # Make mock_running return True once then False
        mock_running.__bool__.side_effect = [True, False]
        
        # Call run method
        worker.run()
        
        # Assertions
        assert mock_close_mongo.called
        assert mock_sqs.receive_messages.called 