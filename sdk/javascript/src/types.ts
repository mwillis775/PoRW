/**
 * Type definitions for the PoRW Blockchain SDK.
 */

/**
 * API response format.
 */
export interface ApiResponse<T> {
  /** Success status */
  success: boolean;
  /** Response data */
  data: T;
  /** Error message (if success is false) */
  error?: string;
}

/**
 * Blockchain information.
 */
export interface BlockchainInfo {
  /** Current blockchain height */
  height: number;
  /** Hash of the latest block */
  latestBlockHash: string;
  /** Timestamp of the latest block */
  latestBlockTimestamp: number;
  /** Total number of transactions */
  totalTransactions: number;
  /** Current difficulty */
  difficulty: number;
  /** Network name (e.g., 'mainnet', 'testnet') */
  network: string;
  /** Protocol version */
  protocolVersion: string;
  /** Connected peers count */
  connectedPeers: number;
  /** Sync status */
  syncStatus: 'synced' | 'syncing' | 'stalled';
  /** Sync progress (0-100) */
  syncProgress?: number;
}

/**
 * Block data.
 */
export interface Block {
  /** Block hash */
  hash: string;
  /** Block height */
  height: number;
  /** Previous block hash */
  previousHash: string;
  /** Block timestamp */
  timestamp: number;
  /** Block type ('PoRW' or 'PoRS') */
  blockType: 'PoRW' | 'PoRS';
  /** Block creator address */
  creator: string;
  /** Transactions in the block */
  transactions: Transaction[];
  /** Block size in bytes */
  size: number;
  /** Block difficulty */
  difficulty: number;
  /** Block nonce */
  nonce: number;
  /** Block version */
  version: number;
  /** Merkle root of transactions */
  merkleRoot: string;
  /** PoRW-specific data (if blockType is 'PoRW') */
  porwData?: {
    /** Protein ID */
    proteinId: string;
    /** Folding result hash */
    foldingResultHash: string;
    /** Energy score */
    energyScore: number;
    /** Minted amount */
    mintedAmount: number;
  };
  /** PoRS-specific data (if blockType is 'PoRS') */
  porsData?: {
    /** Storage proof hash */
    storageProofHash: string;
    /** Quorum signatures */
    quorumSignatures: string[];
    /** Storage rewards */
    storageRewards: {
      /** Node address */
      address: string;
      /** Reward amount */
      amount: number;
    }[];
  };
}

/**
 * Transaction data.
 */
export interface Transaction {
  /** Transaction ID */
  id: string;
  /** Sender address */
  sender: string;
  /** Recipient address */
  recipient: string;
  /** Transaction amount */
  amount: number;
  /** Transaction fee */
  fee: number;
  /** Transaction timestamp */
  timestamp: number;
  /** Transaction nonce */
  nonce: number;
  /** Transaction memo */
  memo?: string;
  /** Whether the memo is encrypted */
  isMemoEncrypted?: boolean;
  /** Transaction signature */
  signature: string;
  /** Block hash (if confirmed) */
  blockHash?: string;
  /** Block height (if confirmed) */
  blockHeight?: number;
  /** Confirmation status */
  status: 'pending' | 'confirmed' | 'failed';
  /** Number of confirmations */
  confirmations?: number;
  /** Transaction type */
  type?: 'regular' | 'contract' | 'confidential';
  /** Contract-specific data (if type is 'contract') */
  contractData?: {
    /** Contract address */
    contractAddress: string;
    /** Function name */
    function: string;
    /** Function arguments */
    arguments: any[];
  };
  /** Confidential transaction data (if type is 'confidential') */
  confidentialData?: {
    /** Commitment */
    commitment: string;
    /** Range proof */
    rangeProof: string;
  };
}

/**
 * Transaction receipt.
 */
export interface TransactionReceipt {
  /** Transaction ID */
  transactionId: string;
  /** Block hash */
  blockHash: string;
  /** Block height */
  blockHeight: number;
  /** Transaction index in the block */
  transactionIndex: number;
  /** Gas used (for contract transactions) */
  gasUsed?: number;
  /** Status */
  status: 'success' | 'failure';
  /** Error message (if status is 'failure') */
  error?: string;
  /** Events emitted by the transaction */
  events?: any[];
}

