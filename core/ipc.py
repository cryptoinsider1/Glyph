#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

class ModuleIPC:
    """Client for calling external modules via JSON over stdin/stdout.
    
    Args:
        module_path (Path): Path to the executable.
        logger (logging.Logger, optional): Logger instance.
    """
    def __init__(self, module_path: Path, logger=None):
        self.module_path = module_path.resolve()
        if not self.module_path.exists():
            raise FileNotFoundError(f"Module executable not found: {module_path}")
        self.logger = logger

    MAX_IPC_SIZE = 10 * 1024 * 1024  # 10 MB

    def call(self, request: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """Отправляет JSON-запрос модулю, возвращает JSON-ответ."""
        data = json.dumps(request)
        if len(data.encode()) > MAX_IPC_SIZE:
        raise ValueError(f"IPC payload too large: {len(data)} > {MAX_IPC_SIZE}")
        if self.logger:
            self.logger.debug(f"IPC call to {self.module_path}: {request}")
        try:
            proc = subprocess.Popen(
                [str(self.module_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = proc.communicate(json.dumps(request), timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            raise RuntimeError(f"Module {self.module_path} timed out after {timeout}s")
        if proc.returncode != 0:
            error_msg = f"Module {self.module_path} exited with code {proc.returncode}\nstderr: {stderr}"
            if self.logger:
                self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        try:
            response = json.loads(stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON from module: {stdout}") from e
        if self.logger:
            self.logger.debug(f"IPC response: {response}")
        return response
