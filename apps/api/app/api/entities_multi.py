"""
Multi-Entity & Thematic Corpora API Routes (Band B #18)
────────────────────────────────────────────────────────────────────────────
Provides endpoints for:
  - Sector/industry entity queries
  - Supply chain analysis
  - Thematic corpora management
  - Cross-entity comparison
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, List
from app.auth.security import get_current_user

from app.services.multi_entity_service import (
    # Data types
    Sector,
    Industry,
    RelationshipType,
    # Functions
    get_entity,
    get_entities_by_sector,
    get_entities_by_industry,
    get_entities_by_theme,
    search_entities,
    get_entity_relationships,
    get_supply_chain,
    get_thematic_corpus,
    list_thematic_corpora,
    create_custom_corpus,
    analyze_theme_across_entities,
    compare_entities_metrics,
    # Serializers
    entity_to_dict,
    relationship_to_dict,
    supply_chain_to_dict,
    corpus_to_dict,
    thematic_result_to_dict,
    metric_to_dict,
)

router = APIRouter(prefix="/entities/multi")


# ── Entity Discovery ───────────────────────────────────────────────────────────

@router.get("/")
def list_entities(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    theme: Optional[str] = Query(None, description="Filter by theme keyword"),
    query: Optional[str] = Query(None, description="Search by name or ticker"),
    min_market_cap: Optional[float] = Query(None, description="Minimum market cap"),
):
    """
    List and search entities with multiple filters.

    Returns:
        List of matching entity profiles
    """
    try:
        # Parse sector
        sector_filter = None
        if sector:
            try:
                sector_filter = [Sector(sector.lower())]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid sector: {sector}")

        # Parse industry
        industry_filter = None
        if industry:
            try:
                industry_filter = [Industry(industry.lower())]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid industry: {industry}")

        # Theme filter
        theme_filter = [theme] if theme else None

        # Search
        entities = search_entities(
            query=query or "",
            sectors=sector_filter,
            industries=industry_filter,
            min_market_cap=min_market_cap,
            themes=theme_filter,
        )

        return {
            "entities": [entity_to_dict(e) for e in entities],
            "total": len(entities),
            "filters": {
                "sector": sector,
                "industry": industry,
                "theme": theme,
                "query": query,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching entities: {str(e)}")


@router.get("/sectors")
def list_sectors():
    """
    List all available sectors.
    """
    return {
        "sectors": [
            {"value": s.value, "name": s.name.replace("_", " ").title()}
            for s in Sector
        ]
    }


@router.get("/industries")
def list_industries():
    """
    List all available industries.
    """
    return {
        "industries": [
            {"value": i.value, "name": i.name.replace("_", " ").title()}
            for i in Industry
        ]
    }


@router.get("/by-sector/{sector}")
def get_sector_entities(sector: str):
    """
    Get all entities in a specific sector.

    Returns:
        List of entities in the sector
    """
    try:
        sector_enum = Sector(sector.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid sector: {sector}")

    entities = get_entities_by_sector(sector_enum)

    return {
        "sector": sector,
        "entities": [entity_to_dict(e) for e in entities],
        "total": len(entities),
    }


@router.get("/by-industry/{industry}")
def get_industry_entities(industry: str):
    """
    Get all entities in a specific industry.

    Returns:
        List of entities in the industry
    """
    try:
        industry_enum = Industry(industry.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid industry: {industry}")

    entities = get_entities_by_industry(industry_enum)

    return {
        "industry": industry,
        "entities": [entity_to_dict(e) for e in entities],
        "total": len(entities),
    }


@router.get("/by-theme/{theme}")
def get_theme_entities(theme: str):
    """
    Get all entities matching a theme keyword.

    Returns:
        List of entities with the theme
    """
    entities = get_entities_by_theme(theme)

    return {
        "theme": theme,
        "entities": [entity_to_dict(e) for e in entities],
        "total": len(entities),
    }


# ── Supply Chain Analysis ──────────────────────────────────────────────────────

@router.get("/supply-chain/{ticker}")
def get_ticker_supply_chain(
    ticker: str,
    max_tiers: int = Query(2, description="Maximum tiers to traverse"),
):
    """
    Get supply chain analysis for a company.

    Identifies suppliers, customers, partners with concentration risk analysis.

    Returns:
        Supply chain graph with risk scores
    """
    try:
        analysis = get_supply_chain(ticker, max_tiers=max_tiers)
        return supply_chain_to_dict(analysis)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing supply chain: {str(e)}")


@router.get("/relationships/{ticker}")
def get_ticker_relationships(
    ticker: str,
    relationship_type: Optional[str] = Query(None, description="Filter by type"),
):
    """
    Get all relationships for a company.

    Returns:
        List of supplier, customer, competitor relationships
    """
    # Parse relationship type
    rel_filter = None
    if relationship_type:
        try:
            rel_filter = [RelationshipType(relationship_type.lower())]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid relationship type: {relationship_type}")

    relationships = get_entity_relationships(ticker, relationship_types=rel_filter)

    entity = get_entity(ticker)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Unknown ticker: {ticker}")

    return {
        "ticker": ticker.upper(),
        "company_name": entity.name,
        "relationships": [relationship_to_dict(r) for r in relationships],
        "total": len(relationships),
    }


# ── Thematic Corpora ───────────────────────────────────────────────────────────

@router.get("/corpora")
def list_all_corpora():
    """
    List all available thematic corpora.

    Returns:
        List of predefined and custom corpora
    """
    corpora = list_thematic_corpora()
    return {
        "corpora": [corpus_to_dict(c) for c in corpora],
        "total": len(corpora),
    }


@router.get("/corpora/{corpus_id}")
def get_corpus(corpus_id: str):
    """
    Get a specific thematic corpus by ID.

    Returns:
        Corpus with entities and metadata
    """
    corpus = get_thematic_corpus(corpus_id)
    if not corpus:
        raise HTTPException(status_code=404, detail=f"Corpus not found: {corpus_id}")

    # Expand entity details
    entity_details = []
    for ticker in corpus.entities:
        entity = get_entity(ticker)
        if entity:
            entity_details.append(entity_to_dict(entity))

    result = corpus_to_dict(corpus)
    result["entity_details"] = entity_details

    return result


@router.post("/corpora/create")
def create_corpus(
    name: str = Query(..., description="Corpus name"),
    description: str = Query(..., description="Corpus description"),
    tickers: str = Query(..., description="Comma-separated tickers"),
    keywords: Optional[str] = Query(None, description="Comma-separated theme keywords"),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a custom thematic corpus.

    Returns:
        Created corpus with ID
    """
    ticker_list = [t.strip() for t in tickers.split(",")]
    keyword_list = [k.strip() for k in keywords.split(",")] if keywords else None

    try:
        corpus = create_custom_corpus(
            name=name,
            description=description,
            tickers=ticker_list,
            keywords=keyword_list,
        )
        return {
            "success": True,
            "corpus": corpus_to_dict(corpus),
            "message": f"Corpus '{name}' created with {len(corpus.entities)} entities",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Thematic Analysis ──────────────────────────────────────────────────────────

@router.get("/analyze/theme")
def analyze_theme(
    theme: str = Query(..., description="Theme to analyze (e.g., 'AI', 'EV')"),
    tickers: Optional[str] = Query(None, description="Comma-separated tickers"),
    corpus_id: Optional[str] = Query(None, description="Use entities from corpus"),
):
    """
    Analyze a theme across multiple entities.

    Calculates exposure scores, sentiment, and trend direction.

    Returns:
        Thematic analysis with rankings and excerpts
    """
    ticker_list = [t.strip() for t in tickers.split(",")] if tickers else None

    try:
        result = analyze_theme_across_entities(
            theme=theme,
            tickers=ticker_list,
            corpus_id=corpus_id,
        )
        return thematic_result_to_dict(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing theme: {str(e)}")


@router.get("/compare")
def compare_entities(
    tickers: str = Query(..., description="Comma-separated tickers to compare"),
    metrics: Optional[str] = Query(None, description="Comma-separated metrics"),
):
    """
    Compare metrics across multiple entities.

    Available metrics: market_cap, revenue_ttm, net_income_ttm, employees

    Returns:
        Comparative metrics with statistics and leader
    """
    ticker_list = [t.strip() for t in tickers.split(",")]
    metric_list = [m.strip() for m in metrics.split(",")] if metrics else None

    if len(ticker_list) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 tickers to compare")

    try:
        results = compare_entities_metrics(ticker_list, metric_list)
        return {
            "tickers": ticker_list,
            "metrics": [metric_to_dict(m) for m in results],
            "total_metrics": len(results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing entities: {str(e)}")


# ── Entity Profile ─────────────────────────────────────────────────────────────

@router.get("/{ticker}")
def get_entity_profile(ticker: str):
    """
    Get detailed profile for a single entity.

    Includes relationships and theme exposure.
    """
    entity = get_entity(ticker)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Unknown ticker: {ticker}")

    relationships = get_entity_relationships(ticker)

    return {
        "entity": entity_to_dict(entity),
        "relationships": [relationship_to_dict(r) for r in relationships],
        "relationship_summary": {
            "suppliers": len([r for r in relationships if r.relationship_type == RelationshipType.SUPPLIER]),
            "customers": len([r for r in relationships if r.relationship_type == RelationshipType.CUSTOMER]),
            "competitors": len([r for r in relationships if r.relationship_type == RelationshipType.COMPETITOR]),
            "partners": len([r for r in relationships if r.relationship_type == RelationshipType.PARTNER]),
        },
    }


# ── Sector Analysis ────────────────────────────────────────────────────────────

@router.get("/analyze/sector/{sector}")
def analyze_sector(
    sector: str,
    theme: Optional[str] = Query(None, description="Theme to analyze within sector"),
):
    """
    Analyze a sector with optional theme focus.

    Returns:
        Sector overview with entity breakdown and theme analysis
    """
    try:
        sector_enum = Sector(sector.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid sector: {sector}")

    entities = get_entities_by_sector(sector_enum)

    result = {
        "sector": sector,
        "total_entities": len(entities),
        "entities": [entity_to_dict(e) for e in entities],
        "market_cap_breakdown": {
            "mega": len([e for e in entities if e.market_cap_category == "mega"]),
            "large": len([e for e in entities if e.market_cap_category == "large"]),
            "mid": len([e for e in entities if e.market_cap_category == "mid"]),
            "small": len([e for e in entities if e.market_cap_category == "small"]),
        },
        "industries": list(set(e.industry.value for e in entities)),
    }

    # If theme specified, include thematic analysis
    if theme:
        tickers = [e.ticker for e in entities]
        try:
            theme_result = analyze_theme_across_entities(theme=theme, tickers=tickers)
            result["theme_analysis"] = thematic_result_to_dict(theme_result)
        except Exception:
            pass

    return result
