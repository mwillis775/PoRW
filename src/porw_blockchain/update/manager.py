# src/porw_blockchain/update/manager.py
"""
Update manager for the PoRW blockchain.

This module provides the main interface for the auto-update functionality,
coordinating the checking, downloading, verification, and installation of updates.
"""

import asyncio
import logging
import os
import platform
import sys
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union, Callable

from .checker import UpdateChecker, ReleaseInfo
from .downloader import UpdateDownloader
from .verifier import UpdateVerifier
from .installer import UpdateInstaller

# Configure logger
logger = logging.getLogger(__name__)


class UpdateStatus(Enum):
    """Status of the update process."""
    IDLE = auto()
    CHECKING = auto()
    UPDATE_AVAILABLE = auto()
    DOWNLOADING = auto()
    VERIFYING = auto()
    READY_TO_INSTALL = auto()
    INSTALLING = auto()
    INSTALLED = auto()
    FAILED = auto()
    NO_UPDATE = auto()


@dataclass
class UpdateConfig:
    """Configuration for the update manager."""
    # Repository information
    repo_owner: str = "mwillis775"
    repo_name: str = "PoRW-PoRS"
    
    # Update settings
    check_interval: int = 86400  # 24 hours in seconds
    auto_download: bool = True
    auto_install: bool = False
    
    # Paths
    download_dir: Path = Path.home() / ".porw" / "updates"
    backup_dir: Path = Path.home() / ".porw" / "backups"
    
    # Version information
    current_version: str = "0.1.0"
    
    # GitHub API settings
    github_api_url: str = "https://api.github.com"
    github_token: Optional[str] = None
    
    # Verification settings
    verify_signature: bool = True
    public_key_path: Optional[Path] = None


class UpdateError(Exception):
    """Exception raised for update errors."""
    pass


