# tests/test_performance.py
"""
Performance benchmarks for the PoRW blockchain.

This module contains performance benchmarks for various components
of the PoRW blockchain to ensure they meet performance requirements.
"""

import asyncio
import json
import os
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from src.porw_blockchain.core.structures import Transaction, PoRWBlock
from src.porw_blockchain.core.consensus import validate_transaction, validate_block
from src.porw_blockchain.protein import data_management
from src.porw_blockchain.storage.pors.data import DataManager
from src.porw_blockchain.storage.pors.challenge import Challenge, ChallengeVerifier


# --- Fixtures ---

@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_transaction():
    """Create a sample transaction for benchmarking."""
    return Transaction(
        id="tx1",
        sender="address1",
        receiver="address2",
        amount=10.0,
        signature="valid_signature"
    )


@pytest.fixture
def sample_block():
    """Create a sample block for benchmarking."""
    transactions = [
        Transaction(
            id=f"tx{i}",
            sender=f"address{i}",
            receiver=f"address{i+1}",
            amount=10.0 + i,
            signature=f"signature{i}"
        )
        for i in range(100)  # 100 transactions per block
    ]
    
    return PoRWBlock(
        index=1,
        previous_hash="0" * 64,
        timestamp=time.time(),
        transactions=transactions,
        nonce=12345,
        difficulty=4,
        protein_id="protein1",
        folding_result={
            "energy": -100.5,
            "rmsd": 0.5,
            "score": 95.0
        },
        creator_address="address0"
    )


@pytest.fixture
def sample_amino_sequence():
    """Sample amino acid sequence for benchmarking."""
    # Create a sequence of ~1000 amino acids
    return "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG" * 16


@pytest.fixture
def sample_structure_data():
    """Sample protein structure data for benchmarking."""
    # Create structure data with 1000 atoms
    coordinates = []
    bonds = []
    
    for i in range(1000):
        coordinates.append({
            "x": i * 0.1,
            "y": i * 0.2,
            "z": i * 0.3,
            "element": "C" if i % 5 == 0 else "N" if i % 5 == 1 else "O" if i % 5 == 2 else "H",
            "residue_index": i // 10
        })
        
        if i > 0:
            bonds.append({
                "atom1_index": i - 1,
                "atom2_index": i,
                "bond_type": "single" if i % 3 == 0 else "double" if i % 3 == 1 else "triple"
            })
    
    return {
        "coordinates": coordinates,
        "bonds": bonds
    }


@pytest.fixture
def large_data_sample():
    """Large data sample for storage benchmarks."""
    # Create a 10 MB data sample
    return b"X" * (10 * 1024 * 1024)


# --- Benchmarks ---

def test_transaction_validation_performance(benchmark, sample_transaction):
    """Benchmark transaction validation performance."""
    result = benchmark(validate_transaction, sample_transaction)
    assert result is True


def test_block_validation_performance(benchmark, sample_block):
    """Benchmark block validation performance."""
    # Mock the validate_transaction function to return True
    with patch('src.porw_blockchain.core.consensus.validate_transaction', return_value=True):
        result = benchmark(validate_block, sample_block)
        assert result is True


def test_protein_data_storage_performance(benchmark, temp_data_dir, sample_amino_sequence, sample_structure_data):
    """Benchmark protein data storage performance."""
    metadata = {
        "name": "Test Protein",
        "source": "Test Source",
        "description": "A test protein for benchmarking",
        "tags": ["test", "protein", "benchmark"],
        "created_by": "test_user",
        "creation_date": "2023-01-01T00:00:00Z"
    }
    
    def store_protein():
        return data_management.save_protein_data(
            amino_sequence=sample_amino_sequence,
            structure_data=sample_structure_data,
            metadata=metadata,
            data_dir=temp_data_dir
        )
    
    protein_id = benchmark(store_protein)
    assert protein_id is not None


def test_protein_data_retrieval_performance(benchmark, temp_data_dir, sample_amino_sequence, sample_structure_data):
    """Benchmark protein data retrieval performance."""
    # First, store the protein data
    metadata = {
        "name": "Test Protein",
        "source": "Test Source",
        "description": "A test protein for benchmarking",
        "tags": ["test", "protein", "benchmark"],
        "created_by": "test_user",
        "creation_date": "2023-01-01T00:00:00Z"
    }
    
    protein_id = data_management.save_protein_data(
        amino_sequence=sample_amino_sequence,
        structure_data=sample_structure_data,
        metadata=metadata,
        data_dir=temp_data_dir
    )
    
    def retrieve_protein():
        return data_management.load_protein_data(
            protein_id=protein_id,
            data_dir=temp_data_dir
        )
    
    amino, structure, meta = benchmark(retrieve_protein)
    assert amino == sample_amino_sequence
    assert structure == sample_structure_data


