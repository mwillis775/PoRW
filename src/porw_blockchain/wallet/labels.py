"""
Transaction labeling and categorization functionality for the PoRW blockchain wallet.

This module provides classes and functions for labeling and categorizing transactions,
allowing users to organize and track their transaction history.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Set, Union

# Configure logger
logger = logging.getLogger(__name__)


class TransactionLabel:
    """
    Represents a label for a transaction.
    
    A transaction label contains information about a transaction, including
    its label, category, notes, and tags.
    """
    
    def __init__(
        self,
        transaction_id: str,
        label: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_at: Optional[int] = None,
        updated_at: Optional[int] = None
    ):
        """
        Initialize a transaction label.
        
        Args:
            transaction_id: The ID of the transaction.
            label: Optional label for the transaction.
            category: Optional category for the transaction.
            notes: Optional notes for the transaction.
            tags: Optional list of tags for the transaction.
            created_at: Optional creation timestamp (default: current time).
            updated_at: Optional update timestamp (default: current time).
        """
        self.transaction_id = transaction_id
        self.label = label
        self.category = category
        self.notes = notes
        self.tags = tags or []
        self.created_at = created_at or int(time.time())
        self.updated_at = updated_at or int(time.time())
        
        logger.debug(f"Created transaction label for {transaction_id}")
    
    def update(
        self,
        label: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> None:
        """
        Update the transaction label.
        
        Args:
            label: Optional new label.
            category: Optional new category.
            notes: Optional new notes.
            tags: Optional new tags.
        """
        if label is not None:  # Allow empty string to clear label
            self.label = label
        
        if category is not None:  # Allow empty string to clear category
            self.category = category
        
        if notes is not None:  # Allow empty string to clear notes
            self.notes = notes
        
        if tags is not None:  # Allow empty list to clear tags
            self.tags = tags
        
        self.updated_at = int(time.time())
        
        logger.debug(f"Updated transaction label for {self.transaction_id}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the transaction label to a dictionary.
        
        Returns:
            A dictionary representation of the transaction label.
        """
        return {
            "transaction_id": self.transaction_id,
            "label": self.label,
            "category": self.category,
            "notes": self.notes,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionLabel':
        """
        Create a transaction label from a dictionary.
        
        Args:
            data: A dictionary representation of the transaction label.
            
        Returns:
            A TransactionLabel object.
        """
        return cls(
            transaction_id=data["transaction_id"],
            label=data.get("label"),
            category=data.get("category"),
            notes=data.get("notes"),
            tags=data.get("tags"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


class TransactionLabelManager:
    """
    Manages transaction labels.
    
    The transaction label manager provides functionality for adding, updating, removing,
    and searching transaction labels.
    """
    
    def __init__(self):
        """
        Initialize a transaction label manager.
        """
        self.labels: Dict[str, TransactionLabel] = {}  # transaction_id -> TransactionLabel
        self.categories: Set[str] = set()  # Set of all categories
        
        logger.debug("Initialized TransactionLabelManager")
    
    def add_label(
        self,
        transaction_id: str,
        label: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> TransactionLabel:
        """
        Add a label to a transaction.
        
        Args:
            transaction_id: The ID of the transaction.
            label: Optional label for the transaction.
            category: Optional category for the transaction.
            notes: Optional notes for the transaction.
            tags: Optional list of tags for the transaction.
            
        Returns:
            The added transaction label.
        """
        # Create transaction label
        transaction_label = TransactionLabel(
            transaction_id=transaction_id,
            label=label,
            category=category,
            notes=notes,
            tags=tags
        )
        
        # Add to labels
        self.labels[transaction_id] = transaction_label
        
        # Add category to categories
        if category:
            self.categories.add(category)
        
        logger.debug(f"Added label to transaction {transaction_id}")
        return transaction_label
    
    def update_label(
        self,
        transaction_id: str,
        label: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> TransactionLabel:
        """
        Update a transaction label.
        
        Args:
            transaction_id: The ID of the transaction.
            label: Optional new label.
            category: Optional new category.
            notes: Optional new notes.
            tags: Optional new tags.
            
        Returns:
            The updated transaction label.
            
        Raises:
            ValueError: If the transaction label is not found.
        """
        if transaction_id not in self.labels:
            raise ValueError(f"Transaction label for {transaction_id} not found")
        
        # Get transaction label
        transaction_label = self.labels[transaction_id]
        
        # Update transaction label
        transaction_label.update(
            label=label,
            category=category,
            notes=notes,
            tags=tags
        )
        
        # Update categories
        if category:
            self.categories.add(category)
        
        logger.debug(f"Updated label for transaction {transaction_id}")
        return transaction_label
    
    def remove_label(self, transaction_id: str) -> None:
        """
        Remove a transaction label.
        
        Args:
            transaction_id: The ID of the transaction.
            
        Raises:
            ValueError: If the transaction label is not found.
        """
        if transaction_id not in self.labels:
            raise ValueError(f"Transaction label for {transaction_id} not found")
        
        # Remove from labels
        self.labels.pop(transaction_id)
        
        # Update categories
        self._update_categories()
        
        logger.debug(f"Removed label for transaction {transaction_id}")
    
    def get_label(self, transaction_id: str) -> Optional[TransactionLabel]:
        """
        Get a transaction label.
        
        Args:
            transaction_id: The ID of the transaction.
            
        Returns:
            The transaction label, or None if not found.
        """
        return self.labels.get(transaction_id)
    
    def search_labels(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[TransactionLabel]:
        """
        Search for transaction labels.
        
        Args:
            query: Optional search query for label, notes, or transaction ID.
            category: Optional category to filter by.
            tags: Optional list of tags to filter by.
            
        Returns:
            A list of matching transaction labels.
        """
        results = []
        
        for label in self.labels.values():
            # If no query, category, or tags, include all labels
            if not query and not category and not tags:
                results.append(label)
                continue
            
            # Check if label matches query
            if query:
                query_lower = query.lower()
                if (
                    (label.label and query_lower in label.label.lower()) or
                    (label.notes and query_lower in label.notes.lower()) or
                    query_lower in label.transaction_id.lower()
                ):
                    # If no category or tags filter, add to results
                    if not category and not tags:
                        results.append(label)
                        continue
            
            # Check if label matches category
            if category:
                if label.category == category:
                    # If no query or tags filter, or query matches, add to results
                    if (not query or (query and (
                        (label.label and query_lower in label.label.lower()) or
                        (label.notes and query_lower in label.notes.lower()) or
                        query_lower in label.transaction_id.lower()
                    ))) and not tags:
                        results.append(label)
                        continue
            
            # Check if label has all required tags
            if tags:
                if all(tag in label.tags for tag in tags):
                    # If no query or category filter, or they match, add to results
                    if (not query or (query and (
                        (label.label and query_lower in label.label.lower()) or
                        (label.notes and query_lower in label.notes.lower()) or
                        query_lower in label.transaction_id.lower()
                    ))) and (not category or label.category == category):
                        results.append(label)
        
        return results
    
    def list_labels(self) -> List[TransactionLabel]:
        """
        List all transaction labels.
        
        Returns:
            A list of all transaction labels.
        """
        return list(self.labels.values())
    
    def get_labels_by_category(self, category: str) -> List[TransactionLabel]:
        """
        Get transaction labels by category.
        
        Args:
            category: The category to filter by.
            
        Returns:
            A list of transaction labels with the given category.
        """
        return [label for label in self.labels.values() if label.category == category]
    
    def get_labels_by_tag(self, tag: str) -> List[TransactionLabel]:
        """
        Get transaction labels by tag.
        
        Args:
            tag: The tag to filter by.
            
        Returns:
            A list of transaction labels with the given tag.
        """
        return [label for label in self.labels.values() if tag in label.tags]
    
    def get_all_categories(self) -> List[str]:
        """
        Get all categories.
        
        Returns:
            A list of all categories.
        """
        return sorted(list(self.categories))
    
    def get_all_tags(self) -> List[str]:
        """
        Get all tags.
        
        Returns:
            A list of all tags.
        """
        tags = set()
        for label in self.labels.values():
            tags.update(label.tags)
        return sorted(list(tags))
    
    def _update_categories(self) -> None:
        """
        Update the set of categories based on the current labels.
        """
        self.categories = {label.category for label in self.labels.values() if label.category}
    
    def add_tag_to_label(self, transaction_id: str, tag: str) -> TransactionLabel:
        """
        Add a tag to a transaction label.
        
        Args:
            transaction_id: The ID of the transaction.
            tag: The tag to add.
            
        Returns:
            The updated transaction label.
            
        Raises:
            ValueError: If the transaction label is not found.
        """
        if transaction_id not in self.labels:
            raise ValueError(f"Transaction label for {transaction_id} not found")
        
        # Get transaction label
        transaction_label = self.labels[transaction_id]
        
        # Add tag if not already present
        if tag not in transaction_label.tags:
            transaction_label.tags.append(tag)
            transaction_label.updated_at = int(time.time())
        
        logger.debug(f"Added tag '{tag}' to transaction {transaction_id}")
        return transaction_label
    
    def remove_tag_from_label(self, transaction_id: str, tag: str) -> TransactionLabel:
        """
        Remove a tag from a transaction label.
        
        Args:
            transaction_id: The ID of the transaction.
            tag: The tag to remove.
            
        Returns:
            The updated transaction label.
            
        Raises:
            ValueError: If the transaction label is not found.
        """
        if transaction_id not in self.labels:
            raise ValueError(f"Transaction label for {transaction_id} not found")
        
        # Get transaction label
        transaction_label = self.labels[transaction_id]
        
        # Remove tag if present
        if tag in transaction_label.tags:
            transaction_label.tags.remove(tag)
            transaction_label.updated_at = int(time.time())
        
        logger.debug(f"Removed tag '{tag}' from transaction {transaction_id}")
        return transaction_label
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the transaction label manager to a dictionary.
        
        Returns:
            A dictionary representation of the transaction label manager.
        """
        return {
            "labels": {
                transaction_id: label.to_dict()
                for transaction_id, label in self.labels.items()
            },
            "categories": list(self.categories)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionLabelManager':
        """
        Create a transaction label manager from a dictionary.
        
        Args:
            data: A dictionary representation of the transaction label manager.
            
        Returns:
            A TransactionLabelManager object.
        """
        manager = cls()
        
        # Load labels
        labels_data = data.get("labels", {})
        for transaction_id, label_data in labels_data.items():
            manager.labels[transaction_id] = TransactionLabel.from_dict(label_data)
        
        # Load categories
        manager.categories = set(data.get("categories", []))
        
        return manager


def create_transaction_label(
    transaction_id: str,
    label: Optional[str] = None,
    category: Optional[str] = None,
    notes: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> TransactionLabel:
    """
    Create a new transaction label.
    
    Args:
        transaction_id: The ID of the transaction.
        label: Optional label for the transaction.
        category: Optional category for the transaction.
        notes: Optional notes for the transaction.
        tags: Optional list of tags for the transaction.
        
    Returns:
        A new TransactionLabel object.
    """
    return TransactionLabel(
        transaction_id=transaction_id,
        label=label,
        category=category,
        notes=notes,
        tags=tags
    )
