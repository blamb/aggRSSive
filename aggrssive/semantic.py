"""Local embeddings for "meaning" rules: is this item about roughly *this*?

Uses a small sentence-embedding model on the CPU. No API key, no per-item cost. Items are embedded
in the background after fetching; a rule's description is embedded once and cached. Everything degrades
gracefully: if the model can't load, meaning rules simply don't match and the UI says so.
"""

from __future__ import annotations

import logging
import threading
import time

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Item

log = logging.getLogger("aggrssive.semantic")

STRICTNESS = {"loose": 0.50, "normal": 0.58, "strict": 0.65}  # cosine thresholds for bge-small, calibrated on real blog posts

_model = None
_lock = threading.Lock()
_failed_at: float | None = None
_rule_cache: dict[str, np.ndarray] = {}


def enabled() -> bool:
    return get_settings().embeddings_enabled


def _get_model():
    """Load the model once; after a failure, wait ten minutes before trying again."""
    global _model, _failed_at
    if _model is not None:
        return _model
    if _failed_at and time.time() - _failed_at < 600:
        return None
    with _lock:
        if _model is not None:
            return _model
        try:
            from fastembed import TextEmbedding

            _model = TextEmbedding(get_settings().embedding_model)
            log.info("embedding model loaded: %s", get_settings().embedding_model)
        except Exception as e:  # download or runtime failure
            _failed_at = time.time()
            log.warning("embedding model unavailable: %s", e)
            return None
    return _model


def embed_texts(texts: list[str]) -> list[np.ndarray] | None:
    if not enabled() or not texts:
        return None
    model = _get_model()
    if model is None:
        return None
    out = []
    for v in model.embed(texts):
        v = np.asarray(v, dtype=np.float32)
        n = np.linalg.norm(v)
        out.append(v / n if n else v)
    return out


def to_bytes(v: np.ndarray) -> bytes:
    return np.asarray(v, dtype=np.float32).tobytes()


def from_bytes(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)


def item_text(item: Item) -> str:
    return f"{item.title}\n{item.text[:1000]}"


def embed_pending(db: Session, limit: int = 200) -> int:
    """Embed items that don't have a vector yet. Returns how many were done."""
    if not enabled():
        return 0
    items = db.execute(select(Item).where(Item.embedding.is_(None)).order_by(Item.published_at.desc()).limit(limit)).scalars().all()
    if not items:
        return 0
    vectors = embed_texts([item_text(i) for i in items])
    if vectors is None:
        return 0
    for item, v in zip(items, vectors):
        item.embedding = to_bytes(v)
    db.commit()
    return len(items)


def rule_vector(pattern: str) -> np.ndarray | None:
    key = pattern.strip().lower()
    if key in _rule_cache:
        return _rule_cache[key]
    vs = embed_texts([pattern])
    if not vs:
        return None
    _rule_cache[key] = vs[0]
    return vs[0]


def similarity(item: Item, pattern: str) -> float | None:
    """Cosine similarity between an item and a rule description, or None if either isn't analysed yet."""
    if item.embedding is None:
        return None
    rv = rule_vector(pattern)
    if rv is None:
        return None
    return float(np.dot(from_bytes(item.embedding), rv))


def strictness_label(threshold: float | None) -> str:
    t = threshold if threshold is not None else STRICTNESS["normal"]
    return min(STRICTNESS, key=lambda k: abs(STRICTNESS[k] - t))
