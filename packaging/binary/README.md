# PoRW Blockchain Binary Distributions

This directory contains binary distributions of the PoRW blockchain system for various platforms.

## Available Platforms

- Windows (64-bit)
- Linux (64-bit)
- macOS (64-bit)

## Installation

### Windows

1. Download the latest `porw-blockchain-windows.zip` from the [releases page](https://github.com/mwillis775/PoRW-PoRS/releases)
2. Extract the ZIP file to a directory of your choice
3. Add the directory to your PATH or run the executables directly

### Linux

1. Download the latest `porw-blockchain-linux.tar.gz` from the [releases page](https://github.com/mwillis775/PoRW-PoRS/releases)
2. Extract the tarball:
   ```bash
   tar -xzf porw-blockchain-linux.tar.gz
   ```
3. Move the executables to a directory in your PATH:
   ```bash
   sudo mv porw-blockchain-linux/* /usr/local/bin/
   ```

### macOS

1. Download the latest `porw-blockchain-darwin.tar.gz` from the [releases page](https://github.com/mwillis775/PoRW-PoRS/releases)
2. Extract the tarball:
   ```bash
   tar -xzf porw-blockchain-darwin.tar.gz
   ```
3. Move the executables to a directory in your PATH:
   ```bash
   sudo mv porw-blockchain-darwin/* /usr/local/bin/
   ```

## Usage

The binary distribution includes the following executables:

- `porw-node`: The main blockchain node
- `porw-storage`: The storage node
- `porw-web`: The web interface
- `porw-shell`: The interactive shell

### Running the Blockchain Node

```bash
porw-node --listen-port 8333 --data-dir ~/.porw/node --log-level INFO
```

### Running the Storage Node

```bash
porw-storage --storage-dir ~/.porw/storage --max-storage 1024 --min-replication 3
```

### Running the Web Interface

```bash
porw-web --host 0.0.0.0 --port 8080
```

### Running the Interactive Shell

```bash
porw-shell
```

## Building from Source

If you prefer to build the binaries yourself, you can use the provided build script:

```bash
# Clone the repository
git clone https://github.com/mwillis775/PoRW-PoRS.git
cd PoRW-PoRS

# Install dependencies
pip install -e .
pip install pyinstaller

# Run the build script
python packaging/build_binary.py
```

This will create binaries for your current platform in the `dist/` directory.
