# src/porw_blockchain/wallet/transaction.py
"""
Transaction creation and signing module for the PoRW blockchain wallet.

This module provides functions for creating, signing, and submitting
transactions to the PoRW blockchain network.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List, Union, Tuple

from ..core.structures import Transaction
from ..core.crypto_utils import (
    sign_message,
    verify_signature,
    get_address_from_pubkey,
    is_valid_address,
    get_balance,
    load_private_key_from_pem,
    load_public_key_from_pem
)
from ..network.client import NetworkClient
from ..privacy.encrypted_memo import encrypt_memo, decrypt_memo, is_encrypted_memo
from ..privacy.confidential_transactions import create_confidential_transaction, verify_confidential_transaction

# Configure logger
logger = logging.getLogger(__name__)


class TransactionBuilder:
    """
    Builder for creating and signing transactions.

    This class provides methods for building, signing, and submitting
    transactions to the PoRW blockchain network.
    """

    def __init__(
        self,
        private_key: str,
        network_client: Optional[NetworkClient] = None,
        testnet: bool = False
    ):
        """
        Initialize the transaction builder.

        Args:
            private_key: The private key for signing transactions.
            network_client: Optional network client for submitting transactions.
            testnet: Whether to use testnet (default: False).
        """
        self.private_key = private_key
        self.network_client = network_client
        self.testnet = testnet

        # Derive public key and address from private key
        from ..core.crypto_utils import get_public_key
        self.public_key = get_public_key(private_key)
        self.address = get_address_from_pubkey(self.public_key)

        logger.debug(f"Initialized TransactionBuilder for address {self.address}")

    def create_transaction(
        self,
        recipient: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None,
        nonce: Optional[int] = None
    ) -> Transaction:
        """
        Create a new transaction.

        Args:
            recipient: The recipient's address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.
            nonce: Optional nonce for the transaction (default: calculated automatically).

        Returns:
            A new unsigned Transaction object.

        Raises:
            ValueError: If the parameters are invalid.
        """
        # Validate recipient address
        if not is_valid_address(recipient):
            raise ValueError(f"Invalid recipient address: {recipient}")

        # Validate amount
        if amount <= 0:
            raise ValueError(f"Invalid amount: {amount}. Amount must be positive.")

        # Get current balance
        balance = self._get_balance()

        # Calculate default fee if not provided
        if fee is None:
            fee = self._calculate_fee(amount, memo)

        # Validate fee
        if fee < 0:
            raise ValueError(f"Invalid fee: {fee}. Fee must be non-negative.")

        # Check if sufficient funds
        if balance < amount + fee:
            raise ValueError(
                f"Insufficient funds. Balance: {balance}, Amount: {amount}, Fee: {fee}"
            )

        # Get nonce if not provided
        if nonce is None:
            nonce = self._get_nonce()

        # Create transaction data
        transaction_data = {
            "sender": self.address,
            "recipient": recipient,
            "amount": amount,
            "fee": fee,
            "timestamp": int(time.time()),
            "nonce": nonce
        }

        # Add memo if provided
        if memo:
            transaction_data["memo"] = memo

        # Create transaction ID (hash of transaction data)
        import hashlib
        tx_hash = hashlib.sha256(json.dumps(transaction_data, sort_keys=True).encode()).hexdigest()

        # Create transaction object
        transaction = Transaction(
            id=tx_hash,
            sender=self.address,
            recipient=recipient,
            amount=amount,
            fee=fee,
            timestamp=transaction_data["timestamp"],
            memo=memo,
            is_memo_encrypted=False,  # Default to unencrypted memo
            signature=None  # Will be signed later
        )

        logger.debug(f"Created transaction {tx_hash} to {recipient} for {amount}")
        return transaction

    def sign_transaction(self, transaction: Transaction) -> Transaction:
        """
        Sign a transaction with the private key.

        Args:
            transaction: The transaction to sign.

        Returns:
            The signed transaction.

        Raises:
            ValueError: If the transaction is already signed or invalid.
        """
        # Check if transaction is already signed
        if transaction.signature:
            raise ValueError(f"Transaction {transaction.id} is already signed")

        # Check if transaction sender matches our address
        if transaction.sender != self.address:
            raise ValueError(
                f"Transaction sender {transaction.sender} does not match wallet address {self.address}"
            )

        # Create transaction data for signing
        tx_data = {
            "id": transaction.id,
            "sender": transaction.sender,
            "receiver": transaction.receiver,
            "amount": transaction.amount,
            "fee": transaction.fee,
            "timestamp": transaction.timestamp,
            "nonce": transaction.nonce
        }

        # Add memo if present
        if transaction.memo:
            tx_data["memo"] = transaction.memo

        # Convert to JSON string
        tx_json = json.dumps(tx_data, sort_keys=True)

        # Sign the transaction
        signature = sign_message(tx_json, self.private_key)

        # Create a new transaction with the signature
        signed_tx = Transaction(
            id=transaction.id,
            sender=transaction.sender,
            receiver=transaction.receiver,
            amount=transaction.amount,
            fee=transaction.fee,
            timestamp=transaction.timestamp,
            nonce=transaction.nonce,
            memo=transaction.memo,
            signature=signature
        )

        logger.debug(f"Signed transaction {transaction.id}")
        return signed_tx

    async def submit_transaction(self, transaction: Transaction) -> Dict[str, Any]:
        """
        Submit a transaction to the network.

        Args:
            transaction: The transaction to submit.

        Returns:
            The response from the network.

        Raises:
            ValueError: If the transaction is invalid or not signed.
            ConnectionError: If there's an error connecting to the network.
        """
        # Check if transaction is signed
        if not transaction.signature:
            raise ValueError(f"Transaction {transaction.id} is not signed")

        # Verify the transaction signature
        tx_data = {
            "id": transaction.id,
            "sender": transaction.sender,
            "receiver": transaction.receiver,
            "amount": transaction.amount,
            "fee": transaction.fee,
            "timestamp": transaction.timestamp,
            "nonce": transaction.nonce
        }

        # Add memo if present
        if transaction.memo:
            tx_data["memo"] = transaction.memo

        # Convert to JSON string
        tx_json = json.dumps(tx_data, sort_keys=True)

        # Get public key from address
        # In a real implementation, this would be stored or derived
        # For now, we'll use the one from initialization
        public_key = self.public_key

        # Verify signature
        if not verify_signature(tx_json, transaction.signature, public_key):
            raise ValueError(f"Invalid signature for transaction {transaction.id}")

        # Check if network client is available
        if not self.network_client:
            raise ValueError("No network client available for submitting transaction")

        try:
            # Submit transaction to network
            response = await self.network_client.submit_transaction(transaction)
            logger.info(f"Submitted transaction {transaction.id} to network")
            return response
        except Exception as e:
            logger.error(f"Error submitting transaction {transaction.id}: {e}")
            raise ConnectionError(f"Failed to submit transaction: {e}")

    def create_and_sign_transaction(
        self,
        recipient: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None,
        nonce: Optional[int] = None
    ) -> Transaction:
        """
        Create and sign a transaction in one step.

        Args:
            recipient: The recipient's address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.
            nonce: Optional nonce for the transaction (default: calculated automatically).

        Returns:
            A signed Transaction object.

        Raises:
            ValueError: If the parameters are invalid.
        """
        # Create transaction
        transaction = self.create_transaction(recipient, amount, fee, memo, nonce)

        # Sign transaction
        signed_transaction = self.sign_transaction(transaction)

        return signed_transaction

    def create_transaction_with_encrypted_memo(
        self,
        recipient: str,
        recipient_public_key_pem: bytes,
        amount: float,
        memo: str,
        fee: Optional[float] = None,
        nonce: Optional[int] = None
    ) -> Transaction:
        """
        Create a transaction with an encrypted memo.

        Args:
            recipient: The recipient's address.
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
            sender_private_key_pem = self.private_key.encode('utf-8')
            encrypted_memo = encrypt_memo(
                memo=memo,
                recipient_public_key_pem=recipient_public_key_pem,
                sender_private_key_pem=sender_private_key_pem
            )

            # Create transaction with encrypted memo
            transaction = self.create_transaction(
                recipient=recipient,
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

    def create_and_sign_transaction_with_encrypted_memo(
        self,
        recipient: str,
        recipient_public_key_pem: bytes,
        amount: float,
        memo: str,
        fee: Optional[float] = None,
        nonce: Optional[int] = None
    ) -> Transaction:
        """
        Create and sign a transaction with an encrypted memo in one step.

        Args:
            recipient: The recipient's address.
            recipient_public_key_pem: The recipient's public key in PEM format.
            amount: The amount to send.
            memo: The memo to encrypt.
            fee: The transaction fee (default: calculated automatically).
            nonce: Optional nonce for the transaction (default: calculated automatically).

        Returns:
            A signed Transaction object with an encrypted memo.

        Raises:
            ValueError: If the parameters are invalid.
        """
        # Create transaction with encrypted memo
        transaction = self.create_transaction_with_encrypted_memo(
            recipient=recipient,
            recipient_public_key_pem=recipient_public_key_pem,
            amount=amount,
            memo=memo,
            fee=fee,
            nonce=nonce
        )

        # Sign transaction
        signed_transaction = self.sign_transaction(transaction)

        return signed_transaction

    async def create_sign_and_submit_transaction_with_encrypted_memo(
        self,
        recipient: str,
        recipient_public_key_pem: bytes,
        amount: float,
        memo: str,
        fee: Optional[float] = None,
        nonce: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create, sign, and submit a transaction with an encrypted memo in one step.

        Args:
            recipient: The recipient's address.
            recipient_public_key_pem: The recipient's public key in PEM format.
            amount: The amount to send.
            memo: The memo to encrypt.
            fee: The transaction fee (default: calculated automatically).
            nonce: Optional nonce for the transaction (default: calculated automatically).

        Returns:
            The response from the network.

        Raises:
            ValueError: If the parameters are invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        # Create and sign transaction with encrypted memo
        signed_transaction = self.create_and_sign_transaction_with_encrypted_memo(
            recipient=recipient,
            recipient_public_key_pem=recipient_public_key_pem,
            amount=amount,
            memo=memo,
            fee=fee,
            nonce=nonce
        )

        # Submit transaction
        response = await self.submit_transaction(signed_transaction)

        return response

    def decrypt_memo(
        self,
        transaction: Transaction,
        sender_public_key_pem: Optional[bytes] = None
    ) -> str:
        """
        Decrypt an encrypted memo in a transaction.

        Args:
            transaction: The transaction containing the encrypted memo.
            sender_public_key_pem: Optional sender's public key in PEM format.
                If provided, the memo signature will be verified.

        Returns:
            The decrypted memo.

        Raises:
            ValueError: If the transaction does not contain an encrypted memo.
        """
        # Check if the transaction has an encrypted memo
        if not transaction.memo or not transaction.is_memo_encrypted:
            raise ValueError("Transaction does not contain an encrypted memo")

        try:
            # Decrypt the memo
            private_key_pem = self.private_key.encode('utf-8')
            decrypted_memo, signature_verified = decrypt_memo(
                encrypted_memo=transaction.memo,
                private_key_pem=private_key_pem,
                sender_public_key_pem=sender_public_key_pem
            )

            if sender_public_key_pem and not signature_verified:
                logger.warning("Memo signature verification failed")

            return decrypted_memo

        except Exception as e:
            logger.error(f"Error decrypting transaction memo: {e}")
            raise

    def create_confidential_transaction(
        self,
        recipient: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None
    ) -> Transaction:
        """
        Create a confidential transaction that hides the amount.

        Args:
            recipient: The recipient's address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.

        Returns:
            A new unsigned confidential Transaction object.

        Raises:
            ValueError: If the parameters are invalid.
        """
        try:
            # Validate recipient address
            if not is_valid_address(recipient):
                raise ValueError(f"Invalid recipient address: {recipient}")

            # Validate amount
            if amount <= 0:
                raise ValueError(f"Invalid amount: {amount}. Amount must be positive.")

            # Get current balance
            balance = self._get_balance()

            # Calculate default fee if not provided
            if fee is None:
                fee = self._calculate_fee(amount, memo)

            # Validate fee
            if fee < 0:
                raise ValueError(f"Invalid fee: {fee}. Fee must be non-negative.")

            # Check if sufficient funds
            if balance < amount + fee:
                raise ValueError(
                    f"Insufficient funds. Balance: {balance}, Amount: {amount}, Fee: {fee}"
                )

            # Create confidential transaction
            sender_private_key_pem = self.private_key.encode('utf-8')
            transaction = create_confidential_transaction(
                sender_private_key=sender_private_key_pem,
                sender_address=self.address,
                recipient_address=recipient,
                amount=amount,
                fee=fee,
                memo=memo
            )

            return transaction

        except Exception as e:
            logger.error(f"Error creating confidential transaction: {e}")
            raise

    def create_and_sign_confidential_transaction(
        self,
        recipient: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None
    ) -> Transaction:
        """
        Create and sign a confidential transaction in one step.

        Args:
            recipient: The recipient's address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.

        Returns:
            A signed confidential Transaction object.

        Raises:
            ValueError: If the parameters are invalid.
        """
        # Create confidential transaction
        transaction = self.create_confidential_transaction(
            recipient=recipient,
            amount=amount,
            fee=fee,
            memo=memo
        )

        # Sign transaction
        signed_transaction = self.sign_transaction(transaction)

        return signed_transaction

    async def create_sign_and_submit_confidential_transaction(
        self,
        recipient: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create, sign, and submit a confidential transaction in one step.

        Args:
            recipient: The recipient's address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.

        Returns:
            The response from the network.

        Raises:
            ValueError: If the parameters are invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        # Create and sign confidential transaction
        signed_transaction = self.create_and_sign_confidential_transaction(
            recipient=recipient,
            amount=amount,
            fee=fee,
            memo=memo
        )

        # Submit transaction
        response = await self.submit_transaction(signed_transaction)

        return response

    async def create_sign_and_submit_transaction(
        self,
        recipient: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None,
        nonce: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create, sign, and submit a transaction in one step.

        Args:
            recipient: The recipient's address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.
            nonce: Optional nonce for the transaction (default: calculated automatically).

        Returns:
            The response from the network.

        Raises:
            ValueError: If the parameters are invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        # Create and sign transaction
        signed_transaction = self.create_and_sign_transaction(
            recipient, amount, fee, memo, nonce
        )

        # Submit transaction
        response = await self.submit_transaction(signed_transaction)

        return response

    def _calculate_fee(self, amount: float, memo: Optional[str] = None) -> float:
        """
        Calculate the transaction fee.

        Args:
            amount: The transaction amount.
            memo: Optional memo to include with the transaction.

        Returns:
            The calculated fee.
        """
        # Base fee
        base_fee = 0.001

        # Add fee based on amount (0.1%)
        amount_fee = amount * 0.001

        # Add fee for memo if present
        memo_fee = 0.0005 if memo else 0

        # Calculate total fee
        total_fee = base_fee + amount_fee + memo_fee

        # Round to 8 decimal places
        total_fee = round(total_fee, 8)

        return total_fee

    def _get_balance(self) -> float:
        """
        Get the current balance for the wallet address.

        Returns:
            The current balance.
        """
        # In a real implementation, this would query the blockchain
        # For now, we'll use the get_balance function from crypto_utils
        return get_balance(self.address)

    def _get_nonce(self) -> int:
        """
        Get the next nonce for the wallet address.

        Returns:
            The next nonce.
        """
        # In a real implementation, this would query the blockchain
        # For now, we'll return a timestamp-based nonce
        return int(time.time() * 1000)


class TransactionMonitor:
    """
    Monitor for tracking transaction status.

    This class provides methods for tracking the status of transactions
    on the PoRW blockchain network.
    """

    def __init__(self, network_client: NetworkClient):
        """
        Initialize the transaction monitor.

        Args:
            network_client: Network client for querying the blockchain.
        """
        self.network_client = network_client
        logger.debug("Initialized TransactionMonitor")

    async def get_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get the status of a transaction.

        Args:
            transaction_id: The ID of the transaction to check.

        Returns:
            A dictionary with transaction status information.

        Raises:
            ValueError: If the transaction ID is invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        try:
            # Query transaction status from network
            status = await self.network_client.get_transaction(transaction_id)
            return status
        except Exception as e:
            logger.error(f"Error getting transaction status for {transaction_id}: {e}")
            raise ConnectionError(f"Failed to get transaction status: {e}")

    async def wait_for_confirmation(
        self,
        transaction_id: str,
        confirmations: int = 6,
        timeout: int = 300,
        check_interval: int = 10
    ) -> Dict[str, Any]:
        """
        Wait for a transaction to be confirmed.

        Args:
            transaction_id: The ID of the transaction to check.
            confirmations: The number of confirmations to wait for (default: 6).
            timeout: The maximum time to wait in seconds (default: 300).
            check_interval: The interval between checks in seconds (default: 10).

        Returns:
            A dictionary with transaction status information.

        Raises:
            ValueError: If the transaction ID is invalid.
            ConnectionError: If there's an error connecting to the network.
            TimeoutError: If the transaction is not confirmed within the timeout.
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Get transaction status
                status = await self.get_transaction_status(transaction_id)

                # Check if transaction is confirmed
                if status.get("confirmations", 0) >= confirmations:
                    logger.info(f"Transaction {transaction_id} confirmed with {status.get('confirmations')} confirmations")
                    return status

                # Wait for next check
                logger.debug(f"Transaction {transaction_id} has {status.get('confirmations', 0)} confirmations, waiting for {confirmations}")
                await asyncio.sleep(check_interval)
            except Exception as e:
                logger.error(f"Error checking transaction status for {transaction_id}: {e}")
                # Continue waiting, might be a temporary network issue
                await asyncio.sleep(check_interval)

        # Timeout reached
        raise TimeoutError(f"Transaction {transaction_id} not confirmed within {timeout} seconds")

    async def get_address_transactions(
        self,
        address: str,
        limit: int = 10,
        offset: int = 0,
        include_pending: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get transactions for an address.

        Args:
            address: The address to get transactions for.
            limit: The maximum number of transactions to return (default: 10).
            offset: The offset for pagination (default: 0).
            include_pending: Whether to include pending transactions (default: True).

        Returns:
            A list of transactions for the address.

        Raises:
            ValueError: If the address is invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        # Validate address
        if not is_valid_address(address):
            raise ValueError(f"Invalid address: {address}")

        try:
            # Query transactions from network
            transactions = await self.network_client.get_address_transactions(
                address, limit, offset, include_pending
            )
            return transactions
        except Exception as e:
            logger.error(f"Error getting transactions for address {address}: {e}")
            raise ConnectionError(f"Failed to get address transactions: {e}")


# Import asyncio at the module level to avoid circular imports
import asyncio
