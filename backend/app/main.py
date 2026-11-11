"""
Main FastAPI application entrypoint for University Document Intelligence.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.api.error_handlers import register_error_handlers
from app.adapters.api.routers import auth, health
from app.adapters.persistence.database import Base, engine
from app.composition.settings import get_settings

settings = get_settings()

# Initialize DB tables for development/testing
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="University Document Intelligence API",
    description="Grounded, permission-safe RAG assistant for university documents",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized Error Handlers
register_error_handlers(app)

# Include Routers
app.include_router(health.router)
app.include_router(auth.router)


@app.get("/")
def root():
    return {
        "name": "University Document Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
