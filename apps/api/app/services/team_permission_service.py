"""
Team Permission Roles Service (Band C #49)
Admin/editor/viewer roles and permissions
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from enum import Enum
import uuid


class Permission(str, Enum):
    # Read permissions
    VIEW_WATCHLISTS = "view_watchlists"
    VIEW_DASHBOARDS = "view_dashboards"
    VIEW_REPORTS = "view_reports"
    VIEW_MEMBERS = "view_members"

    # Edit permissions
    EDIT_WATCHLISTS = "edit_watchlists"
    EDIT_DASHBOARDS = "edit_dashboards"
    CREATE_REPORTS = "create_reports"
    ADD_COMMENTS = "add_comments"

    # Admin permissions
    MANAGE_MEMBERS = "manage_members"
    MANAGE_ROLES = "manage_roles"
    DELETE_RESOURCES = "delete_resources"
    MANAGE_SETTINGS = "manage_settings"
    EXPORT_DATA = "export_data"

    # Owner permissions
    TRANSFER_OWNERSHIP = "transfer_ownership"
    DELETE_WORKSPACE = "delete_workspace"


# Role permission mappings
ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
    "viewer": {
        Permission.VIEW_WATCHLISTS,
        Permission.VIEW_DASHBOARDS,
        Permission.VIEW_REPORTS,
        Permission.VIEW_MEMBERS,
    },
    "editor": {
        Permission.VIEW_WATCHLISTS,
        Permission.VIEW_DASHBOARDS,
        Permission.VIEW_REPORTS,
        Permission.VIEW_MEMBERS,
        Permission.EDIT_WATCHLISTS,
        Permission.EDIT_DASHBOARDS,
        Permission.CREATE_REPORTS,
        Permission.ADD_COMMENTS,
        Permission.EXPORT_DATA,
    },
    "admin": {
        Permission.VIEW_WATCHLISTS,
        Permission.VIEW_DASHBOARDS,
        Permission.VIEW_REPORTS,
        Permission.VIEW_MEMBERS,
        Permission.EDIT_WATCHLISTS,
        Permission.EDIT_DASHBOARDS,
        Permission.CREATE_REPORTS,
        Permission.ADD_COMMENTS,
        Permission.MANAGE_MEMBERS,
        Permission.MANAGE_ROLES,
        Permission.DELETE_RESOURCES,
        Permission.MANAGE_SETTINGS,
        Permission.EXPORT_DATA,
    },
    "owner": {
        p for p in Permission
    },
}


@dataclass
class TeamMember:
    """Team member with role"""
    user_id: str
    email: str
    name: str
    role: str
    custom_permissions: Set[Permission] = field(default_factory=set)
    created_at: str = ""
    last_active: str = ""

    def get_permissions(self) -> Set[Permission]:
        """Get all permissions for this member"""
        base_perms = ROLE_PERMISSIONS.get(self.role, set())
        return base_perms | self.custom_permissions

    def has_permission(self, permission: Permission) -> bool:
        """Check if member has a specific permission"""
        return permission in self.get_permissions()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "permissions": [p.value for p in self.get_permissions()],
            "custom_permissions": [p.value for p in self.custom_permissions],
            "created_at": self.created_at,
            "last_active": self.last_active,
        }


@dataclass
class Team:
    """Team with members and permissions"""
    team_id: str
    name: str
    owner_id: str
    members: List[TeamMember] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "name": self.name,
            "owner_id": self.owner_id,
            "members": [m.to_dict() for m in self.members],
            "member_count": len(self.members),
            "created_at": self.created_at,
        }


# Mock teams
TEAMS: Dict[str, Team] = {
    "TEAM001": Team(
        team_id="TEAM001",
        name="Research Team",
        owner_id="demo_user",
        created_at="2024-01-15T10:00:00Z",
        members=[
            TeamMember("demo_user", "owner@example.com", "Demo Owner", "owner", set(), "2024-01-15T10:00:00Z", "2024-08-17T09:00:00Z"),
            TeamMember("user_admin", "admin@example.com", "Admin User", "admin", set(), "2024-01-20T10:00:00Z", "2024-08-16T15:00:00Z"),
            TeamMember("user_editor", "editor@example.com", "Editor User", "editor", set(), "2024-02-01T10:00:00Z", "2024-08-17T08:00:00Z"),
            TeamMember("user_viewer", "viewer@example.com", "Viewer User", "viewer", set(), "2024-02-15T10:00:00Z", "2024-08-15T12:00:00Z"),
        ],
    ),
}


def get_roles() -> List[Dict[str, Any]]:
    """Get all available roles with their permissions"""
    roles = []
    for role_name, permissions in ROLE_PERMISSIONS.items():
        roles.append({
            "role": role_name,
            "permissions": [p.value for p in permissions],
            "permission_count": len(permissions),
            "description": _get_role_description(role_name),
        })
    return roles


def _get_role_description(role: str) -> str:
    """Get role description"""
    descriptions = {
        "viewer": "Can view all resources but cannot make changes",
        "editor": "Can view and edit resources, create reports",
        "admin": "Full access except ownership transfer and deletion",
        "owner": "Full access including ownership transfer",
    }
    return descriptions.get(role, "")


def get_permissions() -> List[Dict[str, Any]]:
    """Get all available permissions"""
    return [
        {"permission": p.value, "category": _get_permission_category(p)}
        for p in Permission
    ]


def _get_permission_category(permission: Permission) -> str:
    """Get permission category"""
    if "view" in permission.value:
        return "read"
    elif any(x in permission.value for x in ["edit", "create", "add"]):
        return "write"
    elif any(x in permission.value for x in ["manage", "delete", "transfer"]):
        return "admin"
    return "other"


def create_team(owner_id: str, name: str) -> Dict[str, Any]:
    """Create a new team"""
    team_id = f"TEAM{str(uuid.uuid4())[:6].upper()}"
    now = datetime.now().isoformat() + "Z"

    team = Team(
        team_id=team_id,
        name=name,
        owner_id=owner_id,
        created_at=now,
        members=[
            TeamMember(
                user_id=owner_id,
                email=f"{owner_id}@example.com",
                name=owner_id.replace("_", " ").title(),
                role="owner",
                created_at=now,
                last_active=now,
            )
        ],
    )
    TEAMS[team_id] = team
    return team.to_dict()


def get_team(team_id: str) -> Optional[Dict[str, Any]]:
    """Get team by ID"""
    team = TEAMS.get(team_id)
    return team.to_dict() if team else None


def get_user_teams(user_id: str) -> List[Dict[str, Any]]:
    """Get all teams for a user"""
    results = []
    for team in TEAMS.values():
        for member in team.members:
            if member.user_id == user_id:
                team_dict = team.to_dict()
                team_dict["user_role"] = member.role
                results.append(team_dict)
                break
    return results


def add_team_member(
    team_id: str,
    user_id: str,
    email: str,
    name: str,
    role: str,
) -> Dict[str, Any]:
    """Add member to team"""
    team = TEAMS.get(team_id)
    if not team:
        return {"error": "Team not found"}

    if role not in ROLE_PERMISSIONS:
        return {"error": f"Invalid role: {role}"}

    # Check if already member
    for member in team.members:
        if member.user_id == user_id:
            return {"error": "User is already a member"}

    now = datetime.now().isoformat() + "Z"
    member = TeamMember(
        user_id=user_id,
        email=email,
        name=name,
        role=role,
        created_at=now,
        last_active=now,
    )
    team.members.append(member)
    return {"success": True, "member": member.to_dict()}


def remove_team_member(team_id: str, user_id: str) -> Dict[str, Any]:
    """Remove member from team"""
    team = TEAMS.get(team_id)
    if not team:
        return {"error": "Team not found"}

    for member in team.members:
        if member.user_id == user_id:
            if member.role == "owner":
                return {"error": "Cannot remove team owner"}
            team.members.remove(member)
            return {"success": True}

    return {"error": "Member not found"}


def update_member_role(
    team_id: str,
    user_id: str,
    new_role: str,
) -> Dict[str, Any]:
    """Update member's role"""
    team = TEAMS.get(team_id)
    if not team:
        return {"error": "Team not found"}

    if new_role not in ROLE_PERMISSIONS:
        return {"error": f"Invalid role: {new_role}"}

    for member in team.members:
        if member.user_id == user_id:
            if member.role == "owner":
                return {"error": "Cannot change owner role directly"}
            member.role = new_role
            return {"success": True, "member": member.to_dict()}

    return {"error": "Member not found"}


