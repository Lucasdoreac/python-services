import pytest
import mongomock
from datetime import datetime, timedelta
# Mocking pymongo.MongoClient with mongomock.MongoClient globally before importing any modules
pytest.MonkeyPatch().setattr('pymongo.MongoClient', mongomock.MongoClient)

# Import the AuthenticationRepository after applying the global mock
from DAL import AuthenticationRepository
from BLL import AuthenticationController  # Assuming the controller is in a module named 'controller'

@pytest.fixture(scope='class')
def auth_repo():
    """Fixture to create an AuthenticationRepository with a mocked database."""
    yield AuthenticationRepository()
    # Here you would add any necessary cleanup if there are side effects
    # Since mongomock cleans itself up and no other cleanup is mentioned,
    # this may simply pass without additional code.


class TestAuthenticationRepository:
    def test_insert_authentication(self, auth_repo):
        """Test inserting an authentication record."""
        email = "user@example.com"
        token = "secure_token"
        expires_at = datetime.now() + timedelta(days=1)
        inserted_id = auth_repo.insert_authentication(email, token, expires_at)
        assert inserted_id is not None, "Failed to insert authentication data."

    def test_validate_authentication(self, auth_repo):
        """Test validating an existing authentication record."""
        email = "user@example.com"
        token = "secure_token"
        expires_at = datetime.now() + timedelta(days=1)
        auth_repo.insert_authentication(email, token, expires_at)
        is_valid = auth_repo.validate_authentication(email, token)
        assert is_valid, "Authentication should be valid."

        # Test with expired token
        expired_token = "expired_token"
        expired_at = datetime.now() - timedelta(days=1)
        auth_repo.insert_authentication(email, expired_token, expired_at)
        is_expired = auth_repo.validate_authentication(email, expired_token)
        assert not is_expired, "Expired token should not be valid."

    def test_validate_nonexistent_authentication(self, auth_repo):
        """Test the validation of a nonexistent authentication record."""
        is_valid = auth_repo.validate_authentication("nonexistent@example.com", "any_token")
        assert not is_valid, "Nonexistent authentication should not be valid."


# Controller test starts here
@pytest.fixture(scope='class')
def auth_controller(auth_repo):
    """Fixture to create an instance of AuthenticationController with the mocked AuthenticationRepository."""
    # Mock the repository within the controller
    controller = AuthenticationController()
    controller.tokens_repository = auth_repo
    return controller


@pytest.mark.usefixtures("auth_controller")
class TestAuthenticationController:
    def test_insert_token(self, auth_controller):
        email = "user@example.com"
        token = "secure_token"
        inserted_id = auth_controller.insert_token(email, token)
        assert inserted_id is not None, "Token insertion failed."

    def test_is_token_valid(self, auth_controller):
        email = "user@example.com"
        token = "secure_token"
        # Insert a valid token
        auth_controller.insert_token(email, token)
        assert auth_controller.is_token_valid(token, email), "The token should be valid."

        # Check expired token
        expired_token = "expired_token"
        expired_at = datetime.now() - timedelta(days=1)
        auth_controller.tokens_repository.insert_authentication(email, expired_token, expired_at)
        assert not auth_controller.is_token_valid(expired_token, email), "The expired token should not be valid."

    def test_is_token_nonexistent(self, auth_controller):
        assert not auth_controller.is_token_valid("nonexistent_token", "fake@example.com"), "Nonexistent token should not be valid."