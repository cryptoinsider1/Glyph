"""
Простой нагрузочный тест: многократное добавление файлов.
Запуск: pytest tests/load/test_load.py -s --count=100
"""

from pathlib import Path
import tempfile
import subprocess
import time


def test_load_add_files(benchmark):
    # не идеально, но для демонстрации
    with tempfile.TemporaryDirectory() as tmpdir:
        # генерируем много маленьких файлов
        file_paths = []
        for i in range(100):
            p = Path(tmpdir) / f"file{i}.txt"
            p.write_text(f"data{i}" * 100)
            file_paths.append(p)

        # замеряем время добавления
        start = time.time()
        for f in file_paths:
            subprocess.run(
                f"python core/orchestrator.py add {f}", shell=True, capture_output=True
            )
        duration = time.time() - start
        print(f"\nAdded 100 files in {duration:.2f} seconds")
