from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.connection import init_pool, close_pool
from routes import declarations, zone, narrative, counties


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="FloodReport API", lifespan=lifespan)

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
