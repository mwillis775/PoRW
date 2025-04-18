"""
Stealth address implementation for the PoRW blockchain.

This module provides functions for creating and using stealth addresses,
which allow recipients to receive funds without revealing their identity.

Stealth addresses work by generating a one-time address for each transaction,
making it impossible to link multiple transactions to the same recipient.

The implementation uses Elliptic Curve Diffie-Hellman (ECDH) to derive shared secrets
and generate one-time addresses that only the recipient can detect and spend from.
"""

import os
import hashlib
import base58
import logging
from typing import Tuple, Dict, Any, Optional, List, Union

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend

from ..core.crypto_utils import (
    CURVE,
    load_private_key_from_pem,
    load_public_key_from_pem,
    serialize_private_key,
    serialize_public_key,
    ADDRESS_PREFIX,
    ADDRESS_VERSION,
    TESTNET_ADDRESS_VERSION,
    base58check_encode
)

# Configure logger
logger = logging.getLogger(__name__)

# Constants
STEALTH_ADDRESS_PREFIX = "stealth"
STEALTH_META_PREFIX = "meta"
STEALTH_VERSION = 1


class StealthMetadata:
    """Class representing stealth address metadata."""
    
    def __init__(
        self,
        view_public_key: ec.EllipticCurvePublicKey,
        spend_public_key: ec.EllipticCurvePublicKey,
        nonce: Optional[bytes] = None,
        version: int = STEALTH_VERSION
    ):
        """
        Initialize stealth metadata.
        
        Args:
            view_public_key: The recipient's view public key.
            spend_public_key: The recipient's spend public key.
            nonce: Optional nonce for additional entropy (default: random).
            version: Stealth address version (default: 1).
        """
        self.view_public_key = view_public_key
        self.spend_public_key = spend_public_key
        self.nonce = nonce or os.urandom(32)
        self.version = version
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metadata to a dictionary.
        
        Returns:
            A dictionary representation of the metadata.
        """
        return {
            "view_public_key": serialize_public_key(self.view_public_key).decode('utf-8'),
            "spend_public_key": serialize_public_key(self.spend_public_key).decode('utf-8'),
            "nonce": self.nonce.hex(),
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StealthMetadata':
        """
        Create metadata from a dictionary.
        
        Args:
            data: A dictionary representation of the metadata.
            
        Returns:
            A StealthMetadata object.
        """
        view_public_key = load_public_key_from_pem(data["view_public_key"].encode('utf-8'))
        spend_public_key = load_public_key_from_pem(data["spend_public_key"].encode('utf-8'))
        nonce = bytes.fromhex(data["nonce"])
        version = data.get("version", STEALTH_VERSION)
        
        return cls(view_public_key, spend_public_key, nonce, version)
    
    def to_bytes(self) -> bytes:
        """
        Convert metadata to bytes.
        
        Returns:
            A byte representation of the metadata.
        """
        import json
        return json.dumps(self.to_dict()).encode('utf-8')
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'StealthMetadata':
        """
        Create metadata from bytes.
        
        Args:
            data: A byte representation of the metadata.
            
        Returns:
            A StealthMetadata object.
        """
        import json
        return cls.from_dict(json.loads(data.decode('utf-8')))


class StealthKeys:
    """Class representing stealth keys."""
    
    def __init__(
        self,
        view_private_key: Optional[ec.EllipticCurvePrivateKey] = None,
        spend_private_key: Optional[ec.EllipticCurvePrivateKey] = None
    ):
        """
        Initialize stealth keys.
        
        Args:
            view_private_key: The view private key (default: generate new).
            spend_private_key: The spend private key (default: generate new).
        """
        # Generate or use provided keys
        self.view_private_key = view_private_key or ec.generate_private_key(CURVE, default_backend())
        self.spend_private_key = spend_private_key or ec.generate_private_key(CURVE, default_backend())
        
        # Derive public keys
        self.view_public_key = self.view_private_key.public_key()
        self.spend_public_key = self.spend_private_key.public_key()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert stealth keys to a dictionary.
        
        Returns:
            A dictionary representation of the stealth keys.
        """
        return {
            "view_private_key": serialize_private_key(self.view_private_key).decode('utf-8'),
            "spend_private_key": serialize_private_key(self.spend_private_key).decode('utf-8'),
            "view_public_key": serialize_public_key(self.view_public_key).decode('utf-8'),
            "spend_public_key": serialize_public_key(self.spend_public_key).decode('utf-8')
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StealthKeys':
        """
        Create stealth keys from a dictionary.
        
        Args:
            data: A dictionary representation of the stealth keys.
            
        Returns:
            A StealthKeys object.
        """
        view_private_key = load_private_key_from_pem(data["view_private_key"].encode('utf-8'))
        spend_private_key = load_private_key_from_pem(data["spend_private_key"].encode('utf-8'))
        
        return cls(view_private_key, spend_private_key)
    
    def get_metadata(self) -> StealthMetadata:
        """
        Get metadata for the stealth keys.
        
        Returns:
            A StealthMetadata object.
        """
        return StealthMetadata(self.view_public_key, self.spend_public_key)


def generate_stealth_address(metadata: StealthMetadata, testnet: bool = False) -> str:
    """
    Generate a stealth address from metadata.
    
    Args:
        metadata: The stealth metadata.
        testnet: Whether to generate a testnet address (default: False).
        
    Returns:
        A stealth address.
    """
    # Serialize metadata
    metadata_bytes = metadata.to_bytes()
    
    # Hash metadata
    metadata_hash = hashlib.sha256(metadata_bytes).digest()
    
    # Choose version byte based on network
    version = TESTNET_ADDRESS_VERSION if testnet else ADDRESS_VERSION
    
    # Encode with Base58Check
    encoded_address = base58check_encode(version, metadata_hash[:20])
    
    # Add stealth prefix
    stealth_address = f"{STEALTH_ADDRESS_PREFIX}_{encoded_address}"
    
    logger.debug(f"Generated stealth address: {stealth_address}")
    return stealth_address


def create_stealth_payment_address(
    stealth_address: str,
    sender_private_key: ec.EllipticCurvePrivateKey,
    testnet: bool = False
) -> Tuple[str, Dict[str, Any]]:
    """
    Create a one-time payment address for a stealth recipient.
    
    Args:
        stealth_address: The recipient's stealth address.
        sender_private_key: The sender's private key.
        testnet: Whether to generate a testnet address (default: False).
        
    Returns:
        A tuple containing the payment address and transaction metadata.
    """
    # Extract metadata from stealth address
    if not stealth_address.startswith(f"{STEALTH_ADDRESS_PREFIX}_"):
        raise ValueError(f"Invalid stealth address format: {stealth_address}")
    
    # Extract encoded part
    encoded_part = stealth_address.split('_', 1)[1]
    
    # Decode Base58Check
    version, metadata_hash = base58.b58decode_check(encoded_part)
    
    # TODO: Retrieve full metadata from blockchain or metadata store
    # For now, we'll assume the metadata is provided directly
    # In a real implementation, we would look up the metadata using the hash
    
    # Generate ephemeral key pair
    ephemeral_private_key = ec.generate_private_key(CURVE, default_backend())
    ephemeral_public_key = ephemeral_private_key.public_key()
    
    # Get recipient's view public key from metadata
    # This would normally be retrieved from the blockchain or metadata store
    # For demonstration, we'll use a placeholder
    recipient_view_public_key = ephemeral_public_key  # Placeholder
    recipient_spend_public_key = ephemeral_public_key  # Placeholder
    
    # Compute shared secret using ECDH
    shared_secret = sender_private_key.exchange(
        ec.ECDH(),
        recipient_view_public_key
    )
    
    # Derive payment key using HKDF
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"PoRW-Stealth-Address"
    )
    payment_key = hkdf.derive(shared_secret)
    
    # Convert payment key to scalar
    payment_scalar = int.from_bytes(payment_key, byteorder='big') % CURVE.order
    
    # Compute payment public key: P' = P + H(rA)G
    # where P is the recipient's spend public key, r is the sender's private key,
    # A is the recipient's view public key, and G is the base point
    recipient_spend_public_key_point = recipient_spend_public_key.public_numbers()
    payment_point = ec.EllipticCurvePublicKey.from_encoded_point(
        CURVE,
        recipient_spend_public_key_point.encode_point()
    )
    
    # Generate payment address
    payment_public_key_bytes = payment_point.public_bytes(
        encoding=ec.PublicFormat.CompressedPoint,
        format=ec.PublicFormat.CompressedPoint
    )
    
    # Hash the payment public key
    payment_hash = hashlib.sha256(payment_public_key_bytes).digest()
    ripemd160_hash = hashlib.new('ripemd160', payment_hash).digest()
    
    # Choose version byte based on network
    version = TESTNET_ADDRESS_VERSION if testnet else ADDRESS_VERSION
    
    # Encode with Base58Check
    encoded_address = base58check_encode(version, ripemd160_hash)
    
    # Add human-readable prefix
    payment_address = f"{ADDRESS_PREFIX}_{encoded_address}"
    
    # Create transaction metadata
    tx_metadata = {
        "ephemeral_public_key": serialize_public_key(ephemeral_public_key).decode('utf-8'),
        "stealth_address": stealth_address
    }
    
    logger.debug(f"Created stealth payment address: {payment_address}")
    return payment_address, tx_metadata


