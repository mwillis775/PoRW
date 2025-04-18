#!/usr/bin/env python3
"""
Simple web interface for the PoRW blockchain system.
"""

import asyncio
import json
import logging
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import aiohttp_jinja2
import jinja2
from aiohttp import web

from ..core.blockchain import Blockchain
from ..core.wallet import Wallet
from ..mining.miner import MiningNode
from ..storage.node import StorageNode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
WALLET = None
BLOCKCHAIN = None
MINING_NODE = None
STORAGE_NODE = None


class SimpleWebInterface:
    """Simple web interface for the PoRW blockchain system."""

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

        # Add filters
        env.filters['datetime'] = self._format_datetime

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

    def _format_datetime(self, value):
        """Format a datetime object or timestamp as a string."""
        if isinstance(value, (int, float)):
            # Convert timestamp to datetime
            dt = datetime.fromtimestamp(value)
        elif isinstance(value, datetime):
            dt = value
        else:
            return str(value)

        return dt.strftime('%Y-%m-%d %H:%M:%S')

    async def _startup(self, app):
        """Start up the web interface."""
        global WALLET, BLOCKCHAIN, MINING_NODE, STORAGE_NODE

        # Initialize the blockchain
        BLOCKCHAIN = Blockchain(self.data_dir)

        # Initialize the wallet
        wallet_path = self.data_dir / 'wallet.json'
        if wallet_path.exists():
            WALLET = Wallet.load(wallet_path)

        logger.info("Web interface started")

    async def _cleanup(self, app):
        """Clean up the web interface."""
        global WALLET, MINING_NODE, STORAGE_NODE

        # Stop the mining node
        if MINING_NODE and MINING_NODE.running:
            await MINING_NODE.stop()

        # Stop the storage node
        if STORAGE_NODE and STORAGE_NODE.running:
            await STORAGE_NODE.stop()

        # Save the wallet
        if WALLET:
            WALLET.save(self.data_dir / 'wallet.json')

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
            'wallet': WALLET
        }

    @aiohttp_jinja2.template('wallet.html')
    async def handle_wallet(self, request):
        """Handle the wallet page."""
        global WALLET, BLOCKCHAIN

        # Get wallet balance
        balance = 0.0
        if WALLET and BLOCKCHAIN:
            balance = BLOCKCHAIN.get_balance(WALLET.address)

        return {
            'title': 'Wallet - PoRW Blockchain',
            'wallet': WALLET,
            'balance': balance
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

    @aiohttp_jinja2.template('mining.html')
    async def handle_mining(self, request):
        """Handle the mining page."""
        return {
            'title': 'Mining - PoRW Blockchain',
            'wallet': WALLET,
            'miner': MINING_NODE
        }

    @aiohttp_jinja2.template('storage.html')
    async def handle_storage(self, request):
        """Handle the storage page."""
        return {
            'title': 'Storage - PoRW Blockchain',
            'wallet': WALLET,
            'storage_node': STORAGE_NODE
        }

    async def handle_wallet_send(self, request):
        """Handle sending tokens from the wallet."""
        global WALLET

        if not WALLET:
            return web.HTTPBadRequest(text="No wallet available")

        # Get the form data
        data = await request.post()
        recipient = data.get('recipient')
        amount = data.get('amount')

        if not recipient or not amount:
            return web.HTTPBadRequest(text="Recipient and amount are required")

        try:
            # Convert amount to float
            amount = float(amount)

            # Create and sign the transaction
            try:
                transaction = WALLET.create_transaction(recipient, amount)

                # In a real implementation, this would broadcast the transaction to the network
                # For now, we'll just add it to the wallet's transaction list
                if transaction not in WALLET.transactions:
                    WALLET.transactions.append(transaction)

                # Save the wallet
                WALLET.save(self.data_dir / 'wallet.json')
            except Exception as e:
                logger.error(f"Error creating transaction: {e}")
                return web.HTTPBadRequest(text=f"Error creating transaction: {e}")

            # Redirect to the wallet page
            return web.HTTPFound('/wallet')

        except Exception as e:
            return web.HTTPBadRequest(text=f"Error sending tokens: {e}")

    async def handle_mining_start(self, request):
        """Handle starting the mining node."""
        global WALLET, BLOCKCHAIN, MINING_NODE

        if not WALLET:
            return web.HTTPBadRequest(text="No wallet available")

        # Check if mining node is already running
        if MINING_NODE and MINING_NODE.running:
            return web.json_response({"status": "success", "message": "Mining node is already running"})

        # Create and start the mining node
        try:
            MINING_NODE = MiningNode(WALLET, BLOCKCHAIN, self.data_dir)
            await MINING_NODE.start()

            return web.json_response({
                "status": "success",
                "message": "Mining node started",
                "mining_status": MINING_NODE.get_status()
            })

        except Exception as e:
            logger.error(f"Error starting mining node: {e}")
            return web.HTTPBadRequest(text=f"Error starting mining node: {e}")

    async def handle_mining_stop(self, request):
        """Handle stopping the mining node."""
        global MINING_NODE

        # Check if mining node is running
        if not MINING_NODE or not MINING_NODE.running:
            return web.json_response({"status": "success", "message": "Mining node is not running"})

        # Stop the mining node
        try:
            await MINING_NODE.stop()

            return web.json_response({
                "status": "success",
                "message": "Mining node stopped"
            })

        except Exception as e:
            logger.error(f"Error stopping mining node: {e}")
            return web.HTTPBadRequest(text=f"Error stopping mining node: {e}")

    async def handle_storage_start(self, request):
        """Handle starting the storage node."""
        global WALLET, BLOCKCHAIN, STORAGE_NODE

        if not WALLET:
            return web.HTTPBadRequest(text="No wallet available")

        # Check if storage node is already running
        if STORAGE_NODE and STORAGE_NODE.running:
            return web.json_response({"status": "success", "message": "Storage node is already running"})

        # Create and start the storage node
        try:
            STORAGE_NODE = StorageNode(WALLET, BLOCKCHAIN, self.data_dir)
            await STORAGE_NODE.start()

            return web.json_response({
                "status": "success",
                "message": "Storage node started",
                "storage_status": STORAGE_NODE.get_status()
            })

        except Exception as e:
            logger.error(f"Error starting storage node: {e}")
            return web.HTTPBadRequest(text=f"Error starting storage node: {e}")

    async def handle_storage_stop(self, request):
        """Handle stopping the storage node."""
        global STORAGE_NODE

        # Check if storage node is running
        if not STORAGE_NODE or not STORAGE_NODE.running:
            return web.json_response({"status": "success", "message": "Storage node is not running"})

        # Stop the storage node
        try:
            await STORAGE_NODE.stop()

            return web.json_response({
                "status": "success",
                "message": "Storage node stopped"
            })

        except Exception as e:
            logger.error(f"Error stopping storage node: {e}")
            return web.HTTPBadRequest(text=f"Error stopping storage node: {e}")


def main():
    """Main entry point for the web interface."""
    import argparse

    parser = argparse.ArgumentParser(description='PoRW Blockchain Web Interface')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--data-dir', type=Path, help='Data directory for the blockchain')

    args = parser.parse_args()

    # Create and run the web interface
    web_interface = SimpleWebInterface(
        host=args.host,
        port=args.port,
        data_dir=args.data_dir
    )

    asyncio.run(web_interface.run())


if __name__ == '__main__':
    main()
