#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List


class MetadataStore:
    """
    Управляет метаданными файлов в SQLite.

    Схема:
      id, file_path, hash, metadata (JSON),
      added, verified, last_checked
    """

    def __init__(self, db_path: str = "./data/metadata.db", logger=None):
        self.db_path = Path(db_path)
        self.logger = logger
        self._init_db()

    # -------------------------
    # DB internals
    # -------------------------
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    hash TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    added TEXT NOT NULL,
                    verified INTEGER DEFAULT 1,
                    last_checked TEXT
                )
                """
            )
            conn.commit()
            if self.logger:
                self.logger.debug("Metadata DB initialized")
        finally:
            conn.close()

    # -------------------------
    # Create
    # -------------------------
    def add_entry(
        self,
        file_path: str,
        file_hash: str,
        metadata: Dict[str, Any],
    ) -> int:
        metadata_json = json.dumps(metadata, ensure_ascii=False)
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = self._get_conn()
        try:
            cur = conn.execute(
                """
                INSERT INTO books
                (file_path, hash, metadata, added, verified, last_checked)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (file_path, file_hash, metadata_json, now_iso, now_iso),
            )
            conn.commit()
            entry_id = cur.lastrowid
            if self.logger:
                self.logger.info(f"Added entry ID {entry_id} -> {file_path}")
            return entry_id
        finally:
            conn.close()

    # -------------------------
    # Read
    # -------------------------
    def _row_to_entry(self, row: sqlite3.Row) -> Dict[str, Any]:
        entry = dict(row)
        entry["metadata"] = json.loads(entry["metadata"])
        return entry

    def get_entry_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM books WHERE file_path = ?",
                (file_path,),
            ).fetchone()
            return self._row_to_entry(row) if row else None
        finally:
            conn.close()

    def get_entry_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM books WHERE hash = ?",
                (file_hash,),
            ).fetchone()
            return self._row_to_entry(row) if row else None
        finally:
            conn.close()

    def get_entry_by_id(self, entry_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM books WHERE id = ?",
                (entry_id,),
            ).fetchone()
            return self._row_to_entry(row) if row else None
        finally:
            conn.close()

    # -------------------------
    # Update
    # -------------------------
    def update_verification(self, file_path: str, verified: bool) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        verified_int = 1 if verified else 0

        conn = self._get_conn()
        try:
            conn.execute(
                """
                UPDATE books
                SET verified = ?, last_checked = ?
                WHERE file_path = ?
                """,
                (verified_int, now_iso, file_path),
            )
            conn.commit()
        finally:
            conn.close()

    # -------------------------
    # List
    # -------------------------
    def list_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM books ORDER BY added DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._row_to_entry(r) for r in rows]
        finally:
            conn.close()
