"""
Recurring transactions functionality for the PoRW blockchain wallet.

This module provides classes and functions for creating and managing
recurring transactions, allowing users to automate regular payments.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union

# Configure logger
logger = logging.getLogger(__name__)


class RecurrenceInterval(Enum):
    """Enum for recurrence intervals."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class RecurringTransaction:
    """
    Represents a recurring transaction.
    
    A recurring transaction contains information about a transaction that
    should be executed repeatedly at specified intervals.
    """
    
    def __init__(
        self,
        transaction_id: str,
        recipient: str,
        amount: float,
        interval: Union[RecurrenceInterval, str],
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        custom_days: Optional[int] = None,
        memo: Optional[str] = None,
        fee: Optional[float] = None,
        enabled: bool = True,
        last_executed: Optional[int] = None,
        next_execution: Optional[int] = None,
        execution_count: int = 0,
        max_executions: Optional[int] = None,
        created_at: Optional[int] = None,
        updated_at: Optional[int] = None
    ):
        """
        Initialize a recurring transaction.
        
        Args:
            transaction_id: Unique identifier for the recurring transaction.
            recipient: The recipient's address.
            amount: The amount to send.
            interval: The recurrence interval (daily, weekly, biweekly, monthly, quarterly, yearly, custom).
            start_date: Optional start date as Unix timestamp (default: current time).
            end_date: Optional end date as Unix timestamp.
            custom_days: Optional custom interval in days (only used if interval is CUSTOM).
            memo: Optional memo to include with the transaction.
            fee: Optional transaction fee.
            enabled: Whether the recurring transaction is enabled (default: True).
            last_executed: Optional timestamp of the last execution.
            next_execution: Optional timestamp of the next execution.
            execution_count: Number of times the transaction has been executed (default: 0).
            max_executions: Optional maximum number of executions.
            created_at: Optional creation timestamp (default: current time).
            updated_at: Optional update timestamp (default: current time).
        """
        self.transaction_id = transaction_id
        self.recipient = recipient
        self.amount = amount
        
        # Handle interval as string or enum
        if isinstance(interval, str):
            try:
                self.interval = RecurrenceInterval(interval)
            except ValueError:
                # Default to custom if invalid string
                self.interval = RecurrenceInterval.CUSTOM
                if custom_days is None:
                    custom_days = 30  # Default to 30 days if custom interval but no days specified
        else:
            self.interval = interval
        
        self.start_date = start_date or int(time.time())
        self.end_date = end_date
        self.custom_days = custom_days
        self.memo = memo
        self.fee = fee
        self.enabled = enabled
        self.last_executed = last_executed
        self.next_execution = next_execution or self._calculate_next_execution()
        self.execution_count = execution_count
        self.max_executions = max_executions
        self.created_at = created_at or int(time.time())
        self.updated_at = updated_at or int(time.time())
        
        logger.debug(f"Created recurring transaction {transaction_id} to {recipient} for {amount}")
    
    def _calculate_next_execution(self) -> int:
        """
        Calculate the next execution time based on the interval and last execution.
        
        Returns:
            The next execution time as Unix timestamp.
        """
        # If we have a last execution, calculate from that
        base_time = self.last_executed if self.last_executed else self.start_date
        
        # Convert timestamp to datetime
        base_dt = datetime.fromtimestamp(base_time)
        
        # Calculate next execution based on interval
        if self.interval == RecurrenceInterval.DAILY:
            next_dt = base_dt + timedelta(days=1)
        elif self.interval == RecurrenceInterval.WEEKLY:
            next_dt = base_dt + timedelta(weeks=1)
        elif self.interval == RecurrenceInterval.BIWEEKLY:
            next_dt = base_dt + timedelta(weeks=2)
        elif self.interval == RecurrenceInterval.MONTHLY:
            # Add a month (approximately)
            if base_dt.month == 12:
                next_dt = base_dt.replace(year=base_dt.year + 1, month=1)
            else:
                next_dt = base_dt.replace(month=base_dt.month + 1)
        elif self.interval == RecurrenceInterval.QUARTERLY:
            # Add 3 months
            month = base_dt.month
            year = base_dt.year
            month += 3
            if month > 12:
                month -= 12
                year += 1
            next_dt = base_dt.replace(year=year, month=month)
        elif self.interval == RecurrenceInterval.YEARLY:
            next_dt = base_dt.replace(year=base_dt.year + 1)
        elif self.interval == RecurrenceInterval.CUSTOM:
            days = self.custom_days or 30  # Default to 30 days if not specified
            next_dt = base_dt + timedelta(days=days)
        else:
            # Default to monthly if invalid interval
            if base_dt.month == 12:
                next_dt = base_dt.replace(year=base_dt.year + 1, month=1)
            else:
                next_dt = base_dt.replace(month=base_dt.month + 1)
        
        return int(next_dt.timestamp())
    
    def update_next_execution(self) -> int:
        """
        Update the next execution time.
        
        Returns:
            The updated next execution time.
        """
        self.next_execution = self._calculate_next_execution()
        return self.next_execution
    
    def is_due(self) -> bool:
        """
        Check if the recurring transaction is due for execution.
        
        Returns:
            True if the transaction is due, False otherwise.
        """
        if not self.enabled:
            return False
        
        current_time = int(time.time())
        
        # Check if we've reached the end date
        if self.end_date and current_time > self.end_date:
            return False
        
        # Check if we've reached the maximum number of executions
        if self.max_executions and self.execution_count >= self.max_executions:
            return False
        
        # Check if it's time to execute
        return current_time >= self.next_execution
    
    def mark_executed(self) -> None:
        """
        Mark the recurring transaction as executed.
        """
        current_time = int(time.time())
        self.last_executed = current_time
        self.execution_count += 1
        self.update_next_execution()
        self.updated_at = current_time
        
        logger.info(f"Marked recurring transaction {self.transaction_id} as executed")
    
    def update(
        self,
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
    ) -> None:
        """
        Update the recurring transaction.
        
        Args:
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
        """
        if recipient is not None:
            self.recipient = recipient
        
        if amount is not None:
            self.amount = amount
        
        if interval is not None:
            # Handle interval as string or enum
            if isinstance(interval, str):
                try:
                    self.interval = RecurrenceInterval(interval)
                except ValueError:
                    # Default to custom if invalid string
                    self.interval = RecurrenceInterval.CUSTOM
                    if custom_days is None and self.custom_days is None:
                        self.custom_days = 30  # Default to 30 days if custom interval but no days specified
            else:
                self.interval = interval
        
        if start_date is not None:
            self.start_date = start_date
        
        if end_date is not None:
            self.end_date = end_date
        
        if custom_days is not None:
            self.custom_days = custom_days
        
        if memo is not None:
            self.memo = memo
        
        if fee is not None:
            self.fee = fee
        
        if enabled is not None:
            self.enabled = enabled
        
        if max_executions is not None:
            self.max_executions = max_executions
        
        # Update next execution time
        self.update_next_execution()
        
        # Update timestamp
        self.updated_at = int(time.time())
        
        logger.debug(f"Updated recurring transaction {self.transaction_id}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the recurring transaction to a dictionary.
        
        Returns:
            A dictionary representation of the recurring transaction.
        """
        return {
            "transaction_id": self.transaction_id,
            "recipient": self.recipient,
            "amount": self.amount,
            "interval": self.interval.value,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "custom_days": self.custom_days,
            "memo": self.memo,
            "fee": self.fee,
            "enabled": self.enabled,
            "last_executed": self.last_executed,
            "next_execution": self.next_execution,
            "execution_count": self.execution_count,
            "max_executions": self.max_executions,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecurringTransaction':
        """
        Create a recurring transaction from a dictionary.
        
        Args:
            data: A dictionary representation of the recurring transaction.
            
        Returns:
            A RecurringTransaction object.
        """
        return cls(
            transaction_id=data["transaction_id"],
            recipient=data["recipient"],
            amount=data["amount"],
            interval=data["interval"],
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            custom_days=data.get("custom_days"),
            memo=data.get("memo"),
            fee=data.get("fee"),
            enabled=data.get("enabled", True),
            last_executed=data.get("last_executed"),
            next_execution=data.get("next_execution"),
            execution_count=data.get("execution_count", 0),
            max_executions=data.get("max_executions"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


class RecurringTransactionManager:
    """
    Manages recurring transactions.
    
    The recurring transaction manager provides functionality for adding, updating, removing,
    and executing recurring transactions.
    """
    
    def __init__(self):
        """
        Initialize a recurring transaction manager.
        """
        self.transactions: Dict[str, RecurringTransaction] = {}  # transaction_id -> RecurringTransaction
        
        logger.debug("Initialized RecurringTransactionManager")
    
    def add_transaction(
        self,
        transaction_id: str,
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
    ) -> RecurringTransaction:
        """
        Add a recurring transaction.
        
        Args:
            transaction_id: Unique identifier for the recurring transaction.
            recipient: The recipient's address.
            amount: The amount to send.
            interval: The recurrence interval.
            start_date: Optional start date as Unix timestamp.
            end_date: Optional end date as Unix timestamp.
            custom_days: Optional custom interval in days.
            memo: Optional memo to include with the transaction.
            fee: Optional transaction fee.
            enabled: Whether the recurring transaction is enabled.
            max_executions: Optional maximum number of executions.
            
        Returns:
            The added recurring transaction.
            
        Raises:
            ValueError: If a transaction with the same ID already exists.
        """
        if transaction_id in self.transactions:
            raise ValueError(f"Transaction with ID {transaction_id} already exists")
        
        # Create recurring transaction
        transaction = RecurringTransaction(
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
        
        # Add to transactions
        self.transactions[transaction_id] = transaction
        
        logger.info(f"Added recurring transaction {transaction_id}")
        return transaction
    
    def update_transaction(
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
    ) -> RecurringTransaction:
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
            The updated recurring transaction.
            
        Raises:
            ValueError: If the transaction is not found.
        """
        if transaction_id not in self.transactions:
            raise ValueError(f"Transaction with ID {transaction_id} not found")
        
        # Get transaction
        transaction = self.transactions[transaction_id]
        
        # Update transaction
        transaction.update(
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
        
        logger.info(f"Updated recurring transaction {transaction_id}")
        return transaction
    
    def remove_transaction(self, transaction_id: str) -> None:
        """
        Remove a recurring transaction.
        
        Args:
            transaction_id: The ID of the transaction to remove.
            
        Raises:
            ValueError: If the transaction is not found.
        """
        if transaction_id not in self.transactions:
            raise ValueError(f"Transaction with ID {transaction_id} not found")
        
        # Remove from transactions
        self.transactions.pop(transaction_id)
        
        logger.info(f"Removed recurring transaction {transaction_id}")
    
    def get_transaction(self, transaction_id: str) -> Optional[RecurringTransaction]:
        """
        Get a recurring transaction.
        
        Args:
            transaction_id: The ID of the transaction to get.
            
        Returns:
            The recurring transaction, or None if not found.
        """
        return self.transactions.get(transaction_id)
    
    def list_transactions(self) -> List[RecurringTransaction]:
        """
        List all recurring transactions.
        
        Returns:
            A list of all recurring transactions.
        """
        return list(self.transactions.values())
    
    def get_due_transactions(self) -> List[RecurringTransaction]:
        """
        Get recurring transactions that are due for execution.
        
        Returns:
            A list of recurring transactions that are due.
        """
        return [tx for tx in self.transactions.values() if tx.is_due()]
    
    def mark_executed(self, transaction_id: str) -> None:
        """
        Mark a recurring transaction as executed.
        
        Args:
            transaction_id: The ID of the transaction to mark as executed.
            
        Raises:
            ValueError: If the transaction is not found.
        """
        if transaction_id not in self.transactions:
            raise ValueError(f"Transaction with ID {transaction_id} not found")
        
        # Mark as executed
        self.transactions[transaction_id].mark_executed()
    
    def enable_transaction(self, transaction_id: str) -> RecurringTransaction:
        """
        Enable a recurring transaction.
        
        Args:
            transaction_id: The ID of the transaction to enable.
            
        Returns:
            The updated recurring transaction.
            
        Raises:
            ValueError: If the transaction is not found.
        """
        if transaction_id not in self.transactions:
            raise ValueError(f"Transaction with ID {transaction_id} not found")
        
        # Enable transaction
        transaction = self.transactions[transaction_id]
        transaction.update(enabled=True)
        
        logger.info(f"Enabled recurring transaction {transaction_id}")
        return transaction
    
    def disable_transaction(self, transaction_id: str) -> RecurringTransaction:
        """
        Disable a recurring transaction.
        
        Args:
            transaction_id: The ID of the transaction to disable.
            
        Returns:
            The updated recurring transaction.
            
        Raises:
            ValueError: If the transaction is not found.
        """
        if transaction_id not in self.transactions:
            raise ValueError(f"Transaction with ID {transaction_id} not found")
        
        # Disable transaction
        transaction = self.transactions[transaction_id]
        transaction.update(enabled=False)
        
        logger.info(f"Disabled recurring transaction {transaction_id}")
        return transaction
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the recurring transaction manager to a dictionary.
        
        Returns:
            A dictionary representation of the recurring transaction manager.
        """
        return {
            "transactions": {
                transaction_id: transaction.to_dict()
                for transaction_id, transaction in self.transactions.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecurringTransactionManager':
        """
        Create a recurring transaction manager from a dictionary.
        
        Args:
            data: A dictionary representation of the recurring transaction manager.
            
        Returns:
            A RecurringTransactionManager object.
        """
        manager = cls()
        
        transactions_data = data.get("transactions", {})
        for transaction_id, transaction_data in transactions_data.items():
            manager.transactions[transaction_id] = RecurringTransaction.from_dict(transaction_data)
        
        return manager


def create_recurring_transaction(
    transaction_id: str,
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
) -> RecurringTransaction:
    """
    Create a new recurring transaction.
    
    Args:
        transaction_id: Unique identifier for the recurring transaction.
        recipient: The recipient's address.
        amount: The amount to send.
        interval: The recurrence interval.
        start_date: Optional start date as Unix timestamp.
        end_date: Optional end date as Unix timestamp.
        custom_days: Optional custom interval in days.
        memo: Optional memo to include with the transaction.
        fee: Optional transaction fee.
        enabled: Whether the recurring transaction is enabled.
        max_executions: Optional maximum number of executions.
        
    Returns:
        A new RecurringTransaction object.
    """
    return RecurringTransaction(
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
