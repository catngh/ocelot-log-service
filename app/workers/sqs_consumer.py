import json
import logging
import time
import signal
import sys
from datetime import datetime
from typing import Dict, Any
from bson import ObjectId

from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.services.sqs_service import get_sqs_service
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Flag to control worker loop
running = True

def signal_handler(sig, frame):
    """
    Handle termination signals gracefully.
    """
    global running
    logger.info("Received termination signal. Shutting down...")
    running = False

class LogConsumerWorker:
    """
    Worker that consumes log messages from SQS and saves them to MongoDB.
    """
    
    def __init__(self):
        """
        Initialize the worker with SQS service and MongoDB connection.
        """
        # Connect to MongoDB
        connect_to_mongo()
        self.db = get_database()
        self.logs_collection = self.db["logs"]
        
        # Initialize SQS service using the singleton pattern
        self.sqs_service = get_sqs_service()
        
        logger.info("Log consumer worker initialized")
    
    def process_message(self, message: Dict[str, Any]) -> bool:
        """
        Process a single SQS message.
        
        Args:
            message: SQS message object
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # Extract message body
            message_body = json.loads(message["Body"])
            logger.info(f"Processing message: {message['MessageId']}")
            
            # Parse timestamp if it's a string
            if isinstance(message_body.get("timestamp"), str):
                message_body["timestamp"] = datetime.fromisoformat(message_body["timestamp"].replace("Z", "+00:00"))
            
            # Get tenant_id from the message
            tenant_id = message_body.get("tenant_id")
            if not tenant_id:
                logger.error("Message missing tenant_id, cannot process")
                return False
            
            # Insert log into MongoDB
            result = self.logs_collection.insert_one(message_body)
            logger.info(f"Log inserted into MongoDB with ID: {result.inserted_id}")
            
            # Delete message from queue
            self.sqs_service.delete_message(message["ReceiptHandle"])
            
            return True
        except Exception as e:
            logger.error(f"Error processing message {message.get('MessageId')}: {str(e)}")
            return False
    
    def run(self):
        """
        Main worker loop that continuously polls SQS for messages.
        """
        logger.info("Starting log consumer worker")
        
        while running:
            try:
                # Receive messages from SQS
                messages = self.sqs_service.receive_messages(max_messages=10, wait_time=20)
                
                if not messages:
                    logger.debug("No messages received, continuing...")
                    continue
                
                # Process each message
                for message in messages:
                    self.process_message(message)
                    
            except Exception as e:
                logger.error(f"Error in worker loop: {str(e)}")
                # Sleep briefly before retrying
                time.sleep(5)
        
        # Cleanup when loop exits
        logger.info("Worker loop terminated")
        close_mongo_connection()


def main():
    """
    Entry point for the worker.
    """
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run the worker
    worker = LogConsumerWorker()
    worker.run()


if __name__ == "__main__":
    main() 