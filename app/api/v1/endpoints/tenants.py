from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Body, status
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId

from app.api.deps import get_tenant_collection, get_db, get_current_user
from app.models.user import TokenData
from app.models.tenant import Tenant, TenantCreate, TenantUpdate, TenantInDB
from app.core.security import get_password_hash

router = APIRouter()


@router.post("", response_model=Tenant, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant: TenantCreate,
    collection: Collection = Depends(get_tenant_collection),
    db: Database = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Create a new tenant.
    """
    # Check if tenant ID already exists
    if collection.find_one({"tenant_id": tenant.tenant_id}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with ID {tenant.tenant_id} already exists",
        )
    
    # Create tenant object
    tenant_dict = tenant.dict(exclude={"api_key"})
    tenant_in_db = TenantInDB(**tenant_dict)
    
    # Handle API key if provided
    if tenant.api_key:
        hashed_api_key = get_password_hash(tenant.api_key)
        tenant_in_db.api_keys = [hashed_api_key]
    
    # Insert tenant to database
    result = collection.insert_one(tenant_in_db.dict(by_alias=True))
    
    # Get the created tenant
    created_tenant = collection.find_one({"_id": result.inserted_id})
    
    if created_tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    
    return created_tenant


@router.get("", response_model=List[Tenant])
async def get_tenants(
    collection: Collection = Depends(get_tenant_collection),
    current_user: TokenData = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    """
    Get all tenants.
    """
    tenants = list(collection.find().skip(skip).limit(limit))
    return tenants


@router.get("/{tenant_id}", response_model=Tenant)
async def get_tenant(
    tenant_id: str = Path(..., title="The ID of the tenant to get"),
    collection: Collection = Depends(get_tenant_collection),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Get a specific tenant by ID.
    """
    if ObjectId.is_valid(tenant_id):
        tenant = collection.find_one({"_id": ObjectId(tenant_id)})
    else:
        tenant = collection.find_one({"tenant_id": tenant_id})
    
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    
    return tenant


@router.put("/{tenant_id}", response_model=Tenant)
async def update_tenant(
    tenant_update: TenantUpdate,
    tenant_id: str = Path(..., title="The ID of the tenant to update"),
    collection: Collection = Depends(get_tenant_collection),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Update a tenant by ID.
    """
    # Find tenant
    if ObjectId.is_valid(tenant_id):
        tenant = collection.find_one({"_id": ObjectId(tenant_id)})
    else:
        tenant = collection.find_one({"tenant_id": tenant_id})
    
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    
    # Update tenant with new fields
    update_data = tenant_update.dict(exclude_unset=True)
    result = collection.update_one(
        {"_id": tenant["_id"]}, {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED, detail="Tenant not modified"
        )
    
    # Get the updated tenant
    updated_tenant = collection.find_one({"_id": tenant["_id"]})
    
    return updated_tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str = Path(..., title="The ID of the tenant to delete"),
    collection: Collection = Depends(get_tenant_collection),
    db: Database = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Delete a tenant by ID.
    """
    # Find tenant
    if ObjectId.is_valid(tenant_id):
        tenant = collection.find_one({"_id": ObjectId(tenant_id)})
        if tenant is None:
            tenant = collection.find_one({"tenant_id": tenant_id})
    else:
        tenant = collection.find_one({"tenant_id": tenant_id})
    
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    
    # Delete tenant
    result = collection.delete_one({"_id": tenant["_id"]})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    
    return None 