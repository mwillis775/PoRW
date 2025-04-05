# src/porw_blockchain/rpc/schemas.py
"""
Pydantic schemas for API request and response data validation.

These schemas define the expected structure for data exchanged via the API,
ensuring consistency and providing clear API contracts. They may initially
mirror core data structures but can evolve independently.
"""

import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# Import core structures to potentially reuse or reference fields
# Note: We inherit directly for simplicity now, but could define fields
# explicitly if API structure needs to differ from core structure.
from ...core.structures import Block as CoreBlock
from ...core.structures import Transaction as CoreTransaction


# --- Transaction Schemas ---

class TransactionResponse(CoreTransaction):
    """
    Schema for representing a transaction in API responses.
    Inherits fields from core.structures.Transaction.
    """
    # Example of adding an API-specific field or overriding one later:
    # confirmation_status: Optional[str] = None

    class Config:
        # Example for OpenAPI documentation
        json_schema_extra = {
            "example": {
                "sender": "address1...",
                "recipient": "address2...",
                "amount": 10.5,
                "timestamp": "2025-04-05T18:42:00Z",
                "signature": "signature_string...",
            }
        }


# --- Block Schemas ---

class BlockResponse(CoreBlock):
    """
    Schema for representing a block in API responses.
    Inherits fields from core.structures.Block.
    Includes nested TransactionResponse objects.

    (Overriding transactions field to use TransactionResponse schema)
    """
    # Override the transactions field to use the API-specific response schema
    transactions: List[TransactionResponse]

    class Config:
        # Example for OpenAPI documentation
        json_schema_extra = {
            "example": {
                "index": 1,
                "timestamp": "2025-04-05T18:40:00Z",
                "transactions": [
                    {
                        "sender": "address1...",
                        "recipient": "address2...",
                        "amount": 10.5,
                        "timestamp": "2025-04-05T18:39:00Z",
                        "signature": "signature_string...",
                    }
                ],
                "proof": 12345,
                "previous_hash": "a" * 64,
                "hash": "b" * 64,
            }
        }


# --- Generic Schemas ---

class StatusResponse(BaseModel):
    """Simple schema for status responses."""
    status: str

    class Config:
        json_schema_extra = {
            "example": {"status": "ok"}
        }

# --- Schemas for Request Bodies (Placeholders for future use) ---

# Example: Schema for submitting a new transaction via API
# class TransactionCreate(BaseModel):
#     sender: str
#     recipient: str
#     amount: float
#     # Signature might be added separately or included here
#     pass