"""
Team Permission Roles API (#49)
"""

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/teams", tags=["Teams"])

try:
    from ..services.team_permission_service import (
        get_roles,
        get_permissions,
        create_team,
        get_team,
        get_user_teams,
        add_team_member,
        remove_team_member,
        update_member_role,
        add_custom_permission,
        remove_custom_permission,
        check_permission,
        get_member_permissions,
        transfer_ownership,
        Permission,
    )
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False


@router.get("/roles")
def api_get_roles():
    """Get all available roles"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"roles": get_roles()}


@router.get("/permissions")
def api_get_permissions():
    """Get all available permissions"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"permissions": get_permissions()}


@router.get("/")
def api_get_user_teams(
    user_id: str = Query(default="demo_user"),
):
    """Get all teams for user"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"teams": get_user_teams(user_id)}


@router.post("/")
def api_create_team(
    name: str,
    user_id: str = Query(default="demo_user"),
):
    """Create a new team"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return create_team(user_id, name)


@router.get("/{team_id}")
def api_get_team(team_id: str):
    """Get team by ID"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    team = get_team(team_id)
    return team if team else {"error": "Team not found"}


@router.post("/{team_id}/members")
def api_add_member(
    team_id: str,
    user_id: str,
    email: str,
    name: str,
    role: str = Query(default="viewer"),
):
    """Add member to team"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return add_team_member(team_id, user_id, email, name, role)


@router.delete("/{team_id}/members/{user_id}")
def api_remove_member(
    team_id: str,
    user_id: str,
):
    """Remove member from team"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return remove_team_member(team_id, user_id)


@router.put("/{team_id}/members/{user_id}/role")
def api_update_role(
    team_id: str,
    user_id: str,
    role: str,
):
    """Update member's role"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return update_member_role(team_id, user_id, role)


@router.post("/{team_id}/members/{user_id}/permissions")
def api_add_permission(
    team_id: str,
    user_id: str,
    permission: str,
):
    """Add custom permission to member"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    try:
        perm = Permission(permission)
    except ValueError:
        return {"error": f"Invalid permission: {permission}"}
    return add_custom_permission(team_id, user_id, perm)


@router.delete("/{team_id}/members/{user_id}/permissions/{permission}")
def api_remove_permission(
    team_id: str,
    user_id: str,
    permission: str,
):
    """Remove custom permission from member"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    try:
        perm = Permission(permission)
    except ValueError:
        return {"error": f"Invalid permission: {permission}"}
    return remove_custom_permission(team_id, user_id, perm)


@router.get("/{team_id}/members/{user_id}/check")
def api_check_permission(
    team_id: str,
    user_id: str,
    permission: str,
):
    """Check if user has specific permission"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    try:
        perm = Permission(permission)
    except ValueError:
        return {"error": f"Invalid permission: {permission}"}
    return check_permission(team_id, user_id, perm)


@router.get("/{team_id}/members/{user_id}/permissions")
def api_get_member_permissions(
    team_id: str,
    user_id: str,
):
    """Get all permissions for a member"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_member_permissions(team_id, user_id)


@router.post("/{team_id}/transfer-ownership")
def api_transfer_ownership(
    team_id: str,
    new_owner_id: str,
    current_owner_id: str = Query(default="demo_user"),
):
    """Transfer team ownership"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return transfer_ownership(team_id, current_owner_id, new_owner_id)
