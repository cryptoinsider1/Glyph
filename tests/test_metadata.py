import tempfile
from pathlib import Path
from core.metadata_store import MetadataStore


def test_add_and_get():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = MetadataStore(str(db_path))
        entry_id = store.add_entry("/fake/path", "abcdef", {"title": "Test"})
        assert entry_id > 0
        entry = store.get_entry_by_path("/fake/path")
        assert entry is not None
        assert entry["hash"] == "abcdef"
