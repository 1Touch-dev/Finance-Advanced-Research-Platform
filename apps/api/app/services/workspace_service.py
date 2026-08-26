"""
Shared Workspaces Service (Band C #48)
Real CRUD backed by SQLAlchemy models.
"""
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.session import get_db_context
from app.models.models import Workspace, Membership, Role, AuditLog, Organization, User
from app.core.no_data import no_data_response, NoDataReason

logger = logging.getLogger(__name__)


class WorkspaceRole(str, Enum):
    owner = "owner"
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


def _parse_id(id_str: str) -> Optional[int]:
    """Safely parse an ID string to integer."""
    if id_str is None:
        return None
    try:
        return int(id_str)
    except (ValueError, TypeError):
        return None


def _ws_to_dict(ws: Workspace) -> Dict[str, Any]:
    """Convert Workspace model to dictionary."""
    return {
        "id": ws.id,
        "org_id": ws.org_id,
        "name": ws.name,
        "skill_budget_usd": ws.skill_budget_usd,
        "skill_spend_usd": ws.skill_spend_usd,
    }


def _membership_to_dict(m: Membership, db) -> Dict[str, Any]:
    """Convert Membership model to dictionary with role info."""
    role = db.query(Role).filter(Role.id == m.role_id).first()
    user = db.query(User).filter(User.id == m.user_id).first()
    return {
        "id": m.id,
        "user_id": m.user_id,
        "email": user.email if user else None,
        "name": user.name if user else None,
        "workspace_id": m.workspace_id,
        "role": role.name if role else "unknown",
    }


def create_workspace(
    owner_id: str,
    name: str,
    description: str = "",
) -> Dict[str, Any]:
    """Create a new workspace and add owner as first member."""
    uid = _parse_id(owner_id)
    if uid is None:
        return {
            "status": "error",
            "reason": "Invalid owner_id",
            **no_data_response(
                owner_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                source="workspace_service", details="owner_id must be a valid integer"
            ),
        }

    try:
        with get_db_context() as db:
            # Verify owner exists
            owner = db.query(User).filter(User.id == uid).first()
            if not owner:
                return {
                    "status": "error",
                    "reason": "Owner not found",
                    **no_data_response(
                        owner_id, "user", NoDataReason.ENTITY_NOT_FOUND,
                        source="workspace_service", details=f"User with id {owner_id} does not exist"
                    ),
                }

            # Get or create default organization
            org = db.query(Organization).first()
            if not org:
                org = Organization(name="default")
                db.add(org)
                db.flush()

            # Create workspace
            ws = Workspace(org_id=org.id, name=name)
            db.add(ws)
            db.flush()

            # Create owner role for this workspace
            owner_role = Role(name="owner", workspace_id=ws.id)
            db.add(owner_role)
            db.flush()

            # Add owner as first member
            membership = Membership(
                user_id=uid,
                workspace_id=ws.id,
                role_id=owner_role.id,
            )
            db.add(membership)

            # Audit log
            log = AuditLog(
                user_id=uid,
                workspace_id=ws.id,
                action="workspace_created",
                entity_type="workspace",
                entity_id=str(ws.id),
                meta={"name": name, "description": description},
            )
            db.add(log)
            db.commit()
            db.refresh(ws)

            logger.info(f"Workspace '{name}' (id={ws.id}) created by user {uid}")
            return {"status": "created", **_ws_to_dict(ws)}

    except SQLAlchemyError as e:
        logger.error(f"Database error creating workspace: {e}")
        return {
            "status": "error",
            "reason": "Database error",
            **no_data_response(
                name, "workspace", NoDataReason.API_ERROR,
                source="workspace_service", details=str(e)
            ),
        }


