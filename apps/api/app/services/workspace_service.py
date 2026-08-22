"""
Shared Workspaces Service (Band C #48)
Real CRUD backed by SQLAlchemy models.
"""
from typing import List, Optional, Dict, Any
from enum import Enum

from sqlalchemy.exc import IntegrityError

from app.db.session import get_db_context
from app.models.models import Workspace, Membership, Role, AuditLog, Organization


class WorkspaceRole(str, Enum):
    owner = "owner"
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


def _ws_to_dict(ws: Workspace) -> Dict[str, Any]:
    return {
        "id": ws.id,
        "org_id": ws.org_id,
        "name": ws.name,
        "skill_budget_usd": ws.skill_budget_usd,
        "skill_spend_usd": ws.skill_spend_usd,
    }


def _membership_to_dict(m: Membership, db) -> Dict[str, Any]:
    role = db.query(Role).filter(Role.id == m.role_id).first()
    return {
        "id": m.id,
        "user_id": m.user_id,
        "workspace_id": m.workspace_id,
        "role": role.name if role else "unknown",
    }


def create_workspace(
    owner_id: str,
    name: str,
    description: str = "",
) -> Dict[str, Any]:
    """Create a new workspace and add owner as first member."""
    with get_db_context() as db:
        org = db.query(Organization).first()
        if not org:
            org = Organization(name="default")
            db.add(org)
            db.flush()

        ws = Workspace(org_id=org.id, name=name)
        db.add(ws)
        db.flush()

        owner_role = db.query(Role).filter(
            Role.workspace_id == ws.id, Role.name == "owner"
        ).first()
        if not owner_role:
            owner_role = Role(name="owner", workspace_id=ws.id)
            db.add(owner_role)
            db.flush()

        membership = Membership(
            user_id=int(owner_id) if owner_id.isdigit() else 1,
            workspace_id=ws.id,
            role_id=owner_role.id,
        )
        db.add(membership)

        log = AuditLog(
            user_id=int(owner_id) if owner_id.isdigit() else None,
            workspace_id=ws.id,
            action="workspace_created",
            entity_type="workspace",
            entity_id=str(ws.id),
            meta={"name": name},
        )
        db.add(log)
        db.commit()
        db.refresh(ws)
        return {"status": "created", **_ws_to_dict(ws)}


def get_workspace(workspace_id: str) -> Optional[Dict[str, Any]]:
    """Get workspace by ID."""
    with get_db_context() as db:
        ws = db.query(Workspace).filter(Workspace.id == int(workspace_id)).first()
        if not ws:
            return None
        result = _ws_to_dict(ws)
        members = db.query(Membership).filter(Membership.workspace_id == ws.id).all()
        result["members"] = [_membership_to_dict(m, db) for m in members]
        return result


def get_user_workspaces(user_id: str) -> List[Dict[str, Any]]:
    """Get all workspaces where user is a member."""
    with get_db_context() as db:
        uid = int(user_id) if user_id.isdigit() else 0
        memberships = db.query(Membership).filter(Membership.user_id == uid).all()
        ws_ids = [m.workspace_id for m in memberships]
        if not ws_ids:
            return []
        workspaces = db.query(Workspace).filter(Workspace.id.in_(ws_ids)).all()
        return [_ws_to_dict(ws) for ws in workspaces]


def add_member(
    workspace_id: str,
    user_id: str,
    email: str,
    name: str,
    role: "WorkspaceRole",
    invited_by: str,
) -> Dict[str, Any]:
    """Add a member to workspace with the given role."""
    with get_db_context() as db:
        ws_id = int(workspace_id)
        uid = int(user_id) if user_id.isdigit() else 0

        role_obj = db.query(Role).filter(
            Role.workspace_id == ws_id, Role.name == role.value
        ).first()
        if not role_obj:
            role_obj = Role(name=role.value, workspace_id=ws_id)
            db.add(role_obj)
            db.flush()

        membership = Membership(user_id=uid, workspace_id=ws_id, role_id=role_obj.id)
        db.add(membership)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return {"status": "error", "reason": "User already a member of this workspace"}

        log = AuditLog(
            user_id=uid,
            workspace_id=ws_id,
            action="member_added",
            entity_type="membership",
            meta={"role": role.value, "invited_by": invited_by},
        )
        db.add(log)
        db.commit()
        return {"status": "added", "user_id": uid, "workspace_id": ws_id, "role": role.value}


