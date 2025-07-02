from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import ssl
from app.core.config import settings

# MongoDB client instance
mongo_client = None
# MongoDB database instance
database = None


def get_database():
    """
    Get database instance.
    """
    return database


def connect_to_mongo():
    """
    Connect to MongoDB.
    """
    global mongo_client, database
    
    if mongo_client is not None:
        return
    
    try:
        if "mongodb+srv" in settings.MONGODB_URL:
            mongo_client = MongoClient(settings.MONGODB_URL,server_api=ServerApi('1'))
        else:
            mongo_client = MongoClient(settings.MONGODB_URL)
        mongo_client.admin.command('ping')
        
        database = mongo_client[settings.MONGODB_DB_NAME]
        
        # Create collections and indexes
        setup_collections()
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        raise


def close_mongo_connection():
    """
    Close MongoDB connection.
    """
    global mongo_client
    
    if mongo_client is not None:
        mongo_client.close()
        mongo_client = None
        print("MongoDB connection closed")


def setup_collections():
    """
    Set up collections and indexes.
    """
    # Create tenant collection
    tenant_collection = database["tenants"]
    # Create unique index on tenant_id
    tenant_collection.create_index("tenant_id", unique=True)
    
    # Create logs collection with multi-tenant approach
    logs_collection = database["logs"]
    # Create indexes for common query patterns
    logs_collection.create_index("tenant_id")  # For tenant isolation
    logs_collection.create_index([("tenant_id", 1), ("timestamp", 1)])  # For tenant + time queries
    logs_collection.create_index([("tenant_id", 1), ("action", 1), ("resource_type", 1)])  # For filtered queries
    logs_collection.create_index([("tenant_id", 1), ("severity", 1)])  # For severity filtering
    logs_collection.create_index([("tenant_id", 1), ("resource_id", 1)])  # For resource queries
    # Create text index for full-text search
    logs_collection.create_index([("message", "text")])
    
    # Create JWT tokens collection
    jwt_collection = database["jwt_tokens"]
    # Create indexes for JWT tokens
    jwt_collection.create_index("jti", unique=True)
    jwt_collection.create_index("expires_at")
    jwt_collection.create_index("tenant_ids")
    jwt_collection.create_index("roles")


def get_collection(collection_name):
    """
    Get a collection by name.
    """
    return database[collection_name]

def get_jwt_collection():
    """
    Get JWT tokens collection.
    """
    return database["jwt_tokens"] 