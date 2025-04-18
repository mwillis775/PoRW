# PoRW Blockchain

Proof of Research Work Blockchain Implementation
NOT IN A WORKING STAE BUT ITS GETTING THERE
## Overview

This project implements a blockchain using a hybrid consensus mechanism:

1. **Proof of Research Work (PoRW)**: A novel consensus mechanism that rewards computational work done for protein folding research.
2. **Proof of Reliable Storage (PoRS)**: A consensus mechanism that rewards nodes for reliably storing blockchain data.

## Features

- Hybrid consensus mechanism (PoRW + PoRS)
- Real protein folding computation for scientific research
- Distributed storage system with challenge/response verification
- Interactive shell for blockchain interaction
- Web interface for managing wallet, mining, and storage nodes
- Checkpoint system for faster validation
- Efficient chain traversal functions
- Pending transaction management
- State management system
- Docker containerization for easy deployment

## Installation

```bash
# Clone the repository
git clone https://github.com/mwillis775/PoRW-PoRS.git
cd PoRW-PoRS

# Install dependencies
poetry install
```

## Usage

### Interactive Shell

```bash
# Run the interactive shell
poetry run python -m porw_blockchain.cli.shell
```

### API Server

```bash
# Run the API server
poetry run python -m porw_blockchain.bin.porw-api
```

### Web Interface

```bash
# Run the web interface
./run_web_interface.sh
```

The web interface provides a user-friendly way to interact with the blockchain, including:

- Dashboard with network statistics
- Wallet management (create, import, send transactions)
- Mining node management (start, stop, monitor performance)
- Storage node management (start, stop, monitor storage usage)
- Block explorer to view blockchain data

## Development

```bash
# Run tests
poetry run pytest

# Run linting
poetry run ruff check .
poetry run mypy src

# Run security checks
poetry run bandit -r src
```

## License

See the [LICENSE](LICENSE) file for details.
