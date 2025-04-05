# tests/conftest.py
"""
Pytest fixtures for testing the PoRW Blockchain application.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool # Use StaticPool for SQLite in-memory

# Adjust import path based on your project structure
from src.porw_blockchain.storage.database import Base # Import Base from your models/db setup
from src.porw_blockchain.storage.database import DATABASE_URL as REAL_DATABASE_URL # If needed

# Use an in-memory SQLite database for testing
# Use StaticPool to ensure the same connection is used across a test session's scope
TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"

# Keep test engine separate from the main app engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}, # Required for SQLite usage in multiple test functions
    poolclass=StaticPool
)

# Create a sessionmaker configured for testing
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function") # Recreate DB for each test function
def db_session() -> Session:
    """
    Pytest fixture to provide a clean database session for each test function.
    Creates all tables, yields a session, and drops all tables after the test.
    """
    # Create tables before the test runs
    Base.metadata.create_all(bind=test_engine)
    
    db = TestingSessionLocal()
    try:
        yield db # Provide the session to the test function
    finally:
        db.close()
        # Drop all tables after the test finishes
        Base.metadata.drop_all(bind=test_engine)