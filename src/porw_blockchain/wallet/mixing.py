"""
Mixing wallet functionality for the PoRW blockchain.

This module provides a wallet extension for participating in mixing sessions,
which enhance privacy by breaking the transaction graph.
"""

import os
import uuid
import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime

from ..core.structures import Transaction
from ..core.crypto_utils import (
    load_private_key_from_pem,
    load_public_key_from_pem,
    serialize_private_key,
    serialize_public_key,
    is_valid_address
)
from ..privacy.mixing import (
    MixingParticipant,
    get_mixing_coordinator,
    DEFAULT_DENOMINATION,
    DEFAULT_MIXING_FEE_PERCENT
)

# Configure logger
logger = logging.getLogger(__name__)


class MixingWallet:
    """
    Wallet extension for mixing functionality.
    
    This class provides methods for participating in mixing sessions
    to enhance privacy.
    """
    
    def __init__(self, private_key: str, address: str):
        """
        Initialize the mixing wallet.
        
        Args:
            private_key: The wallet's private key.
            address: The wallet's address.
        """
        self.private_key = private_key
        self.address = address
        self.participants = {}  # {participant_id: MixingParticipant}
        self.sessions = {}  # {session_id: {participant_id, status, ...}}
        self.output_addresses = set()  # Set of output addresses used in mixing
        
        logger.info(f"Initialized mixing wallet for {address}")
    
    async def create_mixing_session(
        self,
        denomination: float = DEFAULT_DENOMINATION,
        min_participants: int = 3,
        max_participants: int = 20,
        fee_percent: float = DEFAULT_MIXING_FEE_PERCENT
    ) -> Dict[str, Any]:
        """
        Create a new mixing session.
        
        Args:
            denomination: The amount each participant will mix.
            min_participants: Minimum number of participants required.
            max_participants: Maximum number of participants allowed.
            fee_percent: Fee percentage for the mixing service.
            
        Returns:
            The created mixing session data.
        """
        # Get mixing coordinator
        coordinator = get_mixing_coordinator()
        
        # Create session
        session = coordinator.create_session(
            denomination=denomination,
            min_participants=min_participants,
            max_participants=max_participants,
            fee_percent=fee_percent
        )
        
        # Store session
        self.sessions[session.session_id] = {
            "session_id": session.session_id,
            "denomination": denomination,
            "min_participants": min_participants,
            "max_participants": max_participants,
            "fee_percent": fee_percent,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "participants": []
        }
        
        logger.info(f"Created mixing session {session.session_id}")
        return session.to_dict()
    
    async def join_mixing_session(
        self,
        session_id: str,
        output_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Join an existing mixing session.
        
        Args:
            session_id: The ID of the session to join.
            output_address: Optional output address (default: generate new).
            
        Returns:
            The participant data.
            
        Raises:
            ValueError: If the session is not found or cannot be joined.
        """
        # Get mixing coordinator
        coordinator = get_mixing_coordinator()
        
        # Get session
        session = coordinator.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Check if session can be joined
        if session.status != "created" and session.status != "registration":
            raise ValueError(f"Cannot join session {session_id}: session is in {session.status} state")
        
        # Generate output address if not provided
        if not output_address:
            # In a real implementation, this would generate a new address
            # For demonstration, we'll use a random UUID
            output_address = f"mix_{uuid.uuid4().hex}"
        
        # Check if output address is already used
        if output_address in self.output_addresses:
            raise ValueError(f"Output address {output_address} is already used in another mixing session")
        
        # Create participant
        participant = MixingParticipant(
            private_key=self.private_key,
            input_address=self.address,
            output_address=output_address
        )
        
        # Create blinded output
        coordinator_public_key_pem = serialize_public_key(session.coordinator_public_key)
        blinded_output = participant.create_blinded_output(coordinator_public_key_pem)
        
        # Create proof of funds
        proof_of_funds = participant.create_proof_of_funds()
        
        # Register participant
        success = session.register_participant(
            participant_id=participant.participant_id,
            input_address=self.address,
            output_address=output_address,
            blinded_output=blinded_output,
            proof_of_funds=proof_of_funds
        )
        
        if not success:
            raise ValueError(f"Failed to register participant in session {session_id}")
        
        # Store participant
        self.participants[participant.participant_id] = participant
        participant.session_id = session_id
        
        # Add output address to used set
        self.output_addresses.add(output_address)
        
        # Update session data
        if session_id in self.sessions:
            self.sessions[session_id]["participants"].append(participant.participant_id)
            self.sessions[session_id]["status"] = session.status
        else:
            self.sessions[session_id] = {
                "session_id": session_id,
                "denomination": session.denomination,
                "min_participants": session.min_participants,
                "max_participants": session.max_participants,
                "fee_percent": session.fee_percent,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "participants": [participant.participant_id]
            }
        
        logger.info(f"Joined mixing session {session_id} as participant {participant.participant_id}")
        
        # Return participant data
        return {
            "participant_id": participant.participant_id,
            "session_id": session_id,
            "input_address": self.address,
            "output_address": output_address,
            "status": "registered"
        }
    
    async def get_blind_signature(
        self,
        session_id: str,
        participant_id: str
    ) -> Dict[str, Any]:
        """
        Get a blind signature from the mixing coordinator.
        
        Args:
            session_id: The session ID.
            participant_id: The participant ID.
            
        Returns:
            The blind signature data.
            
        Raises:
            ValueError: If the session or participant is not found.
        """
        # Get mixing coordinator
        coordinator = get_mixing_coordinator()
        
        # Get session
        session = coordinator.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Check if participant exists
        if participant_id not in self.participants:
            raise ValueError(f"Participant {participant_id} not found")
        
        # Get participant
        participant = self.participants[participant_id]
        
        # Check if participant is in the right session
        if participant.session_id != session_id:
            raise ValueError(f"Participant {participant_id} is not in session {session_id}")
        
        # Get blind signature
        blind_signature = session.create_blind_signature(participant_id)
        
        # Unblind signature
        unblinded_signature = participant.unblind_signature(blind_signature)
        
        # Verify unblinded signature
        coordinator_public_key_pem = serialize_public_key(session.coordinator_public_key)
        is_valid = participant.verify_unblinded_signature(coordinator_public_key_pem)
        
        if not is_valid:
            raise ValueError(f"Invalid unblinded signature for participant {participant_id}")
        
        # Update session data
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = session.status
        
        logger.info(f"Got blind signature for participant {participant_id} in session {session_id}")
        
        # Return signature data
        return {
            "participant_id": participant_id,
            "session_id": session_id,
            "blind_signature": blind_signature.hex(),
            "unblinded_signature": unblinded_signature.hex(),
            "is_valid": is_valid
        }
    
    async def sign_coinjoin_transaction(
        self,
        session_id: str,
        participant_id: str
    ) -> Dict[str, Any]:
        """
        Sign a CoinJoin transaction.
        
        Args:
            session_id: The session ID.
            participant_id: The participant ID.
            
        Returns:
            The signature data.
            
        Raises:
            ValueError: If the session or participant is not found.
        """
        # Get mixing coordinator
        coordinator = get_mixing_coordinator()
        
        # Get session
        session = coordinator.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Check if participant exists
        if participant_id not in self.participants:
            raise ValueError(f"Participant {participant_id} not found")
        
        # Get participant
        participant = self.participants[participant_id]
        
        # Check if participant is in the right session
        if participant.session_id != session_id:
            raise ValueError(f"Participant {participant_id} is not in session {session_id}")
        
        # Create CoinJoin transaction if not already created
        if not session.coinjoin_transaction:
            session.create_coinjoin_transaction()
        
        # Sign transaction
        signature = participant.sign_transaction(session.coinjoin_transaction)
        
        # Add signature to session
        session.add_transaction_signature(participant_id, signature)
        
        # Update session data
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = session.status
        
        logger.info(f"Signed CoinJoin transaction for participant {participant_id} in session {session_id}")
        
        # Return signature data
        return {
            "participant_id": participant_id,
            "session_id": session_id,
            "signature": signature.hex(),
            "status": session.status
        }
    
    async def get_final_transaction(self, session_id: str) -> Dict[str, Any]:
        """
        Get the final CoinJoin transaction.
        
        Args:
            session_id: The session ID.
            
        Returns:
            The final transaction data.
            
        Raises:
            ValueError: If the session is not found or not completed.
        """
        # Get mixing coordinator
        coordinator = get_mixing_coordinator()
        
        # Get session
        session = coordinator.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Check if session is completed
        if session.status != "completed":
            raise ValueError(f"Session {session_id} is not completed")
        
        # Get final transaction
        final_transaction = session.get_final_transaction()
        
        # Update session data
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = session.status
        
        logger.info(f"Got final transaction for session {session_id}")
        
        # Return transaction data
        return final_transaction
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get the status of a mixing session.
        
        Args:
            session_id: The session ID.
            
        Returns:
            The session status data.
            
        Raises:
            ValueError: If the session is not found.
        """
        # Get mixing coordinator
        coordinator = get_mixing_coordinator()
        
        # Get session
        session = coordinator.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Update session data
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = session.status
        
        # Return session data
        return session.to_dict()
    
    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all active mixing sessions.
        
        Returns:
            A list of active session data.
        """
        # Get mixing coordinator
        coordinator = get_mixing_coordinator()
        
        # Get active sessions
        active_sessions = coordinator.get_active_sessions()
        
        # Return session data
        return [session.to_dict() for session in active_sessions]
    
    async def get_my_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all mixing sessions the wallet is participating in.
        
        Returns:
            A list of session data.
        """
        # Return session data
        return list(self.sessions.values())
    
    async def get_my_participants(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all participants the wallet has created.
        
        Args:
            session_id: Optional session ID to filter by.
            
        Returns:
            A list of participant data.
        """
        # Filter participants by session ID if provided
        if session_id:
            participants = [
                p for p in self.participants.values()
                if p.session_id == session_id
            ]
        else:
            participants = list(self.participants.values())
        
        # Return participant data
        return [
            {
                "participant_id": p.participant_id,
                "session_id": p.session_id,
                "input_address": p.input_address,
                "output_address": p.output_address
            }
            for p in participants
        ]
    
    async def submit_final_transaction(self, session_id: str) -> Dict[str, Any]:
        """
        Submit the final CoinJoin transaction to the network.
        
        Args:
            session_id: The session ID.
            
        Returns:
            The submission response.
            
        Raises:
            ValueError: If the session is not found or not completed.
            NotImplementedError: This method is not fully implemented.
        """
        # Get final transaction
        final_transaction = await self.get_final_transaction(session_id)
        
        # In a real implementation, this would submit the transaction to the network
        # For demonstration, we'll just return the transaction
        logger.info(f"Submitted final transaction for session {session_id}")
        
        # Return submission response
        return {
            "session_id": session_id,
            "transaction_id": "dummy_transaction_id",
            "status": "submitted",
            "timestamp": datetime.now().isoformat()
        }