def get_workspace(workspace_id: str) -> Optional[Dict[str, Any]]:
    """Get workspace by ID."""
    ws_id = _parse_id(workspace_id)
    if ws_id is None:
        return {
            "status": "error",
            "reason": "Invalid workspace_id",
            **no_data_response(
                workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                source="workspace_service", details="workspace_id must be a valid integer"
            ),
        }

    try:
        with get_db_context() as db:
            ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
            if not ws:
                return {
                    "status": "error",
                    "reason": "Workspace not found",
                    **no_data_response(
                        workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                        source="workspace_service", details=f"Workspace with id {workspace_id} does not exist"
                    ),
                }

            result = _ws_to_dict(ws)
            members = db.query(Membership).filter(Membership.workspace_id == ws.id).all()
            result["members"] = [_membership_to_dict(m, db) for m in members]
            return result

    except SQLAlchemyError as e:
        logger.error(f"Database error getting workspace {workspace_id}: {e}")
        return {
            "status": "error",
            "reason": "Database error",
            **no_data_response(
                workspace_id, "workspace", NoDataReason.API_ERROR,
                source="workspace_service", details=str(e)
            ),
        }


def get_user_workspaces(user_id: str) -> List[Dict[str, Any]]:
    """Get all workspaces where user is a member."""
    uid = _parse_id(user_id)
    if uid is None:
        return []

    try:
        with get_db_context() as db:
            memberships = db.query(Membership).filter(Membership.user_id == uid).all()
            ws_ids = [m.workspace_id for m in memberships]
            if not ws_ids:
                return []
            workspaces = db.query(Workspace).filter(Workspace.id.in_(ws_ids)).all()
            return [_ws_to_dict(ws) for ws in workspaces]

    except SQLAlchemyError as e:
        logger.error(f"Database error getting workspaces for user {user_id}: {e}")
        return []


def add_member(
    workspace_id: str,
    user_id: str,
    email: str,
    name: str,
    role: "WorkspaceRole",
    invited_by: str,
) -> Dict[str, Any]:
    """Add a member to workspace with the given role."""
    ws_id = _parse_id(workspace_id)
    uid = _parse_id(user_id)
    inviter_id = _parse_id(invited_by)

    if ws_id is None:
        return {
            "status": "error",
            "reason": "Invalid workspace_id",
            **no_data_response(
                workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                source="workspace_service", details="workspace_id must be a valid integer"
            ),
        }

    if uid is None:
        return {
            "status": "error",
            "reason": "Invalid user_id",
            **no_data_response(
                user_id, "user", NoDataReason.ENTITY_NOT_FOUND,
                source="workspace_service", details="user_id must be a valid integer"
            ),
        }

    try:
        with get_db_context() as db:
            # Verify workspace exists
            ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
            if not ws:
                return {
                    "status": "error",
                    "reason": "Workspace not found",
                    **no_data_response(
                        workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                        source="workspace_service", details=f"Workspace with id {workspace_id} does not exist"
                    ),
                }

            # Verify user exists
            user = db.query(User).filter(User.id == uid).first()
            if not user:
                return {
                    "status": "error",
                    "reason": "User not found",
                    **no_data_response(
                        user_id, "user", NoDataReason.ENTITY_NOT_FOUND,
                        source="workspace_service", details=f"User with id {user_id} does not exist"
                    ),
                }

            # Get or create role
            role_obj = db.query(Role).filter(
                Role.workspace_id == ws_id, Role.name == role.value
            ).first()
            if not role_obj:
                role_obj = Role(name=role.value, workspace_id=ws_id)
                db.add(role_obj)
                db.flush()

            # Create membership
            membership = Membership(user_id=uid, workspace_id=ws_id, role_id=role_obj.id)
            db.add(membership)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                return {"status": "error", "reason": "User already a member of this workspace"}

            # Audit log
            log = AuditLog(
                user_id=inviter_id,
                workspace_id=ws_id,
                action="member_added",
                entity_type="membership",
                entity_id=str(membership.id),
                meta={"role": role.value, "invited_user_id": uid, "invited_by": invited_by},
            )
            db.add(log)
            db.commit()

            logger.info(f"User {uid} added to workspace {ws_id} with role {role.value}")
            return {"status": "added", "user_id": uid, "workspace_id": ws_id, "role": role.value}

    except SQLAlchemyError as e:
        logger.error(f"Database error adding member to workspace: {e}")
        return {
            "status": "error",
            "reason": "Database error",
            **no_data_response(
                workspace_id, "membership", NoDataReason.API_ERROR,
                source="workspace_service", details=str(e)
            ),
        }


