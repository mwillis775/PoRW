"""
API endpoints for smart contracts on the PoRW blockchain.

This module provides API endpoints for interacting with smart contracts,
including deployment, execution, and querying.
"""

import logging
from typing import Dict, List, Any, Optional, Union

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field

from .models import (
    SmartContract,
    ContractTransaction,
    ContractExecutionResult,
    ContractEvent,
    ContractState,
    ContractLanguage
)
from .manager import ContractManager
from .transaction import (
    create_contract_deployment_transaction,
    create_contract_call_transaction,
    create_contract_transfer_transaction,
    validate_contract_transaction
)

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/contracts",
    tags=["contracts"],
    responses={404: {"description": "Not found"}},
)

# Global contract manager instance
contract_manager = ContractManager()


# --- Request/Response Models ---

class ContractDeploymentRequest(BaseModel):
    """Request model for deploying a contract."""
    sender: str = Field(..., description="Address of the sender")
    name: str = Field(..., description="Name of the contract")
    description: Optional[str] = Field(None, description="Description of the contract")
    language: ContractLanguage = Field(..., description="Language of the contract")
    code: str = Field(..., description="Source code of the contract")
    abi: Dict[str, Any] = Field(..., description="ABI of the contract")
    value: float = Field(0.0, ge=0, description="Amount of PORW tokens to transfer to the contract")
    gas_limit: int = Field(2000000, gt=0, description="Maximum amount of gas that can be used")
    gas_price: float = Field(0.0000001, gt=0, description="Price per unit of gas in PORW tokens")
    private_key: str = Field(..., description="Private key of the sender (for signing)")


class ContractCallRequest(BaseModel):
    """Request model for calling a contract function."""
    sender: str = Field(..., description="Address of the sender")
    contract_id: str = Field(..., description="ID of the contract")
    function: str = Field(..., description="Name of the function to call")
    arguments: List[Any] = Field(default_factory=list, description="Arguments to pass to the function")
    value: float = Field(0.0, ge=0, description="Amount of PORW tokens to transfer to the contract")
    gas_limit: int = Field(1000000, gt=0, description="Maximum amount of gas that can be used")
    gas_price: float = Field(0.0000001, gt=0, description="Price per unit of gas in PORW tokens")
    private_key: str = Field(..., description="Private key of the sender (for signing)")


class ContractTransferRequest(BaseModel):
    """Request model for transferring tokens to a contract."""
    sender: str = Field(..., description="Address of the sender")
    contract_id: str = Field(..., description="ID of the contract")
    value: float = Field(..., gt=0, description="Amount of PORW tokens to transfer to the contract")
    gas_limit: int = Field(100000, gt=0, description="Maximum amount of gas that can be used")
    gas_price: float = Field(0.0000001, gt=0, description="Price per unit of gas in PORW tokens")
    private_key: str = Field(..., description="Private key of the sender (for signing)")


class ContractResponse(BaseModel):
    """Response model for contract information."""
    contract_id: str = Field(..., description="ID of the contract")
    creator: str = Field(..., description="Address of the contract creator")
    name: str = Field(..., description="Name of the contract")
    description: Optional[str] = Field(None, description="Description of the contract")
    language: ContractLanguage = Field(..., description="Language of the contract")
    abi: Dict[str, Any] = Field(..., description="ABI of the contract")
    state: ContractState = Field(..., description="State of the contract")
    created_at: float = Field(..., description="Timestamp when the contract was created")
    updated_at: Optional[float] = Field(None, description="Timestamp when the contract was last updated")
    balance: float = Field(..., description="Balance of the contract in PORW tokens")
    version: int = Field(..., description="Version of the contract")


class ContractListResponse(BaseModel):
    """Response model for listing contracts."""
    contracts: List[ContractResponse] = Field(..., description="List of contracts")


class ContractEventResponse(BaseModel):
    """Response model for contract events."""
    contract_id: str = Field(..., description="ID of the contract")
    name: str = Field(..., description="Name of the event")
    data: Dict[str, Any] = Field(..., description="Event data")
    block_index: Optional[int] = Field(None, description="Index of the block containing the event")
    transaction_id: str = Field(..., description="ID of the transaction that triggered the event")
    timestamp: float = Field(..., description="Timestamp when the event was emitted")


