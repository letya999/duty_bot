"""Service for Organization operations."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Organization, User, Workspace, Team
from app.repositories import OrganizationRepository, WorkspaceRepository, TeamRepository
from app.exceptions import NotFoundError, ConflictError


class OrganizationService:
    """Service for managing organizations."""

    def __init__(
        self,
        org_repo: OrganizationRepository,
        workspace_repo: WorkspaceRepository,
        team_repo: TeamRepository,
        db: AsyncSession
    ):
        self.org_repo = org_repo
        self.workspace_repo = workspace_repo
        self.team_repo = team_repo
        self.db = db

    async def create_organization(self, name: str, created_by_user_id: Optional[int] = None) -> Organization:
        """Create a new organization."""
        # Check if organization with this name already exists
        existing = await self.org_repo.get_by_name(name)
        if existing:
            raise ConflictError(f"Organization '{name}' already exists")

        return await self.org_repo.create({
            'name': name,
            'created_by_user_id': created_by_user_id
        })

    async def get_organization(self, organization_id: int) -> Optional[Organization]:
        """Get organization by ID."""
        return await self.org_repo.get_by_id(organization_id)

    async def list_organizations(self, skip: int = 0, limit: int = 100) -> List[Organization]:
        """List all organizations."""
        return await self.org_repo.list_all_with_workspaces(skip, limit)

    async def update_organization(self, organization_id: int, name: str) -> Optional[Organization]:
        """Update organization details."""
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise NotFoundError(f"Organization {organization_id} not found")

        # Check if new name conflicts with existing organization
        if name != org.name:
            existing = await self.org_repo.get_by_name(name)
            if existing:
                raise ConflictError(f"Organization '{name}' already exists")

        return await self.org_repo.update(organization_id, {'name': name})

    async def add_workspace_to_organization(self, organization_id: int, workspace_id: int) -> Optional[Workspace]:
        """Add a workspace to an organization."""
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise NotFoundError(f"Organization {organization_id} not found")

        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundError(f"Workspace {workspace_id} not found")

        return await self.workspace_repo.update(workspace_id, {'organization_id': organization_id})

    async def remove_workspace_from_organization(self, workspace_id: int) -> Optional[Workspace]:
        """Remove a workspace from an organization."""
        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundError(f"Workspace {workspace_id} not found")

        return await self.workspace_repo.update(workspace_id, {'organization_id': None})

    async def get_organization_workspaces(self, organization_id: int) -> List[Workspace]:
        """Get all workspaces in an organization."""
        org = await self.org_repo.get_with_workspaces(organization_id)
        if not org:
            raise NotFoundError(f"Organization {organization_id} not found")
        return org.workspaces

    async def get_organization_teams(self, organization_id: int) -> List[Team]:
        """Get all teams in an organization."""
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise NotFoundError(f"Organization {organization_id} not found")

        # Get teams with organization_id set to this organization
        teams = [team for team in org.teams if team.organization_id == organization_id]
        return teams

    async def get_organization_users(self, organization_id: int) -> List[User]:
        """Get all users in an organization."""
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise NotFoundError(f"Organization {organization_id} not found")
        return org.users

    async def delete_organization(self, organization_id: int) -> bool:
        """Delete an organization."""
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise NotFoundError(f"Organization {organization_id} not found")

        return await self.org_repo.delete(organization_id)
