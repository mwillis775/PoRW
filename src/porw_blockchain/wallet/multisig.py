"""
Multi-signature wallet functionality for the PoRW blockchain.

This module provides classes and functions for creating and managing
multi-signature wallets, which require multiple signatures to authorize
transactions.
"""

import hashlib
import json
import logging
import os
import time
from typing import Dict, List, Optional, Any, Tuple, Set, Union

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

from ..core.structures import Transaction
from ..core.crypto_utils import (
    CURVE,
    load_private_key_from_pem,
    load_public_key_from_pem,
    serialize_private_key,
    serialize_public_key,
    get_address_from_pubkey,
    is_valid_address,
    sign_message,
    verify_signature
)

# Configure logger
logger = logging.getLogger(__name__)


class MultiSigWallet:
    """
    Multi-signature wallet for the PoRW blockchain.
    
    This class provides functionality for creating and managing multi-signature
    wallets, which require multiple signatures to authorize transactions.
    """
    
    def __init__(
        self,
        wallet_id: Optional[str] = None,
        required_signatures: int = 2,
        total_signers: int = 3,
        private_key: Optional[str] = None,
        public_keys: Optional[List[str]] = None,
        address: Optional[str] = None,
        description: Optional[str] = None
    ):
        """
        Initialize a multi-signature wallet.
        
        Args:
            wallet_id: Unique identifier for the wallet (default: generated).
            required_signatures: Number of signatures required to authorize transactions (default: 2).
            total_signers: Total number of signers (default: 3).
            private_key: The user's private key for this multisig wallet (optional).
            public_keys: List of public keys for all signers (optional).
            address: The multisig wallet address (optional, will be generated if not provided).
            description: Optional description for the wallet.
        """
        self.wallet_id = wallet_id or self._generate_wallet_id()
        self.required_signatures = required_signatures
        self.total_signers = total_signers
        self.private_key = private_key
        self.public_keys = public_keys or []
        self.address = address
        self.description = description or f"MultiSig Wallet ({required_signatures}-of-{total_signers})"
        self.creation_time = int(time.time())
        self.pending_transactions: Dict[str, Dict[str, Any]] = {}
        
        # Generate address if not provided and we have all public keys
        if not self.address and len(self.public_keys) == self.total_signers:
            self.address = self._generate_multisig_address()
        
        logger.info(f"Initialized MultiSigWallet {self.wallet_id} ({required_signatures}-of-{total_signers})")
    
    def _generate_wallet_id(self) -> str:
        """
        Generate a unique wallet ID.
        
        Returns:
            A unique wallet ID.
        """
        import uuid
        return f"multisig_{uuid.uuid4().hex[:8]}"
    
    def _generate_multisig_address(self) -> str:
        """
        Generate a multi-signature wallet address from the public keys.
        
        Returns:
            The multi-signature wallet address.
            
        Raises:
            ValueError: If there are not enough public keys.
        """
        if len(self.public_keys) != self.total_signers:
            raise ValueError(f"Need {self.total_signers} public keys, but only have {len(self.public_keys)}")
        
        # Sort public keys to ensure consistent address generation
        sorted_pubkeys = sorted(self.public_keys)
        
        # Create a string representation of the multisig configuration
        multisig_data = {
            "required_signatures": self.required_signatures,
            "public_keys": sorted_pubkeys
        }
        multisig_str = json.dumps(multisig_data, sort_keys=True)
        
        # Hash the multisig data
        multisig_hash = hashlib.sha256(multisig_str.encode()).digest()
        
        # Create address with a multisig prefix
        from ..core.crypto_utils import base58check_encode, ADDRESS_VERSION
        address = base58check_encode(ADDRESS_VERSION, multisig_hash[:20])
        
        # Add a multisig prefix
        multisig_address = f"ms_{address}"
        
        logger.debug(f"Generated multisig address: {multisig_address}")
        return multisig_address
    
    def add_public_key(self, public_key: str) -> None:
        """
        Add a public key to the multi-signature wallet.
        
        Args:
            public_key: The public key to add.
            
        Raises:
            ValueError: If the wallet already has the maximum number of public keys.
        """
        if len(self.public_keys) >= self.total_signers:
            raise ValueError(f"Wallet already has {self.total_signers} public keys")
        
        if public_key not in self.public_keys:
            self.public_keys.append(public_key)
            logger.debug(f"Added public key to multisig wallet {self.wallet_id}")
            
            # Generate address if we now have all public keys
            if len(self.public_keys) == self.total_signers and not self.address:
                self.address = self._generate_multisig_address()
    
    def create_transaction(
        self,
        recipient: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new multi-signature transaction.
        
        Args:
            recipient: The recipient's address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.
            
        Returns:
            A dictionary containing the transaction data.
            
        Raises:
            ValueError: If the wallet is not fully initialized or the parameters are invalid.
        """
        if not self.address:
            raise ValueError("Wallet address not generated yet. Add all required public keys first.")
        
        if not is_valid_address(recipient):
            raise ValueError(f"Invalid recipient address: {recipient}")
        
        if amount <= 0:
            raise ValueError(f"Invalid amount: {amount}. Amount must be positive.")
        
        if fee is not None and fee < 0:
            raise ValueError(f"Invalid fee: {fee}. Fee must be non-negative.")
        
        # Create transaction data
        transaction_data = {
            "sender": self.address,
            "recipient": recipient,
            "amount": amount,
            "fee": fee,
            "timestamp": int(time.time()),
            "memo": memo,
            "is_multisig": True,
            "required_signatures": self.required_signatures,
            "total_signers": self.total_signers,
            "signatures": {}  # Will be populated as signers sign the transaction
        }
        
        # Generate transaction ID
        tx_hash = hashlib.sha256(json.dumps(transaction_data, sort_keys=True).encode()).hexdigest()
        transaction_data["transaction_id"] = tx_hash
        
        # Store in pending transactions
        self.pending_transactions[tx_hash] = transaction_data
        
        logger.info(f"Created multisig transaction {tx_hash} to {recipient} for {amount}")
        return transaction_data
    
    def sign_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """
        Sign a pending multi-signature transaction.
        
        Args:
            transaction_id: The ID of the transaction to sign.
            
        Returns:
            The updated transaction data.
            
        Raises:
            ValueError: If the transaction is not found or the user's private key is not set.
        """
        if not self.private_key:
            raise ValueError("Private key not set. Cannot sign transaction.")
        
        if transaction_id not in self.pending_transactions:
            raise ValueError(f"Transaction {transaction_id} not found in pending transactions")
        
        # Get transaction data
        transaction_data = self.pending_transactions[transaction_id]
        
        # Create message to sign (transaction data without signatures)
        signing_data = transaction_data.copy()
        signing_data.pop("signatures", None)
        message = json.dumps(signing_data, sort_keys=True)
        
        # Load private key
        private_key_obj = load_private_key_from_pem(self.private_key.encode())
        
        # Sign message
        signature = private_key_obj.sign(
            message.encode(),
            ec.ECDSA(hashes.SHA256())
        )
        
        # Get public key
        public_key = serialize_public_key(private_key_obj.public_key()).decode()
        
        # Add signature to transaction
        transaction_data["signatures"][public_key] = signature.hex()
        
        # Update pending transaction
        self.pending_transactions[transaction_id] = transaction_data
        
        logger.info(f"Signed multisig transaction {transaction_id}")
        return transaction_data
    
    def verify_transaction(self, transaction_id: str) -> bool:
        """
        Verify if a multi-signature transaction has enough valid signatures.
        
        Args:
            transaction_id: The ID of the transaction to verify.
            
        Returns:
            True if the transaction has enough valid signatures, False otherwise.
            
        Raises:
            ValueError: If the transaction is not found.
        """
        if transaction_id not in self.pending_transactions:
            raise ValueError(f"Transaction {transaction_id} not found in pending transactions")
        
        # Get transaction data
        transaction_data = self.pending_transactions[transaction_id]
        
        # Create message that was signed
        signing_data = transaction_data.copy()
        signing_data.pop("signatures", None)
        message = json.dumps(signing_data, sort_keys=True)
        
        # Verify each signature
        valid_signatures = 0
        for public_key, signature_hex in transaction_data["signatures"].items():
            try:
                # Convert signature to bytes
                signature = bytes.fromhex(signature_hex)
                
                # Load public key
                public_key_obj = load_public_key_from_pem(public_key.encode())
                
                # Verify signature
                public_key_obj.verify(
                    signature,
                    message.encode(),
                    ec.ECDSA(hashes.SHA256())
                )
                
                # Signature is valid
                valid_signatures += 1
            except Exception as e:
                logger.warning(f"Invalid signature from {public_key}: {e}")
        
        # Check if we have enough valid signatures
        has_enough_signatures = valid_signatures >= self.required_signatures
        
        logger.info(f"Multisig transaction {transaction_id} has {valid_signatures}/{self.required_signatures} valid signatures")
        return has_enough_signatures
    
    def finalize_transaction(self, transaction_id: str) -> Transaction:
        """
        Finalize a multi-signature transaction that has enough valid signatures.
        
        Args:
            transaction_id: The ID of the transaction to finalize.
            
        Returns:
            A Transaction object ready to be submitted to the network.
            
        Raises:
            ValueError: If the transaction is not found or doesn't have enough valid signatures.
        """
        if not self.verify_transaction(transaction_id):
            raise ValueError(f"Transaction {transaction_id} doesn't have enough valid signatures")
        
        # Get transaction data
        transaction_data = self.pending_transactions[transaction_id]
        
        # Create Transaction object
        transaction = Transaction(
            sender=transaction_data["sender"],
            recipient=transaction_data["recipient"],
            amount=transaction_data["amount"],
            fee=transaction_data["fee"],
            timestamp=transaction_data["timestamp"],
            memo=transaction_data["memo"],
            transaction_id=transaction_id,
            is_memo_encrypted=False  # Assuming memo is not encrypted
        )
        
        # Add multisig data to transaction
        transaction.multisig_data = {
            "required_signatures": self.required_signatures,
            "total_signers": self.total_signers,
            "signatures": transaction_data["signatures"]
        }
        
        # Remove from pending transactions
        self.pending_transactions.pop(transaction_id)
        
        logger.info(f"Finalized multisig transaction {transaction_id}")
        return transaction
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the multi-signature wallet to a dictionary.
        
        Returns:
            A dictionary representation of the wallet.
        """
        return {
            "wallet_id": self.wallet_id,
            "required_signatures": self.required_signatures,
            "total_signers": self.total_signers,
            "public_keys": self.public_keys,
            "address": self.address,
            "description": self.description,
            "creation_time": self.creation_time,
            "pending_transactions": self.pending_transactions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], private_key: Optional[str] = None) -> 'MultiSigWallet':
        """
        Create a multi-signature wallet from a dictionary.
        
        Args:
            data: A dictionary representation of the wallet.
            private_key: The user's private key for this multisig wallet (optional).
            
        Returns:
            A MultiSigWallet object.
        """
        wallet = cls(
            wallet_id=data["wallet_id"],
            required_signatures=data["required_signatures"],
            total_signers=data["total_signers"],
            private_key=private_key,
            public_keys=data["public_keys"],
            address=data["address"],
            description=data.get("description")
        )
        
        wallet.creation_time = data.get("creation_time", int(time.time()))
        wallet.pending_transactions = data.get("pending_transactions", {})
        
        return wallet


