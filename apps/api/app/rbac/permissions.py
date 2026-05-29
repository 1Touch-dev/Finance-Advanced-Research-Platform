from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.auth.security import decode_token
from app.models.models import Membership, Role, Permission, RolePermission, Workspace

# ABAC hook placeholder

def abac_check(subject: dict, action: str, resource: dict) -> bool:
    return True

class Current:
    def __init__(self, user_id: int, email: str):
        self.user_id = user_id
        self.email = email

async def get_current_user(authorization: Optional[str] = None) -> Current:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ",1)[1]
    payload = decode_token(token)
    return Current(user_id=int(payload["sub"]), email=payload.get("email"))

def require_permission(perm_name: str):
    async def checker(curr: Current = Depends(get_current_user), db: Session = Depends(get_db), workspace_id: Optional[int] = None):
        q = (
            db.query(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(Membership, Membership.role_id == Role.id)
            .filter(Permission.name == perm_name, Membership.user_id == curr.user_id)
        )
        if workspace_id:
            q = q.join(Workspace, Workspace.id == Membership.workspace_id).filter(Workspace.id == workspace_id)
        ok = db.query(q.exists()).scalar()
        if not ok:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {perm_name}")
        return curr
    return checker