def remove_member(workspace_id: str, user_id: str) -> Dict[str, Any]:
    """Remove a member from workspace."""
    ws_id = _parse_id(workspace_id)
    uid = _parse_id(user_id)

    if ws_id is None:
        return {
            "status": "error",
            "reason": "Invalid workspace_id",
            **no_data_response(
                workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                source="workspace_service", details="workspace_id must be a valid integer"
            ),
        }

    if uid is None:
        return {
            "status": "error",
            "reason": "Invalid user_id",
            **no_data_response(
                user_id, "user", NoDataReason.ENTITY_NOT_FOUND,
                source="workspace_service", details="user_id must be a valid integer"
            ),
        }

    try:
        with get_db_context() as db:
            membership = db.query(Membership).filter(
                Membership.workspace_id == ws_id, Membership.user_id == uid
            ).first()
            if not membership:
                return {
                    "status": "error",
                    "reason": "Membership not found",
                    **no_data_response(
                        f"{user_id}@{workspace_id}", "membership", NoDataReason.ENTITY_NOT_FOUND,
                        source="workspace_service", details="User is not a member of this workspace"
                    ),
                }

            db.delete(membership)

            log = AuditLog(
                user_id=uid,
                workspace_id=ws_id,
                action="member_removed",
                entity_type="membership",
            )
            db.add(log)
            db.commit()

            logger.info(f"User {uid} removed from workspace {ws_id}")
            return {"status": "removed", "user_id": uid, "workspace_id": ws_id}

    except SQLAlchemyError as e:
        logger.error(f"Database error removing member from workspace: {e}")
        return {
            "status": "error",
            "reason": "Database error",
            **no_data_response(
                workspace_id, "membership", NoDataReason.API_ERROR,
                source="workspace_service", details=str(e)
            ),
        }


def update_member_role(
    workspace_id: str,
    user_id: str,
    new_role: "WorkspaceRole",
) -> Dict[str, Any]:
    """Update member's role in workspace."""
    ws_id = _parse_id(workspace_id)
    uid = _parse_id(user_id)

    if ws_id is None:
        return {
            "status": "error",
            "reason": "Invalid workspace_id",
            **no_data_response(
                workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                source="workspace_service", details="workspace_id must be a valid integer"
            ),
        }

    if uid is None:
        return {
            "status": "error",
            "reason": "Invalid user_id",
            **no_data_response(
                user_id, "user", NoDataReason.ENTITY_NOT_FOUND,
                source="workspace_service", details="user_id must be a valid integer"
            ),
        }

    try:
        with get_db_context() as db:
            membership = db.query(Membership).filter(
                Membership.workspace_id == ws_id, Membership.user_id == uid
            ).first()
            if not membership:
                return {
                    "status": "error",
                    "reason": "Membership not found",
                    **no_data_response(
                        f"{user_id}@{workspace_id}", "membership", NoDataReason.ENTITY_NOT_FOUND,
                        source="workspace_service", details="User is not a member of this workspace"
                    ),
                }

            # Get or create role
            role_obj = db.query(Role).filter(
                Role.workspace_id == ws_id, Role.name == new_role.value
            ).first()
            if not role_obj:
                role_obj = Role(name=new_role.value, workspace_id=ws_id)
                db.add(role_obj)
                db.flush()

            old_role_id = membership.role_id
            membership.role_id = role_obj.id

            log = AuditLog(
                user_id=uid,
                workspace_id=ws_id,
                action="role_updated",
                entity_type="membership",
                meta={"new_role": new_role.value, "old_role_id": old_role_id},
            )
            db.add(log)
            db.commit()

            logger.info(f"User {uid} role updated to {new_role.value} in workspace {ws_id}")
            return {"status": "updated", "user_id": uid, "workspace_id": ws_id, "role": new_role.value}

    except SQLAlchemyError as e:
        logger.error(f"Database error updating member role: {e}")
        return {
            "status": "error",
            "reason": "Database error",
            **no_data_response(
                workspace_id, "membership", NoDataReason.API_ERROR,
                source="workspace_service", details=str(e)
            ),
        }


