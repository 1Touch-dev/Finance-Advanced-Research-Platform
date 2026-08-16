"""
Portfolio Tracking API (Band C #32)
--------------------------------------------------------------------------------
Endpoints:
- GET /portfolio - List all portfolios
- POST /portfolio - Create portfolio
- GET /portfolio/{id} - Get portfolio summary with holdings
- PUT /portfolio/{id} - Update portfolio
- DELETE /portfolio/{id} - Delete portfolio
- POST /portfolio/{id}/positions - Add position
- PUT /portfolio/{id}/positions/{pos_id} - Update position
- DELETE /portfolio/{id}/positions/{pos_id} - Delete position
- GET /portfolio/{id}/performance - Get performance metrics
- GET /portfolio/{id}/allocation - Get sector allocation
- POST /portfolio/{id}/import - Import positions from CSV
- GET /portfolio/compare - Compare multiple portfolios
"""

from fastapi import APIRouter, Query, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
import csv
import io

from app.db.session import get_db
from app.models.monitor import Portfolio, Position
from app.services.portfolio_service import get_portfolio_service

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# ── List Portfolios ───────────────────────────────────────────────────────────

@router.get("")
async def list_portfolios(
    db: Session = Depends(get_db),
):
    """
    List all portfolios with summary metrics.
    """
    portfolios = db.query(Portfolio).order_by(Portfolio.created_at.desc()).all()

    result = []
    service = get_portfolio_service()

    for p in portfolios:
        # Get positions
        positions = db.execute(
            text("SELECT ticker, qty, cost_basis FROM positions WHERE portfolio_id = :pid"),
            {"pid": p.id}
        ).fetchall()

        pos_list = [{"ticker": r[0], "qty": r[1], "cost_basis": r[2]} for r in positions]
        holdings = service.calculate_holdings(pos_list)
        performance = service.calculate_performance(holdings)

        result.append({
            "id": p.id,
            "name": p.name,
            "base_currency": p.base_ccy or "USD",
            "thesis": p.thesis,
            "holdings_count": len(holdings),
            "total_market_value": round(performance.total_market_value, 2),
            "total_unrealized_pnl": round(performance.total_unrealized_pnl, 2),
            "total_unrealized_pnl_pct": round(performance.total_unrealized_pnl_pct, 2),
            "day_change": round(performance.day_change, 2),
            "day_change_pct": round(performance.day_change_pct, 2),
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return {
        "portfolios": result,
        "count": len(result),
    }


# ── Create Portfolio ──────────────────────────────────────────────────────────

@router.post("")
async def create_portfolio(
    name: str = Query(..., description="Portfolio name"),
    base_currency: str = Query("USD", description="Base currency"),
    thesis: Optional[str] = Query(None, description="Investment thesis"),
    db: Session = Depends(get_db),
):
    """
    Create a new portfolio.
    """
    portfolio = Portfolio(
        name=name,
        base_ccy=base_currency,
        thesis=thesis,
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "base_currency": portfolio.base_ccy,
        "thesis": portfolio.thesis,
        "created_at": portfolio.created_at.isoformat() if portfolio.created_at else None,
    }


# ── Compare Portfolios (MUST come before /{portfolio_id}) ─────────────────────

@router.get("/compare")
async def compare_portfolios(
    ids: str = Query(..., description="Comma-separated portfolio IDs"),
    db: Session = Depends(get_db),
):
    """
    Compare multiple portfolios side by side.
    """
    import datetime

    portfolio_ids = [int(x.strip()) for x in ids.split(",")]

    if len(portfolio_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 portfolios to compare")

    service = get_portfolio_service()
    results = []

    for pid in portfolio_ids:
        portfolio = db.query(Portfolio).filter_by(id=pid).first()
        if not portfolio:
            continue

        positions = db.execute(
            text("SELECT ticker, qty, cost_basis FROM positions WHERE portfolio_id = :pid"),
            {"pid": pid}
        ).fetchall()

        pos_list = [{"ticker": r[0], "qty": r[1], "cost_basis": r[2]} for r in positions]
        holdings = service.calculate_holdings(pos_list)
        performance = service.calculate_performance(holdings)
        allocation = service.calculate_sector_allocation(holdings)

        results.append({
            "portfolio_id": pid,
            "name": portfolio.name,
            "performance": performance.to_dict(),
            "top_holdings": [h.to_dict() for h in holdings[:5]],
            "sector_allocation": [a.to_dict() for a in allocation[:5]],
        })

    return {
        "portfolios": results,
        "comparison_date": str(datetime.datetime.now().date()),
    }


# ── Get Portfolio Summary ─────────────────────────────────────────────────────

@router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
):
    """
    Get full portfolio summary with holdings, allocation, and performance.
    """
    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Get positions
    positions = db.execute(
        text("SELECT id, ticker, qty, cost_basis, notes FROM positions WHERE portfolio_id = :pid"),
        {"pid": portfolio_id}
    ).fetchall()

    pos_list = [
        {"id": r[0], "ticker": r[1], "qty": r[2], "cost_basis": r[3], "notes": r[4]}
        for r in positions
    ]

    service = get_portfolio_service()
    summary = service.get_portfolio_summary(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        base_currency=portfolio.base_ccy or "USD",
        thesis=portfolio.thesis,
        positions=pos_list,
        created_at=portfolio.created_at.isoformat() if portfolio.created_at else "",
    )

    return summary.to_dict()


# ── Update Portfolio ──────────────────────────────────────────────────────────

@router.put("/{portfolio_id}")
async def update_portfolio(
    portfolio_id: int,
    name: Optional[str] = Query(None),
    base_currency: Optional[str] = Query(None),
    thesis: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Update portfolio metadata.
    """
    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if name is not None:
        portfolio.name = name
    if base_currency is not None:
        portfolio.base_ccy = base_currency
    if thesis is not None:
        portfolio.thesis = thesis

    db.commit()

    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "base_currency": portfolio.base_ccy,
        "thesis": portfolio.thesis,
    }


# ── Delete Portfolio ──────────────────────────────────────────────────────────

@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a portfolio and all its positions.
    """
    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Delete positions first
    db.execute(
        text("DELETE FROM positions WHERE portfolio_id = :pid"),
        {"pid": portfolio_id}
    )
    db.delete(portfolio)
    db.commit()

    return {"deleted": True, "portfolio_id": portfolio_id}


# ── Add Position ──────────────────────────────────────────────────────────────

@router.post("/{portfolio_id}/positions")
async def add_position(
    portfolio_id: int,
    ticker: str = Query(..., description="Stock ticker"),
    quantity: float = Query(..., description="Number of shares"),
    cost_basis: float = Query(..., description="Cost per share"),
    notes: Optional[str] = Query(None, description="Position notes"),
    db: Session = Depends(get_db),
):
    """
    Add a position to the portfolio.
    """
    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    position = Position(
        portfolio_id=portfolio_id,
        ticker=ticker.upper(),
        qty=quantity,
        cost_basis=cost_basis,
        notes=notes,
    )
    db.add(position)
    db.commit()
    db.refresh(position)

    return {
        "id": position.id,
        "portfolio_id": portfolio_id,
        "ticker": position.ticker,
        "quantity": position.qty,
        "cost_basis": position.cost_basis,
        "notes": position.notes,
    }


# ── Update Position ───────────────────────────────────────────────────────────

@router.put("/{portfolio_id}/positions/{position_id}")
async def update_position(
    portfolio_id: int,
    position_id: int,
    quantity: Optional[float] = Query(None),
    cost_basis: Optional[float] = Query(None),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Update an existing position.
    """
    position = db.query(Position).filter_by(id=position_id, portfolio_id=portfolio_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    if quantity is not None:
        position.qty = quantity
    if cost_basis is not None:
        position.cost_basis = cost_basis
    if notes is not None:
        position.notes = notes

    db.commit()

    return {
        "id": position.id,
        "ticker": position.ticker,
        "quantity": position.qty,
        "cost_basis": position.cost_basis,
        "notes": position.notes,
    }


# ── Delete Position ───────────────────────────────────────────────────────────

@router.delete("/{portfolio_id}/positions/{position_id}")
async def delete_position(
    portfolio_id: int,
    position_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a position from the portfolio.
    """
    position = db.query(Position).filter_by(id=position_id, portfolio_id=portfolio_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    db.delete(position)
    db.commit()

    return {"deleted": True, "position_id": position_id}


# ── Get Performance ───────────────────────────────────────────────────────────

@router.get("/{portfolio_id}/performance")
async def get_performance(
    portfolio_id: int,
    db: Session = Depends(get_db),
):
    """
    Get portfolio performance metrics.
    """
    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    positions = db.execute(
        text("SELECT ticker, qty, cost_basis FROM positions WHERE portfolio_id = :pid"),
        {"pid": portfolio_id}
    ).fetchall()

    pos_list = [{"ticker": r[0], "qty": r[1], "cost_basis": r[2]} for r in positions]

    service = get_portfolio_service()
    holdings = service.calculate_holdings(pos_list)
    performance = service.calculate_performance(holdings)

    return {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio.name,
        **performance.to_dict(),
    }


# ── Get Allocation ────────────────────────────────────────────────────────────

@router.get("/{portfolio_id}/allocation")
async def get_allocation(
    portfolio_id: int,
    db: Session = Depends(get_db),
):
    """
    Get portfolio sector allocation.
    """
    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    positions = db.execute(
        text("SELECT ticker, qty, cost_basis FROM positions WHERE portfolio_id = :pid"),
        {"pid": portfolio_id}
    ).fetchall()

    pos_list = [{"ticker": r[0], "qty": r[1], "cost_basis": r[2]} for r in positions]

    service = get_portfolio_service()
    holdings = service.calculate_holdings(pos_list)
    allocation = service.calculate_sector_allocation(holdings)

    return {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio.name,
        "sectors": [a.to_dict() for a in allocation],
    }


# ── Import Positions ──────────────────────────────────────────────────────────

@router.post("/{portfolio_id}/import")
async def import_positions(
    portfolio_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Import positions from CSV file.

    CSV format:
    ticker,quantity,cost_basis,notes
    AAPL,100,150.50,Apple position
    MSFT,50,350.25,Microsoft position
    """
    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))

    imported = 0
    errors = []

    for row in reader:
        try:
            ticker = row.get("ticker", "").upper().strip()
            qty = float(row.get("quantity", row.get("qty", 0)))
            cost = float(row.get("cost_basis", row.get("cost", 0)))
            notes = row.get("notes", "")

            if ticker and qty > 0:
                position = Position(
                    portfolio_id=portfolio_id,
                    ticker=ticker,
                    qty=qty,
                    cost_basis=cost,
                    notes=notes,
                )
                db.add(position)
                imported += 1
        except Exception as e:
            errors.append(str(e))

    db.commit()

    return {
        "imported": imported,
        "errors": errors,
        "portfolio_id": portfolio_id,
    }


