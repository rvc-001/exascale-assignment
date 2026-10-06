from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from database import engine
from models import Base
from routers import emissions, analytics, metrics
from seed import seed_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables (idempotent — safe to run every startup)
    Base.metadata.create_all(bind=engine)
    # Seed if empty (seed_database() checks internally and skips if already done)
    seed_database()
    yield
    # (cleanup code would go here if needed)

app = FastAPI(
    title="GHG Emissions Reporting API",
    version="1.0.0",
    description="Carbon Emissions Reporting Platform — GHG Protocol Scope 1 & 2",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Router registration ──
app.include_router(emissions.router)
app.include_router(analytics.router)
app.include_router(metrics.router)

@app.get("/health")
def health():
    return {"status": "ok"}
