# src/porw_blockchain/storage/models.py
"""SQLAlchemy models for representing blockchain data in the database."""

import datetime
from typing import List # Note: Storing complex types like lists might require JSON/serialization

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


class DbBlock(Base):
    """Database model for a block."""

    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    index: Mapped[int] = mapped_column(unique=True, index=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    proof: Mapped[int]
    previous_hash: Mapped[str] = mapped_column(String(64), index=True) # Assuming SHA-256 hash length
    hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Relationship to transactions (One-to-Many)
    # Note: This assumes transactions are stored separately and linked.
    # Storing JSON might be simpler initially if transactions aren't queried individually.
    transactions: Mapped[List["DbTransaction"]] = relationship(
        back_populates="block", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DbBlock(index={self.index}, hash='{self.hash[:8]}...')>"


class DbTransaction(Base):
    """Database model for a transaction."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int] = mapped_column(ForeignKey("blocks.id"), index=True)
    sender: Mapped[str] = mapped_column(String(255)) # Adjust length as needed
    recipient: Mapped[str] = mapped_column(String(255)) # Adjust length as needed
    amount: Mapped[float] = mapped_column(Float) # Consider Numeric/Decimal for precision
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    signature: Mapped[str] = mapped_column(Text, nullable=True) # Signature might be long

    # Relationship back to the block (Many-to-One)
    block: Mapped[DbBlock] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return f"<DbTransaction(id={self.id}, block_id={self.block_id})>"