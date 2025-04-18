# src/porw_blockchain/rpc/app.py
"""
FastAPI application for the PoRW blockchain RPC API.

This module provides a FastAPI application for the PoRW blockchain RPC API,
including routes for blockchain, wallet, and node operations.
"""

import logging
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..core.blockchain import Blockchain
from ..storage.database import Database
from ..explorer.router import router as explorer_router

# Configure logger
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create a FastAPI application.

    Returns:
        FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title="PoRW Blockchain API",
        description="API for the PoRW blockchain",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add exception handler
    @app.exception_handler(Exception)
    async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Handle exceptions.

        Args:
            request: Request
            exc: Exception

        Returns:
            JSON response
        """
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": str(exc)
            }
        )

    # Add health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check() -> Dict[str, Any]:
        """
        Health check endpoint.

        Returns:
            Health status
        """
        return {
            "success": True,
            "data": {
                "status": "ok",
                "version": "0.1.0"
            },
            "error": None
        }

    # Include routers
    app.include_router(explorer_router)

    return app


# Create app instance
app = create_app()
