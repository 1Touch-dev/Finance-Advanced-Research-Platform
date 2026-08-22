"""
Team Permission Roles Service (Band C #49)
Real CRUD backed by SQLAlchemy models.
"""
from typing import List, Optional, Dict, Any
from enum import Enum

from sqlalchemy.exc import IntegrityError

from app.db.session import get_db_context
from app.models.models import Role, Permission as PermModel, RolePermission, Membership, Workspace


class Permission(str, Enum):
    read = "read"
    write = "write"
    delete = "delete"
    admin = "admin"
    invite = "invite"
    manage_roles = "manage_roles"
    manage_billing = "manage_billing"
    export = "export"


def _role_to_dict(role: Role, db) -> Dict[str, Any]:
    rps = db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
    perm_ids = [rp.permission_id for rp in rps]
    perms = []
    if perm_ids:
        perm_objs = db.query(PermModel).filter(PermModel.id.in_(perm_ids)).all()
        perms = [p.name for p in perm_objs]
    return {
        "id": role.id,
        "name": role.name,
        "workspace_id": role.workspace_id,
        "permissions": perms,
    }


def get_roles() -> List[Dict[str, Any]]:
    """Get all available roles with their permissions."""
    with get_db_context() as db:
        roles = db.query(Role).all()
        return [_role_to_dict(r, db) for r in roles]


def get_permissions() -> List[Dict[str, Any]]:
    """Get all available permissions."""
    with get_db_context() as db:
        perms = db.query(PermModel).all()
        return [{"id": p.id, "name": p.name} for p in perms]


def create_team(owner_id: str, name: str) -> Dict[str, Any]:
    """Create a new team (role) in the first workspace for the user, or a specified workspace."""
    with get_db_context() as db:
        uid = int(owner_id) if owner_id.isdigit() else 0
        membership = db.query(Membership).filter(Membership.user_id == uid).first()
        if membership:
            ws_id = membership.workspace_id
        else:
            ws = db.query(Workspace).first()
            if not ws:
                return {"status": "error", "reason": "No workspace available"}
            ws_id = ws.id

        role = Role(name=name, workspace_id=ws_id)
        db.add(role)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return {"status": "error", "reason": f"Team/role '{name}' already exists in workspace"}
        db.refresh(role)
        return {"status": "created", **_role_to_dict(role, db)}


def get_team(team_id: str) -> Optional[Dict[str, Any]]:
    """Get team (role) by ID."""
    with get_db_context() as db:
        role = db.query(Role).filter(Role.id == int(team_id)).first()
        if not role:
            return None
        result = _role_to_dict(role, db)
        members = db.query(Membership).filter(Membership.role_id == role.id).all()
        result["members"] = [
            {"id": m.id, "user_id": m.user_id, "workspace_id": m.workspace_id}
            for m in members
        ]
        return result


def get_user_teams(user_id: str) -> List[Dict[str, Any]]:
    """Get all teams (roles) a user belongs to."""
    with get_db_context() as db:
        uid = int(user_id) if user_id.isdigit() else 0
        memberships = db.query(Membership).filter(Membership.user_id == uid).all()
        role_ids = list({m.role_id for m in memberships})
        if not role_ids:
            return []
        roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
        return [_role_to_dict(r, db) for r in roles]


def add_team_member(
    team_id: str,
    user_id: str,
    email: str,
    name: str,
    role: str,
) -> Dict[str, Any]:
    """Add member to team (assigns role via membership)."""
    with get_db_context() as db:
        role_obj = db.query(Role).filter(Role.id == int(team_id)).first()
        if not role_obj:
            return {"status": "error", "reason": "Team/role not found"}

        uid = int(user_id) if user_id.isdigit() else 0
        membership = Membership(
            user_id=uid,
            workspace_id=role_obj.workspace_id,
            role_id=role_obj.id,
        )
        db.add(membership)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return {"status": "error", "reason": "User already a member of this workspace"}
        return {"status": "added", "user_id": uid, "team_id": int(team_id), "role": role_obj.name}


def remove_team_member(team_id: str, user_id: str) -> Dict[str, Any]:
    """Remove member from team."""
    with get_db_context() as db:
        uid = int(user_id) if user_id.isdigit() else 0
        membership = db.query(Membership).filter(
            Membership.role_id == int(team_id), Membership.user_id == uid
        ).first()
        if not membership:
            return {"status": "error", "reason": "Membership not found"}
        db.delete(membership)
        db.commit()
        return {"status": "removed", "user_id": uid, "team_id": int(team_id)}


