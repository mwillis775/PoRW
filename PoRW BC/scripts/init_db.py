# scripts/init_db.py
"""
Initializes the database by creating tables based on SQLAlchemy models.

This script should be run once during setup or whenever the database
schema needs to be recreated (in development/testing).
Use database migrations (e.g., Alembic) for production environments.
"""

import sys
import os

# Ensure the source directory is in the Python path
# This allows importing from src.porw_blockchain
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

try:
    # Import the init_db function from the storage module
    from src.porw_blockchain.storage.database import init_db
except ImportError as e:
    print(f"Error: Failed to import database module. Make sure you are running this script "
          f"from the project root or have the 'src' directory in your PYTHONPATH. Details: {e}")
    sys.exit(1)

if __name__ == "__main__":
    print("Attempting to initialize the database...")
    try:
        # Call the function that creates tables based on models
        init_db()
        # Note: The init_db function in database.py already includes print statements
        # print("Database tables should now be created (if they didn't exist).")
    except Exception as e:
        print(f"An error occurred during database initialization: {e}")
        sys.exit(1)