def test_protein_structure_conversion_performance(benchmark, sample_amino_sequence, sample_structure_data):
    """Benchmark protein structure conversion performance."""
    def convert_to_pdb():
        return data_management.structure_to_pdb(sample_amino_sequence, sample_structure_data)
    
    pdb_content = benchmark(convert_to_pdb)
    assert pdb_content is not None
    assert "ATOM" in pdb_content


@pytest.mark.asyncio
async def test_storage_data_chunking_performance(benchmark, temp_data_dir, large_data_sample):
    """Benchmark storage data chunking performance."""
    # Create data manager
    data_manager = DataManager(temp_data_dir, chunk_size=1024 * 1024)  # 1 MB chunks
    await data_manager.initialize()
    
    def store_data():
        # We need to run this in an event loop
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(data_manager.store_data(large_data_sample))
    
    data_id = benchmark(store_data)
    assert data_id is not None
    
    # Clean up
    await data_manager.finalize()


@pytest.mark.asyncio
async def test_challenge_verification_performance(benchmark):
    """Benchmark challenge verification performance."""
    # Create verifier
    verifier = ChallengeVerifier(verification_threshold=0.8)
    
    # Create test data (1 MB)
    test_data = b"X" * (1024 * 1024)
    
    # Create hash challenge
    hash_challenge = Challenge(
        challenge_id="hash_challenge",
        chunk_id="test_chunk",
        challenge_type="hash",
        parameters={},
        timestamp=time.time()
    )
    
    # Create correct hash response
    import hashlib
    correct_hash = hashlib.sha256(test_data).hexdigest()
    correct_response = ChallengeResponse(
        challenge_id="hash_challenge",
        chunk_id="test_chunk",
        proof=correct_hash,
        timestamp=time.time()
    )
    
    def verify_challenge():
        # We need to run this in an event loop
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(verifier.verify_response(hash_challenge, correct_response, test_data))
    
    result = benchmark(verify_challenge)
    assert result is True


def test_message_serialization_performance(benchmark):
    """Benchmark message serialization performance."""
    from src.porw_blockchain.network.message import Message, MessageType
    
    # Create a message with a large payload
    large_payload = {"data": "X" * 10000}  # 10 KB payload
    message = Message(
        msg_type=MessageType.BLOCK,
        payload=large_payload,
        sender="test_sender",
        receiver="test_receiver"
    )
    
    def serialize_message():
        return message.to_json()
    
    json_str = benchmark(serialize_message)
    assert json_str is not None
    assert len(json_str) > 10000


def test_message_deserialization_performance(benchmark):
    """Benchmark message deserialization performance."""
    from src.porw_blockchain.network.message import Message, MessageType
    
    # Create a message with a large payload
    large_payload = {"data": "X" * 10000}  # 10 KB payload
    message = Message(
        msg_type=MessageType.BLOCK,
        payload=large_payload,
        sender="test_sender",
        receiver="test_receiver"
    )
    
    # Serialize the message
    json_str = message.to_json()
    
    def deserialize_message():
        return Message.from_json(json_str)
    
    deserialized = benchmark(deserialize_message)
    assert deserialized is not None
    assert deserialized.msg_type == message.msg_type
    assert deserialized.payload == message.payload


def test_api_serialization_performance(benchmark):
    """Benchmark API serialization performance."""
    # Create a large data structure to serialize
    large_data = {
        "blocks": [
            {
                "index": i,
                "block_hash": f"hash_{i}",
                "previous_hash": f"hash_{i-1}" if i > 0 else "0" * 64,
                "timestamp": time.time(),
                "block_type": "PoRW" if i % 2 == 0 else "PoRS",
                "creator_address": f"address_{i % 5}",
                "transactions": [
                    {
                        "transaction_id": f"tx_{i}_{j}",
                        "sender": f"address_{j}",
                        "recipient": f"address_{j+1}",
                        "amount": 10.0 + j,
                        "fee": 0.1,
                        "timestamp": time.time()
                    }
                    for j in range(10)  # 10 transactions per block
                ]
            }
            for i in range(100)  # 100 blocks
        ]
    }
    
    def serialize_data():
        return json.dumps(large_data)
    
    json_str = benchmark(serialize_data)
    assert json_str is not None
    assert len(json_str) > 10000
