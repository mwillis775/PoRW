# tests/test_storage_crud.py
"""
Tests for the database CRUD operations defined in storage.crud.
"""

import pytest
from sqlalchemy.orm import Session
import datetime

# Adjust import paths as needed
from src.porw_blockchain.storage import crud
from src.porw_blockchain.storage import models # To verify instance types

# Note: db_session fixture is automatically imported by pytest from conftest.py


def test_create_db_block(db_session: Session):
    """Test creating a block in the database."""
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    block_data = {
        "index": 0,
        "timestamp": timestamp,
        "proof": 12345,
        "previous_hash": "0" * 64,
        "hash": "a" * 64,
    }
    
    created_block = crud.create_db_block(db=db_session, **block_data)
    
    assert created_block is not None
    assert isinstance(created_block, models.DbBlock)
    assert created_block.id is not None # Should have an ID after commit
    assert created_block.index == block_data["index"]
    assert created_block.timestamp == block_data["timestamp"]
    assert created_block.proof == block_data["proof"]
    assert created_block.previous_hash == block_data["previous_hash"]
    assert created_block.hash == block_data["hash"]


def test_get_db_block_by_hash(db_session: Session):
    """Test retrieving a block by its hash."""
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    block_hash = "b" * 64
    block_data = {
        "index": 1, "timestamp": timestamp, "proof": 54321,
        "previous_hash": "a" * 64, "hash": block_hash
    }
    crud.create_db_block(db=db_session, **block_data) # Create the block first
    
    retrieved_block = crud.get_db_block_by_hash(db=db_session, block_hash=block_hash)
    
    assert retrieved_block is not None
    assert retrieved_block.hash == block_hash
    assert retrieved_block.index == 1


def test_get_db_block_by_hash_not_found(db_session: Session):
    """Test retrieving a non-existent block by hash."""
    retrieved_block = crud.get_db_block_by_hash(db=db_session, block_hash="nonexistent")
    assert retrieved_block is None


def test_get_db_block_by_index(db_session: Session):
    """Test retrieving a block by its index."""
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    block_index = 2
    block_data = {
        "index": block_index, "timestamp": timestamp, "proof": 9876,
        "previous_hash": "b" * 64, "hash": "c" * 64
    }
    crud.create_db_block(db=db_session, **block_data) # Create the block
    
    retrieved_block = crud.get_db_block_by_index(db=db_session, index=block_index)
    
    assert retrieved_block is not None
    assert retrieved_block.index == block_index
    assert retrieved_block.hash == "c" * 64


def test_get_db_block_by_index_not_found(db_session: Session):
    """Test retrieving a non-existent block by index."""
    retrieved_block = crud.get_db_block_by_index(db=db_session, index=999)
    assert retrieved_block is None


def test_get_latest_db_block(db_session: Session):
    """Test retrieving the latest block (highest index)."""
    # Create block 0
    crud.create_db_block(
        db=db_session, index=0, timestamp=datetime.datetime.now(datetime.timezone.utc),
        proof=1, previous_hash="0"*64, hash="a"*64
    )
    # Create block 1 (should be latest)
    ts_latest = datetime.datetime.now(datetime.timezone.utc)
    crud.create_db_block(
        db=db_session, index=1, timestamp=ts_latest,
        proof=2, previous_hash="a"*64, hash="b"*64
    )
    
    latest_block = crud.get_latest_db_block(db=db_session)
    
    assert latest_block is not None
    assert latest_block.index == 1
    assert latest_block.hash == "b" * 64
    assert latest_block.timestamp == ts_latest


def test_get_latest_db_block_empty(db_session: Session):
    """Test retrieving latest block when DB is empty."""
    latest_block = crud.get_latest_db_block(db=db_session)
    assert latest_block is None


def test_create_db_transaction(db_session: Session):
    """Test creating a transaction in the database."""
    transaction_data = {
        "transaction_id": "tx1",
        "sender": "address1",
        "receiver": "address2",
        "amount": 10.0,
        "signature": "valid_signature",
        "block_id": None
    }

    created_transaction = crud.create_db_transaction(db=db_session, **transaction_data)

    assert created_transaction is not None
    assert created_transaction.transaction_id == transaction_data["transaction_id"]
    assert created_transaction.sender == transaction_data["sender"]
    assert created_transaction.receiver == transaction_data["receiver"]
    assert created_transaction.amount == transaction_data["amount"]
    assert created_transaction.signature == transaction_data["signature"]
    assert created_transaction.block_id == transaction_data["block_id"]

def test_get_db_transactions_for_block(db_session: Session):
    """Test retrieving transactions for a specific block."""
    block_id = 1
    transaction_data_1 = {
        "transaction_id": "tx1",
        "sender": "address1",
        "receiver": "address2",
        "amount": 10.0,
        "signature": "valid_signature",
        "block_id": block_id
    }
    transaction_data_2 = {
        "transaction_id": "tx2",
        "sender": "address3",
        "receiver": "address4",
        "amount": 20.0,
        "signature": "valid_signature",
        "block_id": block_id
    }

    crud.create_db_transaction(db=db_session, **transaction_data_1)
    crud.create_db_transaction(db=db_session, **transaction_data_2)

    transactions = crud.get_db_transactions_for_block(db=db_session, block_id=block_id)

    assert len(transactions) == 2
    assert transactions[0].transaction_id == transaction_data_1["transaction_id"]
    assert transactions[1].transaction_id == transaction_data_2["transaction_id"]