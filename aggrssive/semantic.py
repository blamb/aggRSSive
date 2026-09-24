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
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Item

log = logging.getLogger("aggrssive.semantic")

STRICTNESS = {"loose": 0.50, "normal": 0.58, "strict": 0.65}  # cosine thresholds for bge-small, calibrated on real blog posts

_model = None
_lock = threading.Lock()
_failed_at: float | None = None
_rule_cache: dict[str, np.ndarray] = {}
_index: dict | None = None  # {"n": int, "at": float, "ids": ndarray, "sources": ndarray, "matrix": ndarray}


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

            # Two threads and small batches: this runs beside the web app on a small container.
            _model = TextEmbedding(get_settings().embedding_model, threads=2)
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
    # Batch size and input length bound the attention buffer: 256 x 512 tokens needs ~1.2 GB and
    # crashed a 1-2 GB container; 16 x ~150 tokens needs a few MB.
    for v in model.embed(texts, batch_size=16):
        v = np.asarray(v, dtype=np.float32)
        n = np.linalg.norm(v)
        out.append(v / n if n else v)
    return out


def to_bytes(v: np.ndarray) -> bytes:
    return np.asarray(v, dtype=np.float32).tobytes()


def from_bytes(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)


def item_text(item: Item) -> str:
    return f"{item.title}\n{item.text[:500]}"


def embed_pending(db: Session, limit: int = 100) -> int:
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
    vs = embed_texts([pattern[:500]])
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


def _load_index(db: Session) -> dict | None:
    """All item vectors as one matrix, cached until new items are analysed (or two minutes pass)."""
    global _index
    n = db.scalar(select(func.count(Item.id)).where(Item.embedding.is_not(None))) or 0
    if _index and _index["n"] == n and time.time() - _index["at"] < 120:
        return _index
    if not n:
        _index = None
        return None
    rows = db.execute(select(Item.id, Item.source_id, Item.embedding).where(Item.embedding.is_not(None))).all()
    width = len(rows[0][2])
    rows = [r for r in rows if len(r[2]) == width]  # ignore vectors from a different model
    _index = {
        "n": n,
        "at": time.time(),
        "ids": np.array([r[0] for r in rows]),
        "sources": np.array([r[1] for r in rows]),
        "matrix": np.stack([from_bytes(r[2]) for r in rows]),
    }
    return _index


def search(db: Session, query: str, limit: int = 12, source_limit: int = 10, floor: float | None = None) -> dict | None:
    """Posts about *query* and the feeds that publish them, ranked by meaning.

    Returns None when embeddings are off or nothing has been analysed yet; otherwise
    {"posts": [(Item, score)], "sources": [(source_id, score, hits)], "analysed": n, "pending": m}.
    A source's score is the mean of its best three posts, so one lucky hit doesn't outrank a feed
    that writes about the subject regularly.
    """
    if not enabled():
        return None
    idx = _load_index(db)
    if idx is None:
        return None
    qv = rule_vector(query)
    if qv is None:
        return None
    floor = STRICTNESS["loose"] if floor is None else floor
    scores = idx["matrix"] @ qv
    order = np.argsort(-scores)
    top_items = [(int(idx["ids"][i]), float(scores[i])) for i in order[:limit] if scores[i] >= floor]
    by_source: dict[int, list[float]] = {}
    for i in order:
        if scores[i] < floor:
            break
        by_source.setdefault(int(idx["sources"][i]), []).append(float(scores[i]))
    ranked = sorted(((sid, float(np.mean(sorted(v, reverse=True)[:3])), len(v)) for sid, v in by_source.items()), key=lambda r: -r[1])[:source_limit]
    items = {i.id: i for i in db.execute(select(Item).where(Item.id.in_([i for i, _ in top_items]))).scalars()} if top_items else {}
    pending = db.scalar(select(func.count(Item.id)).where(Item.embedding.is_(None))) or 0
    return {"posts": [(items[i], s) for i, s in top_items if i in items], "sources": ranked, "analysed": idx["n"], "pending": pending}
