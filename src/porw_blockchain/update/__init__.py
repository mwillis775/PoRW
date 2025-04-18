# src/porw_blockchain/update/__init__.py
"""
Auto-update functionality for the PoRW blockchain.

This package provides functionality for automatically updating the software,
including checking for updates, downloading updates, verifying updates,
and installing updates.
"""

from .manager import UpdateManager, UpdateConfig, UpdateStatus, UpdateError
from .checker import UpdateChecker, ReleaseInfo
from .downloader import UpdateDownloader
from .verifier import UpdateVerifier
from .installer import UpdateInstaller

__all__ = [
    'UpdateManager',
    'UpdateConfig',
    'UpdateStatus',
    'UpdateError',
    'UpdateChecker',
    'ReleaseInfo',
    'UpdateDownloader',
    'UpdateVerifier',
    'UpdateInstaller'
]
