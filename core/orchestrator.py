#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import json
from pathlib import Path
import sqlite3

# Добавляем путь к проекту для импортов
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.logger import setup_logger, AuditLogger
from core.metadata_store import MetadataStore
from core.ipc import ModuleIPC
from core import RemoteStorage

def load_config():
    config_path = PROJECT_ROOT / "config" / "settings.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}. Copy from settings.example.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    try:
        config = load_config()
    except Exception as e:
        print(f"FATAL: Cannot load config: {e}")
        sys.exit(1)

    logger = setup_logger(config)
    audit = AuditLogger(Path("./logs/audit.jsonl"))  # отдельный аудит-лог

    # Инициализация хранилища метаданных
    try:
        store = MetadataStore(db_path=config["metadata"]["database"], logger=logger)
    except Exception as e:
        logger.error(f"Metadata store init failed: {e}")
        sys.exit(1)

    # Инициализация удалённого хранилища
    remote = RemoteStorage(config["storage"], logger=logger)

    # Инициализация крипто-модуля (если включён)
    crypto_ipc = None
    if config["modules"].get("crypto", {}).get("enabled"):
        crypto_path = PROJECT_ROOT / config["modules"]["crypto"]["path"]
        try:
            crypto_ipc = ModuleIPC(crypto_path, logger=logger)
        except Exception as e:
            logger.error(f"Crypto module init failed: {e}")
            sys.exit(1)

    parser = argparse.ArgumentParser(description="Glyph CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    add_parser = subparsers.add_parser("add", help="Add a file")
    add_parser.add_argument("file", help="Path to file")
    add_parser.add_argument("--title", help="Title")
    add_parser.add_argument("--author", help="Author")
    add_parser.add_argument("--tags", help="Comma-separated tags")
    add_parser.add_argument("--no-verify", action="store_true", help="Skip copy verification")

    # verify
    verify_parser = subparsers.add_parser("verify", help="Verify file integrity")
    verify_parser.add_argument("file", help="Path to file")

    # list
    list_parser = subparsers.add_parser("list", help="List recent entries")
    list_parser.add_argument("--limit", type=int, default=20, help="Limit entries")

    args = parser.parse_args()

    if args.command == "add":
        file_path = Path(args.file).expanduser().resolve()
        if not file_path.is_file():
            logger.error(f"File not found: {file_path}")
            sys.exit(1)

        logger.info(f"Adding file: {file_path}")

        # Вычисляем хеш через внешний модуль или локально
        if crypto_ipc:
            try:
                with open(file_path, "rb") as f:
                    data = f.read()
                req = {"cmd": "hash", "data": data.hex(), "algorithm": config["security"]["hash_algo"]}
                resp = crypto_ipc.call(req)
                if "error" in resp:
                    logger.error(f"Crypto module error: {resp['error']}")
                    sys.exit(1)
                file_hash = resp["result"]
            except Exception as e:
                logger.error(f"Hash computation failed: {e}")
                sys.exit(1)
        else:
            # fallback на встроенную функцию (но мы хотим использовать внешний модуль)
            from core.file_handler import calculate_hash
            file_hash = calculate_hash(file_path, algorithm=config["security"]["hash_algo"], logger=logger)

        existing = store.get_entry_by_hash(file_hash)
        if existing:
            logger.warning(f"Duplicate hash! Existing entry ID {existing['id']}")
            sys.exit(1)

        metadata = {
            "title": args.title if args.title else file_path.stem,
            "author": args.author if args.author else "Unknown",
            "tags": args.tags.split(",") if args.tags else [],
            "original_filename": file_path.name,
            "size_bytes": file_path.stat().st_size,
        }

        # Целевой путь в архиве
        archive_dir = Path(config["storage"]["archive_dir"])
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / file_path.name
        if archive_path.exists():
            base = archive_path.stem
            suffix = archive_path.suffix
            counter = 1
            while archive_path.exists():
                archive_path = archive_dir / f"{base}_{counter}{suffix}"
                counter += 1
            logger.info(f"Using archive path: {archive_path}")

        # Копирование с проверкой
        from core.file_handler import copy_file_with_verify
        try:
            copy_file_with_verify(file_path, archive_path, verify=not args.no_verify, logger=logger)
        except Exception as e:
            logger.error(f"Copy failed: {e}")
            sys.exit(1)

        # Шифрование, если включено
        if config["security"]["encryption"]["enabled"] and crypto_ipc:
            enc_config = config["security"]["encryption"]
            key = os.environ.get(enc_config["key_env_var"])
            if not key:
                logger.error(f"Encryption enabled but env var {enc_config['key_env_var']} not set")
                sys.exit(1)
            try:
                with open(archive_path, "rb") as f:
                    data = f.read()
                req = {"cmd": "encrypt", "data": data.hex(), "key": key, "algorithm": enc_config["algorithm"]}
                resp = crypto_ipc.call(req)
                if "error" in resp:
                    logger.error(f"Encryption error: {resp['error']}")
                    sys.exit(1)
                encrypted_data = bytes.fromhex(resp["result"])
                encrypted_path = archive_path.with_suffix(archive_path.suffix + ".enc")
                encrypted_path.write_bytes(encrypted_data)
                archive_path.unlink()  # удаляем незашифрованный
                archive_path = encrypted_path
                logger.info(f"File encrypted: {encrypted_path}")
            except Exception as e:
                logger.error(f"Encryption failed: {e}")
                sys.exit(1)

        # Отправка на удалённое хранилище
        remote.send_file(archive_path)

        # Сохраняем в БД
        try:
            entry_id = store.add_entry(str(archive_path), file_hash, metadata)
            logger.info(f"✅ Entry added with ID {entry_id}")
            audit.log("file_added", {"file": str(archive_path), "hash": file_hash, "id": entry_id})
        except sqlite3.IntegrityError:
            logger.error("Database integrity error")
            sys.exit(1)

    elif args.command == "verify":
        file_path = Path(args.file).expanduser().resolve()
        if not file_path.is_file():
            logger.error(f"File not found: {file_path}")
            sys.exit(1)

        entry = store.get_entry_by_path(str(file_path))
        if not entry:
            logger.warning(f"No entry found for {file_path}")
            sys.exit(1)

        # Вычисляем хеш
        if crypto_ipc:
            try:
                with open(file_path, "rb") as f:
                    data = f.read()
                req = {"cmd": "hash", "data": data.hex(), "algorithm": config["security"]["hash_algo"]}
                resp = crypto_ipc.call(req)
                if "error" in resp:
                    logger.error(f"Crypto module error: {resp['error']}")
                    sys.exit(1)
                current_hash = resp["result"]
            except Exception as e:
                logger.error(f"Hash computation failed: {e}")
                sys.exit(1)
        else:
            from core.file_handler import calculate_hash
            current_hash = calculate_hash(file_path, algorithm=config["security"]["hash_algo"], logger=logger)

        if current_hash == entry["hash"]:
            logger.info("✅ Integrity verified")
            store.update_verification(str(file_path), True)
            audit.log("verify_success", {"file": str(file_path), "hash": current_hash})
        else:
            logger.error("❌ Integrity check failed")
            store.update_verification(str(file_path), False)
            audit.log("verify_failed", {"file": str(file_path), "expected": entry["hash"], "actual": current_hash})
            sys.exit(1)

    elif args.command == "list":
        entries = store.list_entries(limit=args.limit)
        if not entries:
            print("No entries.")
        else:
            print(f"\nLast {len(entries)} entries:\n")
            for e in entries:
                verified = "✅" if e["verified"] else "❌"
                print(f"ID: {e['id']} {verified}")
                print(f"  File: {e['file_path']}")
                print(f"  Title: {e['metadata'].get('title', 'N/A')}")
                print(f"  Author: {e['metadata'].get('author', 'N/A')}")
                print(f"  Added: {e['added']}\n")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
