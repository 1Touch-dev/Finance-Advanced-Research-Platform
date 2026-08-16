"""
Dashboard & Shared Watchlists API (Band C #46)
--------------------------------------------------------------------------------
Endpoints:
- GET /dashboard - Get user's dashboards
- POST /dashboard - Create dashboard
- PUT /dashboard/{id} - Update dashboard
- DELETE /dashboard/{id} - Delete dashboard
- POST /dashboard/{id}/widgets - Add widget
- PUT /dashboard/{id}/widgets/{widget_id} - Update widget
- DELETE /dashboard/{id}/widgets/{widget_id} - Delete widget
- GET /dashboard/widget-types - Get available widget types
- POST /watchlist/{id}/share - Share watchlist
- DELETE /watchlist/{id}/share/{share_id} - Revoke share
- GET /watchlist/shared - Get watchlists shared with user
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import datetime

from app.db.session import get_db
from app.models.monitor import (
    Watchlist,
    WatchlistItem,
    WatchlistShare,
    Dashboard,
    DashboardWidget,
)
from app.services.dashboard_service import (
    get_default_dashboard_config,
    get_available_widget_types,
    validate_widget_config,
    SharedWatchlist,
    WatchlistShareInfo,
    DashboardConfig,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ── Dashboard Endpoints ───────────────────────────────────────────────────────

@router.get("")
async def list_dashboards(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """
    Get all dashboards for a user.
    """
    try:
        dashboards = db.query(Dashboard).filter_by(user_id=user_id).all()
    except Exception:
        # Table may not exist yet
        return {
            "dashboards": [get_default_dashboard_config(user_id)],
            "count": 1,
            "has_default": False,
        }

    if not dashboards:
        # Return default dashboard config if user has none
        return {
            "dashboards": [get_default_dashboard_config(user_id)],
            "count": 1,
            "has_default": False,
        }

    result = []
    for d in dashboards:
        widgets = db.query(DashboardWidget).filter_by(dashboard_id=d.id).all()
        result.append({
            "dashboard_id": d.id,
            "name": d.name,
            "is_default": d.is_default,
            "layout": d.layout,
            "widgets": [
                {
                    "widget_id": w.id,
                    "widget_type": w.widget_type,
                    "title": w.title,
                    "config": w.config,
                    "position": {"x": w.position_x, "y": w.position_y},
                    "size": {"width": w.width, "height": w.height},
                }
                for w in widgets
            ],
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        })

    return {
        "dashboards": result,
        "count": len(result),
        "has_default": any(d["is_default"] for d in result),
    }


@router.post("")
async def create_dashboard(
    user_id: str = Query(..., description="User ID"),
    name: str = Query("My Dashboard", description="Dashboard name"),
    is_default: bool = Query(False, description="Set as default"),
    db: Session = Depends(get_db),
):
    """
    Create a new dashboard.
    """
    # If setting as default, unset other defaults
    if is_default:
        db.execute(
            text("UPDATE dashboards SET is_default = false WHERE user_id = :uid"),
            {"uid": user_id}
        )

    dashboard = Dashboard(
        user_id=user_id,
        name=name,
        is_default=is_default,
        layout={"columns": 3, "rows": 2, "gap": 16},
    )
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)

    return {
        "dashboard_id": dashboard.id,
        "name": dashboard.name,
        "is_default": dashboard.is_default,
        "created_at": dashboard.created_at.isoformat() if dashboard.created_at else None,
    }


@router.get("/{dashboard_id}")
async def get_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific dashboard with all widgets.
    """
    dashboard = db.query(Dashboard).filter_by(id=dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    widgets = db.query(DashboardWidget).filter_by(dashboard_id=dashboard_id).all()

    return {
        "dashboard_id": dashboard.id,
        "user_id": dashboard.user_id,
        "name": dashboard.name,
        "is_default": dashboard.is_default,
        "layout": dashboard.layout,
        "widgets": [
            {
                "widget_id": w.id,
                "widget_type": w.widget_type,
                "title": w.title,
                "config": w.config,
                "position": {"x": w.position_x, "y": w.position_y},
                "size": {"width": w.width, "height": w.height},
            }
            for w in widgets
        ],
        "created_at": dashboard.created_at.isoformat() if dashboard.created_at else None,
        "updated_at": dashboard.updated_at.isoformat() if dashboard.updated_at else None,
    }


@router.put("/{dashboard_id}")
async def update_dashboard(
    dashboard_id: int,
    name: Optional[str] = Query(None),
    is_default: Optional[bool] = Query(None),
    layout: Optional[dict] = None,
    db: Session = Depends(get_db),
):
    """
    Update dashboard settings.
    """
    dashboard = db.query(Dashboard).filter_by(id=dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    if name is not None:
        dashboard.name = name
    if layout is not None:
        dashboard.layout = layout
    if is_default is not None:
        if is_default:
            # Unset other defaults
            db.execute(
                text("UPDATE dashboards SET is_default = false WHERE user_id = :uid AND id != :did"),
                {"uid": dashboard.user_id, "did": dashboard_id}
            )
        dashboard.is_default = is_default

    db.commit()

    return {
        "dashboard_id": dashboard.id,
        "name": dashboard.name,
        "is_default": dashboard.is_default,
        "updated": True,
    }


@router.delete("/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a dashboard and all its widgets.
    """
    dashboard = db.query(Dashboard).filter_by(id=dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Delete widgets first
    db.execute(
        text("DELETE FROM dashboard_widgets WHERE dashboard_id = :did"),
        {"did": dashboard_id}
    )
    db.delete(dashboard)
    db.commit()

    return {"deleted": True, "dashboard_id": dashboard_id}


# ── Widget Endpoints ──────────────────────────────────────────────────────────

@router.post("/{dashboard_id}/widgets")
async def add_widget(
    dashboard_id: int,
    widget_type: str = Query(..., description="Widget type"),
    title: Optional[str] = Query(None, description="Widget title"),
    position_x: int = Query(0, description="X position"),
    position_y: int = Query(0, description="Y position"),
    width: int = Query(1, description="Width in grid units"),
    height: int = Query(1, description="Height in grid units"),
    config: Optional[dict] = None,
    db: Session = Depends(get_db),
):
    """
    Add a widget to a dashboard.
    """
    dashboard = db.query(Dashboard).filter_by(id=dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    widget = DashboardWidget(
        dashboard_id=dashboard_id,
        widget_type=widget_type,
        title=title,
        config=config or {},
        position_x=position_x,
        position_y=position_y,
        width=width,
        height=height,
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)

    return {
        "widget_id": widget.id,
        "widget_type": widget.widget_type,
        "title": widget.title,
        "position": {"x": widget.position_x, "y": widget.position_y},
        "size": {"width": widget.width, "height": widget.height},
    }


@router.put("/{dashboard_id}/widgets/{widget_id}")
async def update_widget(
    dashboard_id: int,
    widget_id: int,
    title: Optional[str] = Query(None),
    position_x: Optional[int] = Query(None),
    position_y: Optional[int] = Query(None),
    width: Optional[int] = Query(None),
    height: Optional[int] = Query(None),
    config: Optional[dict] = None,
    db: Session = Depends(get_db),
):
    """
    Update a widget's configuration or position.
    """
    widget = db.query(DashboardWidget).filter_by(
        id=widget_id, dashboard_id=dashboard_id
    ).first()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    if title is not None:
        widget.title = title
    if position_x is not None:
        widget.position_x = position_x
    if position_y is not None:
        widget.position_y = position_y
    if width is not None:
        widget.width = width
    if height is not None:
        widget.height = height
    if config is not None:
        widget.config = config

    db.commit()

    return {
        "widget_id": widget.id,
        "updated": True,
    }


@router.delete("/{dashboard_id}/widgets/{widget_id}")
async def delete_widget(
    dashboard_id: int,
    widget_id: int,
    db: Session = Depends(get_db),
):
    """
    Remove a widget from a dashboard.
    """
    widget = db.query(DashboardWidget).filter_by(
        id=widget_id, dashboard_id=dashboard_id
    ).first()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    db.delete(widget)
    db.commit()

    return {"deleted": True, "widget_id": widget_id}


@router.get("/widget-types")
async def list_widget_types():
    """
    Get available widget types and their configuration options.
    """
    return {
        "widget_types": get_available_widget_types(),
        "count": len(get_available_widget_types()),
    }


# ── Watchlist Sharing Endpoints ───────────────────────────────────────────────

watchlist_router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@watchlist_router.post("/{watchlist_id}/share")
async def share_watchlist(
    watchlist_id: int,
    shared_by: str = Query(..., description="User sharing the watchlist"),
    shared_with: str = Query(..., description="User to share with"),
    permission: str = Query("view", description="Permission level: view or edit"),
    db: Session = Depends(get_db),
):
    """
    Share a watchlist with another user.
    """
    watchlist = db.query(Watchlist).filter_by(id=watchlist_id).first()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    if permission not in ("view", "edit"):
        raise HTTPException(status_code=400, detail="Permission must be 'view' or 'edit'")

    # Check if already shared
    existing = db.query(WatchlistShare).filter_by(
        watchlist_id=watchlist_id,
        shared_with=shared_with
    ).first()
    if existing:
        existing.permission = permission
        db.commit()
        return {
            "share_id": existing.id,
            "watchlist_id": watchlist_id,
            "shared_with": shared_with,
            "permission": permission,
            "updated": True,
        }

    share = WatchlistShare(
        watchlist_id=watchlist_id,
        shared_by=shared_by,
        shared_with=shared_with,
        permission=permission,
    )
    db.add(share)
    db.commit()
    db.refresh(share)

    return {
        "share_id": share.id,
        "watchlist_id": watchlist_id,
        "watchlist_name": watchlist.name,
        "shared_with": shared_with,
        "permission": permission,
    }


@watchlist_router.delete("/{watchlist_id}/share/{share_id}")
async def revoke_share(
    watchlist_id: int,
    share_id: int,
    db: Session = Depends(get_db),
):
    """
    Revoke a watchlist share.
    """
    share = db.query(WatchlistShare).filter_by(
        id=share_id, watchlist_id=watchlist_id
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    db.delete(share)
    db.commit()

    return {"revoked": True, "share_id": share_id}


@watchlist_router.get("/{watchlist_id}/shares")
async def get_watchlist_shares(
    watchlist_id: int,
    db: Session = Depends(get_db),
):
    """
    Get all shares for a watchlist.
    """
    watchlist = db.query(Watchlist).filter_by(id=watchlist_id).first()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    shares = db.query(WatchlistShare).filter_by(watchlist_id=watchlist_id).all()

    return {
        "watchlist_id": watchlist_id,
        "watchlist_name": watchlist.name,
        "shares": [
            {
                "share_id": s.id,
                "shared_by": s.shared_by,
                "shared_with": s.shared_with,
                "permission": s.permission,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in shares
        ],
        "count": len(shares),
    }


@watchlist_router.get("/shared")
async def get_shared_watchlists(
    user_id: str = Query(..., description="User ID to get shared watchlists for"),
    db: Session = Depends(get_db),
):
    """
    Get all watchlists shared with a user.
    """
    try:
        shares = db.query(WatchlistShare).filter_by(shared_with=user_id).all()
    except Exception:
        # Table may not exist yet
        return {
            "shared_watchlists": [],
            "count": 0,
        }

    result = []
    for share in shares:
        watchlist = db.query(Watchlist).filter_by(id=share.watchlist_id).first()
        if watchlist:
            items = db.execute(
                text("SELECT id, ticker, entity_id, notes FROM watchlist_items WHERE watchlist_id = :wid"),
                {"wid": watchlist.id}
            ).fetchall()

            result.append({
                "watchlist_id": watchlist.id,
                "name": watchlist.name,
                "owner": share.shared_by,
                "permission": share.permission,
                "item_count": len(items),
                "items": [
                    {"id": r[0], "ticker": r[1], "entity_id": r[2], "notes": r[3]}
                    for r in items
                ],
                "shared_at": share.created_at.isoformat() if share.created_at else None,
            })

    return {
        "shared_watchlists": result,
        "count": len(result),
    }
