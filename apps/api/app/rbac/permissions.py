from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.auth.security import get_current_user as _get_current_user_dict
from app.models.models import Membership, Role, Permission, RolePermission, Workspace

# ABAC hook placeholder

def abac_check(subject: dict, action: str, resource: dict) -> bool:
    return True

class Current:
    def __init__(self, user_id: int, email: str):
        self.user_id = user_id
        self.email = email


async def get_current_user(
    principal: dict = Depends(_get_current_user_dict),
) -> Current:
    """Adapt the canonical Authorization-header dependency to the RBAC ``Current`` shape.

    Delegating rather than re-implementing matters here: the previous signature was
    ``authorization: Optional[str] = None``, which FastAPI resolves as a *query*
    parameter. The header was therefore never read (every call 401'd) and the only
    way through was ``?authorization=Bearer+<token>``, i.e. tokens in URLs and logs.
    """
    return Current(user_id=principal["user_id"], email=principal.get("email"))

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
