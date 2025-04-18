"""
Virtual Machine for executing smart contracts on the PoRW blockchain.

This module provides a sandboxed environment for executing smart contracts
written in Python, WebAssembly, or JSON.
"""

import ast
import builtins
import importlib
import inspect
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Set, Tuple, Union
from types import ModuleType

from .models import (
    SmartContract,
    ContractTransaction,
    ContractExecutionResult,
    ContractEvent,
    ContractLanguage
)

# Configure logger
logger = logging.getLogger(__name__)


class GasCounter:
    """
    Tracks gas usage during contract execution.
    """
    # Gas costs for different operations
    COSTS = {
        "LOAD_ATTR": 1,       # Loading an attribute
        "LOAD_CONST": 1,      # Loading a constant
        "LOAD_GLOBAL": 1,     # Loading a global variable
        "LOAD_NAME": 1,       # Loading a name
        "STORE_ATTR": 2,      # Storing an attribute
        "STORE_NAME": 2,      # Storing a name
        "BINARY_ADD": 2,      # Addition
        "BINARY_SUBTRACT": 2, # Subtraction
        "BINARY_MULTIPLY": 3, # Multiplication
        "BINARY_DIVIDE": 3,   # Division
        "COMPARE_OP": 2,      # Comparison
        "CALL_FUNCTION": 5,   # Function call
        "JUMP_ABSOLUTE": 1,   # Jump
        "JUMP_IF_TRUE": 1,    # Conditional jump
        "JUMP_IF_FALSE": 1,   # Conditional jump
        "FOR_ITER": 3,        # Loop iteration
        "LIST_APPEND": 2,     # Append to list
        "DICT_UPDATE": 3,     # Update dictionary
        "DEFAULT": 1          # Default cost for other operations
    }
    
    def __init__(self, gas_limit: int):
        """
        Initialize the gas counter.
        
        Args:
            gas_limit: Maximum amount of gas that can be used.
        """
        self.gas_limit = gas_limit
        self.gas_used = 0
    
    def charge(self, op_name: str, count: int = 1) -> None:
        """
        Charge gas for an operation.
        
        Args:
            op_name: Name of the operation.
            count: Number of times to charge for the operation.
            
        Raises:
            OutOfGasError: If the gas limit is exceeded.
        """
        cost = self.COSTS.get(op_name, self.COSTS["DEFAULT"]) * count
        self.gas_used += cost
        
        if self.gas_used > self.gas_limit:
            raise OutOfGasError(f"Gas limit exceeded: {self.gas_used} > {self.gas_limit}")
    
    def remaining(self) -> int:
        """
        Get the remaining gas.
        
        Returns:
            The amount of gas remaining.
        """
        return max(0, self.gas_limit - self.gas_used)


class ContractError(Exception):
    """Base class for contract-related errors."""
    pass


class OutOfGasError(ContractError):
    """Raised when a contract runs out of gas."""
    pass


class InvalidContractError(ContractError):
    """Raised when a contract is invalid."""
    pass


class ContractExecutionError(ContractError):
    """Raised when an error occurs during contract execution."""
    pass


