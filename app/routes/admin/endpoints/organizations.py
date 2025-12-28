"""Organization management endpoints"""
import logging
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models import User
from app.services.organization_service import OrganizationService
from app.services.user_account_service import UserAccountService
from app.routes.admin.dependencies import get_organization_service, get_user_account_service
from app.exceptions import NotFoundError, ConflictError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations", tags=["Organizations"])


# Request/Response models
class CreateOrganizationRequest(BaseModel):
    name: str


class UpdateOrganizationRequest(BaseModel):
    name: str


class WorkspaceInOrganization(BaseModel):
    id: int
    name: str
    workspace_type: str
    external_id: str
    organization_id: Optional[int] = None


class UserAccountResponse(BaseModel):
    id: int
    provider: str
    provider_id: str
    username: Optional[str]
    account_email: Optional[str]


class UserInOrganization(BaseModel):
    id: int
    display_name: Optional[str]
    is_superadmin: bool
    user_accounts: List[UserAccountResponse]


class TeamInOrganization(BaseModel):
    id: int
    name: str
    display_name: str
    member_count: int


class OrganizationResponse(BaseModel):
    id: int
    name: str
    created_by_user_id: Optional[int]
    created_at: str


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(
    req: CreateOrganizationRequest,
    user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """Create a new organization (SuperAdmin only)"""
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmins can create organizations"
        )

    try:
        org = await org_service.create_organization(req.name, user.id)
        return OrganizationResponse(
            id=org.id,
            name=org.name,
            created_by_user_id=org.created_by_user_id,
            created_at=org.created_at.isoformat() if org.created_at else None
        )
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating organization: {e}")
        raise HTTPException(status_code=500, detail="Failed to create organization")


@router.get("/{org_id}")
async def get_organization(
    org_id: int,
    user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """Get organization details"""
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmins can access organizations"
        )

    try:
        org = await org_service.get_organization(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        return OrganizationResponse(
            id=org.id,
            name=org.name,
            created_by_user_id=org.created_by_user_id,
            created_at=org.created_at.isoformat() if org.created_at else None
        )
    except Exception as e:
        logger.error(f"Error getting organization: {e}")
        raise HTTPException(status_code=500, detail="Failed to get organization")


@router.get("")
async def list_organizations(
    user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_organization_service),
    skip: int = 0,
    limit: int = 100
) -> List[OrganizationResponse]:
    """List all organizations (SuperAdmin only)"""
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmins can list organizations"
        )

    try:
        orgs = await org_service.list_organizations(skip, limit)
        return [
            OrganizationResponse(
                id=org.id,
                name=org.name,
                created_by_user_id=org.created_by_user_id,
                created_at=org.created_at.isoformat() if org.created_at else None
            )
            for org in orgs
        ]
    except Exception as e:
        logger.error(f"Error listing organizations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list organizations")


@router.put("/{org_id}")
async def update_organization(
    org_id: int,
    req: UpdateOrganizationRequest,
    user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """Update organization details"""
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmins can update organizations"
        )

    try:
        org = await org_service.update_organization(org_id, req.name)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        return OrganizationResponse(
            id=org.id,
            name=org.name,
            created_by_user_id=org.created_by_user_id,
            created_at=org.created_at.isoformat() if org.created_at else None
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating organization: {e}")
        raise HTTPException(status_code=500, detail="Failed to update organization")


@router.post("/{org_id}/workspaces/{workspace_id}")
async def add_workspace_to_organization(
    org_id: int,
    workspace_id: int,
    user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_organization_service)
) -> dict:
    """Add workspace to organization"""
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmins can manage organization workspaces"
        )

    try:
        workspace = await org_service.add_workspace_to_organization(org_id, workspace_id)
        return {"status": "success", "workspace_id": workspace.id}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding workspace to organization: {e}")
        raise HTTPException(status_code=500, detail="Failed to add workspace")


