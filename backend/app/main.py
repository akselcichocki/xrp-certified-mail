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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://certmail.akselcichocki.com",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple rate limiting
from collections import defaultdict
import time as _time

_rate_limits = defaultdict(list)
_RATE_LIMIT = 30  # requests per minute
_RATE_WINDOW = 60  # seconds

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = _time.time()
    # Clean old entries
    _rate_limits[client_ip] = [t for t in _rate_limits[client_ip] if now - t < _RATE_WINDOW]
    if len(_rate_limits[client_ip]) >= _RATE_LIMIT:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
    _rate_limits[client_ip].append(now)
    return await call_next(request)

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
