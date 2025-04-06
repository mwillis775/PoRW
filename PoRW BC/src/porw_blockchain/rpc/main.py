# src/porw_blockchain/rpc/main.py
"""Main FastAPI application entry point and core API routes."""

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

# Assuming config setup allows easy import, adjust if needed
# from .. import config
from ..storage import database, crud, models # Example imports, refine as needed

# --- Add this import ---
from .routers import blocks # Import the new router

# Create database tables if they don't exist (for dev purposes)
# Consider calling this from a script like `init_db.py` instead for more control
# database.init_db() # Disabled by default - run explicitly via script

# Create the FastAPI application instance
app = FastAPI(
    title="PoRW Blockchain Node API",
    description="API for interacting with the Proof of Real Work Blockchain Node.",
    version="0.1.0",
)

# --- Include the router ---
app.include_router(blocks.router) # Add the block routes to the main app


# Dependency for getting DB session
def get_db():
    """FastAPI dependency to provide a database session."""
    # Note: This dependency was fetched from the user upload
    # but the implementation shown here reflects standard practice.
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health", tags=["Status"], summary="Health Check")
async def health_check():
    """Perform a basic health check of the API."""
    # Note: This endpoint was fetched from the user upload
    # but the implementation shown here reflects standard practice.
    return {"status": "ok"}


# Example placeholder route - replace with actual blockchain logic later
# This example endpoint in the main file can likely be removed now
# that we have specific routers.
# @app.get("/blocks/latest", tags=["Blocks"], summary="Get Latest Block") ...

# Add other routers here later, e.g.:
# from .routers import transactions, nodes
# app.include_router(transactions.router)
# app.include_router(nodes.router)