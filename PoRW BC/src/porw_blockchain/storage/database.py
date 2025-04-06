# src/porw_blockchain/storage/database.py
"""Database connection and session management using SQLAlchemy."""

import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base  # Import Base from models

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Provide a default or raise a more specific error
    # For now, using a placeholder for SQLite for local dev if no URL is set
    print("Warning: DATABASE_URL not set, using ephemeral SQLite database.")
    DATABASE_URL = "sqlite+pysqlite:///:memory:"
    # Or raise ConfigurationError("DATABASE_URL environment variable not set.")

# Create the SQLAlchemy engine
# pool_pre_ping=True checks connection validity before use
# echo=False disables verbose SQL logging in production (set echo=True for debugging)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize the database by creating tables defined in models."""
    # This is a dangerous operation in production with existing data.
    # Use migrations (e.g., Alembic) for production environments.
    print("Initializing database and creating tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        # Consider more robust error handling or logging


# Optional: Context manager for sessions (useful for dependency injection)
@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()