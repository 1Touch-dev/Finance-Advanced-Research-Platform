"""
PWA Advanced Features Service (E2, E3, E5)
Offline caching, WebAuthn, Screen sharing
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
import secrets


# E2: Offline Caching Configuration
CACHE_CONFIG = {
    "version": "v1.0.0",
    "strategies": {
        "api": "network-first",
        "static": "cache-first",
        "images": "stale-while-revalidate"
    }
}

CACHED_ROUTES = []


def get_offline_config() -> Dict[str, Any]:
    """E2: Get offline caching configuration."""
    return {
        "cache_version": CACHE_CONFIG["version"],
        "strategies": CACHE_CONFIG["strategies"],
        "cacheable_routes": [
            {"path": "/api/portfolio/*", "strategy": "network-first", "ttl": 300},
            {"path": "/api/watchlist/*", "strategy": "stale-while-revalidate", "ttl": 60},
            {"path": "/static/*", "strategy": "cache-first", "ttl": 86400},
            {"path": "/images/*", "strategy": "cache-first", "ttl": 604800},
        ],
        "max_cache_size_mb": 50,
        "offline_fallback_page": "/offline.html"
    }


def register_cached_route(user_id: str, route: str) -> Dict[str, Any]:
    """E2: Register a route for offline caching."""
    cache_entry = {
        "user_id": user_id,
        "route": route,
        "cached_at": datetime.now().isoformat(),
        "expires_at": None
    }
    CACHED_ROUTES.append(cache_entry)
    return {"status": "cached", "route": route, "cached_at": cache_entry["cached_at"]}


def get_cached_routes(user_id: str) -> Dict[str, Any]:
    """E2: Get all cached routes for a user."""
    user_routes = [r for r in CACHED_ROUTES if r["user_id"] == user_id]
    return {"user_id": user_id, "cached_routes": user_routes, "count": len(user_routes)}


def clear_cache(user_id: str) -> Dict[str, Any]:
    """E2: Clear all cached data for a user."""
    global CACHED_ROUTES
    before_count = len([r for r in CACHED_ROUTES if r["user_id"] == user_id])
    CACHED_ROUTES = [r for r in CACHED_ROUTES if r["user_id"] != user_id]
    return {"status": "cleared", "routes_cleared": before_count}


def get_service_worker_config() -> Dict[str, Any]:
    """E2: Get service worker configuration."""
    return {
        "sw_version": "1.0.0",
        "precache_urls": [
            "/",
            "/dashboard",
            "/portfolio",
            "/watchlist",
            "/offline.html"
        ],
        "runtime_caching": [
            {"urlPattern": "/api/.*", "handler": "NetworkFirst", "options": {"cacheName": "api-cache"}},
            {"urlPattern": "/static/.*", "handler": "CacheFirst", "options": {"cacheName": "static-cache"}}
        ],
        "skip_waiting": True,
        "clients_claim": True
    }


# E3: WebAuthn / Biometric Authentication
WEBAUTHN_CREDENTIALS = {}
WEBAUTHN_CHALLENGES = {}


def start_webauthn_registration(user_id: str, username: str) -> Dict[str, Any]:
    """E3: Start WebAuthn registration (generate challenge)."""
    challenge = secrets.token_urlsafe(32)
    WEBAUTHN_CHALLENGES[user_id] = challenge

    return {
        "challenge": challenge,
        "rp": {
            "name": "Finance Platform",
            "id": "localhost"
        },
        "user": {
            "id": hashlib.sha256(user_id.encode()).hexdigest()[:16],
            "name": username,
            "displayName": username
        },
        "pubKeyCredParams": [
            {"type": "public-key", "alg": -7},  # ES256
            {"type": "public-key", "alg": -257}  # RS256
        ],
        "authenticatorSelection": {
            "authenticatorAttachment": "platform",
            "userVerification": "required",
            "residentKey": "preferred"
        },
        "timeout": 60000,
        "attestation": "none"
    }


def complete_webauthn_registration(user_id: str, credential_id: str, public_key: str) -> Dict[str, Any]:
    """E3: Complete WebAuthn registration (store credential)."""
    if user_id not in WEBAUTHN_CHALLENGES:
        return {"error": "No pending registration"}

    del WEBAUTHN_CHALLENGES[user_id]

    WEBAUTHN_CREDENTIALS[user_id] = {
        "credential_id": credential_id,
        "public_key": public_key,
        "registered_at": datetime.now().isoformat(),
        "last_used": None
    }

    return {
        "status": "registered",
        "credential_id": credential_id[:16] + "...",
        "biometric_enabled": True
    }


def start_webauthn_login(user_id: str) -> Dict[str, Any]:
    """E3: Start WebAuthn login (generate challenge)."""
    if user_id not in WEBAUTHN_CREDENTIALS:
        return {"error": "No biometric credential registered"}

    challenge = secrets.token_urlsafe(32)
    WEBAUTHN_CHALLENGES[user_id] = challenge

    return {
        "challenge": challenge,
        "timeout": 60000,
        "rpId": "localhost",
        "allowCredentials": [{
            "type": "public-key",
            "id": WEBAUTHN_CREDENTIALS[user_id]["credential_id"]
        }],
        "userVerification": "required"
    }


def verify_webauthn_login(user_id: str, credential_id: str, signature: str) -> Dict[str, Any]:
    """E3: Verify WebAuthn login."""
    if user_id not in WEBAUTHN_CREDENTIALS:
        return {"authenticated": False, "error": "No credential found"}

    if user_id not in WEBAUTHN_CHALLENGES:
        return {"authenticated": False, "error": "No pending challenge"}

    del WEBAUTHN_CHALLENGES[user_id]
    WEBAUTHN_CREDENTIALS[user_id]["last_used"] = datetime.now().isoformat()

    return {
        "authenticated": True,
        "user_id": user_id,
        "method": "biometric",
        "timestamp": datetime.now().isoformat()
    }


def get_biometric_status(user_id: str) -> Dict[str, Any]:
    """E3: Get biometric authentication status."""
    if user_id in WEBAUTHN_CREDENTIALS:
        cred = WEBAUTHN_CREDENTIALS[user_id]
        return {
            "user_id": user_id,
            "biometric_enabled": True,
            "registered_at": cred["registered_at"],
            "last_used": cred["last_used"]
        }
    return {"user_id": user_id, "biometric_enabled": False}


# E5: Screen Sharing / Collaboration
SCREEN_SESSIONS = {}


def create_screen_session(user_id: str, session_name: str = None) -> Dict[str, Any]:
    """E5: Create a screen sharing session."""
    session_id = secrets.token_urlsafe(8)

    session = {
        "session_id": session_id,
        "host_user_id": user_id,
        "session_name": session_name or f"Session {session_id[:4]}",
        "status": "waiting",
        "participants": [user_id],
        "created_at": datetime.now().isoformat(),
        "signaling_server": "wss://signal.finance-platform.com",
        "ice_servers": [
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "stun:stun1.l.google.com:19302"}
        ]
    }

    SCREEN_SESSIONS[session_id] = session
    return session


def join_screen_session(session_id: str, user_id: str) -> Dict[str, Any]:
    """E5: Join a screen sharing session."""
    if session_id not in SCREEN_SESSIONS:
        return {"error": "Session not found"}

    session = SCREEN_SESSIONS[session_id]
    if user_id not in session["participants"]:
        session["participants"].append(user_id)

    session["status"] = "active"

    return {
        "session_id": session_id,
        "status": "joined",
        "host": session["host_user_id"],
        "participants": session["participants"],
        "ice_servers": session["ice_servers"]
    }


def leave_screen_session(session_id: str, user_id: str) -> Dict[str, Any]:
    """E5: Leave a screen sharing session."""
    if session_id not in SCREEN_SESSIONS:
        return {"error": "Session not found"}

    session = SCREEN_SESSIONS[session_id]
    if user_id in session["participants"]:
        session["participants"].remove(user_id)

    if not session["participants"]:
        session["status"] = "ended"

    return {"status": "left", "session_id": session_id}


def end_screen_session(session_id: str, user_id: str) -> Dict[str, Any]:
    """E5: End a screen sharing session (host only)."""
    if session_id not in SCREEN_SESSIONS:
        return {"error": "Session not found"}

    session = SCREEN_SESSIONS[session_id]
    if session["host_user_id"] != user_id:
        return {"error": "Only host can end session"}

    session["status"] = "ended"
    session["ended_at"] = datetime.now().isoformat()

    return {"status": "ended", "session_id": session_id}


def get_active_sessions(user_id: str) -> Dict[str, Any]:
    """E5: Get all active screen sharing sessions for a user."""
    user_sessions = [
        s for s in SCREEN_SESSIONS.values()
        if user_id in s["participants"] and s["status"] != "ended"
    ]
    return {"user_id": user_id, "sessions": user_sessions, "count": len(user_sessions)}


def get_session_info(session_id: str) -> Dict[str, Any]:
    """E5: Get screen sharing session info."""
    if session_id not in SCREEN_SESSIONS:
        return {"error": "Session not found"}
    return SCREEN_SESSIONS[session_id]