def add_resource(
    workspace_id: str,
    resource_type: str,
    resource_id: str,
) -> Dict[str, Any]:
    """Add a resource to workspace (logged via audit)."""
    ws_id = _parse_id(workspace_id)

    if ws_id is None:
        return {
            "status": "error",
            "reason": "Invalid workspace_id",
            **no_data_response(
                workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                source="workspace_service", details="workspace_id must be a valid integer"
            ),
        }

    try:
        with get_db_context() as db:
            # Verify workspace exists
            ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
            if not ws:
                return {
                    "status": "error",
                    "reason": "Workspace not found",
                    **no_data_response(
                        workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                        source="workspace_service", details=f"Workspace with id {workspace_id} does not exist"
                    ),
                }

            log = AuditLog(
                workspace_id=ws_id,
                action="resource_added",
                entity_type=resource_type,
                entity_id=resource_id,
            )
            db.add(log)
            db.commit()

            logger.info(f"Resource {resource_type}:{resource_id} added to workspace {ws_id}")
            return {"status": "added", "workspace_id": ws_id, "resource_type": resource_type, "resource_id": resource_id}

    except SQLAlchemyError as e:
        logger.error(f"Database error adding resource to workspace: {e}")
        return {
            "status": "error",
            "reason": "Database error",
            **no_data_response(
                workspace_id, "resource", NoDataReason.API_ERROR,
                source="workspace_service", details=str(e)
            ),
        }


def remove_resource(
    workspace_id: str,
    resource_type: str,
    resource_id: str,
) -> Dict[str, Any]:
    """Remove a resource from workspace (logged via audit)."""
    ws_id = _parse_id(workspace_id)

    if ws_id is None:
        return {
            "status": "error",
            "reason": "Invalid workspace_id",
            **no_data_response(
                workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                source="workspace_service", details="workspace_id must be a valid integer"
            ),
        }

    try:
        with get_db_context() as db:
            # Verify workspace exists
            ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
            if not ws:
                return {
                    "status": "error",
                    "reason": "Workspace not found",
                    **no_data_response(
                        workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                        source="workspace_service", details=f"Workspace with id {workspace_id} does not exist"
                    ),
                }

            log = AuditLog(
                workspace_id=ws_id,
                action="resource_removed",
                entity_type=resource_type,
                entity_id=resource_id,
            )
            db.add(log)
            db.commit()

            logger.info(f"Resource {resource_type}:{resource_id} removed from workspace {ws_id}")
            return {"status": "removed", "workspace_id": ws_id, "resource_type": resource_type, "resource_id": resource_id}

    except SQLAlchemyError as e:
        logger.error(f"Database error removing resource from workspace: {e}")
        return {
            "status": "error",
            "reason": "Database error",
            **no_data_response(
                workspace_id, "resource", NoDataReason.API_ERROR,
                source="workspace_service", details=str(e)
            ),
        }