/**
 * Network statistics.
 */
export interface NetworkStats {
  /** Total number of nodes */
  totalNodes: number;
  /** Number of mining nodes */
  miningNodes: number;
  /** Number of storage nodes */
  storageNodes: number;
  /** Average block time (in seconds) */
  averageBlockTime: number;
  /** Current hash rate */
  hashRate: number;
  /** Total supply */
  totalSupply: number;
  /** Circulating supply */
  circulatingSupply: number;
  /** Transaction count (last 24 hours) */
  transactionCount24h: number;
  /** Average transaction fee (last 24 hours) */
  averageTransactionFee24h: number;
  /** Network uptime (in seconds) */
  uptime: number;
  /** Protocol version */
  protocolVersion: string;
}

/**
 * Protein data.
 */
export interface ProteinData {
  /** Protein ID */
  id: string;
  /** Protein name */
  name: string;
  /** Amino acid sequence */
  sequence: string;
  /** Protein structure data */
  structure?: {
    /** Structure format (e.g., 'PDB', 'mmCIF') */
    format: string;
    /** Structure data */
    data: string;
    /** Structure visualization URL */
    visualizationUrl?: string;
  };
  /** Energy score */
  energyScore?: number;
  /** Folding timestamp */
  foldingTimestamp?: number;
  /** Folding method */
  foldingMethod?: string;
  /** Scientific value assessment */
  scientificValue?: {
    /** Novelty score (0-100) */
    novelty: number;
    /** Quality score (0-100) */
    quality: number;
    /** Relevance score (0-100) */
    relevance: number;
    /** Overall value score (0-100) */
    overall: number;
  };
  /** References to scientific literature */
  references?: {
    /** Reference title */
    title: string;
    /** Reference URL */
    url: string;
    /** Reference authors */
    authors: string[];
    /** Reference publication date */
    date: string;
  }[];
  /** Metadata */
  metadata?: Record<string, any>;
}

/**
 * Storage node information.
 */
export interface StorageNodeInfo {
  /** Node ID */
  id: string;
  /** Node address */
  address: string;
  /** Node URL */
  url: string;
  /** Node status */
  status: 'online' | 'offline' | 'syncing';
  /** Storage capacity (in bytes) */
  capacity: number;
  /** Used storage (in bytes) */
  used: number;
  /** Uptime (in seconds) */
  uptime: number;
  /** Reliability score (0-100) */
  reliability: number;
  /** Last seen timestamp */
  lastSeen: number;
  /** Node version */
  version: string;
  /** Node location */
  location?: {
    /** Country */
    country: string;
    /** Region */
    region?: string;
    /** City */
    city?: string;
    /** Latitude */
    latitude?: number;
    /** Longitude */
    longitude?: number;
  };
}

/**
 * Wallet options.
 */
export interface WalletOptions {
  /** Network to use ('mainnet' or 'testnet') */
  network?: 'mainnet' | 'testnet';
  /** Client instance */
  client?: any;
  /** Auto-save wallet to local storage */
  autoSave?: boolean;
}

/**
 * Transaction options.
 */
export interface TransactionOptions {
  /** Transaction fee */
  fee?: number;
  /** Transaction memo */
  memo?: string;
  /** Whether to encrypt the memo */
  encryptMemo?: boolean;
  /** Recipient's public key (required for encrypted memos) */
  recipientPublicKey?: string;
  /** Whether to use confidential transactions */
  confidential?: boolean;
  /** Transaction nonce */
  nonce?: number;
}

/**
 * Contract options.
 */
export interface ContractOptions {
  /** Contract address */
  address: string;
  /** Contract ABI */
  abi: any[];
  /** Wallet instance */
  wallet?: any;
  /** Client instance */
  client?: any;
}

/**
 * Hardware wallet options.
 */
export interface HardwareWalletOptions {
  /** Hardware wallet type */
  type?: 'ledger' | 'trezor';
  /** Derivation path */
  derivationPath?: string;
}
