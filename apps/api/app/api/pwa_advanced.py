"""
PWA Advanced Features API (E2, E3, E5)
Offline caching, WebAuthn, Screen sharing
"""
from fastapi import APIRouter, Query, Body
from typing import Optional

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
async def offline_config():
    """E2: Get offline caching configuration."""
    return get_offline_config()


@router.get("/offline/sw-config")
async def sw_config():
    """E2: Get service worker configuration."""
    return get_service_worker_config()


@router.post("/offline/cache")
async def cache_route(
    user_id: str = Query(...),
    route: str = Query(...)
):
    """E2: Register a route for offline caching."""
    return register_cached_route(user_id, route)


@router.get("/offline/cached")
async def cached_routes(user_id: str = Query(...)):
    """E2: Get all cached routes for a user."""
    return get_cached_routes(user_id)


@router.delete("/offline/cache")
async def clear_user_cache(user_id: str = Query(...)):
    """E2: Clear all cached data for a user."""
    return clear_cache(user_id)


# ========== E3: WebAuthn / Biometric ==========

@router.post("/biometric/register/start")
async def biometric_register_start(
    user_id: str = Query(...),
    username: str = Query(...)
):
    """E3: Start WebAuthn registration."""
    return start_webauthn_registration(user_id, username)


@router.post("/biometric/register/complete")
async def biometric_register_complete(
    user_id: str = Query(...),
    credential_id: str = Body(...),
    public_key: str = Body(...)
):
    """E3: Complete WebAuthn registration."""
    return complete_webauthn_registration(user_id, credential_id, public_key)


@router.post("/biometric/login/start")
async def biometric_login_start(user_id: str = Query(...)):
    """E3: Start WebAuthn login."""
    return start_webauthn_login(user_id)


@router.post("/biometric/login/verify")
async def biometric_login_verify(
    user_id: str = Query(...),
    credential_id: str = Body(...),
    signature: str = Body(...)
):
    """E3: Verify WebAuthn login."""
    return verify_webauthn_login(user_id, credential_id, signature)


@router.get("/biometric/status")
async def biometric_status(user_id: str = Query(...)):
    """E3: Get biometric authentication status."""
    return get_biometric_status(user_id)


# ========== E5: Screen Sharing ==========

@router.post("/screen/create")
async def screen_create(
    user_id: str = Query(...),
    session_name: Optional[str] = Query(None)
):
    """E5: Create a screen sharing session."""
    return create_screen_session(user_id, session_name)


@router.post("/screen/{session_id}/join")
async def screen_join(session_id: str, user_id: str = Query(...)):
    """E5: Join a screen sharing session."""
    return join_screen_session(session_id, user_id)


@router.post("/screen/{session_id}/leave")
async def screen_leave(session_id: str, user_id: str = Query(...)):
    """E5: Leave a screen sharing session."""
    return leave_screen_session(session_id, user_id)


@router.post("/screen/{session_id}/end")
async def screen_end(session_id: str, user_id: str = Query(...)):
    """E5: End a screen sharing session."""
    return end_screen_session(session_id, user_id)


@router.get("/screen/active")
async def screen_active(user_id: str = Query(...)):
    """E5: Get all active screen sharing sessions."""
    return get_active_sessions(user_id)


@router.get("/screen/{session_id}")
async def screen_info(session_id: str):
    """E5: Get screen sharing session info."""
    return get_session_info(session_id)
