#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

class MetadataStore:
    def __init__(self, db_path: str = "./data/metadata.db", logger=None):
        self.db_path = Path(db_path)
        self.logger = logger
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    hash TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    added TEXT NOT NULL,
                    verified INTEGER DEFAULT 1,
                    last_checked TEXT
                )
            """)
            conn.commit()
            if self.logger:
                self.logger.debug("Metadata table initialized.")
        except sqlite3.Error as e:
            if self.logger:
                self.logger.error(f"DB init error: {e}")
            raise
        finally:
            conn.close()

    def _get_conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def add_entry(self, file_path: str, file_hash: str, metadata: Dict[str, Any]) -> int:
        metadata_json = json.dumps(metadata, ensure_ascii=False)
        added_iso = datetime.utcnow().isoformat() + "Z"
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                INSERT INTO books (file_path, hash, metadata, added, verified, last_checked)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (file_path, file_hash, metadata_json, added_iso, added_iso))
            conn.commit()
            new_id = cursor.lastrowid
            if self.logger:
                self.logger.info(f"Added entry ID {new_id} for {file_path}")
            return new_id
        except sqlite3.IntegrityError:
            if self.logger:
                self.logger.error(f"Entry for {file_path} already exists.")
            raise
        finally:
            conn.close()

    def get_entry_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM books WHERE file_path = ?", (file_path,)).fetchone()
            if row:
                entry = dict(row)
                entry["metadata"] = json.loads(entry["metadata"])
                return entry
            return None
        finally:
            conn.close()

    def get_entry_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM books WHERE hash = ?", (file_hash,)).fetchone()
            if row:
                entry = dict(row)
                entry["metadata"] = json.loads(entry["metadata"])
                return entry
            return None
        finally:
            conn.close()

    def update_verification(self, file_path: str, verified: bool):
        checked_iso = datetime.utcnow().isoformat() + "Z"
        verified_int = 1 if verified else 0
        conn = self._get_conn()
        try:
            conn.execute("""
                UPDATE books
                SET verified = ?, last_checked = ?
                WHERE file_path = ?
            """, (verified_int, checked_iso, file_path))
            conn.commit()
            if self.logger:
                self.logger.debug(f"Verification updated for {file_path}: verified={verified}")
        except sqlite3.Error as e:
            if self.logger:
                self.logger.error(f"Error updating verification: {e}")
            raise
        finally:
            conn.close()

    def list_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM books ORDER BY added DESC LIMIT ?", (limit,)).fetchall()
            entries = []
            for row in rows:
                entry = dict(row)
                entry["metadata"] = json.loads(entry["metadata"])
                entries.append(entry)
            return entries
        finally:
            conn.close()
