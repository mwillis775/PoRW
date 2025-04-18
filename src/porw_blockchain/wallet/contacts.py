"""
Contact management functionality for the PoRW blockchain wallet.

This module provides classes and functions for managing contacts and address book
entries, allowing users to save and organize addresses with names and additional
information.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Union

from ..core.crypto_utils import is_valid_address

# Configure logger
logger = logging.getLogger(__name__)


class Contact:
    """
    Represents a contact in the address book.
    
    A contact contains information about a person or entity, including
    their name, address, and optional additional information.
    """
    
    def __init__(
        self,
        name: str,
        address: str,
        contact_id: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_at: Optional[int] = None,
        updated_at: Optional[int] = None
    ):
        """
        Initialize a contact.
        
        Args:
            name: The name of the contact.
            address: The blockchain address of the contact.
            contact_id: Unique identifier for the contact (default: generated).
            email: Optional email address.
            phone: Optional phone number.
            description: Optional description.
            tags: Optional list of tags for categorization.
            created_at: Optional creation timestamp (default: current time).
            updated_at: Optional update timestamp (default: current time).
            
        Raises:
            ValueError: If the address is invalid.
        """
        if not is_valid_address(address):
            raise ValueError(f"Invalid address: {address}")
        
        self.name = name
        self.address = address
        self.contact_id = contact_id or self._generate_contact_id()
        self.email = email
        self.phone = phone
        self.description = description
        self.tags = tags or []
        self.created_at = created_at or int(time.time())
        self.updated_at = updated_at or int(time.time())
        
        logger.debug(f"Created contact: {self.name} ({self.address})")
    
    def _generate_contact_id(self) -> str:
        """
        Generate a unique contact ID.
        
        Returns:
            A unique contact ID.
        """
        import uuid
        return f"contact_{uuid.uuid4().hex[:8]}"
    
    def update(
        self,
        name: Optional[str] = None,
        address: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> None:
        """
        Update the contact information.
        
        Args:
            name: Optional new name.
            address: Optional new address.
            email: Optional new email.
            phone: Optional new phone.
            description: Optional new description.
            tags: Optional new tags.
            
        Raises:
            ValueError: If the address is invalid.
        """
        if address and not is_valid_address(address):
            raise ValueError(f"Invalid address: {address}")
        
        if name:
            self.name = name
        
        if address:
            self.address = address
        
        if email is not None:  # Allow empty string to clear email
            self.email = email
        
        if phone is not None:  # Allow empty string to clear phone
            self.phone = phone
        
        if description is not None:  # Allow empty string to clear description
            self.description = description
        
        if tags is not None:  # Allow empty list to clear tags
            self.tags = tags
        
        self.updated_at = int(time.time())
        
        logger.debug(f"Updated contact: {self.name} ({self.address})")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the contact to a dictionary.
        
        Returns:
            A dictionary representation of the contact.
        """
        return {
            "contact_id": self.contact_id,
            "name": self.name,
            "address": self.address,
            "email": self.email,
            "phone": self.phone,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Contact':
        """
        Create a contact from a dictionary.
        
        Args:
            data: A dictionary representation of the contact.
            
        Returns:
            A Contact object.
        """
        return cls(
            name=data["name"],
            address=data["address"],
            contact_id=data.get("contact_id"),
            email=data.get("email"),
            phone=data.get("phone"),
            description=data.get("description"),
            tags=data.get("tags"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


class AddressBook:
    """
    Manages a collection of contacts.
    
    The address book provides functionality for adding, updating, removing,
    and searching contacts.
    """
    
    def __init__(self):
        """
        Initialize an address book.
        """
        self.contacts: Dict[str, Contact] = {}  # contact_id -> Contact
        self.address_index: Dict[str, str] = {}  # address -> contact_id
        
        logger.debug("Initialized AddressBook")
    
    def add_contact(self, contact: Contact) -> Contact:
        """
        Add a contact to the address book.
        
        Args:
            contact: The contact to add.
            
        Returns:
            The added contact.
            
        Raises:
            ValueError: If a contact with the same ID already exists.
        """
        if contact.contact_id in self.contacts:
            raise ValueError(f"Contact with ID {contact.contact_id} already exists")
        
        self.contacts[contact.contact_id] = contact
        self.address_index[contact.address] = contact.contact_id
        
        logger.debug(f"Added contact to address book: {contact.name} ({contact.address})")
        return contact
    
    def update_contact(
        self,
        contact_id: str,
        name: Optional[str] = None,
        address: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Contact:
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
            The updated contact.
            
        Raises:
            ValueError: If the contact is not found or the address is invalid.
        """
        if contact_id not in self.contacts:
            raise ValueError(f"Contact with ID {contact_id} not found")
        
        contact = self.contacts[contact_id]
        
        # If address is changing, update the address index
        if address and address != contact.address:
            # Remove old address from index
            self.address_index.pop(contact.address, None)
            
            # Add new address to index
            self.address_index[address] = contact_id
        
        # Update the contact
        contact.update(
            name=name,
            address=address,
            email=email,
            phone=phone,
            description=description,
            tags=tags
        )
        
        logger.debug(f"Updated contact in address book: {contact.name} ({contact.address})")
        return contact
    
    def remove_contact(self, contact_id: str) -> None:
        """
        Remove a contact from the address book.
        
        Args:
            contact_id: The ID of the contact to remove.
            
        Raises:
            ValueError: If the contact is not found.
        """
        if contact_id not in self.contacts:
            raise ValueError(f"Contact with ID {contact_id} not found")
        
        contact = self.contacts[contact_id]
        
        # Remove from address index
        self.address_index.pop(contact.address, None)
        
        # Remove from contacts
        self.contacts.pop(contact_id)
        
        logger.debug(f"Removed contact from address book: {contact.name} ({contact.address})")
    
    def get_contact(self, contact_id: str) -> Contact:
        """
        Get a contact by ID.
        
        Args:
            contact_id: The ID of the contact to get.
            
        Returns:
            The contact.
            
        Raises:
            ValueError: If the contact is not found.
        """
        if contact_id not in self.contacts:
            raise ValueError(f"Contact with ID {contact_id} not found")
        
        return self.contacts[contact_id]
    
    def get_contact_by_address(self, address: str) -> Optional[Contact]:
        """
        Get a contact by address.
        
        Args:
            address: The address to look up.
            
        Returns:
            The contact, or None if not found.
        """
        contact_id = self.address_index.get(address)
        if not contact_id:
            return None
        
        return self.contacts.get(contact_id)
    
    def get_contact_by_name(self, name: str) -> Optional[Contact]:
        """
        Get a contact by name.
        
        Args:
            name: The name to look up.
            
        Returns:
            The first contact with the given name, or None if not found.
        """
        for contact in self.contacts.values():
            if contact.name.lower() == name.lower():
                return contact
        
        return None
    
    def search_contacts(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Contact]:
        """
        Search for contacts.
        
        Args:
            query: Optional search query for name, address, email, or description.
            tags: Optional list of tags to filter by.
            
        Returns:
            A list of matching contacts.
        """
        results = []
        
        for contact in self.contacts.values():
            # If no query or tags, include all contacts
            if not query and not tags:
                results.append(contact)
                continue
            
            # Check if contact matches query
            if query:
                query_lower = query.lower()
                if (
                    query_lower in contact.name.lower() or
                    query_lower in contact.address.lower() or
                    (contact.email and query_lower in contact.email.lower()) or
                    (contact.description and query_lower in contact.description.lower())
                ):
                    # If no tags filter, add to results
                    if not tags:
                        results.append(contact)
                        continue
            
            # Check if contact has all required tags
            if tags:
                if all(tag in contact.tags for tag in tags):
                    # If no query or query matches, add to results
                    if not query or query_lower in contact.name.lower():
                        results.append(contact)
        
        return results
    
    def list_contacts(self) -> List[Contact]:
        """
        List all contacts in the address book.
        
        Returns:
            A list of all contacts.
        """
        return list(self.contacts.values())
    
    def get_contacts_by_tag(self, tag: str) -> List[Contact]:
        """
        Get contacts by tag.
        
        Args:
            tag: The tag to filter by.
            
        Returns:
            A list of contacts with the given tag.
        """
        return [contact for contact in self.contacts.values() if tag in contact.tags]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the address book to a dictionary.
        
        Returns:
            A dictionary representation of the address book.
        """
        return {
            "contacts": {
                contact_id: contact.to_dict()
                for contact_id, contact in self.contacts.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AddressBook':
        """
        Create an address book from a dictionary.
        
        Args:
            data: A dictionary representation of the address book.
            
        Returns:
            An AddressBook object.
        """
        address_book = cls()
        
        contacts_data = data.get("contacts", {})
        for contact_id, contact_data in contacts_data.items():
            contact = Contact.from_dict(contact_data)
            address_book.contacts[contact_id] = contact
            address_book.address_index[contact.address] = contact_id
        
        return address_book


def create_contact(
    name: str,
    address: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> Contact:
    """
    Create a new contact.
    
    Args:
        name: The name of the contact.
        address: The blockchain address of the contact.
        email: Optional email address.
        phone: Optional phone number.
        description: Optional description.
        tags: Optional list of tags for categorization.
        
    Returns:
        A new Contact object.
        
    Raises:
        ValueError: If the address is invalid.
    """
    return Contact(
        name=name,
        address=address,
        email=email,
        phone=phone,
        description=description,
        tags=tags
    )
