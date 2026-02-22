#!/usr/bin/env python3
import sys
import json


def main():
    for line in sys.stdin:
        try:
            req = json.loads(line)
        except Exception:
            print(json.dumps({"error": "Invalid JSON"}))
            continue

        cmd = req.get("cmd")
        if cmd == "analyze":
            # Простейший анализ: возвращаем заглушку
            result = {
                "language": "en",
                "summary": "This is a stub summary.",
                "keywords": ["stub", "test"],
            }
            print(json.dumps({"result": result}))
        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))


if __name__ == "__main__":
    main()
