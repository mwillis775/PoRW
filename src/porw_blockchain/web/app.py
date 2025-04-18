#!/usr/bin/env python3
"""
Web interface for the PoRW blockchain system.
"""

import asyncio
import json
import logging
import os
import secrets
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import aiohttp_jinja2
import jinja2
from aiohttp import web

from ..core.wallet import Wallet
from ..core.blockchain import Blockchain
from ..network.node import Node
from ..protein.mining import ProteinMiner, MiningConfig
from ..protein.data_management import (
    list_protein_data,
    load_protein_data,
    save_protein_data,
    generate_protein_id,
    DEFAULT_PROTEIN_DATA_DIR
)
from ..storage.pors.node import StorageNode
from ..contracts.manager import ContractManager
from ..contracts.models import ContractLanguage
from ..contracts.transaction import (
    create_contract_deployment_transaction,
    create_contract_call_transaction,
    create_contract_transfer_transaction
)
from ..storage.database import Database
from .routes.explorer import setup_explorer_routes
from .filters import setup_filters

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
BLOCKCHAIN = None
NODE = None
MINER = None
STORAGE_NODE = None
WALLET = None
CONTRACT_MANAGER = None


class WebInterface:
    """Web interface for the PoRW blockchain system."""

    def __init__(self, host: str = '127.0.0.1', port: int = 8080, data_dir: Optional[Path] = None):
        """
        Initialize the web interface.

        Args:
            host: Host to bind to
            port: Port to bind to
            data_dir: Data directory for the blockchain
        """
        self.host = host
        self.port = port
        self.data_dir = data_dir or Path.home() / '.porw' / 'web'
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Create the web application
        self.app = web.Application()

        # Set up Jinja2 templates
        env = aiohttp_jinja2.setup(
            self.app,
            loader=jinja2.FileSystemLoader(
                os.path.join(os.path.dirname(__file__), 'templates')
            )
        )

        # Set up template filters
        setup_filters(env)

        # Set up routes
        self._setup_routes()

        # Set up static files
        self.app.router.add_static(
            '/static/',
            os.path.join(os.path.dirname(__file__), 'static'),
            name='static'
        )

        # Set up session middleware
        self.app.middlewares.append(self._session_middleware)

        # Set up startup and cleanup
        self.app.on_startup.append(self._startup)
        self.app.on_cleanup.append(self._cleanup)

        logger.info(f"Initialized web interface on {host}:{port}")

    def _setup_routes(self):
        """Set up the routes for the web interface."""
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/dashboard', self.handle_dashboard)
        self.app.router.add_get('/wallet', self.handle_wallet)
        self.app.router.add_post('/wallet/create', self.handle_wallet_create)
        self.app.router.add_post('/wallet/import', self.handle_wallet_import)
        self.app.router.add_post('/wallet/send', self.handle_wallet_send)
        self.app.router.add_get('/mining', self.handle_mining)
        self.app.router.add_post('/mining/start', self.handle_mining_start)
        self.app.router.add_post('/mining/stop', self.handle_mining_stop)
        self.app.router.add_get('/storage', self.handle_storage)
        self.app.router.add_post('/storage/start', self.handle_storage_start)
        self.app.router.add_post('/storage/stop', self.handle_storage_stop)

        # Set up explorer routes
        self.app['static_root'] = os.path.join(os.path.dirname(__file__), 'static')
        setup_explorer_routes(self.app, BLOCKCHAIN, Database())

        # Protein data routes
        self.app.router.add_get('/protein-data', self.handle_protein_data)
        self.app.router.add_get('/protein-data/{protein_id}', self.handle_protein_detail)
        self.app.router.add_get('/protein-data/{protein_id}/download', self.handle_protein_download)
        self.app.router.add_get('/science', self.handle_science)

        # Smart contract routes
        self.app.router.add_get('/contracts', self.handle_contracts)
        self.app.router.add_get('/contracts/{contract_id}', self.handle_contract_detail)
        self.app.router.add_get('/contracts/deploy', self.handle_contract_deploy)
        self.app.router.add_post('/contracts/deploy', self.handle_contract_deploy_post)
        self.app.router.add_get('/contracts/{contract_id}/interact', self.handle_contract_interact)
        self.app.router.add_post('/contracts/{contract_id}/call', self.handle_contract_call)
        self.app.router.add_post('/contracts/{contract_id}/transfer', self.handle_contract_transfer)
        self.app.router.add_post('/contracts/{contract_id}/pause', self.handle_contract_pause)
        self.app.router.add_post('/contracts/{contract_id}/resume', self.handle_contract_resume)
        self.app.router.add_post('/contracts/{contract_id}/terminate', self.handle_contract_terminate)

        # API routes
        self.app.router.add_get('/api/status', self.handle_api_status)
        self.app.router.add_get('/api/wallet/balance', self.handle_api_wallet_balance)
        self.app.router.add_get('/api/wallet/transactions', self.handle_api_wallet_transactions)
        self.app.router.add_get('/api/wallet/decrypt-memo', self.handle_api_wallet_decrypt_memo)
        self.app.router.add_get('/api/protein-data', self.handle_api_protein_data)
        self.app.router.add_get('/api/protein-data/{protein_id}', self.handle_api_protein_detail)
        self.app.router.add_get('/api/protein-data/{protein_id}/pdb', self.handle_api_protein_pdb)

        # Zero-Knowledge Proof routes
        self.app.router.add_get('/zkp', self.handle_zkp)
        self.app.router.add_post('/zkp/confidential-transaction', self.handle_zkp_confidential_transaction)
        self.app.router.add_post('/zkp/identity-proof', self.handle_zkp_identity_proof)
        self.app.router.add_post('/zkp/contract-proof', self.handle_zkp_contract_proof)
        self.app.router.add_post('/zkp/protein-proof', self.handle_zkp_protein_proof)
        self.app.router.add_post('/zkp/verify', self.handle_zkp_verify)

        # Stealth Address routes
        self.app.router.add_get('/stealth', self.handle_stealth)
        self.app.router.add_post('/stealth/create', self.handle_stealth_create)
        self.app.router.add_post('/stealth/send', self.handle_stealth_send)
        self.app.router.add_get('/api/stealth/scan', self.handle_api_stealth_scan)

        # Mixing routes
        self.app.router.add_get('/mixing', self.handle_mixing)
        self.app.router.add_post('/mixing/create', self.handle_mixing_create)
        self.app.router.add_post('/mixing/join', self.handle_mixing_join)
        self.app.router.add_get('/mixing/session/{session_id}', self.handle_mixing_session)
        self.app.router.add_get('/api/mixing/active-sessions', self.handle_api_mixing_active_sessions)
        self.app.router.add_get('/api/mixing/my-sessions', self.handle_api_mixing_my_sessions)
        self.app.router.add_get('/api/mixing/get-signature', self.handle_api_mixing_get_signature)
        self.app.router.add_get('/api/mixing/sign-transaction', self.handle_api_mixing_sign_transaction)
        self.app.router.add_get('/api/mixing/submit-transaction', self.handle_api_mixing_submit_transaction)

        # Multi-Signature Wallet routes
        self.app.router.add_get('/multisig', self.handle_multisig)
        self.app.router.add_post('/multisig/create', self.handle_multisig_create)
        self.app.router.add_post('/multisig/join', self.handle_multisig_join)
        self.app.router.add_get('/multisig/wallet/{wallet_id}', self.handle_multisig_wallet)
        self.app.router.add_post('/multisig/wallet/{wallet_id}/add-key', self.handle_multisig_add_key)
        self.app.router.add_post('/multisig/wallet/{wallet_id}/create-transaction', self.handle_multisig_create_transaction)
        self.app.router.add_post('/multisig/wallet/{wallet_id}/sign-transaction', self.handle_multisig_sign_transaction)
        self.app.router.add_post('/multisig/wallet/{wallet_id}/submit-transaction', self.handle_multisig_submit_transaction)
        self.app.router.add_get('/multisig/wallet/{wallet_id}/transaction/{transaction_id}', self.handle_multisig_transaction)
        self.app.router.add_get('/api/multisig/wallet/{wallet_id}', self.handle_api_multisig_wallet)

        # Address Book routes
        self.app.router.add_get('/contacts', self.handle_contacts)
        self.app.router.add_post('/contacts/add', self.handle_contacts_add)
        self.app.router.add_post('/contacts/delete', self.handle_contacts_delete)
        self.app.router.add_get('/contacts/{contact_id}', self.handle_contact_detail)
        self.app.router.add_get('/contacts/{contact_id}/edit', self.handle_contact_edit)
        self.app.router.add_post('/contacts/{contact_id}/update', self.handle_contact_update)
        self.app.router.add_post('/contacts/{contact_id}/add-tag', self.handle_contact_add_tag)
        self.app.router.add_post('/contacts/{contact_id}/remove-tag', self.handle_contact_remove_tag)

        # Transaction Labeling routes
        self.app.router.add_get('/transactions/{transaction_id}', self.handle_transaction_detail)
        self.app.router.add_get('/transactions/labels', self.handle_transaction_labels)
        self.app.router.add_post('/transactions/labels/add', self.handle_transaction_label_add)
        self.app.router.add_post('/transactions/labels/delete', self.handle_transaction_label_delete)
        self.app.router.add_get('/transactions/labels/{transaction_id}', self.handle_transaction_label_detail)
        self.app.router.add_get('/transactions/labels/{transaction_id}/edit', self.handle_transaction_label_edit)
        self.app.router.add_post('/transactions/labels/{transaction_id}/update', self.handle_transaction_label_update)
        self.app.router.add_post('/transactions/labels/{transaction_id}/add-tag', self.handle_transaction_label_add_tag)
        self.app.router.add_post('/transactions/labels/{transaction_id}/remove-tag', self.handle_transaction_label_remove_tag)

        # Recurring Transactions routes
        self.app.router.add_get('/recurring', self.handle_recurring)
        self.app.router.add_post('/recurring/create', self.handle_recurring_create)
        self.app.router.add_post('/recurring/delete', self.handle_recurring_delete)
        self.app.router.add_get('/recurring/{transaction_id}', self.handle_recurring_detail)
        self.app.router.add_get('/recurring/{transaction_id}/edit', self.handle_recurring_edit)
        self.app.router.add_post('/recurring/{transaction_id}/update', self.handle_recurring_update)
        self.app.router.add_post('/recurring/{transaction_id}/enable', self.handle_recurring_enable)
        self.app.router.add_post('/recurring/{transaction_id}/disable', self.handle_recurring_disable)
        self.app.router.add_post('/recurring/{transaction_id}/execute', self.handle_recurring_execute)
        self.app.router.add_post('/recurring/execute-all', self.handle_recurring_execute_all)

    @web.middleware
    async def _session_middleware(self, request, handler):
        """Session middleware for the web interface."""
        # Create a session if one doesn't exist
        session = request.cookies.get('session')
        if not session:
            session = secrets.token_hex(16)

        # Call the handler
        response = await handler(request)

        # Set the session cookie
        if not isinstance(response, web.StreamResponse):
            response = web.Response(body=response, content_type='text/html')
        response.set_cookie('session', session, max_age=3600*24*7)

        return response

    async def _startup(self, app):
        """Start up the web interface."""
        global BLOCKCHAIN, NODE, MINER, STORAGE_NODE, WALLET, CONTRACT_MANAGER

        # Initialize the blockchain
        BLOCKCHAIN = Blockchain(data_dir=self.data_dir / 'blockchain')

        # Initialize the node
        NODE = Node(
            host='0.0.0.0',
            port=3000,
            blockchain=BLOCKCHAIN,
            data_dir=self.data_dir / 'node'
        )

        # Initialize the wallet
        wallet_path = self.data_dir / 'wallet.json'
        if wallet_path.exists():
            WALLET = Wallet.load(wallet_path)

        # Initialize the contract manager
        CONTRACT_MANAGER = ContractManager(data_dir=self.data_dir / 'contracts')

        # Start the node
        await NODE.start()

        logger.info("Web interface started")

    async def _cleanup(self, app):
        """Clean up the web interface."""
        global BLOCKCHAIN, NODE, MINER, STORAGE_NODE, WALLET, CONTRACT_MANAGER

        # Stop the miner if it's running
        if MINER and MINER.running:
            await MINER.stop()

        # Stop the storage node if it's running
        if STORAGE_NODE and STORAGE_NODE.running:
            await STORAGE_NODE.stop()

        # Stop the node
        if NODE:
            await NODE.stop()

        # Save the wallet
        if WALLET:
            WALLET.save(self.data_dir / 'wallet.json')

        # Clean up contract manager (if needed)
        CONTRACT_MANAGER = None

        logger.info("Web interface stopped")

    async def run(self):
        """Run the web interface."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"Web interface running on http://{self.host}:{self.port}")

        # Keep the server running
        while True:
            await asyncio.sleep(3600)

    @aiohttp_jinja2.template('index.html')
    async def handle_index(self, request):
        """Handle the index page."""
        return {
            'title': 'PoRW Blockchain',
            'wallet': WALLET,
            'blockchain': BLOCKCHAIN,
            'node': NODE,
            'miner': MINER,
            'storage_node': STORAGE_NODE
        }

    @aiohttp_jinja2.template('dashboard.html')
    async def handle_dashboard(self, request):
        """Handle the dashboard page."""
        return {
            'title': 'Dashboard - PoRW Blockchain',
            'wallet': WALLET,
            'blockchain': BLOCKCHAIN,
            'node': NODE,
            'miner': MINER,
            'storage_node': STORAGE_NODE
        }

    @aiohttp_jinja2.template('wallet.html')
    async def handle_wallet(self, request):
        """Handle the wallet page."""
        return {
            'title': 'Wallet - PoRW Blockchain',
            'wallet': WALLET,
            'blockchain': BLOCKCHAIN
        }

    async def handle_wallet_create(self, request):
        """Handle wallet creation."""
        global WALLET

        # Create a new wallet
        WALLET = Wallet.create()

        # Save the wallet
        WALLET.save(self.data_dir / 'wallet.json')

        # Redirect to the wallet page
        return web.HTTPFound('/wallet')

    async def handle_wallet_import(self, request):
        """Handle wallet import."""
        global WALLET

        # Get the private key from the form
        data = await request.post()
        private_key = data.get('private_key')

        if not private_key:
            return web.HTTPBadRequest(text="Private key is required")

        try:
            # Import the wallet
            WALLET = Wallet.from_private_key(private_key)

            # Save the wallet
            WALLET.save(self.data_dir / 'wallet.json')

            # Redirect to the wallet page
            return web.HTTPFound('/wallet')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error importing wallet: {e}")

    async def handle_wallet_send(self, request):
        """Handle sending tokens from the wallet."""
        global WALLET, BLOCKCHAIN, NODE

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction details from the form
        data = await request.post()
        recipient = data.get('recipient')
        amount = data.get('amount')
        memo = data.get('memo', '')
        encrypt_memo = data.get('encrypt_memo', 'off') == 'on'
        recipient_public_key = data.get('recipient_public_key', '')
        confidential = data.get('confidential', 'off') == 'on'

        if not recipient or not amount:
            return web.HTTPBadRequest(text="Recipient and amount are required")

        try:
            # Convert amount to float
            amount = float(amount)

            # Create transaction based on options
            if confidential:
                # Create confidential transaction
                if encrypt_memo and memo:
                    # Can't have both confidential and encrypted memo yet
                    return web.HTTPBadRequest(text="Confidential transactions with encrypted memos are not supported yet")

                # Create confidential transaction
                transaction = WALLET.create_and_sign_confidential_transaction(
                    recipient=recipient,
                    amount=amount,
                    memo=memo if memo else None
                )
            elif encrypt_memo and memo and recipient_public_key:
                # Create transaction with encrypted memo
                from ..privacy.encrypted_memo import encrypt_memo as encrypt_memo_func
                encrypted_memo = encrypt_memo_func(
                    memo=memo,
                    recipient_public_key_pem=recipient_public_key.encode('utf-8'),
                    sender_private_key_pem=WALLET.private_key.encode('utf-8')
                )
                transaction = WALLET.create_transaction(recipient, amount, memo=encrypted_memo)
                transaction.is_memo_encrypted = True
            else:
                # Create regular transaction
                transaction = WALLET.create_transaction(recipient, amount, memo=memo if memo else None)

            # Broadcast the transaction
            if NODE:
                await NODE.broadcast_transaction(transaction)

            # Redirect to the wallet page
            return web.HTTPFound('/wallet')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error sending transaction: {e}")

    @aiohttp_jinja2.template('mining.html')
    async def handle_mining(self, request):
        """Handle the mining page."""
        return {
            'title': 'Mining - PoRW Blockchain',
            'wallet': WALLET,
            'blockchain': BLOCKCHAIN,
            'miner': MINER
        }

    async def handle_mining_start(self, request):
        """Handle starting the miner."""
        global MINER, WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Check if miner is already running
        if MINER and MINER.running:
            return web.HTTPBadRequest(text="Miner is already running")

        # Get mining configuration from the form
        data = await request.post()
        mining_threads = int(data.get('mining_threads', 4))
        enable_gpu = data.get('enable_gpu', 'off') == 'on'

        # Create mining configuration
        config = MiningConfig(
            enable_mining=True,
            mining_threads=mining_threads,
            enable_gpu=enable_gpu,
            protein_data_dir=self.data_dir / 'protein_data'
        )

        # Create and start the miner
        MINER = ProteinMiner(config)
        await MINER.start()

        # Redirect to the mining page
        return web.HTTPFound('/mining')

    async def handle_mining_stop(self, request):
        """Handle stopping the miner."""
        global MINER

        # Check if miner is running
        if not MINER or not MINER.running:
            return web.HTTPBadRequest(text="Miner is not running")

        # Stop the miner
        await MINER.stop()

        # Redirect to the mining page
        return web.HTTPFound('/mining')

    @aiohttp_jinja2.template('storage.html')
    async def handle_storage(self, request):
        """Handle the storage page."""
        return {
            'title': 'Storage - PoRW Blockchain',
            'wallet': WALLET,
            'blockchain': BLOCKCHAIN,
            'storage_node': STORAGE_NODE
        }

    async def handle_storage_start(self, request):
        """Handle starting the storage node."""
        global STORAGE_NODE, WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Check if storage node is already running
        if STORAGE_NODE and STORAGE_NODE.running:
            return web.HTTPBadRequest(text="Storage node is already running")

        # Get storage configuration from the form
        data = await request.post()
        storage_capacity = int(data.get('storage_capacity', 1024)) * 1024 * 1024  # Convert MB to bytes

        # Create and start the storage node
        STORAGE_NODE = StorageNode(
            node_id=f"storage_{WALLET.address[:8]}",
            host='0.0.0.0',
            port=3500,
            data_dir=self.data_dir / 'storage',
            capacity=storage_capacity
        )

        await STORAGE_NODE.start()

        # Redirect to the storage page
        return web.HTTPFound('/storage')

    async def handle_storage_stop(self, request):
        """Handle stopping the storage node."""
        global STORAGE_NODE

        # Check if storage node is running
        if not STORAGE_NODE or not STORAGE_NODE.running:
            return web.HTTPBadRequest(text="Storage node is not running")

        # Stop the storage node
        await STORAGE_NODE.stop()

        # Redirect to the storage page
        return web.HTTPFound('/storage')

    async def handle_api_status(self, request):
        """Handle API status request."""
        status = {
            'blockchain': {
                'height': BLOCKCHAIN.height if BLOCKCHAIN else 0,
                'last_block': BLOCKCHAIN.last_block.to_dict() if BLOCKCHAIN and BLOCKCHAIN.last_block else None
            },
            'node': {
                'running': NODE.running if NODE else False,
                'peers': len(NODE.peers) if NODE else 0
            },
            'miner': {
                'running': MINER.running if MINER else False,
                'status': MINER.get_status() if MINER else None
            },
            'storage_node': {
                'running': STORAGE_NODE.running if STORAGE_NODE else False,
                'status': STORAGE_NODE.get_status() if STORAGE_NODE else None
            },
            'wallet': {
                'address': WALLET.address if WALLET else None,
                'balance': WALLET.get_balance() if WALLET else 0
            }
        }

        return web.json_response(status)

    async def handle_api_wallet_balance(self, request):
        """Handle API wallet balance request."""
        if not WALLET:
            return web.json_response({'error': 'No wallet found'}, status=400)

        balance = WALLET.get_balance()

        return web.json_response({'balance': balance})

    async def handle_api_wallet_transactions(self, request):
        """Handle API wallet transactions request."""
        if not WALLET:
            return web.json_response({'error': 'No wallet found'}, status=400)

        transactions = WALLET.get_transactions()

        return web.json_response({'transactions': transactions})

    async def handle_api_wallet_decrypt_memo(self, request):
        """Handle API wallet decrypt memo request."""
        if not WALLET:
            return web.json_response({'error': 'No wallet found'}, status=400)

        # Get parameters
        tx_id = request.query.get('tx_id')
        sender_public_key = request.query.get('sender_public_key')

        if not tx_id:
            return web.json_response({'error': 'Transaction ID is required'}, status=400)

        try:
            # Find the transaction
            transaction = None
            for tx in WALLET.get_transactions():
                if tx.transaction_id == tx_id:
                    transaction = tx
                    break

            if not transaction:
                return web.json_response({'error': 'Transaction not found'}, status=404)

            # Check if the transaction has an encrypted memo
            if not transaction.memo or not transaction.is_memo_encrypted:
                return web.json_response({'error': 'Transaction does not have an encrypted memo'}, status=400)

            # Decrypt the memo
            from ..privacy.encrypted_memo import decrypt_memo
            private_key_pem = WALLET.private_key.encode('utf-8')
            sender_public_key_pem = sender_public_key.encode('utf-8') if sender_public_key else None

            decrypted_memo, signature_verified = decrypt_memo(
                encrypted_memo=transaction.memo,
                private_key_pem=private_key_pem,
                sender_public_key_pem=sender_public_key_pem
            )

            return web.json_response({
                'decrypted_memo': decrypted_memo,
                'signature_verified': signature_verified
            })

        except Exception as e:
            logger.exception(f"Error decrypting memo: {e}")
            return web.json_response({'error': str(e)}, status=500)

    @aiohttp_jinja2.template('protein_data.html')
    async def handle_protein_data(self, request):
        """Handle the protein data page."""
        # Get query parameters
        query = request.query
        search = query.get('search', '')
        sort = query.get('sort', 'date_desc')
        page = int(query.get('page', 1))
        limit = int(query.get('limit', 25))

        # List protein data
        try:
            proteins = list_protein_data(DEFAULT_PROTEIN_DATA_DIR)

            # Filter by search term if provided
            if search:
                proteins = [p for p in proteins if search.lower() in p.get('name', '').lower() or
                                                 search.lower() in p.get('protein_id', '').lower()]

            # Sort proteins
            if sort == 'date_desc':
                proteins.sort(key=lambda p: p.get('folding_timestamp', 0), reverse=True)
            elif sort == 'date_asc':
                proteins.sort(key=lambda p: p.get('folding_timestamp', 0))
            elif sort == 'energy_asc':
                proteins.sort(key=lambda p: p.get('energy_score', 0))
            elif sort == 'size_desc':
                proteins.sort(key=lambda p: len(p.get('amino_sequence', '')), reverse=True)
            elif sort == 'size_asc':
                proteins.sort(key=lambda p: len(p.get('amino_sequence', '')))

            # Calculate pagination
            total_proteins = len(proteins)
            total_pages = (total_proteins + limit - 1) // limit
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            proteins_page = proteins[start_idx:end_idx]

            # Calculate statistics
            total_amino_acids = sum(len(p.get('amino_sequence', '')) for p in proteins)
            total_compute_hours = sum(p.get('folding_time_ms', 0) for p in proteins) / (1000 * 60 * 60)

            # Generate stats data for chart
            now = time.time()
            week_seconds = 7 * 24 * 60 * 60
            protein_stats_data = [
                len([p for p in proteins if now - p.get('folding_timestamp', 0) < week_seconds]),
                len([p for p in proteins if week_seconds <= now - p.get('folding_timestamp', 0) < 2 * week_seconds]),
                len([p for p in proteins if 2 * week_seconds <= now - p.get('folding_timestamp', 0) < 3 * week_seconds]),
                len([p for p in proteins if 3 * week_seconds <= now - p.get('folding_timestamp', 0) < 4 * week_seconds])
            ]

            # Helper function for pagination URLs
            def pagination_url(page_num):
                params = dict(request.query)
                params['page'] = str(page_num)
                return f"/protein-data?{urlencode(params)}"

            return {
                'title': 'Protein Data - PoRW Blockchain',
                'proteins': proteins_page,
                'total_proteins': total_proteins,
                'total_amino_acids': total_amino_acids,
                'total_compute_hours': total_compute_hours,
                'protein_stats_data': protein_stats_data,
                'page': page,
                'limit': limit,
                'total_pages': total_pages,
                'search': search,
                'sort': sort,
                'pagination_url': pagination_url
            }
        except Exception as e:
            logger.exception(f"Error loading protein data: {e}")
            return {
                'title': 'Protein Data - PoRW Blockchain',
                'proteins': [],
                'total_proteins': 0,
                'total_amino_acids': 0,
                'total_compute_hours': 0,
                'protein_stats_data': [0, 0, 0, 0],
                'page': 1,
                'limit': limit,
                'total_pages': 1,
                'search': search,
                'sort': sort,
                'error': str(e)
            }

    @aiohttp_jinja2.template('protein_detail.html')
    async def handle_protein_detail(self, request):
        """Handle the protein detail page."""
        protein_id = request.match_info.get('protein_id')

        try:
            # Load protein data
            protein = load_protein_data(DEFAULT_PROTEIN_DATA_DIR, protein_id)
            if not protein:
                raise web.HTTPNotFound(text=f"Protein not found: {protein_id}")

            # Generate energy profile data for chart
            amino_sequence = protein.get('amino_sequence', '')
            energy_scores = protein.get('residue_energy_scores', [])

            # If no per-residue energy scores, generate dummy data
            if not energy_scores or len(energy_scores) != len(amino_sequence):
                energy_scores = [protein.get('energy_score', 0) / len(amino_sequence)] * len(amino_sequence)

            energy_profile = {
                'positions': list(range(1, len(amino_sequence) + 1)),
                'values': energy_scores
            }

            return {
                'title': f"{protein.get('name', 'Protein')} - PoRW Blockchain",
                'protein': protein,
                'energy_profile': energy_profile
            }
        except web.HTTPNotFound:
            raise
        except Exception as e:
            logger.exception(f"Error loading protein detail: {e}")
            raise web.HTTPInternalServerError(text=f"Error loading protein detail: {e}")

    async def handle_protein_download(self, request):
        """Handle protein data download."""
        protein_id = request.match_info.get('protein_id')
        format_type = request.query.get('format', 'pdb')

        try:
            # Load protein data
            protein = load_protein_data(DEFAULT_PROTEIN_DATA_DIR, protein_id)
            if not protein:
                raise web.HTTPNotFound(text=f"Protein not found: {protein_id}")

            if format_type == 'json':
                # Return JSON data
                return web.json_response(protein)
            else:
                # Return PDB file
                pdb_data = protein.get('pdb_data', '')
                if not pdb_data:
                    raise web.HTTPNotFound(text=f"PDB data not found for protein: {protein_id}")

                # Set up response with appropriate headers
                response = web.Response(text=pdb_data)
                response.headers['Content-Type'] = 'chemical/x-pdb'
                response.headers['Content-Disposition'] = f'attachment; filename="{protein_id}.pdb"'
                return response
        except web.HTTPNotFound:
            raise
        except Exception as e:
            logger.exception(f"Error downloading protein data: {e}")
            raise web.HTTPInternalServerError(text=f"Error downloading protein data: {e}")

    @aiohttp_jinja2.template('science.html')
    async def handle_science(self, request):
        """Handle the science page."""
        try:
            # List protein data for statistics
            proteins = list_protein_data(DEFAULT_PROTEIN_DATA_DIR)

            # Calculate statistics
            total_proteins = len(proteins)
            total_amino_acids = sum(len(p.get('amino_sequence', '')) for p in proteins)
            total_compute_hours = sum(p.get('folding_time_ms', 0) for p in proteins) / (1000 * 60 * 60)

            # Sample publications (in a real system, these would come from a database)
            publications = [
                {
                    'title': 'Distributed Protein Folding on a Blockchain Network',
                    'authors': 'Smith J., Johnson A., Williams M.',
                    'journal': 'Journal of Computational Biology',
                    'volume': '28',
                    'issue': '4',
                    'pages': '405-418',
                    'date': '2023',
                    'url': 'https://example.com/publication1'
                },
                {
                    'title': 'Proof of Real Work: A Novel Consensus Mechanism for Scientific Computing',
                    'authors': 'Brown R., Davis K., Miller L.',
                    'journal': 'Blockchain Research Letters',
                    'volume': '15',
                    'issue': '2',
                    'pages': '123-142',
                    'date': '2022',
                    'url': 'https://example.com/publication2'
                }
            ]

            return {
                'title': 'Scientific Impact - PoRW Blockchain',
                'total_proteins': total_proteins,
                'total_amino_acids': total_amino_acids,
                'total_compute_hours': total_compute_hours,
                'scientific_citations': 12,  # Sample data
                'publications': publications
            }
        except Exception as e:
            logger.exception(f"Error loading science page: {e}")
            return {
                'title': 'Scientific Impact - PoRW Blockchain',
                'total_proteins': 0,
                'total_amino_acids': 0,
                'total_compute_hours': 0,
                'scientific_citations': 0,
                'publications': [],
                'error': str(e)
            }

    @aiohttp_jinja2.template('contracts.html')
    async def handle_contracts(self, request):
        """Handle the contracts page."""
        try:
            # List all contracts
            contracts = CONTRACT_MANAGER.list_contracts()

            return {
                'title': 'Smart Contracts - PoRW Blockchain',
                'contracts': contracts,
                'wallet': WALLET
            }
        except Exception as e:
            logger.exception(f"Error loading contracts: {e}")
            return {
                'title': 'Smart Contracts - PoRW Blockchain',
                'contracts': [],
                'wallet': WALLET,
                'error': str(e)
            }

    @aiohttp_jinja2.template('contract_detail.html')
    async def handle_contract_detail(self, request):
        """Handle the contract detail page."""
        contract_id = request.match_info.get('contract_id')

        try:
            # Get contract
            contract = CONTRACT_MANAGER.get_contract(contract_id)
            if not contract:
                raise web.HTTPNotFound(text=f"Contract not found: {contract_id}")

            # Get contract events
            events = CONTRACT_MANAGER.get_contract_events(contract_id)

            return {
                'title': f"{contract.name} - PoRW Blockchain",
                'contract': contract,
                'events': events,
                'wallet': WALLET
            }
        except web.HTTPNotFound:
            raise
        except Exception as e:
            logger.exception(f"Error loading contract detail: {e}")
            raise web.HTTPInternalServerError(text=f"Error loading contract detail: {e}")

    @aiohttp_jinja2.template('contract_deploy.html')
    async def handle_contract_deploy(self, request):
        """Handle the contract deployment page."""
        # Check if a template was requested
        template_name = request.query.get('template')
        template = None

        if template_name == 'token':
            # Load token contract template (Python)
            with open(os.path.join(os.path.dirname(__file__), '../contracts/examples/token.py'), 'r') as f:
                code = f.read()

            template = {
                'name': 'Token Contract',
                'description': 'A standard token contract with transfer, approve, and transferFrom functionality.',
                'language': ContractLanguage.PYTHON,
                'code': code,
                'abi': {
                    'functions': [
                        {'name': 'initialize', 'params': [
                            {'name': 'name', 'type': 'string'},
                            {'name': 'symbol', 'type': 'string'},
                            {'name': 'total_supply', 'type': 'number'}
                        ]},
                        {'name': 'name', 'params': [], 'constant': True},
                        {'name': 'symbol', 'params': [], 'constant': True},
                        {'name': 'total_supply', 'params': [], 'constant': True},
                        {'name': 'balance_of', 'params': [{'name': 'owner', 'type': 'string'}], 'constant': True},
                        {'name': 'allowance', 'params': [
                            {'name': 'owner', 'type': 'string'},
                            {'name': 'spender', 'type': 'string'}
                        ], 'constant': True},
                        {'name': 'transfer', 'params': [
                            {'name': 'to', 'type': 'string'},
                            {'name': 'amount', 'type': 'number'}
                        ]},
                        {'name': 'approve', 'params': [
                            {'name': 'spender', 'type': 'string'},
                            {'name': 'amount', 'type': 'number'}
                        ]},
                        {'name': 'transfer_from', 'params': [
                            {'name': 'from_address', 'type': 'string'},
                            {'name': 'to', 'type': 'string'},
                            {'name': 'amount', 'type': 'number'}
                        ]}
                    ]
                }
            }
        elif template_name == 'token_json':
            # Load token contract template (JSON)
            with open(os.path.join(os.path.dirname(__file__), '../contracts/examples/token.json'), 'r') as f:
                code = f.read()

            template = {
                'name': 'Token Contract (JSON)',
                'description': 'A JSON-based token contract with basic functionality.',
                'language': ContractLanguage.JSON,
                'code': code,
                'abi': {
                    'functions': [
                        {'name': 'initialize', 'params': [
                            {'name': 'name', 'type': 'string'},
                            {'name': 'symbol', 'type': 'string'},
                            {'name': 'total_supply', 'type': 'number'}
                        ]},
                        {'name': 'name', 'params': [], 'constant': True},
                        {'name': 'symbol', 'params': [], 'constant': True},
                        {'name': 'total_supply', 'params': [], 'constant': True},
                        {'name': 'balance_of', 'params': [{'name': 'owner', 'type': 'string'}], 'constant': True},
                        {'name': 'transfer', 'params': [
                            {'name': 'to', 'type': 'string'},
                            {'name': 'amount', 'type': 'number'}
                        ]}
                    ]
                }
            }
        elif template_name == 'crowdfunding':
            # Load crowdfunding contract template
            with open(os.path.join(os.path.dirname(__file__), '../contracts/examples/crowdfunding.py'), 'r') as f:
                code = f.read()

            template = {
                'name': 'Crowdfunding Contract',
                'description': 'A crowdfunding contract with goal, deadline, and refund functionality.',
                'language': ContractLanguage.PYTHON,
                'code': code,
                'abi': {
                    'functions': [
                        {'name': 'initialize', 'params': [
                            {'name': 'goal', 'type': 'number'},
                            {'name': 'deadline', 'type': 'number'}
                        ]},
                        {'name': 'contribute', 'params': []},
                        {'name': 'check_goal_reached', 'params': [], 'constant': True},
                        {'name': 'check_deadline_passed', 'params': [], 'constant': True},
                        {'name': 'withdraw', 'params': []},
                        {'name': 'refund', 'params': []},
                        {'name': 'get_campaign_info', 'params': [], 'constant': True},
                        {'name': 'get_contribution', 'params': [{'name': 'contributor', 'type': 'string'}], 'constant': True}
                    ]
                }
            }
        elif template_name == 'storage':
            # Create a simple data storage contract
            code = '''# Data Storage Contract

def initialize():
    """Initialize the storage contract."""
    context.set_storage("owner", context.get_sender())
    context.log("Storage contract initialized")
    context.emit_event("Initialized", {"owner": context.get_sender()})

def store(key, value):
    """Store a value in the contract's storage.

    Args:
        key: The key to store the value under.
        value: The value to store.

    Returns:
        True if successful.
    """
    # Only the owner can store data
    if context.get_sender() != context.get_storage("owner"):
        context.log(f"Unauthorized: {context.get_sender()} is not the owner")
        return False

    context.set_storage(key, value)
    context.log(f"Stored value under key: {key}")
    context.emit_event("DataStored", {"key": key})
    return True

def retrieve(key):
    """Retrieve a value from the contract's storage.

    Args:
        key: The key to retrieve the value for.

    Returns:
        The stored value, or None if not found.
    """
    value = context.get_storage(key)
    context.log(f"Retrieved value for key: {key}")
    return value

def list_keys():
    """List all keys in the contract's storage.

    Returns:
        A list of keys.
    """
    # In a real implementation, we would need to maintain a list of keys
    # For this example, we'll return a placeholder
    keys = context.get_storage("keys") or []
    return keys

def delete(key):
    """Delete a value from the contract's storage.

    Args:
        key: The key to delete.

    Returns:
        True if successful, False if not authorized.
    """
    # Only the owner can delete data
    if context.get_sender() != context.get_storage("owner"):
        context.log(f"Unauthorized: {context.get_sender()} is not the owner")
        return False

    # In a real implementation, we would delete the key
    # For this example, we'll just log the action
    context.log(f"Deleted key: {key}")
    context.emit_event("DataDeleted", {"key": key})
    return True
'''

            template = {
                'name': 'Data Storage Contract',
                'description': 'A contract for storing and retrieving data on the blockchain.',
                'language': ContractLanguage.PYTHON,
                'code': code,
                'abi': {
                    'functions': [
                        {'name': 'initialize', 'params': []},
                        {'name': 'store', 'params': [
                            {'name': 'key', 'type': 'string'},
                            {'name': 'value', 'type': 'string'}
                        ]},
                        {'name': 'retrieve', 'params': [{'name': 'key', 'type': 'string'}], 'constant': True},
                        {'name': 'list_keys', 'params': [], 'constant': True},
                        {'name': 'delete', 'params': [{'name': 'key', 'type': 'string'}]}
                    ]
                }
            }

        return {
            'title': 'Deploy Contract - PoRW Blockchain',
            'template': template,
            'template_name': template_name,
            'wallet': WALLET
        }

    async def handle_contract_deploy_post(self, request):
        """Handle contract deployment form submission."""
        try:
            # Parse form data
            data = await request.post()

            # Create contract data
            contract_data = {
                "name": data.get('name'),
                "description": data.get('description'),
                "language": data.get('language'),
                "code": data.get('code'),
                "abi": json.loads(data.get('abi'))
            }

            # Create deployment transaction
            transaction = create_contract_deployment_transaction(
                sender=data.get('sender'),
                private_key=data.get('private_key'),
                contract_data=contract_data,
                value=float(data.get('value', 0)),
                gas_limit=int(data.get('gas_limit', 2000000)),
                gas_price=float(data.get('gas_price', 0.0000001))
            )

            # Deploy contract
            result = CONTRACT_MANAGER.deploy_contract(transaction)

            if result.success:
                # Redirect to the contract detail page
                return web.HTTPFound(f"/contracts/{result.return_value}")
            else:
                # Return to the deployment page with an error
                return web.HTTPFound(f"/contracts/deploy?error={result.error}")

        except Exception as e:
            logger.exception(f"Error deploying contract: {e}")
            return web.HTTPFound(f"/contracts/deploy?error={str(e)}")

    @aiohttp_jinja2.template('contract_interact.html')
    async def handle_contract_interact(self, request):
        """Handle the contract interaction page."""
        contract_id = request.match_info.get('contract_id')

        try:
            # Get contract
            contract = CONTRACT_MANAGER.get_contract(contract_id)
            if not contract:
                raise web.HTTPNotFound(text=f"Contract not found: {contract_id}")

            # Get transaction history (in a real implementation, this would come from the blockchain)
            # For now, we'll use a placeholder
            transaction_history = []

            # Check if there's a result from a previous interaction
            result = None
            if 'result' in request.query:
                result_data = json.loads(request.query['result'])
                result = {
                    'success': result_data.get('success', False),
                    'return_value': result_data.get('return_value'),
                    'gas_used': result_data.get('gas_used', 0),
                    'logs': result_data.get('logs', []),
                    'error': result_data.get('error'),
                    'transaction_id': result_data.get('transaction_id'),
                    'gas_price': float(request.query.get('gas_price', 0.0000001))
                }

            return {
                'title': f"Interact with {contract.name} - PoRW Blockchain",
                'contract': contract,
                'transaction_history': transaction_history,
                'result': result,
                'wallet': WALLET
            }
        except web.HTTPNotFound:
            raise
        except Exception as e:
            logger.exception(f"Error loading contract interaction page: {e}")
            raise web.HTTPInternalServerError(text=f"Error loading contract interaction page: {e}")

    async def handle_contract_call(self, request):
        """Handle contract function call."""
        contract_id = request.match_info.get('contract_id')

        try:
            # Parse form data
            data = await request.post()

            # Get function name and arguments
            function = data.get('function')

            # Parse arguments
            arguments = []
            for key in data.keys():
                if key.startswith('arguments['):
                    index = int(key.split('[')[1].split(']')[0])
                    while len(arguments) <= index:
                        arguments.append(None)
                    arguments[index] = data[key]

            # Create call transaction
            transaction = create_contract_call_transaction(
                sender=data.get('sender'),
                private_key=data.get('private_key'),
                contract_id=contract_id,
                function=function,
                arguments=arguments,
                value=float(data.get('value', 0)),
                gas_limit=int(data.get('gas_limit', 1000000)),
                gas_price=float(data.get('gas_price', 0.0000001))
            )

            # Execute transaction
            result = CONTRACT_MANAGER.execute_transaction(transaction)

            # Redirect to the interaction page with the result
            result_json = json.dumps({
                'success': result.success,
                'return_value': result.return_value,
                'gas_used': result.gas_used,
                'logs': result.logs,
                'error': result.error,
                'transaction_id': transaction.transaction_id
            })

            return web.HTTPFound(f"/contracts/{contract_id}/interact?result={result_json}&gas_price={transaction.gas_price}")

        except Exception as e:
            logger.exception(f"Error calling contract function: {e}")
            return web.HTTPFound(f"/contracts/{contract_id}/interact?error={str(e)}")

    async def handle_contract_transfer(self, request):
        """Handle token transfer to contract."""
        contract_id = request.match_info.get('contract_id')

        try:
            # Parse form data
            data = await request.post()

            # Create transfer transaction
            transaction = create_contract_transfer_transaction(
                sender=data.get('sender'),
                private_key=data.get('private_key'),
                contract_id=contract_id,
                value=float(data.get('value')),
                gas_limit=int(data.get('gas_limit', 100000)),
                gas_price=float(data.get('gas_price', 0.0000001))
            )

            # Execute transaction
            result = CONTRACT_MANAGER.execute_transaction(transaction)

            # Redirect to the interaction page with the result
            result_json = json.dumps({
                'success': result.success,
                'return_value': result.return_value,
                'gas_used': result.gas_used,
                'logs': result.logs,
                'error': result.error,
                'transaction_id': transaction.transaction_id
            })

            return web.HTTPFound(f"/contracts/{contract_id}/interact?result={result_json}&gas_price={transaction.gas_price}")

        except Exception as e:
            logger.exception(f"Error transferring to contract: {e}")
            return web.HTTPFound(f"/contracts/{contract_id}/interact?error={str(e)}")

    async def handle_contract_pause(self, request):
        """Handle pausing a contract."""
        contract_id = request.match_info.get('contract_id')

        try:
            # Pause the contract
            success = CONTRACT_MANAGER.pause_contract(contract_id)

            if not success:
                return web.HTTPBadRequest(text=f"Failed to pause contract: {contract_id}")

            # Redirect to the contract detail page
            return web.HTTPFound(f"/contracts/{contract_id}")

        except Exception as e:
            logger.exception(f"Error pausing contract: {e}")
            return web.HTTPInternalServerError(text=f"Error pausing contract: {e}")

    async def handle_contract_resume(self, request):
        """Handle resuming a contract."""
        contract_id = request.match_info.get('contract_id')

        try:
            # Resume the contract
            success = CONTRACT_MANAGER.resume_contract(contract_id)

            if not success:
                return web.HTTPBadRequest(text=f"Failed to resume contract: {contract_id}")

            # Redirect to the contract detail page
            return web.HTTPFound(f"/contracts/{contract_id}")

        except Exception as e:
            logger.exception(f"Error resuming contract: {e}")
            return web.HTTPInternalServerError(text=f"Error resuming contract: {e}")

    async def handle_contract_terminate(self, request):
        """Handle terminating a contract."""
        contract_id = request.match_info.get('contract_id')

        try:
            # Terminate the contract
            success = CONTRACT_MANAGER.terminate_contract(contract_id)

            if not success:
                return web.HTTPBadRequest(text=f"Failed to terminate contract: {contract_id}")

            # Redirect to the contract detail page
            return web.HTTPFound(f"/contracts/{contract_id}")

        except Exception as e:
            logger.exception(f"Error terminating contract: {e}")
            return web.HTTPInternalServerError(text=f"Error terminating contract: {e}")

    # --- Zero-Knowledge Proof Handlers ---

    @aiohttp_jinja2.template('zkp.html')
    async def handle_zkp(self, request):
        """Handle the zero-knowledge proofs page."""
        return {
            'title': 'Zero-Knowledge Proofs - PoRW Blockchain',
            'wallet': WALLET
        }

    async def handle_zkp_confidential_transaction(self, request):
        """Handle creating a confidential transaction with ZKP."""
        global WALLET, NODE

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction details from the form
        data = await request.post()
        recipient = data.get('recipient')
        amount = data.get('amount')
        memo = data.get('memo', '')

        if not recipient or not amount:
            return web.HTTPBadRequest(text="Recipient and amount are required")

        try:
            # Convert amount to float
            amount = float(amount)

            # Create confidential transaction with ZKP
            transaction = WALLET.create_confidential_transaction_with_zkp(
                recipient=recipient,
                amount=amount,
                memo=memo if memo else None
            )

            # Broadcast the transaction
            if NODE:
                await NODE.broadcast_transaction(transaction)

            # Redirect to the wallet page
            return web.HTTPFound('/wallet')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error creating confidential transaction: {e}")

    async def handle_zkp_identity_proof(self, request):
        """Handle creating an identity proof."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the identity data from the form
        data = await request.post()
        name = data.get('name')
        age = data.get('age')
        country = data.get('country')
        id_number = data.get('id_number')
        public_attributes = data.getall('public_attributes')

        if not name or not age or not country or not id_number:
            return web.HTTPBadRequest(text="All identity fields are required")

        try:
            # Convert age to int
            age = int(age)

            # Create identity data
            identity_data = {
                'name': name,
                'age': age,
                'country': country,
                'id_number': id_number
            }

            # Create identity proof
            identity_proof = WALLET.create_identity_proof(
                identity_data=identity_data,
                public_attributes=public_attributes
            )

            # Return the proof as JSON
            return web.json_response(identity_proof)

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error creating identity proof: {e}")

    async def handle_zkp_contract_proof(self, request):
        """Handle creating a private contract proof."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the contract data from the form
        data = await request.post()
        contract_code = data.get('contract_code')
        contract_inputs_str = data.get('contract_inputs')
        private_inputs_str = data.get('private_inputs')

        if not contract_code or not contract_inputs_str or not private_inputs_str:
            return web.HTTPBadRequest(text="All contract fields are required")

        try:
            # Parse JSON inputs
            import json
            contract_inputs = json.loads(contract_inputs_str)
            private_inputs = json.loads(private_inputs_str)

            # Create contract state (simplified for demo)
            contract_state = {
                'balance': 100.0,
                'owner': WALLET.address,
                'created_at': int(time.time())
            }

            # Create contract proof
            contract_proof = WALLET.create_private_contract_proof(
                contract_code=contract_code,
                contract_state=contract_state,
                contract_inputs=contract_inputs,
                private_inputs=private_inputs
            )

            # Return the proof as JSON
            return web.json_response(contract_proof)

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error creating contract proof: {e}")

    async def handle_zkp_protein_proof(self, request):
        """Handle creating a protein folding proof."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the protein data from the form
        data = await request.post()
        protein_sequence = data.get('protein_sequence')
        folding_result_str = data.get('folding_result')
        folding_parameters_str = data.get('folding_parameters')

        if not protein_sequence or not folding_result_str or not folding_parameters_str:
            return web.HTTPBadRequest(text="All protein folding fields are required")

        try:
            # Parse JSON inputs
            import json
            folding_result = json.loads(folding_result_str)
            folding_parameters = json.loads(folding_parameters_str)

            # Create protein folding proof
            folding_proof = WALLET.create_protein_folding_proof(
                protein_sequence=protein_sequence,
                folding_result=folding_result,
                folding_parameters=folding_parameters
            )

            # Return the proof as JSON
            return web.json_response(folding_proof)

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error creating protein folding proof: {e}")

    async def handle_zkp_verify(self, request):
        """Handle verifying a zero-knowledge proof."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the proof from the form
        data = await request.post()
        proof_json = data.get('proof_json')

        if not proof_json:
            return web.HTTPBadRequest(text="Proof JSON is required")

        try:
            # Import verify_proof function
            from ..privacy.zkp import verify_proof

            # Verify the proof
            is_valid = verify_proof(proof_json)

            # Return the verification result
            return web.json_response({
                'is_valid': is_valid,
                'message': "Proof is valid" if is_valid else "Proof is invalid"
            })

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error verifying proof: {e}")

    # --- Stealth Address Handlers ---

    @aiohttp_jinja2.template('stealth.html')
    async def handle_stealth(self, request):
        """Handle the stealth address page."""
        global WALLET

        stealth_address = None
        stealth_payments = []

        if WALLET:
            try:
                # Get stealth address if available
                try:
                    stealth_address = WALLET.get_stealth_address()
                except ValueError:
                    # No stealth address yet
                    pass

                # Get stealth payments if available
                if stealth_address:
                    try:
                        stealth_payments = await WALLET.scan_for_stealth_payments()
                    except Exception as e:
                        logger.error(f"Error scanning for stealth payments: {e}")
            except Exception as e:
                logger.error(f"Error getting stealth data: {e}")

        return {
            'title': 'Stealth Addresses - PoRW Blockchain',
            'wallet': WALLET,
            'stealth_address': stealth_address,
            'stealth_payments': stealth_payments
        }

    async def handle_stealth_create(self, request):
        """Handle creating a stealth address."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        try:
            # Create stealth keys
            stealth_data = WALLET.create_stealth_keys()

            # Redirect to the stealth page
            return web.HTTPFound('/stealth')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error creating stealth address: {e}")

    async def handle_stealth_send(self, request):
        """Handle sending to a stealth address."""
        global WALLET, NODE

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction details from the form
        data = await request.post()
        recipient_stealth_address = data.get('recipient_stealth_address')
        amount = data.get('amount')
        memo = data.get('memo', '')

        if not recipient_stealth_address or not amount:
            return web.HTTPBadRequest(text="Recipient stealth address and amount are required")

        try:
            # Convert amount to float
            amount = float(amount)

            # Create and submit stealth payment
            response = await WALLET.create_and_submit_stealth_payment(
                recipient_stealth_address=recipient_stealth_address,
                amount=amount,
                memo=memo if memo else None
            )

            # Redirect to the wallet page
            return web.HTTPFound('/wallet')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error sending to stealth address: {e}")

    async def handle_api_stealth_scan(self, request):
        """Handle API stealth scan request."""
        global WALLET

        if not WALLET:
            return web.json_response({'error': 'No wallet found'}, status=400)

        try:
            # Scan for stealth payments
            payments = await WALLET.scan_for_stealth_payments()

            # Return the payments
            return web.json_response({
                'payments': payments
            })

        except Exception as e:
            return web.json_response({'error': f'Error scanning for stealth payments: {e}'}, status=500)

    # --- Mixing Handlers ---

    @aiohttp_jinja2.template('mixing.html')
    async def handle_mixing(self, request):
        """Handle the mixing page."""
        global WALLET

        active_sessions = []
        my_sessions = []

        if WALLET and WALLET.mixing_wallet:
            try:
                # Get active sessions
                active_sessions = await WALLET.get_active_mixing_sessions()

                # Get my sessions
                my_sessions = await WALLET.get_my_mixing_sessions()
            except Exception as e:
                logger.error(f"Error getting mixing data: {e}")

        return {
            'title': 'Coin Mixing - PoRW Blockchain',
            'wallet': WALLET,
            'active_sessions': active_sessions,
            'my_sessions': my_sessions
        }

    async def handle_mixing_create(self, request):
        """Handle creating a mixing session."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the session details from the form
        data = await request.post()
        denomination = data.get('denomination')
        min_participants = data.get('min_participants')
        max_participants = data.get('max_participants')
        fee_percent = data.get('fee_percent')

        if not denomination:
            return web.HTTPBadRequest(text="Denomination is required")

        try:
            # Convert parameters to appropriate types
            denomination = float(denomination)
            min_participants = int(min_participants) if min_participants else 3
            max_participants = int(max_participants) if max_participants else 20
            fee_percent = float(fee_percent) if fee_percent else 0.005

            # Create mixing session
            session = await WALLET.create_mixing_session(
                denomination=denomination,
                min_participants=min_participants,
                max_participants=max_participants,
                fee_percent=fee_percent
            )

            # Redirect to the mixing page
            return web.HTTPFound('/mixing')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error creating mixing session: {e}")

    async def handle_mixing_join(self, request):
        """Handle joining a mixing session."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the session details from the form
        data = await request.post()
        session_id = data.get('session_id')
        output_address = data.get('output_address')

        if not session_id:
            return web.HTTPBadRequest(text="Session ID is required")

        try:
            # Join mixing session
            participant = await WALLET.join_mixing_session(
                session_id=session_id,
                output_address=output_address if output_address else None
            )

            # Redirect to the mixing page
            return web.HTTPFound('/mixing')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error joining mixing session: {e}")

    async def handle_mixing_session(self, request):
        """Handle viewing a mixing session."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the session ID from the URL
        session_id = request.match_info['session_id']

        try:
            # Get session status
            session = await WALLET.get_mixing_session_status(session_id)

            # Get my participants in this session
            participants = await WALLET.mixing_wallet.get_my_participants(session_id)

            # Render the session page
            return aiohttp_jinja2.render_template(
                'mixing_session.html',
                request,
                {
                    'title': f'Mixing Session {session_id} - PoRW Blockchain',
                    'wallet': WALLET,
                    'session': session,
                    'participants': participants
                }
            )

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error getting mixing session: {e}")

    async def handle_api_mixing_active_sessions(self, request):
        """Handle API active mixing sessions request."""
        global WALLET

        if not WALLET:
            return web.json_response({'error': 'No wallet found'}, status=400)

        try:
            # Get active sessions
            sessions = await WALLET.get_active_mixing_sessions()

            # Return the sessions
            return web.json_response({
                'sessions': sessions
            })

        except Exception as e:
            return web.json_response({'error': f'Error getting active mixing sessions: {e}'}, status=500)

    async def handle_api_mixing_my_sessions(self, request):
        """Handle API my mixing sessions request."""
        global WALLET

        if not WALLET:
            return web.json_response({'error': 'No wallet found'}, status=400)

        try:
            # Get my sessions
            sessions = await WALLET.get_my_mixing_sessions()

            # Return the sessions
            return web.json_response({
                'sessions': sessions
            })

        except Exception as e:
            return web.json_response({'error': f'Error getting my mixing sessions: {e}'}, status=500)

    async def handle_api_mixing_get_signature(self, request):
        """Handle API get blind signature request."""
        global WALLET

        if not WALLET:
            return web.json_response({'error': 'No wallet found'}, status=400)

        # Get the session ID and participant ID from the query
        session_id = request.query.get('session_id')
        participant_id = request.query.get('participant_id')

        if not session_id or not participant_id:
            return web.json_response({'error': 'Session ID and participant ID are required'}, status=400)

        try:
            # Get blind signature
            signature = await WALLET.get_blind_signature(
                session_id=session_id,
                participant_id=participant_id
            )

            # Return the signature
            return web.json_response(signature)

        except Exception as e:
            return web.json_response({'error': f'Error getting blind signature: {e}'}, status=500)

    async def handle_api_mixing_sign_transaction(self, request):
        """Handle API sign transaction request."""
        global WALLET

        if not WALLET:
            return web.json_response({'error': 'No wallet found'}, status=400)

        # Get the session ID and participant ID from the query
        session_id = request.query.get('session_id')
        participant_id = request.query.get('participant_id')

        if not session_id or not participant_id:
            return web.json_response({'error': 'Session ID and participant ID are required'}, status=400)

        try:
            # Sign transaction
            signature = await WALLET.sign_coinjoin_transaction(
                session_id=session_id,
                participant_id=participant_id
            )

            # Return the signature
            return web.json_response(signature)

        except Exception as e:
            return web.json_response({'error': f'Error signing transaction: {e}'}, status=500)

    async def handle_api_mixing_submit_transaction(self, request):
        """Handle API submit transaction request."""
        global WALLET

        if not WALLET:
            return web.json_response({'error': 'No wallet found'}, status=400)

        # Get the session ID from the query
        session_id = request.query.get('session_id')

        if not session_id:
            return web.json_response({'error': 'Session ID is required'}, status=400)

        try:
            # Submit transaction
            response = await WALLET.submit_coinjoin_transaction(session_id)

            # Return the response
            return web.json_response(response)

        except Exception as e:
            return web.json_response({'error': f'Error submitting transaction: {e}'}, status=500)

    # --- Multi-Signature Wallet Handlers ---

    @aiohttp_jinja2.template('multisig.html')
    async def handle_multisig(self, request):
        """Handle the multi-signature wallets page."""
        global WALLET

        multisig_wallets = []

        if WALLET:
            try:
                # Get multisig wallets
                multisig_wallets = WALLET.list_multisig_wallets()
            except Exception as e:
                logger.error(f"Error getting multisig wallets: {e}")

        return {
            'title': 'Multi-Signature Wallets - PoRW Blockchain',
            'wallet': WALLET,
            'multisig_wallets': multisig_wallets
        }

    async def handle_multisig_create(self, request):
        """Handle creating a multi-signature wallet."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the wallet details from the form
        data = await request.post()
        required_signatures = data.get('required_signatures')
        total_signers = data.get('total_signers')
        public_keys_text = data.get('public_keys')
        description = data.get('description')

        if not required_signatures or not total_signers:
            return web.HTTPBadRequest(text="Required signatures and total signers are required")

        try:
            # Convert parameters to appropriate types
            required_signatures = int(required_signatures)
            total_signers = int(total_signers)

            # Parse public keys
            public_keys = None
            if public_keys_text:
                public_keys = [key.strip() for key in public_keys_text.split('\n') if key.strip()]

            # Create multisig wallet
            wallet_data = WALLET.create_multisig_wallet(
                required_signatures=required_signatures,
                total_signers=total_signers,
                public_keys=public_keys,
                description=description
            )

            # Redirect to the multisig page
            return web.HTTPFound('/multisig')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error creating multisig wallet: {e}")

    async def handle_multisig_join(self, request):
        """Handle joining a multi-signature wallet."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the wallet data from the form
        data = await request.post()
        wallet_data_text = data.get('wallet_data')

        if not wallet_data_text:
            return web.HTTPBadRequest(text="Wallet data is required")

        try:
            # Parse wallet data
            import json
            wallet_data = json.loads(wallet_data_text)

            # Join multisig wallet
            joined_wallet = WALLET.join_multisig_wallet(wallet_data)

            # Redirect to the multisig page
            return web.HTTPFound('/multisig')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error joining multisig wallet: {e}")

    @aiohttp_jinja2.template('multisig_wallet.html')
    async def handle_multisig_wallet(self, request):
        """Handle viewing a multi-signature wallet."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the wallet ID from the URL
        wallet_id = request.match_info['wallet_id']

        try:
            # Get wallet data
            wallet = WALLET.get_multisig_wallet(wallet_id)

            # Get pending transactions
            pending_transactions = wallet.get('pending_transactions', {})

            # Render the wallet page
            return {
                'title': f'Multi-Signature Wallet {wallet_id} - PoRW Blockchain',
                'wallet': wallet,
                'pending_transactions': pending_transactions
            }

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error getting multisig wallet: {e}")

    async def handle_multisig_add_key(self, request):
        """Handle adding a public key to a multi-signature wallet."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the wallet ID from the URL
        wallet_id = request.match_info['wallet_id']

        # Get the public key from the form
        data = await request.post()
        public_key = data.get('public_key')

        if not public_key:
            return web.HTTPBadRequest(text="Public key is required")

        try:
            # Get wallet
            if wallet_id not in WALLET.multisig_wallets:
                return web.HTTPBadRequest(text=f"Multisig wallet {wallet_id} not found")

            # Add public key
            WALLET.multisig_wallets[wallet_id].add_public_key(public_key)

            # Update wallet data
            WALLET.wallet_data["multisig_wallets"][wallet_id] = WALLET.multisig_wallets[wallet_id].to_dict()

            # Save wallet if auto_save is enabled
            if WALLET.auto_save and WALLET.wallet_password:
                WALLET.save_wallet(WALLET.wallet_password)

            # Redirect to the wallet page
            return web.HTTPFound(f'/multisig/wallet/{wallet_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error adding public key: {e}")

    async def handle_multisig_create_transaction(self, request):
        """Handle creating a transaction for a multi-signature wallet."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the wallet ID from the URL
        wallet_id = request.match_info['wallet_id']

        # Get the transaction details from the form
        data = await request.post()
        recipient = data.get('recipient')
        amount = data.get('amount')
        fee = data.get('fee')
        memo = data.get('memo')

        if not recipient or not amount:
            return web.HTTPBadRequest(text="Recipient and amount are required")

        try:
            # Convert amount to float
            amount = float(amount)
            fee = float(fee) if fee else None

            # Create transaction
            transaction = WALLET.create_multisig_transaction(
                wallet_id=wallet_id,
                recipient=recipient,
                amount=amount,
                fee=fee,
                memo=memo if memo else None
            )

            # Redirect to the transaction page
            return web.HTTPFound(f'/multisig/wallet/{wallet_id}/transaction/{transaction["transaction_id"]}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error creating transaction: {e}")

    async def handle_multisig_sign_transaction(self, request):
        """Handle signing a multi-signature transaction."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the wallet ID from the URL
        wallet_id = request.match_info['wallet_id']

        # Get the transaction ID from the form
        data = await request.post()
        transaction_id = data.get('transaction_id')

        if not transaction_id:
            return web.HTTPBadRequest(text="Transaction ID is required")

        try:
            # Sign transaction
            transaction = WALLET.sign_multisig_transaction(
                wallet_id=wallet_id,
                transaction_id=transaction_id
            )

            # Redirect to the transaction page
            return web.HTTPFound(f'/multisig/wallet/{wallet_id}/transaction/{transaction_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error signing transaction: {e}")

    async def handle_multisig_submit_transaction(self, request):
        """Handle submitting a multi-signature transaction."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the wallet ID from the URL
        wallet_id = request.match_info['wallet_id']

        # Get the transaction ID from the form
        data = await request.post()
        transaction_id = data.get('transaction_id')

        if not transaction_id:
            return web.HTTPBadRequest(text="Transaction ID is required")

        try:
            # Verify transaction
            if not WALLET.verify_multisig_transaction(wallet_id, transaction_id):
                return web.HTTPBadRequest(text="Transaction does not have enough signatures")

            # Submit transaction
            await WALLET.finalize_and_submit_multisig_transaction(
                wallet_id=wallet_id,
                transaction_id=transaction_id
            )

            # Redirect to the wallet page
            return web.HTTPFound(f'/multisig/wallet/{wallet_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error submitting transaction: {e}")

    @aiohttp_jinja2.template('multisig_transaction.html')
    async def handle_multisig_transaction(self, request):
        """Handle viewing a multi-signature transaction."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the wallet ID and transaction ID from the URL
        wallet_id = request.match_info['wallet_id']
        transaction_id = request.match_info['transaction_id']

        try:
            # Get wallet
            wallet = WALLET.get_multisig_wallet(wallet_id)

            # Get transaction
            if transaction_id not in wallet.get('pending_transactions', {}):
                return web.HTTPBadRequest(text=f"Transaction {transaction_id} not found")

            transaction = wallet['pending_transactions'][transaction_id]

            # Render the transaction page
            return {
                'title': f'Multi-Signature Transaction {transaction_id} - PoRW Blockchain',
                'wallet': wallet,
                'transaction': transaction
            }

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error getting transaction: {e}")

    async def handle_api_multisig_wallet(self, request):
        """Handle API multisig wallet request."""
        global WALLET

        if not WALLET:
            return web.json_response({'error': 'No wallet found'}, status=400)

        # Get the wallet ID from the URL
        wallet_id = request.match_info['wallet_id']

        try:
            # Get wallet data
            wallet = WALLET.get_multisig_wallet(wallet_id)

            # Return the wallet data
            return web.json_response(wallet)

        except Exception as e:
            return web.json_response({'error': f'Error getting multisig wallet: {e}'}, status=500)

    # --- Address Book Handlers ---

    @aiohttp_jinja2.template('contacts.html')
    async def handle_contacts(self, request):
        """Handle the address book page."""
        global WALLET

        contacts = []
        all_tags = []
        query = request.query.get('query', '')
        tags_param = request.query.getall('tags', [])

        if WALLET:
            try:
                # Get all tags for filter dropdown
                all_tags = WALLET.get_all_tags()

                # Search contacts based on query and tags
                if query or tags_param:
                    contacts = WALLET.search_contacts(query=query, tags=tags_param if tags_param else None)
                else:
                    # List all contacts
                    contacts = WALLET.list_contacts()
            except Exception as e:
                logger.error(f"Error getting contacts: {e}")

        return {
            'title': 'Address Book - PoRW Blockchain',
            'wallet': WALLET,
            'contacts': contacts,
            'all_tags': all_tags,
            'query': query,
            'selected_tags': tags_param
        }

    async def handle_contacts_add(self, request):
        """Handle adding a contact."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the contact details from the form
        data = await request.post()
        name = data.get('name')
        address = data.get('address')
        email = data.get('email')
        phone = data.get('phone')
        description = data.get('description')
        tags_text = data.get('tags')

        if not name or not address:
            return web.HTTPBadRequest(text="Name and address are required")

        try:
            # Parse tags
            tags = None
            if tags_text:
                tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]

            # Add contact
            WALLET.add_contact(
                name=name,
                address=address,
                email=email if email else None,
                phone=phone if phone else None,
                description=description if description else None,
                tags=tags
            )

            # Redirect to the contacts page
            return web.HTTPFound('/contacts')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error adding contact: {e}")

    async def handle_contacts_delete(self, request):
        """Handle deleting a contact."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the contact ID from the form
        data = await request.post()
        contact_id = data.get('contact_id')

        if not contact_id:
            return web.HTTPBadRequest(text="Contact ID is required")

        try:
            # Remove contact
            WALLET.remove_contact(contact_id)

            # Redirect to the contacts page
            return web.HTTPFound('/contacts')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error deleting contact: {e}")

    @aiohttp_jinja2.template('contact_detail.html')
    async def handle_contact_detail(self, request):
        """Handle viewing a contact."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the contact ID from the URL
        contact_id = request.match_info['contact_id']

        try:
            # Get contact
            contact = WALLET.get_contact(contact_id)

            # Render the contact page
            return {
                'title': f'Contact: {contact["name"]} - PoRW Blockchain',
                'wallet': WALLET,
                'contact': contact
            }

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error getting contact: {e}")

    @aiohttp_jinja2.template('contact_edit.html')
    async def handle_contact_edit(self, request):
        """Handle editing a contact."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the contact ID from the URL
        contact_id = request.match_info['contact_id']

        try:
            # Get contact
            contact = WALLET.get_contact(contact_id)

            # Render the edit page
            return {
                'title': f'Edit Contact: {contact["name"]} - PoRW Blockchain',
                'wallet': WALLET,
                'contact': contact
            }

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error getting contact: {e}")

    async def handle_contact_update(self, request):
        """Handle updating a contact."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the contact ID from the URL
        contact_id = request.match_info['contact_id']

        # Get the contact details from the form
        data = await request.post()
        name = data.get('name')
        address = data.get('address')
        email = data.get('email')
        phone = data.get('phone')
        description = data.get('description')
        tags_text = data.get('tags')

        if not name or not address:
            return web.HTTPBadRequest(text="Name and address are required")

        try:
            # Parse tags
            tags = None
            if tags_text:
                tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]

            # Update contact
            WALLET.update_contact(
                contact_id=contact_id,
                name=name,
                address=address,
                email=email if email else None,
                phone=phone if phone else None,
                description=description if description else None,
                tags=tags
            )

            # Redirect to the contact detail page
            return web.HTTPFound(f'/contacts/{contact_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error updating contact: {e}")

    async def handle_contact_add_tag(self, request):
        """Handle adding a tag to a contact."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the contact ID from the URL
        contact_id = request.match_info['contact_id']

        # Get the tag from the form
        data = await request.post()
        tag = data.get('tag')

        if not tag:
            return web.HTTPBadRequest(text="Tag is required")

        try:
            # Add tag to contact
            WALLET.add_tag_to_contact(contact_id, tag)

            # Redirect to the contact detail page
            return web.HTTPFound(f'/contacts/{contact_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error adding tag: {e}")

    async def handle_contact_remove_tag(self, request):
        """Handle removing a tag from a contact."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the contact ID from the URL
        contact_id = request.match_info['contact_id']

        # Get the tag from the form
        data = await request.post()
        tag = data.get('tag')

        if not tag:
            return web.HTTPBadRequest(text="Tag is required")

        try:
            # Remove tag from contact
            WALLET.remove_tag_from_contact(contact_id, tag)

            # Redirect to the contact detail page
            return web.HTTPFound(f'/contacts/{contact_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error removing tag: {e}")

    # --- Transaction Labeling Handlers ---

    @aiohttp_jinja2.template('transaction.html')
    async def handle_transaction_detail(self, request):
        """Handle viewing a transaction."""
        global WALLET, BLOCKCHAIN

        # Get the transaction ID from the URL
        transaction_id = request.match_info['transaction_id']

        try:
            # Get transaction
            transaction = None

            # Try to get from blockchain
            if BLOCKCHAIN:
                transaction = BLOCKCHAIN.get_transaction(transaction_id)

            # If not found in blockchain, try to get from wallet
            if not transaction and WALLET:
                transactions = await WALLET.get_transactions()
                for tx in transactions:
                    if tx.get('transaction_id') == transaction_id:
                        transaction = tx
                        break

            if not transaction:
                return web.HTTPBadRequest(text=f"Transaction {transaction_id} not found")

            # Get transaction label if exists
            label = None
            all_categories = []
            if WALLET:
                label = WALLET.get_transaction_label(transaction_id)
                all_categories = WALLET.get_all_transaction_categories()

            # Render the transaction page
            return {
                'title': f'Transaction {transaction_id} - PoRW Blockchain',
                'wallet': WALLET,
                'transaction': transaction,
                'label': label,
                'all_categories': all_categories
            }

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error getting transaction: {e}")

    @aiohttp_jinja2.template('transaction_labels.html')
    async def handle_transaction_labels(self, request):
        """Handle the transaction labels page."""
        global WALLET

        transaction_labels = []
        all_categories = []
        all_tags = []
        query = request.query.get('query', '')
        category = request.query.get('category', '')
        tags_param = request.query.getall('tags', [])

        if WALLET:
            try:
                # Get all categories and tags for filter dropdowns
                all_categories = WALLET.get_all_transaction_categories()
                all_tags = WALLET.get_all_transaction_tags()

                # Search transaction labels based on query, category, and tags
                if query or category or tags_param:
                    transaction_labels = WALLET.search_transaction_labels(
                        query=query if query else None,
                        category=category if category else None,
                        tags=tags_param if tags_param else None
                    )
                else:
                    # List all transaction labels
                    transaction_labels = WALLET.list_transaction_labels()
            except Exception as e:
                logger.error(f"Error getting transaction labels: {e}")

        return {
            'title': 'Transaction Labels - PoRW Blockchain',
            'wallet': WALLET,
            'transaction_labels': transaction_labels,
            'all_categories': all_categories,
            'all_tags': all_tags,
            'query': query,
            'category': category,
            'selected_tags': tags_param
        }

    async def handle_transaction_label_add(self, request):
        """Handle adding a transaction label."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction label details from the form
        data = await request.post()
        transaction_id = data.get('transaction_id')
        label = data.get('label')
        category = data.get('category')
        notes = data.get('notes')
        tags_text = data.get('tags')

        if not transaction_id:
            return web.HTTPBadRequest(text="Transaction ID is required")

        try:
            # Parse tags
            tags = None
            if tags_text:
                tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]

            # Add transaction label
            WALLET.add_transaction_label(
                transaction_id=transaction_id,
                label=label if label else None,
                category=category if category else None,
                notes=notes if notes else None,
                tags=tags
            )

            # Redirect to the transaction detail page
            return web.HTTPFound(f'/transactions/{transaction_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error adding transaction label: {e}")

    async def handle_transaction_label_delete(self, request):
        """Handle deleting a transaction label."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction ID from the form
        data = await request.post()
        transaction_id = data.get('transaction_id')

        if not transaction_id:
            return web.HTTPBadRequest(text="Transaction ID is required")

        try:
            # Remove transaction label
            WALLET.remove_transaction_label(transaction_id)

            # Redirect to the transaction detail page
            return web.HTTPFound(f'/transactions/{transaction_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error deleting transaction label: {e}")

    @aiohttp_jinja2.template('transaction_label_detail.html')
    async def handle_transaction_label_detail(self, request):
        """Handle viewing a transaction label."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction ID from the URL
        transaction_id = request.match_info['transaction_id']

        try:
            # Get transaction label
            label = WALLET.get_transaction_label(transaction_id)

            if not label:
                return web.HTTPBadRequest(text=f"Transaction label for {transaction_id} not found")

            # Render the transaction label page
            return {
                'title': f'Transaction Label: {label["label"] or transaction_id} - PoRW Blockchain',
                'wallet': WALLET,
                'label': label
            }

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error getting transaction label: {e}")

    @aiohttp_jinja2.template('transaction_label_edit.html')
    async def handle_transaction_label_edit(self, request):
        """Handle editing a transaction label."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction ID from the URL
        transaction_id = request.match_info['transaction_id']

        try:
            # Get transaction label
            label = WALLET.get_transaction_label(transaction_id)

            if not label:
                return web.HTTPBadRequest(text=f"Transaction label for {transaction_id} not found")

            # Get all categories for dropdown
            all_categories = WALLET.get_all_transaction_categories()

            # Render the edit page
            return {
                'title': f'Edit Transaction Label: {label["label"] or transaction_id} - PoRW Blockchain',
                'wallet': WALLET,
                'label': label,
                'all_categories': all_categories
            }

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error getting transaction label: {e}")

    async def handle_transaction_label_update(self, request):
        """Handle updating a transaction label."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction ID from the URL
        transaction_id = request.match_info['transaction_id']

        # Get the transaction label details from the form
        data = await request.post()
        label = data.get('label')
        category = data.get('category')
        notes = data.get('notes')
        tags_text = data.get('tags')

        try:
            # Parse tags
            tags = None
            if tags_text:
                tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]

            # Update transaction label
            WALLET.update_transaction_label(
                transaction_id=transaction_id,
                label=label if label else None,
                category=category if category else None,
                notes=notes if notes else None,
                tags=tags
            )

            # Redirect to the transaction label detail page
            return web.HTTPFound(f'/transactions/labels/{transaction_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error updating transaction label: {e}")

    async def handle_transaction_label_add_tag(self, request):
        """Handle adding a tag to a transaction label."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction ID from the URL
        transaction_id = request.match_info['transaction_id']

        # Get the tag from the form
        data = await request.post()
        tag = data.get('tag')

        if not tag:
            return web.HTTPBadRequest(text="Tag is required")

        try:
            # Add tag to transaction label
            WALLET.add_tag_to_transaction_label(transaction_id, tag)

            # Redirect to the transaction label detail page
            return web.HTTPFound(f'/transactions/labels/{transaction_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error adding tag: {e}")

    async def handle_transaction_label_remove_tag(self, request):
        """Handle removing a tag from a transaction label."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction ID from the URL
        transaction_id = request.match_info['transaction_id']

        # Get the tag from the form
        data = await request.post()
        tag = data.get('tag')

        if not tag:
            return web.HTTPBadRequest(text="Tag is required")

        try:
            # Remove tag from transaction label
            WALLET.remove_tag_from_transaction_label(transaction_id, tag)

            # Redirect to the transaction label detail page
            return web.HTTPFound(f'/transactions/labels/{transaction_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error removing tag: {e}")

    # --- Recurring Transaction Handlers ---

    @aiohttp_jinja2.template('recurring.html')
    async def handle_recurring(self, request):
        """Handle the recurring transactions page."""
        global WALLET

        recurring_transactions = []
        due_transactions = []

        if WALLET:
            try:
                # List all recurring transactions
                recurring_transactions = WALLET.list_recurring_transactions()

                # Get due transactions
                due_transactions = WALLET.get_due_recurring_transactions()
            except Exception as e:
                logger.error(f"Error getting recurring transactions: {e}")

        return {
            'title': 'Recurring Transactions - PoRW Blockchain',
            'wallet': WALLET,
            'recurring_transactions': recurring_transactions,
            'due_transactions': due_transactions
        }

    async def handle_recurring_create(self, request):
        """Handle creating a recurring transaction."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the recurring transaction details from the form
        data = await request.post()
        recipient = data.get('recipient')
        amount = data.get('amount')
        interval = data.get('interval')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        custom_days = data.get('custom_days')
        memo = data.get('memo')
        fee = data.get('fee')
        enabled = data.get('enabled') == 'true'
        max_executions = data.get('max_executions')

        if not recipient or not amount or not interval:
            return web.HTTPBadRequest(text="Recipient, amount, and interval are required")

        try:
            # Convert amount to float
            amount = float(amount)

            # Convert fee to float if provided
            fee = float(fee) if fee else None

            # Convert custom_days to int if provided
            custom_days = int(custom_days) if custom_days else None

            # Convert max_executions to int if provided
            max_executions = int(max_executions) if max_executions else None

            # Convert start_date and end_date to timestamps if provided
            start_date = None
            if start_date_str:
                start_date = int(datetime.strptime(start_date_str, '%Y-%m-%d').timestamp())

            end_date = None
            if end_date_str:
                end_date = int(datetime.strptime(end_date_str, '%Y-%m-%d').timestamp())

            # Create recurring transaction
            WALLET.create_recurring_transaction(
                recipient=recipient,
                amount=amount,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                custom_days=custom_days,
                memo=memo if memo else None,
                fee=fee,
                enabled=enabled,
                max_executions=max_executions
            )

            # Redirect to the recurring transactions page
            return web.HTTPFound('/recurring')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error creating recurring transaction: {e}")

    async def handle_recurring_delete(self, request):
        """Handle deleting a recurring transaction."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction ID from the form
        data = await request.post()
        transaction_id = data.get('transaction_id')

        if not transaction_id:
            return web.HTTPBadRequest(text="Transaction ID is required")

        try:
            # Remove recurring transaction
            WALLET.remove_recurring_transaction(transaction_id)

            # Redirect to the recurring transactions page
            return web.HTTPFound('/recurring')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error deleting recurring transaction: {e}")

    @aiohttp_jinja2.template('recurring_detail.html')
    async def handle_recurring_detail(self, request):
        """Handle viewing a recurring transaction."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction ID from the URL
        transaction_id = request.match_info['transaction_id']

        try:
            # Get recurring transaction
            transaction = WALLET.get_recurring_transaction(transaction_id)

            if not transaction:
                return web.HTTPBadRequest(text=f"Recurring transaction {transaction_id} not found")

            # Render the recurring transaction page
            return {
                'title': f'Recurring Transaction: {transaction_id} - PoRW Blockchain',
                'wallet': WALLET,
                'transaction': transaction
            }

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error getting recurring transaction: {e}")

    @aiohttp_jinja2.template('recurring_edit.html')
    async def handle_recurring_edit(self, request):
        """Handle editing a recurring transaction."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction ID from the URL
        transaction_id = request.match_info['transaction_id']

        try:
            # Get recurring transaction
            transaction = WALLET.get_recurring_transaction(transaction_id)

            if not transaction:
                return web.HTTPBadRequest(text=f"Recurring transaction {transaction_id} not found")

            # Render the edit page
            return {
                'title': f'Edit Recurring Transaction: {transaction_id} - PoRW Blockchain',
                'wallet': WALLET,
                'transaction': transaction
            }

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error getting recurring transaction: {e}")

    async def handle_recurring_update(self, request):
        """Handle updating a recurring transaction."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction ID from the URL
        transaction_id = request.match_info['transaction_id']

        # Get the recurring transaction details from the form
        data = await request.post()
        recipient = data.get('recipient')
        amount = data.get('amount')
        interval = data.get('interval')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        custom_days = data.get('custom_days')
        memo = data.get('memo')
        fee = data.get('fee')
        enabled = data.get('enabled') == 'true'
        max_executions = data.get('max_executions')

        if not recipient or not amount or not interval:
            return web.HTTPBadRequest(text="Recipient, amount, and interval are required")

        try:
            # Convert amount to float
            amount = float(amount)

            # Convert fee to float if provided
            fee = float(fee) if fee else None

            # Convert custom_days to int if provided
            custom_days = int(custom_days) if custom_days else None

            # Convert max_executions to int if provided
            max_executions = int(max_executions) if max_executions else None

            # Convert start_date and end_date to timestamps if provided
            start_date = None
            if start_date_str:
                start_date = int(datetime.strptime(start_date_str, '%Y-%m-%d').timestamp())

            end_date = None
            if end_date_str:
                end_date = int(datetime.strptime(end_date_str, '%Y-%m-%d').timestamp())

            # Update recurring transaction
            WALLET.update_recurring_transaction(
                transaction_id=transaction_id,
                recipient=recipient,
                amount=amount,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                custom_days=custom_days,
                memo=memo if memo else None,
                fee=fee,
                enabled=enabled,
                max_executions=max_executions
            )

            # Redirect to the recurring transaction detail page
            return web.HTTPFound(f'/recurring/{transaction_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error updating recurring transaction: {e}")

    async def handle_recurring_enable(self, request):
        """Handle enabling a recurring transaction."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction ID from the URL
        transaction_id = request.match_info['transaction_id']

        try:
            # Enable recurring transaction
            WALLET.enable_recurring_transaction(transaction_id)

            # Redirect to the recurring transaction detail page
            return web.HTTPFound(f'/recurring/{transaction_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error enabling recurring transaction: {e}")

    async def handle_recurring_disable(self, request):
        """Handle disabling a recurring transaction."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction ID from the URL
        transaction_id = request.match_info['transaction_id']

        try:
            # Disable recurring transaction
            WALLET.disable_recurring_transaction(transaction_id)

            # Redirect to the recurring transaction detail page
            return web.HTTPFound(f'/recurring/{transaction_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error disabling recurring transaction: {e}")

    async def handle_recurring_execute(self, request):
        """Handle executing a recurring transaction."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        # Get the transaction ID from the URL
        transaction_id = request.match_info['transaction_id']

        try:
            # Execute recurring transaction
            await WALLET.execute_recurring_transaction(transaction_id)

            # Redirect to the recurring transaction detail page
            return web.HTTPFound(f'/recurring/{transaction_id}')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error executing recurring transaction: {e}")

    async def handle_recurring_execute_all(self, request):
        """Handle executing all due recurring transactions."""
        global WALLET

        # Check if wallet exists
        if not WALLET:
            return web.HTTPBadRequest(text="No wallet found")

        try:
            # Execute all due recurring transactions
            await WALLET.execute_due_transactions()

            # Redirect to the recurring transactions page
            return web.HTTPFound('/recurring')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error executing due transactions: {e}")

def main():
    """Main entry point for the web interface."""
    import argparse

    parser = argparse.ArgumentParser(description='PoRW Blockchain Web Interface')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--data-dir', type=Path, help='Data directory for the blockchain')

    args = parser.parse_args()

    # Create and run the web interface
    web_interface = WebInterface(
        host=args.host,
        port=args.port,
        data_dir=args.data_dir
    )

    asyncio.run(web_interface.run())


if __name__ == '__main__':
    main()
