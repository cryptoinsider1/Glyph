import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

project = "Glyph"
copyright = "2026, Vladimir Goncharov"
author = "Vladimir Goncharov"
release = "0.2.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",  # для Google-style docstrings
]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
