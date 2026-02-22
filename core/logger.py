#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            log_record.update(record.extra)
        return json.dumps(log_record, ensure_ascii=False)

class AuditLogger:
    """Дополнительный логгер для аудита с цепочкой хешей."""
    def __init__(self, audit_file: Path):
        self.audit_file = audit_file
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.audit_file.exists():
            self.audit_file.write_text("", encoding="utf-8")

    def _last_hash(self) -> str:
        last = ""
        for line in self.audit_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                last = obj["hash"]
        return last or "GENESIS"

    def log(self, event: str, payload: Dict[str, Any]) -> str:
        prev = self._last_hash()
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "payload": payload,
            "prev": prev,
        }
        blob = json.dumps(entry, sort_keys=True, ensure_ascii=False).encode("utf-8")
        entry["hash"] = hashlib.sha256(blob + prev.encode("utf-8")).hexdigest()
        with self.audit_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry["hash"]

def setup_logger(config: dict) -> logging.Logger:
    log_file = Path(config["logging"]["file"])
    log_level_name = config["logging"]["level"].upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    use_json = config["logging"].get("json_format", False)

    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("glyph")
    logger.setLevel(log_level)

    if logger.hasHandlers():
        logger.handlers.clear()

    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    if use_json:
        file_formatter = JsonFormatter()
    else:
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"Logger initialized. Level: {log_level_name}, File: {log_file}")
    return logger
