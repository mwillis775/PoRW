# src/porw_blockchain/storage/models.py
"""
SQLAlchemy models for representing blockchain data (Blocks, Transactions)
in the database, supporting the hybrid PoRW/PoRS structure.

Uses Single Table Inheritance for the Block model.
"""

import datetime
import enum
from typing import List, Optional, Dict, Any

# Import necessary SQLAlchemy components
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Numeric, JSON
# Use JSONB for PostgreSQL for better performance/indexing if applicable
# from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# --- Base Model ---
class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


# --- Transaction Model ---
class DbTransaction(Base):
    """Database model for a transaction."""
    __tablename__ = "transactions"

    # Core Fields
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="Unique SHA256 hash ID of the transaction")
    sender: Mapped[str] = mapped_column(String(255), index=True, comment="Sender's address")
    recipient: Mapped[str] = mapped_column(String(255), index=True, comment="Recipient's address")
    # Use Numeric for precise currency values, specify precision/scale as needed
    amount: Mapped[Numeric] = mapped_column(Numeric(precision=18, scale=8), comment="Amount transferred")
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), comment="Timestamp of transaction creation")
    signature: Mapped[Optional[str]] = mapped_column(Text, comment="Digital signature of the transaction")

    # Foreign Key to Block (nullable, as tx might be in mempool)
    block_id: Mapped[Optional[int]] = mapped_column(ForeignKey("blocks.id"), index=True, nullable=True, comment="ID of the block containing this transaction (if any)")

    # Relationship back to the block (Many-to-One)
    # Defines the relationship from the Transaction side
    block: Mapped[Optional["DbBlock"]] = relationship(back_populates="transactions") # Use string "DbBlock" to avoid import cycle

    def __repr__(self) -> str:
        return f"<DbTransaction(id={self.id}, tx_id='{self.transaction_id[:8]}...', block_id={self.block_id})>"


# --- Block Model (Single Table Inheritance) ---
class DbBlock(Base):
    """Base database model for all block types (PoRW and PoRS)."""
    __tablename__ = "blocks"

    # --- Common Fields ---
    id: Mapped[int] = mapped_column(primary_key=True)
    block_type: Mapped[str] = mapped_column(String(10), index=True, comment="Discriminator: 'PoRW' or 'PoRS'") # Discriminator column
    index: Mapped[int] = mapped_column(unique=True, index=True, comment="Sequential block index")
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), comment="Timestamp of block creation")
    previous_hash: Mapped[str] = mapped_column(String(64), index=True, comment="Hash of the previous block")
    block_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="Hash of this block")

    # --- PoRW Specific Fields (Nullable) ---
    porw_proof: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, comment="Proof data for PoRW blocks (JSON)")
    minted_amount: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=18, scale=8), nullable=True, comment="Currency minted in PoRW blocks")
    protein_data_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True, comment="Reference to protein data for PoRW blocks")

    # --- PoRS Specific Fields (Nullable) ---
    pors_proof: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, comment="Proof data for PoRS blocks (JSON)")
    storage_rewards: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, comment="Storage rewards distribution in PoRS blocks (JSON)")

    # --- Relationship to Transactions (One-to-Many) ---
    # This relationship applies primarily to PoRS blocks, but the relationship definition is on the base class.
    # PoRW blocks will typically have an empty list here.
    transactions: Mapped[List["DbTransaction"]] = relationship(
        back_populates="block", # Link back from DbTransaction.block
        cascade="all, delete-orphan", # Delete transactions if block is deleted
        lazy="selectin" # Use selectin loading for potentially better performance fetching blocks+txs
    )

    # --- Polymorphism Configuration ---
    __mapper_args__ = {
        "polymorphic_identity": "block", # Identity for the base class
        "polymorphic_on": "block_type",  # Column used to determine the subclass
    }

    def __repr__(self) -> str:
        return f"<DbBlock(id={self.id}, type='{self.block_type}', index={self.index}, hash='{self.block_hash[:8]}...')>"


# --- Subclasses for Polymorphism ---
# These don't define new columns but allow querying specifically for PoRW/PoRS blocks

class DbPoRWBlock(DbBlock):
    """Represents a PoRW block row in the 'blocks' table."""
    __mapper_args__ = {
        "polymorphic_identity": "PoRW", # Value in 'block_type' for PoRW rows
    }
    def __repr__(self) -> str:
        return f"<DbPoRWBlock(id={self.id}, index={self.index}, hash='{self.block_hash[:8]}...')>"


class DbPoRSBlock(DbBlock):
    """Represents a PoRS block row in the 'blocks' table."""
    __mapper_args__ = {
        "polymorphic_identity": "PoRS", # Value in 'block_type' for PoRS rows
    }
    def __repr__(self) -> str:
        return f"<DbPoRSBlock(id={self.id}, index={self.index}, hash='{self.block_hash[:8]}...')>"

