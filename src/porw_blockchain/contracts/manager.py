"""
Contract manager for the PoRW blockchain.

This module provides functionality for managing smart contracts,
including deployment, execution, and state management.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from .models import (
    SmartContract,
    ContractTransaction,
    ContractExecutionResult,
    ContractEvent,
    ContractState
)
from .vm import ContractVM, ContractError

# Configure logger
logger = logging.getLogger(__name__)


class ContractManager:
    """
    Manages smart contracts on the PoRW blockchain.
    """
    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the contract manager.
        
        Args:
            data_dir: Directory for storing contract data.
        """
        self.vm = ContractVM()
        
        # Set up data directory
        if data_dir is None:
            data_dir = Path.home() / ".porw" / "contracts"
        elif isinstance(data_dir, str):
            data_dir = Path(data_dir)
        
        self.data_dir = data_dir
        self.contracts_dir = self.data_dir / "contracts"
        self.events_dir = self.data_dir / "events"
        
        # Create directories if they don't exist
        os.makedirs(self.contracts_dir, exist_ok=True)
        os.makedirs(self.events_dir, exist_ok=True)
        
        # Load existing contracts
        self._load_contracts()
    
    def _load_contracts(self) -> None:
        """Load existing contracts from storage."""
        for contract_file in self.contracts_dir.glob("contract_*.json"):
            try:
                with open(contract_file, 'r') as f:
                    contract_data = json.load(f)
                
                contract = SmartContract.from_dict(contract_data)
                self.vm.register_contract(contract)
                
                logger.info(f"Loaded contract {contract.contract_id}")
            except Exception as e:
                logger.error(f"Error loading contract from {contract_file}: {e}")
    
    def _save_contract(self, contract: SmartContract) -> None:
        """
        Save a contract to disk.
        
        Args:
            contract: The contract to save.
        """
        contract_file = self.contracts_dir / f"contract_{contract.contract_id}.json"
        
        try:
            with open(contract_file, 'w') as f:
                json.dump(contract.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving contract to {contract_file}: {e}")
    
    def _save_event(self, event: ContractEvent) -> None:
        """
        Save an event to disk.
        
        Args:
            event: The event to save.
        """
        event_file = self.events_dir / f"event_{event.contract_id}_{int(event.timestamp)}.json"
        
        try:
            with open(event_file, 'w') as f:
                json.dump(event.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving event to {event_file}: {e}")
    
    def deploy_contract(self, transaction: ContractTransaction) -> ContractExecutionResult:
        """
        Deploy a new contract.
        
        Args:
            transaction: The deployment transaction.
            
        Returns:
            The result of the deployment.
        """
        result = self.vm.execute_transaction(transaction)
        
        if result.success:
            # Get the contract ID from the result
            contract_id = result.return_value
            
            # Get the contract from the VM
            contract = self.vm.get_contract(contract_id)
            
            if contract:
                # Save the contract
                self._save_contract(contract)
                
                # Update contract state
                contract.state = ContractState.ACTIVE
                self._save_contract(contract)
        
        return result
    
    def execute_transaction(self, transaction: ContractTransaction) -> ContractExecutionResult:
        """
        Execute a contract transaction.
        
        Args:
            transaction: The transaction to execute.
            
        Returns:
            The result of the execution.
        """
        # Check if the contract exists
        if transaction.contract_id:
            contract = self.vm.get_contract(transaction.contract_id)
            if not contract:
                return ContractExecutionResult(
                    success=False,
                    gas_used=0,
                    error=f"Contract not found: {transaction.contract_id}"
                )
            
            # Check if the contract is active
            if contract.state != ContractState.ACTIVE:
                return ContractExecutionResult(
                    success=False,
                    gas_used=0,
                    error=f"Contract is not active: {contract.state}"
                )
        
        # Execute the transaction
        result = self.vm.execute_transaction(transaction)
        
        if result.success:
            # Get the contract from the VM
            contract = self.vm.get_contract(transaction.contract_id)
            
            if contract:
                # Save the contract with updated state
                self._save_contract(contract)
                
                # Save events
                for event in result.events:
                    self._save_event(event)
        
        return result
    
    def get_contract(self, contract_id: str) -> Optional[SmartContract]:
        """
        Get a contract by ID.
        
        Args:
            contract_id: The ID of the contract.
            
        Returns:
            The contract, or None if not found.
        """
        return self.vm.get_contract(contract_id)
    
    def list_contracts(self) -> List[SmartContract]:
        """
        Get a list of all contracts.
        
        Returns:
            List of contracts.
        """
        return list(self.vm.contracts.values())
    
    def get_contract_events(self, contract_id: str) -> List[ContractEvent]:
        """
        Get events for a contract.
        
        Args:
            contract_id: The ID of the contract.
            
        Returns:
            List of events.
        """
        events = []
        
        for event_file in self.events_dir.glob(f"event_{contract_id}_*.json"):
            try:
                with open(event_file, 'r') as f:
                    event_data = json.load(f)
                
                event = ContractEvent.from_dict(event_data)
                events.append(event)
            except Exception as e:
                logger.error(f"Error loading event from {event_file}: {e}")
        
        # Sort events by timestamp
        events.sort(key=lambda e: e.timestamp)
        
        return events
    
    def update_blockchain_state(self, state: Dict[str, Any]) -> None:
        """
        Update the blockchain state.
        
        Args:
            state: The new blockchain state.
        """
        self.vm.update_blockchain_state(state)
    
    def pause_contract(self, contract_id: str) -> bool:
        """
        Pause a contract.
        
        Args:
            contract_id: The ID of the contract.
            
        Returns:
            True if successful, False otherwise.
        """
        contract = self.vm.get_contract(contract_id)
        if not contract:
            return False
        
        contract.state = ContractState.PAUSED
        contract.updated_at = time.time()
        
        self._save_contract(contract)
        return True
    
    def resume_contract(self, contract_id: str) -> bool:
        """
        Resume a paused contract.
        
        Args:
            contract_id: The ID of the contract.
            
        Returns:
            True if successful, False otherwise.
        """
        contract = self.vm.get_contract(contract_id)
        if not contract:
            return False
        
        if contract.state != ContractState.PAUSED:
            return False
        
        contract.state = ContractState.ACTIVE
        contract.updated_at = time.time()
        
        self._save_contract(contract)
        return True
    
    def terminate_contract(self, contract_id: str) -> bool:
        """
        Terminate a contract.
        
        Args:
            contract_id: The ID of the contract.
            
        Returns:
            True if successful, False otherwise.
        """
        contract = self.vm.get_contract(contract_id)
        if not contract:
            return False
        
        contract.state = ContractState.TERMINATED
        contract.updated_at = time.time()
        
        self._save_contract(contract)
        return True
