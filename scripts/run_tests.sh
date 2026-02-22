#!/bin/bash
cd "$(dirname "$0")/.."
source venv/bin/activate
PYTHONPATH=. pytest tests/ -v
