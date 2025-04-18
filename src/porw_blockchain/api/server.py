# src/porw_blockchain/api/server.py
"""
API server implementation for the PoRW blockchain.

This module provides the main API server that handles RESTful API
and JSON-RPC requests for interacting with the blockchain.
"""

import asyncio
import json
import logging
import os
import signal
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Callable, Union, Type

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from pydantic import BaseModel

from ..core.structures import Transaction, AnyBlock, PoRWBlock, PoRSBlock
from ..network.node import Node
from ..contracts.api import router as contracts_router

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """Configuration for the API server."""
    # Server settings
    host: str = "127.0.0.1"
    port: int = 8080
    debug: bool = False

    # API settings
    enable_rest_api: bool = True
    enable_json_rpc: bool = True

    # Security settings
    enable_auth: bool = False
    api_keys: List[str] = field(default_factory=list)
    jwt_secret: Optional[str] = None

    # CORS settings
    cors_origins: List[str] = field(default_factory=lambda: ["*"])

    # Rate limiting
    enable_rate_limiting: bool = False
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Documentation
    enable_docs: bool = True

    # Data directory
    data_dir: Optional[Path] = None

    def __post_init__(self):
        """Initialize default values."""
        # Set default data directory if not provided
        if not self.data_dir:
            self.data_dir = Path.home() / ".porw" / "api"

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)


class APIServer:
    """
    API server for the PoRW blockchain.

    This class provides RESTful API and JSON-RPC interfaces for
    interacting with the blockchain.
    """

    def __init__(
        self,
        config: APIConfig,
        node: Optional[Node] = None
    ):
        """
        Initialize the API server.

        Args:
            config: Configuration for the API server.
            node: Optional Node instance to connect to.
        """
        self.config = config
        self.node = node

        # Create FastAPI app
        self.app = FastAPI(
            title="PoRW Blockchain API",
            description="API for interacting with the PoRW blockchain",
            version="0.1.0",
            docs_url="/docs" if self.config.enable_docs else None,
            redoc_url="/redoc" if self.config.enable_docs else None
        )

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add rate limiting middleware if enabled
        if self.config.enable_rate_limiting:
            self._add_rate_limiting_middleware()

        # Add authentication middleware if enabled
        if self.config.enable_auth:
            self._add_auth_middleware()

        # Set up API routes
        self._setup_routes()

        # Server state
        self.running = False
        self.server = None

        logger.info(f"Initialized API server on {self.config.host}:{self.config.port}")

    def _add_rate_limiting_middleware(self) -> None:
        """Add rate limiting middleware to the FastAPI app."""
        from .middleware import RateLimitingMiddleware

        self.app.add_middleware(
            RateLimitingMiddleware,
            limit=self.config.rate_limit_requests,
            window=self.config.rate_limit_window
        )

        logger.info(f"Added rate limiting middleware: {self.config.rate_limit_requests} requests per {self.config.rate_limit_window} seconds")

    def _add_auth_middleware(self) -> None:
        """Add authentication middleware to the FastAPI app."""
        from .middleware import AuthMiddleware

        self.app.add_middleware(
            AuthMiddleware,
            api_keys=self.config.api_keys,
            jwt_secret=self.config.jwt_secret
        )

        logger.info("Added authentication middleware")

    def _setup_routes(self) -> None:
        """Set up API routes."""
        # Create routers
        rest_router = APIRouter(prefix="/api/v1", tags=["REST API"])
        rpc_router = APIRouter(prefix="/rpc", tags=["JSON-RPC"])

        # Add REST API routes if enabled
        if self.config.enable_rest_api:
            self._setup_rest_routes(rest_router)
            self.app.include_router(rest_router)

        # Add JSON-RPC routes if enabled
        if self.config.enable_json_rpc:
            self._setup_rpc_routes(rpc_router)
            self.app.include_router(rpc_router)

        # Add smart contract routes
        self.app.include_router(contracts_router)

        # Add health check route
        @self.app.get("/health", tags=["Health"])
        async def health_check():
            """Health check endpoint."""
            return {"status": "ok", "timestamp": time.time()}

    def _setup_rest_routes(self, router: APIRouter) -> None:
        """
        Set up RESTful API routes.

        Args:
            router: The APIRouter to add routes to.
        """
        from .rest import setup_rest_routes
        setup_rest_routes(router, self)

    def _setup_rpc_routes(self, router: APIRouter) -> None:
        """
        Set up JSON-RPC routes.

        Args:
            router: The APIRouter to add routes to.
        """
        from .rpc import setup_rpc_routes
        setup_rpc_routes(router, self)

    async def start(self) -> None:
        """Start the API server."""
        if self.running:
            logger.warning("API server is already running")
            return

        self.running = True
        logger.info(f"Starting API server on {self.config.host}:{self.config.port}")

        config = uvicorn.Config(
            app=self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="debug" if self.config.debug else "info",
            loop="asyncio"
        )

        self.server = uvicorn.Server(config)
        await self.server.serve()

    async def stop(self) -> None:
        """Stop the API server."""
        if not self.running:
            return

        logger.info("Stopping API server")
        self.running = False

        if self.server:
            self.server.should_exit = True
            await self.server.shutdown()

        logger.info("API server stopped")


async def run_api_server(config: APIConfig, node: Optional[Node] = None) -> None:
    """
    Run an API server with the given configuration.

    Args:
        config: The API server configuration.
        node: Optional Node instance to connect to.
    """
    # Create and start the API server
    server = APIServer(config, node)

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(server.stop()))

    try:
        await server.start()
    except Exception as e:
        logger.error(f"Error running API server: {e}")
    finally:
        await server.stop()