class ContractContext:
    """
    Execution context for a smart contract.
    
    Provides access to blockchain data and contract state during execution.
    """
    def __init__(
        self,
        contract: SmartContract,
        transaction: ContractTransaction,
        gas_counter: GasCounter,
        blockchain_state: Dict[str, Any]
    ):
        """
        Initialize the contract context.
        
        Args:
            contract: The contract being executed.
            transaction: The transaction that triggered the execution.
            gas_counter: The gas counter for tracking gas usage.
            blockchain_state: Current state of the blockchain.
        """
        self.contract = contract
        self.transaction = transaction
        self.gas_counter = gas_counter
        self.blockchain_state = blockchain_state
        self.logs: List[str] = []
        self.events: List[ContractEvent] = []
        self.state_changes: Dict[str, Any] = {}
    
    def log(self, message: str) -> None:
        """
        Add a log message.
        
        Args:
            message: The message to log.
        """
        self.gas_counter.charge("CALL_FUNCTION")
        self.logs.append(message)
    
    def emit_event(self, name: str, data: Dict[str, Any]) -> None:
        """
        Emit an event.
        
        Args:
            name: Name of the event.
            data: Event data.
        """
        self.gas_counter.charge("CALL_FUNCTION")
        self.gas_counter.charge("DICT_UPDATE", len(data))
        
        event = ContractEvent(
            contract_id=self.contract.contract_id,
            name=name,
            data=data,
            transaction_id=self.transaction.transaction_id,
            timestamp=time.time()
        )
        self.events.append(event)
    
    def get_storage(self, key: str) -> Any:
        """
        Get a value from the contract's storage.
        
        Args:
            key: The key to retrieve.
            
        Returns:
            The value associated with the key, or None if not found.
        """
        self.gas_counter.charge("CALL_FUNCTION")
        self.gas_counter.charge("LOAD_ATTR")
        return self.contract.storage.get(key)
    
    def set_storage(self, key: str, value: Any) -> None:
        """
        Set a value in the contract's storage.
        
        Args:
            key: The key to set.
            value: The value to store.
        """
        self.gas_counter.charge("CALL_FUNCTION")
        self.gas_counter.charge("STORE_ATTR")
        self.state_changes[key] = value
    
    def get_balance(self, address: Optional[str] = None) -> float:
        """
        Get the balance of an address.
        
        Args:
            address: The address to check, or None for the contract's balance.
            
        Returns:
            The balance in PORW tokens.
        """
        self.gas_counter.charge("CALL_FUNCTION")
        
        if address is None:
            return self.contract.balance
        
        # In a real implementation, this would query the blockchain state
        return self.blockchain_state.get("balances", {}).get(address, 0.0)
    
    def get_block_height(self) -> int:
        """
        Get the current block height.
        
        Returns:
            The current block height.
        """
        self.gas_counter.charge("CALL_FUNCTION")
        return self.blockchain_state.get("block_height", 0)
    
    def get_timestamp(self) -> float:
        """
        Get the current block timestamp.
        
        Returns:
            The current block timestamp.
        """
        self.gas_counter.charge("CALL_FUNCTION")
        return self.blockchain_state.get("timestamp", time.time())
    
    def get_sender(self) -> str:
        """
        Get the address of the transaction sender.
        
        Returns:
            The sender's address.
        """
        self.gas_counter.charge("CALL_FUNCTION")
        return self.transaction.sender
    
    def get_value(self) -> float:
        """
        Get the value sent with the transaction.
        
        Returns:
            The value in PORW tokens.
        """
        self.gas_counter.charge("CALL_FUNCTION")
        return self.transaction.value


