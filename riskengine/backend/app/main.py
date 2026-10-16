import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health, signals, portfolio as portfolio_api, stress as stress_api
from app.api.deps import get_engine
from app.config import get_settings
from app.logging_conf import setup_logging

settings = get_settings()
setup_logging(settings.log_level)
log = logging.getLogger(__name__)

TAGS = [{"name": "system", "description": "Health and configuration."},
        {"name": "risk-engine", "description": "Unstructured text -> structured risk signals."},
        {"name": "module-a", "description": "Tactical index rebalancing."},
        {"name": "module-b", "description": "Strategic portfolio stress testing."}]


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        engine = get_engine()
        if engine.store.count() == 0:       # first start: populate (live if enabled, else bundled data)
            sigs, _ = engine.ingest_and_score()
            log.info("Startup: scored %d signals", len(sigs))
    except Exception:
        log.exception("Startup population failed; API will serve an empty store")
    yield


app = FastAPI(title=settings.app_name, version=settings.version, openapi_tags=TAGS, lifespan=lifespan,
              description="Unstructured text -> structured risk signals -> Module A / Module B")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def access_log(request: Request, call_next):
    t0 = time.perf_counter()
    resp = await call_next(request)
    log.info("%s %s -> %d (%.0f ms)", request.method, request.url.path, resp.status_code, (time.perf_counter() - t0) * 1000)
    return resp


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": type(exc).__name__})


from pathlib import Path
from starlette.staticfiles import StaticFiles

app.include_router(health.router)
app.include_router(signals.router)
app.include_router(portfolio_api.router)
app.include_router(stress_api.router)

frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