@router.delete("/{org_id}/workspaces/{workspace_id}")
async def remove_workspace_from_organization(
    org_id: int,
    workspace_id: int,
    user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_organization_service)
) -> dict:
    """Remove workspace from organization"""
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmins can manage organization workspaces"
        )

    try:
        await org_service.remove_workspace_from_organization(workspace_id)
        return {"status": "success"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing workspace from organization: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove workspace")


@router.get("/workspaces/all", tags=["Workspaces"])
async def list_all_workspaces(
    user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_organization_service)
) -> List[WorkspaceInOrganization]:
    """List all workspaces in the system (SuperAdmin only)"""
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmins can list all workspaces"
        )

    try:
        # Use repository to list all workspaces
        workspaces = await org_service.workspace_repo.list_all()
        return [
            WorkspaceInOrganization(
                id=ws.id,
                name=ws.name,
                workspace_type=ws.workspace_type,
                external_id=ws.external_id,
                organization_id=ws.organization_id
            )
            for ws in workspaces
        ]
    except Exception as e:
        logger.error(f"Error listing all workspaces: {e}")
        raise HTTPException(status_code=500, detail="Failed to list workspaces")


@router.get("/{org_id}/workspaces")
async def get_organization_workspaces(
    org_id: int,
    user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_organization_service)
) -> List[WorkspaceInOrganization]:
    """Get all workspaces in organization"""
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmins can access organization workspaces"
        )

    try:
        workspaces = await org_service.get_organization_workspaces(org_id)
        return [
            WorkspaceInOrganization(
                id=ws.id,
                name=ws.name,
                workspace_type=ws.workspace_type,
                external_id=ws.external_id,
                organization_id=ws.organization_id
            )
            for ws in workspaces
        ]
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting organization workspaces: {e}")
        raise HTTPException(status_code=500, detail="Failed to get workspaces")


@router.get("/{org_id}/users")
async def get_organization_users(
    org_id: int,
    user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_organization_service),
    user_account_service: UserAccountService = Depends(get_user_account_service)
) -> List[UserInOrganization]:
    """Get all users in organization with their accounts"""
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmins can access organization users"
        )

    try:
        users = await org_service.get_organization_users(org_id)
        result = []
        for u in users:
            accounts_summary = await user_account_service.get_user_accounts_summary(u.id)
            all_accounts = accounts_summary.get('slack', []) + accounts_summary.get('telegram', [])
            result.append(UserInOrganization(
                id=u.id,
                display_name=u.display_name,
                is_superadmin=u.is_superadmin,
                user_accounts=[
                    UserAccountResponse(
                        id=acc['id'],
                        provider=acc.get('provider', 'unknown'),
                        provider_id=acc['provider_id'],
                        username=acc['username'],
                        account_email=acc['email']
                    )
                    for acc in all_accounts
                ]
            ))
        return result
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting organization users: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users")


@router.post("/{org_id}/users/{user_id}/accounts")
async def add_user_account(
    org_id: int,
    user_id: int,
    req: dict,
    admin: User = Depends(get_current_user),
    user_account_service: UserAccountService = Depends(get_user_account_service)
) -> UserAccountResponse:
    """Add a new login method to a user"""
    if not admin.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmins can add user accounts"
        )

    try:
        account = await user_account_service.create_user_account(
            user_id=user_id,
            provider=req['provider'],
            provider_id=req['provider_id'],
            workspace_id=req.get('workspace_id'),
            username=req.get('username'),
            account_email=req.get('account_email')
        )
        return UserAccountResponse(
            id=account.id,
            provider=account.provider,
            provider_id=account.provider_id,
            username=account.username,
            account_email=account.account_email
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding user account: {e}")
        raise HTTPException(status_code=500, detail="Failed to add account")


@router.delete("/{org_id}/users/{user_id}/accounts/{account_id}")
async def remove_user_account(
    org_id: int,
    user_id: int,
    account_id: int,
    admin: User = Depends(get_current_user),
    user_account_service: UserAccountService = Depends(get_user_account_service)
) -> dict:
    """Remove a login method from a user"""
    if not admin.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmins can remove user accounts"
        )

    try:
        success = await user_account_service.delete_user_account(account_id)
        if not success:
            raise HTTPException(status_code=404, detail="Account not found")
        return {"status": "success"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing user account: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove account")
