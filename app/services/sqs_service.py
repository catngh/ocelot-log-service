import boto3
import json
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global instance for singleton pattern
_sqs_service_instance = None

class SQSService:
    """
    Service for interacting with Amazon SQS.
    """
    
    def __init__(self):
        """
        Initialize SQS client with AWS credentials from settings.
        """
        logger.info("Initializing SQS service")
        # Re-import settings to ensure we have the latest values
        from app.core.config import settings
        
        self.sqs = boto3.client(
            'sqs',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.queue_url = settings.SQS_QUEUE_URL
        logger.info(f"SQS service initialized with queue URL: {self.queue_url}")
        
    def send_message(self, message_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to the SQS queue.
        
        Args:
            message_body: Dictionary containing the message data
            
        Returns:
            Dictionary containing the SQS response
        """
        try:
            # Convert message body to JSON string
            message_str = json.dumps(message_body)
            
            # Send message to SQS
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message_str
            )
            
            logger.info(f"Message sent to SQS: {response['MessageId']}")
            return response
        except Exception as e:
            logger.error(f"Error sending message to SQS: {str(e)}")
            raise
    
    def receive_messages(self, max_messages: int = 10, wait_time: int = 20) -> list:
        """
        Receive messages from the SQS queue.
        
        Args:
            max_messages: Maximum number of messages to receive (1-10)
            wait_time: Long polling wait time in seconds (0-20)
            
        Returns:
            List of received messages
        """
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time,
                AttributeNames=['All'],
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            logger.info(f"Received {len(messages)} messages from SQS")
            return messages
        except Exception as e:
            logger.error(f"Error receiving messages from SQS: {str(e)}")
            raise
    
    def delete_message(self, receipt_handle: str) -> Dict[str, Any]:
        """
        Delete a message from the SQS queue after processing.
        
        Args:
            receipt_handle: Receipt handle of the message to delete
            
        Returns:
            Dictionary containing the SQS response
        """
        try:
            response = self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            
            logger.info(f"Deleted message from SQS: {receipt_handle}")
            return response
        except Exception as e:
            logger.error(f"Error deleting message from SQS: {str(e)}")
            raise


def get_sqs_service() -> SQSService:
    """
    Factory function to create a new SQS service instance or return the existing one.
    Implements the singleton pattern to avoid creating multiple connections.
    """
    global _sqs_service_instance
    if _sqs_service_instance is None:
        _sqs_service_instance = SQSService()
    return _sqs_service_instance 