# src/porw_blockchain/update/downloader.py
"""
Update downloader for the PoRW blockchain.

This module provides functionality for downloading updates from GitHub releases.
"""

import asyncio
import logging
import os
import platform
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union, Callable

import aiohttp

from .checker import ReleaseInfo

# Configure logger
logger = logging.getLogger(__name__)


class UpdateDownloader:
    """
    Downloader for updates.
    
    This class provides functionality for downloading updates from GitHub releases.
    """

    def __init__(self, download_dir: Path):
        """
        Initialize the update downloader.
        
        Args:
            download_dir: The directory to download updates to.
        """
        self.download_dir = download_dir
        
        # Create download directory if it doesn't exist
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def download_update(
        self,
        release_info: ReleaseInfo,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Path:
        """
        Download an update.
        
        Args:
            release_info: The release information for the update to download.
            progress_callback: Optional callback function for download progress.
                              The callback receives a float between 0 and 1
                              representing the download progress.
        
        Returns:
            The path to the downloaded update.
        
        Raises:
            ValueError: If the release has no download URL.
            IOError: If there's an error downloading the update.
        """
        if not release_info.download_url:
            raise ValueError("Release has no download URL")
        
        logger.info(f"Downloading update {release_info.version} from {release_info.download_url}")
        
        # Determine file name from URL
        file_name = os.path.basename(release_info.download_url)
        if "?" in file_name:
            file_name = file_name.split("?")[0]
        
        # Add version to file name if not already present
        if release_info.version not in file_name:
            name, ext = os.path.splitext(file_name)
            file_name = f"{name}-{release_info.version}{ext}"
        
        # Create download path
        download_path = self.download_dir / file_name
        
        # Download file
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(release_info.download_url) as response:
                    if response.status != 200:
                        raise IOError(f"Error downloading update: {response.status} {await response.text()}")
                    
                    # Get total size
                    total_size = int(response.headers.get("Content-Length", 0))
                    
                    # Create temporary file
                    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                        temp_path = temp_file.name
                        
                        # Download chunks
                        downloaded_size = 0
                        async for chunk in response.content.iter_chunked(8192):
                            temp_file.write(chunk)
                            downloaded_size += len(chunk)
                            
                            # Report progress
                            if progress_callback and total_size > 0:
                                progress = downloaded_size / total_size
                                progress_callback(progress)
            
            # Move temporary file to download path
            shutil.move(temp_path, download_path)
            
            logger.info(f"Update downloaded to {download_path}")
            return download_path
        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            
            # Clean up temporary file if it exists
            if "temp_path" in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            
            raise IOError(f"Error downloading update: {e}")

    def get_downloaded_updates(self) -> List[Path]:
        """
        Get a list of downloaded updates.
        
        Returns:
            A list of paths to downloaded updates.
        """
        return list(self.download_dir.glob("*"))

    def clean_old_downloads(self, keep_latest: int = 3) -> None:
        """
        Clean old downloaded updates.
        
        Args:
            keep_latest: The number of latest updates to keep (default: 3).
        """
        # Get all downloaded updates
        downloads = self.get_downloaded_updates()
        
        # Sort by modification time (newest first)
        downloads.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        # Delete old downloads
        for download in downloads[keep_latest:]:
            try:
                download.unlink()
                logger.info(f"Deleted old download: {download}")
            except Exception as e:
                logger.error(f"Error deleting old download {download}: {e}")

    def get_download_dir_size(self) -> int:
        """
        Get the size of the download directory in bytes.
        
        Returns:
            The size of the download directory in bytes.
        """
        total_size = 0
        for path in self.download_dir.glob("**/*"):
            if path.is_file():
                total_size += path.stat().st_size
        return total_size