class ContractEventsResponse(BaseModel):
    """Response model for listing contract events."""
    events: List[ContractEventResponse] = Field(..., description="List of events")


class ContractExecutionResponse(BaseModel):
    """Response model for contract execution results."""
    success: bool = Field(..., description="Whether the execution was successful")
    return_value: Any = Field(None, description="Return value of the function call")
    gas_used: int = Field(..., description="Amount of gas used during execution")
    logs: List[str] = Field(..., description="Logs generated during execution")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    transaction_id: str = Field(..., description="ID of the transaction")


# --- API Endpoints ---

@router.post("/deploy", response_model=ContractExecutionResponse)
async def deploy_contract(request: ContractDeploymentRequest):
    """
    Deploy a new smart contract.
    """
    try:
        # Create contract data
        contract_data = {
            "name": request.name,
            "description": request.description,
            "language": request.language,
            "code": request.code,
            "abi": request.abi
        }
        
        # Create deployment transaction
        transaction = create_contract_deployment_transaction(
            sender=request.sender,
            private_key=request.private_key,
            contract_data=contract_data,
            value=request.value,
            gas_limit=request.gas_limit,
            gas_price=request.gas_price
        )
        
        # Validate transaction
        if not validate_contract_transaction(transaction):
            raise HTTPException(status_code=400, detail="Invalid transaction")
        
        # Deploy contract
        result = contract_manager.deploy_contract(transaction)
        
        # Return result
        return ContractExecutionResponse(
            success=result.success,
            return_value=result.return_value,
            gas_used=result.gas_used,
            logs=result.logs,
            error=result.error,
            transaction_id=transaction.transaction_id
        )
    
    except Exception as e:
        logger.exception("Error deploying contract")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/call", response_model=ContractExecutionResponse)
async def call_contract(request: ContractCallRequest):
    """
    Call a function on a smart contract.
    """
    try:
        # Create call transaction
        transaction = create_contract_call_transaction(
            sender=request.sender,
            private_key=request.private_key,
            contract_id=request.contract_id,
            function=request.function,
            arguments=request.arguments,
            value=request.value,
            gas_limit=request.gas_limit,
            gas_price=request.gas_price
        )
        
        # Validate transaction
        if not validate_contract_transaction(transaction):
            raise HTTPException(status_code=400, detail="Invalid transaction")
        
        # Execute transaction
        result = contract_manager.execute_transaction(transaction)
        
        # Return result
        return ContractExecutionResponse(
            success=result.success,
            return_value=result.return_value,
            gas_used=result.gas_used,
            logs=result.logs,
            error=result.error,
            transaction_id=transaction.transaction_id
        )
    
    except Exception as e:
        logger.exception("Error calling contract")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transfer", response_model=ContractExecutionResponse)
async def transfer_to_contract(request: ContractTransferRequest):
    """
    Transfer tokens to a smart contract.
    """
    try:
        # Create transfer transaction
        transaction = create_contract_transfer_transaction(
            sender=request.sender,
            private_key=request.private_key,
            contract_id=request.contract_id,
            value=request.value,
            gas_limit=request.gas_limit,
            gas_price=request.gas_price
        )
        
        # Validate transaction
        if not validate_contract_transaction(transaction):
            raise HTTPException(status_code=400, detail="Invalid transaction")
        
        # Execute transaction
        result = contract_manager.execute_transaction(transaction)
        
        # Return result
        return ContractExecutionResponse(
            success=result.success,
            return_value=result.return_value,
            gas_used=result.gas_used,
            logs=result.logs,
            error=result.error,
            transaction_id=transaction.transaction_id
        )
    
    except Exception as e:
        logger.exception("Error transferring to contract")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(contract_id: str):
    """
    Get information about a smart contract.
    """
    try:
        # Get contract
        contract = contract_manager.get_contract(contract_id)
        
        if not contract:
            raise HTTPException(status_code=404, detail=f"Contract not found: {contract_id}")
        
        # Return contract information
        return ContractResponse(
            contract_id=contract.contract_id,
            creator=contract.creator,
            name=contract.name,
            description=contract.description,
            language=contract.language,
            abi=contract.abi,
            state=contract.state,
            created_at=contract.created_at,
            updated_at=contract.updated_at,
            balance=contract.balance,
            version=contract.version
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.exception("Error getting contract")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=ContractListResponse)
async def list_contracts():
    """
    List all smart contracts.
    """
    try:
        # Get contracts
        contracts = contract_manager.list_contracts()
        
        # Convert to response model
        contract_responses = [
            ContractResponse(
                contract_id=contract.contract_id,
                creator=contract.creator,
                name=contract.name,
                description=contract.description,
                language=contract.language,
                abi=contract.abi,
                state=contract.state,
                created_at=contract.created_at,
                updated_at=contract.updated_at,
                balance=contract.balance,
                version=contract.version
            )
            for contract in contracts
        ]
        
        return ContractListResponse(contracts=contract_responses)
    
    except Exception as e:
        logger.exception("Error listing contracts")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{contract_id}/events", response_model=ContractEventsResponse)