def scan_for_stealth_payments(
    view_private_key: ec.EllipticCurvePrivateKey,
    spend_public_key: ec.EllipticCurvePublicKey,
    blockchain_transactions: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Scan the blockchain for stealth payments to the owner of the view private key.
    
    Args:
        view_private_key: The recipient's view private key.
        spend_public_key: The recipient's spend public key.
        blockchain_transactions: List of transactions to scan.
        
    Returns:
        A list of detected stealth payments.
    """
    detected_payments = []
    
    for tx in blockchain_transactions:
        # Check if transaction has stealth metadata
        if "stealth_metadata" not in tx:
            continue
        
        try:
            # Extract ephemeral public key from metadata
            ephemeral_public_key_pem = tx["stealth_metadata"].get("ephemeral_public_key")
            if not ephemeral_public_key_pem:
                continue
            
            ephemeral_public_key = load_public_key_from_pem(ephemeral_public_key_pem.encode('utf-8'))
            
            # Compute shared secret using ECDH
            shared_secret = view_private_key.exchange(
                ec.ECDH(),
                ephemeral_public_key
            )
            
            # Derive payment key using HKDF
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"PoRW-Stealth-Address"
            )
            payment_key = hkdf.derive(shared_secret)
            
            # Convert payment key to scalar
            payment_scalar = int.from_bytes(payment_key, byteorder='big') % CURVE.order
            
            # Compute payment public key: P' = P + H(rA)G
            # where P is the recipient's spend public key, r is the sender's private key,
            # A is the recipient's view public key, and G is the base point
            spend_public_key_point = spend_public_key.public_numbers()
            payment_point = ec.EllipticCurvePublicKey.from_encoded_point(
                CURVE,
                spend_public_key_point.encode_point()
            )
            
            # Generate payment address
            payment_public_key_bytes = payment_point.public_bytes(
                encoding=ec.PublicFormat.CompressedPoint,
                format=ec.PublicFormat.CompressedPoint
            )
            
            # Hash the payment public key
            payment_hash = hashlib.sha256(payment_public_key_bytes).digest()
            ripemd160_hash = hashlib.new('ripemd160', payment_hash).digest()
            
            # Choose version byte based on network
            version = ADDRESS_VERSION  # Assuming mainnet
            
            # Encode with Base58Check
            encoded_address = base58check_encode(version, ripemd160_hash)
            
            # Add human-readable prefix
            payment_address = f"{ADDRESS_PREFIX}_{encoded_address}"
            
            # Check if the payment address matches the transaction recipient
            if tx["recipient"] == payment_address:
                # This payment is for us
                detected_payments.append({
                    "transaction": tx,
                    "payment_key": payment_key.hex(),
                    "is_spent": False  # We would check the blockchain to see if this output is spent
                })
        
        except Exception as e:
            logger.error(f"Error scanning transaction for stealth payments: {e}")
            continue
    
    return detected_payments


def recover_stealth_payment_private_key(
    view_private_key: ec.EllipticCurvePrivateKey,
    spend_private_key: ec.EllipticCurvePrivateKey,
    ephemeral_public_key: ec.EllipticCurvePublicKey
) -> ec.EllipticCurvePrivateKey:
    """
    Recover the private key for a stealth payment.
    
    Args:
        view_private_key: The recipient's view private key.
        spend_private_key: The recipient's spend private key.
        ephemeral_public_key: The ephemeral public key used in the transaction.
        
    Returns:
        The private key for the stealth payment.
    """
    # Compute shared secret using ECDH
    shared_secret = view_private_key.exchange(
        ec.ECDH(),
        ephemeral_public_key
    )
    
    # Derive payment key using HKDF
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"PoRW-Stealth-Address"
    )
    payment_key = hkdf.derive(shared_secret)
    
    # Convert payment key to scalar
    payment_scalar = int.from_bytes(payment_key, byteorder='big') % CURVE.order
    
    # Compute payment private key: x' = x + H(rA)
    # where x is the recipient's spend private key, r is the sender's private key,
    # A is the recipient's view public key
    spend_private_key_value = spend_private_key.private_numbers().private_value
    payment_private_key_value = (spend_private_key_value + payment_scalar) % CURVE.order
    
    # Create payment private key
    payment_private_key = ec.derive_private_key(
        payment_private_key_value,
        CURVE,
        default_backend()
    )
    
    return payment_private_key


def generate_stealth_keys() -> StealthKeys:
    """
    Generate a new set of stealth keys.
    
    Returns:
        A StealthKeys object.
    """
    return StealthKeys()


def create_stealth_wallet() -> Dict[str, Any]:
    """
    Create a new stealth wallet.
    
    Returns:
        A dictionary containing the stealth wallet data.
    """
    # Generate stealth keys
    stealth_keys = generate_stealth_keys()
    
    # Generate stealth address
    metadata = stealth_keys.get_metadata()
    stealth_address = generate_stealth_address(metadata)
    
    # Create wallet data
    wallet_data = {
        "stealth_keys": stealth_keys.to_dict(),
        "stealth_address": stealth_address,
        "metadata": metadata.to_dict()
    }
    
    return wallet_data
