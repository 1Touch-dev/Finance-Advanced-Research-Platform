"""
PWA Advanced Features API (E2, E3, E5)
Offline caching, WebAuthn, Screen sharing
"""
from fastapi import APIRouter, Query, Body, Depends
from typing import Optional

from app.auth.security import get_current_user

from app.services.pwa_advanced_service import (
    # E2: Offline Caching
    get_offline_config,
    register_cached_route,
    get_cached_routes,
    clear_cache,
    get_service_worker_config,
    # E3: WebAuthn
    start_webauthn_registration,
    complete_webauthn_registration,
    start_webauthn_login,
    verify_webauthn_login,
    get_biometric_status,
    # E5: Screen Sharing
    create_screen_session,
    join_screen_session,
    leave_screen_session,
    end_screen_session,
    get_active_sessions,
    get_session_info,
)

router = APIRouter(prefix="/pwa-advanced", tags=["PWA Advanced"])


# ========== E2: Offline Caching ==========

@router.get("/offline/config")
def offline_config():
    """E2: Get offline caching configuration."""
    return get_offline_config()


@router.get("/offline/sw-config")
def sw_config():
    """E2: Get service worker configuration."""
    return get_service_worker_config()


@router.post("/offline/cache")
def cache_route(
    user_id: str = Query(...),
    route: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """E2: Register a route for offline caching."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return register_cached_route(user_id, route)


@router.get("/offline/cached")
def cached_routes(user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """E2: Get all cached routes for a user."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return get_cached_routes(user_id)


@router.delete("/offline/cache")
def clear_user_cache(user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """E2: Clear all cached data for a user."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return clear_cache(user_id)


# ========== E3: WebAuthn / Biometric ==========

@router.post("/biometric/register/start")
def biometric_register_start(
    user_id: str = Query(...),
    username: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """E3: Start WebAuthn registration."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return start_webauthn_registration(user_id, username)


@router.post("/biometric/register/complete")
def biometric_register_complete(
    user_id: str = Query(...),
    credential_id: str = Body(...),
    public_key: str = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """E3: Complete WebAuthn registration."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return complete_webauthn_registration(user_id, credential_id, public_key)


@router.post("/biometric/login/start")
def biometric_login_start(user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """E3: Start WebAuthn login."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return start_webauthn_login(user_id)


@router.post("/biometric/login/verify")
def biometric_login_verify(
    user_id: str = Query(...),
    credential_id: str = Body(...),
    signature: str = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """E3: Verify WebAuthn login."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return verify_webauthn_login(user_id, credential_id, signature)


@router.get("/biometric/status")
def biometric_status(user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """E3: Get biometric authentication status."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return get_biometric_status(user_id)


# ========== E5: Screen Sharing ==========

@router.post("/screen/create")
def screen_create(
    user_id: str = Query(...),
    session_name: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """E5: Create a screen sharing session."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return create_screen_session(user_id, session_name)


@router.post("/screen/{session_id}/join")
def screen_join(session_id: str, user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """E5: Join a screen sharing session."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return join_screen_session(session_id, user_id)


@router.post("/screen/{session_id}/leave")
def screen_leave(session_id: str, user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """E5: Leave a screen sharing session."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return leave_screen_session(session_id, user_id)


@router.post("/screen/{session_id}/end")
def screen_end(session_id: str, user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """E5: End a screen sharing session."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return end_screen_session(session_id, user_id)


@router.get("/screen/active")
def screen_active(user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """E5: Get all active screen sharing sessions."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return get_active_sessions(user_id)


@router.get("/screen/{session_id}")
def screen_info(session_id: str):
    """E5: Get screen sharing session info."""
    return get_session_info(session_id)
