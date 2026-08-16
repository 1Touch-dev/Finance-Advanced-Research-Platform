"""
Shared Workspaces Service (Band C #48)
Team collaboration spaces
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


@dataclass
class WorkspaceMember:
    """Workspace member"""
    user_id: str
    email: str
    name: str
    role: WorkspaceRole
    joined_at: str
    invited_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "role": self.role.value,
            "joined_at": self.joined_at,
            "invited_by": self.invited_by,
        }


@dataclass
class Workspace:
    """Shared workspace"""
    workspace_id: str
    name: str
    description: str
    owner_id: str
    created_at: str
    members: List[WorkspaceMember] = field(default_factory=list)
    watchlists: List[str] = field(default_factory=list)
    dashboards: List[str] = field(default_factory=list)
    reports: List[str] = field(default_factory=list)
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "created_at": self.created_at,
            "members": [m.to_dict() for m in self.members],
            "member_count": len(self.members),
            "watchlists": self.watchlists,
            "dashboards": self.dashboards,
            "reports": self.reports,
            "is_active": self.is_active,
        }


# Mock workspaces
WORKSPACES: Dict[str, Workspace] = {
    "WS001": Workspace(
        workspace_id="WS001",
        name="Research Team",
        description="Collaborative research workspace for the equity team",
        owner_id="demo_user",
        created_at="2024-01-15T10:30:00Z",
        members=[
            WorkspaceMember("demo_user", "demo@example.com", "Demo User", WorkspaceRole.OWNER, "2024-01-15T10:30:00Z"),
            WorkspaceMember("user_2", "analyst@example.com", "Jane Analyst", WorkspaceRole.EDITOR, "2024-01-20T14:00:00Z", "demo_user"),
            WorkspaceMember("user_3", "viewer@example.com", "Bob Viewer", WorkspaceRole.VIEWER, "2024-02-01T09:00:00Z", "demo_user"),
        ],
        watchlists=["WL001", "WL002"],
        dashboards=["DASH001"],
        reports=["RPT001", "RPT002"],
    ),
    "WS002": Workspace(
        workspace_id="WS002",
        name="Trading Desk",
        description="Real-time trading collaboration",
        owner_id="user_2",
        created_at="2024-02-10T08:00:00Z",
        members=[
            WorkspaceMember("user_2", "trader@example.com", "Jane Trader", WorkspaceRole.OWNER, "2024-02-10T08:00:00Z"),
            WorkspaceMember("demo_user", "demo@example.com", "Demo User", WorkspaceRole.EDITOR, "2024-02-15T11:00:00Z", "user_2"),
        ],
        watchlists=["WL003"],
        dashboards=["DASH002"],
        reports=[],
    ),
}


def create_workspace(
    owner_id: str,
    name: str,
    description: str = "",
) -> Dict[str, Any]:
    """Create a new workspace"""
    workspace_id = f"WS{str(uuid.uuid4())[:8].upper()}"
    now = datetime.now().isoformat() + "Z"

    workspace = Workspace(
        workspace_id=workspace_id,
        name=name,
        description=description,
        owner_id=owner_id,
        created_at=now,
        members=[
            WorkspaceMember(
                user_id=owner_id,
                email=f"{owner_id}@example.com",
                name=owner_id.replace("_", " ").title(),
                role=WorkspaceRole.OWNER,
                joined_at=now,
            )
        ],
    )
    WORKSPACES[workspace_id] = workspace
    return workspace.to_dict()


def get_workspace(workspace_id: str) -> Optional[Dict[str, Any]]:
    """Get workspace by ID"""
    workspace = WORKSPACES.get(workspace_id)
    return workspace.to_dict() if workspace else None


def get_user_workspaces(user_id: str) -> List[Dict[str, Any]]:
    """Get all workspaces for a user"""
    results = []
    for workspace in WORKSPACES.values():
        for member in workspace.members:
            if member.user_id == user_id:
                ws_dict = workspace.to_dict()
                ws_dict["user_role"] = member.role.value
                results.append(ws_dict)
                break
    return results


def add_member(
    workspace_id: str,
    user_id: str,
    email: str,
    name: str,
    role: WorkspaceRole,
    invited_by: str,
) -> Dict[str, Any]:
    """Add a member to workspace"""
    workspace = WORKSPACES.get(workspace_id)
    if not workspace:
        return {"error": "Workspace not found"}

    # Check if already member
    for member in workspace.members:
        if member.user_id == user_id:
            return {"error": "User is already a member"}

    member = WorkspaceMember(
        user_id=user_id,
        email=email,
        name=name,
        role=role,
        joined_at=datetime.now().isoformat() + "Z",
        invited_by=invited_by,
    )
    workspace.members.append(member)
    return {"success": True, "member": member.to_dict()}


def remove_member(workspace_id: str, user_id: str) -> Dict[str, Any]:
    """Remove a member from workspace"""
    workspace = WORKSPACES.get(workspace_id)
    if not workspace:
        return {"error": "Workspace not found"}

    # Can't remove owner
    for member in workspace.members:
        if member.user_id == user_id:
            if member.role == WorkspaceRole.OWNER:
                return {"error": "Cannot remove workspace owner"}
            workspace.members.remove(member)
            return {"success": True}

    return {"error": "Member not found"}


def update_member_role(
    workspace_id: str,
    user_id: str,
    new_role: WorkspaceRole,
) -> Dict[str, Any]:
    """Update member's role"""
    workspace = WORKSPACES.get(workspace_id)
    if not workspace:
        return {"error": "Workspace not found"}

    for member in workspace.members:
        if member.user_id == user_id:
            if member.role == WorkspaceRole.OWNER:
                return {"error": "Cannot change owner role"}
            member.role = new_role
            return {"success": True, "member": member.to_dict()}

    return {"error": "Member not found"}