def update_workspace(
    workspace_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Update workspace details."""
    ws_id = _parse_id(workspace_id)

    if ws_id is None:
        return {
            "status": "error",
            "reason": "Invalid workspace_id",
            **no_data_response(
                workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                source="workspace_service", details="workspace_id must be a valid integer"
            ),
        }

    try:
        with get_db_context() as db:
            ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
            if not ws:
                return {
                    "status": "error",
                    "reason": "Workspace not found",
                    **no_data_response(
                        workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                        source="workspace_service", details=f"Workspace with id {workspace_id} does not exist"
                    ),
                }

            changes = {}
            if name is not None:
                changes["old_name"] = ws.name
                changes["new_name"] = name
                ws.name = name

            log = AuditLog(
                workspace_id=ws.id,
                action="workspace_updated",
                entity_type="workspace",
                entity_id=str(ws.id),
                meta={"changes": changes, "description": description},
            )
            db.add(log)
            db.commit()
            db.refresh(ws)

            logger.info(f"Workspace {ws_id} updated")
            return {"status": "updated", **_ws_to_dict(ws)}

    except SQLAlchemyError as e:
        logger.error(f"Database error updating workspace: {e}")
        return {
            "status": "error",
            "reason": "Database error",
            **no_data_response(
                workspace_id, "workspace", NoDataReason.API_ERROR,
                source="workspace_service", details=str(e)
            ),
        }


def delete_workspace(workspace_id: str) -> Dict[str, Any]:
    """Delete a workspace and its memberships."""
    ws_id = _parse_id(workspace_id)

    if ws_id is None:
        return {
            "status": "error",
            "reason": "Invalid workspace_id",
            **no_data_response(
                workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                source="workspace_service", details="workspace_id must be a valid integer"
            ),
        }

    try:
        with get_db_context() as db:
            ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
            if not ws:
                return {
                    "status": "error",
                    "reason": "Workspace not found",
                    **no_data_response(
                        workspace_id, "workspace", NoDataReason.ENTITY_NOT_FOUND,
                        source="workspace_service", details=f"Workspace with id {workspace_id} does not exist"
                    ),
                }

            ws_name = ws.name

            # Delete related records first
            db.query(Membership).filter(Membership.workspace_id == ws_id).delete()
            db.query(Role).filter(Role.workspace_id == ws_id).delete()
            db.delete(ws)

            # Audit log (note: workspace_id will be orphaned after commit)
            log = AuditLog(
                workspace_id=ws_id,
                action="workspace_deleted",
                entity_type="workspace",
                entity_id=str(ws_id),
                meta={"name": ws_name},
            )
            db.add(log)
            db.commit()

            logger.info(f"Workspace {ws_id} ({ws_name}) deleted")
            return {"status": "deleted", "workspace_id": ws_id, "name": ws_name}

    except SQLAlchemyError as e:
        logger.error(f"Database error deleting workspace: {e}")
        return {
            "status": "error",
            "reason": "Database error",
            **no_data_response(
                workspace_id, "workspace", NoDataReason.API_ERROR,
                source="workspace_service", details=str(e)
            ),
        }


def get_workspace_activity(workspace_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent activity in workspace from audit_logs."""
    ws_id = _parse_id(workspace_id)

    if ws_id is None:
        return []

    try:
        with get_db_context() as db:
            # Verify workspace exists
            ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
            if not ws:
                return []

            logs = (
                db.query(AuditLog)
                .filter(AuditLog.workspace_id == ws_id)
                .order_by(AuditLog.ts.desc())
                .limit(limit)
                .all()
            )

            result = []
            for log in logs:
                user = None
                if log.user_id:
                    user = db.query(User).filter(User.id == log.user_id).first()

                result.append({
                    "id": log.id,
                    "timestamp": log.ts.isoformat() if log.ts else None,
                    "user_id": log.user_id,
                    "user_email": user.email if user else None,
                    "user_name": user.name if user else None,
                    "action": log.action,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                    "meta": log.meta,
                })

            return result

    except SQLAlchemyError as e:
        logger.error(f"Database error getting workspace activity: {e}")
        return []


def list_all_workspaces(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """List all workspaces (admin function)."""
    try:
        with get_db_context() as db:
            total = db.query(Workspace).count()
            workspaces = (
                db.query(Workspace)
                .order_by(Workspace.id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return {
                "status": "ok",
                "total": total,
                "limit": limit,
                "offset": offset,
                "workspaces": [_ws_to_dict(ws) for ws in workspaces],
            }

    except SQLAlchemyError as e:
        logger.error(f"Database error listing workspaces: {e}")
        return {
            "status": "error",
            "reason": "Database error",
            **no_data_response(
                "all", "workspaces", NoDataReason.API_ERROR,
                source="workspace_service", details=str(e)
            ),
        }
