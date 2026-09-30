"""
Document metadata store — lightweight JSON file persistence.

V1-compatible storage: a single JSON file holds all document records.
No complex database required. Suitable for the single-user student
use case described in the PRD.

File location: backend/data/metadata/documents.json
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from app.core.config import settings
from app.models.document import DocumentMeta, ProcessingStatus

# Storage path
_METADATA_DIR = settings.DATA_DIR / "metadata"
_METADATA_FILE = _METADATA_DIR / "documents.json"

# Thread-safe lock for file writes
_lock = threading.Lock()


def _ensure_dir() -> None:
    _METADATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_all() -> dict[str, dict]:
    """Read the entire document store from disk."""
    _ensure_dir()
    if not _METADATA_FILE.exists():
        return {}
    try:
        text = _METADATA_FILE.read_text(encoding="utf-8")
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        return {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write_all(data: dict[str, dict]) -> None:
    """Write the entire document store to disk."""
    _ensure_dir()
    _METADATA_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


class DocumentStore:
    """Persist and retrieve DocumentMeta records."""

    @staticmethod
    def save(doc: DocumentMeta) -> None:
        """Save or update a document record."""
        with _lock:
            store = _read_all()
            store[doc.document_id] = doc.model_dump(mode="json")
            _write_all(store)

    @staticmethod
    def get(document_id: str) -> DocumentMeta | None:
        """Retrieve a single document by ID, or None if not found."""
        store = _read_all()
        raw = store.get(document_id)
        if raw is None:
            return None
        return DocumentMeta(**raw)

    @staticmethod
    def list_all() -> list[DocumentMeta]:
        """Return all documents, newest first."""
        store = _read_all()
        docs = [DocumentMeta(**v) for v in store.values()]
        docs.sort(key=lambda d: d.upload_date, reverse=True)
        return docs

    @staticmethod
    def update_status(
        document_id: str,
        status: ProcessingStatus,
        error_message: str | None = None,
        **extra_fields,
    ) -> DocumentMeta | None:
        """
        Update processing status (and optionally other fields) for a document.
        Returns the updated DocumentMeta, or None if not found.
        """
        with _lock:
            store = _read_all()
            raw = store.get(document_id)
            if raw is None:
                return None

            raw["processing_status"] = status.value
            if error_message is not None:
                raw["error_message"] = error_message
            else:
                raw.pop("error_message", None)

            for key, value in extra_fields.items():
                if key in DocumentMeta.model_fields:
                    # Serialize Pydantic sub-models if necessary
                    if hasattr(value, "model_dump"):
                        raw[key] = value.model_dump(mode="json")
                    elif isinstance(value, list) and value and hasattr(value[0], "model_dump"):
                        raw[key] = [item.model_dump(mode="json") for item in value]
                    else:
                        raw[key] = value

            store[document_id] = raw
            _write_all(store)
            return DocumentMeta(**raw)

    @staticmethod
    def delete(document_id: str) -> bool:
        """Remove a document record. Returns True if it existed."""
        with _lock:
            store = _read_all()
            if document_id in store:
                del store[document_id]
                _write_all(store)
                return True
            return False
