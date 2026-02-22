#!/usr/bin/env python3
import tempfile
import subprocess
import time
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        files = []
        for i in range(100):
            p = Path(tmpdir) / f"f{i}.txt"
            p.write_text("x" * 1024)
            files.append(p)

        start = time.time()
        for f in files:
            subprocess.run(
                ["python", "core/orchestrator.py", "add", str(f)], capture_output=True
            )
        elapsed = time.time() - start
        print(f"Added {len(files)} files in {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()
