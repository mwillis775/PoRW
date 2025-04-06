# PoRW Blockchain Node: Hybrid Consensus Implementation

## Overview

This project is the reference implementation for a blockchain node utilizing an innovative hybrid consensus mechanism combining **Proof of Real Work (PoRW)** and **Proof of Reliable Storage (PoRS)**.

The primary goals are:

1.  **Incentivize Valuable Computation (PoRW):** Reward nodes for performing verifiable, computationally intensive tasks beneficial to scientific research (initially focused on protein folding). PoRW is responsible for minting all new currency based on the successful validation of this work, targeting a controlled inflation rate.
2.  **Ensure Network Utility & Data Integrity (PoRS):** Provide a reliable and efficient layer for processing user transactions and ensuring the long-term integrity of stored data (including potentially large datasets from PoRW). PoRS blocks are generated at regular intervals, validated by quorum-based storage checks.

This hybrid approach separates concerns, aiming to create a blockchain that is both purposeful in its work validation and practical for everyday transactions and data storage.

## Key Features

* **Hybrid Consensus:** PoRW (Protein Folding) + PoRS (Quorum Storage Checks).
* **Time-Adjusted Minting:** PoRW mints currency with rewards adjusted based on time since the last PoRW block, targeting ~2% annual inflation.
* **Transaction Processing:** Handled efficiently by regular PoRS blocks.
* **Integrated Verifiable Storage:** PoRS mechanism includes checks and incentives for reliable data storage.
* **Technology Stack:**
    * Python 3.10+
    * FastAPI (for RPC API)
    * SQLAlchemy (for PostgreSQL ORM)
    * Pydantic (for data validation & settings)
    * PostgreSQL (for data persistence)
    * Poetry (for dependency management)
    * Pytest (for testing)
    * `cryptography` library (for ECDSA signatures)

## Project Structure

/porw-blockchain|-- src/porw_blockchain/  # Main Python package|   |-- core/             # Consensus, structures, validation, crypto, protein folding|   |-- node/             # P2P communication, synchronization|   |-- rpc/              # FastAPI app, routers, schemas|   |-- storage/          # Database models, CRUD, session management|   -- config.py         # Application configuration |-- scripts/              # Helper scripts (init_db.py, run_dev.sh) |-- tests/                # Unit and integration tests |-- docs/                 # Project documentation (Sphinx) |-- .env.example          # Example environment variables |-- pyproject.toml        # Poetry configuration -- README.md             # This file
*(See the `docs/` directory for more detailed architecture information).*

## Getting Started

### Prerequisites

* Python 3.10+
* Poetry ([Installation Guide](https://python-poetry.org/docs/#installation))
* PostgreSQL Server (running and accessible)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd porw-blockchain
    ```

2.  **Install dependencies using Poetry:**
    ```bash
    poetry install
    ```
    *(This creates a virtual environment and installs packages listed in `pyproject.toml`)*

### Configuration

1.  **Create Environment File:**
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```

2.  **Edit `.env`:**
    Open the `.env` file and set *at least* the `DATABASE_URL` for your PostgreSQL instance. Adjust other variables like `P2P_PORT` or `LOG_LEVEL` if needed.
    ```dotenv
    # Example:
    DATABASE_URL="postgresql+psycopg2://your_db_user:your_db_password@your_db_host:5432/porw_db_name"
    P2P_PORT=6888
    LOG_LEVEL="INFO"
    # Add other settings from config.py as needed
    ```

### Database Setup (Development/Testing)

1.  **Initialize Database Schema:**
    Run the initialization script using Poetry. This creates the necessary tables based on the SQLAlchemy models in `src/porw_blockchain/storage/models.py`.
    ```bash
    poetry run python scripts/init_db.py
    ```
    **Note:** For production environments, use a proper database migration tool like Alembic instead of running `init_db.py` directly on existing databases.

### Running the Node (Development Mode)

1.  **Start the FastAPI Server:**
    Use the provided development script:
    ```bash
    poetry run bash scripts/run_dev.sh
    ```
    Alternatively, you can run `uvicorn` directly:
    ```bash
    poetry run uvicorn src.porw_blockchain.rpc.main:app --reload --host 0.0.0.0 --port 8000
    ```
    *(The node API will typically be available at `http://127.0.0.1:8000`)*

## API Documentation

Once the server is running, interactive API documentation is automatically available via your web browser:

* **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Testing

Run the test suite using Pytest via Poetry:

```bash
poetry run pytest
