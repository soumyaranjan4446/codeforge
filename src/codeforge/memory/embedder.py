"""Local sentence-transformers embedder for failure signatures."""
from __future__ import annotations
from functools import lru_cache
import numpy as np
from sentence_transformers import SentenceTransformer
from ..config import get_settings


@lru_cache
def _model() -> SentenceTransformer:
    return SentenceTransformer(get_settings().embed_model)


def embed(text: str) -> np.ndarray:
    return _model().encode(text, normalize_embeddings=True).astype(np.float32)