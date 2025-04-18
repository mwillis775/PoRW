"""
Stealth wallet functionality for the PoRW blockchain.

This module provides methods for creating and using stealth addresses in the wallet,
allowing users to receive funds without revealing their identity on the blockchain.
"""

import logging
import os
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

from ..core.structures import Transaction
from ..core.crypto_utils import (
    load_private_key_from_pem,
    load_public_key_from_pem,
    serialize_private_key,
    serialize_public_key,
    CURVE
)
from ..privacy.stealth_address import (
    StealthMetadata,
    StealthKeys,
    generate_stealth_address,
    create_stealth_payment_address,
    scan_for_stealth_payments,
    recover_stealth_payment_private_key,
    generate_stealth_keys,
    create_stealth_wallet
)

# Configure logger
logger = logging.getLogger(__name__)


class StealthWallet:
    """
    Wallet extension for stealth address functionality.
    
    This class provides methods for creating and using stealth addresses
    in the wallet.
    """
    
    def __init__(self, private_key: str, address: str):
        """
        Initialize the stealth wallet.
        
        Args:
            private_key: The wallet's private key.
            address: The wallet's address.
        """
        self.private_key = private_key
        self.address = address
        self.stealth_keys = None
        self.stealth_address = None
        
    def create_stealth_keys(self) -> Dict[str, Any]:
        """
        Create a new set of stealth keys.
        
        Returns:
            A dictionary containing the stealth keys data.
        """
        # Generate stealth keys
        self.stealth_keys = generate_stealth_keys()
        
        # Generate stealth address
        metadata = self.stealth_keys.get_metadata()
        self.stealth_address = generate_stealth_address(metadata)
        
        # Create stealth keys data
        stealth_data = {
            "stealth_keys": self.stealth_keys.to_dict(),
            "stealth_address": self.stealth_address,
            "metadata": metadata.to_dict()
        }
        
        logger.info(f"Created stealth address: {self.stealth_address}")
        return stealth_data
    
    def load_stealth_keys(self, stealth_data: Dict[str, Any]) -> None:
        """
        Load stealth keys from data.
        
        Args:
            stealth_data: A dictionary containing the stealth keys data.
        """
        # Load stealth keys
        self.stealth_keys = StealthKeys.from_dict(stealth_data["stealth_keys"])
        self.stealth_address = stealth_data["stealth_address"]
        
        logger.info(f"Loaded stealth address: {self.stealth_address}")
    
    def get_stealth_address(self) -> str:
        """
        Get the stealth address.
        
        Returns:
            The stealth address.
            
        Raises:
            ValueError: If no stealth keys are loaded.
        """
        if not self.stealth_address:
            raise ValueError("No stealth keys loaded")
        
        return self.stealth_address
    
    def create_stealth_payment(
        self,
        recipient_stealth_address: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None
    ) -> Tuple[Transaction, Dict[str, Any]]:
        """
        Create a transaction to a stealth address.
        
        Args:
            recipient_stealth_address: The recipient's stealth address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.
            
        Returns:
            A tuple containing the transaction and stealth metadata.
            
        Raises:
            ValueError: If the parameters are invalid.
        """
        try:
            # Load sender's private key
            sender_private_key = load_private_key_from_pem(self.private_key.encode('utf-8'))
            
            # Create stealth payment address
            payment_address, stealth_metadata = create_stealth_payment_address(
                stealth_address=recipient_stealth_address,
                sender_private_key=sender_private_key
            )
            
            # Create transaction
            from .transaction import TransactionBuilder
            tx_builder = TransactionBuilder(
                private_key=self.private_key
            )
            
            # Create transaction to the payment address
            transaction = tx_builder.create_transaction(
                recipient=payment_address,
                amount=amount,
                fee=fee,
                memo=memo
            )
            
            # Add stealth metadata to transaction
            transaction.stealth_metadata = stealth_metadata
            
            return transaction, stealth_metadata
        
        except Exception as e:
            logger.error(f"Error creating stealth payment: {e}")
            raise
    
    def scan_for_payments(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scan for stealth payments to this wallet.
        
        Args:
            transactions: List of transactions to scan.
            
        Returns:
            A list of detected stealth payments.
            
        Raises:
            ValueError: If no stealth keys are loaded.
        """
        if not self.stealth_keys:
            raise ValueError("No stealth keys loaded")
        
        try:
            # Scan for payments
            detected_payments = scan_for_stealth_payments(
                view_private_key=self.stealth_keys.view_private_key,
                spend_public_key=self.stealth_keys.spend_public_key,
                blockchain_transactions=transactions
            )
            
            return detected_payments
        
        except Exception as e:
            logger.error(f"Error scanning for stealth payments: {e}")
            raise
    
    def recover_payment_private_key(self, ephemeral_public_key_pem: str) -> str:
        """
        Recover the private key for a stealth payment.
        
        Args:
            ephemeral_public_key_pem: The ephemeral public key used in the transaction.
            
        Returns:
            The private key for the stealth payment in PEM format.
            
        Raises:
            ValueError: If no stealth keys are loaded.
        """
        if not self.stealth_keys:
            raise ValueError("No stealth keys loaded")
        
        try:
            # Load ephemeral public key
            ephemeral_public_key = load_public_key_from_pem(ephemeral_public_key_pem.encode('utf-8'))
            
            # Recover payment private key
            payment_private_key = recover_stealth_payment_private_key(
                view_private_key=self.stealth_keys.view_private_key,
                spend_private_key=self.stealth_keys.spend_private_key,
                ephemeral_public_key=ephemeral_public_key
            )
            
            # Serialize private key
            payment_private_key_pem = serialize_private_key(payment_private_key).decode('utf-8')
            
            return payment_private_key_pem
        
        except Exception as e:
            logger.error(f"Error recovering payment private key: {e}")
            raise
