"""Qdrant-backed semantic memory of historical bug resolutions."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Sequence
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from ..config import get_settings, get_yaml_config
from ..schemas import FailureSignature, PatchRecord
from .embedder import embed


class BugMemory:
    """Stores & retrieves patch contexts keyed by failure-signature embeddings."""

    def __init__(self):
        s = get_settings()
        self.client = QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key or None)
        self.collection = s.qdrant_collection
        self._ensure_collection()

    def _ensure_collection(self):
        cols = {c.name for c in self.client.get_collections().collections}
        if self.collection not in cols:
            self.client.create_collection(
                self.collection,
                vectors_config=qm.VectorParams(size=384, distance=qm.Distance.COSINE),
            )

    def store(self, signature: FailureSignature, record: PatchRecord) -> str:
        vec = embed(signature.to_text()).tolist()
        point_id = record.id or str(uuid.uuid4())
        self.client.upsert(
            self.collection,
            points=[qm.PointStruct(
                id=point_id,
                vector=vec,
                payload={
                    "test_name": signature.test_name,
                    "error_type": signature.error_type,
                    "error_summary": signature.error_summary,
                    "code_module": signature.code_module,
                    "original_code": record.original_code,
                    "patched_code": record.patched_code,
                    "diff": record.diff,
                    "tests_passed_after": record.tests_passed_after,
                    "created_at": record.created_at.isoformat(),
                    "tags": record.tags,
                },
            )],
        )
        return point_id

    def retrieve(self, signature: FailureSignature, top_k: int | None = None,
                 min_score: float | None = None) -> list[PatchRecord]:
        cfg = get_yaml_config().memory
        top_k = top_k or cfg.top_k
        min_score = min_score or cfg.min_score

        vec = embed(signature.to_text()).tolist()
        resp = self.client.query_points(
            collection_name=self.collection, query=vec, limit=top_k,
            score_threshold=min_score,
        )
        out: list[PatchRecord] = []
        for h in resp.points:
            p = h.payload
            out.append(PatchRecord(
                id=str(h.id),
                signature=FailureSignature(
                    test_name=p["test_name"],
                    error_type=p["error_type"],
                    error_summary=p["error_summary"],
                    code_module=p["code_module"],
                ),
                original_code=p["original_code"],
                patched_code=p["patched_code"],
                diff=p["diff"],
                tests_passed_after=p["tests_passed_after"],
                created_at=datetime.fromisoformat(p["created_at"]),
                tags=p.get("tags", []),
            ))
        return out