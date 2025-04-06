# PoRW Blockchain Node

A blockchain implementation using a novel Proof of Real Work (PoRW) consensus mechanism.

## Overview

This project is the reference implementation for the PoRW blockchain node. It includes:
* Core blockchain logic (block/transaction handling, consensus).
* P2P networking layer for node communication.
* A REST API (built with FastAPI) for interacting with the node.
* Data persistence using PostgreSQL via SQLAlchemy.

## Getting Started

### Prerequisites

* Python 3.10+
* Poetry (for dependency management): [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation)
* PostgreSQL database accessible

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd porw-blockchain
    ```

2.  **Install dependencies:**
    ```bash
    poetry install
    ```

3.  **Set up environment variables:**
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and set your `DATABASE_URL`:
    ```dotenv
    DATABASE_URL="postgresql+psycopg2://user:password@host:port/dbname"
    ```

4.  **Initialize the database:**
    Run the database initialization script within the Poetry environment:
    ```bash
    poetry run python src/porw_blockchain/storage/database.py # Or use the script if it handles this
    # Alternative if using a dedicated script:
    # poetry run python scripts/init_db.py
    ```
    *Note: Check the implementation in `database.py` or `scripts/init_db.py` for the exact command.*

5.  **Run the application (Development Server):**
    ```bash
    poetry run uvicorn src.porw_blockchain.rpc.main:app --reload
    # Or use the run script:
    # poetry run bash scripts/run_dev.sh
    ```

### API Documentation

Once the server is running, interactive API documentation (Swagger UI) is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Contributing

(Placeholder for contribution guidelines - setup, testing, PR process)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