def add_custom_permission(
    team_id: str,
    user_id: str,
    permission: Permission,
) -> Dict[str, Any]:
    """Add custom permission to a member"""
    team = TEAMS.get(team_id)
    if not team:
        return {"error": "Team not found"}

    for member in team.members:
        if member.user_id == user_id:
            member.custom_permissions.add(permission)
            return {"success": True, "member": member.to_dict()}

    return {"error": "Member not found"}


def remove_custom_permission(
    team_id: str,
    user_id: str,
    permission: Permission,
) -> Dict[str, Any]:
    """Remove custom permission from a member"""
    team = TEAMS.get(team_id)
    if not team:
        return {"error": "Team not found"}

    for member in team.members:
        if member.user_id == user_id:
            member.custom_permissions.discard(permission)
            return {"success": True, "member": member.to_dict()}

    return {"error": "Member not found"}


def check_permission(
    team_id: str,
    user_id: str,
    permission: Permission,
) -> Dict[str, Any]:
    """Check if user has a specific permission"""
    team = TEAMS.get(team_id)
    if not team:
        return {"error": "Team not found", "has_permission": False}

    for member in team.members:
        if member.user_id == user_id:
            return {
                "has_permission": member.has_permission(permission),
                "role": member.role,
                "permission": permission.value,
            }

    return {"error": "Member not found", "has_permission": False}


def get_member_permissions(team_id: str, user_id: str) -> Dict[str, Any]:
    """Get all permissions for a team member"""
    team = TEAMS.get(team_id)
    if not team:
        return {"error": "Team not found"}

    for member in team.members:
        if member.user_id == user_id:
            permissions = member.get_permissions()
            return {
                "user_id": user_id,
                "role": member.role,
                "permissions": [p.value for p in permissions],
                "custom_permissions": [p.value for p in member.custom_permissions],
                "can_edit": Permission.EDIT_WATCHLISTS in permissions,
                "can_manage": Permission.MANAGE_MEMBERS in permissions,
                "is_admin": member.role in ["admin", "owner"],
            }

    return {"error": "Member not found"}


def transfer_ownership(team_id: str, current_owner: str, new_owner: str) -> Dict[str, Any]:
    """Transfer team ownership"""
    team = TEAMS.get(team_id)
    if not team:
        return {"error": "Team not found"}

    if team.owner_id != current_owner:
        return {"error": "Only owner can transfer ownership"}

    # Find members
    current_owner_member = None
    new_owner_member = None

    for member in team.members:
        if member.user_id == current_owner:
            current_owner_member = member
        elif member.user_id == new_owner:
            new_owner_member = member

    if not new_owner_member:
        return {"error": "New owner must be a team member"}

    # Transfer
    current_owner_member.role = "admin"
    new_owner_member.role = "owner"
    team.owner_id = new_owner

    return {"success": True, "new_owner": new_owner_member.to_dict()}
