#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import shutil
from pathlib import Path
from typing import Union

def calculate_hash(file_path: Union[str, Path], algorithm: str = 'sha256', logger=None) -> str:
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    hash_func = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def copy_file_with_verify(src: Union[str, Path], dst: Union[str, Path], verify=True, logger=None) -> Path:
    src = Path(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if verify:
        src_hash = calculate_hash(src, logger=logger)
        dst_hash = calculate_hash(dst, logger=logger)
        if src_hash != dst_hash:
            raise RuntimeError(f"Hash mismatch after copy: {src_hash} vs {dst_hash}")
    return dst
