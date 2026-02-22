.PHONY: help setup build test run clean

help:
	@echo "Glyph Makefile"
	@echo "  setup      – create virtual env and install Python dependencies"
	@echo "  build      – build Rust crypto module"
	@echo "  test       – run all tests"
	@echo "  run        – run orchestrator CLI (example: make run CMD='add ~/file.pdf')"
	@echo "  clean      – remove build artifacts and data"

setup:
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r modules/ai_python/requirements.txt
	@echo "Virtual env created. Activate with: source venv/bin/activate"

build:
	cd modules/crypto_rust && cargo build --release
	@echo "Rust module built at modules/crypto_rust/target/release/crypto_rust"

test:
	. venv/bin/activate && PYTHONPATH=. pytest tests/ -v

run:
	. venv/bin/activate && PYTHONPATH=. python core/orchestrator.py $(CMD)

clean:
	rm -rf venv
	rm -rf data/
	rm -rf logs/
	cd modules/crypto_rust && cargo clean
	find . -type d -name "__pycache__" -exec rm -rf {} +
