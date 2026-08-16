from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

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
app.include_router(core_router)
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
if _CHAT_ROUTER:
    app.include_router(chat_router)

try:
    from app.api.tracking import router as tracking_router
    app.include_router(tracking_router)
except Exception:
    pass

try:
    from app.api.market import router as market_router
    app.include_router(market_router)
except Exception:
    pass

try:
    from app.api.filings import router as filings_router
    app.include_router(filings_router)
except Exception:
    pass

try:
    from app.api.documents import router as documents_router
    app.include_router(documents_router)
except Exception:
    pass

try:
    from app.api.entities_multi import router as entities_multi_router
    app.include_router(entities_multi_router)
except Exception:
    pass

try:
    from app.api.consensus import router as consensus_router
    app.include_router(consensus_router)
except Exception:
    pass

try:
    from app.api.guidance import router as guidance_router
    app.include_router(guidance_router)
except Exception:
    pass

try:
    from app.api.analysts import router as analysts_router
    app.include_router(analysts_router)
except Exception:
    pass

try:
    from app.api.volume import router as volume_router
    app.include_router(volume_router)
except Exception:
    pass

try:
    from app.api.formula import router as formula_router
    app.include_router(formula_router)
except Exception:
    pass

try:
    from app.api.volatility import router as volatility_router
    app.include_router(volatility_router)
except Exception:
    pass

try:
    from app.api.leaderboard import router as leaderboard_router
    app.include_router(leaderboard_router)
except Exception:
    pass

try:
    from app.api.ontology import router as ontology_router
    app.include_router(ontology_router)
except Exception:
    pass

try:
    from app.api.health_rag import router as health_rag_router
    app.include_router(health_rag_router)
except Exception:
    pass

try:
    from app.api.docket import router as docket_router
    app.include_router(docket_router)
except Exception:
    pass

try:
    from app.api.whisper import router as whisper_router
    app.include_router(whisper_router)
except Exception:
    pass

try:
    from app.api.portfolio import router as portfolio_router
    app.include_router(portfolio_router)
except Exception:
    pass

try:
    from app.api.dashboard import router as dashboard_router, watchlist_router
    app.include_router(dashboard_router)
    app.include_router(watchlist_router)
except Exception:
    pass

try:
    from app.api.litigation import router as litigation_router
    app.include_router(litigation_router)
except Exception:
    pass

try:
    from app.api.legal_proceedings import router as legal_proceedings_router
    app.include_router(legal_proceedings_router)
except Exception:
    pass

try:
    from app.api.revision_screener import router as revision_screener_router
    app.include_router(revision_screener_router)
except Exception:
    pass

try:
    from app.api.comments import router as comments_router, annotations_router
    app.include_router(comments_router)
    app.include_router(annotations_router)
except Exception:
    pass

try:
    from app.api.earnings_calendar import router as earnings_router
    app.include_router(earnings_router)
except Exception:
    pass

try:
    from app.api.price_alerts import router as price_alerts_router
    app.include_router(price_alerts_router)
except Exception:
    pass

try:
    from app.api.short_interest import router as short_interest_router
    app.include_router(short_interest_router)
except Exception:
    pass

try:
    from app.api.ipo_calendar import router as ipo_router
    app.include_router(ipo_router)
except Exception:
    pass

try:
    from app.api.ma_rumors import router as ma_rumors_router
    app.include_router(ma_rumors_router)
except Exception:
    pass

try:
    from app.api.insider_activity import router as insider_activity_router
    app.include_router(insider_activity_router)
except Exception:
    pass

try:
    from app.api.cost_basis import router as cost_basis_router
    app.include_router(cost_basis_router)
except Exception:
    pass

try:
    from app.api.benchmark import router as benchmark_router
    app.include_router(benchmark_router)
except Exception:
    pass

try:
    from app.api.tax_lots import router as tax_lots_router
    app.include_router(tax_lots_router)
except Exception:
    pass

try:
    from app.api.workspaces import router as workspaces_router
    app.include_router(workspaces_router)
except Exception:
    pass

try:
    from app.api.team_permissions import router as team_permissions_router
    app.include_router(team_permissions_router)
except Exception:
    pass

try:
    from app.api.person_timeline import router as person_timeline_router
    app.include_router(person_timeline_router)
except Exception:
    pass

try:
    from app.api.valuation_timeline import router as valuation_timeline_router
    app.include_router(valuation_timeline_router)
except Exception:
    pass

try:
    from app.api.data_visualizations import router as data_viz_router
    app.include_router(data_viz_router)
except Exception:
    pass

try:
    from app.api.reddit_whale import router as reddit_whale_router
    app.include_router(reddit_whale_router)
except Exception:
    pass

try:
    from app.api.bubble_charts import router as bubble_charts_router
    app.include_router(bubble_charts_router)
except Exception:
    pass

try:
    from app.api.mobile_pwa import router as mobile_pwa_router
    app.include_router(mobile_pwa_router)
except Exception:
    pass

try:
    from app.api.global_equity import router as global_equity_router
    app.include_router(global_equity_router)
except Exception:
    pass

try:
    from app.api.brokerage_sync import router as brokerage_sync_router
    app.include_router(brokerage_sync_router)
except Exception:
    pass

try:
    from prometheus_client import make_asgi_app as _make_prom_app
    _metrics_app = _make_prom_app()
    app.mount("/metrics", _metrics_app)
except Exception:
    pass

@app.on_event("startup")
async def on_startup():
    logger.info({"event": "startup"})
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
