# Glyph
Безопасная энциклопедия знаний

**Glyph** — это ядро защищённой, масштабируемой системы управления знаниями. Проект стартует как библиотека с контролем целостности и шифрованием, но архитектура позволяет эволюционировать в распределённую научную сеть, включая модули на разных языках (Python, Rust, Go и др.).

## Особенности первого пилота

- Добавление файлов с вычислением хеша (SHA-256).
- Сохранение метаданных в SQLite.
- Опциональное шифрование через внешний Rust-модуль (AES-256).
- Проверка целостности файлов.
- Структурированное логирование в JSON с верифицируемой цепочкой.
- Модульная архитектура: криптография вынесена в отдельный Rust-процесс.

## Требования

- macOS / Linux (протестировано на MacBook A3401)
- Python 3.11+
- Rust (для сборки крипто-модуля)
- OpenSSL (системная утилита, для шифрования, если не используем Rust)
- make (опционально)

## Быстрый старт

1. **Клонируйте репозиторий**:
   ```bash
   git clone <url>
   cd glyph

## License

This project is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.

## Versioning

We use [SemVer](https://semver.org/) for versioning. For the versions available, see the [CHANGELOG](CHANGELOG.md).

## Documentation

Full documentation is available at [Read the Docs](https://glyph.readthedocs.io/).

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.
