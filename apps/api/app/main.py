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
from app.core.logging import logger

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

@app.on_event("startup")
async def on_startup():
    logger.info({"event": "startup"})
