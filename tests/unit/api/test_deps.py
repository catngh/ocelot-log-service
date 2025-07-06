import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from datetime import datetime, timedelta

from app.api.deps import (
    get_tenant_id,
    validate_token,
    get_current_token,
    check_tenant_access,
    check_role_permissions,
)
from app.models.token import TokenData, UserRole

class TestDeps:
    async def test_get_tenant_id(self):
        # Test with valid header
        tenant_id = await get_tenant_id(x_tenant_id="test-tenant")
        assert tenant_id == "test-tenant"
        
        # Test with empty header
        with pytest.raises(HTTPException) as excinfo:
            await get_tenant_id(x_tenant_id="")
        assert excinfo.value.status_code == 400
        assert "X-Tenant-ID header is required" in excinfo.value.detail
    
    @pytest.mark.asyncio
    @patch('app.api.deps.get_jwt_collection')
    @patch('app.api.deps.decode_token')
    async def test_validate_token_valid(self, mock_decode_token, mock_get_jwt_collection):
        # Setup mocks
        mock_decode_token.return_value = {"jti": "test-jti", "sub": "test-user"}
        
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {
            "jti": "test-jti",
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "revoked": False
        }
        mock_get_jwt_collection.return_value = mock_collection
        
        # Test valid token
        result = await validate_token("valid-token")
        assert result["jti"] == "test-jti"
        assert result["revoked"] is False
    
    @pytest.mark.asyncio
    @patch('app.api.deps.get_jwt_collection')
    @patch('app.api.deps.decode_token')
    async def test_validate_token_expired(self, mock_decode_token, mock_get_jwt_collection):
        # Setup mocks
        mock_decode_token.return_value = {"jti": "test-jti", "sub": "test-user"}
        
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {
            "jti": "test-jti",
            "expires_at": datetime.utcnow() - timedelta(hours=1),  # Expired
            "revoked": False
        }
        mock_get_jwt_collection.return_value = mock_collection
        
        # Test expired token
        with pytest.raises(HTTPException) as excinfo:
            await validate_token("expired-token")
        assert excinfo.value.status_code == 401
        assert "Token has expired" in excinfo.value.detail
    
    @pytest.mark.asyncio
    @patch('app.api.deps.get_jwt_collection')
    @patch('app.api.deps.decode_token')
    async def test_validate_token_revoked(self, mock_decode_token, mock_get_jwt_collection):
        # Setup mocks
        mock_decode_token.return_value = {"jti": "test-jti", "sub": "test-user"}
        
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {
            "jti": "test-jti",
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "revoked": True  # Revoked
        }
        mock_get_jwt_collection.return_value = mock_collection
        
        # Test revoked token
        with pytest.raises(HTTPException) as excinfo:
            await validate_token("revoked-token")
        assert excinfo.value.status_code == 401
        assert "Token has been revoked" in excinfo.value.detail
    
    @pytest.mark.asyncio
    async def test_check_tenant_access_valid(self):
        # Test valid access
        token_data = TokenData(tenant_ids=["tenant-1", "tenant-2"])
        result = await check_tenant_access(tenant_id="tenant-1", token_data=token_data)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_tenant_access_invalid(self):
        # Test invalid access
        token_data = TokenData(tenant_ids=["tenant-1", "tenant-2"])
        with pytest.raises(HTTPException) as excinfo:
            await check_tenant_access(tenant_id="tenant-3", token_data=token_data)
        assert excinfo.value.status_code == 403
        assert "Token does not have access to tenant" in excinfo.value.detail
    
    @pytest.mark.asyncio
    async def test_check_role_permissions(self):
        # Test admin access
        admin_token = TokenData(roles=["admin"])
        check_admin = check_role_permissions(["admin"])
        result = await check_admin(admin_token)
        assert result is True
        
        # Test writer access
        writer_token = TokenData(roles=["writer"])
        check_writer = check_role_permissions(["admin", "writer"])
        result = await check_writer(writer_token)
        assert result is True
        
        # Test insufficient permissions
        reader_token = TokenData(roles=["reader"])
        check_admin = check_role_permissions(["admin"])
        with pytest.raises(HTTPException) as excinfo:
            await check_admin(reader_token)
        assert excinfo.value.status_code == 403
        assert "Insufficient permissions" in excinfo.value.detail 