class ContractVM:
    """
    Virtual Machine for executing smart contracts.
    """
    def __init__(self):
        """Initialize the virtual machine."""
        self.contracts: Dict[str, SmartContract] = {}
        self.blockchain_state: Dict[str, Any] = {
            "block_height": 0,
            "timestamp": time.time(),
            "balances": {}
        }
    
    def register_contract(self, contract: SmartContract) -> None:
        """
        Register a contract with the VM.
        
        Args:
            contract: The contract to register.
        """
        self.contracts[contract.contract_id] = contract
    
    def get_contract(self, contract_id: str) -> Optional[SmartContract]:
        """
        Get a contract by ID.
        
        Args:
            contract_id: The ID of the contract.
            
        Returns:
            The contract, or None if not found.
        """
        return self.contracts.get(contract_id)
    
    def update_blockchain_state(self, state: Dict[str, Any]) -> None:
        """
        Update the blockchain state.
        
        Args:
            state: The new blockchain state.
        """
        self.blockchain_state.update(state)
    
    def execute_transaction(self, transaction: ContractTransaction) -> ContractExecutionResult:
        """
        Execute a contract transaction.
        
        Args:
            transaction: The transaction to execute.
            
        Returns:
            The result of the execution.
            
        Raises:
            ContractError: If an error occurs during execution.
        """
        # Check if this is a contract deployment
        if transaction.contract_id is None:
            # This is a contract deployment
            return self._deploy_contract(transaction)
        
        # This is a contract function call or token transfer
        contract = self.get_contract(transaction.contract_id)
        if contract is None:
            raise ContractError(f"Contract not found: {transaction.contract_id}")
        
        # Initialize gas counter
        gas_counter = GasCounter(transaction.gas_limit)
        
        # Create execution context
        context = ContractContext(
            contract=contract,
            transaction=transaction,
            gas_counter=gas_counter,
            blockchain_state=self.blockchain_state
        )
        
        try:
            # If no function is specified, this is a token transfer
            if transaction.function is None:
                # Update contract balance
                contract.balance += transaction.value
                
                return ContractExecutionResult(
                    success=True,
                    gas_used=gas_counter.gas_used,
                    logs=[f"Transferred {transaction.value} PORW to contract {contract.contract_id}"]
                )
            
            # Execute the specified function
            if contract.language == ContractLanguage.PYTHON:
                result = self._execute_python_contract(contract, transaction.function, transaction.arguments, context)
            elif contract.language == ContractLanguage.WASM:
                result = self._execute_wasm_contract(contract, transaction.function, transaction.arguments, context)
            elif contract.language == ContractLanguage.JSON:
                result = self._execute_json_contract(contract, transaction.function, transaction.arguments, context)
            else:
                raise ContractError(f"Unsupported contract language: {contract.language}")
            
            # Apply state changes
            for key, value in context.state_changes.items():
                contract.storage[key] = value
            
            # Update contract
            contract.updated_at = time.time()
            
            return ContractExecutionResult(
                success=True,
                return_value=result,
                gas_used=gas_counter.gas_used,
                logs=context.logs,
                state_changes=context.state_changes,
                events=context.events
            )
        
        except OutOfGasError as e:
            return ContractExecutionResult(
                success=False,
                gas_used=gas_counter.gas_limit,  # All gas is consumed
                error=str(e)
            )
        
        except Exception as e:
            logger.exception(f"Error executing contract {contract.contract_id}")
            return ContractExecutionResult(
                success=False,
                gas_used=gas_counter.gas_used,
                error=str(e)
            )
    
    def _deploy_contract(self, transaction: ContractTransaction) -> ContractExecutionResult:
        """
        Deploy a new contract.
        
        Args:
            transaction: The deployment transaction.
            
        Returns:
            The result of the deployment.
            
        Raises:
            ContractError: If an error occurs during deployment.
        """
        try:
            # Parse contract data from transaction arguments
            if len(transaction.arguments) < 1:
                raise ContractError("Contract data not provided")
            
            contract_data = transaction.arguments[0]
            if not isinstance(contract_data, dict):
                raise ContractError("Contract data must be a dictionary")
            
            # Create contract
            contract_data["creator"] = transaction.sender
            contract_data["balance"] = transaction.value
            
            contract = SmartContract(**contract_data)
            
            # Validate contract
            if contract.language == ContractLanguage.PYTHON:
                self._validate_python_contract(contract)
            elif contract.language == ContractLanguage.WASM:
                self._validate_wasm_contract(contract)
            elif contract.language == ContractLanguage.JSON:
                self._validate_json_contract(contract)
            else:
                raise ContractError(f"Unsupported contract language: {contract.language}")
            
            # Register contract
            self.register_contract(contract)
            
            return ContractExecutionResult(
                success=True,
                return_value=contract.contract_id,
                gas_used=transaction.gas_limit // 2,  # Arbitrary gas usage for deployment
                logs=[f"Deployed contract {contract.contract_id}"]
            )
        
        except Exception as e:
            logger.exception("Error deploying contract")
            return ContractExecutionResult(
                success=False,
                gas_used=transaction.gas_limit,  # All gas is consumed on error
                error=str(e)
            )
    
    def _validate_python_contract(self, contract: SmartContract) -> None:
        """
        Validate a Python contract.
        
        Args:
            contract: The contract to validate.
            
        Raises:
            InvalidContractError: If the contract is invalid.
        """
        try:
            # Parse the code
            tree = ast.parse(contract.code)
            
            # Check for prohibited constructs
            for node in ast.walk(tree):
                # Disallow imports
                if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    raise InvalidContractError("Import statements are not allowed in contracts")
                
                # Disallow exec and eval
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ["exec", "eval"]:
                            raise InvalidContractError(f"Use of {node.func.id} is not allowed in contracts")
            
            # Check ABI
            if not isinstance(contract.abi, dict):
                raise InvalidContractError("ABI must be a dictionary")
            
            if "functions" not in contract.abi:
                raise InvalidContractError("ABI must contain a 'functions' field")
            
            if not isinstance(contract.abi["functions"], list):
                raise InvalidContractError("ABI 'functions' field must be a list")
            
            # Validate each function in the ABI
            for func in contract.abi["functions"]:
                if not isinstance(func, dict):
                    raise InvalidContractError("Each function in ABI must be a dictionary")
                
                if "name" not in func:
                    raise InvalidContractError("Each function in ABI must have a 'name' field")
                
                if "params" not in func:
                    raise InvalidContractError("Each function in ABI must have a 'params' field")
                
                if not isinstance(func["params"], list):
                    raise InvalidContractError("Function 'params' field must be a list")
        
        except SyntaxError as e:
            raise InvalidContractError(f"Syntax error in contract code: {e}")
        
        except Exception as e:
            raise InvalidContractError(f"Error validating contract: {e}")
    
    def _validate_wasm_contract(self, contract: SmartContract) -> None:
        """
        Validate a WebAssembly contract.
        
        Args:
            contract: The contract to validate.
            
        Raises:
            InvalidContractError: If the contract is invalid.
        """
        # WebAssembly validation would go here
        # For now, just check that the ABI is valid
        if not isinstance(contract.abi, dict):
            raise InvalidContractError("ABI must be a dictionary")
        
        if "functions" not in contract.abi:
            raise InvalidContractError("ABI must contain a 'functions' field")
        
        if not isinstance(contract.abi["functions"], list):
            raise InvalidContractError("ABI 'functions' field must be a list")
    
    def _validate_json_contract(self, contract: SmartContract) -> None:
        """
        Validate a JSON contract.
        
        Args:
            contract: The contract to validate.
            
        Raises:
            InvalidContractError: If the contract is invalid.
        """
        try:
            # Parse the code as JSON
            code_json = json.loads(contract.code)
            
            # Check that the code is a dictionary
            if not isinstance(code_json, dict):
                raise InvalidContractError("JSON contract code must be a dictionary")
            
            # Check that the code contains functions
            if "functions" not in code_json:
                raise InvalidContractError("JSON contract must contain a 'functions' field")
            
            if not isinstance(code_json["functions"], dict):
                raise InvalidContractError("JSON contract 'functions' field must be a dictionary")
            
            # Check ABI
            if not isinstance(contract.abi, dict):
                raise InvalidContractError("ABI must be a dictionary")
            
            if "functions" not in contract.abi:
                raise InvalidContractError("ABI must contain a 'functions' field")
            
            if not isinstance(contract.abi["functions"], list):
                raise InvalidContractError("ABI 'functions' field must be a list")
            
            # Validate each function in the ABI
            for func in contract.abi["functions"]:
                if not isinstance(func, dict):
                    raise InvalidContractError("Each function in ABI must be a dictionary")
                
                if "name" not in func:
                    raise InvalidContractError("Each function in ABI must have a 'name' field")
                
                if func["name"] not in code_json["functions"]:
                    raise InvalidContractError(f"Function '{func['name']}' declared in ABI but not found in code")
        
        except json.JSONDecodeError:
            raise InvalidContractError("Invalid JSON in contract code")
        
        except Exception as e:
            raise InvalidContractError(f"Error validating contract: {e}")
    
    def _execute_python_contract(
        self,
        contract: SmartContract,
        function_name: str,
        arguments: List[Any],
        context: ContractContext
    ) -> Any:
        """
        Execute a Python contract.
        
        Args:
            contract: The contract to execute.
            function_name: The name of the function to call.
            arguments: The arguments to pass to the function.
            context: The execution context.
            
        Returns:
            The result of the function call.
            
        Raises:
            ContractExecutionError: If an error occurs during execution.
        """
        # Check if the function exists in the ABI
        function_exists = False
        for func in contract.abi.get("functions", []):
            if func.get("name") == function_name:
                function_exists = True
                break
        
        if not function_exists:
            raise ContractExecutionError(f"Function '{function_name}' not found in contract ABI")
        
        # Create a safe execution environment
        safe_builtins = {
            name: getattr(builtins, name)
            for name in [
                "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float",
                "frozenset", "int", "isinstance", "issubclass", "len", "list", "map",
                "max", "min", "range", "reversed", "round", "set", "sorted", "str",
                "sum", "tuple", "zip"
            ]
        }
        
        # Create a namespace for the contract
        namespace = {
            "__builtins__": safe_builtins,
            "context": context
        }
        
        try:
            # Execute the contract code
            exec(contract.code, namespace)
            
            # Check if the function exists
            if function_name not in namespace:
                raise ContractExecutionError(f"Function '{function_name}' not found in contract code")
            
            # Call the function
            function = namespace[function_name]
            if not callable(function):
                raise ContractExecutionError(f"'{function_name}' is not a callable function")
            
            return function(*arguments)
        
        except Exception as e:
            raise ContractExecutionError(f"Error executing contract: {e}")
    
    def _execute_wasm_contract(
        self,
        contract: SmartContract,
        function_name: str,
        arguments: List[Any],
        context: ContractContext
    ) -> Any:
        """
        Execute a WebAssembly contract.
        
        Args:
            contract: The contract to execute.
            function_name: The name of the function to call.
            arguments: The arguments to pass to the function.
            context: The execution context.
            
        Returns:
            The result of the function call.
            
        Raises:
            ContractExecutionError: If an error occurs during execution.
        """
        # WebAssembly execution would go here
        # For now, raise an error
        raise ContractExecutionError("WebAssembly contracts are not yet supported")
    
    def _execute_json_contract(
        self,
        contract: SmartContract,
        function_name: str,
        arguments: List[Any],
        context: ContractContext
    ) -> Any:
        """
        Execute a JSON contract.
        
        Args:
            contract: The contract to execute.
            function_name: The name of the function to call.
            arguments: The arguments to pass to the function.
            context: The execution context.
            
        Returns:
            The result of the function call.
            
        Raises:
            ContractExecutionError: If an error occurs during execution.
        """
        try:
            # Parse the code
            code_json = json.loads(contract.code)
            
            # Check if the function exists
            if "functions" not in code_json:
                raise ContractExecutionError("Contract does not contain any functions")
            
            if function_name not in code_json["functions"]:
                raise ContractExecutionError(f"Function '{function_name}' not found in contract")
            
            # Get the function
            function = code_json["functions"][function_name]
            
            # Check if the function is a simple value
            if not isinstance(function, dict):
                return function
            
            # Check if the function is a conditional
            if "if" in function:
                condition = function["if"]
                if isinstance(condition, dict):
                    # Evaluate the condition
                    if "equals" in condition:
                        equals = condition["equals"]
                        if len(equals) != 2:
                            raise ContractExecutionError("'equals' condition must have exactly 2 elements")
                        
                        # Get the values to compare
                        left = equals[0]
                        right = equals[1]
                        
                        # Handle special values
                        if isinstance(left, str) and left.startswith("$"):
                            if left == "$sender":
                                left = context.get_sender()
                            elif left == "$value":
                                left = context.get_value()
                            elif left == "$balance":
                                left = context.get_balance()
                            elif left == "$timestamp":
                                left = context.get_timestamp()
                            elif left == "$block_height":
                                left = context.get_block_height()
                            elif left.startswith("$storage."):
                                key = left[9:]
                                left = context.get_storage(key)
                            elif left.startswith("$arg."):
                                index = int(left[5:])
                                if index < len(arguments):
                                    left = arguments[index]
                                else:
                                    left = None
                        
                        if isinstance(right, str) and right.startswith("$"):
                            if right == "$sender":
                                right = context.get_sender()
                            elif right == "$value":
                                right = context.get_value()
                            elif right == "$balance":
                                right = context.get_balance()
                            elif right == "$timestamp":
                                right = context.get_timestamp()
                            elif right == "$block_height":
                                right = context.get_block_height()
                            elif right.startswith("$storage."):
                                key = right[9:]
                                right = context.get_storage(key)
                            elif right.startswith("$arg."):
                                index = int(right[5:])
                                if index < len(arguments):
                                    right = arguments[index]
                                else:
                                    right = None
                        
                        # Compare the values
                        if left == right:
                            return self._execute_json_action(function["then"], arguments, context)
                        elif "else" in function:
                            return self._execute_json_action(function["else"], arguments, context)
                        else:
                            return None
                    
                    # Add more condition types as needed
                    
                    raise ContractExecutionError(f"Unsupported condition type: {list(condition.keys())[0]}")
            
            # Check if the function is an action
            return self._execute_json_action(function, arguments, context)
        
        except json.JSONDecodeError:
            raise ContractExecutionError("Invalid JSON in contract code")
        
        except Exception as e:
            raise ContractExecutionError(f"Error executing contract: {e}")
    
    def _execute_json_action(
        self,
        action: Dict[str, Any],
        arguments: List[Any],
        context: ContractContext
    ) -> Any:
        """
        Execute a JSON contract action.
        
        Args:
            action: The action to execute.
            arguments: The arguments passed to the function.
            context: The execution context.
            
        Returns:
            The result of the action.
            
        Raises:
            ContractExecutionError: If an error occurs during execution.
        """
        if not isinstance(action, dict):
            return action
        
        # Check for special actions
        if "return" in action:
            return action["return"]
        
        if "set_storage" in action:
            storage_updates = action["set_storage"]
            if not isinstance(storage_updates, dict):
                raise ContractExecutionError("'set_storage' action must be a dictionary")
            
            for key, value in storage_updates.items():
                # Handle special values
                if isinstance(value, str) and value.startswith("$"):
                    if value == "$sender":
                        value = context.get_sender()
                    elif value == "$value":
                        value = context.get_value()
                    elif value == "$balance":
                        value = context.get_balance()
                    elif value == "$timestamp":
                        value = context.get_timestamp()
                    elif value == "$block_height":
                        value = context.get_block_height()
                    elif value.startswith("$storage."):
                        storage_key = value[9:]
                        value = context.get_storage(storage_key)
                    elif value.startswith("$arg."):
                        index = int(value[5:])
                        if index < len(arguments):
                            value = arguments[index]
                        else:
                            value = None
                
                context.set_storage(key, value)
            
            return None
        
        if "log" in action:
            message = action["log"]
            
            # Handle special values
            if isinstance(message, str) and message.startswith("$"):
                if message == "$sender":
                    message = context.get_sender()
                elif message == "$value":
                    message = str(context.get_value())
                elif message == "$balance":
                    message = str(context.get_balance())
                elif message == "$timestamp":
                    message = str(context.get_timestamp())
                elif message == "$block_height":
                    message = str(context.get_block_height())
                elif message.startswith("$storage."):
                    key = message[9:]
                    message = str(context.get_storage(key))
                elif message.startswith("$arg."):
                    index = int(message[5:])
                    if index < len(arguments):
                        message = str(arguments[index])
                    else:
                        message = "null"
            
            context.log(str(message))
            return None
        
        if "emit" in action:
            event = action["emit"]
            if not isinstance(event, dict):
                raise ContractExecutionError("'emit' action must be a dictionary")
            
            if "name" not in event:
                raise ContractExecutionError("Event must have a 'name' field")
            
            if "data" not in event:
                raise ContractExecutionError("Event must have a 'data' field")
            
            name = event["name"]
            data = event["data"]
            
            # Process data to handle special values
            processed_data = {}
            for key, value in data.items():
                if isinstance(value, str) and value.startswith("$"):
                    if value == "$sender":
                        value = context.get_sender()
                    elif value == "$value":
                        value = context.get_value()
                    elif value == "$balance":
                        value = context.get_balance()
                    elif value == "$timestamp":
                        value = context.get_timestamp()
                    elif value == "$block_height":
                        value = context.get_block_height()
                    elif value.startswith("$storage."):
                        storage_key = value[9:]
                        value = context.get_storage(storage_key)
                    elif value.startswith("$arg."):
                        index = int(value[5:])
                        if index < len(arguments):
                            value = arguments[index]
                        else:
                            value = None
                
                processed_data[key] = value
            
            context.emit_event(name, processed_data)
            return None
        
        # Add more action types as needed
        
        raise ContractExecutionError(f"Unsupported action type: {list(action.keys())[0]}")
