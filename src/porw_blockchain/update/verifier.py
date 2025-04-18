# src/porw_blockchain/update/verifier.py
"""
Update verifier for the PoRW blockchain.

This module provides functionality for verifying the integrity and authenticity
of downloaded updates.
"""

import asyncio
import hashlib
import logging
import os
import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import utils as crypto_utils
from cryptography.hazmat.primitives.serialization import load_pem_public_key

# Configure logger
logger = logging.getLogger(__name__)


class UpdateVerifier:
    """
    Verifier for updates.
    
    This class provides functionality for verifying the integrity and authenticity
    of downloaded updates.
    """

    def __init__(
        self,
        verify_signature: bool = True,
        public_key_path: Optional[Path] = None
    ):
        """
        Initialize the update verifier.
        
        Args:
            verify_signature: Whether to verify the signature of updates (default: True).
            public_key_path: Path to the public key file for signature verification.
                            Required if verify_signature is True.
        """
        self.verify_signature = verify_signature
        self.public_key_path = public_key_path
        self.public_key = None
        
        # Load public key if provided
        if self.verify_signature and self.public_key_path:
            self._load_public_key()

    def _load_public_key(self) -> None:
        """
        Load the public key for signature verification.
        
        Raises:
            ValueError: If the public key file doesn't exist or is invalid.
        """
        if not self.public_key_path or not self.public_key_path.exists():
            raise ValueError(f"Public key file not found: {self.public_key_path}")
        
        try:
            with open(self.public_key_path, "rb") as f:
                self.public_key = load_pem_public_key(f.read())
            
            logger.info(f"Loaded public key from {self.public_key_path}")
        except Exception as e:
            logger.error(f"Error loading public key: {e}")
            raise ValueError(f"Error loading public key: {e}")

    async def verify_update(self, update_path: Path) -> bool:
        """
        Verify an update.
        
        Args:
            update_path: The path to the update to verify.
        
        Returns:
            True if the update is valid, False otherwise.
        """
        logger.info(f"Verifying update at {update_path}")
        
        # Check if file exists
        if not update_path.exists():
            logger.error(f"Update file not found: {update_path}")
            return False
        
        # Verify file integrity
        if not await self._verify_file_integrity(update_path):
            logger.error(f"Update file integrity check failed: {update_path}")
            return False
        
        # Verify signature if enabled
        if self.verify_signature:
            if not await self._verify_signature(update_path):
                logger.error(f"Update signature verification failed: {update_path}")
                return False
        
        # Verify archive if it's an archive
        if update_path.suffix in [".zip", ".tar", ".gz", ".bz2", ".xz"]:
            if not await self._verify_archive(update_path):
                logger.error(f"Update archive verification failed: {update_path}")
                return False
        
        logger.info(f"Update verified successfully: {update_path}")
        return True

    async def _verify_file_integrity(self, file_path: Path) -> bool:
        """
        Verify the integrity of a file.
        
        Args:
            file_path: The path to the file to verify.
        
        Returns:
            True if the file is valid, False otherwise.
        """
        try:
            # Check if file exists and is not empty
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return False
            
            if file_path.stat().st_size == 0:
                logger.error(f"File is empty: {file_path}")
                return False
            
            # Check if file is readable
            with open(file_path, "rb") as f:
                # Read a small chunk to verify it's readable
                f.read(1024)
            
            return True
        except Exception as e:
            logger.error(f"Error verifying file integrity: {e}")
            return False

    async def _verify_signature(self, file_path: Path) -> bool:
        """
        Verify the signature of a file.
        
        Args:
            file_path: The path to the file to verify.
        
        Returns:
            True if the signature is valid, False otherwise.
        """
        if not self.public_key:
            if not self.public_key_path:
                logger.error("No public key provided for signature verification")
                return False
            
            try:
                self._load_public_key()
            except ValueError:
                return False
        
        # Look for signature file
        signature_path = file_path.with_suffix(file_path.suffix + ".sig")
        if not signature_path.exists():
            signature_path = file_path.with_name(file_path.name + ".sig")
        
        if not signature_path.exists():
            logger.error(f"Signature file not found for {file_path}")
            return False
        
        try:
            # Read signature
            with open(signature_path, "rb") as f:
                signature = f.read()
            
            # Calculate file hash
            with open(file_path, "rb") as f:
                file_data = f.read()
            
            # Verify signature
            try:
                self.public_key.verify(
                    signature,
                    file_data,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                
                logger.info(f"Signature verified for {file_path}")
                return True
            except Exception as e:
                logger.error(f"Signature verification failed: {e}")
                return False
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False

    async def _verify_archive(self, archive_path: Path) -> bool:
        """
        Verify an archive file.
        
        Args:
            archive_path: The path to the archive to verify.
        
        Returns:
            True if the archive is valid, False otherwise.
        """
        try:
            # Check if it's a zip file
            if archive_path.suffix == ".zip":
                with zipfile.ZipFile(archive_path, "r") as zip_file:
                    # Test the integrity of the zip file
                    result = zip_file.testzip()
                    if result is not None:
                        logger.error(f"Zip file integrity check failed at {result}")
                        return False
            
            # Check if it's a tar file
            elif archive_path.suffix in [".tar", ".gz", ".bz2", ".xz"]:
                with tarfile.open(archive_path, "r:*") as tar_file:
                    # Check if the tar file can be read
                    for member in tar_file.getmembers():
                        if member.isfile():
                            # Extract a small part of the file to verify it's readable
                            f = tar_file.extractfile(member)
                            if f:
                                f.read(1024)
                                break
            
            return True
        except Exception as e:
            logger.error(f"Error verifying archive: {e}")
            return False

    def calculate_file_hash(self, file_path: Path, algorithm: str = "sha256") -> str:
        """
        Calculate the hash of a file.
        
        Args:
            file_path: The path to the file to hash.
            algorithm: The hash algorithm to use (default: "sha256").
        
        Returns:
            The hash of the file as a hex string.
        
        Raises:
            ValueError: If the hash algorithm is not supported.
            IOError: If there's an error reading the file.
        """
        if algorithm not in hashlib.algorithms_available:
            raise ValueError(f"Hash algorithm not supported: {algorithm}")
        
        try:
            hasher = hashlib.new(algorithm)
            
            with open(file_path, "rb") as f:
                # Read and update hash in chunks
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            raise IOError(f"Error calculating file hash: {e}")

    def verify_file_hash(self, file_path: Path, expected_hash: str, algorithm: str = "sha256") -> bool:
        """
        Verify the hash of a file.
        
        Args:
            file_path: The path to the file to verify.
            expected_hash: The expected hash of the file.
            algorithm: The hash algorithm to use (default: "sha256").
        
        Returns:
            True if the hash matches, False otherwise.
        """
        try:
            actual_hash = self.calculate_file_hash(file_path, algorithm)
            return actual_hash.lower() == expected_hash.lower()
        except Exception as e:
            logger.error(f"Error verifying file hash: {e}")
            return False
