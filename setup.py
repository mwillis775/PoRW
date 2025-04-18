#!/usr/bin/env python
# setup.py is provided for compatibility with older tools
# The actual build configuration is in pyproject.toml

from setuptools import setup

if __name__ == "__main__":
    setup(
        name="porw-blockchain",
        version="0.1.0",
        description="Proof of Real Work Blockchain Node",
        author="Michael Willis",
        author_email="mwillis775@gmail.com",
        url="https://github.com/mwillis775/PoRW-PoRS",
        packages=["porw_blockchain"],
        package_dir={"": "src"},
        install_requires=[
            "fastapi>=0.110.0",
            "uvicorn[standard]>=0.29.0",
            "sqlalchemy>=2.0.29",
            "psycopg2-binary>=2.9.9",
            "python-dotenv>=1.0.1",
            "pydantic>=2.6.4",
            "cryptography>=44.0.2",
            "aiohttp>=3.11.16",
            "httpx>=0.28.1",
            "aiohttp-jinja2>=1.6",
            "ecdsa>=0.19.1",
            "base58>=2.1.1",
        ],
        extras_require={
            "mining": ["pyrosetta", "numpy", "scipy"],
            "storage": ["aiofiles", "aiohttp"],
            "web": ["aiohttp-jinja2", "jinja2"],
            "all": ["pyrosetta", "numpy", "scipy", "aiofiles", "aiohttp", "aiohttp-jinja2", "jinja2"],
        },
        entry_points={
            "console_scripts": [
                "porw-node=porw_blockchain.bin.porw-node:main",
                "porw-storage=porw_blockchain.bin.porw-storage:main",
                "porw-web=porw_blockchain.web.app:main",
                "porw-shell=porw_blockchain.cli.shell:main",
            ],
        },
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "Intended Audience :: Science/Research",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Topic :: Scientific/Engineering :: Bio-Informatics",
            "Topic :: System :: Distributed Computing",
        ],
        python_requires=">=3.10",
    )
