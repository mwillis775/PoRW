#!/usr/bin/env python3
"""
Wallet implementation for the PoRW blockchain.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import ecdsa
import hashlib
import base58

from .structures import Transaction

logger = logging.getLogger(__name__)


class Wallet:
    """
    Wallet for the PoRW blockchain.

    This class provides functionality for:
    1. Creating and managing private/public key pairs
    2. Generating addresses
    3. Creating and signing transactions
    4. Managing balances
    """

    def __init__(self, private_key: Optional[str] = None):
        """
        Initialize a wallet.

        Args:
            private_key: Private key for the wallet (optional)
        """
        if private_key:
            # Import existing private key
            self.private_key = ecdsa.SigningKey.from_string(
                bytes.fromhex(private_key),
                curve=ecdsa.SECP256k1
            )
        else:
            # Generate new private key
            self.private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)

        # Derive public key
        self.public_key = self.private_key.get_verifying_key()

        # Generate address
        self.address = self._generate_address()

        # Transaction cache
        self.transactions = []

        logger.info(f"Initialized wallet with address {self.address}")

    def _generate_address(self) -> str:
        """
        Generate a wallet address from the public key.

        Returns:
            The wallet address
        """
        # Get the public key in compressed format
        public_key_bytes = self.public_key.to_string("compressed")

        # Hash the public key with SHA-256 twice (instead of RIPEMD-160 which may not be available)
        sha256_hash = hashlib.sha256(public_key_bytes).digest()
        sha256_hash2 = hashlib.sha256(sha256_hash).digest()

        # Use the first 20 bytes as a replacement for RIPEMD-160
        hash160 = sha256_hash2[:20]

        # Add version byte (0x00 for mainnet)
        versioned_hash = b'\x00' + hash160

        # Calculate checksum (first 4 bytes of double SHA-256)
        checksum = hashlib.sha256(hashlib.sha256(versioned_hash).digest()).digest()[:4]

        # Combine versioned hash and checksum
        binary_address = versioned_hash + checksum

        # Encode with Base58
        address = base58.b58encode(binary_address).decode('utf-8')

        return address

    def create_transaction(self, recipient: str, amount: float) -> Transaction:
        """
        Create a transaction.

        Args:
            recipient: Recipient address
            amount: Amount to send

        Returns:
            The created transaction
        """
        # Create transaction
        transaction = Transaction(
            sender=self.address,
            recipient=recipient,
            amount=amount,
            timestamp=int(time.time()),
            signature=""
        )

        # Sign transaction
        # Use model_dump instead of to_dict
        transaction_data = transaction.model_dump(exclude={'signature', 'transaction_id'}, mode='json')
        transaction_bytes = json.dumps(transaction_data, sort_keys=True).encode('utf-8')
        signature = self.private_key.sign(transaction_bytes)
        transaction.signature = signature.hex()

        # Add to transaction cache
        self.transactions.append(transaction)

        logger.info(f"Created transaction: {self.address} -> {recipient} ({amount})")

        return transaction

    def verify_transaction(self, transaction: Transaction) -> bool:
        """
        Verify a transaction signature.

        Args:
            transaction: Transaction to verify

        Returns:
            True if the signature is valid, False otherwise
        """
        # Get the transaction data without the signature
        transaction_data = transaction.model_dump(exclude={'signature', 'transaction_id'}, mode='json')
        transaction_bytes = json.dumps(transaction_data, sort_keys=True).encode('utf-8')

        # Get the public key from the sender address
        # In a real implementation, you would need to look up the public key
        # For now, we'll just verify transactions from this wallet
        if transaction.sender != self.address:
            logger.warning(f"Cannot verify transaction from {transaction.sender}")
            return False

        try:
            # Verify the signature
            self.public_key.verify(
                bytes.fromhex(transaction.signature),
                transaction_bytes
            )
            return True

        except ecdsa.BadSignatureError:
            logger.warning(f"Invalid signature for transaction {transaction.id}")
            return False

    def get_balance(self) -> float:
        """
        Get the wallet balance.

        In a real implementation, this would query the blockchain.
        For now, we'll just return a dummy value.

        Returns:
            The wallet balance
        """
        # TODO: Implement real balance calculation
        return 100.0

    def get_transactions(self) -> List[Dict[str, Any]]:
        """
        Get the wallet transactions.

        Returns:
            List of transactions
        """
        return [tx.model_dump(mode='json') for tx in self.transactions]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the wallet to a dictionary.

        Returns:
            Dictionary representation of the wallet
        """
        return {
            'address': self.address,
            'public_key': self.public_key.to_string("compressed").hex(),
            'private_key': self.private_key.to_string().hex(),
            'transactions': [tx.model_dump(mode='json') for tx in self.transactions]
        }

    def save(self, path: Path) -> None:
        """
        Save the wallet to a file.

        Args:
            path: Path to save the wallet to
        """
        # Create parent directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save wallet to file
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

        logger.info(f"Saved wallet to {path}")

    @classmethod
    def load(cls, path: Path) -> 'Wallet':
        """
        Load a wallet from a file.

        Args:
            path: Path to load the wallet from

        Returns:
            The loaded wallet
        """
        # Load wallet from file
        with open(path, 'r') as f:
            wallet_data = json.load(f)

        # Create wallet from private key
        wallet = cls(private_key=wallet_data['private_key'])

        # Load transactions
        for tx_data in wallet_data.get('transactions', []):
            transaction = Transaction(
                sender=tx_data['sender'],
                recipient=tx_data['recipient'],
                amount=tx_data['amount'],
                timestamp=tx_data['timestamp'],
                signature=tx_data['signature']
            )
            wallet.transactions.append(transaction)

        logger.info(f"Loaded wallet from {path}")

        return wallet

    @classmethod
    def create(cls) -> 'Wallet':
        """
        Create a new wallet.

        Returns:
            The created wallet
        """
        return cls()

    @classmethod
    def from_private_key(cls, private_key: str) -> 'Wallet':
        """
        Create a wallet from a private key.

        Args:
            private_key: Private key for the wallet

        Returns:
            The created wallet
        """
        return cls(private_key=private_key)