def remove_member(workspace_id: str, user_id: str) -> Dict[str, Any]:
    """Remove a member from workspace."""
    with get_db_context() as db:
        ws_id = int(workspace_id)
        uid = int(user_id) if user_id.isdigit() else 0
        membership = db.query(Membership).filter(
            Membership.workspace_id == ws_id, Membership.user_id == uid
        ).first()
        if not membership:
            return {"status": "error", "reason": "Membership not found"}
        db.delete(membership)

        log = AuditLog(
            user_id=uid,
            workspace_id=ws_id,
            action="member_removed",
            entity_type="membership",
        )
        db.add(log)
        db.commit()
        return {"status": "removed", "user_id": uid, "workspace_id": ws_id}


def update_member_role(
    workspace_id: str,
    user_id: str,
    new_role: "WorkspaceRole",
) -> Dict[str, Any]:
    """Update member's role in workspace."""
    with get_db_context() as db:
        ws_id = int(workspace_id)
        uid = int(user_id) if user_id.isdigit() else 0
        membership = db.query(Membership).filter(
            Membership.workspace_id == ws_id, Membership.user_id == uid
        ).first()
        if not membership:
            return {"status": "error", "reason": "Membership not found"}

        role_obj = db.query(Role).filter(
            Role.workspace_id == ws_id, Role.name == new_role.value
        ).first()
        if not role_obj:
            role_obj = Role(name=new_role.value, workspace_id=ws_id)
            db.add(role_obj)
            db.flush()

        membership.role_id = role_obj.id

        log = AuditLog(
            user_id=uid,
            workspace_id=ws_id,
            action="role_updated",
            entity_type="membership",
            meta={"new_role": new_role.value},
        )
        db.add(log)
        db.commit()
        return {"status": "updated", "user_id": uid, "workspace_id": ws_id, "role": new_role.value}


def add_resource(
    workspace_id: str,
    resource_type: str,
    resource_id: str,
) -> Dict[str, Any]:
    """Add a resource to workspace (logged via audit)."""
    with get_db_context() as db:
        ws_id = int(workspace_id)
        log = AuditLog(
            workspace_id=ws_id,
            action="resource_added",
            entity_type=resource_type,
            entity_id=resource_id,
        )
        db.add(log)
        db.commit()
        return {"status": "added", "workspace_id": ws_id, "resource_type": resource_type, "resource_id": resource_id}


def remove_resource(
    workspace_id: str,
    resource_type: str,
    resource_id: str,
) -> Dict[str, Any]:
    """Remove a resource from workspace (logged via audit)."""
    with get_db_context() as db:
        ws_id = int(workspace_id)
        log = AuditLog(
            workspace_id=ws_id,
            action="resource_removed",
            entity_type=resource_type,
            entity_id=resource_id,
        )
        db.add(log)
        db.commit()
        return {"status": "removed", "workspace_id": ws_id, "resource_type": resource_type, "resource_id": resource_id}


def update_workspace(
    workspace_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Update workspace details."""
    with get_db_context() as db:
        ws = db.query(Workspace).filter(Workspace.id == int(workspace_id)).first()
        if not ws:
            return {"status": "error", "reason": "Workspace not found"}
        if name is not None:
            ws.name = name

        log = AuditLog(
            workspace_id=ws.id,
            action="workspace_updated",
            entity_type="workspace",
            entity_id=str(ws.id),
            meta={"name": name},
        )
        db.add(log)
        db.commit()
        db.refresh(ws)
        return {"status": "updated", **_ws_to_dict(ws)}


def delete_workspace(workspace_id: str) -> Dict[str, Any]:
    """Delete a workspace and its memberships."""
    with get_db_context() as db:
        ws_id = int(workspace_id)
        ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
        if not ws:
            return {"status": "error", "reason": "Workspace not found"}

        db.query(Membership).filter(Membership.workspace_id == ws_id).delete()
        db.query(Role).filter(Role.workspace_id == ws_id).delete()
        db.delete(ws)

        log = AuditLog(
            workspace_id=ws_id,
            action="workspace_deleted",
            entity_type="workspace",
            entity_id=str(ws_id),
        )
        db.add(log)
        db.commit()
        return {"status": "deleted", "workspace_id": ws_id}


def get_workspace_activity(workspace_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent activity in workspace from audit_logs."""
    with get_db_context() as db:
        ws_id = int(workspace_id)
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.workspace_id == ws_id)
            .order_by(AuditLog.ts.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": log.id,
                "timestamp": log.ts.isoformat() if log.ts else None,
                "user_id": log.user_id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "meta": log.meta,
            }
            for log in logs
        ]