def create_multisig_wallet(
    required_signatures: int,
    total_signers: int,
    private_key: str,
    public_keys: Optional[List[str]] = None,
    description: Optional[str] = None
) -> MultiSigWallet:
    """
    Create a new multi-signature wallet.
    
    Args:
        required_signatures: Number of signatures required to authorize transactions.
        total_signers: Total number of signers.
        private_key: The user's private key for this multisig wallet.
        public_keys: List of public keys for all signers (optional).
        description: Optional description for the wallet.
        
    Returns:
        A new MultiSigWallet object.
        
    Raises:
        ValueError: If the parameters are invalid.
    """
    if required_signatures <= 0:
        raise ValueError("Required signatures must be positive")
    
    if total_signers < required_signatures:
        raise ValueError("Total signers must be at least equal to required signatures")
    
    # Create wallet
    wallet = MultiSigWallet(
        required_signatures=required_signatures,
        total_signers=total_signers,
        private_key=private_key,
        public_keys=public_keys or [],
        description=description
    )
    
    # Add user's public key if not already in the list
    if private_key:
        private_key_obj = load_private_key_from_pem(private_key.encode())
        public_key = serialize_public_key(private_key_obj.public_key()).decode()
        
        if public_key not in wallet.public_keys:
            wallet.add_public_key(public_key)
    
    logger.info(f"Created new multisig wallet: {wallet.wallet_id} ({required_signatures}-of-{total_signers})")
    return wallet


