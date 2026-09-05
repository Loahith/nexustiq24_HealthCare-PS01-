"""
Local FAISS-backed retrieval-augmented-generation (RAG) store over the
healthcare guideline documents in data/medical_guidelines/.

Embeddings are produced by the Gemini embedding API when GEMINI_API_KEY
is configured. If no key is present (offline demo mode), the store
automatically falls back to a lightweight TF-IDF-style keyword vector so
the app remains fully functional without external API access.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np

logger = logging.getLogger("nexustiq24.rag")

GUIDELINES_DIR = Path(__file__).resolve().parents[2] / "data" / "medical_guidelines"
EMBED_DIM_FALLBACK = 256


@dataclass
class Chunk:
    doc_id: str
    source: str
    text: str


def _chunk_document(path: Path, max_chars: int = 400) -> List[Chunk]:
    text = path.read_text(encoding="utf-8")
    # split on bullet points / paragraphs for reasonably sized chunks
    parts = [p.strip() for p in re.split(r"\n\s*-\s+|\n\n+", text) if p.strip()]
    chunks = []
    for i, part in enumerate(parts):
        if part.startswith("#"):
            continue
        chunks.append(Chunk(doc_id=f"{path.stem}-{i}", source=path.name, text=part[:max_chars]))
    return chunks


def _hash_embed(text: str, dim: int = EMBED_DIM_FALLBACK) -> np.ndarray:
    """Deterministic bag-of-words hashing embedding used when no API key is set."""
    vec = np.zeros(dim, dtype="float32")
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    for tok in tokens:
        idx = hash(tok) % dim
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


class GuidelineRAG:
    def __init__(self) -> None:
        self.chunks: List[Chunk] = []
        self.index = None
        self.dim = EMBED_DIM_FALLBACK
        self.use_gemini = False
        self._gemini_model_name = "models/text-embedding-004"
        self._maybe_init_gemini()
        self._build_index()

    def _maybe_init_gemini(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            logger.info("GEMINI_API_KEY not set -> RAG using offline keyword embeddings.")
            return
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            self._genai = genai
            self.use_gemini = True
            self.dim = 768
            logger.info("RAG using Gemini embeddings (%s).", self._gemini_model_name)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to init Gemini embeddings, falling back to offline mode: %s", exc)
            self.use_gemini = False

    def _embed(self, text: str) -> np.ndarray:
        if self.use_gemini:
            try:
                result = self._genai.embed_content(model=self._gemini_model_name, content=text)
                vec = np.array(result["embedding"], dtype="float32")
                norm = np.linalg.norm(vec)
                return vec / norm if norm > 0 else vec
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Gemini embedding call failed, using offline fallback for this text: %s", exc)
                return _hash_embed(text, EMBED_DIM_FALLBACK)
        return _hash_embed(text, self.dim)

    def _build_index(self) -> None:
        import faiss

        for path in sorted(GUIDELINES_DIR.glob("*.md")):
            self.chunks.extend(_chunk_document(path))

        if not self.chunks:
            self.index = None
            return

        vectors = np.stack([self._embed(c.text) for c in self.chunks])
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)
        logger.info("RAG index built with %d chunks (dim=%d).", len(self.chunks), vectors.shape[1])

    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[Chunk, float]]:
        if not self.chunks or self.index is None:
            return []
        q_vec = self._embed(query).reshape(1, -1)
        scores, idxs = self.index.search(q_vec, min(top_k, len(self.chunks)))
        results = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                continue
            results.append((self.chunks[idx], float(score)))
        return results


_rag_singleton: "GuidelineRAG | None" = None


def get_rag() -> GuidelineRAG:
    global _rag_singleton
    if _rag_singleton is None:
        _rag_singleton = GuidelineRAG()
    return _rag_singleton
