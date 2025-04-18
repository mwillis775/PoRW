# src/porw_blockchain/protein/mining_cli.py
"""
Command-line interface for the PoRW blockchain protein folding miner.
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import List, Optional

from .mining import ProteinMiner, MiningConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_parser() -> argparse.ArgumentParser:
    """Sets up the command-line argument parser."""
    parser = argparse.ArgumentParser(description="PoRW Blockchain Protein Folding Miner")
    
    # Mining settings
    parser.add_argument("--enable-mining", action="store_true", help="Enable mining (default: enabled)")
    parser.add_argument("--mining-threads", type=int, default=4, help="Number of mining threads (default: 4)")
    parser.add_argument("--enable-gpu", action="store_true", help="Enable GPU acceleration (default: disabled)")
    parser.add_argument("--no-gpu", action="store_true", help="Disable GPU acceleration")
    
    # Protein data settings
    parser.add_argument("--protein-data-dir", type=Path, help="Protein data directory (default: ~/.porw/protein_data)")
    
    # Mining parameters
    parser.add_argument("--target-folding-time", type=int, default=60000, help="Target folding time in milliseconds (default: 60000)")
    parser.add_argument("--max-folding-attempts", type=int, default=10, help="Maximum folding attempts per block (default: 10)")
    
    # Node connection
    parser.add_argument("--node-host", default="127.0.0.1", help="Node host to connect to (default: 127.0.0.1)")
    parser.add_argument("--node-port", type=int, default=8333, help="Node port to connect to (default: 8333)")
    
    # Logging
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO", help="Logging level (default: INFO)")
    parser.add_argument("--log-file", help="Log file path (default: porw_miner.log)")
    
    return parser


async def run_miner(args: argparse.Namespace) -> None:
    """
    Run the protein folding miner.
    
    Args:
        args: Command-line arguments
    """
    # Configure logging
    log_level = getattr(logging, args.log_level)
    logging.getLogger().setLevel(log_level)
    
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(file_handler)
    
    # Create mining configuration
    config = MiningConfig(
        enable_mining=args.enable_mining,
        mining_threads=args.mining_threads,
        enable_gpu=args.enable_gpu and not args.no_gpu,
        protein_data_dir=args.protein_data_dir,
        target_folding_time_ms=args.target_folding_time,
        max_folding_attempts=args.max_folding_attempts
    )
    
    # Create and start the miner
    miner = ProteinMiner(config)
    
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(miner.stop()))
    
    try:
        await miner.start()
        
        # Keep running until stopped
        while miner.running:
            await asyncio.sleep(1)
    
    except Exception as e:
        logger.error(f"Error running miner: {e}")
    
    finally:
        await miner.stop()


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI."""
    parser = setup_parser()
    parsed_args = parser.parse_args(args)
    
    try:
        asyncio.run(run_miner(parsed_args))
        return 0
    
    except KeyboardInterrupt:
        logger.info("Miner stopped by user")
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
