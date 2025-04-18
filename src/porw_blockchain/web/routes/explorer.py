# src/porw_blockchain/web/routes/explorer.py
"""
Web routes for the blockchain explorer.

This module provides web routes for the blockchain explorer, including
block, transaction, address, and network statistics views.
"""

import io
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

import aiohttp_jinja2
import qrcode
from aiohttp import web

from ...core.blockchain import Blockchain
from ...explorer.api import ExplorerAPI, create_explorer_api
from ...explorer.visualization import BlockchainVisualizer, create_visualizer
from ...storage.database import Database

# Configure logger
logger = logging.getLogger(__name__)


class ExplorerRoutes:
    """Web routes for the blockchain explorer."""

    def __init__(self, app: web.Application, blockchain: Blockchain, database: Database):
        """
        Initialize the explorer routes.

        Args:
            app: Web application
            blockchain: Blockchain instance
            database: Database instance
        """
        self.app = app
        self.blockchain = blockchain
        self.database = database
        self.explorer_api = create_explorer_api(blockchain, database)
        self.visualizer = create_visualizer(self.explorer_api)
        
        # Create static directory for visualizations
        os.makedirs(os.path.join(app['static_root'], 'images', 'explorer'), exist_ok=True)
        
        # Generate visualizations
        self._generate_visualizations()
        
        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register explorer routes."""
        self.app.router.add_get('/explorer', self.explorer_index, name='explorer_index')
        self.app.router.add_get('/explorer/search', self.explorer_search, name='explorer_search')
        self.app.router.add_get('/explorer/blocks', self.explorer_blocks, name='explorer_blocks')
        self.app.router.add_get('/explorer/blocks/{height}', self.explorer_block, name='explorer_block')
        self.app.router.add_get('/explorer/transactions', self.explorer_transactions, name='explorer_transactions')
        self.app.router.add_get('/explorer/transactions/{tx_id}', self.explorer_transaction, name='explorer_transaction')
        self.app.router.add_get('/explorer/addresses/{address}', self.explorer_address, name='explorer_address')
        self.app.router.add_get('/explorer/addresses/{address}/qr', self.explorer_address_qr, name='explorer_address_qr')
        self.app.router.add_get('/explorer/proteins', self.explorer_proteins, name='explorer_proteins')
        self.app.router.add_get('/explorer/proteins/{protein_id}', self.explorer_protein, name='explorer_protein')
        self.app.router.add_get('/explorer/proteins/{protein_id}/download', self.explorer_protein_download, name='explorer_protein_download')
        self.app.router.add_get('/explorer/storage-nodes', self.explorer_storage_nodes, name='explorer_storage_nodes')
        self.app.router.add_get('/explorer/storage-nodes/{node_id}', self.explorer_storage_node, name='explorer_storage_node')

    def _generate_visualizations(self):
        """Generate visualizations for the explorer."""
        try:
            # Generate block time chart
            block_time_path = os.path.join(self.app['static_root'], 'images', 'explorer', 'block_time_chart.png')
            self.visualizer.generate_block_time_chart(save_path=block_time_path)
            
            # Generate transaction volume chart
            tx_volume_path = os.path.join(self.app['static_root'], 'images', 'explorer', 'transaction_volume_chart.png')
            self.visualizer.generate_transaction_volume_chart(save_path=tx_volume_path)
            
            # Generate protein folding chart
            protein_chart_path = os.path.join(self.app['static_root'], 'images', 'explorer', 'protein_folding_chart.png')
            self.visualizer.generate_protein_folding_chart(save_path=protein_chart_path)
            
            # Generate storage node chart
            storage_chart_path = os.path.join(self.app['static_root'], 'images', 'explorer', 'storage_node_chart.png')
            self.visualizer.generate_storage_node_chart(save_path=storage_chart_path)
            
            logger.info("Generated explorer visualizations")
        except Exception as e:
            logger.error(f"Error generating explorer visualizations: {e}")

    @aiohttp_jinja2.template('explorer/index.html')
    async def explorer_index(self, request: web.Request) -> Dict[str, Any]:
        """
        Explorer index page.

        Args:
            request: Web request

        Returns:
            Template context
        """
        try:
            # Get network stats
            stats = self.explorer_api.get_network_stats()
            
            # Get latest blocks
            latest_blocks = self.explorer_api.get_latest_blocks(limit=10)
            
            # Get latest transactions
            latest_transactions = []
            for block in latest_blocks[:3]:
                block_detail = self.explorer_api.get_block_by_hash(block.hash)
                if block_detail and block_detail.transactions:
                    latest_transactions.extend(block_detail.transactions)
                    if len(latest_transactions) >= 10:
                        latest_transactions = latest_transactions[:10]
                        break
            
            return {
                'stats': stats,
                'latest_blocks': latest_blocks,
                'latest_transactions': latest_transactions
            }
        except Exception as e:
            logger.error(f"Error rendering explorer index: {e}")
            raise web.HTTPInternalServerError(text=str(e))

    @aiohttp_jinja2.template('explorer/search.html')
    async def explorer_search(self, request: web.Request) -> Dict[str, Any]:
        """
        Search the blockchain.

        Args:
            request: Web request

        Returns:
            Template context
        """
        try:
            query = request.query.get('query', '')
            if not query:
                raise web.HTTPBadRequest(text="Search query is required")
            
            # Search the blockchain
            results = self.explorer_api.search(query)
            
            return {
                'query': query,
                'results': results
            }
        except Exception as e:
            logger.error(f"Error searching blockchain: {e}")
            raise web.HTTPInternalServerError(text=str(e))

    @aiohttp_jinja2.template('explorer/blocks.html')
    async def explorer_blocks(self, request: web.Request) -> Dict[str, Any]:
        """
        List blocks.

        Args:
            request: Web request

        Returns:
            Template context
        """
        try:
            page = int(request.query.get('page', '1'))
            limit = int(request.query.get('limit', '25'))
            
            # Get blocks
            blocks = self.explorer_api.get_latest_blocks(limit=limit, offset=(page - 1) * limit)
            
            # Get total blocks
            total_blocks = self.blockchain.get_height() + 1
            total_pages = (total_blocks + limit - 1) // limit
            
            return {
                'blocks': blocks,
                'page': page,
                'limit': limit,
                'total_blocks': total_blocks,
                'total_pages': total_pages
            }
        except Exception as e:
            logger.error(f"Error listing blocks: {e}")
            raise web.HTTPInternalServerError(text=str(e))

    @aiohttp_jinja2.template('explorer/block.html')
    async def explorer_block(self, request: web.Request) -> Dict[str, Any]:
        """
        Block details.

        Args:
            request: Web request

        Returns:
            Template context
        """
        try:
            height = int(request.match_info['height'])
            
            # Get block
            block = self.explorer_api.get_block_by_height(height)
            if not block:
                raise web.HTTPNotFound(text=f"Block with height {height} not found")
            
            return {
                'block': block
            }
        except ValueError:
            raise web.HTTPBadRequest(text="Invalid block height")
        except Exception as e:
            logger.error(f"Error getting block details: {e}")
            raise web.HTTPInternalServerError(text=str(e))

    @aiohttp_jinja2.template('explorer/transactions.html')
    async def explorer_transactions(self, request: web.Request) -> Dict[str, Any]:
        """
        List transactions.

        Args:
            request: Web request

        Returns:
            Template context
        """
        try:
            page = int(request.query.get('page', '1'))
            limit = int(request.query.get('limit', '25'))
            
            # Get transactions
            transactions = []
            blocks = self.explorer_api.get_latest_blocks(limit=10)
            
            for block in blocks:
                block_detail = self.explorer_api.get_block_by_hash(block.hash)
                if block_detail and block_detail.transactions:
                    transactions.extend(block_detail.transactions)
            
            # Apply pagination
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            transactions = transactions[start_idx:end_idx]
            
            # Get total transactions (approximate)
            total_transactions = self.explorer_api.get_network_stats().total_transactions
            total_pages = (total_transactions + limit - 1) // limit
            
            return {
                'transactions': transactions,
                'page': page,
                'limit': limit,
                'total_transactions': total_transactions,
                'total_pages': total_pages
            }
        except Exception as e:
            logger.error(f"Error listing transactions: {e}")
            raise web.HTTPInternalServerError(text=str(e))

    @aiohttp_jinja2.template('explorer/transaction.html')
    async def explorer_transaction(self, request: web.Request) -> Dict[str, Any]:
        """
        Transaction details.

        Args:
            request: Web request

        Returns:
            Template context
        """
        try:
            tx_id = request.match_info['tx_id']
            
            # Get transaction
            tx = self.explorer_api.get_transaction(tx_id)
            if not tx:
                raise web.HTTPNotFound(text=f"Transaction with ID {tx_id} not found")
            
            return {
                'tx': tx
            }
        except Exception as e:
            logger.error(f"Error getting transaction details: {e}")
            raise web.HTTPInternalServerError(text=str(e))

    @aiohttp_jinja2.template('explorer/address.html')
    async def explorer_address(self, request: web.Request) -> Dict[str, Any]:
        """
        Address details.

        Args:
            request: Web request

        Returns:
            Template context
        """
        try:
            address_str = request.match_info['address']
            page = int(request.query.get('page', '1'))
            limit = int(request.query.get('limit', '25'))
            
            # Get address
            address = self.explorer_api.get_address(address_str)
            if not address:
                raise web.HTTPNotFound(text=f"Address {address_str} not found")
            
            # Get transactions for the address
            transactions = self.explorer_api.get_transactions_by_address(address_str, limit=limit, offset=(page - 1) * limit)
            
            # Update address with paginated transactions
            address.transactions = transactions
            
            # Calculate total pages
            total_pages = (address.transaction_count + limit - 1) // limit
            
            return {
                'address': address,
                'page': page,
                'limit': limit,
                'total_pages': total_pages
            }
        except Exception as e:
            logger.error(f"Error getting address details: {e}")
            raise web.HTTPInternalServerError(text=str(e))

    async def explorer_address_qr(self, request: web.Request) -> web.Response:
        """
        Generate QR code for an address.

        Args:
            request: Web request

        Returns:
            QR code image
        """
        try:
            address = request.match_info['address']
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(address)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return web.Response(
                body=img_bytes.read(),
                content_type='image/png'
            )
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            raise web.HTTPInternalServerError(text=str(e))

    @aiohttp_jinja2.template('explorer/proteins.html')
    async def explorer_proteins(self, request: web.Request) -> Dict[str, Any]:
        """
        List proteins.

        Args:
            request: Web request

        Returns:
            Template context
        """
        try:
            page = int(request.query.get('page', '1'))
            limit = int(request.query.get('limit', '25'))
            
            # Get proteins
            proteins = self.explorer_api.get_proteins(limit=limit, offset=(page - 1) * limit)
            
            # Get total proteins
            total_proteins = self.explorer_api.get_network_stats().protein_count
            total_pages = (total_proteins + limit - 1) // limit
            
            return {
                'proteins': proteins,
                'page': page,
                'limit': limit,
                'total_proteins': total_proteins,
                'total_pages': total_pages
            }
        except Exception as e:
            logger.error(f"Error listing proteins: {e}")
            raise web.HTTPInternalServerError(text=str(e))

    @aiohttp_jinja2.template('explorer/protein.html')
    async def explorer_protein(self, request: web.Request) -> Dict[str, Any]:
        """
        Protein details.

        Args:
            request: Web request

        Returns:
            Template context
        """
        try:
            protein_id = request.match_info['protein_id']
            
            # Get protein
            protein = self.explorer_api.get_protein(protein_id)
            if not protein:
                raise web.HTTPNotFound(text=f"Protein with ID {protein_id} not found")
            
            return {
                'protein': protein
            }
        except Exception as e:
            logger.error(f"Error getting protein details: {e}")
            raise web.HTTPInternalServerError(text=str(e))

    async def explorer_protein_download(self, request: web.Request) -> web.Response:
        """
        Download protein data.

        Args:
            request: Web request

        Returns:
            Protein data file
        """
        try:
            protein_id = request.match_info['protein_id']
            format_type = request.query.get('format', 'pdb').lower()
            
            # Get protein
            protein = self.explorer_api.get_protein(protein_id)
            if not protein:
                raise web.HTTPNotFound(text=f"Protein with ID {protein_id} not found")
            
            if format_type == 'fasta':
                # Generate FASTA format
                fasta = f">{protein.id} {protein.name}\n"
                
                # Split sequence into lines of 60 characters
                sequence = protein.sequence
                for i in range(0, len(sequence), 60):
                    fasta += sequence[i:i+60] + "\n"
                
                return web.Response(
                    body=fasta,
                    content_type='text/plain',
                    headers={
                        'Content-Disposition': f'attachment; filename="{protein.id}.fasta"'
                    }
                )
            elif format_type == 'pdb':
                # Generate PDB format (simplified)
                pdb = f"HEADER    {protein.name}\n"
                pdb += f"TITLE     {protein.name}\n"
                pdb += f"REMARK    Energy Score: {protein.energy_score}\n"
                pdb += f"REMARK    Scientific Value: {protein.scientific_value}\n"
                
                # Add atom coordinates if available
                if protein.structure and 'coordinates' in protein.structure:
                    for i, coord in enumerate(protein.structure['coordinates']):
                        atom_name = "CA"  # Alpha carbon
                        res_name = protein.sequence[i] if i < len(protein.sequence) else "GLY"
                        pdb += f"ATOM  {i+1:5d}  {atom_name:<4s}{res_name:3s} A{i+1:4d}    {coord['x']:8.3f}{coord['y']:8.3f}{coord['z']:8.3f}  1.00  0.00\n"
                
                pdb += "END\n"
                
                return web.Response(
                    body=pdb,
                    content_type='text/plain',
                    headers={
                        'Content-Disposition': f'attachment; filename="{protein.id}.pdb"'
                    }
                )
            else:
                raise web.HTTPBadRequest(text=f"Unsupported format: {format_type}")
        except Exception as e:
            logger.error(f"Error downloading protein data: {e}")
            raise web.HTTPInternalServerError(text=str(e))

    @aiohttp_jinja2.template('explorer/storage_nodes.html')
    async def explorer_storage_nodes(self, request: web.Request) -> Dict[str, Any]:
        """
        List storage nodes.

        Args:
            request: Web request

        Returns:
            Template context
        """
        try:
            page = int(request.query.get('page', '1'))
            limit = int(request.query.get('limit', '25'))
            
            # Get storage nodes
            nodes = self.explorer_api.get_storage_nodes(limit=limit, offset=(page - 1) * limit)
            
            # Get total storage nodes
            total_nodes = self.explorer_api.get_network_stats().storage_nodes
            total_pages = (total_nodes + limit - 1) // limit
            
            return {
                'nodes': nodes,
                'page': page,
                'limit': limit,
                'total_nodes': total_nodes,
                'total_pages': total_pages
            }
        except Exception as e:
            logger.error(f"Error listing storage nodes: {e}")
            raise web.HTTPInternalServerError(text=str(e))

    @aiohttp_jinja2.template('explorer/storage_node.html')
    async def explorer_storage_node(self, request: web.Request) -> Dict[str, Any]:
        """
        Storage node details.

        Args:
            request: Web request

        Returns:
            Template context
        """
        try:
            node_id = request.match_info['node_id']
            
            # Get storage node
            node = self.explorer_api.get_storage_node(node_id)
            if not node:
                raise web.HTTPNotFound(text=f"Storage node with ID {node_id} not found")
            
            return {
                'node': node
            }
        except Exception as e:
            logger.error(f"Error getting storage node details: {e}")
            raise web.HTTPInternalServerError(text=str(e))


def setup_explorer_routes(app: web.Application, blockchain: Blockchain, database: Database):
    """
    Set up explorer routes.

    Args:
        app: Web application
        blockchain: Blockchain instance
        database: Database instance
    """
    ExplorerRoutes(app, blockchain, database)
