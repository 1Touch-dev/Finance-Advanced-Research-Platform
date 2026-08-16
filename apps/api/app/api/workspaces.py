"""
Shared Workspaces API (#48)
"""

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])

try:
    from ..services.workspace_service import (
        create_workspace,
        get_workspace,
        get_user_workspaces,
        add_member,
        remove_member,
        update_member_role,
        add_resource,
        remove_resource,
        update_workspace,
        delete_workspace,
        get_workspace_activity,
        WorkspaceRole,
    )
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False


@router.get("/")
def api_get_user_workspaces(
    user_id: str = Query(default="demo_user"),
):
    """Get all workspaces for user"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"workspaces": get_user_workspaces(user_id)}


@router.post("/")
def api_create_workspace(
    name: str,
    description: str = "",
    user_id: str = Query(default="demo_user"),
):
    """Create a new workspace"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return create_workspace(user_id, name, description)


@router.get("/{workspace_id}")
def api_get_workspace(workspace_id: str):
    """Get workspace by ID"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    workspace = get_workspace(workspace_id)
    return workspace if workspace else {"error": "Workspace not found"}


@router.put("/{workspace_id}")
def api_update_workspace(
    workspace_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
):
    """Update workspace details"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return update_workspace(workspace_id, name, description)


@router.delete("/{workspace_id}")
def api_delete_workspace(workspace_id: str):
    """Delete a workspace"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return delete_workspace(workspace_id)


@router.post("/{workspace_id}/members")
def api_add_member(
    workspace_id: str,
    user_id: str,
    email: str,
    name: str,
    role: str = Query(default="viewer"),
    invited_by: str = Query(default="demo_user"),
):
    """Add member to workspace"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    try:
        role_enum = WorkspaceRole(role)
    except ValueError:
        return {"error": f"Invalid role: {role}"}
    return add_member(workspace_id, user_id, email, name, role_enum, invited_by)


@router.delete("/{workspace_id}/members/{user_id}")
def api_remove_member(
    workspace_id: str,
    user_id: str,
):
    """Remove member from workspace"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return remove_member(workspace_id, user_id)


@router.put("/{workspace_id}/members/{user_id}/role")
def api_update_member_role(
    workspace_id: str,
    user_id: str,
    role: str,
):
    """Update member's role"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    try:
        role_enum = WorkspaceRole(role)
    except ValueError:
        return {"error": f"Invalid role: {role}"}
    return update_member_role(workspace_id, user_id, role_enum)


@router.post("/{workspace_id}/resources")
def api_add_resource(
    workspace_id: str,
    resource_type: str,
    resource_id: str,
):
    """Add resource to workspace"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return add_resource(workspace_id, resource_type, resource_id)


@router.delete("/{workspace_id}/resources/{resource_type}/{resource_id}")
def api_remove_resource(
    workspace_id: str,
    resource_type: str,
    resource_id: str,
):
    """Remove resource from workspace"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return remove_resource(workspace_id, resource_type, resource_id)


@router.get("/{workspace_id}/activity")
def api_get_activity(
    workspace_id: str,
    limit: int = Query(default=20),
):
    """Get workspace activity"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"activity": get_workspace_activity(workspace_id, limit)}
