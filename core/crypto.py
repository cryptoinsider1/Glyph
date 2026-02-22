#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import os
from pathlib import Path


def encrypt_file(
    input_path: Path,
    output_path: Path,
    key: str,
    algorithm: str = "aes-256-cbc",
    logger=None,
) -> Path:
    """
    Шифрует файл с помощью openssl.
    Требует наличия openssl в системе.
    """
    if not input_path.is_file():
        raise FileNotFoundError(f"Файл для шифрования не найден: {input_path}")

    # Создаем директорию для выходного файла, если нужно
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "openssl",
        "enc",
        f"-{algorithm}",
        "-salt",
        "-in",
        str(input_path),
        "-out",
        str(output_path),
        "-pass",
        f"pass:{key}",
    ]

    if logger:
        logger.info(f"Шифрование {input_path} -> {output_path}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            error_msg = f"Ошибка шифрования: {result.stderr}"
            if logger:
                logger.error(error_msg)
            raise RuntimeError(error_msg)
        if logger:
            logger.debug("Шифрование успешно.")
        return output_path
    except FileNotFoundError:
        # openssl не найден
        raise RuntimeError(
            "OpenSSL не найден в системе. Установите openssl или проверьте PATH."
        )


def decrypt_file(
    input_path: Path,
    output_path: Path,
    key: str,
    algorithm: str = "aes-256-cbc",
    logger=None,
) -> Path:
    """
    Дешифрует файл.
    """
    if not input_path.is_file():
        raise FileNotFoundError(f"Файл для дешифровки не найден: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "openssl",
        "enc",
        "-d",
        f"-{algorithm}",
        "-in",
        str(input_path),
        "-out",
        str(output_path),
        "-pass",
        f"pass:{key}",
    ]

    if logger:
        logger.info(f"Дешифровка {input_path} -> {output_path}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            error_msg = f"Ошибка дешифровки: {result.stderr}"
            if logger:
                logger.error(error_msg)
            raise RuntimeError(error_msg)
        if logger:
            logger.debug("Дешифровка успешна.")
        return output_path
    except FileNotFoundError:
        raise RuntimeError("OpenSSL не найден в системе.")


def generate_key() -> str:
    """Генерирует случайный ключ (пароль) для шифрования."""
    import base64

    return base64.urlsafe_b64encode(os.urandom(32)).decode()
