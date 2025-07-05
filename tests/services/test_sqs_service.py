import unittest
from unittest.mock import patch, MagicMock
import json
from app.services.sqs_service import SQSService

class TestSQSService(unittest.TestCase):
    """
    Test cases for the SQS service.
    """
    
    @patch('boto3.client')
    def setUp(self, mock_boto_client):
        """
        Set up test fixtures.
        """
        self.mock_sqs_client = MagicMock()
        mock_boto_client.return_value = self.mock_sqs_client
        self.sqs_service = SQSService()
        self.sqs_service.queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
    
    def test_send_message(self):
        """
        Test sending a message to SQS.
        """
        # Mock response
        self.mock_sqs_client.send_message.return_value = {
            'MessageId': '12345678-1234-1234-1234-123456789012',
            'MD5OfMessageBody': 'md5hash'
        }
        
        # Test data
        message = {
            "action": "CREATE",
            "resource_type": "user",
            "resource_id": "user123",
            "message": "User created"
        }
        
        # Call the method
        response = self.sqs_service.send_message(message)
        
        # Assertions
        self.mock_sqs_client.send_message.assert_called_once_with(
            QueueUrl=self.sqs_service.queue_url,
            MessageBody=json.dumps(message)
        )
        self.assertEqual(response['MessageId'], '12345678-1234-1234-1234-123456789012')
    
    def test_receive_messages(self):
        """
        Test receiving messages from SQS.
        """
        # Mock response
        self.mock_sqs_client.receive_message.return_value = {
            'Messages': [
                {
                    'MessageId': '12345678-1234-1234-1234-123456789012',
                    'ReceiptHandle': 'receipt-handle',
                    'Body': json.dumps({
                        "action": "CREATE",
                        "resource_type": "user",
                        "resource_id": "user123",
                        "message": "User created"
                    })
                }
            ]
        }
        
        # Call the method
        messages = self.sqs_service.receive_messages(max_messages=1, wait_time=0)
        
        # Assertions
        self.mock_sqs_client.receive_message.assert_called_once_with(
            QueueUrl=self.sqs_service.queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=0,
            AttributeNames=['All'],
            MessageAttributeNames=['All']
        )
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['MessageId'], '12345678-1234-1234-1234-123456789012')
    
    def test_delete_message(self):
        """
        Test deleting a message from SQS.
        """
        # Mock response
        self.mock_sqs_client.delete_message.return_value = {}
        
        # Receipt handle
        receipt_handle = 'test-receipt-handle'
        
        # Call the method
        self.sqs_service.delete_message(receipt_handle)
        
        # Assertions
        self.mock_sqs_client.delete_message.assert_called_once_with(
            QueueUrl=self.sqs_service.queue_url,
            ReceiptHandle=receipt_handle
        )


if __name__ == '__main__':
    unittest.main() 