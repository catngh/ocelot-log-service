#!/usr/bin/env python
"""
Ocelot Log Service - SQS Consumer Service

This script starts the SQS consumer service that processes log messages from SQS
and stores them in MongoDB and optionally indexes them in OpenSearch.
"""
import logging
import sys
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env", override=True)
from app.workers.sqs_consumer import main
from app.core.config import settings

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("SQS Consumer Service stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"SQS Consumer Service failed: {str(e)}")
        sys.exit(1) 