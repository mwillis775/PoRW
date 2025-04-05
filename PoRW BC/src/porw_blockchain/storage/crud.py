# src/porw_blockchain/storage/crud.py
"""
Database CRUD (Create, Read, Update, Delete) operations for blockchain models.
"""

import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc # Import desc for ordering

# Assuming core structures might be used for input data eventually
# from ..core import structures
from . import models


# === Block Operations ===

def create_db_block(
    db: Session,
    index: int,
    timestamp: datetime.datetime,
    proof: int,
    previous_hash: str,
    hash: str,
    # transactions: List[structures.Transaction] # Future: handle transaction data
) -> models.DbBlock:
    """
    Creates and saves a new block record in the database.

    Args:
        db: The SQLAlchemy database session.
        index: The index of the block.
        timestamp: The timestamp of the block creation.
        proof: The proof (nonce) found for the block.
        previous_hash: The hash of the preceding block.
        hash: The calculated hash of this block.
        # transactions: List of transactions included in the block (TBD).

    Returns:
        The newly created DbBlock object.

    Raises:
        SQLAlchemyError: If there is an issue during database interaction.
    """
    # TODO: Handle transaction data persistence when creating blocks.
    # This might involve creating DbTransaction objects and linking them.

    db_block = models.DbBlock(
        index=index,
        timestamp=timestamp,
        proof=proof,
        previous_hash=previous_hash,
        hash=hash,
    )
    try:
        db.add(db_block)
        db.commit()
        db.refresh(db_block) # Refresh to get ID, default values, etc.
        return db_block
    except Exception as e:
        db.rollback() # Rollback in case of error
        # Consider logging the error here
        # logger.error(f"Error creating block in DB: {e}")
        raise # Re-raise the exception


def get_db_block_by_hash(db: Session, block_hash: str) -> Optional[models.DbBlock]:
    """
    Retrieves a block from the database by its hash.

    Args:
        db: The SQLAlchemy database session.
        block_hash: The hash of the block to retrieve.

    Returns:
        The DbBlock object if found, otherwise None.
    """
    return db.query(models.DbBlock).filter(models.DbBlock.hash == block_hash).first()


def get_db_block_by_index(db: Session, index: int) -> Optional[models.DbBlock]:
    """
    Retrieves a block from the database by its index.

    Args:
        db: The SQLAlchemy database session.
        index: The index of the block to retrieve.

    Returns:
        The DbBlock object if found, otherwise None.
    """
    return db.query(models.DbBlock).filter(models.DbBlock.index == index).first()


def get_latest_db_block(db: Session) -> Optional[models.DbBlock]:
    """
    Retrieves the block with the highest index from the database.

    Args:
        db: The SQLAlchemy database session.

    Returns:
        The latest DbBlock object if one exists, otherwise None.
    """
    return db.query(models.DbBlock).order_by(desc(models.DbBlock.index)).first()


# === Transaction Operations ===

# TODO: Add CRUD functions for transactions as needed, e.g.:
# def create_db_transaction(...)
# def get_db_transactions_for_block(...)