# src/porw_blockchain/update/installer.py
"""
Update installer for the PoRW blockchain.

This module provides functionality for installing updates and rolling back
to previous versions if necessary.
"""

import asyncio
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union

# Configure logger
logger = logging.getLogger(__name__)


class UpdateInstaller:
    """
    Installer for updates.
    
    This class provides functionality for installing updates and rolling back
    to previous versions if necessary.
    """

    def __init__(self, backup_dir: Path):
        """
        Initialize the update installer.
        
        Args:
            backup_dir: The directory to store backups in.
        """
        self.backup_dir = backup_dir
        
        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Get installation directory
        self.install_dir = Path(sys.prefix)
        
        # Get executable path
        self.executable_path = Path(sys.executable)

    async def install_update(self, update_path: Path) -> bool:
        """
        Install an update.
        
        Args:
            update_path: The path to the update to install.
        
        Returns:
            True if the update was installed successfully, False otherwise.
        """
        logger.info(f"Installing update from {update_path}")
        
        # Create backup before installing
        backup_path = await self._create_backup()
        if not backup_path:
            logger.error("Failed to create backup")
            return False
        
        # Determine installation method based on file type
        if update_path.suffix == ".zip":
            success = await self._install_from_zip(update_path)
        elif update_path.suffix in [".tar", ".gz", ".bz2", ".xz"]:
            success = await self._install_from_tar(update_path)
        elif update_path.suffix == ".exe" and platform.system() == "Windows":
            success = await self._install_from_exe(update_path)
        elif update_path.suffix == ".dmg" and platform.system() == "Darwin":
            success = await self._install_from_dmg(update_path)
        elif update_path.suffix == ".deb" and platform.system() == "Linux":
            success = await self._install_from_deb(update_path)
        elif update_path.suffix == ".rpm" and platform.system() == "Linux":
            success = await self._install_from_rpm(update_path)
        elif update_path.suffix == ".whl":
            success = await self._install_from_wheel(update_path)
        else:
            logger.error(f"Unsupported update file type: {update_path.suffix}")
            return False
        
        if not success:
            logger.error("Update installation failed")
            
            # Try to restore from backup
            if not self.rollback_update():
                logger.error("Failed to rollback update")
            
            return False
        
        logger.info("Update installed successfully")
        return True

    async def _create_backup(self) -> Optional[Path]:
        """
        Create a backup of the current installation.
        
        Returns:
            The path to the backup, or None if backup creation failed.
        """
        logger.info("Creating backup of current installation")
        
        try:
            # Create backup directory with timestamp
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            backup_path = self.backup_dir / f"backup-{timestamp}"
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Copy current installation to backup directory
            if platform.system() == "Windows":
                # On Windows, copy the entire installation directory
                for item in self.install_dir.glob("*"):
                    if item.is_dir():
                        shutil.copytree(item, backup_path / item.name)
                    else:
                        shutil.copy2(item, backup_path / item.name)
            else:
                # On Unix-like systems, copy the Python package
                package_dir = self.install_dir / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "porw_blockchain"
                if package_dir.exists():
                    shutil.copytree(package_dir, backup_path / "porw_blockchain")
                else:
                    logger.warning(f"Package directory not found: {package_dir}")
            
            logger.info(f"Backup created at {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None

    def rollback_update(self) -> bool:
        """
        Rollback to the previous version.
        
        Returns:
            True if the rollback was successful, False otherwise.
        """
        logger.info("Rolling back update")
        
        try:
            # Find the latest backup
            backups = list(self.backup_dir.glob("backup-*"))
            if not backups:
                logger.error("No backups found")
                return False
            
            # Sort backups by modification time (newest first)
            backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            latest_backup = backups[0]
            
            logger.info(f"Rolling back to backup at {latest_backup}")
            
            # Restore from backup
            if platform.system() == "Windows":
                # On Windows, restore the entire installation directory
                for item in latest_backup.glob("*"):
                    dest_path = self.install_dir / item.name
                    if dest_path.exists():
                        if dest_path.is_dir():
                            shutil.rmtree(dest_path)
                        else:
                            dest_path.unlink()
                    
                    if item.is_dir():
                        shutil.copytree(item, dest_path)
                    else:
                        shutil.copy2(item, dest_path)
            else:
                # On Unix-like systems, restore the Python package
                package_dir = self.install_dir / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "porw_blockchain"
                if package_dir.exists():
                    shutil.rmtree(package_dir)
                
                backup_package_dir = latest_backup / "porw_blockchain"
                if backup_package_dir.exists():
                    shutil.copytree(backup_package_dir, package_dir)
                else:
                    logger.warning(f"Backup package directory not found: {backup_package_dir}")
            
            logger.info("Rollback completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error rolling back update: {e}")
            return False

    async def _install_from_zip(self, zip_path: Path) -> bool:
        """
        Install an update from a zip file.
        
        Args:
            zip_path: The path to the zip file.
        
        Returns:
            True if the installation was successful, False otherwise.
        """
        logger.info(f"Installing from zip file: {zip_path}")
        
        try:
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract zip file
                with zipfile.ZipFile(zip_path, "r") as zip_file:
                    zip_file.extractall(temp_path)
                
                # Find the package directory
                package_dir = None
                for item in temp_path.glob("**/porw_blockchain"):
                    if item.is_dir():
                        package_dir = item
                        break
                
                if not package_dir:
                    logger.error("Package directory not found in zip file")
                    return False
                
                # Install the package
                return await self._install_from_directory(package_dir)
        except Exception as e:
            logger.error(f"Error installing from zip file: {e}")
            return False

    async def _install_from_tar(self, tar_path: Path) -> bool:
        """
        Install an update from a tar file.
        
        Args:
            tar_path: The path to the tar file.
        
        Returns:
            True if the installation was successful, False otherwise.
        """
        logger.info(f"Installing from tar file: {tar_path}")
        
        try:
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract tar file
                with tarfile.open(tar_path, "r:*") as tar_file:
                    tar_file.extractall(temp_path)
                
                # Find the package directory
                package_dir = None
                for item in temp_path.glob("**/porw_blockchain"):
                    if item.is_dir():
                        package_dir = item
                        break
                
                if not package_dir:
                    logger.error("Package directory not found in tar file")
                    return False
                
                # Install the package
                return await self._install_from_directory(package_dir)
        except Exception as e:
            logger.error(f"Error installing from tar file: {e}")
            return False

    async def _install_from_directory(self, source_dir: Path) -> bool:
        """
        Install an update from a directory.
        
        Args:
            source_dir: The path to the directory containing the package.
        
        Returns:
            True if the installation was successful, False otherwise.
        """
        logger.info(f"Installing from directory: {source_dir}")
        
        try:
            # Determine destination directory
            if platform.system() == "Windows":
                # On Windows, install to the site-packages directory
                dest_dir = self.install_dir / "Lib" / "site-packages" / "porw_blockchain"
            else:
                # On Unix-like systems, install to the site-packages directory
                dest_dir = self.install_dir / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "porw_blockchain"
            
            # Remove existing package
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            
            # Copy new package
            shutil.copytree(source_dir, dest_dir)
            
            logger.info(f"Package installed to {dest_dir}")
            return True
        except Exception as e:
            logger.error(f"Error installing from directory: {e}")
            return False

    async def _install_from_exe(self, exe_path: Path) -> bool:
        """
        Install an update from an executable file (Windows).
        
        Args:
            exe_path: The path to the executable file.
        
        Returns:
            True if the installation was successful, False otherwise.
        """
        logger.info(f"Installing from executable: {exe_path}")
        
        try:
            # Run the installer
            process = await asyncio.create_subprocess_exec(
                str(exe_path),
                "/SILENT",  # Silent installation
                "/NORESTART",  # Don't restart the computer
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Installer failed with return code {process.returncode}")
                logger.error(f"Stdout: {stdout.decode()}")
                logger.error(f"Stderr: {stderr.decode()}")
                return False
            
            logger.info("Installer completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error installing from executable: {e}")
            return False

    async def _install_from_dmg(self, dmg_path: Path) -> bool:
        """
        Install an update from a DMG file (macOS).
        
        Args:
            dmg_path: The path to the DMG file.
        
        Returns:
            True if the installation was successful, False otherwise.
        """
        logger.info(f"Installing from DMG: {dmg_path}")
        
        try:
            # Create temporary directory for mounting
            with tempfile.TemporaryDirectory() as temp_dir:
                mount_point = Path(temp_dir) / "dmg"
                mount_point.mkdir()
                
                # Mount the DMG
                process = await asyncio.create_subprocess_exec(
                    "hdiutil",
                    "attach",
                    str(dmg_path),
                    "-mountpoint",
                    str(mount_point),
                    "-nobrowse",
                    "-quiet",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Failed to mount DMG: {stderr.decode()}")
                    return False
                
                try:
                    # Find the app bundle
                    app_bundle = None
                    for item in mount_point.glob("*.app"):
                        if item.is_dir():
                            app_bundle = item
                            break
                    
                    if not app_bundle:
                        logger.error("App bundle not found in DMG")
                        return False
                    
                    # Copy the app bundle to the Applications directory
                    applications_dir = Path("/Applications")
                    dest_app = applications_dir / app_bundle.name
                    
                    # Remove existing app if it exists
                    if dest_app.exists():
                        shutil.rmtree(dest_app)
                    
                    # Copy the app bundle
                    shutil.copytree(app_bundle, dest_app)
                    
                    logger.info(f"App installed to {dest_app}")
                    return True
                finally:
                    # Unmount the DMG
                    process = await asyncio.create_subprocess_exec(
                        "hdiutil",
                        "detach",
                        str(mount_point),
                        "-quiet",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    await process.communicate()
        except Exception as e:
            logger.error(f"Error installing from DMG: {e}")
            return False

    async def _install_from_deb(self, deb_path: Path) -> bool:
        """
        Install an update from a DEB file (Debian/Ubuntu).
        
        Args:
            deb_path: The path to the DEB file.
        
        Returns:
            True if the installation was successful, False otherwise.
        """
        logger.info(f"Installing from DEB: {deb_path}")
        
        try:
            # Run the installer
            process = await asyncio.create_subprocess_exec(
                "sudo",
                "dpkg",
                "-i",
                str(deb_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Installer failed with return code {process.returncode}")
                logger.error(f"Stdout: {stdout.decode()}")
                logger.error(f"Stderr: {stderr.decode()}")
                
                # Try to fix dependencies
                process = await asyncio.create_subprocess_exec(
                    "sudo",
                    "apt-get",
                    "install",
                    "-f",
                    "-y",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Failed to fix dependencies: {stderr.decode()}")
                    return False
                
                logger.info("Dependencies fixed, installation completed")
                return True
            
            logger.info("Installer completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error installing from DEB: {e}")
            return False

    async def _install_from_rpm(self, rpm_path: Path) -> bool:
        """
        Install an update from an RPM file (Fedora/RHEL/CentOS).
        
        Args:
            rpm_path: The path to the RPM file.
        
        Returns:
            True if the installation was successful, False otherwise.
        """
        logger.info(f"Installing from RPM: {rpm_path}")
        
        try:
            # Run the installer
            process = await asyncio.create_subprocess_exec(
                "sudo",
                "rpm",
                "-U",
                "--force",
                str(rpm_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Installer failed with return code {process.returncode}")
                logger.error(f"Stdout: {stdout.decode()}")
                logger.error(f"Stderr: {stderr.decode()}")
                return False
            
            logger.info("Installer completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error installing from RPM: {e}")
            return False

    async def _install_from_wheel(self, wheel_path: Path) -> bool:
        """
        Install an update from a wheel file.
        
        Args:
            wheel_path: The path to the wheel file.
        
        Returns:
            True if the installation was successful, False otherwise.
        """
        logger.info(f"Installing from wheel: {wheel_path}")
        
        try:
            # Run pip to install the wheel
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "--force-reinstall",
                str(wheel_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Pip install failed with return code {process.returncode}")
                logger.error(f"Stdout: {stdout.decode()}")
                logger.error(f"Stderr: {stderr.decode()}")
                return False
            
            logger.info("Pip install completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error installing from wheel: {e}")
            return False
