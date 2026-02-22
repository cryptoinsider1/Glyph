#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import os
import shutil
from pathlib import Path
from typing import Union

# Импортируем логгер (он будет передан из orchestrator'а)
# Мы не создаем логгер здесь, чтобы не плодить сущности


def calculate_hash(file_path: Union[str, Path], algorithm: str = 'sha256', logger=None) -> str:
    """
    Вычисляет хеш файла, читая его блоками (эффективно для больших файлов).
    """
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    hash_func = hashlib.new(algorithm)
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):  # 64KB блоки
                hash_func.update(chunk)
    except Exception as e:
        if logger:
            logger.error(f"Ошибка чтения файла {file_path} для хеширования: {e}")
        raise

    digest = hash_func.hexdigest()
    if logger:
        logger.debug(f"Хеш ({algorithm}) для {file_path.name}: {digest}")
    return digest


def copy_file_with_verify(src: Union[str, Path], dst: Union[str, Path],
                          verify: bool = True, logger=None) -> Path:
    """
    Копирует файл и опционально проверяет целостность по хешу.
    Возвращает путь к новому файлу.
    """
    src = Path(src)
    dst = Path(dst)

    if not src.is_file():
        raise FileNotFoundError(f"Исходный файл не найден: {src}")

    # Создаем целевую директорию, если её нет
    dst.parent.mkdir(parents=True, exist_ok=True)

    if logger:
        logger.info(f"Копирование {src} -> {dst}")

    try:
        # Копируем с сохранением метаданных (shutil.copy2)
        shutil.copy2(src, dst)
    except Exception as e:
        if logger:
            logger.error(f"Ошибка копирования {src} -> {dst}: {e}")
        raise

    if verify:
        if logger:
            logger.debug("Верификация копирования по хешу...")
        src_hash = calculate_hash(src, logger=logger)
        dst_hash = calculate_hash(dst, logger=logger)
        if src_hash != dst_hash:
            error_msg = f"Хеши не совпадают после копирования! Источник: {src_hash}, Копия: {dst_hash}"
            if logger:
                logger.error(error_msg)
            raise RuntimeError(error_msg)
        if logger:
            logger.info("Верификация успешна.")

    return dst


def move_file_with_verify(src: Union[str, Path], dst: Union[str, Path],
                          verify: bool = True, logger=None) -> Path:
    """Перемещает файл с проверкой (копирование + удаление источника)."""
    dst_path = copy_file_with_verify(src, dst, verify, logger)
    # Удаляем исходный файл
    src_path = Path(src)
    src_path.unlink()
    if logger:
        logger.info(f"Исходный файл {src} удален.")
    return dst_path
