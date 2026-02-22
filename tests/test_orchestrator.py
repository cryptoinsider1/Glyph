import subprocess
import tempfile
from pathlib import Path

def test_add_and_verify():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Создаём временный файл
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Hello, Glyph!")
        # Запускаем добавление
        cmd = f"python core/orchestrator.py add {test_file} --title 'Test' --author 'Tester'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        # Проверяем лог
        # ... упрощённо
