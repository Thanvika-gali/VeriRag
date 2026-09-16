"""FastAPI main application entry point for VeriRAG."""

import os
import sys
from contextlib import asynccontextmanager

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
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
            "Evidence-Grounded AI Response Validation & Retrieval Engine."
        ),
        version="1.0.0",
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

    # Exception Handlers to guarantee consistent JSON error responses
    @app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            err_msg = str(detail["error"])
        elif isinstance(detail, str):
            err_msg = detail
        else:
            err_msg = str(detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": err_msg, "detail": err_msg},
        )

    @app.exception_handler(RequestValidationError)
    async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        err_msg = "Invalid input: " + "; ".join(
            f"{'.'.join(str(loc) for loc in e.get('loc', []))}: {e.get('msg', '')}" for e in errors
        ) if errors else "Invalid request payload."
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"success": False, "error": err_msg, "detail": err_msg},
        )

    @app.exception_handler(Exception)
    async def custom_global_exception_handler(request: Request, exc: Exception):
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Unable to retrieve evidence. Please check that the backend and knowledge base are running.",
                "detail": "Unable to retrieve evidence. Please check that the backend and knowledge base are running.",
            },
        )

    # Include API router
    app.include_router(api_router)

    @app.get("/", tags=["Root"])
    def root():
        return {
            "status": "online",
            "name": "PROOFRAG API",
            "project": "PROOFRAG",
            "version": "1.0.0",
            "tagline": "AI Response Verification & Evidence Engine",
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
