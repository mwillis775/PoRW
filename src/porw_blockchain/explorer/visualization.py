# src/porw_blockchain/explorer/visualization.py
"""
Visualization tools for the blockchain explorer.

This module provides tools for visualizing blockchain data,
including charts, graphs, and network visualizations.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from .api import ExplorerAPI

# Configure logger
logger = logging.getLogger(__name__)


class BlockchainVisualizer:
    """Visualizer for blockchain data."""

    def __init__(self, explorer_api: ExplorerAPI):
        """
        Initialize the blockchain visualizer.

        Args:
            explorer_api: Explorer API instance
        """
        self.explorer_api = explorer_api
        self.output_dir = os.path.join(os.getcwd(), "visualizations")
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_block_time_chart(
        self,
        days: int = 30,
        save_path: Optional[str] = None,
        show: bool = False
    ) -> Optional[Figure]:
        """
        Generate a chart of block times over time.

        Args:
            days: Number of days to include (default: 30)
            save_path: Path to save the chart (default: None)
            show: Whether to show the chart (default: False)

        Returns:
            Matplotlib figure, or None if there was an error
        """
        try:
            # Get latest blocks
            blocks = self.explorer_api.get_latest_blocks(days * 24 * 6)  # Assuming 1 block per 10 minutes
            
            if not blocks:
                logger.warning("No blocks found")
                return None
            
            # Extract timestamps and calculate block times
            timestamps = [block.timestamp for block in blocks]
            timestamps.reverse()  # Oldest first
            
            block_times = []
            for i in range(1, len(timestamps)):
                block_times.append(timestamps[i] - timestamps[i-1])
            
            # Create dates for x-axis
            dates = [datetime.fromtimestamp(ts) for ts in timestamps[1:]]
            
            # Create DataFrame
            df = pd.DataFrame({
                'date': dates,
                'block_time': block_times
            })
            
            # Resample to daily average
            daily_avg = df.set_index('date').resample('D').mean()
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot data
            ax.plot(daily_avg.index, daily_avg['block_time'], marker='o', linestyle='-')
            
            # Add moving average
            window_size = 7
            if len(daily_avg) >= window_size:
                daily_avg['ma'] = daily_avg['block_time'].rolling(window=window_size).mean()
                ax.plot(daily_avg.index, daily_avg['ma'], color='red', linestyle='--', label=f'{window_size}-day MA')
            
            # Add labels and title
            ax.set_xlabel('Date')
            ax.set_ylabel('Block Time (seconds)')
            ax.set_title(f'Average Block Time (Last {days} Days)')
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Add legend
            ax.legend()
            
            # Format y-axis
            ax.set_ylim(bottom=0)
            
            # Rotate x-axis labels
            plt.xticks(rotation=45)
            
            # Tight layout
            plt.tight_layout()
            
            # Save figure
            if save_path:
                plt.savefig(save_path)
            
            # Show figure
            if show:
                plt.show()
            
            return fig
        except Exception as e:
            logger.error(f"Error generating block time chart: {e}")
            return None

    def generate_transaction_volume_chart(
        self,
        days: int = 30,
        save_path: Optional[str] = None,
        show: bool = False
    ) -> Optional[Figure]:
        """
        Generate a chart of transaction volume over time.

        Args:
            days: Number of days to include (default: 30)
            save_path: Path to save the chart (default: None)
            show: Whether to show the chart (default: False)

        Returns:
            Matplotlib figure, or None if there was an error
        """
        try:
            # Get latest blocks
            blocks = self.explorer_api.get_latest_blocks(days * 24 * 6)  # Assuming 1 block per 10 minutes
            
            if not blocks:
                logger.warning("No blocks found")
                return None
            
            # Extract timestamps and transaction counts
            data = []
            for block in blocks:
                data.append({
                    'timestamp': block.timestamp,
                    'transaction_count': block.transaction_count
                })
            
            # Create DataFrame
            df = pd.DataFrame(data)
            df['date'] = df['timestamp'].apply(lambda x: datetime.fromtimestamp(x))
            
            # Resample to daily sum
            daily_sum = df.set_index('date')['transaction_count'].resample('D').sum()
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot data
            ax.bar(daily_sum.index, daily_sum, alpha=0.7)
            
            # Add moving average
            window_size = 7
            if len(daily_sum) >= window_size:
                ma = daily_sum.rolling(window=window_size).mean()
                ax.plot(daily_sum.index, ma, color='red', linestyle='-', linewidth=2, label=f'{window_size}-day MA')
            
            # Add labels and title
            ax.set_xlabel('Date')
            ax.set_ylabel('Number of Transactions')
            ax.set_title(f'Daily Transaction Volume (Last {days} Days)')
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Add legend
            ax.legend()
            
            # Format y-axis
            ax.set_ylim(bottom=0)
            
            # Rotate x-axis labels
            plt.xticks(rotation=45)
            
            # Tight layout
            plt.tight_layout()
            
            # Save figure
            if save_path:
                plt.savefig(save_path)
            
            # Show figure
            if show:
                plt.show()
            
            return fig
        except Exception as e:
            logger.error(f"Error generating transaction volume chart: {e}")
            return None

    def generate_network_graph(
        self,
        max_transactions: int = 100,
        save_path: Optional[str] = None,
        show: bool = False
    ) -> Optional[Figure]:
        """
        Generate a network graph of transactions.

        Args:
            max_transactions: Maximum number of transactions to include (default: 100)
            save_path: Path to save the graph (default: None)
            show: Whether to show the graph (default: False)

        Returns:
            Matplotlib figure, or None if there was an error
        """
        try:
            # Get latest blocks
            blocks = self.explorer_api.get_latest_blocks(10)
            
            if not blocks:
                logger.warning("No blocks found")
                return None
            
            # Extract transactions
            transactions = []
            for block in blocks:
                block_detail = self.explorer_api.get_block_by_hash(block.hash)
                if block_detail and block_detail.transactions:
                    transactions.extend(block_detail.transactions)
                    if len(transactions) >= max_transactions:
                        transactions = transactions[:max_transactions]
                        break
            
            if not transactions:
                logger.warning("No transactions found")
                return None
            
            # Create graph
            G = nx.DiGraph()
            
            # Add nodes and edges
            for tx in transactions:
                sender = tx.sender
                recipient = tx.recipient
                amount = tx.amount
                
                # Add nodes
                if not G.has_node(sender):
                    G.add_node(sender, type='sender')
                
                if not G.has_node(recipient):
                    G.add_node(recipient, type='recipient')
                
                # Add edge
                G.add_edge(sender, recipient, amount=amount, tx_id=tx.id)
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 10))
            
            # Set node positions
            pos = nx.spring_layout(G, k=0.3, iterations=50)
            
            # Draw nodes
            sender_nodes = [node for node, attr in G.nodes(data=True) if attr.get('type') == 'sender']
            recipient_nodes = [node for node, attr in G.nodes(data=True) if attr.get('type') == 'recipient']
            
            nx.draw_networkx_nodes(G, pos, nodelist=sender_nodes, node_color='skyblue', node_size=100, alpha=0.8)
            nx.draw_networkx_nodes(G, pos, nodelist=recipient_nodes, node_color='lightgreen', node_size=100, alpha=0.8)
            
            # Draw edges
            edge_weights = [G[u][v]['amount'] for u, v in G.edges()]
            max_weight = max(edge_weights) if edge_weights else 1
            normalized_weights = [0.5 + 2.5 * (w / max_weight) for w in edge_weights]
            
            nx.draw_networkx_edges(G, pos, width=normalized_weights, alpha=0.5, edge_color='gray', arrows=True, arrowsize=10)
            
            # Draw labels for high-degree nodes
            high_degree_nodes = [node for node, degree in dict(G.degree()).items() if degree > 2]
            nx.draw_networkx_labels(G, pos, labels={node: node[:8] + '...' for node in high_degree_nodes}, font_size=8)
            
            # Add title
            plt.title(f'Transaction Network Graph (Last {len(transactions)} Transactions)')
            
            # Remove axis
            plt.axis('off')
            
            # Tight layout
            plt.tight_layout()
            
            # Save figure
            if save_path:
                plt.savefig(save_path)
            
            # Show figure
            if show:
                plt.show()
            
            return fig
        except Exception as e:
            logger.error(f"Error generating network graph: {e}")
            return None

    def generate_address_distribution_chart(
        self,
        num_addresses: int = 100,
        save_path: Optional[str] = None,
        show: bool = False
    ) -> Optional[Figure]:
        """
        Generate a chart of address balance distribution.

        Args:
            num_addresses: Number of top addresses to include (default: 100)
            save_path: Path to save the chart (default: None)
            show: Whether to show the chart (default: False)

        Returns:
            Matplotlib figure, or None if there was an error
        """
        try:
            # Get top addresses by balance
            # This is a placeholder - in a real implementation, you would get this from the database
            addresses = []
            for i in range(num_addresses):
                addresses.append({
                    'address': f'porw1address{i}',
                    'balance': 1000 * np.random.pareto(1.5)
                })
            
            # Sort by balance
            addresses.sort(key=lambda x: x['balance'], reverse=True)
            
            # Create DataFrame
            df = pd.DataFrame(addresses)
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot data
            ax.bar(range(len(df)), df['balance'], alpha=0.7)
            
            # Add labels and title
            ax.set_xlabel('Address Rank')
            ax.set_ylabel('Balance')
            ax.set_title(f'Top {num_addresses} Addresses by Balance')
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Format y-axis
            ax.set_yscale('log')
            
            # Tight layout
            plt.tight_layout()
            
            # Save figure
            if save_path:
                plt.savefig(save_path)
            
            # Show figure
            if show:
                plt.show()
            
            return fig
        except Exception as e:
            logger.error(f"Error generating address distribution chart: {e}")
            return None

    def generate_protein_folding_chart(
        self,
        days: int = 30,
        save_path: Optional[str] = None,
        show: bool = False
    ) -> Optional[Figure]:
        """
        Generate a chart of protein folding activity over time.

        Args:
            days: Number of days to include (default: 30)
            save_path: Path to save the chart (default: None)
            show: Whether to show the chart (default: False)

        Returns:
            Matplotlib figure, or None if there was an error
        """
        try:
            # Get proteins
            proteins = self.explorer_api.get_proteins(limit=days * 10)
            
            if not proteins:
                logger.warning("No proteins found")
                return None
            
            # Extract data
            data = []
            for protein in proteins:
                data.append({
                    'timestamp': protein.folding_timestamp,
                    'energy_score': protein.energy_score,
                    'scientific_value': protein.scientific_value
                })
            
            # Create DataFrame
            df = pd.DataFrame(data)
            df['date'] = df['timestamp'].apply(lambda x: datetime.fromtimestamp(x))
            
            # Resample to daily average
            daily_avg = df.set_index('date').resample('D').mean()
            
            # Create figure
            fig, ax1 = plt.subplots(figsize=(12, 6))
            
            # Plot energy score
            color = 'tab:blue'
            ax1.set_xlabel('Date')
            ax1.set_ylabel('Energy Score', color=color)
            ax1.plot(daily_avg.index, daily_avg['energy_score'], marker='o', linestyle='-', color=color)
            ax1.tick_params(axis='y', labelcolor=color)
            
            # Create second y-axis
            ax2 = ax1.twinx()
            color = 'tab:red'
            ax2.set_ylabel('Scientific Value', color=color)
            ax2.plot(daily_avg.index, daily_avg['scientific_value'], marker='s', linestyle='-', color=color)
            ax2.tick_params(axis='y', labelcolor=color)
            
            # Add title
            plt.title(f'Protein Folding Activity (Last {days} Days)')
            
            # Add grid
            ax1.grid(True, linestyle='--', alpha=0.7)
            
            # Rotate x-axis labels
            plt.xticks(rotation=45)
            
            # Tight layout
            plt.tight_layout()
            
            # Save figure
            if save_path:
                plt.savefig(save_path)
            
            # Show figure
            if show:
                plt.show()
            
            return fig
        except Exception as e:
            logger.error(f"Error generating protein folding chart: {e}")
            return None

    def generate_storage_node_chart(
        self,
        save_path: Optional[str] = None,
        show: bool = False
    ) -> Optional[Figure]:
        """
        Generate a chart of storage node capacity and usage.

        Args:
            save_path: Path to save the chart (default: None)
            show: Whether to show the chart (default: False)

        Returns:
            Matplotlib figure, or None if there was an error
        """
        try:
            # Get storage nodes
            nodes = self.explorer_api.get_storage_nodes(limit=20)
            
            if not nodes:
                logger.warning("No storage nodes found")
                return None
            
            # Extract data
            node_ids = [node.id[:8] + '...' for node in nodes]
            capacities = [node.capacity / (1024**3) for node in nodes]  # Convert to GB
            used = [node.used / (1024**3) for node in nodes]  # Convert to GB
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Set width of bars
            bar_width = 0.35
            
            # Set positions of bars on x-axis
            r1 = np.arange(len(node_ids))
            r2 = [x + bar_width for x in r1]
            
            # Create bars
            ax.bar(r1, capacities, width=bar_width, label='Capacity', color='skyblue')
            ax.bar(r2, used, width=bar_width, label='Used', color='lightcoral')
            
            # Add labels and title
            ax.set_xlabel('Storage Node')
            ax.set_ylabel('Storage (GB)')
            ax.set_title('Storage Node Capacity and Usage')
            
            # Add xticks on the middle of the group bars
            ax.set_xticks([r + bar_width/2 for r in range(len(node_ids))])
            ax.set_xticklabels(node_ids, rotation=45, ha='right')
            
            # Add legend
            ax.legend()
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Tight layout
            plt.tight_layout()
            
            # Save figure
            if save_path:
                plt.savefig(save_path)
            
            # Show figure
            if show:
                plt.show()
            
            return fig
        except Exception as e:
            logger.error(f"Error generating storage node chart: {e}")
            return None

    def generate_dashboard(self, output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Generate a dashboard with multiple visualizations.

        Args:
            output_dir: Directory to save the visualizations (default: self.output_dir)

        Returns:
            Dictionary mapping chart names to file paths
        """
        if output_dir is None:
            output_dir = self.output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate charts
        charts = {}
        
        # Block time chart
        block_time_path = os.path.join(output_dir, 'block_time_chart.png')
        if self.generate_block_time_chart(save_path=block_time_path):
            charts['block_time'] = block_time_path
        
        # Transaction volume chart
        tx_volume_path = os.path.join(output_dir, 'transaction_volume_chart.png')
        if self.generate_transaction_volume_chart(save_path=tx_volume_path):
            charts['transaction_volume'] = tx_volume_path
        
        # Network graph
        network_graph_path = os.path.join(output_dir, 'network_graph.png')
        if self.generate_network_graph(save_path=network_graph_path):
            charts['network_graph'] = network_graph_path
        
        # Address distribution chart
        address_dist_path = os.path.join(output_dir, 'address_distribution_chart.png')
        if self.generate_address_distribution_chart(save_path=address_dist_path):
            charts['address_distribution'] = address_dist_path
        
        # Protein folding chart
        protein_chart_path = os.path.join(output_dir, 'protein_folding_chart.png')
        if self.generate_protein_folding_chart(save_path=protein_chart_path):
            charts['protein_folding'] = protein_chart_path
        
        # Storage node chart
        storage_chart_path = os.path.join(output_dir, 'storage_node_chart.png')
        if self.generate_storage_node_chart(save_path=storage_chart_path):
            charts['storage_node'] = storage_chart_path
        
        # Generate HTML dashboard
        html_path = os.path.join(output_dir, 'dashboard.html')
        self._generate_dashboard_html(charts, html_path)
        
        return charts

    def _generate_dashboard_html(self, charts: Dict[str, str], output_path: str) -> None:
        """
        Generate an HTML dashboard.

        Args:
            charts: Dictionary mapping chart names to file paths
            output_path: Path to save the HTML file
        """
        try:
            # Get network stats
            stats = self.explorer_api.get_network_stats()
            
            # Create HTML content
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>PoRW Blockchain Dashboard</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                    }}
                    .header {{
                        background-color: #2c3e50;
                        color: white;
                        padding: 20px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }}
                    .stats-container {{
                        display: flex;
                        flex-wrap: wrap;
                        justify-content: space-between;
                        margin-bottom: 20px;
                    }}
                    .stat-card {{
                        background-color: white;
                        border-radius: 5px;
                        padding: 15px;
                        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                        width: calc(25% - 20px);
                        margin-bottom: 20px;
                    }}
                    .stat-card h3 {{
                        margin-top: 0;
                        color: #2c3e50;
                    }}
                    .stat-value {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #3498db;
                    }}
                    .chart-container {{
                        background-color: white;
                        border-radius: 5px;
                        padding: 20px;
                        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                        margin-bottom: 20px;
                    }}
                    .chart-container h2 {{
                        margin-top: 0;
                        color: #2c3e50;
                    }}
                    .chart {{
                        width: 100%;
                        height: auto;
                    }}
                    .row {{
                        display: flex;
                        flex-wrap: wrap;
                        margin: 0 -10px;
                    }}
                    .col-6 {{
                        width: calc(50% - 20px);
                        margin: 0 10px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>PoRW Blockchain Dashboard</h1>
                        <p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    
                    <div class="stats-container">
                        <div class="stat-card">
                            <h3>Blockchain Height</h3>
                            <div class="stat-value">{stats.height}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Total Transactions</h3>
                            <div class="stat-value">{stats.total_transactions}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Active Nodes</h3>
                            <div class="stat-value">{stats.active_nodes}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Average Block Time</h3>
                            <div class="stat-value">{stats.average_block_time:.2f}s</div>
                        </div>
                        <div class="stat-card">
                            <h3>Hash Rate</h3>
                            <div class="stat-value">{stats.hash_rate / 1000000:.2f} MH/s</div>
                        </div>
                        <div class="stat-card">
                            <h3>Total Supply</h3>
                            <div class="stat-value">{stats.total_supply:,.2f}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Transactions (24h)</h3>
                            <div class="stat-value">{stats.transaction_count_24h}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Protein Count</h3>
                            <div class="stat-value">{stats.protein_count}</div>
                        </div>
                    </div>
                    
                    <div class="row">
            """
            
            # Add charts
            if 'block_time' in charts:
                html += f"""
                        <div class="col-6">
                            <div class="chart-container">
                                <h2>Block Time</h2>
                                <img class="chart" src="{os.path.basename(charts['block_time'])}" alt="Block Time Chart">
                            </div>
                        </div>
                """
            
            if 'transaction_volume' in charts:
                html += f"""
                        <div class="col-6">
                            <div class="chart-container">
                                <h2>Transaction Volume</h2>
                                <img class="chart" src="{os.path.basename(charts['transaction_volume'])}" alt="Transaction Volume Chart">
                            </div>
                        </div>
                """
            
            if 'network_graph' in charts:
                html += f"""
                        <div class="col-6">
                            <div class="chart-container">
                                <h2>Transaction Network</h2>
                                <img class="chart" src="{os.path.basename(charts['network_graph'])}" alt="Network Graph">
                            </div>
                        </div>
                """
            
            if 'address_distribution' in charts:
                html += f"""
                        <div class="col-6">
                            <div class="chart-container">
                                <h2>Address Distribution</h2>
                                <img class="chart" src="{os.path.basename(charts['address_distribution'])}" alt="Address Distribution Chart">
                            </div>
                        </div>
                """
            
            if 'protein_folding' in charts:
                html += f"""
                        <div class="col-6">
                            <div class="chart-container">
                                <h2>Protein Folding Activity</h2>
                                <img class="chart" src="{os.path.basename(charts['protein_folding'])}" alt="Protein Folding Chart">
                            </div>
                        </div>
                """
            
            if 'storage_node' in charts:
                html += f"""
                        <div class="col-6">
                            <div class="chart-container">
                                <h2>Storage Node Capacity</h2>
                                <img class="chart" src="{os.path.basename(charts['storage_node'])}" alt="Storage Node Chart">
                            </div>
                        </div>
                """
            
            html += """
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Write HTML to file
            with open(output_path, 'w') as f:
                f.write(html)
            
            logger.info(f"Dashboard generated at {output_path}")
        except Exception as e:
            logger.error(f"Error generating dashboard HTML: {e}")


def create_visualizer(explorer_api: ExplorerAPI) -> BlockchainVisualizer:
    """
    Create a blockchain visualizer.

    Args:
        explorer_api: Explorer API instance

    Returns:
        BlockchainVisualizer instance
    """
    return BlockchainVisualizer(explorer_api)
