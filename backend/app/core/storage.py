from __future__ import annotations

import secrets
import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class Storage(Protocol):
    def save(self, *, content: bytes, extension: str, prefix: str) -> str: ...

    def delete(self, reference: str) -> None: ...


class LocalDiskStorage:
    def __init__(self, root: Path, url_prefix: str) -> None:
        self.root = root
        self.url_prefix = url_prefix.rstrip("/")

    def save(self, *, content: bytes, extension: str, prefix: str = "issues") -> str:
        folder = self.root / prefix
        folder.mkdir(parents=True, exist_ok=True)

        name = f"{uuid.uuid4().hex}{secrets.token_hex(4)}{extension}"
        (folder / name).write_bytes(content)
        return f"{self.url_prefix}/{prefix}/{name}"

    def delete(self, reference: str) -> None:
        if not reference.startswith(f"{self.url_prefix}/"):
            return
        relative = reference[len(self.url_prefix) + 1 :]
        target = (self.root / relative).resolve()
        if self.root.resolve() in target.parents and target.is_file():
            target.unlink(missing_ok=True)


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = LocalDiskStorage(
            root=Path(settings.upload_dir), url_prefix=settings.upload_url_prefix
        )
    return _storage
