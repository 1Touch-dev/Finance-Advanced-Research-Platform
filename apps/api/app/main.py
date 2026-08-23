from dotenv import load_dotenv
from pathlib import Path

_env_path = Path(__file__).resolve().parents[2] / ".env"
if not _env_path.exists():
    _env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_env_path, override=False)

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as core_router
from app.api.sources import router as sources_router
from app.api.evidence import router as evidence_router
from app.api.entities import router as entities_router
from app.api.search import router as search_router
from app.api.search_os import router as searchos_router
from app.api.graph import router as graph_router
from app.api.finance import router as finance_router
from app.api.skills import router as skills_router
from app.api.reports import router as reports_router
from app.api.review import router as review_router
from app.api.monitor import router as monitor_router
from app.api.compliance import router as compliance_router
from app.api.demo import router as demo_router
from app.api.registry import router as registry_router
from app.api.intelligence import router as intelligence_router
from app.api.support import router as support_router
from app.api.billing import router as billing_router
from app.api.status import router as status_router
from app.api.seo import router as seo_router
from app.api.freshness import router as freshness_router
from app.api.editorial import router as editorial_router
from app.api.compliance_content import router as compliance_content_router
from app.api.experiments import router as experiments_router
from app.api.ai_visibility import router as ai_visibility_router
from app.api.export import router as export_router
from app.api.honesty import router as honesty_router
from app.api.fact_scoring import router as fact_scoring_router
from app.api.intelligence_graph import router as intelligence_graph_router
from app.api.auth import router as auth_router
from app.core.logging import logger

try:
    from app.api.chat import router as chat_router
    _CHAT_ROUTER = True
except ImportError:
    _CHAT_ROUTER = False

app = FastAPI(title="Identity & Collaboration API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3003",
        "http://184.72.123.188:3000",
        "http://184.72.123.188:3002",
        "http://184.72.123.188:3003",
        "http://184.72.123.188:3005",
        # AWS Amplify domains
        "https://8th-july-sprint.d11ri08de55gmb.amplifyapp.com",
        "https://main.d11ri08de55gmb.amplifyapp.com",
        "https://d11ri08de55gmb.amplifyapp.com",
        # Duck DNS domain
        "https://financeintell.duckdns.org",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.core.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)

app.include_router(core_router)
app.include_router(auth_router)
app.include_router(sources_router)
app.include_router(evidence_router)
app.include_router(entities_router)
app.include_router(search_router)
app.include_router(searchos_router)
app.include_router(graph_router)
app.include_router(finance_router)
app.include_router(skills_router)
app.include_router(reports_router)
app.include_router(review_router)
app.include_router(monitor_router)
app.include_router(compliance_router)
app.include_router(demo_router)
app.include_router(registry_router)
app.include_router(intelligence_router)
app.include_router(support_router)
app.include_router(billing_router)
app.include_router(status_router)
app.include_router(seo_router)
app.include_router(freshness_router)
app.include_router(editorial_router)
app.include_router(compliance_content_router)
app.include_router(experiments_router)
app.include_router(ai_visibility_router)
app.include_router(export_router)
app.include_router(honesty_router)
app.include_router(fact_scoring_router)
app.include_router(intelligence_graph_router)
if _CHAT_ROUTER:
    app.include_router(chat_router)

def _safe_include(module_path: str, attr: str = "router", extra_attrs: list = None):
    """Import and include a router, logging failures instead of silently swallowing."""
    try:
        mod = __import__(module_path, fromlist=[attr])
        app.include_router(getattr(mod, attr))
        if extra_attrs:
            for a in extra_attrs:
                app.include_router(getattr(mod, a))
    except Exception as exc:
        logger.warning({"event": "router_load_failed", "module": module_path, "error": str(exc)})

