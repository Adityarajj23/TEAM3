"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import auth, defects, execution, misc, projects, requirements, tests, users
from app.core.config import get_settings
from app.core.errors import install_handlers
from app.services.audit import current_trace_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.init_db import initialise
    initialise()
    yield


app = FastAPI(title="TraceTest AI", version="1.0.0", lifespan=lifespan,
              description="Enterprise QA lifecycle and test intelligence platform API.",
              openapi_url="/api/v1/openapi.json", docs_url="/api/docs", redoc_url=None)
install_handlers(app)
settings = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Trace-Id"])

_buckets: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


@app.middleware("http")
async def platform_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex[:16]
    request.state.trace_id = trace_id
    token = current_trace_id.set(trace_id)
    try:
        if request.url.path.startswith("/api/") and not request.url.path.endswith("/events"):
            ident = request.cookies.get("tt_session") or (request.client.host if request.client else "anon")
            limit = get_settings().rate_limit_per_minute
            now = time.monotonic()
            with _lock:
                q = _buckets[ident]
                while q and now - q[0] > 60:
                    q.popleft()
                if len(q) >= limit:
                    return JSONResponse(status_code=429, content={"error": {
                        "code": "rate_limited", "message": "Too many requests", "details": None, "trace_id": trace_id}})
                q.append(now)
        response = await call_next(request)
    finally:
        current_trace_id.reset(token)
    response.headers["X-Trace-Id"] = trace_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


api = APIRouter(prefix="/api/v1")
for r in (auth.router, users.router, projects.router, requirements.router, tests.router, execution.router,
          defects.router, misc.router):
    api.include_router(r)
app.include_router(api)
