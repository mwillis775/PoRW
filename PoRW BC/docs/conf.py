# docs/conf.py
# Configuration file for the Sphinx documentation builder.

import os
import sys

# Add project source directory to the path for autodoc
sys.path.insert(0, os.path.abspath('../src'))

# -- Project information -----------------------------------------------------
project = 'PoRW Blockchain Node'
copyright = '2025, <Your Name or Organization>' # Update copyright
author = '<Your Name or Organization>' # Update author
release = '0.1.0' # The full version, including alpha/beta/rc tags

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',  # Include documentation from docstrings
    'sphinx.ext.napoleon', # Support for Google and NumPy style docstrings
    'sphinx.ext.intersphinx', # Link to other projects' documentation
    'sphinx.ext.viewcode', # Add links to source code
    'sphinx_rtd_theme',    # Read the Docs theme
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Map documentation for other projects (e.g., Python standard library)
intersphinx_mapping = {'python': ('https://docs.python.org/3', None)}

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static'] # Custom static files (CSS, images)

# -- Autodoc configuration ---------------------------------------------------
autodoc_member_order = 'bysource' # Order members by source code order
# autodoc_default_options = {
#     'members': True,
#     'undoc-members': True, # Include members without docstrings (use with caution)
#     'private-members': False,
#     'special-members': '__init__',
#     'show-inheritance': True,
# }