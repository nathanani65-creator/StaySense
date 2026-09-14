import re
import threading

import numpy as np
from sqlalchemy.orm import Session

from .. import models
from .embedder import encode

_lock = threading.Lock()
_index = None
_id_map: list[int] = []  # FAISS row -> accommodation_id


def _accommodation_text(acc: models.Accommodation) -> str:
    """The text an embedding is built from. Combine name, description, tags
    and district/landmark so location-flavoured queries ("ริมน้ำ", "ใกล้วัดใหญ่")
    also match."""
    parts = [acc.name, acc.description or "", acc.district.name, acc.district.landmark_name or ""]
    parts += acc.tags_json or []
    return "passage: " + " ".join(p for p in parts if p)


def build_index(db: Session) -> int:
    """Rebuilds the in-memory FAISS index from all active accommodations.
    Call this at startup and again after any accommodation is created,
    edited, or deleted (e.g. from the admin router)."""
    global _index, _id_map

    accs = (
        db.query(models.Accommodation)
        .filter(models.Accommodation.status == "published")
        .all()
    )
    if not accs:
        with _lock:
            _index = None
            _id_map = []
        return 0

    texts = [_accommodation_text(a) for a in accs]
    vectors = encode(texts)
    dim = vectors.shape[1]

    import faiss  # lazy import: heavy dep, only needed when actually (re)building the index
    index = faiss.IndexFlatIP(dim)  # inner product on normalized vectors == cosine similarity
    index.add(vectors)

    with _lock:
        _index = index
        _id_map = [a.id for a in accs]

    return len(accs)


PRICE_PATTERN = re.compile(r"(\d{1,3}(?:,\d{3})*|\d+)\s*(?:บาท)?")


def extract_price_ceiling(query: str) -> float | None:
    """Mirrors the frontend's simple price-ceiling extraction: the first
    3-5 digit number found in the query, treated as a maximum price."""
    cleaned = query.replace(",", "")
    match = re.search(r"\d{3,6}", cleaned)
    return float(match.group()) if match else None


def semantic_search(query: str, top_k: int = 50) -> list[tuple[int, float]]:
    """Returns [(accommodation_id, similarity_score), ...] sorted best-first."""
    with _lock:
        index, id_map = _index, list(_id_map)

    if index is None or index.ntotal == 0:
        return []

    q_vec = encode(["query: " + query])
    scores, indices = index.search(q_vec, min(top_k, index.ntotal))

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        results.append((id_map[idx], float(score)))
    return results