def join_multisig_wallet(
    wallet_data: Dict[str, Any],
    private_key: str
) -> MultiSigWallet:
    """
    Join an existing multi-signature wallet.
    
    Args:
        wallet_data: The wallet data to join.
        private_key: The user's private key for this multisig wallet.
        
    Returns:
        A MultiSigWallet object.
    """
    # Create wallet from data
    wallet = MultiSigWallet.from_dict(wallet_data, private_key)
    
    # Add user's public key if not already in the list
    private_key_obj = load_private_key_from_pem(private_key.encode())
    public_key = serialize_public_key(private_key_obj.public_key()).decode()
    
    if public_key not in wallet.public_keys:
        wallet.add_public_key(public_key)
    
    logger.info(f"Joined multisig wallet: {wallet.wallet_id}")
    return wallet


def verify_multisig_transaction(transaction: Dict[str, Any]) -> bool:
    """
    Verify if a multi-signature transaction has enough valid signatures.
    
    Args:
        transaction: The transaction data to verify.
        
    Returns:
        True if the transaction has enough valid signatures, False otherwise.
    """
    # Extract multisig data
    required_signatures = transaction.get("required_signatures", 0)
    signatures = transaction.get("signatures", {})
    
    # Create message that was signed
    signing_data = transaction.copy()
    signing_data.pop("signatures", None)
    message = json.dumps(signing_data, sort_keys=True)
    
    # Verify each signature
    valid_signatures = 0
    for public_key, signature_hex in signatures.items():
        try:
            # Convert signature to bytes
            signature = bytes.fromhex(signature_hex)
            
            # Load public key
            public_key_obj = load_public_key_from_pem(public_key.encode())
            
            # Verify signature
            public_key_obj.verify(
                signature,
                message.encode(),
                ec.ECDSA(hashes.SHA256())
            )
            
            # Signature is valid
            valid_signatures += 1
        except Exception as e:
            logger.warning(f"Invalid signature from {public_key}: {e}")
    
    # Check if we have enough valid signatures
    has_enough_signatures = valid_signatures >= required_signatures
    
    logger.info(f"Multisig transaction has {valid_signatures}/{required_signatures} valid signatures")
    return has_enough_signatures
