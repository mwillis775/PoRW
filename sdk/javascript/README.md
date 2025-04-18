# PoRW Blockchain JavaScript/TypeScript SDK

A JavaScript/TypeScript SDK for interacting with the PoRW Blockchain.

## Installation

### npm

```bash
npm install porw-blockchain-sdk
```

### yarn

```bash
yarn add porw-blockchain-sdk
```

## Features

- Wallet management (create, import, export)
- Transaction creation and signing
- Blockchain querying (blocks, transactions, balances)
- Smart contract interaction
- Protein folding data access
- Storage node interaction
- Hardware wallet support
- TypeScript type definitions

## Usage Examples

### Creating a Wallet

```typescript
import { Wallet } from 'porw-blockchain-sdk';

// Create a new wallet
const wallet = new Wallet();
await wallet.create('strong-password');
console.log('New wallet address:', wallet.address);

// Save wallet to file
await wallet.saveToFile('my-wallet.json', 'strong-password');

// Load wallet from file
const loadedWallet = new Wallet();
await loadedWallet.loadFromFile('my-wallet.json', 'strong-password');
```

### Connecting to a Node

```typescript
import { PoRWClient } from 'porw-blockchain-sdk';

// Connect to a local node
const client = new PoRWClient('http://localhost:8000');

// Connect to a specific network
const testnetClient = new PoRWClient('https://testnet.porw-blockchain.org');
```

### Sending a Transaction

```typescript
import { Wallet, PoRWClient } from 'porw-blockchain-sdk';

// Load wallet and connect to node
const wallet = new Wallet();
await wallet.loadFromFile('my-wallet.json', 'strong-password');
const client = new PoRWClient('http://localhost:8000');

// Create and send a transaction
const txResult = await wallet.sendTransaction({
  recipient: 'porw1abcdef1234567890abcdef1234567890abcdef',
  amount: 10.5,
  memo: 'Payment for services'
});

console.log('Transaction ID:', txResult.transactionId);
```

### Querying the Blockchain

```typescript
import { PoRWClient } from 'porw-blockchain-sdk';

const client = new PoRWClient('http://localhost:8000');

// Get blockchain info
const info = await client.getBlockchainInfo();
console.log('Current height:', info.height);

// Get a block by height
const block = await client.getBlockByHeight(12345);
console.log('Block hash:', block.hash);

// Get a transaction
const tx = await client.getTransaction('abcdef1234567890abcdef1234567890');
console.log('Transaction:', tx);
```

### Working with Smart Contracts

```typescript
import { Wallet, Contract } from 'porw-blockchain-sdk';

// Load wallet
const wallet = new Wallet();
await wallet.loadFromFile('my-wallet.json', 'strong-password');

// Connect to a contract
const contract = new Contract({
  address: 'porw1contract1234567890abcdef1234567890abcdef',
  abi: [...], // Contract ABI
  wallet: wallet
});

// Call a read-only method
const result = await contract.call('getBalance', ['porw1abcdef1234567890abcdef1234567890abcdef']);
console.log('Balance:', result);

// Execute a transaction method
const txResult = await contract.execute('transfer', [
  'porw1abcdef1234567890abcdef1234567890abcdef',
  10.5
]);
console.log('Transaction ID:', txResult.transactionId);
```

### Accessing Protein Folding Data

```typescript
import { PoRWClient } from 'porw-blockchain-sdk';

const client = new PoRWClient('http://localhost:8000');

// Get protein folding data
const proteinData = await client.getProteinFoldingData('protein123');
console.log('Protein structure:', proteinData.structure);

// Get list of available proteins
const proteins = await client.getAvailableProteins();
console.log('Available proteins:', proteins);
```

### Using Hardware Wallets

```typescript
import { HardwareWallet } from 'porw-blockchain-sdk';

// Connect to a Ledger hardware wallet
const hardwareWallet = new HardwareWallet();
await hardwareWallet.connect('ledger');

// Get address
const address = await hardwareWallet.getAddress("m/44'/0'/0'/0/0");
console.log('Hardware wallet address:', address);

// Sign a transaction
const signedTx = await hardwareWallet.signTransaction(transaction);
```

## API Documentation

For detailed API documentation, see the [API.md](./docs/API.md) file.

## Development

### Prerequisites

- Node.js 14+
- npm or yarn

### Building from Source

```bash
# Clone the repository
git clone https://github.com/mwillis775/PoRW-PoRS.git
cd PoRW-PoRS/sdk/javascript

# Install dependencies
npm install

# Build the SDK
npm run build
```

### Running Tests

```bash
npm test
```

## License

This SDK is released under the MIT License. See the [LICENSE](../../LICENSE) file for details.
