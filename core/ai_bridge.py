import os
import json
import subprocess
# Можно будет реализовать вызов curl или написать на socket

def query_ai(prompt, model="gpt-3.5-turbo", api_key_env="OPENAI_API_KEY"):
    api_key = os.environ.get(api_key_env)
    if not api_key:
        return None
    # Пример вызова через curl (системный вызов)
    cmd = [
        "curl", "https://api.openai.com/v1/chat/completions",
        "-H", f"Authorization: Bearer {api_key}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        })
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    return None
