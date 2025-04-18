"""
Privacy features for the PoRW blockchain.

This package provides privacy-enhancing technologies for the PoRW blockchain,
including encrypted memos, confidential transactions, stealth addresses,
zero-knowledge proofs, and mixing services.
"""

from .encrypted_memo import encrypt_memo, decrypt_memo, is_encrypted_memo
from .confidential_transactions import (
    create_confidential_transaction,
    verify_confidential_transaction,
    create_pedersen_commitment,
    verify_pedersen_commitment,
    create_range_proof,
    verify_range_proof,
    generate_blinding_factor
)
from .zkp import (
    SchnorrProof,
    BulletproofRangeProof,
    ZKSnarkProof,
    create_schnorr_proof,
    create_range_proof as create_zkp_range_proof,
    create_zksnark_proof,
    verify_proof
)
from .zkp_applications import (
    create_confidential_transaction_with_zkp,
    verify_confidential_transaction_with_zkp,
    create_identity_proof,
    verify_identity_proof,
    create_private_contract_proof,
    verify_private_contract_proof,
    create_protein_folding_proof,
    verify_protein_folding_proof
)
from .stealth_address import (
    StealthMetadata,
    StealthKeys,
    generate_stealth_address,
    create_stealth_payment_address,
    scan_for_stealth_payments,
    recover_stealth_payment_private_key,
    generate_stealth_keys,
    create_stealth_wallet
)
from .mixing import (
    MixingSession,
    MixingCoordinator,
    MixingParticipant,
    get_mixing_coordinator,
    start_mixing_coordinator,
    stop_mixing_coordinator
)

__all__ = [
    # Encrypted memo functions
    'encrypt_memo',
    'decrypt_memo',
    'is_encrypted_memo',

    # Confidential transaction functions
    'create_confidential_transaction',
    'verify_confidential_transaction',
    'create_pedersen_commitment',
    'verify_pedersen_commitment',
    'create_range_proof',
    'verify_range_proof',
    'generate_blinding_factor',

    # Zero-knowledge proof classes
    'SchnorrProof',
    'BulletproofRangeProof',
    'ZKSnarkProof',

    # Zero-knowledge proof functions
    'create_schnorr_proof',
    'create_zkp_range_proof',
    'create_zksnark_proof',
    'verify_proof',

    # Zero-knowledge proof applications
    'create_confidential_transaction_with_zkp',
    'verify_confidential_transaction_with_zkp',
    'create_identity_proof',
    'verify_identity_proof',
    'create_private_contract_proof',
    'verify_private_contract_proof',
    'create_protein_folding_proof',
    'verify_protein_folding_proof',

    # Stealth address classes
    'StealthMetadata',
    'StealthKeys',

    # Stealth address functions
    'generate_stealth_address',
    'create_stealth_payment_address',
    'scan_for_stealth_payments',
    'recover_stealth_payment_private_key',
    'generate_stealth_keys',
    'create_stealth_wallet',

    # Mixing classes
    'MixingSession',
    'MixingCoordinator',
    'MixingParticipant',

    # Mixing functions
    'get_mixing_coordinator',
    'start_mixing_coordinator',
    'stop_mixing_coordinator',
]
