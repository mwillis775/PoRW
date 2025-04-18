# src/porw_blockchain/update/checker.py
"""
Update checker for the PoRW blockchain.

This module provides functionality for checking for updates by querying
the GitHub API for releases.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple, Union

import aiohttp
from packaging import version

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class ReleaseInfo:
    """Information about a release."""
    version: str
    tag_name: str
    name: str
    body: str
    html_url: str
    published_at: str
    prerelease: bool
    assets: List[Dict[str, Any]]
    download_url: Optional[str] = None


class UpdateChecker:
    """
    Checker for updates.
    
    This class provides functionality for checking for updates by querying
    the GitHub API for releases.
    """

    def __init__(
        self,
        repo_owner: str,
        repo_name: str,
        current_version: str,
        github_api_url: str = "https://api.github.com",
        github_token: Optional[str] = None
    ):
        """
        Initialize the update checker.
        
        Args:
            repo_owner: The owner of the GitHub repository.
            repo_name: The name of the GitHub repository.
            current_version: The current version of the software.
            github_api_url: The GitHub API URL (default: "https://api.github.com").
            github_token: Optional GitHub API token for authentication.
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.current_version = current_version
        self.github_api_url = github_api_url
        self.github_token = github_token

    async def check_for_updates(
        self,
        include_prereleases: bool = False
    ) -> Tuple[bool, Optional[ReleaseInfo]]:
        """
        Check for updates.
        
        Args:
            include_prereleases: Whether to include prereleases (default: False).
        
        Returns:
            A tuple containing:
            - A boolean indicating whether an update is available.
            - The latest release information, or None if no update is available.
        """
        logger.info(f"Checking for updates (current version: {self.current_version})")
        
        # Get releases from GitHub API
        releases = await self._get_releases()
        
        if not releases:
            logger.info("No releases found")
            return False, None
        
        # Parse current version
        try:
            current_version_parsed = version.parse(self.current_version)
        except version.InvalidVersion:
            logger.error(f"Invalid current version: {self.current_version}")
            return False, None
        
        # Find latest release
        latest_release = None
        for release in releases:
            # Skip prereleases if not included
            if release["prerelease"] and not include_prereleases:
                continue
            
            # Parse version from tag name
            tag_name = release["tag_name"]
            version_match = re.search(r"v?(\d+\.\d+\.\d+)", tag_name)
            if not version_match:
                logger.warning(f"Could not parse version from tag name: {tag_name}")
                continue
            
            release_version_str = version_match.group(1)
            
            try:
                release_version = version.parse(release_version_str)
            except version.InvalidVersion:
                logger.warning(f"Invalid release version: {release_version_str}")
                continue
            
            # Check if this release is newer than the current version
            if release_version > current_version_parsed:
                # Create release info
                release_info = self._create_release_info(release)
                
                # Check if this is the latest release
                if latest_release is None or version.parse(release_info.version) > version.parse(latest_release.version):
                    latest_release = release_info
        
        if latest_release is not None:
            logger.info(f"Update available: {latest_release.version}")
            return True, latest_release
        else:
            logger.info("No update available")
            return False, None

    async def _get_releases(self) -> List[Dict[str, Any]]:
        """
        Get releases from GitHub API.
        
        Returns:
            A list of release dictionaries.
        """
        url = f"{self.github_api_url}/repos/{self.repo_owner}/{self.repo_name}/releases"
        
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error getting releases: {response.status} {await response.text()}")
                    return []

    def _create_release_info(self, release: Dict[str, Any]) -> ReleaseInfo:
        """
        Create release information from a GitHub API release.
        
        Args:
            release: The GitHub API release dictionary.
        
        Returns:
            A ReleaseInfo object.
        """
        # Parse version from tag name
        tag_name = release["tag_name"]
        version_match = re.search(r"v?(\d+\.\d+\.\d+)", tag_name)
        if version_match:
            version_str = version_match.group(1)
        else:
            version_str = tag_name
        
        # Find download URL for the appropriate asset
        download_url = None
        assets = release.get("assets", [])
        
        # Get system information
        import platform
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Find appropriate asset for the current system
        for asset in assets:
            asset_name = asset["name"].lower()
            
            # Check if asset is appropriate for the current system
            if system == "windows" and asset_name.endswith(".exe"):
                download_url = asset["browser_download_url"]
                break
            elif system == "darwin" and asset_name.endswith(".dmg"):
                download_url = asset["browser_download_url"]
                break
            elif system == "linux" and asset_name.endswith(".deb") and "amd64" in asset_name and machine == "x86_64":
                download_url = asset["browser_download_url"]
                break
            elif system == "linux" and asset_name.endswith(".deb") and "arm64" in asset_name and machine == "aarch64":
                download_url = asset["browser_download_url"]
                break
            elif asset_name.endswith(".tar.gz") or asset_name.endswith(".zip"):
                # Use archive as fallback
                download_url = asset["browser_download_url"]
        
        # If no appropriate asset found, use the source code
        if download_url is None and "tarball_url" in release:
            download_url = release["tarball_url"]
        
        return ReleaseInfo(
            version=version_str,
            tag_name=release["tag_name"],
            name=release["name"],
            body=release["body"],
            html_url=release["html_url"],
            published_at=release["published_at"],
            prerelease=release["prerelease"],
            assets=assets,
            download_url=download_url
        )
