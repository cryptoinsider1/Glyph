#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys
from pathlib import Path

from core.file_handler import calculate_hash, copy_file_with_verify
from core.ipc import ModuleIPC
from core.logger import AuditLogger, setup_logger
from core.metadata_store import MetadataStore
from core.remote import RemoteStorage


PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)


# -------------------------
# Config
# -------------------------
def load_config() -> dict:
    cfg = PROJECT_ROOT / "config" / "settings.json"
    if not cfg.exists():
        raise FileNotFoundError(
            f"Config not found: {cfg}. Copy from config/settings.example.json"
        )
    return json.loads(cfg.read_text(encoding="utf-8"))


# -------------------------
# CLI
# -------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Glyph CLI v0.2.1")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add file")
    p_add.add_argument("file")
    p_add.add_argument("--title")
    p_add.add_argument("--author")
    p_add.add_argument("--tags")
    p_add.add_argument("--no-verify", action="store_true")

    p_ver = sub.add_parser("verify", help="Verify integrity")
    p_ver.add_argument("file", nargs="?")
    p_ver.add_argument("--id", type=int)
    p_ver.add_argument("--hash")

    p_list = sub.add_parser("list", help="List entries")
    p_list.add_argument("--limit", type=int, default=20)

    return parser


# -------------------------
# Helpers
# -------------------------
def resolve_entry(store: MetadataStore, args) -> dict:
    if args.id is not None:
        entry = store.get_entry_by_id(args.id)
    elif args.hash:
        entry = store.get_entry_by_hash(args.hash)
    elif args.file:
        path = Path(args.file).expanduser().resolve()
        entry = store.get_entry_by_path(str(path))
    else:
        raise ValueError("Specify --id, --hash or file path")

    if not entry:
        raise LookupError("Entry not found")
    return entry


# -------------------------
# Main
# -------------------------
def main() -> None:
    try:
        config = load_config()
    except Exception as exc:
        print(f"FATAL: Cannot load config: {exc}")
        sys.exit(1)

    logger = setup_logger(config)
    audit = AuditLogger(Path("logs/audit.jsonl"))

    store = MetadataStore(
        db_path=config["metadata"]["database"],
        logger=logger,
    )

    remote = RemoteStorage(config["storage"], logger)

    crypto_ipc = None
    crypto_cfg = config.get("modules", {}).get("crypto", {})
    if crypto_cfg.get("enabled"):
        crypto_ipc = ModuleIPC(
            PROJECT_ROOT / crypto_cfg["path"],
            logger=logger,
        )

    args = build_parser().parse_args()

    # -------------------------
    # ADD
    # -------------------------
    if args.command == "add":
        src = Path(args.file).expanduser().resolve()
        if not src.is_file():
            logger.error(f"File not found: {src}")
            sys.exit(1)

        algo = config["security"]["hash_algo"]
        file_hash = (
            crypto_ipc.hash_file(src, algo)
            if crypto_ipc
            else calculate_hash(src, algo, logger)
        )

        if store.get_entry_by_hash(file_hash):
            logger.error("Duplicate file (hash exists)")
            sys.exit(1)

        archive = Path(config["storage"]["archive_dir"])
        archive.mkdir(parents=True, exist_ok=True)
        dst = archive / src.name

        copy_file_with_verify(src, dst, not args.no_verify, logger)

        meta = {
            "title": args.title or src.stem,
            "author": args.author or "Unknown",
            "tags": args.tags.split(",") if args.tags else [],
            "original_filename": src.name,
            "size_bytes": src.stat().st_size,
        }

        remote.send_file(dst)
        entry_id = store.add_entry(str(dst), file_hash, meta)

        audit.log("file_added", {"id": entry_id, "hash": file_hash})
        logger.info(f"✅ Entry added with ID {entry_id}")

    # -------------------------
    # VERIFY++
    # -------------------------
    elif args.command == "verify":
        try:
            entry = resolve_entry(store, args)
        except Exception as exc:
            logger.error(str(exc))
            sys.exit(1)

        path = Path(entry["file_path"])
        algo = config["security"]["hash_algo"]
        current = (
            crypto_ipc.hash_file(path, algo)
            if crypto_ipc
            else calculate_hash(path, algo, logger)
        )

        ok = current == entry["hash"]
        store.update_verification(entry["file_path"], ok)

        audit.log(
            "verify",
            {"id": entry["id"], "ok": ok},
        )

        if ok:
            logger.info("✅ Integrity verified")
        else:
            logger.error("❌ Integrity FAILED")
            sys.exit(1)

    # -------------------------
    # LIST
    # -------------------------
    elif args.command == "list":
        for e in store.list_entries(args.limit):
            mark = "✅" if e["verified"] else "❌"
            print(
                f"{mark} ID={e['id']} {e['metadata'].get('title','')} ({e['file_path']})"
            )


if __name__ == "__main__":
    main()
