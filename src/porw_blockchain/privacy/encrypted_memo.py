"""
Encrypted memo functionality for the PoRW blockchain.

This module provides functions for encrypting and decrypting transaction memos,
allowing users to include private information in their transactions.
"""

import base64
import json
import logging
from typing import Optional, Tuple, Dict, Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.padding import PKCS7
import os

from ..core.crypto_utils import (
    load_private_key_from_pem,
    load_public_key_from_pem,
    CURVE
)

# Configure logger
logger = logging.getLogger(__name__)


def encrypt_memo(
    memo: str,
    recipient_public_key_pem: bytes,
    sender_private_key_pem: Optional[bytes] = None
) -> str:
    """
    Encrypt a memo for the recipient.
    
    Args:
        memo: The memo to encrypt.
        recipient_public_key_pem: The recipient's public key in PEM format.
        sender_private_key_pem: Optional sender's private key in PEM format.
            If provided, the memo will be signed.
    
    Returns:
        The encrypted memo as a base64-encoded string.
    """
    try:
        # Load recipient's public key
        recipient_public_key = load_public_key_from_pem(recipient_public_key_pem)
        
        # Generate ephemeral key pair for ECDH
        ephemeral_private_key = ec.generate_private_key(CURVE)
        ephemeral_public_key = ephemeral_private_key.public_key()
        
        # Perform ECDH to derive shared secret
        shared_secret = ephemeral_private_key.exchange(
            ec.ECDH(),
            recipient_public_key
        )
        
        # Derive encryption key using HKDF
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=None,
            info=b'PoRW-Memo-Encryption'
        ).derive(shared_secret)
        
        # Generate random IV
        iv = os.urandom(16)  # 128 bits for AES
        
        # Pad the memo
        padder = PKCS7(algorithms.AES.block_size).padder()
        memo_bytes = memo.encode('utf-8')
        padded_memo = padder.update(memo_bytes) + padder.finalize()
        
        # Encrypt the memo
        cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_memo) + encryptor.finalize()
        
        # Prepare result
        result = {
            'version': 1,
            'ephemeral_public_key': base64.b64encode(
                ephemeral_public_key.public_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
            ).decode('utf-8'),
            'iv': base64.b64encode(iv).decode('utf-8'),
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8')
        }
        
        # Add signature if sender's private key is provided
        if sender_private_key_pem:
            sender_private_key = load_private_key_from_pem(sender_private_key_pem)
            signature = sender_private_key.sign(
                memo_bytes,
                ec.ECDSA(hashes.SHA256())
            )
            result['signature'] = base64.b64encode(signature).decode('utf-8')
        
        # Encode the result as JSON and then base64
        return base64.b64encode(json.dumps(result).encode('utf-8')).decode('utf-8')
    
    except Exception as e:
        logger.error(f"Error encrypting memo: {e}")
        raise


def decrypt_memo(
    encrypted_memo: str,
    private_key_pem: bytes,
    sender_public_key_pem: Optional[bytes] = None
) -> Tuple[str, bool]:
    """
    Decrypt an encrypted memo.
    
    Args:
        encrypted_memo: The encrypted memo as a base64-encoded string.
        private_key_pem: The recipient's private key in PEM format.
        sender_public_key_pem: Optional sender's public key in PEM format.
            If provided, the memo signature will be verified.
    
    Returns:
        A tuple containing the decrypted memo and a boolean indicating
        whether the signature was verified (if applicable).
    """
    try:
        # Decode the encrypted memo
        encrypted_data = json.loads(base64.b64decode(encrypted_memo).decode('utf-8'))
        
        # Check version
        version = encrypted_data.get('version', 1)
        if version != 1:
            raise ValueError(f"Unsupported encrypted memo version: {version}")
        
        # Load private key
        private_key = load_private_key_from_pem(private_key_pem)
        
        # Decode ephemeral public key
        ephemeral_public_key_bytes = base64.b64decode(encrypted_data['ephemeral_public_key'])
        ephemeral_public_key = serialization.load_der_public_key(ephemeral_public_key_bytes)
        
        # Perform ECDH to derive shared secret
        shared_secret = private_key.exchange(
            ec.ECDH(),
            ephemeral_public_key
        )
        
        # Derive encryption key using HKDF
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=None,
            info=b'PoRW-Memo-Encryption'
        ).derive(shared_secret)
        
        # Decode IV and ciphertext
        iv = base64.b64decode(encrypted_data['iv'])
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        
        # Decrypt the memo
        cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Unpad the plaintext
        unpadder = PKCS7(algorithms.AES.block_size).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        
        # Decode the plaintext
        memo = plaintext.decode('utf-8')
        
        # Verify signature if sender's public key is provided
        signature_verified = False
        if 'signature' in encrypted_data and sender_public_key_pem:
            try:
                sender_public_key = load_public_key_from_pem(sender_public_key_pem)
                signature = base64.b64decode(encrypted_data['signature'])
                sender_public_key.verify(
                    signature,
                    memo.encode('utf-8'),
                    ec.ECDSA(hashes.SHA256())
                )
                signature_verified = True
            except Exception as e:
                logger.warning(f"Signature verification failed: {e}")
        
        return memo, signature_verified
    
    except Exception as e:
        logger.error(f"Error decrypting memo: {e}")
        raise


def is_encrypted_memo(memo: str) -> bool:
    """
    Check if a memo is encrypted.
    
    Args:
        memo: The memo to check.
    
    Returns:
        True if the memo is encrypted, False otherwise.
    """
    try:
        # Try to decode the memo as base64
        decoded = base64.b64decode(memo)
        
        # Try to parse the decoded data as JSON
        data = json.loads(decoded)
        
        # Check if the required fields are present
        return (
            isinstance(data, dict) and
            'version' in data and
            'ephemeral_public_key' in data and
            'iv' in data and
            'ciphertext' in data
        )
    except Exception:
        return False
