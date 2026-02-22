#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from core.file_handler import calculate_hash, copy_file_with_verify
from core.ipc import ModuleIPC
from core.logger import AuditLogger, setup_logger
from core.metadata_store import MetadataStore
from core.remote import RemoteStorage

# -------------------------------------------------
# Project root
# -------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]


# -------------------------------------------------
# Config
# -------------------------------------------------
def load_config() -> dict:
    config_path = PROJECT_ROOT / "config" / "settings.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config not found: {config_path}. "
            f"Copy from config/settings.example.json"
        )

    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------------------------------
# CLI parser
# -------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Glyph CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -------- ADD --------
    add_parser = subparsers.add_parser("add", help="Add a file")
    add_parser.add_argument("file", help="Path to file")
    add_parser.add_argument("--title", help="Title")
    add_parser.add_argument("--author", help="Author")
    add_parser.add_argument("--tags", help="Comma-separated tags")
    add_parser.add_argument("--no-verify", action="store_true")

    # -------- VERIFY (VERIFY++) --------
    verify_parser = subparsers.add_parser("verify", help="Verify file integrity")

    group = verify_parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--id", type=int)
    group.add_argument("--hash")
    group.add_argument("--path")

    # backward-compatible shorthand:
    verify_parser.add_argument(
        "target",
        nargs="?",
        help="Shorthand for --path",
    )

    # -------- LIST --------
    list_parser = subparsers.add_parser("list", help="List recent entries")
    list_parser.add_argument("--limit", type=int, default=20)

    return parser


# -------------------------------------------------
# Main
# -------------------------------------------------
def main() -> None:
    # ---- config ----
    try:
        config = load_config()
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: Cannot load config: {exc}")
        sys.exit(1)

    # ---- logging ----
    logger = setup_logger(config)
    audit = AuditLogger(Path("logs/audit.jsonl"))

    # ---- metadata store ----
    try:
        store = MetadataStore(
            db_path=config["metadata"]["database"],
            logger=logger,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Metadata store init failed: {exc}")
        sys.exit(1)

    # ---- remote storage ----
    remote = RemoteStorage(config["storage"], logger=logger)

    # ---- crypto module (optional) ----
    crypto_ipc: ModuleIPC | None = None
    crypto_cfg = config.get("modules", {}).get("crypto", {})
    if crypto_cfg.get("enabled"):
        crypto_path = PROJECT_ROOT / crypto_cfg["path"]
        try:
            crypto_ipc = ModuleIPC(crypto_path, logger=logger)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Crypto module init failed: {exc}")
            sys.exit(1)

    # ---- parse args ----
    parser = build_parser()
    args = parser.parse_args()

    # =================================================
    # ADD
    # =================================================
    if args.command == "add":
        file_path = Path(args.file).expanduser().resolve()
        if not file_path.is_file():
            logger.error(f"File not found: {file_path}")
            sys.exit(1)

        logger.info(f"Adding file: {file_path}")

        # ---- hash ----
        if crypto_ipc:
            data = file_path.read_bytes()
            resp = crypto_ipc.call(
                {
                    "cmd": "hash",
                    "data": data.hex(),
                    "algorithm": config["security"]["hash_algo"],
                }
            )
            if "error" in resp:
                logger.error(resp["error"])
                sys.exit(1)
            file_hash = resp["result"]
        else:
            file_hash = calculate_hash(
                file_path,
                algorithm=config["security"]["hash_algo"],
                logger=logger,
            )

        if store.get_entry_by_hash(file_hash):
            logger.warning("Duplicate file detected")
            sys.exit(1)

        metadata = {
            "title": args.title or file_path.stem,
            "author": args.author or "Unknown",
            "tags": args.tags.split(",") if args.tags else [],
            "original_filename": file_path.name,
            "size_bytes": file_path.stat().st_size,
        }

        archive_dir = Path(config["storage"]["archive_dir"])
        archive_dir.mkdir(parents=True, exist_ok=True)

        archive_path = archive_dir / file_path.name
        counter = 1
        while archive_path.exists():
            archive_path = archive_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
            counter += 1

        try:
            copy_file_with_verify(
                file_path,
                archive_path,
                verify=not args.no_verify,
                logger=logger,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Copy failed: {exc}")
            sys.exit(1)

        # ---- encryption (optional) ----
        enc_cfg = config["security"]["encryption"]
        if enc_cfg["enabled"] and crypto_ipc:
            key = os.environ.get(enc_cfg["key_env_var"])
            if not key:
                logger.error("Encryption key env var not set")
                sys.exit(1)

            data = archive_path.read_bytes()
            resp = crypto_ipc.call(
                {
                    "cmd": "encrypt",
                    "data": data.hex(),
                    "key": key,
                    "algorithm": enc_cfg["algorithm"],
                }
            )
            if "error" in resp:
                logger.error(resp["error"])
                sys.exit(1)

            encrypted_path = archive_path.with_suffix(archive_path.suffix + ".enc")
            encrypted_path.write_bytes(bytes.fromhex(resp["result"]))
            archive_path.unlink()
            archive_path = encrypted_path

        remote.send_file(archive_path)

        try:
            entry_id = store.add_entry(
                str(archive_path),
                file_hash,
                metadata,
            )
        except sqlite3.IntegrityError:
            logger.error("Database integrity error")
            sys.exit(1)

        audit.log(
            "file_added",
            {"file": str(archive_path), "hash": file_hash, "id": entry_id},
        )
        logger.info(f"✅ Entry added with ID {entry_id}")

    # =================================================
    # VERIFY (VERIFY++)
    # =================================================
    elif args.command == "verify":
        # backward compatibility
        if not (args.id or args.hash or args.path):
            if args.target:
                args.path = args.target
            else:
                parser.error("one of the arguments --id --hash --path is required")

        entry = None
        file_path: Path | None = None

        if args.id:
            entry = store.get_entry_by_id(args.id)
            if entry:
                file_path = Path(entry["file_path"])
        elif args.hash:
            entry = store.get_entry_by_hash(args.hash)
            if entry:
                file_path = Path(entry["file_path"])
        elif args.path:
            file_path = Path(args.path).expanduser().resolve()
            entry = store.get_entry_by_path(str(file_path))

        if not entry or not file_path or not file_path.exists():
            logger.error("Entry not found")
            sys.exit(1)

        if crypto_ipc:
            data = file_path.read_bytes()
            resp = crypto_ipc.call(
                {
                    "cmd": "hash",
                    "data": data.hex(),
                    "algorithm": config["security"]["hash_algo"],
                }
            )
            current_hash = resp["result"]
        else:
            current_hash = calculate_hash(
                file_path,
                algorithm=config["security"]["hash_algo"],
                logger=logger,
            )

        ok = current_hash == entry["hash"]
        store.update_verification(str(file_path), ok)

        audit.log(
            "verify",
            {
                "file": str(file_path),
                "expected": entry["hash"],
                "actual": current_hash,
                "ok": ok,
            },
        )

        if ok:
            logger.info("✅ Integrity verified")
        else:
            logger.error("❌ Integrity failed")
            sys.exit(1)

    # =================================================
    # LIST
    # =================================================
    elif args.command == "list":
        entries = store.list_entries(limit=args.limit)
        for e in entries:
            status = "✅" if e["verified"] else "❌"
            print(
                f"{status} ID={e['id']} "
                f"{e['metadata'].get('title', '')} "
                f"({e['file_path']})"
            )


if __name__ == "__main__":
    main()
