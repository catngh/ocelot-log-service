import os
from typing import Any, Dict, Optional, List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator
from dotenv import load_dotenv
import pathlib

# Get the project root directory - this ensures we find the .env file regardless of where the script is run from
ROOT_DIR = pathlib.Path(__file__).parent.parent.parent
env_path = os.path.join(ROOT_DIR, '.env')

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Ocelot Log Service"
    SERVICE_NAME_PREFIX: str = "ocelot"
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
    
    class Config:
        env_file = env_path
        case_sensitive = True


def load_config() -> Settings:
    """
    Load and initialize settings.
    
    Returns:
        Settings: Initialized settings object
    """
    # Load .env file explicitly from project root
    load_dotenv(dotenv_path=env_path)
    config = Settings()
    return config


settings = load_config() 