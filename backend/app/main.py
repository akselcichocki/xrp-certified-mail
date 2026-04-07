from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import settings
from app.api.v1 import health, certify

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

app = FastAPI(
    title="XRP Certified Mail",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

# CORS -- wide open for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(certify.router, prefix="/api/v1", tags=["certify"])


@app.on_event("startup")
async def startup():
    logger.info(
        "xrp_certified_mail_started",
        environment=settings.ENVIRONMENT,
        xrp_network=settings.XRP_NETWORK,
    )


@app.get("/")
async def root():
    return {
        "service": "xrp-certified-mail",
        "version": "1.0.0",
        "status": "running",
        "network": settings.XRP_NETWORK,
    }
