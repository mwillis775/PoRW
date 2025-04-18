/**
 * Cryptographic utilities for the PoRW Blockchain SDK.
 */

import * as elliptic from 'elliptic';
import * as bip39 from 'bip39';
import * as sha256 from 'js-sha256';
import * as bs58 from 'bs58';

// Initialize elliptic curve
const ec = new elliptic.ec('secp256k1');

/**
 * Generates a key pair from a mnemonic phrase.
 * 
 * @param mnemonic - Mnemonic phrase
 * @returns Object containing private and public keys
 */
export async function generateKeyPair(mnemonic: string): Promise<{ privateKey: string; publicKey: string }> {
  // Convert mnemonic to seed
  const seed = await bip39.mnemonicToSeed(mnemonic);
  
  // Use first 32 bytes of seed as private key
  const privateKeyBytes = seed.slice(0, 32);
  const privateKey = Buffer.from(privateKeyBytes).toString('hex');
  
  // Generate key pair from private key
  const keyPair = ec.keyFromPrivate(privateKey, 'hex');
  const publicKey = keyPair.getPublic(true, 'hex');
  
  return { privateKey, publicKey };
}

/**
 * Generates an address from a public key.
 * 
 * @param publicKey - Public key
 * @param testnet - Whether to generate a testnet address
 * @returns Wallet address
 */
export function addressFromPublicKey(publicKey: string, testnet: boolean = false): string {
  // Hash public key with SHA-256
  const hash = sha256.sha256(Buffer.from(publicKey, 'hex'));
  
  // Take first 20 bytes of hash
  const addressBytes = Buffer.from(hash, 'hex').slice(0, 20);
  
  // Add version byte (0x00 for mainnet, 0x6f for testnet)
  const versionByte = testnet ? 0x6f : 0x00;
  const versionedBytes = Buffer.concat([Buffer.from([versionByte]), addressBytes]);
  
  // Add checksum (first 4 bytes of double SHA-256 of versioned bytes)
  const checksum = Buffer.from(sha256.sha256(sha256.sha256(versionedBytes)), 'hex').slice(0, 4);
  const addressWithChecksum = Buffer.concat([versionedBytes, checksum]);
  
  // Encode with Base58
  const address = bs58.encode(addressWithChecksum);
  
  // Add prefix
  return `porw1${address}`;
}

/**
 * Signs data with a private key.
 * 
 * @param privateKey - Private key
 * @param data - Data to sign
 * @returns Signature as a hex string
 */
export async function signData(privateKey: string, data: string): Promise<string> {
  // Hash data with SHA-256
  const hash = sha256.sha256(data);
  
  // Sign hash with private key
  const keyPair = ec.keyFromPrivate(privateKey, 'hex');
  const signature = keyPair.sign(Buffer.from(hash, 'hex'));
  
  // Convert signature to DER format
  const derSignature = signature.toDER('hex');
  
  return derSignature;
}

/**
 * Verifies a signature.
 * 
 * @param publicKey - Public key
 * @param data - Original data
 * @param signature - Signature to verify
 * @returns Whether the signature is valid
 */
export function verifySignature(publicKey: string, data: string, signature: string): boolean {
  try {
    // Hash data with SHA-256
    const hash = sha256.sha256(data);
    
    // Verify signature
    const keyPair = ec.keyFromPublic(publicKey, 'hex');
    return keyPair.verify(Buffer.from(hash, 'hex'), signature);
  } catch (error) {
    console.error('Error verifying signature:', error);
    return false;
  }
}

/**
 * Encrypts data with a public key.
 * 
 * @param publicKey - Public key
 * @param data - Data to encrypt
 * @returns Encrypted data as a hex string
 */
export function encryptData(publicKey: string, data: string): string {
  // TODO: Implement proper encryption
  // This is a placeholder
  return `encrypted_${data}`;
}

/**
 * Decrypts data with a private key.
 * 
 * @param privateKey - Private key
 * @param encryptedData - Encrypted data
 * @returns Decrypted data
 */
export function decryptData(privateKey: string, encryptedData: string): string {
  // TODO: Implement proper decryption
  // This is a placeholder
  return encryptedData.replace('encrypted_', '');
}