def add_resource(
    workspace_id: str,
    resource_type: str,  # watchlist, dashboard, report
    resource_id: str,
) -> Dict[str, Any]:
    """Add a resource to workspace"""
    workspace = WORKSPACES.get(workspace_id)
    if not workspace:
        return {"error": "Workspace not found"}

    if resource_type == "watchlist":
        if resource_id not in workspace.watchlists:
            workspace.watchlists.append(resource_id)
    elif resource_type == "dashboard":
        if resource_id not in workspace.dashboards:
            workspace.dashboards.append(resource_id)
    elif resource_type == "report":
        if resource_id not in workspace.reports:
            workspace.reports.append(resource_id)
    else:
        return {"error": "Invalid resource type"}

    return {"success": True, "workspace": workspace.to_dict()}


def remove_resource(
    workspace_id: str,
    resource_type: str,
    resource_id: str,
) -> Dict[str, Any]:
    """Remove a resource from workspace"""
    workspace = WORKSPACES.get(workspace_id)
    if not workspace:
        return {"error": "Workspace not found"}

    if resource_type == "watchlist" and resource_id in workspace.watchlists:
        workspace.watchlists.remove(resource_id)
    elif resource_type == "dashboard" and resource_id in workspace.dashboards:
        workspace.dashboards.remove(resource_id)
    elif resource_type == "report" and resource_id in workspace.reports:
        workspace.reports.remove(resource_id)
    else:
        return {"error": "Resource not found"}

    return {"success": True}


def update_workspace(
    workspace_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Update workspace details"""
    workspace = WORKSPACES.get(workspace_id)
    if not workspace:
        return {"error": "Workspace not found"}

    if name:
        workspace.name = name
    if description is not None:
        workspace.description = description

    return workspace.to_dict()


def delete_workspace(workspace_id: str) -> Dict[str, Any]:
    """Delete a workspace"""
    if workspace_id not in WORKSPACES:
        return {"error": "Workspace not found"}

    del WORKSPACES[workspace_id]
    return {"success": True}


def get_workspace_activity(workspace_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent activity in workspace"""
    # Mock activity data
    activities = [
        {"type": "member_joined", "user": "Jane Analyst", "timestamp": "2024-08-16T14:30:00Z"},
        {"type": "watchlist_updated", "user": "Demo User", "resource": "Tech Watchlist", "timestamp": "2024-08-16T12:00:00Z"},
        {"type": "report_shared", "user": "Demo User", "resource": "Q3 Analysis", "timestamp": "2024-08-15T16:45:00Z"},
        {"type": "dashboard_created", "user": "Jane Analyst", "resource": "Market Overview", "timestamp": "2024-08-15T10:00:00Z"},
        {"type": "comment_added", "user": "Bob Viewer", "resource": "NVDA Analysis", "timestamp": "2024-08-14T09:30:00Z"},
    ]
    return activities[:limit]
