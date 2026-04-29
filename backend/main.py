from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from db.connection import init_pool, close_pool
from limiter import limiter
from routes import declarations, zone, narrative, counties


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="Hazard Viewer API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# trust X-Forwarded-For from Render's proxy so rate limiting uses the real client IP
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(declarations.router, prefix="/api")
app.include_router(zone.router, prefix="/api")
app.include_router(narrative.router, prefix="/api")
app.include_router(counties.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
