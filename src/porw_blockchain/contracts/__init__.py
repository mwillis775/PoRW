# src/porw_blockchain/contracts/__init__.py
"""
Smart contracts module for the PoRW blockchain.

This package provides functionality for creating, deploying, and executing
smart contracts on the PoRW blockchain.
"""

from .models import (
    SmartContract,
    ContractTransaction,
    ContractExecutionResult,
    ContractEvent,
    ContractState,
    ContractLanguage
)
from .manager import ContractManager
from .vm import ContractVM, ContractError, OutOfGasError
from .transaction import (
    create_contract_deployment_transaction,
    create_contract_call_transaction,
    create_contract_transfer_transaction,
    validate_contract_transaction,
    serialize_contract_transaction,
    deserialize_contract_transaction
)
