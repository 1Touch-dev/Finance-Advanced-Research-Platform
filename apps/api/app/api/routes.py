from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.models.models import Base, Organization, Workspace, User, Role, Permission, RolePermission, Membership, Project, Case, Invitation, AuditLog
from app.auth.security import (
    hash_password,
    verify_password,
    create_token,
    create_refresh_token,
    exchange_refresh_token,
    revoke_token,
)
from app.auth.oidc import oidc_provider
import secrets
from app.rbac.permissions import require_permission, Current

router = APIRouter()

@router.get('/health')
def health():
    return {"status": "ok"}

@router.post('/bootstrap')
def bootstrap(db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=db.get_bind())
    base_perms = [
        'org:create','workspace:create','workspace:invite','project:create','case:create',
        'member:read','member:manage','audit:read','entity:read','entity:export'
    ]
    for p in base_perms:
        if not db.query(Permission).filter_by(name=p).first():
            db.add(Permission(name=p))
    db.commit()
    return {"seeded_permissions": base_perms}

@router.post('/auth/register')
def register(email: str, password: str, name: Optional[str]=None, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(400, 'email exists')
    u = User(email=email, name=name, password_hash=hash_password(password))
    db.add(u); db.commit(); db.refresh(u)
    db.add(AuditLog(user_id=u.id, action='user.register', entity_type='user', entity_id=str(u.id)))
    db.commit()
    return {"id": u.id, "email": u.email}

@router.post('/auth/login')
def login(email: str, password: str, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=email).first()
    if not u or not u.password_hash or not verify_password(password, u.password_hash):
        raise HTTPException(401, 'invalid credentials')
    tok = create_token(u.id, u.email)
    refresh = create_refresh_token(u.id, u.email)
    db.add(AuditLog(user_id=u.id, action='auth.login', entity_type='user', entity_id=str(u.id)))
    db.commit()
    return {"token": tok, "refresh_token": refresh}

@router.post('/auth/refresh')
def refresh_auth(refresh_token: str):
    result = exchange_refresh_token(refresh_token)
    if not result:
        raise HTTPException(401, 'invalid refresh token')
    return result

@router.post('/auth/logout')
def logout(token: str):
    revoke_token(token)
    return {"ok": True}

@router.get('/auth/oidc/login')
def oidc_login():
    if not oidc_provider.configured():
        raise HTTPException(501, 'OIDC not configured — set OIDC_CLIENT_ID and OIDC_CLIENT_SECRET')
    state = secrets.token_urlsafe(16)
    return {"authorization_url": oidc_provider.authorization_url(state), "state": state}

@router.get('/auth/oidc/callback')
def oidc_callback(code: str, db: Session = Depends(get_db)):
    if not oidc_provider.configured():
        raise HTTPException(501, 'OIDC not configured')
    tokens = oidc_provider.exchange_code(code)
    userinfo = oidc_provider.get_userinfo(tokens["access_token"])
    email = userinfo.get("email")
    if not email:
        raise HTTPException(400, 'no email from OIDC provider')
    u = db.query(User).filter_by(email=email).first()
    if not u:
        u = User(email=email, name=userinfo.get("name"), password_hash=None)
        db.add(u)
        db.commit()
        db.refresh(u)
    tok = create_token(u.id, u.email)
    refresh = create_refresh_token(u.id, u.email)
    db.add(AuditLog(user_id=u.id, action='auth.oidc_login', entity_type='user', entity_id=str(u.id)))
    db.commit()
    return {"token": tok, "refresh_token": refresh, "email": email}

@router.post('/orgs')
def create_org(name: str, curr: Current = Depends(require_permission('org:create')), db: Session = Depends(get_db)):
    org = Organization(name=name)
    db.add(org); db.commit(); db.refresh(org)
    db.add(AuditLog(user_id=curr.user_id, org_id=org.id, action='org.create', entity_type='org', entity_id=str(org.id)))
    db.commit()
    return {"id": org.id, "name": org.name}

@router.post('/workspaces')
def create_workspace(org_id: int, name: str, curr: Current = Depends(require_permission('workspace:create')), db: Session = Depends(get_db)):
    ws = Workspace(org_id=org_id, name=name)
    db.add(ws); db.commit(); db.refresh(ws)
    roles = ['owner','admin','member','reviewer','guest']
    role_map = {}
    for r in roles:
        role_obj = Role(name=r, workspace_id=ws.id)
        db.add(role_obj); db.flush(); role_map[r] = role_obj
    perm_map = {p.name:p for p in db.query(Permission).all()}
    grants = {
        'owner': list(perm_map.keys()),
        'admin': [k for k in perm_map if not k.startswith('org:')],
        'member': ['project:create','case:create','entity:read'],
        'reviewer': ['entity:read'],
        'guest': ['entity:read']
    }
    for role_name, perms in grants.items():
        for p in perms:
            db.add(RolePermission(role_id=role_map[role_name].id, permission_id=perm_map[p].id))
    db.commit()
    db.add(AuditLog(user_id=curr.user_id, org_id=org_id, workspace_id=ws.id, action='workspace.create', entity_type='workspace', entity_id=str(ws.id)))
    db.commit()
    return {"id": ws.id, "name": ws.name}

@router.post('/workspaces/{workspace_id}/members')
def add_member(workspace_id: int, user_id: int, role_name: str, curr: Current = Depends(require_permission('member:manage')), db: Session = Depends(get_db)):
    role = db.query(Role).filter_by(workspace_id=workspace_id, name=role_name).first()
    if not role: raise HTTPException(404, 'role not found')
    m = Membership(user_id=user_id, workspace_id=workspace_id, role_id=role.id)
    db.add(m); db.commit(); db.refresh(m)
    db.add(AuditLog(user_id=curr.user_id, workspace_id=workspace_id, action='member.add', entity_type='membership', entity_id=str(m.id), meta={"added_user": user_id, "role": role_name}))
    db.commit()
    return {"id": m.id}

@router.post('/workspaces/{workspace_id}/projects')
def create_project(workspace_id: int, name: str, curr: Current = Depends(require_permission('project:create')), db: Session = Depends(get_db)):
    p = Project(workspace_id=workspace_id, name=name)
    db.add(p); db.commit(); db.refresh(p)
    db.add(AuditLog(user_id=curr.user_id, workspace_id=workspace_id, action='project.create', entity_type='project', entity_id=str(p.id)))
    db.commit()
    return {"id": p.id, "name": p.name}

@router.post('/workspaces/{workspace_id}/cases')
def create_case(workspace_id: int, title: str, curr: Current = Depends(require_permission('case:create')), db: Session = Depends(get_db)):
    c = Case(workspace_id=workspace_id, title=title)
    db.add(c); db.commit(); db.refresh(c)
    db.add(AuditLog(user_id=curr.user_id, workspace_id=workspace_id, action='case.create', entity_type='case', entity_id=str(c.id)))
    db.commit()
    return {"id": c.id, "title": c.title}

@router.get('/audit')
def query_audit(limit: int = 50, curr: Current = Depends(require_permission('audit:read')), db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.ts.desc()).limit(limit).all()
    return [
        {"id": r.id, "ts": r.ts.isoformat() if r.ts else None, "action": r.action, "entity_type": r.entity_type, "entity_id": r.entity_id, "user_id": r.user_id, "org_id": r.org_id, "workspace_id": r.workspace_id, "meta": r.meta}
        for r in rows
    ]
