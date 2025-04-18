# PoRW Blockchain PyPI Packaging

This directory contains information about packaging the PoRW blockchain system for PyPI distribution.

## Package Structure

The PoRW blockchain package is structured as follows:

- `src/porw_blockchain/`: Main Python package
- `pyproject.toml`: Poetry configuration file
- `setup.py`: Setuptools configuration file (for compatibility)
- `MANIFEST.in`: List of non-Python files to include in the package

## Building the Package

### Using Poetry (Recommended)

```bash
# Build the package
poetry build

# This will create both .tar.gz and .whl files in the dist/ directory
```

### Using Setuptools

```bash
# Build the package
python setup.py sdist bdist_wheel
```

## Publishing to PyPI

### Using Poetry (Recommended)

```bash
# Publish to PyPI
poetry publish

# Or publish to TestPyPI
poetry publish -r testpypi
```

### Using Twine

```bash
# Install twine
pip install twine

# Upload to PyPI
twine upload dist/*

# Or upload to TestPyPI
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

## Installation

Once published, users can install the package using pip:

```bash
# Install the basic package
pip install porw-blockchain

# Install with mining extras
pip install porw-blockchain[mining]

# Install with storage extras
pip install porw-blockchain[storage]

# Install with web interface extras
pip install porw-blockchain[web]

# Install with all extras
pip install porw-blockchain[all]
```

## Version Management

The package version is defined in `pyproject.toml`. To update the version:

```bash
# Update the version
poetry version patch  # or minor, major, etc.

# Build and publish the new version
poetry build
poetry publish
```

## Binary Distributions

For platforms where installing from PyPI might be challenging (e.g., due to dependencies like PyRosetta), consider providing binary distributions:

1. Build the package on each target platform
2. Create platform-specific installers or packages
3. Distribute through GitHub releases or a dedicated download page
