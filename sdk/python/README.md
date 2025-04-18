# PoRW Blockchain Python SDK

A Python SDK for interacting with the PoRW Blockchain.

## Installation

```bash
pip install porw-blockchain-sdk
```

## Features

- Wallet management (create, import, export)
- Transaction creation and signing
- Blockchain querying (blocks, transactions, balances)
- Smart contract interaction
- Protein folding data access
- Storage node interaction
- Hardware wallet support

## Usage Examples

### Creating a Wallet

```python
from porw_blockchain import Wallet

# Create a new wallet
wallet = Wallet()
wallet.create("strong-password")
print(f"New wallet address: {wallet.address}")

# Save wallet to file
wallet.save_to_file("my-wallet.json", "strong-password")

# Load wallet from file
loaded_wallet = Wallet()
loaded_wallet.load_from_file("my-wallet.json", "strong-password")
```

### Connecting to a Node

```python
from porw_blockchain import PoRWClient

# Connect to a local node
client = PoRWClient("http://localhost:8000")

# Connect to a specific network
testnet_client = PoRWClient("https://testnet.porw-blockchain.org")
```

### Sending a Transaction

```python
from porw_blockchain import Wallet, PoRWClient

# Load wallet and connect to node
wallet = Wallet()
wallet.load_from_file("my-wallet.json", "strong-password")
client = PoRWClient("http://localhost:8000")
wallet.set_client(client)

# Create and send a transaction
tx_result = wallet.send_transaction(
    recipient="porw1abcdef1234567890abcdef1234567890abcdef",
    amount=10.5,
    memo="Payment for services"
)

print(f"Transaction ID: {tx_result['transaction_id']}")
```

### Querying the Blockchain

```python
from porw_blockchain import PoRWClient

client = PoRWClient("http://localhost:8000")

# Get blockchain info
info = client.get_blockchain_info()
print(f"Current height: {info['height']}")

# Get a block by height
block = client.get_block_by_height(12345)
print(f"Block hash: {block['hash']}")

# Get a transaction
tx = client.get_transaction("abcdef1234567890abcdef1234567890")
print(f"Transaction: {tx}")
```

### Working with Smart Contracts

```python
from porw_blockchain import Wallet, Contract

# Load wallet
wallet = Wallet()
wallet.load_from_file("my-wallet.json", "strong-password")

# Connect to a contract
contract = Contract(
    address="porw1contract1234567890abcdef1234567890abcdef",
    abi=[...],  # Contract ABI
    wallet=wallet
)

# Call a read-only method
result = contract.call("get_balance", ["porw1abcdef1234567890abcdef1234567890abcdef"])
print(f"Balance: {result}")

# Execute a transaction method
tx_result = contract.execute("transfer", [
    "porw1abcdef1234567890abcdef1234567890abcdef",
    10.5
])
print(f"Transaction ID: {tx_result['transaction_id']}")
```

### Accessing Protein Folding Data

```python
from porw_blockchain import PoRWClient

client = PoRWClient("http://localhost:8000")

# Get protein folding data
protein_data = client.get_protein_folding_data("protein123")
print(f"Protein structure: {protein_data['structure']}")

# Get list of available proteins
proteins = client.get_available_proteins()
print(f"Available proteins: {proteins}")
```

### Using Hardware Wallets

```python
from porw_blockchain import HardwareWallet

# Connect to a Ledger hardware wallet
hardware_wallet = HardwareWallet()
hardware_wallet.connect("ledger")

# Get address
address = hardware_wallet.get_address("m/44'/0'/0'/0/0")
print(f"Hardware wallet address: {address}")

# Sign a transaction
signed_tx = hardware_wallet.sign_transaction(transaction)
```

## API Documentation

For detailed API documentation, see the [API.md](./docs/API.md) file.

## Development

### Prerequisites

- Python 3.8+
- pip

### Building from Source

```bash
# Clone the repository
git clone https://github.com/mwillis775/PoRW-PoRS.git
cd PoRW-PoRS/sdk/python

# Install dependencies
pip install -e .

# Run tests
pytest
```

## License

This SDK is released under the MIT License. See the [LICENSE](../../LICENSE) file for details.