async def get_contract_events(contract_id: str):
    """
    Get events for a smart contract.
    """
    try:
        # Check if contract exists
        contract = contract_manager.get_contract(contract_id)
        
        if not contract:
            raise HTTPException(status_code=404, detail=f"Contract not found: {contract_id}")
        
        # Get events
        events = contract_manager.get_contract_events(contract_id)
        
        # Convert to response model
        event_responses = [
            ContractEventResponse(
                contract_id=event.contract_id,
                name=event.name,
                data=event.data,
                block_index=event.block_index,
                transaction_id=event.transaction_id,
                timestamp=event.timestamp
            )
            for event in events
        ]
        
        return ContractEventsResponse(events=event_responses)
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.exception("Error getting contract events")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{contract_id}/pause", response_model=ContractResponse)
async def pause_contract(contract_id: str):
    """
    Pause a smart contract.
    """
    try:
        # Check if contract exists
        contract = contract_manager.get_contract(contract_id)
        
        if not contract:
            raise HTTPException(status_code=404, detail=f"Contract not found: {contract_id}")
        
        # Pause contract
        success = contract_manager.pause_contract(contract_id)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to pause contract: {contract_id}")
        
        # Get updated contract
        contract = contract_manager.get_contract(contract_id)
        
        # Return contract information
        return ContractResponse(
            contract_id=contract.contract_id,
            creator=contract.creator,
            name=contract.name,
            description=contract.description,
            language=contract.language,
            abi=contract.abi,
            state=contract.state,
            created_at=contract.created_at,
            updated_at=contract.updated_at,
            balance=contract.balance,
            version=contract.version
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.exception("Error pausing contract")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{contract_id}/resume", response_model=ContractResponse)
async def resume_contract(contract_id: str):
    """
    Resume a paused smart contract.
    """
    try:
        # Check if contract exists
        contract = contract_manager.get_contract(contract_id)
        
        if not contract:
            raise HTTPException(status_code=404, detail=f"Contract not found: {contract_id}")
        
        # Resume contract
        success = contract_manager.resume_contract(contract_id)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to resume contract: {contract_id}")
        
        # Get updated contract
        contract = contract_manager.get_contract(contract_id)
        
        # Return contract information
        return ContractResponse(
            contract_id=contract.contract_id,
            creator=contract.creator,
            name=contract.name,
            description=contract.description,
            language=contract.language,
            abi=contract.abi,
            state=contract.state,
            created_at=contract.created_at,
            updated_at=contract.updated_at,
            balance=contract.balance,
            version=contract.version
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.exception("Error resuming contract")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{contract_id}/terminate", response_model=ContractResponse)
async def terminate_contract(contract_id: str):
    """
    Terminate a smart contract.
    """
    try:
        # Check if contract exists
        contract = contract_manager.get_contract(contract_id)
        
        if not contract:
            raise HTTPException(status_code=404, detail=f"Contract not found: {contract_id}")
        
        # Terminate contract
        success = contract_manager.terminate_contract(contract_id)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to terminate contract: {contract_id}")
        
        # Get updated contract
        contract = contract_manager.get_contract(contract_id)
        
        # Return contract information
        return ContractResponse(
            contract_id=contract.contract_id,
            creator=contract.creator,
            name=contract.name,
            description=contract.description,
            language=contract.language,
            abi=contract.abi,
            state=contract.state,
            created_at=contract.created_at,
            updated_at=contract.updated_at,
            balance=contract.balance,
            version=contract.version
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.exception("Error terminating contract")
        raise HTTPException(status_code=500, detail=str(e))
