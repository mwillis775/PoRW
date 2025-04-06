# src/porw_blockchain/config.py
"""
Centralized application configuration management.

Uses Pydantic's BaseSettings to load configuration from environment
variables and .env files, providing type validation and defaults.
"""

from pydantic import Field
# Use pydantic-settings for automatic .env loading etc.
# Ensure 'pydantic-settings' is added to pyproject.toml dependencies
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging # Import logging to use standard level names

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    """
    # Database configuration
    DATABASE_URL: str = Field(
        ..., # Ellipsis indicates this field is required (no default)
        description="URL for connecting to the PostgreSQL database. Format: postgresql+psycopg2://user:password@host:port/dbname"
    )

    # P2P Networking configuration
    P2P_PORT: int = Field(
        default=6888,
        description="Port number for P2P node communication."
    )
    NODE_HOST: str = Field(
        default="0.0.0.0",
        description="Host address for the P2P server to listen on."
    )
    # Potential future setting for bootstrap nodes
    # BOOTSTRAP_NODES: List[str] = Field(default=[], description="List of initial peer addresses to connect to.")

    # Logging configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (e.g., DEBUG, INFO, WARNING, ERROR)."
    )

    # Pydantic BaseSettings configuration
    # Tells BaseSettings to look for a .env file and treat variable names as case-insensitive
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False # Environment variables often case-insensitive
    )

# Create a single instance of the Settings class for the application to use
# This instance will automatically load values when it's created.
settings = Settings()

# --- Optional: Configure Root Logger ---
# You might want to configure the root logger based on the loaded settings
# Or handle this in a dedicated logging setup function called from main app entry point
# logging.basicConfig(level=settings.LOG_LEVEL.upper())
# logging.getLogger().setLevel(settings.LOG_LEVEL.upper())