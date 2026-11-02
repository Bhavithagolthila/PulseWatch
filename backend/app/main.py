from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import alerts, auth, dashboard, incidents, monitors
from .config import settings
from .database import Base, engine
from .services.auth import require_user
from .services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.scheduler_enabled:
        start_scheduler()
    yield
    if settings.scheduler_enabled:
        stop_scheduler()


app = FastAPI(
    title="PulseWatch API",
    version="1.0.0",
    description="API health monitoring and reliability dashboard",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=False,  # token is sent in the Authorization header, not a cookie
    allow_methods=["*"],
    allow_headers=["*"],
)
# Public: /api/health and /api/auth/login. Everything else requires a valid login token.
app.include_router(auth.router)
protected = [Depends(require_user)]
app.include_router(monitors.router, dependencies=protected)
app.include_router(dashboard.router, dependencies=protected)
app.include_router(incidents.router, dependencies=protected)
app.include_router(alerts.router, dependencies=protected)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "service": "PulseWatch API"}