# Core feature routers
_safe_include("app.api.tracking")
_safe_include("app.api.market")
_safe_include("app.api.filings")
_safe_include("app.api.documents")
_safe_include("app.api.entities_multi")
_safe_include("app.api.consensus")
_safe_include("app.api.guidance")
_safe_include("app.api.analysts")
_safe_include("app.api.volume")
_safe_include("app.api.formula")
_safe_include("app.api.volatility")
_safe_include("app.api.leaderboard")
_safe_include("app.api.ontology")
_safe_include("app.api.health_rag")
_safe_include("app.api.docket")
_safe_include("app.api.whisper")
_safe_include("app.api.portfolio")
_safe_include("app.api.dashboard", extra_attrs=["watchlist_router"])
_safe_include("app.api.litigation")
_safe_include("app.api.legal_proceedings")
_safe_include("app.api.revision_screener")
_safe_include("app.api.comments", extra_attrs=["annotations_router"])
_safe_include("app.api.earnings_calendar", attr="router")
_safe_include("app.api.price_alerts")
_safe_include("app.api.short_interest")
_safe_include("app.api.ipo_calendar")
_safe_include("app.api.ma_rumors")
_safe_include("app.api.insider_activity")
_safe_include("app.api.cost_basis")
_safe_include("app.api.benchmark")
_safe_include("app.api.tax_lots")
_safe_include("app.api.workspaces")
_safe_include("app.api.team_permissions")
_safe_include("app.api.person_timeline")
_safe_include("app.api.valuation_timeline")
_safe_include("app.api.data_visualizations", attr="router")
_safe_include("app.api.reddit_whale")
_safe_include("app.api.bubble_charts")
_safe_include("app.api.mobile_pwa")
_safe_include("app.api.global_equity")
_safe_include("app.api.brokerage_sync")
_safe_include("app.api.autonomous_agent")
_safe_include("app.api.recursive_entity")
_safe_include("app.api.narrative_model")
_safe_include("app.api.portfolio_analytics")
_safe_include("app.api.pwa_advanced")
_safe_include("app.api.government")
_safe_include("app.api.corporate_ownership")

try:
    from prometheus_client import make_asgi_app as _make_prom_app
    _metrics_app = _make_prom_app()
    app.mount("/metrics", _metrics_app)
except Exception:
    pass

@app.on_event("startup")
async def on_startup():
    logger.info({"event": "startup"})

    # Ensure the schema exists. Individual routers call Base.metadata.create_all()
    # ad hoc, so whether a table existed depended on which endpoint happened to be
    # hit first: /auth/register 500'd on a fresh database because nothing had run
    # create_all yet. Alembic owns the schema in deployment (`alembic upgrade head`);
    # this is the safety net for fresh SQLite databases and test runs.
    if os.getenv("DB_AUTO_CREATE", "on") != "off":
        try:
            import importlib

            from app.db.session import engine
            from app.models.base import Base

            # importlib rather than `import app.models.models`, which would rebind
            # the local name `app` and shadow the FastAPI instance.
            importlib.import_module("app.models.models")

            Base.metadata.create_all(bind=engine)
        except Exception as exc:
            logger.warning({"event": "db_auto_create_failed", "error": str(exc)})
    # Preload RAG models in a background thread so first-request latency (cold
    # HF download / model init) doesn't hit a user, and so the model is a warmed
    # thread-safe singleton before any concurrent request constructs it.
    if os.getenv("RAG_PRELOAD", "on") != "off":
        import threading

        def _warm():
            try:
                from app.services.rag import rerank
                active = rerank.preload()
                logger.info({"event": "rag_preload", "reranker_active": active})
            except Exception as exc:
                logger.info({"event": "rag_preload_skipped", "error": str(exc)})

        threading.Thread(target=_warm, name="rag-preload", daemon=True).start()

    # Start background data-refresh scheduler
    try:
        from app.services.scheduler import start_scheduler
        start_scheduler()
        logger.info({"event": "scheduler_started"})
    except Exception as exc:
        logger.warning({"event": "scheduler_start_failed", "error": str(exc)})
