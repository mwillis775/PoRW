"""
Transaction handling for smart contracts on the PoRW blockchain.

This module provides functionality for creating, signing, and validating
contract transactions.
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional, Union

from ..core.crypto_utils import sign_message, verify_signature, is_valid_address
from .models import ContractTransaction, SmartContract

# Configure logger
logger = logging.getLogger(__name__)


def create_contract_transaction(
    sender: str,
    private_key: str,
    contract_id: Optional[str] = None,
    function: Optional[str] = None,
    arguments: Optional[List[Any]] = None,
    value: float = 0.0,
    gas_limit: int = 1000000,
    gas_price: float = 0.0000001
) -> ContractTransaction:
    """
    Create a contract transaction.
    
    Args:
        sender: Address of the sender.
        private_key: Private key of the sender.
        contract_id: ID of the target contract (None for deployment).
        function: Name of the function to call (None for deployment or transfer).
        arguments: Arguments to pass to the function.
        value: Amount of PORW tokens to transfer to the contract.
        gas_limit: Maximum amount of gas that can be used.
        gas_price: Price per unit of gas in PORW tokens.
        
    Returns:
        The created transaction.
        
    Raises:
        ValueError: If the parameters are invalid.
    """
    # Validate sender address
    if not is_valid_address(sender):
        raise ValueError(f"Invalid sender address: {sender}")
    
    # Validate value
    if value < 0:
        raise ValueError(f"Invalid value: {value}")
    
    # Validate gas parameters
    if gas_limit <= 0:
        raise ValueError(f"Invalid gas limit: {gas_limit}")
    
    if gas_price <= 0:
        raise ValueError(f"Invalid gas price: {gas_price}")
    
    # Create transaction
    transaction = ContractTransaction(
        sender=sender,
        contract_id=contract_id,
        function=function,
        arguments=arguments or [],
        value=value,
        gas_limit=gas_limit,
        gas_price=gas_price
    )
    
    # Sign the transaction
    signing_data = transaction.get_signing_data()
    transaction.signature = sign_message(signing_data, private_key)
    
    return transaction


def create_contract_deployment_transaction(
    sender: str,
    private_key: str,
    contract_data: Dict[str, Any],
    value: float = 0.0,
    gas_limit: int = 2000000,
    gas_price: float = 0.0000001
) -> ContractTransaction:
    """
    Create a transaction to deploy a new contract.
    
    Args:
        sender: Address of the sender.
        private_key: Private key of the sender.
        contract_data: Data for the new contract.
        value: Amount of PORW tokens to transfer to the contract.
        gas_limit: Maximum amount of gas that can be used.
        gas_price: Price per unit of gas in PORW tokens.
        
    Returns:
        The created transaction.
        
    Raises:
        ValueError: If the parameters are invalid.
    """
    # Validate contract data
    if not isinstance(contract_data, dict):
        raise ValueError("Contract data must be a dictionary")
    
    required_fields = ["name", "language", "code", "abi"]
    for field in required_fields:
        if field not in contract_data:
            raise ValueError(f"Contract data missing required field: {field}")
    
    # Create transaction
    return create_contract_transaction(
        sender=sender,
        private_key=private_key,
        contract_id=None,  # None for deployment
        function=None,     # None for deployment
        arguments=[contract_data],
        value=value,
        gas_limit=gas_limit,
        gas_price=gas_price
    )


def create_contract_call_transaction(
    sender: str,
    private_key: str,
    contract_id: str,
    function: str,
    arguments: Optional[List[Any]] = None,
    value: float = 0.0,
    gas_limit: int = 1000000,
    gas_price: float = 0.0000001
) -> ContractTransaction:
    """
    Create a transaction to call a contract function.
    
    Args:
        sender: Address of the sender.
        private_key: Private key of the sender.
        contract_id: ID of the target contract.
        function: Name of the function to call.
        arguments: Arguments to pass to the function.
        value: Amount of PORW tokens to transfer to the contract.
        gas_limit: Maximum amount of gas that can be used.
        gas_price: Price per unit of gas in PORW tokens.
        
    Returns:
        The created transaction.
        
    Raises:
        ValueError: If the parameters are invalid.
    """
    # Validate contract ID
    if not contract_id:
        raise ValueError("Contract ID is required")
    
    # Validate function name
    if not function:
        raise ValueError("Function name is required")
    
    # Create transaction
    return create_contract_transaction(
        sender=sender,
        private_key=private_key,
        contract_id=contract_id,
        function=function,
        arguments=arguments or [],
        value=value,
        gas_limit=gas_limit,
        gas_price=gas_price
    )


def create_contract_transfer_transaction(
    sender: str,
    private_key: str,
    contract_id: str,
    value: float,
    gas_limit: int = 100000,
    gas_price: float = 0.0000001
) -> ContractTransaction:
    """
    Create a transaction to transfer tokens to a contract.
    
    Args:
        sender: Address of the sender.
        private_key: Private key of the sender.
        contract_id: ID of the target contract.
        value: Amount of PORW tokens to transfer to the contract.
        gas_limit: Maximum amount of gas that can be used.
        gas_price: Price per unit of gas in PORW tokens.
        
    Returns:
        The created transaction.
        
    Raises:
        ValueError: If the parameters are invalid.
    """
    # Validate contract ID
    if not contract_id:
        raise ValueError("Contract ID is required")
    
    # Validate value
    if value <= 0:
        raise ValueError(f"Invalid value: {value}")
    
    # Create transaction
    return create_contract_transaction(
        sender=sender,
        private_key=private_key,
        contract_id=contract_id,
        function=None,  # None for transfer
        arguments=[],
        value=value,
        gas_limit=gas_limit,
        gas_price=gas_price
    )


def validate_contract_transaction(transaction: ContractTransaction) -> bool:
    """
    Validate a contract transaction.
    
    Args:
        transaction: The transaction to validate.
        
    Returns:
        True if the transaction is valid, False otherwise.
    """
    try:
        # Check if the transaction has a signature
        if not transaction.signature:
            logger.warning("Transaction has no signature")
            return False
        
        # Verify the signature
        signing_data = transaction.get_signing_data()
        if not verify_signature(signing_data, transaction.signature, transaction.sender):
            logger.warning("Invalid transaction signature")
            return False
        
        # Check if the sender is valid
        if not is_valid_address(transaction.sender):
            logger.warning(f"Invalid sender address: {transaction.sender}")
            return False
        
        # Check if the value is valid
        if transaction.value < 0:
            logger.warning(f"Invalid value: {transaction.value}")
            return False
        
        # Check if the gas parameters are valid
        if transaction.gas_limit <= 0:
            logger.warning(f"Invalid gas limit: {transaction.gas_limit}")
            return False
        
        if transaction.gas_price <= 0:
            logger.warning(f"Invalid gas price: {transaction.gas_price}")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Error validating contract transaction: {e}")
        return False


def serialize_contract_transaction(transaction: ContractTransaction) -> str:
    """
    Serialize a contract transaction to JSON.
    
    Args:
        transaction: The transaction to serialize.
        
    Returns:
        JSON string representation of the transaction.
    """
    return json.dumps(transaction.model_dump(), sort_keys=True)


def deserialize_contract_transaction(json_str: str) -> ContractTransaction:
    """
    Deserialize a contract transaction from JSON.
    
    Args:
        json_str: JSON string representation of the transaction.
        
    Returns:
        The deserialized transaction.
        
    Raises:
        ValueError: If the JSON is invalid.
    """
    try:
        data = json.loads(json_str)
        return ContractTransaction(**data)
    except Exception as e:
        raise ValueError(f"Error deserializing contract transaction: {e}")
