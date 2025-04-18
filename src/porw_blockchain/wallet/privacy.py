"""
Privacy-enhanced wallet functionality for the PoRW blockchain.

This module provides functions for creating and managing privacy-enhanced
transactions, including encrypted memos, confidential transactions, and
stealth addresses.
"""

import logging
from typing import Optional, Dict, Any, Tuple

from ..core.structures import Transaction
from ..core.crypto_utils import (
    load_private_key_from_pem,
    load_public_key_from_pem,
    get_address_from_pubkey
)
from ..privacy.encrypted_memo import encrypt_memo, decrypt_memo, is_encrypted_memo

# Configure logger
logger = logging.getLogger(__name__)


def create_transaction_with_encrypted_memo(
    sender_private_key_pem: bytes,
    sender_address: str,
    recipient_address: str,
    recipient_public_key_pem: bytes,
    amount: float,
    memo: str,
    fee: Optional[float] = None,
    nonce: Optional[int] = None
) -> Transaction:
    """
    Create a transaction with an encrypted memo.
    
    Args:
        sender_private_key_pem: The sender's private key in PEM format.
        sender_address: The sender's address.
        recipient_address: The recipient's address.
        recipient_public_key_pem: The recipient's public key in PEM format.
        amount: The amount to send.
        memo: The memo to encrypt.
        fee: The transaction fee (default: calculated automatically).
        nonce: Optional nonce for the transaction (default: calculated automatically).
        
    Returns:
        A new unsigned Transaction object with an encrypted memo.
        
    Raises:
        ValueError: If the parameters are invalid.
    """
    try:
        # Encrypt the memo
        encrypted_memo = encrypt_memo(
            memo=memo,
            recipient_public_key_pem=recipient_public_key_pem,
            sender_private_key_pem=sender_private_key_pem
        )
        
        # Create transaction
        from ..wallet.transaction import TransactionBuilder
        tx_builder = TransactionBuilder(
            private_key=sender_private_key_pem.decode('utf-8')
        )
        
        # Create transaction with encrypted memo
        transaction = tx_builder.create_transaction(
            recipient=recipient_address,
            amount=amount,
            fee=fee,
            memo=encrypted_memo,
            nonce=nonce
        )
        
        # Set the encrypted memo flag
        transaction.is_memo_encrypted = True
        
        return transaction
    
    except Exception as e:
        logger.error(f"Error creating transaction with encrypted memo: {e}")
        raise


def decrypt_transaction_memo(
    transaction: Transaction,
    private_key_pem: bytes,
    sender_public_key_pem: Optional[bytes] = None
) -> Tuple[str, bool]:
    """
    Decrypt an encrypted memo in a transaction.
    
    Args:
        transaction: The transaction containing the encrypted memo.
        private_key_pem: The recipient's private key in PEM format.
        sender_public_key_pem: Optional sender's public key in PEM format.
            If provided, the memo signature will be verified.
    
    Returns:
        A tuple containing the decrypted memo and a boolean indicating
        whether the signature was verified (if applicable).
        
    Raises:
        ValueError: If the transaction does not contain an encrypted memo.
    """
    # Check if the transaction has an encrypted memo
    if not transaction.memo or not transaction.is_memo_encrypted:
        raise ValueError("Transaction does not contain an encrypted memo")
    
    try:
        # Decrypt the memo
        decrypted_memo, signature_verified = decrypt_memo(
            encrypted_memo=transaction.memo,
            private_key_pem=private_key_pem,
            sender_public_key_pem=sender_public_key_pem
        )
        
        return decrypted_memo, signature_verified
    
    except Exception as e:
        logger.error(f"Error decrypting transaction memo: {e}")
        raise