def update_member_role(
    team_id: str,
    user_id: str,
    new_role: str,
) -> Dict[str, Any]:
    """Update member's role within the workspace."""
    with get_db_context() as db:
        uid = int(user_id) if user_id.isdigit() else 0
        current_role = db.query(Role).filter(Role.id == int(team_id)).first()
        if not current_role:
            return {"status": "error", "reason": "Team/role not found"}

        membership = db.query(Membership).filter(
            Membership.role_id == current_role.id, Membership.user_id == uid
        ).first()
        if not membership:
            return {"status": "error", "reason": "Membership not found"}

        new_role_obj = db.query(Role).filter(
            Role.workspace_id == current_role.workspace_id, Role.name == new_role
        ).first()
        if not new_role_obj:
            new_role_obj = Role(name=new_role, workspace_id=current_role.workspace_id)
            db.add(new_role_obj)
            db.flush()

        membership.role_id = new_role_obj.id
        db.commit()
        return {"status": "updated", "user_id": uid, "new_role": new_role, "team_id": new_role_obj.id}


def add_custom_permission(
    team_id: str,
    user_id: str,
    permission: "Permission",
) -> Dict[str, Any]:
    """Add a permission to the team's role."""
    with get_db_context() as db:
        role_id = int(team_id)
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            return {"status": "error", "reason": "Team/role not found"}

        perm = db.query(PermModel).filter(PermModel.name == permission.value).first()
        if not perm:
            perm = PermModel(name=permission.value)
            db.add(perm)
            db.flush()

        rp = RolePermission(role_id=role_id, permission_id=perm.id)
        db.add(rp)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return {"status": "error", "reason": "Permission already assigned to this role"}
        return {"status": "added", "team_id": role_id, "permission": permission.value}


def remove_custom_permission(
    team_id: str,
    user_id: str,
    permission: "Permission",
) -> Dict[str, Any]:
    """Remove a permission from the team's role."""
    with get_db_context() as db:
        role_id = int(team_id)
        perm = db.query(PermModel).filter(PermModel.name == permission.value).first()
        if not perm:
            return {"status": "error", "reason": "Permission not found"}

        rp = db.query(RolePermission).filter(
            RolePermission.role_id == role_id, RolePermission.permission_id == perm.id
        ).first()
        if not rp:
            return {"status": "error", "reason": "Permission not assigned to this role"}
        db.delete(rp)
        db.commit()
        return {"status": "removed", "team_id": role_id, "permission": permission.value}


def check_permission(
    team_id: str,
    user_id: str,
    permission: "Permission",
) -> Dict[str, Any]:
    """Check if a role has a specific permission."""
    with get_db_context() as db:
        role_id = int(team_id)
        perm = db.query(PermModel).filter(PermModel.name == permission.value).first()
        if not perm:
            return {"has_permission": False, "permission": permission.value}

        rp = db.query(RolePermission).filter(
            RolePermission.role_id == role_id, RolePermission.permission_id == perm.id
        ).first()
        return {"has_permission": rp is not None, "permission": permission.value, "team_id": role_id}


def get_member_permissions(team_id: str, user_id: str) -> Dict[str, Any]:
    """Get all permissions for a team member's role."""
    with get_db_context() as db:
        role_id = int(team_id)
        rps = db.query(RolePermission).filter(RolePermission.role_id == role_id).all()
        perm_ids = [rp.permission_id for rp in rps]
        perms = []
        if perm_ids:
            perm_objs = db.query(PermModel).filter(PermModel.id.in_(perm_ids)).all()
            perms = [p.name for p in perm_objs]
        return {"team_id": role_id, "user_id": user_id, "permissions": perms}


def transfer_ownership(team_id: str, current_owner: str, new_owner: str) -> Dict[str, Any]:
    """Transfer team ownership by swapping role assignments."""
    with get_db_context() as db:
        role = db.query(Role).filter(Role.id == int(team_id)).first()
        if not role:
            return {"status": "error", "reason": "Team/role not found"}

        current_uid = int(current_owner) if current_owner.isdigit() else 0
        new_uid = int(new_owner) if new_owner.isdigit() else 0

        current_membership = db.query(Membership).filter(
            Membership.role_id == role.id, Membership.user_id == current_uid
        ).first()
        if not current_membership:
            return {"status": "error", "reason": "Current owner not found in team"}

        new_membership = db.query(Membership).filter(
            Membership.role_id == role.id, Membership.user_id == new_uid
        ).first()
        if not new_membership:
            return {"status": "error", "reason": "New owner not found in team"}

        owner_role = db.query(Role).filter(
            Role.workspace_id == role.workspace_id, Role.name == "owner"
        ).first()
        if owner_role:
            new_membership.role_id = owner_role.id
            current_membership.role_id = role.id
        db.commit()
        return {"status": "transferred", "team_id": int(team_id), "new_owner": new_uid}
