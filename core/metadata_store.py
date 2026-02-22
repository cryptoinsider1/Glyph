#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


class MetadataStore:
    """
    Управляет метаданными книг в SQLite.
    Простая схема: id, file_path, hash, metadata (JSON), added, verified, last_checked.
    """

    def __init__(self, db_path: str = "./data/metadata.db", logger=None):
        self.db_path = Path(db_path)
        self.logger = logger
        self._init_db()

    def _init_db(self):
        """Создает таблицу, если её нет."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    hash TEXT NOT NULL,
                    metadata TEXT NOT NULL,  -- JSON поле
                    added TEXT NOT NULL,     -- ISO timestamp
                    verified INTEGER DEFAULT 1,
                    last_checked TEXT
                )
            """)
            conn.commit()
            if self.logger:
                self.logger.debug("Таблица metadata инициализирована.")
        except sqlite3.Error as e:
            if self.logger:
                self.logger.error(f"Ошибка инициализации БД: {e}")
            raise
        finally:
            conn.close()

    def _get_conn(self):
        """Возвращает соединение с БД (Row factory для удобства)."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Позволяет обращаться по имени колонки
        return conn

    def add_entry(self, file_path: str, file_hash: str,
                  metadata: Dict[str, Any]) -> int:
        """
        Добавляет новую запись. Возвращает ID записи.
        """
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
                self.logger.info(f"Добавлена запись ID {new_id} для файла {file_path}")
            return new_id
        except sqlite3.IntegrityError:
            if self.logger:
                self.logger.error(f"Запись для файла {file_path} уже существует.")
            raise  # Пробрасываем выше, пусть orchestrator решит, что делать
        finally:
            conn.close()

    def get_entry_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Возвращает запись по пути файла или None."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM books WHERE file_path = ?", (file_path,)).fetchone()
            if row:
                # Преобразуем sqlite3.Row в dict
                entry = dict(row)
                # Парсим JSON из metadata
                entry["metadata"] = json.loads(entry["metadata"])
                return entry
            return None
        finally:
            conn.close()

    def get_entry_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Возвращает запись по хешу."""
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
        """Обновляет статус верификации и время проверки."""
        conn = self._get_conn()
        checked_iso = datetime.utcnow().isoformat() + "Z"
        verified_int = 1 if verified else 0
        try:
            conn.execute("""
                UPDATE books
                SET verified = ?, last_checked = ?
                WHERE file_path = ?
            """, (verified_int, checked_iso, file_path))
            conn.commit()
            if self.logger:
                self.logger.debug(f"Статус верификации для {file_path} обновлен: verified={verified}")
        except sqlite3.Error as e:
            if self.logger:
                self.logger.error(f"Ошибка обновления верификации: {e}")
            raise
        finally:
            conn.close()

    def list_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Возвращает список последних записей."""
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
            
