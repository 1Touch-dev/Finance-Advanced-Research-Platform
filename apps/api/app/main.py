from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

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

@app.on_event("startup")
async def on_startup():
    logger.info({"event": "startup"})
