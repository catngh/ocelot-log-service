import pytest
from unittest.mock import MagicMock, patch
import json

from app.services.sqs_service import SQSService, get_sqs_service

class TestSQSService:
    @patch('app.services.sqs_service.boto3')
    def setup_service(self, mock_boto3):
        # Setup boto3 client mock
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Create service
        service = SQSService()
        
        return service, mock_client
    
    def test_init(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Assertions
        assert service.sqs is mock_client
    
    def test_send_message(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Configure mock
        mock_client.send_message.return_value = {"MessageId": "test-message-id"}
        
        # Create test message
        message = {
            "action": "CREATE",
            "resource_type": "user",
            "resource_id": "user123",
            "message": "User created",
            "tenant_id": "test-tenant"
        }
        
        # Call method
        result = service.send_message(message)
        
        # Assertions
        assert mock_client.send_message.called
        assert result["MessageId"] == "test-message-id"
        
        # Check send_message args
        send_args = mock_client.send_message.call_args[1]
        assert "MessageBody" in send_args
        
        # Verify JSON serialization
        message_body = send_args["MessageBody"]
        deserialized = json.loads(message_body)
        assert deserialized["action"] == "CREATE"
        assert deserialized["tenant_id"] == "test-tenant"
    
    def test_receive_messages(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Configure mock
        mock_client.receive_message.return_value = {
            "Messages": [
                {
                    "MessageId": "msg1",
                    "ReceiptHandle": "receipt1",
                    "Body": json.dumps({"message": "Test 1"})
                },
                {
                    "MessageId": "msg2",
                    "ReceiptHandle": "receipt2",
                    "Body": json.dumps({"message": "Test 2"})
                }
            ]
        }
        
        # Call method
        messages = service.receive_messages(max_messages=2, wait_time=5)
        
        # Assertions
        assert mock_client.receive_message.called
        assert len(messages) == 2
        assert messages[0]["MessageId"] == "msg1"
        assert messages[1]["MessageId"] == "msg2"
        
        # Check receive_message args
        receive_args = mock_client.receive_message.call_args[1]
        assert receive_args["MaxNumberOfMessages"] == 2
        assert receive_args["WaitTimeSeconds"] == 5
    
    def test_delete_message(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Configure mock
        mock_client.delete_message.return_value = {}
        
        # Call method
        result = service.delete_message("receipt-handle-123")
        
        # Assertions
        assert mock_client.delete_message.called
        
        # Check delete_message args
        delete_args = mock_client.delete_message.call_args[1]
        assert delete_args["ReceiptHandle"] == "receipt-handle-123"
    
    def test_error_handling_send_message(self):
        # Setup service
        service, mock_client = self.setup_service()
        
        # Configure mock to raise exception
        mock_client.send_message.side_effect = Exception("SQS error")
        
        # Create test message
        message = {"message": "Test"}
        
        # Call method - should raise exception
        with pytest.raises(Exception) as excinfo:
            service.send_message(message)
        
        assert "SQS error" in str(excinfo.value)
    
    @patch('app.services.sqs_service._sqs_service_instance', None)
    @patch('app.services.sqs_service.SQSService')
    def test_get_sqs_service_new(self, mock_service_class):
        # Configure mock
        mock_instance = MagicMock()
        mock_service_class.return_value = mock_instance
        
        # Call function
        service = get_sqs_service()
        
        # Assertions
        assert service is mock_instance
        assert mock_service_class.called
    
    @patch('app.services.sqs_service.SQSService')
    def test_get_sqs_service_existing(self, mock_service_class):
        # Setup existing instance
        existing_instance = MagicMock()
        with patch('app.services.sqs_service._sqs_service_instance', existing_instance):
            # Call function
            service = get_sqs_service()
            
            # Assertions
            assert service is existing_instance
            assert not mock_service_class.called 