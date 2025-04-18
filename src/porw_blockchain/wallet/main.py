# src/porw_blockchain/wallet/main.py
"""
Main wallet module for the PoRW blockchain.

This module provides a unified interface for wallet operations,
including key management, balance checking, transaction creation,
and blockchain querying.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple, Callable

from ..core.structures import Transaction
from ..core.crypto_utils import (
    load_private_key_from_pem,
    load_public_key_from_pem,
    is_valid_address,
    get_address_from_pubkey,
    sign_message,
    verify_signature
)
from ..network.client import NetworkClient
from .key_management import (
    create_new_wallet,
    save_wallet,
    load_wallet,
    list_wallets,
    create_wallet_backup,
    restore_wallet_from_backup,
    export_wallet_to_json,
    import_wallet_from_json
)
from .balance import BalanceTracker
from .transaction import TransactionBuilder, TransactionMonitor
from .blockchain import BlockchainMonitor, BlockchainQuery
from .zkp import ZKPWallet
from .stealth import StealthWallet
from .mixing import MixingWallet
from .multisig import MultiSigWallet, create_multisig_wallet, join_multisig_wallet
from .contacts import AddressBook, Contact, create_contact
from .labels import TransactionLabelManager, TransactionLabel, create_transaction_label
from .recurring import RecurringTransactionManager, RecurringTransaction, RecurrenceInterval, create_recurring_transaction
from .hardware import HardwareWalletManager, HardwareWalletType, hardware_wallet_manager
from .qrcode import QRCodeGenerator, QRCodeParser, QRCodeScanner, PaymentRequest, QRCodeType, QRCodeError, parse_payment_qr_code

# Configure logger
logger = logging.getLogger(__name__)


class Wallet:
    """
    Main wallet class for the PoRW blockchain.

    This class provides a unified interface for wallet operations,
    including key management, balance checking, transaction creation,
    and blockchain querying.
    """

    def __init__(
        self,
        network_client: Optional[NetworkClient] = None,
        testnet: bool = False,
        auto_connect: bool = True
    ):
        """
        Initialize the wallet.

        Args:
            network_client: Optional network client for interacting with the blockchain.
            testnet: Whether to use testnet (default: False).
            auto_connect: Whether to automatically connect to the network (default: True).
        """
        self.testnet = testnet
        self.network_id = "testnet" if testnet else "mainnet"

        # Create network client if not provided
        if network_client is None:
            api_url = "http://localhost:8080"
            self.network_client = NetworkClient(api_url=api_url, testnet=testnet)
        else:
            self.network_client = network_client

        # Initialize wallet components
        self.balance_tracker = BalanceTracker(self.network_client)
        self.blockchain_monitor = BlockchainMonitor(self.network_client)
        self.blockchain_query = BlockchainQuery(self.network_client)
        self.transaction_monitor = TransactionMonitor(self.network_client)

        # Wallet state
        self.wallet_data = None
        self.private_key = None
        self.public_key = None
        self.address = None
        self.transaction_builder = None
        self.zkp_wallet = None
        self.stealth_wallet = None
        self.mixing_wallet = None
        self.multisig_wallets = {}  # {wallet_id: MultiSigWallet}
        self.address_book = AddressBook()
        self.label_manager = TransactionLabelManager()
        self.recurring_manager = RecurringTransactionManager()
        self.is_connected = False

        # Hardware wallet state
        self.hardware_wallet_manager = hardware_wallet_manager
        self.using_hardware_wallet = False
        self.hardware_wallet_type = None
        self.hardware_derivation_path = None

        # QR code scanner
        self.qr_scanner = None

        # Connect to network if auto_connect is True
        if auto_connect:
            asyncio.create_task(self.connect())

        logger.debug(f"Initialized Wallet for {self.network_id}")

    async def connect(self) -> bool:
        """
        Connect to the blockchain network.

        Returns:
            True if connection was successful, False otherwise.
        """
        try:
            self.is_connected = await self.network_client.connect()

            if self.is_connected:
                # Start blockchain monitor
                await self.blockchain_monitor.start()

                # Start balance tracker if wallet is loaded
                if self.address:
                    await self.balance_tracker.track_address(self.address)

                logger.info("Connected to blockchain network")
            else:
                logger.warning("Failed to connect to blockchain network")

            return self.is_connected
        except Exception as e:
            logger.error(f"Error connecting to blockchain network: {e}")
            self.is_connected = False
            return False

    async def disconnect(self) -> None:
        """
        Disconnect from the blockchain network.
        """
        try:
            # Stop blockchain monitor
            await self.blockchain_monitor.stop()

            # Stop balance tracker
            await self.balance_tracker.stop()

            # Disconnect network client
            await self.network_client.disconnect()

            self.is_connected = False
            logger.info("Disconnected from blockchain network")
        except Exception as e:
            logger.error(f"Error disconnecting from blockchain network: {e}")

    # --- Wallet Management ---

    def create_wallet(self, password: str) -> Dict[str, Any]:
        """
        Create a new wallet.

        Args:
            password: The password to encrypt the wallet with.

        Returns:
            The wallet data.
        """
        # Create new wallet
        self.wallet_data = create_new_wallet(password, testnet=self.testnet)

        # Set wallet state
        self.private_key = self.wallet_data["private_key"]
        self.public_key = self.wallet_data["public_key"]
        self.address = self.wallet_data["address"]

        # Create transaction builder
        self.transaction_builder = TransactionBuilder(
            private_key=self.private_key,
            network_client=self.network_client,
            testnet=self.testnet
        )

        # Create ZKP wallet
        self.zkp_wallet = ZKPWallet(
            private_key=self.private_key,
            address=self.address
        )

        # Create stealth wallet
        self.stealth_wallet = StealthWallet(
            private_key=self.private_key,
            address=self.address
        )

        # Load stealth keys if available
        if "stealth_data" in self.wallet_data:
            self.stealth_wallet.load_stealth_keys(self.wallet_data["stealth_data"])

        # Create mixing wallet
        self.mixing_wallet = MixingWallet(
            private_key=self.private_key,
            address=self.address
        )

        # Load mixing data if available
        if "mixing_data" in self.wallet_data:
            # In a real implementation, this would load mixing data
            pass

        # Load multisig wallets if available
        if "multisig_wallets" in self.wallet_data:
            for wallet_id, wallet_data in self.wallet_data["multisig_wallets"].items():
                self.multisig_wallets[wallet_id] = MultiSigWallet.from_dict(
                    wallet_data,
                    private_key=self.private_key
                )

        # Load address book if available
        if "address_book" in self.wallet_data:
            self.address_book = AddressBook.from_dict(self.wallet_data["address_book"])

        # Load transaction labels if available
        if "transaction_labels" in self.wallet_data:
            self.label_manager = TransactionLabelManager.from_dict(self.wallet_data["transaction_labels"])

        # Load recurring transactions if available
        if "recurring_transactions" in self.wallet_data:
            self.recurring_manager = RecurringTransactionManager.from_dict(self.wallet_data["recurring_transactions"])

        # Start tracking balance if connected
        if self.is_connected:
            asyncio.create_task(self.balance_tracker.track_address(self.address))

        logger.info(f"Created new wallet with address: {self.address}")
        return self.wallet_data

    def load_wallet_from_file(self, wallet_path: Union[str, Path], password: str) -> Dict[str, Any]:
        """
        Load a wallet from a file.

        Args:
            wallet_path: Path to the wallet file.
            password: The password to decrypt the wallet with.

        Returns:
            The wallet data.

        Raises:
            FileNotFoundError: If the wallet file doesn't exist.
            ValueError: If decryption fails (wrong password).
        """
        # Load wallet
        self.wallet_data = load_wallet(wallet_path, password)

        # Set wallet state
        self.private_key = self.wallet_data["private_key"]
        self.public_key = self.wallet_data["public_key"]
        self.address = self.wallet_data["address"]

        # Create transaction builder
        self.transaction_builder = TransactionBuilder(
            private_key=self.private_key,
            network_client=self.network_client,
            testnet=self.testnet
        )

        # Start tracking balance if connected
        if self.is_connected:
            asyncio.create_task(self.balance_tracker.track_address(self.address))

        logger.info(f"Loaded wallet with address: {self.address}")
        return self.wallet_data

    def load_wallet_from_data(self, wallet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load a wallet from data.

        Args:
            wallet_data: The wallet data.

        Returns:
            The wallet data.

        Raises:
            ValueError: If the wallet data is invalid.
        """
        # Validate wallet data
        required_fields = ["private_key", "public_key", "address"]
        if not all(field in wallet_data for field in required_fields):
            raise ValueError("Wallet data missing required fields")

        # Set wallet state
        self.wallet_data = wallet_data
        self.private_key = wallet_data["private_key"]
        self.public_key = wallet_data["public_key"]
        self.address = wallet_data["address"]

        # Create transaction builder
        self.transaction_builder = TransactionBuilder(
            private_key=self.private_key,
            network_client=self.network_client,
            testnet=self.testnet
        )

        # Create ZKP wallet
        self.zkp_wallet = ZKPWallet(
            private_key=self.private_key,
            address=self.address
        )

        # Create stealth wallet
        self.stealth_wallet = StealthWallet(
            private_key=self.private_key,
            address=self.address
        )

        # Load stealth keys if available
        if "stealth_data" in self.wallet_data:
            self.stealth_wallet.load_stealth_keys(self.wallet_data["stealth_data"])

        # Create mixing wallet
        self.mixing_wallet = MixingWallet(
            private_key=self.private_key,
            address=self.address
        )

        # Load mixing data if available
        if "mixing_data" in self.wallet_data:
            # In a real implementation, this would load mixing data
            pass

        # Load multisig wallets if available
        if "multisig_wallets" in self.wallet_data:
            for wallet_id, wallet_data in self.wallet_data["multisig_wallets"].items():
                self.multisig_wallets[wallet_id] = MultiSigWallet.from_dict(
                    wallet_data,
                    private_key=self.private_key
                )

        # Load address book if available
        if "address_book" in self.wallet_data:
            self.address_book = AddressBook.from_dict(self.wallet_data["address_book"])

        # Load transaction labels if available
        if "transaction_labels" in self.wallet_data:
            self.label_manager = TransactionLabelManager.from_dict(self.wallet_data["transaction_labels"])

        # Load recurring transactions if available
        if "recurring_transactions" in self.wallet_data:
            self.recurring_manager = RecurringTransactionManager.from_dict(self.wallet_data["recurring_transactions"])

        # Start tracking balance if connected
        if self.is_connected:
            asyncio.create_task(self.balance_tracker.track_address(self.address))

        logger.info(f"Loaded wallet with address: {self.address}")
        return self.wallet_data

    def save_wallet(self, password: str, wallet_name: Optional[str] = None) -> Path:
        """
        Save the wallet to a file.

        Args:
            password: The password to encrypt the wallet with.
            wallet_name: Optional name for the wallet file.

        Returns:
            The path to the saved wallet file.

        Raises:
            ValueError: If no wallet is loaded.
        """
        if not self.wallet_data:
            raise ValueError("No wallet loaded")

        # Save wallet
        wallet_path = save_wallet(self.wallet_data, password, wallet_name)

        logger.info(f"Saved wallet to {wallet_path}")
        return wallet_path

    def backup_wallet(self, password: str, backup_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Create a backup of the wallet.

        Args:
            password: The password to encrypt the backup with.
            backup_path: Optional path for the backup file.

        Returns:
            The path to the backup file.

        Raises:
            ValueError: If no wallet is loaded.
        """
        if not self.wallet_data:
            raise ValueError("No wallet loaded")

        # Create backup
        backup_path = create_wallet_backup(self.wallet_data, password, backup_path)

        logger.info(f"Created wallet backup at {backup_path}")
        return backup_path

    def export_wallet(self, include_private_key: bool = False) -> Dict[str, Any]:
        """
        Export the wallet to a JSON-serializable format.

        Args:
            include_private_key: Whether to include the private key in the export.

        Returns:
            A dictionary containing the exported wallet data.

        Raises:
            ValueError: If no wallet is loaded.
        """
        if not self.wallet_data:
            raise ValueError("No wallet loaded")

        # Export wallet
        export_data = export_wallet_to_json(self.wallet_data, include_private_key)

        logger.info(f"Exported wallet with address: {self.address}")
        return export_data

    @staticmethod
    def list_available_wallets() -> List[Dict[str, Any]]:
        """
        List all available wallets.

        Returns:
            A list of dictionaries containing wallet metadata.
        """
        return list_wallets()

    @staticmethod
    def import_wallet_from_backup(
        backup_path: Union[str, Path],
        password: str,
        new_password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Import a wallet from a backup file.

        Args:
            backup_path: Path to the backup file.
            password: The password to decrypt the backup with.
            new_password: Optional new password for the imported wallet.

        Returns:
            The imported wallet data.

        Raises:
            FileNotFoundError: If the backup file doesn't exist.
            ValueError: If decryption fails (wrong password).
        """
        # Restore wallet from backup
        wallet_data = restore_wallet_from_backup(backup_path, password)

        # Save with new password if provided
        if new_password:
            save_wallet(wallet_data, new_password)

        logger.info(f"Imported wallet with address: {wallet_data['address']}")
        return wallet_data

    # --- Balance Operations ---

    async def get_balance(self) -> float:
        """
        Get the balance of the loaded wallet.

        Returns:
            The current balance.

        Raises:
            ValueError: If no wallet is loaded.
            ConnectionError: If there's an error connecting to the network.
        """
        if not self.address:
            raise ValueError("No wallet loaded")

        return await self.balance_tracker.get_balance(self.address)

    async def get_transaction_history(
        self,
        limit: int = 100,
        offset: int = 0,
        include_pending: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get the transaction history of the loaded wallet.

        Args:
            limit: The maximum number of transactions to return (default: 100).
            offset: The offset for pagination (default: 0).
            include_pending: Whether to include pending transactions (default: True).

        Returns:
            A list of transactions.

        Raises:
            ValueError: If no wallet is loaded.
            ConnectionError: If there's an error connecting to the network.
        """
        if not self.address:
            raise ValueError("No wallet loaded")

        return await self.network_client.get_transactions_for_address(
            self.address, limit, offset, include_pending
        )

    async def get_balance_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the wallet's balance and transaction history.

        Returns:
            A dictionary with balance summary information.

        Raises:
            ValueError: If no wallet is loaded.
            ConnectionError: If there's an error connecting to the network.
        """
        if not self.address:
            raise ValueError("No wallet loaded")

        return await self.balance_tracker.get_balance_summary(self.address)

    # --- Transaction Operations ---

    async def create_transaction(
        self,
        recipient: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None
    ) -> Transaction:
        """
        Create a new transaction.

        Args:
            recipient: The recipient's address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.

        Returns:
            A new unsigned Transaction object.

        Raises:
            ValueError: If no wallet is loaded or if the parameters are invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        if not self.transaction_builder:
            raise ValueError("No wallet loaded")

        return self.transaction_builder.create_transaction(recipient, amount, fee, memo)

    async def sign_transaction(self, transaction: Transaction) -> Transaction:
        """
        Sign a transaction.

        Args:
            transaction: The transaction to sign.

        Returns:
            The signed transaction.

        Raises:
            ValueError: If no wallet is loaded or if the transaction is invalid.
        """
        if not self.transaction_builder:
            raise ValueError("No wallet loaded")

        return self.transaction_builder.sign_transaction(transaction)

    async def create_and_sign_transaction(
        self,
        recipient: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None
    ) -> Transaction:
        """
        Create and sign a transaction in one step.

        Args:
            recipient: The recipient's address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.

        Returns:
            A signed Transaction object.

        Raises:
            ValueError: If no wallet is loaded or if the parameters are invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        if self.using_hardware_wallet:
            # Create transaction using a temporary transaction builder
            from .transaction import TransactionBuilder
            temp_builder = TransactionBuilder(
                private_key="",  # Not needed for creation
                network_client=self.network_client,
                testnet=self.testnet
            )

            # Override the address
            temp_builder.address = self.address

            # Create transaction
            transaction = temp_builder.create_transaction(recipient, amount, fee, memo)

            # Sign with hardware wallet
            if not self.hardware_derivation_path:
                raise ValueError("Hardware wallet derivation path not set")

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

            # Sign with hardware wallet
            signed_tx = self.hardware_wallet_manager.sign_transaction(
                transaction=transaction,
                derivation_path=self.hardware_derivation_path
            )

            return signed_tx
        elif self.transaction_builder:
            return self.transaction_builder.create_and_sign_transaction(recipient, amount, fee, memo)
        else:
            raise ValueError("No wallet loaded")

    async def submit_transaction(self, transaction: Transaction) -> Dict[str, Any]:
        """
        Submit a transaction to the network.

        Args:
            transaction: The transaction to submit.

        Returns:
            The submission response.

        Raises:
            ValueError: If the transaction is invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        if not self.transaction_builder:
            raise ValueError("No wallet loaded")

        return await self.transaction_builder.submit_transaction(transaction)

    async def send(
        self,
        recipient: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create, sign, and submit a transaction in one step.

        Args:
            recipient: The recipient's address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.

        Returns:
            The submission response.

        Raises:
            ValueError: If no wallet is loaded or if the parameters are invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        if not self.transaction_builder:
            raise ValueError("No wallet loaded")

        # Create and sign transaction
        transaction = await self.create_and_sign_transaction(recipient, amount, fee, memo)

        # Submit transaction
        response = await self.submit_transaction(transaction)

        logger.info(f"Sent {amount} to {recipient} (transaction ID: {transaction.transaction_id})")
        return response

    async def get_transaction_fee_estimate(self, priority: str = "medium") -> float:
        """
        Get an estimate of the transaction fee.

        Args:
            priority: The transaction priority (default: "medium").
                     Options: "low", "medium", "high"

        Returns:
            The estimated fee.

        Raises:
            ValueError: If priority is invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        return await self.blockchain_query.get_transaction_fee_estimate(priority)

    # --- Blockchain Operations ---

    async def get_blockchain_info(self) -> Dict[str, Any]:
        """
        Get general information about the blockchain.

        Returns:
            A dictionary with blockchain information.

        Raises:
            ConnectionError: If there's an error connecting to the network.
        """
        return await self.blockchain_query.get_blockchain_info()

    async def get_block_by_hash(self, block_hash: str) -> Dict[str, Any]:
        """
        Get a block by hash.

        Args:
            block_hash: The block hash.

        Returns:
            The block data.

        Raises:
            ValueError: If the hash is invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        return await self.blockchain_query.get_block_by_hash(block_hash)

    async def get_block_by_height(self, height: int) -> Dict[str, Any]:
        """
        Get a block by height.

        Args:
            height: The block height.

        Returns:
            The block data.

        Raises:
            ValueError: If the height is invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        return await self.blockchain_query.get_block_by_height(height)

    async def get_latest_blocks(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get the latest blocks.

        Args:
            count: The number of blocks to get (default: 10).

        Returns:
            A list of the latest blocks.

        Raises:
            ValueError: If count is invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        return await self.blockchain_query.get_latest_blocks(count)

    async def get_transaction(self, tx_id: str) -> Dict[str, Any]:
        """
        Get a transaction by ID.

        Args:
            tx_id: The transaction ID.

        Returns:
            The transaction data.

        Raises:
            ValueError: If the transaction ID is invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        return await self.blockchain_query.get_transaction(tx_id)

    async def get_network_stats(self) -> Dict[str, Any]:
        """
        Get network statistics.

        Returns:
            A dictionary with network statistics.

        Raises:
            ConnectionError: If there's an error connecting to the network.
        """
        return await self.blockchain_query.get_network_stats()

    # --- Event Handling ---

    def on_new_block(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for new block events.

        Args:
            callback: The callback function to call when a new block is found.
        """
        self.blockchain_monitor.register_callback("new_block", callback)

    def on_balance_change(self, callback: Callable[[str, float, float], None]) -> None:
        """
        Register a callback for balance change events.

        Args:
            callback: The callback function to call when the balance changes.
                     The callback receives (address, new_balance, old_balance).
        """
        self.balance_tracker.register_callback("balance_change", callback)

    def on_transaction_received(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for transaction received events.

        Args:
            callback: The callback function to call when a transaction is received.
        """
        self.balance_tracker.register_callback("transaction_received", callback)

    def on_transaction_sent(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for transaction sent events.

        Args:
            callback: The callback function to call when a transaction is sent.
        """
        self.balance_tracker.register_callback("transaction_sent", callback)

    # --- Utility Methods ---

    @staticmethod
    def is_valid_address(address: str) -> bool:
        """
        Check if an address is valid.

        Args:
            address: The address to check.

        Returns:
            True if the address is valid, False otherwise.
        """
        return is_valid_address(address)

    @staticmethod
    def get_address_network(address: str) -> Optional[str]:
        """
        Get the network of an address.

        Args:
            address: The address to check.

        Returns:
            "mainnet", "testnet", or None if the address is invalid.
        """
        from ..core.crypto_utils import get_address_network
        return get_address_network(address)

    def connect_hardware_wallet(self, wallet_type: HardwareWalletType, derivation_path: str = "m/44'/0'/0'/0/0") -> bool:
        """
        Connect to a hardware wallet.

        Args:
            wallet_type: The type of hardware wallet to connect to.
            derivation_path: The BIP32 derivation path to use (default: "m/44'/0'/0'/0/0").

        Returns:
            True if connection was successful, False otherwise.
        """
        logger.info(f"Connecting to {wallet_type.value} hardware wallet")

        # Connect to hardware wallet
        if self.hardware_wallet_manager.connect_wallet(wallet_type):
            # Get address from hardware wallet
            try:
                address = self.hardware_wallet_manager.get_wallet_address(
                    derivation_path=derivation_path,
                    testnet=self.testnet
                )

                # Set wallet state
                self.using_hardware_wallet = True
                self.hardware_wallet_type = wallet_type
                self.hardware_derivation_path = derivation_path
                self.address = address

                # Get device info
                device_info = self.hardware_wallet_manager.get_device_info()
                logger.info(f"Connected to {device_info['type']} {device_info['model']} with address {address}")

                # Initialize wallet components that don't require private key
                if self.is_connected:
                    asyncio.create_task(self.balance_tracker.track_address(self.address))

                return True
            except Exception as e:
                logger.error(f"Error getting address from hardware wallet: {e}")
                self.hardware_wallet_manager.disconnect_wallet(wallet_type)
                return False
        else:
            logger.error(f"Failed to connect to {wallet_type.value} hardware wallet")
            return False

    def disconnect_hardware_wallet(self) -> None:
        """
        Disconnect from the hardware wallet.
        """
        if self.using_hardware_wallet and self.hardware_wallet_type:
            logger.info(f"Disconnecting from {self.hardware_wallet_type.value} hardware wallet")
            self.hardware_wallet_manager.disconnect_wallet(self.hardware_wallet_type)

            # Reset hardware wallet state
            self.using_hardware_wallet = False
            self.hardware_wallet_type = None
            self.hardware_derivation_path = None
            self.address = None

    def is_hardware_wallet_connected(self) -> bool:
        """
        Check if a hardware wallet is connected.

        Returns:
            True if a hardware wallet is connected, False otherwise.
        """
        return self.using_hardware_wallet and self.hardware_wallet_type is not None and \
               self.hardware_wallet_manager.is_wallet_connected(self.hardware_wallet_type)

    def get_hardware_wallet_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the connected hardware wallet.

        Returns:
            A dictionary containing hardware wallet information, or None if no hardware wallet is connected.
        """
        if not self.is_hardware_wallet_connected():
            return None

        try:
            device_info = self.hardware_wallet_manager.get_device_info(self.hardware_wallet_type)
            return {
                "type": self.hardware_wallet_type.value,
                "model": device_info.get("model", "Unknown"),
                "firmware_version": device_info.get("firmware_version", "Unknown"),
                "address": self.address,
                "derivation_path": self.hardware_derivation_path
            }
        except Exception as e:
            logger.error(f"Error getting hardware wallet info: {e}")
            return None

    def sign_message(self, message: str) -> str:
        """
        Sign a message with the wallet's private key.

        Args:
            message: The message to sign.

        Returns:
            The signature as a hex string.

        Raises:
            ValueError: If no wallet is loaded.
        """
        if self.using_hardware_wallet:
            # Use hardware wallet to sign message
            if not self.hardware_derivation_path:
                raise ValueError("Hardware wallet derivation path not set")

            signature = self.hardware_wallet_manager.sign_message(
                message=message,
                derivation_path=self.hardware_derivation_path
            )
            return signature
        elif self.private_key:
            # Use software wallet to sign message
            # Load private key
            private_key_obj = load_private_key_from_pem(self.private_key.encode())

            # Sign message
            signature = sign_message(private_key_obj, message.encode())

            return signature.hex()
        else:
            raise ValueError("No wallet loaded")

    def verify_message(self, message: str, signature: str, address: Optional[str] = None) -> bool:
        """
        Verify a message signature.

        Args:
            message: The message that was signed.
            signature: The signature as a hex string.
            address: The address that signed the message. If None, uses the loaded wallet's address.

        Returns:
            True if the signature is valid, False otherwise.

        Raises:
            ValueError: If no wallet is loaded and no address is provided.
        """
        if not address and not self.public_key:
            raise ValueError("No wallet loaded and no address provided")

        # Use loaded wallet's public key if no address is provided
        if not address:
            public_key_pem = self.public_key.encode()
        else:
            # In a real implementation, we would need to look up the public key for the address
            # For now, we'll just assume the address is the loaded wallet's address
            if address != self.address:
                raise ValueError("Cannot verify message for address other than the loaded wallet's address")
            public_key_pem = self.public_key.encode()

        # Convert signature from hex
        signature_bytes = bytes.fromhex(signature)

        # Verify signature
        return verify_signature(public_key_pem, signature_bytes, message.encode())

    # --- Zero-Knowledge Proof Methods ---

    def create_confidential_transaction_with_zkp(
        self,
        recipient: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None
    ) -> Transaction:
        """
        Create a confidential transaction with zero-knowledge proofs.

        Args:
            recipient: The recipient's address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.

        Returns:
            A confidential transaction with zero-knowledge proofs.

        Raises:
            ValueError: If no wallet is loaded or if the parameters are invalid.
        """
        if not self.zkp_wallet:
            raise ValueError("No wallet loaded")

        return self.zkp_wallet.create_confidential_transaction_with_zkp(
            recipient=recipient,
            amount=amount,
            fee=fee,
            memo=memo
        )

    def create_identity_proof(
        self,
        identity_data: Dict[str, Any],
        public_attributes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create a zero-knowledge proof of identity.

        Args:
            identity_data: The user's identity data.
            public_attributes: List of attributes to make public (default: None).

        Returns:
            A proof of identity.

        Raises:
            ValueError: If no wallet is loaded.
        """
        if not self.zkp_wallet:
            raise ValueError("No wallet loaded")

        return self.zkp_wallet.create_identity_proof(
            identity_data=identity_data,
            public_attributes=public_attributes
        )

    def verify_identity_proof(
        self,
        identity_proof: Dict[str, Any],
        required_attributes: List[str]
    ) -> bool:
        """
        Verify a zero-knowledge proof of identity.

        Args:
            identity_proof: The proof of identity.
            required_attributes: List of attributes that must be verified.

        Returns:
            True if the proof is valid and contains the required attributes, False otherwise.

        Raises:
            ValueError: If no wallet is loaded.
        """
        if not self.zkp_wallet:
            raise ValueError("No wallet loaded")

        return self.zkp_wallet.verify_identity_proof(
            identity_proof=identity_proof,
            required_attributes=required_attributes
        )

    def create_private_contract_proof(
        self,
        contract_code: str,
        contract_state: Dict[str, Any],
        contract_inputs: Dict[str, Any],
        private_inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a zero-knowledge proof of private smart contract execution.

        Args:
            contract_code: The smart contract code.
            contract_state: The current state of the contract.
            contract_inputs: The public inputs to the contract.
            private_inputs: The private inputs to the contract.

        Returns:
            A proof of private contract execution.

        Raises:
            ValueError: If no wallet is loaded.
        """
        if not self.zkp_wallet:
            raise ValueError("No wallet loaded")

        return self.zkp_wallet.create_private_contract_proof(
            contract_code=contract_code,
            contract_state=contract_state,
            contract_inputs=contract_inputs,
            private_inputs=private_inputs
        )

    def create_protein_folding_proof(
        self,
        protein_sequence: str,
        folding_result: Dict[str, Any],
        folding_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a zero-knowledge proof of protein folding computation.

        Args:
            protein_sequence: The protein sequence that was folded.
            folding_result: The result of the protein folding computation.
            folding_parameters: The parameters used for the folding computation.

        Returns:
            A proof of protein folding computation.

        Raises:
            ValueError: If no wallet is loaded.
        """
        if not self.zkp_wallet:
            raise ValueError("No wallet loaded")

        return self.zkp_wallet.create_protein_folding_proof(
            protein_sequence=protein_sequence,
            folding_result=folding_result,
            folding_parameters=folding_parameters
        )

    # --- Stealth Address Methods ---

    def create_stealth_keys(self) -> Dict[str, Any]:
        """
        Create a new set of stealth keys.

        Returns:
            A dictionary containing the stealth keys data.

        Raises:
            ValueError: If no wallet is loaded.
        """
        if not self.stealth_wallet:
            raise ValueError("No wallet loaded")

        # Create stealth keys
        stealth_data = self.stealth_wallet.create_stealth_keys()

        # Update wallet data
        self.wallet_data["stealth_data"] = stealth_data

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        return stealth_data

    def get_stealth_address(self) -> str:
        """
        Get the stealth address.

        Returns:
            The stealth address.

        Raises:
            ValueError: If no stealth keys are loaded.
        """
        if not self.stealth_wallet:
            raise ValueError("No wallet loaded")

        return self.stealth_wallet.get_stealth_address()

    async def create_stealth_payment(
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
            ValueError: If no wallet is loaded or if the parameters are invalid.
        """
        if not self.stealth_wallet:
            raise ValueError("No wallet loaded")

        return self.stealth_wallet.create_stealth_payment(
            recipient_stealth_address=recipient_stealth_address,
            amount=amount,
            fee=fee,
            memo=memo
        )

    async def create_and_submit_stealth_payment(
        self,
        recipient_stealth_address: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create and submit a transaction to a stealth address.

        Args:
            recipient_stealth_address: The recipient's stealth address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.

        Returns:
            The response from the network.

        Raises:
            ValueError: If no wallet is loaded or if the parameters are invalid.
            ConnectionError: If there's an error connecting to the network.
        """
        if not self.stealth_wallet or not self.transaction_builder:
            raise ValueError("No wallet loaded")

        # Create stealth payment
        transaction, stealth_metadata = await self.create_stealth_payment(
            recipient_stealth_address=recipient_stealth_address,
            amount=amount,
            fee=fee,
            memo=memo
        )

        # Sign transaction
        signed_transaction = self.transaction_builder.sign_transaction(transaction)

        # Submit transaction
        response = await self.transaction_builder.submit_transaction(signed_transaction)

        return response

    async def scan_for_stealth_payments(self) -> List[Dict[str, Any]]:
        """
        Scan for stealth payments to this wallet.

        Returns:
            A list of detected stealth payments.

        Raises:
            ValueError: If no stealth keys are loaded.
        """
        if not self.stealth_wallet:
            raise ValueError("No wallet loaded")

        # Get transactions
        transactions = await self.get_transactions()

        # Convert transactions to dictionaries
        tx_dicts = [tx.dict() for tx in transactions]

        # Scan for payments
        return self.stealth_wallet.scan_for_payments(tx_dicts)

    # --- Mixing Methods ---

    async def create_mixing_session(
        self,
        denomination: float = 1.0,
        min_participants: int = 3,
        max_participants: int = 20,
        fee_percent: float = 0.005
    ) -> Dict[str, Any]:
        """
        Create a new mixing session.

        Args:
            denomination: The amount each participant will mix (default: 1.0).
            min_participants: Minimum number of participants required (default: 3).
            max_participants: Maximum number of participants allowed (default: 20).
            fee_percent: Fee percentage for the mixing service (default: 0.5%).

        Returns:
            The created mixing session data.

        Raises:
            ValueError: If no wallet is loaded.
        """
        if not self.mixing_wallet:
            raise ValueError("No wallet loaded")

        # Create mixing session
        session = await self.mixing_wallet.create_mixing_session(
            denomination=denomination,
            min_participants=min_participants,
            max_participants=max_participants,
            fee_percent=fee_percent
        )

        # Update wallet data
        if "mixing_data" not in self.wallet_data:
            self.wallet_data["mixing_data"] = {}

        # Store session in wallet data
        self.wallet_data["mixing_data"][session["session_id"]] = {
            "session_id": session["session_id"],
            "denomination": denomination,
            "status": session["status"],
            "created_at": session["created_at"],
            "participants": []
        }

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        return session

    async def join_mixing_session(
        self,
        session_id: str,
        output_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Join an existing mixing session.

        Args:
            session_id: The ID of the session to join.
            output_address: Optional output address (default: generate new).

        Returns:
            The participant data.

        Raises:
            ValueError: If no wallet is loaded or the session is not found.
        """
        if not self.mixing_wallet:
            raise ValueError("No wallet loaded")

        # Join mixing session
        participant = await self.mixing_wallet.join_mixing_session(
            session_id=session_id,
            output_address=output_address
        )

        # Update wallet data
        if "mixing_data" not in self.wallet_data:
            self.wallet_data["mixing_data"] = {}

        # Store participant in wallet data
        if session_id not in self.wallet_data["mixing_data"]:
            self.wallet_data["mixing_data"][session_id] = {
                "session_id": session_id,
                "status": "joined",
                "participants": []
            }

        self.wallet_data["mixing_data"][session_id]["participants"].append(participant["participant_id"])

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        return participant

    async def get_mixing_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get the status of a mixing session.

        Args:
            session_id: The session ID.

        Returns:
            The session status data.

        Raises:
            ValueError: If no wallet is loaded or the session is not found.
        """
        if not self.mixing_wallet:
            raise ValueError("No wallet loaded")

        # Get session status
        return await self.mixing_wallet.get_session_status(session_id)

    async def get_active_mixing_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all active mixing sessions.

        Returns:
            A list of active session data.

        Raises:
            ValueError: If no wallet is loaded.
        """
        if not self.mixing_wallet:
            raise ValueError("No wallet loaded")

        # Get active sessions
        return await self.mixing_wallet.get_active_sessions()

    async def get_my_mixing_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all mixing sessions the wallet is participating in.

        Returns:
            A list of session data.

        Raises:
            ValueError: If no wallet is loaded.
        """
        if not self.mixing_wallet:
            raise ValueError("No wallet loaded")

        # Get my sessions
        return await self.mixing_wallet.get_my_sessions()

    async def get_blind_signature(
        self,
        session_id: str,
        participant_id: str
    ) -> Dict[str, Any]:
        """
        Get a blind signature from the mixing coordinator.

        Args:
            session_id: The session ID.
            participant_id: The participant ID.

        Returns:
            The blind signature data.

        Raises:
            ValueError: If no wallet is loaded or the session or participant is not found.
        """
        if not self.mixing_wallet:
            raise ValueError("No wallet loaded")

        # Get blind signature
        return await self.mixing_wallet.get_blind_signature(
            session_id=session_id,
            participant_id=participant_id
        )

    async def sign_coinjoin_transaction(
        self,
        session_id: str,
        participant_id: str
    ) -> Dict[str, Any]:
        """
        Sign a CoinJoin transaction.

        Args:
            session_id: The session ID.
            participant_id: The participant ID.

        Returns:
            The signature data.

        Raises:
            ValueError: If no wallet is loaded or the session or participant is not found.
        """
        if not self.mixing_wallet:
            raise ValueError("No wallet loaded")

        # Sign transaction
        return await self.mixing_wallet.sign_coinjoin_transaction(
            session_id=session_id,
            participant_id=participant_id
        )

    async def get_final_coinjoin_transaction(self, session_id: str) -> Dict[str, Any]:
        """
        Get the final CoinJoin transaction.

        Args:
            session_id: The session ID.

        Returns:
            The final transaction data.

        Raises:
            ValueError: If no wallet is loaded or the session is not found or not completed.
        """
        if not self.mixing_wallet:
            raise ValueError("No wallet loaded")

        # Get final transaction
        return await self.mixing_wallet.get_final_transaction(session_id)

    async def submit_coinjoin_transaction(self, session_id: str) -> Dict[str, Any]:
        """
        Submit the final CoinJoin transaction to the network.

        Args:
            session_id: The session ID.

        Returns:
            The submission response.

        Raises:
            ValueError: If no wallet is loaded or the session is not found or not completed.
        """
        if not self.mixing_wallet:
            raise ValueError("No wallet loaded")

        # Submit transaction
        response = await self.mixing_wallet.submit_final_transaction(session_id)

        # Update wallet data
        if "mixing_data" in self.wallet_data and session_id in self.wallet_data["mixing_data"]:
            self.wallet_data["mixing_data"][session_id]["status"] = "completed"
            self.wallet_data["mixing_data"][session_id]["transaction_id"] = response["transaction_id"]

            # Save wallet if auto_save is enabled
            if self.auto_save and self.wallet_password:
                self.save_wallet(self.wallet_password)

        return response

    # --- Multi-Signature Wallet Methods ---

    def create_multisig_wallet(
        self,
        required_signatures: int,
        total_signers: int,
        public_keys: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new multi-signature wallet.

        Args:
            required_signatures: Number of signatures required to authorize transactions.
            total_signers: Total number of signers.
            public_keys: List of public keys for all signers (optional).
            description: Optional description for the wallet.

        Returns:
            The created multi-signature wallet data.

        Raises:
            ValueError: If no wallet is loaded or the parameters are invalid.
        """
        if not self.private_key:
            raise ValueError("No wallet loaded")

        # Create multisig wallet
        multisig_wallet = create_multisig_wallet(
            required_signatures=required_signatures,
            total_signers=total_signers,
            private_key=self.private_key,
            public_keys=public_keys,
            description=description
        )

        # Store in wallet
        self.multisig_wallets[multisig_wallet.wallet_id] = multisig_wallet

        # Update wallet data
        if "multisig_wallets" not in self.wallet_data:
            self.wallet_data["multisig_wallets"] = {}

        self.wallet_data["multisig_wallets"][multisig_wallet.wallet_id] = multisig_wallet.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Created multisig wallet: {multisig_wallet.wallet_id}")
        return multisig_wallet.to_dict()

    def join_multisig_wallet(
        self,
        wallet_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Join an existing multi-signature wallet.

        Args:
            wallet_data: The wallet data to join.

        Returns:
            The joined multi-signature wallet data.

        Raises:
            ValueError: If no wallet is loaded or the wallet data is invalid.
        """
        if not self.private_key:
            raise ValueError("No wallet loaded")

        # Join multisig wallet
        multisig_wallet = join_multisig_wallet(
            wallet_data=wallet_data,
            private_key=self.private_key
        )

        # Store in wallet
        self.multisig_wallets[multisig_wallet.wallet_id] = multisig_wallet

        # Update wallet data
        if "multisig_wallets" not in self.wallet_data:
            self.wallet_data["multisig_wallets"] = {}

        self.wallet_data["multisig_wallets"][multisig_wallet.wallet_id] = multisig_wallet.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Joined multisig wallet: {multisig_wallet.wallet_id}")
        return multisig_wallet.to_dict()

    def get_multisig_wallet(self, wallet_id: str) -> Dict[str, Any]:
        """
        Get a multi-signature wallet by ID.

        Args:
            wallet_id: The ID of the multi-signature wallet.

        Returns:
            The multi-signature wallet data.

        Raises:
            ValueError: If the wallet is not found.
        """
        if wallet_id not in self.multisig_wallets:
            raise ValueError(f"Multisig wallet {wallet_id} not found")

        return self.multisig_wallets[wallet_id].to_dict()

    def list_multisig_wallets(self) -> List[Dict[str, Any]]:
        """
        List all multi-signature wallets.

        Returns:
            A list of multi-signature wallet data.
        """
        return [wallet.to_dict() for wallet in self.multisig_wallets.values()]

    def create_multisig_transaction(
        self,
        wallet_id: str,
        recipient: str,
        amount: float,
        fee: Optional[float] = None,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new multi-signature transaction.

        Args:
            wallet_id: The ID of the multi-signature wallet.
            recipient: The recipient's address.
            amount: The amount to send.
            fee: The transaction fee (default: calculated automatically).
            memo: Optional memo to include with the transaction.

        Returns:
            The created transaction data.

        Raises:
            ValueError: If the wallet is not found or the parameters are invalid.
        """
        if wallet_id not in self.multisig_wallets:
            raise ValueError(f"Multisig wallet {wallet_id} not found")

        # Create transaction
        transaction_data = self.multisig_wallets[wallet_id].create_transaction(
            recipient=recipient,
            amount=amount,
            fee=fee,
            memo=memo
        )

        # Update wallet data
        self.wallet_data["multisig_wallets"][wallet_id] = self.multisig_wallets[wallet_id].to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Created multisig transaction: {transaction_data['transaction_id']}")
        return transaction_data

    def sign_multisig_transaction(
        self,
        wallet_id: str,
        transaction_id: str
    ) -> Dict[str, Any]:
        """
        Sign a multi-signature transaction.

        Args:
            wallet_id: The ID of the multi-signature wallet.
            transaction_id: The ID of the transaction to sign.

        Returns:
            The updated transaction data.

        Raises:
            ValueError: If the wallet or transaction is not found.
        """
        if wallet_id not in self.multisig_wallets:
            raise ValueError(f"Multisig wallet {wallet_id} not found")

        # Sign transaction
        transaction_data = self.multisig_wallets[wallet_id].sign_transaction(transaction_id)

        # Update wallet data
        self.wallet_data["multisig_wallets"][wallet_id] = self.multisig_wallets[wallet_id].to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Signed multisig transaction: {transaction_id}")
        return transaction_data

    def verify_multisig_transaction(
        self,
        wallet_id: str,
        transaction_id: str
    ) -> bool:
        """
        Verify if a multi-signature transaction has enough valid signatures.

        Args:
            wallet_id: The ID of the multi-signature wallet.
            transaction_id: The ID of the transaction to verify.

        Returns:
            True if the transaction has enough valid signatures, False otherwise.

        Raises:
            ValueError: If the wallet or transaction is not found.
        """
        if wallet_id not in self.multisig_wallets:
            raise ValueError(f"Multisig wallet {wallet_id} not found")

        return self.multisig_wallets[wallet_id].verify_transaction(transaction_id)

    async def finalize_and_submit_multisig_transaction(
        self,
        wallet_id: str,
        transaction_id: str
    ) -> Dict[str, Any]:
        """
        Finalize and submit a multi-signature transaction.

        Args:
            wallet_id: The ID of the multi-signature wallet.
            transaction_id: The ID of the transaction to finalize and submit.

        Returns:
            The submission response.

        Raises:
            ValueError: If the wallet or transaction is not found or doesn't have enough signatures.
        """
        if wallet_id not in self.multisig_wallets:
            raise ValueError(f"Multisig wallet {wallet_id} not found")

        if not self.transaction_builder:
            raise ValueError("No wallet loaded")

        # Finalize transaction
        transaction = self.multisig_wallets[wallet_id].finalize_transaction(transaction_id)

        # Submit transaction
        response = await self.transaction_builder.submit_transaction(transaction)

        # Update wallet data
        self.wallet_data["multisig_wallets"][wallet_id] = self.multisig_wallets[wallet_id].to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Submitted multisig transaction: {transaction_id}")
        return response

    # --- Address Book Methods ---

    def add_contact(
        self,
        name: str,
        address: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Add a contact to the address book.

        Args:
            name: The name of the contact.
            address: The blockchain address of the contact.
            email: Optional email address.
            phone: Optional phone number.
            description: Optional description.
            tags: Optional list of tags for categorization.

        Returns:
            The added contact data.

        Raises:
            ValueError: If the address is invalid or a contact with the same address already exists.
        """
        # Create contact
        contact = create_contact(
            name=name,
            address=address,
            email=email,
            phone=phone,
            description=description,
            tags=tags
        )

        # Add to address book
        self.address_book.add_contact(contact)

        # Update wallet data
        if "address_book" not in self.wallet_data:
            self.wallet_data["address_book"] = {}

        self.wallet_data["address_book"] = self.address_book.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Added contact: {name} ({address})")
        return contact.to_dict()

    def update_contact(
        self,
        contact_id: str,
        name: Optional[str] = None,
        address: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Update a contact in the address book.

        Args:
            contact_id: The ID of the contact to update.
            name: Optional new name.
            address: Optional new address.
            email: Optional new email.
            phone: Optional new phone.
            description: Optional new description.
            tags: Optional new tags.

        Returns:
            The updated contact data.

        Raises:
            ValueError: If the contact is not found or the address is invalid.
        """
        # Update contact
        contact = self.address_book.update_contact(
            contact_id=contact_id,
            name=name,
            address=address,
            email=email,
            phone=phone,
            description=description,
            tags=tags
        )

        # Update wallet data
        self.wallet_data["address_book"] = self.address_book.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Updated contact: {contact.name} ({contact.address})")
        return contact.to_dict()

    def remove_contact(self, contact_id: str) -> None:
        """
        Remove a contact from the address book.

        Args:
            contact_id: The ID of the contact to remove.

        Raises:
            ValueError: If the contact is not found.
        """
        # Get contact name for logging
        contact = self.address_book.get_contact(contact_id)
        contact_name = contact.name

        # Remove contact
        self.address_book.remove_contact(contact_id)

        # Update wallet data
        self.wallet_data["address_book"] = self.address_book.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Removed contact: {contact_name}")

    def get_contact(self, contact_id: str) -> Dict[str, Any]:
        """
        Get a contact by ID.

        Args:
            contact_id: The ID of the contact to get.

        Returns:
            The contact data.

        Raises:
            ValueError: If the contact is not found.
        """
        contact = self.address_book.get_contact(contact_id)
        return contact.to_dict()

    def get_contact_by_address(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get a contact by address.

        Args:
            address: The address to look up.

        Returns:
            The contact data, or None if not found.
        """
        contact = self.address_book.get_contact_by_address(address)
        return contact.to_dict() if contact else None

    def get_contact_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a contact by name.

        Args:
            name: The name to look up.

        Returns:
            The contact data, or None if not found.
        """
        contact = self.address_book.get_contact_by_name(name)
        return contact.to_dict() if contact else None

    def search_contacts(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for contacts.

        Args:
            query: Optional search query for name, address, email, or description.
            tags: Optional list of tags to filter by.

        Returns:
            A list of matching contact data.
        """
        contacts = self.address_book.search_contacts(query=query, tags=tags)
        return [contact.to_dict() for contact in contacts]

    def list_contacts(self) -> List[Dict[str, Any]]:
        """
        List all contacts in the address book.

        Returns:
            A list of all contact data.
        """
        contacts = self.address_book.list_contacts()
        return [contact.to_dict() for contact in contacts]

    def get_contacts_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """
        Get contacts by tag.

        Args:
            tag: The tag to filter by.

        Returns:
            A list of contacts with the given tag.
        """
        contacts = self.address_book.get_contacts_by_tag(tag)
        return [contact.to_dict() for contact in contacts]

    def add_tag_to_contact(self, contact_id: str, tag: str) -> Dict[str, Any]:
        """
        Add a tag to a contact.

        Args:
            contact_id: The ID of the contact.
            tag: The tag to add.

        Returns:
            The updated contact data.

        Raises:
            ValueError: If the contact is not found.
        """
        # Get contact
        contact = self.address_book.get_contact(contact_id)

        # Add tag if not already present
        if tag not in contact.tags:
            contact.tags.append(tag)

            # Update contact
            contact.updated_at = int(time.time())

            # Update wallet data
            self.wallet_data["address_book"] = self.address_book.to_dict()

            # Save wallet if auto_save is enabled
            if self.auto_save and self.wallet_password:
                self.save_wallet(self.wallet_password)

            logger.info(f"Added tag '{tag}' to contact: {contact.name}")

        return contact.to_dict()

    def remove_tag_from_contact(self, contact_id: str, tag: str) -> Dict[str, Any]:
        """
        Remove a tag from a contact.

        Args:
            contact_id: The ID of the contact.
            tag: The tag to remove.

        Returns:
            The updated contact data.

        Raises:
            ValueError: If the contact is not found.
        """
        # Get contact
        contact = self.address_book.get_contact(contact_id)

        # Remove tag if present
        if tag in contact.tags:
            contact.tags.remove(tag)

            # Update contact
            contact.updated_at = int(time.time())

            # Update wallet data
            self.wallet_data["address_book"] = self.address_book.to_dict()

            # Save wallet if auto_save is enabled
            if self.auto_save and self.wallet_password:
                self.save_wallet(self.wallet_password)

            logger.info(f"Removed tag '{tag}' from contact: {contact.name}")

        return contact.to_dict()

    def get_all_tags(self) -> List[str]:
        """
        Get all unique tags used in the address book.

        Returns:
            A list of all unique tags.
        """
        tags = set()
        for contact in self.address_book.list_contacts():
            tags.update(contact.tags)
        return sorted(list(tags))

    # --- Transaction Labeling Methods ---

    def add_transaction_label(
        self,
        transaction_id: str,
        label: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Add a label to a transaction.

        Args:
            transaction_id: The ID of the transaction.
            label: Optional label for the transaction.
            category: Optional category for the transaction.
            notes: Optional notes for the transaction.
            tags: Optional list of tags for the transaction.

        Returns:
            The added transaction label data.
        """
        # Create transaction label
        transaction_label = create_transaction_label(
            transaction_id=transaction_id,
            label=label,
            category=category,
            notes=notes,
            tags=tags
        )

        # Add to label manager
        self.label_manager.add_label(
            transaction_id=transaction_id,
            label=label,
            category=category,
            notes=notes,
            tags=tags
        )

        # Update wallet data
        if "transaction_labels" not in self.wallet_data:
            self.wallet_data["transaction_labels"] = {}

        self.wallet_data["transaction_labels"] = self.label_manager.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Added label to transaction {transaction_id}")
        return transaction_label.to_dict()

    def update_transaction_label(
        self,
        transaction_id: str,
        label: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Update a transaction label.

        Args:
            transaction_id: The ID of the transaction.
            label: Optional new label.
            category: Optional new category.
            notes: Optional new notes.
            tags: Optional new tags.

        Returns:
            The updated transaction label data.

        Raises:
            ValueError: If the transaction label is not found.
        """
        # Update transaction label
        transaction_label = self.label_manager.update_label(
            transaction_id=transaction_id,
            label=label,
            category=category,
            notes=notes,
            tags=tags
        )

        # Update wallet data
        self.wallet_data["transaction_labels"] = self.label_manager.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Updated label for transaction {transaction_id}")
        return transaction_label.to_dict()

    def remove_transaction_label(self, transaction_id: str) -> None:
        """
        Remove a transaction label.

        Args:
            transaction_id: The ID of the transaction.

        Raises:
            ValueError: If the transaction label is not found.
        """
        # Remove transaction label
        self.label_manager.remove_label(transaction_id)

        # Update wallet data
        self.wallet_data["transaction_labels"] = self.label_manager.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Removed label for transaction {transaction_id}")

    def get_transaction_label(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a transaction label.

        Args:
            transaction_id: The ID of the transaction.

        Returns:
            The transaction label data, or None if not found.
        """
        transaction_label = self.label_manager.get_label(transaction_id)
        return transaction_label.to_dict() if transaction_label else None

    def search_transaction_labels(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for transaction labels.

        Args:
            query: Optional search query for label, notes, or transaction ID.
            category: Optional category to filter by.
            tags: Optional list of tags to filter by.

        Returns:
            A list of matching transaction label data.
        """
        transaction_labels = self.label_manager.search_labels(
            query=query,
            category=category,
            tags=tags
        )
        return [label.to_dict() for label in transaction_labels]

    def list_transaction_labels(self) -> List[Dict[str, Any]]:
        """
        List all transaction labels.

        Returns:
            A list of all transaction label data.
        """
        transaction_labels = self.label_manager.list_labels()
        return [label.to_dict() for label in transaction_labels]

    def get_transaction_labels_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get transaction labels by category.

        Args:
            category: The category to filter by.

        Returns:
            A list of transaction labels with the given category.
        """
        transaction_labels = self.label_manager.get_labels_by_category(category)
        return [label.to_dict() for label in transaction_labels]

    def get_transaction_labels_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """
        Get transaction labels by tag.

        Args:
            tag: The tag to filter by.

        Returns:
            A list of transaction labels with the given tag.
        """
        transaction_labels = self.label_manager.get_labels_by_tag(tag)
        return [label.to_dict() for label in transaction_labels]

    def get_all_transaction_categories(self) -> List[str]:
        """
        Get all transaction categories.

        Returns:
            A list of all transaction categories.
        """
        return self.label_manager.get_all_categories()

    def get_all_transaction_tags(self) -> List[str]:
        """
        Get all transaction tags.

        Returns:
            A list of all transaction tags.
        """
        return self.label_manager.get_all_tags()

    # --- Recurring Transaction Methods ---

    def create_recurring_transaction(
        self,
        recipient: str,
        amount: float,
        interval: Union[RecurrenceInterval, str],
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        custom_days: Optional[int] = None,
        memo: Optional[str] = None,
        fee: Optional[float] = None,
        enabled: bool = True,
        max_executions: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new recurring transaction.

        Args:
            recipient: The recipient's address.
            amount: The amount to send.
            interval: The recurrence interval (daily, weekly, biweekly, monthly, quarterly, yearly, custom).
            start_date: Optional start date as Unix timestamp (default: current time).
            end_date: Optional end date as Unix timestamp.
            custom_days: Optional custom interval in days (only used if interval is CUSTOM).
            memo: Optional memo to include with the transaction.
            fee: Optional transaction fee.
            enabled: Whether the recurring transaction is enabled (default: True).
            max_executions: Optional maximum number of executions.

        Returns:
            The created recurring transaction data.

        Raises:
            ValueError: If the parameters are invalid.
        """
        # Generate transaction ID
        import uuid
        transaction_id = f"recurring_{uuid.uuid4().hex[:8]}"

        # Create recurring transaction
        transaction = self.recurring_manager.add_transaction(
            transaction_id=transaction_id,
            recipient=recipient,
            amount=amount,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            custom_days=custom_days,
            memo=memo,
            fee=fee,
            enabled=enabled,
            max_executions=max_executions
        )

        # Update wallet data
        if "recurring_transactions" not in self.wallet_data:
            self.wallet_data["recurring_transactions"] = {}

        self.wallet_data["recurring_transactions"] = self.recurring_manager.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Created recurring transaction {transaction_id}")
        return transaction.to_dict()

    def update_recurring_transaction(
        self,
        transaction_id: str,
        recipient: Optional[str] = None,
        amount: Optional[float] = None,
        interval: Optional[Union[RecurrenceInterval, str]] = None,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        custom_days: Optional[int] = None,
        memo: Optional[str] = None,
        fee: Optional[float] = None,
        enabled: Optional[bool] = None,
        max_executions: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update a recurring transaction.

        Args:
            transaction_id: The ID of the transaction to update.
            recipient: Optional new recipient.
            amount: Optional new amount.
            interval: Optional new interval.
            start_date: Optional new start date.
            end_date: Optional new end date.
            custom_days: Optional new custom interval in days.
            memo: Optional new memo.
            fee: Optional new fee.
            enabled: Optional new enabled status.
            max_executions: Optional new maximum number of executions.

        Returns:
            The updated recurring transaction data.

        Raises:
            ValueError: If the transaction is not found or the parameters are invalid.
        """
        # Update recurring transaction
        transaction = self.recurring_manager.update_transaction(
            transaction_id=transaction_id,
            recipient=recipient,
            amount=amount,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            custom_days=custom_days,
            memo=memo,
            fee=fee,
            enabled=enabled,
            max_executions=max_executions
        )

        # Update wallet data
        self.wallet_data["recurring_transactions"] = self.recurring_manager.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Updated recurring transaction {transaction_id}")
        return transaction.to_dict()

    def remove_recurring_transaction(self, transaction_id: str) -> None:
        """
        Remove a recurring transaction.

        Args:
            transaction_id: The ID of the transaction to remove.

        Raises:
            ValueError: If the transaction is not found.
        """
        # Remove recurring transaction
        self.recurring_manager.remove_transaction(transaction_id)

        # Update wallet data
        self.wallet_data["recurring_transactions"] = self.recurring_manager.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Removed recurring transaction {transaction_id}")

    def get_recurring_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a recurring transaction.

        Args:
            transaction_id: The ID of the transaction to get.

        Returns:
            The recurring transaction data, or None if not found.
        """
        transaction = self.recurring_manager.get_transaction(transaction_id)
        return transaction.to_dict() if transaction else None

    def list_recurring_transactions(self) -> List[Dict[str, Any]]:
        """
        List all recurring transactions.

        Returns:
            A list of all recurring transaction data.
        """
        transactions = self.recurring_manager.list_transactions()
        return [transaction.to_dict() for transaction in transactions]

    def get_due_recurring_transactions(self) -> List[Dict[str, Any]]:
        """
        Get recurring transactions that are due for execution.

        Returns:
            A list of recurring transaction data that are due.
        """
        transactions = self.recurring_manager.get_due_transactions()
        return [transaction.to_dict() for transaction in transactions]

    def enable_recurring_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """
        Enable a recurring transaction.

        Args:
            transaction_id: The ID of the transaction to enable.

        Returns:
            The updated recurring transaction data.

        Raises:
            ValueError: If the transaction is not found.
        """
        # Enable recurring transaction
        transaction = self.recurring_manager.enable_transaction(transaction_id)

        # Update wallet data
        self.wallet_data["recurring_transactions"] = self.recurring_manager.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Enabled recurring transaction {transaction_id}")
        return transaction.to_dict()

    def disable_recurring_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """
        Disable a recurring transaction.

        Args:
            transaction_id: The ID of the transaction to disable.

        Returns:
            The updated recurring transaction data.

        Raises:
            ValueError: If the transaction is not found.
        """
        # Disable recurring transaction
        transaction = self.recurring_manager.disable_transaction(transaction_id)

        # Update wallet data
        self.wallet_data["recurring_transactions"] = self.recurring_manager.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Disabled recurring transaction {transaction_id}")
        return transaction.to_dict()

    async def execute_recurring_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """
        Execute a recurring transaction.

        Args:
            transaction_id: The ID of the transaction to execute.

        Returns:
            The execution response.

        Raises:
            ValueError: If the transaction is not found or cannot be executed.
        """
        # Get recurring transaction
        transaction = self.recurring_manager.get_transaction(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction with ID {transaction_id} not found")

        # Check if transaction is enabled
        if not transaction.enabled:
            raise ValueError(f"Transaction {transaction_id} is disabled")

        # Execute transaction
        response = await self.send_transaction(
            recipient=transaction.recipient,
            amount=transaction.amount,
            fee=transaction.fee,
            memo=transaction.memo
        )

        # Mark transaction as executed
        self.recurring_manager.mark_executed(transaction_id)

        # Update wallet data
        self.wallet_data["recurring_transactions"] = self.recurring_manager.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Executed recurring transaction {transaction_id}")
        return response

    async def execute_due_transactions(self) -> List[Dict[str, Any]]:
        """
        Execute all recurring transactions that are due.

        Returns:
            A list of execution responses.
        """
        # Get due transactions
        due_transactions = self.recurring_manager.get_due_transactions()

        # Execute each transaction
        responses = []
        for transaction in due_transactions:
            try:
                response = await self.execute_recurring_transaction(transaction.transaction_id)
                responses.append({
                    "transaction_id": transaction.transaction_id,
                    "success": True,
                    "response": response
                })
            except Exception as e:
                logger.error(f"Error executing recurring transaction {transaction.transaction_id}: {e}")
                responses.append({
                    "transaction_id": transaction.transaction_id,
                    "success": False,
                    "error": str(e)
                })

        return responses

    def add_tag_to_transaction_label(self, transaction_id: str, tag: str) -> Dict[str, Any]:
        """
        Add a tag to a transaction label.

        Args:
            transaction_id: The ID of the transaction.
            tag: The tag to add.

        Returns:
            The updated transaction label data.

        Raises:
            ValueError: If the transaction label is not found.
        """
        # Add tag to transaction label
        transaction_label = self.label_manager.add_tag_to_label(transaction_id, tag)

        # Update wallet data
        self.wallet_data["transaction_labels"] = self.label_manager.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Added tag '{tag}' to transaction {transaction_id}")
        return transaction_label.to_dict()

    def remove_tag_from_transaction_label(self, transaction_id: str, tag: str) -> Dict[str, Any]:
        """
        Remove a tag from a transaction label.

        Args:
            transaction_id: The ID of the transaction.
            tag: The tag to remove.

        Returns:
            The updated transaction label data.

        Raises:
            ValueError: If the transaction label is not found.
        """
        # Remove tag from transaction label
        transaction_label = self.label_manager.remove_tag_from_label(transaction_id, tag)

        # Update wallet data
        self.wallet_data["transaction_labels"] = self.label_manager.to_dict()

        # Save wallet if auto_save is enabled
        if self.auto_save and self.wallet_password:
            self.save_wallet(self.wallet_password)

        logger.info(f"Removed tag '{tag}' from transaction {transaction_id}")
        return transaction_label.to_dict()

    # QR Code Methods

    def generate_payment_qr_code(
        self,
        amount: Optional[float] = None,
        memo: Optional[str] = None,
        label: Optional[str] = None,
        expires: Optional[int] = None,
        request_id: Optional[str] = None
    ) -> str:
        """
        Generate a payment request QR code for this wallet's address.

        Args:
            amount: Optional payment amount
            memo: Optional payment memo
            label: Optional payment label
            expires: Optional expiration timestamp
            request_id: Optional request ID

        Returns:
            QR code data string

        Raises:
            ValueError: If no wallet is loaded
        """
        if not self.address:
            raise ValueError("No wallet loaded")

        payment_request = PaymentRequest(
            address=self.address,
            amount=amount,
            memo=memo,
            label=label,
            expires=expires,
            request_id=request_id
        )

        return QRCodeGenerator.generate_payment_request_data(payment_request)

    def generate_contact_qr_code(
        self,
        contact_name: str
    ) -> str:
        """
        Generate a contact card QR code for a contact in the address book.

        Args:
            contact_name: Name of the contact

        Returns:
            QR code data string

        Raises:
            ValueError: If the contact is not found
        """
        contact = self.address_book.get_contact_by_name(contact_name)
        if not contact:
            raise ValueError(f"Contact not found: {contact_name}")

        return QRCodeGenerator.generate_contact_card_data(
            name=contact.name,
            address=contact.address,
            email=contact.email,
            phone=contact.phone,
            notes=contact.description
        )

    def init_qr_scanner(self) -> bool:
        """
        Initialize the QR code scanner.

        Returns:
            True if the scanner was initialized successfully, False otherwise
        """
        try:
            self.qr_scanner = QRCodeScanner()
            return self.qr_scanner.scanner_available
        except Exception as e:
            logger.error(f"Error initializing QR code scanner: {e}")
            return False

    def scan_qr_code_from_camera(self, camera_index: int = 0, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        Scan a QR code from the camera.

        Args:
            camera_index: Camera index (default: 0)
            timeout: Timeout in seconds (default: 30)

        Returns:
            Parsed QR code data, or None if no QR code was scanned

        Raises:
            QRCodeError: If scanning fails or is not available
        """
        if not self.qr_scanner:
            if not self.init_qr_scanner():
                raise QRCodeError("QR code scanner not available")

        # Scan QR code
        qr_data = self.qr_scanner.scan_from_camera(camera_index, timeout)
        if not qr_data:
            return None

        # Parse QR code data
        return self._process_scanned_qr_code(qr_data)

    def scan_qr_code_from_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Scan a QR code from an image.

        Args:
            image_path: Path to the image file

        Returns:
            Parsed QR code data, or None if no QR code was found

        Raises:
            QRCodeError: If scanning fails or is not available
        """
        if not self.qr_scanner:
            if not self.init_qr_scanner():
                raise QRCodeError("QR code scanner not available")

        # Scan QR code
        qr_data = self.qr_scanner.scan_from_image(image_path)
        if not qr_data:
            return None

        # Parse QR code data
        return self._process_scanned_qr_code(qr_data)

    def _process_scanned_qr_code(self, qr_data: str) -> Dict[str, Any]:
        """
        Process scanned QR code data.

        Args:
            qr_data: QR code data string

        Returns:
            Parsed QR code data

        Raises:
            QRCodeError: If the QR code data is invalid or unsupported
        """
        try:
            # Parse QR code data
            qr_type, data = QRCodeParser.parse_qr_data(qr_data)

            # Return parsed data with type
            return {
                "type": qr_type.value,
                "data": data
            }
        except Exception as e:
            logger.error(f"Error processing QR code data: {e}")
            raise QRCodeError(f"Error processing QR code data: {e}")

    async def process_payment_request_qr_code(self, qr_data: str) -> Dict[str, Any]:
        """
        Process a payment request QR code and prepare a transaction.

        Args:
            qr_data: QR code data string

        Returns:
            Dictionary containing the payment request and prepared transaction

        Raises:
            QRCodeError: If the QR code data is invalid or unsupported
            ValueError: If no wallet is loaded
        """
        if not self.transaction_builder:
            raise ValueError("No wallet loaded")

        try:
            # Parse QR code data
            payment_request = parse_payment_qr_code(qr_data)
            if not payment_request:
                raise QRCodeError("Invalid payment request QR code")

            # Prepare transaction
            transaction = await self.transaction_builder.create_transaction(
                recipient=payment_request.address,
                amount=payment_request.amount if payment_request.amount is not None else 0,
                memo=payment_request.memo
            )

            return {
                "payment_request": {
                    "address": payment_request.address,
                    "amount": payment_request.amount,
                    "memo": payment_request.memo,
                    "label": payment_request.label,
                    "expires": payment_request.expires,
                    "request_id": payment_request.request_id
                },
                "transaction": transaction.to_dict() if hasattr(transaction, 'to_dict') else transaction
            }
        except Exception as e:
            logger.error(f"Error processing payment request QR code: {e}")
            raise QRCodeError(f"Error processing payment request QR code: {e}")
