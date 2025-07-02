import os
from typing import Any, Dict, Optional, List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator
from dotenv import load_dotenv

# Load .env file explicitly
print(f"Loading environment from .env file (exists: {os.path.exists('.env')})")
load_dotenv()

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Ocelot Log Service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # MongoDB settings
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "ocelot_logs"
    
    # JWT Authentication
    SECRET_KEY: str = "dev_secret_key_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    
    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # SQS Configuration
    SQS_QUEUE_URL: Optional[str] = None
    
    # OpenSearch Configuration
    OPENSEARCH_URL: Optional[str] = None
    OPENSEARCH_USERNAME: Optional[str] = None
    OPENSEARCH_PASSWORD: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
print(f"Loaded settings: MONGODB_URL={settings.MONGODB_URL}, PROJECT_NAME={settings.PROJECT_NAME}") 