class UpdateManager:
    """
    Manager for the auto-update functionality.
    
    This class coordinates the checking, downloading, verification,
    and installation of updates.
    """

    def __init__(self, config: Optional[UpdateConfig] = None):
        """
        Initialize the update manager.
        
        Args:
            config: Optional configuration for the update manager.
                   If None, uses default configuration.
        """
        self.config = config or UpdateConfig()
        
        # Create directories if they don't exist
        self.config.download_dir.mkdir(parents=True, exist_ok=True)
        self.config.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.checker = UpdateChecker(
            repo_owner=self.config.repo_owner,
            repo_name=self.config.repo_name,
            current_version=self.config.current_version,
            github_api_url=self.config.github_api_url,
            github_token=self.config.github_token
        )
        
        self.downloader = UpdateDownloader(
            download_dir=self.config.download_dir
        )
        
        self.verifier = UpdateVerifier(
            verify_signature=self.config.verify_signature,
            public_key_path=self.config.public_key_path
        )
        
        self.installer = UpdateInstaller(
            backup_dir=self.config.backup_dir
        )
        
        # State
        self.status = UpdateStatus.IDLE
        self.last_check_time = 0
        self.latest_release: Optional[ReleaseInfo] = None
        self.downloaded_update_path: Optional[Path] = None
        self.update_task = None
        self.callbacks = {
            "on_update_available": [],
            "on_download_progress": [],
            "on_download_complete": [],
            "on_verification_complete": [],
            "on_install_complete": [],
            "on_update_failed": []
        }

    def add_callback(self, event: str, callback: Callable) -> None:
        """
        Add a callback for an update event.
        
        Args:
            event: The event to add a callback for.
                  One of: "on_update_available", "on_download_progress",
                  "on_download_complete", "on_verification_complete",
                  "on_install_complete", "on_update_failed".
            callback: The callback function to add.
        
        Raises:
            ValueError: If the event is not valid.
        """
        if event not in self.callbacks:
            raise ValueError(f"Invalid event: {event}")
        
        self.callbacks[event].append(callback)

    def remove_callback(self, event: str, callback: Callable) -> None:
        """
        Remove a callback for an update event.
        
        Args:
            event: The event to remove a callback for.
            callback: The callback function to remove.
        
        Raises:
            ValueError: If the event is not valid.
        """
        if event not in self.callbacks:
            raise ValueError(f"Invalid event: {event}")
        
        if callback in self.callbacks[event]:
            self.callbacks[event].remove(callback)

    def _trigger_callback(self, event: str, *args, **kwargs) -> None:
        """
        Trigger callbacks for an event.
        
        Args:
            event: The event to trigger callbacks for.
            *args: Arguments to pass to the callbacks.
            **kwargs: Keyword arguments to pass to the callbacks.
        """
        if event not in self.callbacks:
            return
        
        for callback in self.callbacks[event]:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in callback for event {event}: {e}")

    async def start(self) -> None:
        """
        Start the update manager.
        
        This method starts the update check loop, which periodically
        checks for updates based on the configured check interval.
        """
        logger.info("Starting update manager")
        
        # Start update check loop
        self.update_task = asyncio.create_task(self._update_check_loop())

    async def stop(self) -> None:
        """
        Stop the update manager.
        
        This method stops the update check loop.
        """
        logger.info("Stopping update manager")
        
        # Cancel update check loop
        if self.update_task is not None:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
            self.update_task = None

    async def _update_check_loop(self) -> None:
        """
        Update check loop.
        
        This method periodically checks for updates based on the
        configured check interval.
        """
        while True:
            try:
                # Check if it's time to check for updates
                current_time = time.time()
                if current_time - self.last_check_time >= self.config.check_interval:
                    await self.check_for_updates()
                    self.last_check_time = current_time
                
                # Wait for next check
                await asyncio.sleep(60)  # Check every minute if it's time for an update check
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in update check loop: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def check_for_updates(self) -> Tuple[bool, Optional[ReleaseInfo]]:
        """
        Check for updates.
        
        Returns:
            A tuple containing:
            - A boolean indicating whether an update is available.
            - The latest release information, or None if no update is available.
        """
        logger.info("Checking for updates")
        self.status = UpdateStatus.CHECKING
        
        try:
            # Check for updates
            update_available, release_info = await self.checker.check_for_updates()
            
            if update_available:
                logger.info(f"Update available: {release_info.version}")
                self.status = UpdateStatus.UPDATE_AVAILABLE
                self.latest_release = release_info
                
                # Trigger callback
                self._trigger_callback("on_update_available", release_info)
                
                # Auto-download if enabled
                if self.config.auto_download:
                    await self.download_update(release_info)
            else:
                logger.info("No update available")
                self.status = UpdateStatus.NO_UPDATE
            
            return update_available, release_info
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            self.status = UpdateStatus.FAILED
            self._trigger_callback("on_update_failed", str(e))
            raise UpdateError(f"Error checking for updates: {e}")

    async def download_update(self, release_info: Optional[ReleaseInfo] = None) -> Path:
        """
        Download an update.
        
        Args:
            release_info: The release information for the update to download.
                         If None, uses the latest release information.
        
        Returns:
            The path to the downloaded update.
        
        Raises:
            UpdateError: If there's an error downloading the update.
        """
        if release_info is None:
            if self.latest_release is None:
                raise UpdateError("No release information available")
            release_info = self.latest_release
        
        logger.info(f"Downloading update {release_info.version}")
        self.status = UpdateStatus.DOWNLOADING
        
        try:
            # Download update
            update_path = await self.downloader.download_update(
                release_info,
                progress_callback=lambda progress: self._trigger_callback(
                    "on_download_progress", progress
                )
            )
            
            logger.info(f"Update downloaded to {update_path}")
            self.downloaded_update_path = update_path
            
            # Trigger callback
            self._trigger_callback("on_download_complete", update_path)
            
            # Verify update
            await self.verify_update(update_path)
            
            return update_path
        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            self.status = UpdateStatus.FAILED
            self._trigger_callback("on_update_failed", str(e))
            raise UpdateError(f"Error downloading update: {e}")

    async def verify_update(self, update_path: Optional[Path] = None) -> bool:
        """
        Verify an update.
        
        Args:
            update_path: The path to the update to verify.
                        If None, uses the downloaded update path.
        
        Returns:
            True if the update is valid, False otherwise.
        
        Raises:
            UpdateError: If there's an error verifying the update.
        """
        if update_path is None:
            if self.downloaded_update_path is None:
                raise UpdateError("No update downloaded")
            update_path = self.downloaded_update_path
        
        logger.info(f"Verifying update at {update_path}")
        self.status = UpdateStatus.VERIFYING
        
        try:
            # Verify update
            is_valid = await self.verifier.verify_update(update_path)
            
            if is_valid:
                logger.info("Update verified successfully")
                self.status = UpdateStatus.READY_TO_INSTALL
                
                # Trigger callback
                self._trigger_callback("on_verification_complete", True)
                
                # Auto-install if enabled
                if self.config.auto_install:
                    await self.install_update(update_path)
            else:
                logger.error("Update verification failed")
                self.status = UpdateStatus.FAILED
                
                # Trigger callback
                self._trigger_callback("on_verification_complete", False)
                self._trigger_callback("on_update_failed", "Update verification failed")
            
            return is_valid
        except Exception as e:
            logger.error(f"Error verifying update: {e}")
            self.status = UpdateStatus.FAILED
            self._trigger_callback("on_update_failed", str(e))
            raise UpdateError(f"Error verifying update: {e}")

    async def install_update(self, update_path: Optional[Path] = None) -> bool:
        """
        Install an update.
        
        Args:
            update_path: The path to the update to install.
                        If None, uses the downloaded update path.
        
        Returns:
            True if the update was installed successfully, False otherwise.
        
        Raises:
            UpdateError: If there's an error installing the update.
        """
        if update_path is None:
            if self.downloaded_update_path is None:
                raise UpdateError("No update downloaded")
            update_path = self.downloaded_update_path
        
        logger.info(f"Installing update from {update_path}")
        self.status = UpdateStatus.INSTALLING
        
        try:
            # Install update
            success = await self.installer.install_update(update_path)
            
            if success:
                logger.info("Update installed successfully")
                self.status = UpdateStatus.INSTALLED
                
                # Trigger callback
                self._trigger_callback("on_install_complete", True)
            else:
                logger.error("Update installation failed")
                self.status = UpdateStatus.FAILED
                
                # Trigger callback
                self._trigger_callback("on_install_complete", False)
                self._trigger_callback("on_update_failed", "Update installation failed")
            
            return success
        except Exception as e:
            logger.error(f"Error installing update: {e}")
            self.status = UpdateStatus.FAILED
            self._trigger_callback("on_update_failed", str(e))
            raise UpdateError(f"Error installing update: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the update manager.
        
        Returns:
            A dictionary containing status information.
        """
        return {
            "status": self.status.name,
            "last_check_time": self.last_check_time,
            "latest_release": self.latest_release.__dict__ if self.latest_release else None,
            "downloaded_update_path": str(self.downloaded_update_path) if self.downloaded_update_path else None,
            "current_version": self.config.current_version,
            "auto_download": self.config.auto_download,
            "auto_install": self.config.auto_install,
            "check_interval": self.config.check_interval
        }

    def set_config(self, config: UpdateConfig) -> None:
        """
        Set the configuration for the update manager.
        
        Args:
            config: The new configuration.
        """
        self.config = config
        
        # Update components with new configuration
        self.checker = UpdateChecker(
            repo_owner=self.config.repo_owner,
            repo_name=self.config.repo_name,
            current_version=self.config.current_version,
            github_api_url=self.config.github_api_url,
            github_token=self.config.github_token
        )
        
        self.downloader = UpdateDownloader(
            download_dir=self.config.download_dir
        )
        
        self.verifier = UpdateVerifier(
            verify_signature=self.config.verify_signature,
            public_key_path=self.config.public_key_path
        )
        
        self.installer = UpdateInstaller(
            backup_dir=self.config.backup_dir
        )
        
        logger.info("Update manager configuration updated")

    def rollback_update(self) -> bool:
        """
        Rollback the last update.
        
        Returns:
            True if the rollback was successful, False otherwise.
        
        Raises:
            UpdateError: If there's an error rolling back the update.
        """
        logger.info("Rolling back update")
        
        try:
            # Rollback update
            success = self.installer.rollback_update()
            
            if success:
                logger.info("Update rolled back successfully")
            else:
                logger.error("Update rollback failed")
            
            return success
        except Exception as e:
            logger.error(f"Error rolling back update: {e}")
            raise UpdateError(f"Error rolling back update: {e}")


# Create a global update manager instance
update_manager = UpdateManager()
