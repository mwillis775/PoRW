#!/usr/bin/env python
"""
Build binary distributions of the PoRW blockchain system for various platforms.
This script uses PyInstaller to create standalone executables.
"""

import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path

# Define the entry points to create executables for
ENTRY_POINTS = {
    "porw-node": "src/porw_blockchain/bin/porw-node.py",
    "porw-storage": "src/porw_blockchain/bin/porw-storage.py",
    "porw-web": "src/porw_blockchain/web/app.py",
    "porw-shell": "src/porw_blockchain/cli/shell.py",
}

# Define the platforms to build for
PLATFORMS = {
    "windows": {
        "extension": ".exe",
        "dist_dir": "dist/windows",
    },
    "linux": {
        "extension": "",
        "dist_dir": "dist/linux",
    },
    "darwin": {
        "extension": "",
        "dist_dir": "dist/macos",
    },
}


def install_dependencies():
    """Install required dependencies for building."""
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)


def build_binary(entry_point_name, entry_point_path, platform_info):
    """Build a binary for a specific entry point and platform."""
    print(f"Building {entry_point_name} for {platform.system()}...")
    
    # Create the output directory
    os.makedirs(platform_info["dist_dir"], exist_ok=True)
    
    # Build the binary
    subprocess.run([
        "pyinstaller",
        "--onefile",
        "--name", f"{entry_point_name}{platform_info['extension']}",
        "--distpath", platform_info["dist_dir"],
        "--add-data", "src/porw_blockchain/web/templates:porw_blockchain/web/templates",
        "--add-data", "src/porw_blockchain/web/static:porw_blockchain/web/static",
        entry_point_path,
    ], check=True)
    
    print(f"Built {entry_point_name} for {platform.system()} in {platform_info['dist_dir']}")


def create_archive(platform_info):
    """Create an archive of the binaries for distribution."""
    platform_name = platform.system().lower()
    archive_name = f"porw-blockchain-{platform_name}"
    
    if platform_name == "windows":
        # Create a ZIP archive on Windows
        shutil.make_archive(archive_name, "zip", platform_info["dist_dir"])
        print(f"Created {archive_name}.zip")
    else:
        # Create a tarball on Linux/macOS
        shutil.make_archive(archive_name, "gztar", platform_info["dist_dir"])
        print(f"Created {archive_name}.tar.gz")


def main():
    """Main function to build binaries for the current platform."""
    # Get the current platform
    current_platform = platform.system().lower()
    if current_platform not in PLATFORMS:
        print(f"Unsupported platform: {current_platform}")
        sys.exit(1)
    
    platform_info = PLATFORMS[current_platform]
    
    # Install dependencies
    install_dependencies()
    
    # Build binaries for each entry point
    for entry_point_name, entry_point_path in ENTRY_POINTS.items():
        build_binary(entry_point_name, entry_point_path, platform_info)
    
    # Create an archive for distribution
    create_archive(platform_info)


if __name__ == "__main__":
    main()
