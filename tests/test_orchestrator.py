import subprocess
import tempfile
import sqlite3
from pathlib import Path
import pytest
import sys


@pytest.fixture
def setup_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()
        archive_dir = data_dir / "archive"
        archive_dir.mkdir()
        incoming_dir = data_dir / "incoming"
        incoming_dir.mkdir()
        db_path = data_dir / "metadata.db"
        # создаём временный файл для добавления
        test_file = incoming_dir / "test.txt"
        test_file.write_text("Hello, Glyph!")
        yield {
            "root": Path(tmpdir),
            "data": data_dir,
            "archive": archive_dir,
            "incoming": incoming_dir,
            "db": db_path,
            "test_file": test_file,
        }


def test_cli_add_verify_list(setup_env):
    env = setup_env
    # подменяем конфиг или используем переменные окружения / проще запустить с реальным конфигом, но нужно временно переопределить пути.
    # В тестах можно временно изменить settings.json через подстановку или мок.
    # Упростим: будем использовать реальный конфиг, но передадим через аргументы командной строки? В текущем orchestrator.py нет возможности передать конфиг через аргументы.
    # Поэтому напишем тест, который копирует settings.example.json в settings.json с подменой путей на временные.
    config_src = Path("config/settings.example.json")
    config_dst = Path("config/settings.json")
    if config_dst.exists():
        config_dst.unlink()
    # читаем пример и заменяем пути
    import json

    with open(config_src) as f:
        config = json.load(f)
    config["storage"]["incoming_dir"] = str(env["incoming"])
    config["storage"]["archive_dir"] = str(env["archive"])
    config["metadata"]["database"] = str(env["db"])
    config["logging"]["file"] = str(env["root"] / "glyph.log")
    with open(config_dst, "w") as f:
        json.dump(config, f, indent=2)

    try:
        # add
        cmd = ["python", "-m", "core.orchestrator", "list"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        # Проверим, что файл скопирован в архив
        archived = list(env["archive"].glob("*"))
        assert len(archived) == 1
        assert archived[0].name == "test.txt"

        # Проверим запись в БД
        conn = sqlite3.connect(env["db"])
        cursor = conn.execute("SELECT * FROM books")
        rows = cursor.fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][1] == str(archived[0])  # file_path

        # verify
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "core.orchestrator",
                "verify",
                str(archived[0]),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # list
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "core.orchestrator",
                "list",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Test" in result.stdout

    finally:
        if config_dst.exists():
            config_dst.unlink()
