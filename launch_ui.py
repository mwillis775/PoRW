#!/usr/bin/env python3
"""
Launch the PoRW blockchain interactive shell UI.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from porw_blockchain.storage.database import init_db
from porw_blockchain.cli.shell import PoRWShell

def main():
    """Main function."""
    print("=== PoRW Blockchain Interactive Shell ===")
    
    # Initialize the database
    print("\nInitializing database...")
    init_db()
    
    # Create and run the shell
    print("\nStarting interactive shell...")
    shell = PoRWShell(api_url="http://localhost:2000")
    shell.cmdloop()

if __name__ == "__main__":
    main()
