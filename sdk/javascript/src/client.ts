/**
 * PoRW Blockchain Client
 * 
 * This module provides the main client for interacting with the PoRW Blockchain.
 */

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { 
  BlockchainInfo, 
  Block, 
  Transaction, 
  NetworkStats,
  TransactionReceipt,
  ProteinData,
  StorageNodeInfo,
  ApiResponse
} from './types';

/**
 * Configuration options for the PoRW Blockchain client.
 */
export interface PoRWClientConfig {
  /** Base URL of the PoRW Blockchain node */
  baseUrl: string;
  /** API key for authentication (if required) */
  apiKey?: string;
  /** Timeout for API requests in milliseconds */
  timeout?: number;
  /** Whether to use testnet */
  testnet?: boolean;
}

/**
 * Client for interacting with the PoRW Blockchain.
 */
export class PoRWClient {
  private readonly axios: AxiosInstance;
  private readonly config: PoRWClientConfig;

  /**
   * Creates a new PoRW Blockchain client.
   * 
   * @param baseUrlOrConfig - Base URL of the PoRW Blockchain node or a configuration object
   */
  constructor(baseUrlOrConfig: string | PoRWClientConfig) {
    if (typeof baseUrlOrConfig === 'string') {
      this.config = {
        baseUrl: baseUrlOrConfig,
        timeout: 30000,
        testnet: false
      };
    } else {
      this.config = {
        timeout: 30000,
        testnet: false,
        ...baseUrlOrConfig
      };
    }

    const axiosConfig: AxiosRequestConfig = {
      baseURL: this.config.baseUrl,
      timeout: this.config.timeout,
      headers: {}
    };

    if (this.config.apiKey) {
      axiosConfig.headers = {
        'X-API-Key': this.config.apiKey
      };
    }

    this.axios = axios.create(axiosConfig);
  }

  /**
   * Gets information about the blockchain.
   * 
   * @returns Blockchain information
   */
  async getBlockchainInfo(): Promise<BlockchainInfo> {
    const response = await this.axios.get<ApiResponse<BlockchainInfo>>('/api/blockchain/info');
    return response.data.data;
  }

  /**
   * Gets a block by its height.
   * 
   * @param height - Block height
   * @returns Block data
   */
  async getBlockByHeight(height: number): Promise<Block> {
    const response = await this.axios.get<ApiResponse<Block>>(`/api/blocks/height/${height}`);
    return response.data.data;
  }

  /**
   * Gets a block by its hash.
   * 
   * @param hash - Block hash
   * @returns Block data
   */
  async getBlockByHash(hash: string): Promise<Block> {
    const response = await this.axios.get<ApiResponse<Block>>(`/api/blocks/hash/${hash}`);
    return response.data.data;
  }

  /**
   * Gets the latest blocks.
   * 
   * @param limit - Maximum number of blocks to return (default: 10)
   * @returns Array of blocks
   */
  async getLatestBlocks(limit: number = 10): Promise<Block[]> {
    const response = await this.axios.get<ApiResponse<Block[]>>(`/api/blocks/latest?limit=${limit}`);
    return response.data.data;
  }

  /**
   * Gets a transaction by its ID.
   * 
   * @param txId - Transaction ID
   * @returns Transaction data
   */
  async getTransaction(txId: string): Promise<Transaction> {
    const response = await this.axios.get<ApiResponse<Transaction>>(`/api/transactions/${txId}`);
    return response.data.data;
  }

  /**
   * Gets transactions for an address.
   * 
   * @param address - Wallet address
   * @param limit - Maximum number of transactions to return (default: 50)
   * @param offset - Offset for pagination (default: 0)
   * @returns Array of transactions
   */
  async getTransactionsForAddress(address: string, limit: number = 50, offset: number = 0): Promise<Transaction[]> {
    const response = await this.axios.get<ApiResponse<Transaction[]>>(
      `/api/addresses/${address}/transactions?limit=${limit}&offset=${offset}`
    );
    return response.data.data;
  }

  /**
   * Gets the balance for an address.
   * 
   * @param address - Wallet address
   * @returns Balance in PoRW tokens
   */
  async getBalance(address: string): Promise<number> {
    const response = await this.axios.get<ApiResponse<{ balance: number }>>(`/api/addresses/${address}/balance`);
    return response.data.data.balance;
  }

  /**
   * Submits a raw transaction to the network.
   * 
   * @param rawTransaction - Signed transaction data
   * @returns Transaction receipt
   */
  async submitTransaction(rawTransaction: any): Promise<TransactionReceipt> {
    const response = await this.axios.post<ApiResponse<TransactionReceipt>>(
      '/api/transactions/submit',
      rawTransaction
    );
    return response.data.data;
  }

  /**
   * Gets network statistics.
   * 
   * @returns Network statistics
   */
  async getNetworkStats(): Promise<NetworkStats> {
    const response = await this.axios.get<ApiResponse<NetworkStats>>('/api/network/stats');
    return response.data.data;
  }

  /**
   * Gets protein folding data.
   * 
   * @param proteinId - Protein ID
   * @returns Protein data
   */
  async getProteinFoldingData(proteinId: string): Promise<ProteinData> {
    const response = await this.axios.get<ApiResponse<ProteinData>>(`/api/proteins/${proteinId}`);
    return response.data.data;
  }

  /**
   * Gets a list of available proteins.
   * 
   * @param limit - Maximum number of proteins to return (default: 50)
   * @param offset - Offset for pagination (default: 0)
   * @returns Array of protein IDs and metadata
   */
  async getAvailableProteins(limit: number = 50, offset: number = 0): Promise<ProteinData[]> {
    const response = await this.axios.get<ApiResponse<ProteinData[]>>(
      `/api/proteins?limit=${limit}&offset=${offset}`
    );
    return response.data.data;
  }

  /**
   * Gets information about storage nodes.
   * 
   * @param limit - Maximum number of nodes to return (default: 50)
   * @param offset - Offset for pagination (default: 0)
   * @returns Array of storage node information
   */
  async getStorageNodes(limit: number = 50, offset: number = 0): Promise<StorageNodeInfo[]> {
    const response = await this.axios.get<ApiResponse<StorageNodeInfo[]>>(
      `/api/storage/nodes?limit=${limit}&offset=${offset}`
    );
    return response.data.data;
  }

  /**
   * Gets the estimated transaction fee.
   * 
   * @param priority - Transaction priority ('low', 'medium', or 'high')
   * @returns Estimated fee in PoRW tokens
   */
  async getTransactionFeeEstimate(priority: 'low' | 'medium' | 'high' = 'medium'): Promise<number> {
    const response = await this.axios.get<ApiResponse<{ fee: number }>>(
      `/api/transactions/fee-estimate?priority=${priority}`
    );
    return response.data.data.fee;
  }
}
