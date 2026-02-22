import subprocess
import json
import pytest
from pathlib import Path

CRYPTO_PATH = Path("modules/crypto_rust/target/release/crypto_rust")

@pytest.fixture(scope="module")
def crypto_proc():
    if not CRYPTO_PATH.exists():
        pytest.skip("Crypto module not built. Run 'make build'")
    return CRYPTO_PATH

def test_hash(crypto_proc):
    data = b"hello world"
    req = {"cmd": "hash", "data": data.hex(), "algorithm": "sha256"}
    proc = subprocess.Popen([str(crypto_proc)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    stdout, _ = proc.communicate(json.dumps(req))
    resp = json.loads(stdout)
    assert "result" in resp
    assert resp["result"] == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
