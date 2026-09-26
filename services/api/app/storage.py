"""Original-document storage. Keys are generated from content hashes, never from user
file names, and every read is confined to the storage root."""

from pathlib import Path

from app.config import get_settings


class Storage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def put_original(self, organization_id: str, sha256: str, data: bytes, suffix: str) -> str:
        if not (len(sha256) == 64 and all(c in "0123456789abcdef" for c in sha256)):
            raise ValueError("sha256 must be 64 lowercase hex characters")
        if not organization_id.replace("_", "").isalnum() or suffix not in {".pdf"}:
            raise ValueError("invalid storage key component")
        key = f"originals/{organization_id}/{sha256[:2]}/{sha256}{suffix}"
        path = self.path_for(key)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".partial")
            tmp.write_bytes(data)
            tmp.replace(path)
        return key

    def path_for(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("storage key escapes the storage root")
        return path

    def writable(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            probe = self.root / ".probe"
            probe.write_bytes(b"")
            probe.unlink()
            return True
        except OSError:
            return False


def get_storage() -> Storage:
    return Storage(get_settings().storage_dir)
