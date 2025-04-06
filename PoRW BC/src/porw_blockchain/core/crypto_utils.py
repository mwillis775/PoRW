# src/porw_blockchain/core/crypto_utils.py
"""
Core cryptographic utilities for the PoRW blockchain.

Handles key generation, signing, verification, address derivation (placeholder),
and balance checking (placeholder). Uses the 'cryptography' library.
"""

import hashlib
import logging
from typing import Tuple, Optional

# --- Cryptography Library Imports ---
# Ensure 'cryptography' is added as a project dependency
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec # Elliptic Curve
from cryptography.hazmat.primitives.asymmetric import utils as asymmetric_utils

# --- Database Imports (for future use in get_balance) ---
from sqlalchemy.orm import Session
# from ..storage import crud # Needed when get_balance is implemented
# from ..storage.database import get_db_session # Needed when get_balance is implemented


logger = logging.getLogger(__name__)

# --- Constants ---
# Using SECP256k1 curve, common in blockchains (like Bitcoin, Ethereum)
CURVE = ec.SECP256k1()
HASH_ALGORITHM = hashes.SHA256()


# --- Key Management ---

def generate_key_pair() -> Tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
    """
    Generates a new private/public key pair using ECDSA on the SECP256k1 curve.

    Returns:
        A tuple containing the private key object and public key object.
    """
    private_key = ec.generate_private_key(CURVE)
    public_key = private_key.public_key()
    return private_key, public_key


def serialize_private_key(private_key: ec.EllipticCurvePrivateKey) -> bytes:
    """
    Serializes a private key object into PEM format bytes.

    Args:
        private_key: The private key object.

    Returns:
        The private key serialized as PEM bytes.
    """
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption() # No password protection
    )


def serialize_public_key(public_key: ec.EllipticCurvePublicKey) -> bytes:
    """
    Serializes a public key object into PEM format bytes.

    Args:
        public_key: The public key object.

    Returns:
        The public key serialized as PEM bytes.
    """
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )


def load_private_key_from_pem(pem_data: bytes) -> ec.EllipticCurvePrivateKey:
    """Loads a private key from PEM formatted bytes."""
    return serialization.load_pem_private_key(pem_data, password=None)


def load_public_key_from_pem(pem_data: bytes) -> ec.EllipticCurvePublicKey:
    """Loads a public key from PEM formatted bytes."""
    return serialization.load_pem_public_key(pem_data)


def get_address_from_pubkey(public_key: ec.EllipticCurvePublicKey) -> str:
    """
    Derives a blockchain address from a public key.

    !! PLACEHOLDER IMPLEMENTATION !!
    Common methods involve hashing the public key (often compressed format)
    and applying checksums/encoding (like Base58Check). This needs specific
    design choices for the PoRW chain's address format.

    Args:
        public_key: The public key object.

    Returns:
        A string representing the derived blockchain address (placeholder).
    """
    # Example placeholder: Hash the uncompressed public key bytes
    # In practice, use compressed format and proper address encoding.
    public_bytes_uncompressed = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    # Simple SHA256 hash, hex encoded - replace with proper address scheme
    address_hash = hashlib.sha256(public_bytes_uncompressed).hexdigest()
    logger.warning("Using placeholder address derivation logic!")
    return f"porw_{address_hash[:32]}" # Example prefix and truncated hash


# --- Signing and Verification ---

def sign_message(private_key: ec.EllipticCurvePrivateKey, message: bytes) -> bytes:
    """
    Signs a message using the provided private key (ECDSA with SHA256).

    Args:
        private_key: The private key object to sign with.
        message: The message bytes to sign.

    Returns:
        The signature bytes (in DER format).
    """
    chosen_hash = HASH_ALGORITHM
    hasher = hashes.Hash(chosen_hash)
    hasher.update(message)
    digest = hasher.finalize()

    signature = private_key.sign(
        digest,
        ec.ECDSA(asymmetric_utils.Prehashed(chosen_hash))
    )
    return signature


def verify_signature(
    public_key_pem: bytes,
    signature: bytes,
    message: bytes
) -> bool:
    """
    Verifies an ECDSA signature against a message using the public key.

    Args:
        public_key_pem: The signer's public key in PEM format bytes.
        signature: The signature bytes (DER format) to verify.
        message: The original message bytes that were signed.

    Returns:
        True if the signature is valid for the message and public key,
        False otherwise.
    """
    try:
        public_key = load_public_key_from_pem(public_key_pem)

        chosen_hash = HASH_ALGORITHM
        hasher = hashes.Hash(chosen_hash)
        hasher.update(message)
        digest = hasher.finalize()

        # Verify the signature
        public_key.verify(
            signature,
            digest,
            ec.ECDSA(asymmetric_utils.Prehashed(chosen_hash))
        )
        return True  # Signature is valid
    except InvalidSignature:
        logger.debug("Signature verification failed: InvalidSignature exception.")
        return False # Signature is invalid
    except Exception as e:
        # Catch potential errors during key loading or verification process
        logger.error(f"Error during signature verification: {e}", exc_info=True)
        return False # Indicate failure due to an unexpected error


# --- Balance Checking ---

def get_balance(address: str) -> float:
    """
    Calculates the balance for a given address by querying the blockchain state.

    !! PLACEHOLDER IMPLEMENTATION !!
    This function requires access to the transaction history associated with
    the address. The actual implementation depends on creating functions in
    `storage/crud.py` (e.g., `get_transactions_for_address`) to retrieve
    relevant transaction data from the database.

    Args:
        address: The blockchain address to check the balance for.

    Returns:
        The calculated balance (float). Returns 0.0 as a placeholder.
    """
    logger.warning(f"Balance check for address {address} is using placeholder logic!")
    # --- BEGIN Balance Calculation Placeholder ---
    # Required Steps (once dependencies are met):
    # 1. Get a database session (e.g., using `with get_db_session() as db:`).
    # 2. Use/create a CRUD function `crud.get_transactions_for_address(db, address)`
    #    to fetch all relevant DbTransaction objects.
    # 3. Iterate through the transactions:
    #    - Add amount if address is the recipient.
    #    - Subtract amount if address is the sender.
    #    - Consider transaction fees if applicable.
    # 4. Return the final calculated balance.

    calculated_balance = 0.0 # Replace with actual calculation later
    # --- END Balance Calculation Placeholder ---

    return calculated_balance

