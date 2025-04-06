/porw-blockchain
|
|-- .github/
|   `-- workflows/
|       `-- python-ci.yml  # (Includes linting, bandit, testing)
|-- client/
|   `-- ... (Remains largely the same, JS framework TBD)
|-- src/
|   `-- porw_blockchain/  # Main Python package source
|       |-- __init__.py
|       |-- core/
|       |   |-- __init__.py
|       |   |-- consensus.py
|       |   |-- structures.py  # (Block, Transaction classes)
|       |   `-- validation.py
|       |-- node/
|       |   |-- __init__.py
|       |   |-- p2p.py
|       |   `-- sync.py
|       |-- rpc/
|       |   |-- __init__.py
|       |   |-- main.py        # (FastAPI app definition)
|       |   |-- routers/       # (API endpoint definitions)
|       |   |   `-- __init__.py
|       |   `-- schemas.py     # (Pydantic models)
|       |-- storage/
|       |   |-- __init__.py
|       |   |-- database.py    # (SQLAlchemy engine, session setup)
|       |   |-- models.py      # (SQLAlchemy table models)
|       |   `-- crud.py        # (Create, Read, Update, Delete functions)
|       `-- config.py        # (App configuration loading)
|-- config/                # Static config files, templates if any
|   `-- logging.conf
|-- scripts/
|   |-- init_db.py         # (Optional: script to initialize DB schema)
|   `-- run_dev.sh         # (Script to start dev server)
|-- tests/
|   |-- __init__.py
|   |-- conftest.py        # (Pytest fixtures)
|   |-- test_core.py
|   |-- test_rpc.py
|   `-- ... (Subdirs for unit/integration maybe)
|-- docs/
|   |-- conf.py            # (Sphinx config)
|   |-- index.rst | index.md
|   |-- architecture.rst
|   `-- api.rst
|
|-- .env.example           # Example environment variables (Jeffery, Robert)
|-- .gitignore             # Python specific (Jeffery)
|-- LICENSE                # (Jeffery)
|-- README.md              # Updated for Python setup (Jeffery)
`-- pyproject.toml         # Poetry deps, build config, lint/format config (Bill, Jeffery)