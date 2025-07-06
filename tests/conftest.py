# Configure test fixtures for pytest
import pytest

# No path manipulation needed - the package should be installed properly
# Tests should import from the installed package

@pytest.fixture(scope="session")
def test_app():
    """
    Create a test app instance for testing.
    """
    from app.db.mongodb import close_mongo_connection
    
    # Teardown - ensure database connection is closed after tests
    yield
    close_mongo_connection()

# Any other test fixtures can be defined here 