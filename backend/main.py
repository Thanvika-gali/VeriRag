"""FastAPI main application entry point for VeriRAG."""

import os
import sys
from contextlib import asynccontextmanager

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.endpoints import router as api_router
from backend.database.sqlite_db import db_instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database initialization."""
    db_instance.init_db()
    yield


def create_app() -> FastAPI:
    """Application factory for VeriRAG FastAPI backend."""
    app = FastAPI(
        title="VeriRAG API",
        description=(
            "Evidence-Grounded AI Response Validation System with Hallucination Detection Assistance. "
            "Milestone 1: Input Processing, Knowledge Base Indexing & Semantic Evidence Retrieval."
        ),
        version="1.0.0-m1",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS configuration
    cors_origins_str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://localhost:8001",
    )
    origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router)

    @app.get("/", tags=["Root"])
    def root():
        return {
            "project": "VeriRAG",
            "tagline": "Evidence-Grounded AI Response Validation System with Hallucination Detection Assistance",
            "milestone": "Milestone 1 (Evidence Ingestion & RAG Retrieval)",
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host=host, port=port)
