"""
Sentence Transformers embedding adapter.
Generates 384-dimensional dense vectors using BAAI/bge-small-en-v1.5 on CPU.
Includes deterministic hash fallback for offline test environments.
"""
import hashlib
from typing import List, Optional
from app.application.ports import EmbeddingPort
from app.composition.settings import get_settings


class SentenceTransformerEmbeddingAdapter(EmbeddingPort):
    def __init__(self, model_name: Optional[str] = None):
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self._model = None
        self._dimension = 384

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except Exception:
                self._model = "fallback"
        return self._model

    def _deterministic_fallback_embed(self, text: str) -> List[float]:
        """
        Produces a normalized 384-dimensional vector deterministically from text
        for offline unit tests without requiring Hugging Face downloads.
        """
        import math
        vec = []
        for i in range(self._dimension):
            h = hashlib.sha256(f"{text}:{i}".encode("utf-8")).digest()
            val = (int.from_bytes(h[:4], "big") / 0xFFFFFFFF) * 2.0 - 1.0
            vec.append(val)
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_query(self, query: str) -> List[float]:
        model = self._get_model()
        if model == "fallback":
            return self._deterministic_fallback_embed(query)
        # BGE recommends query prefix for asymmetric search
        query_text = f"Represent this sentence for searching relevant passages: {query}"
        emb = model.encode(query_text, normalize_embeddings=True)
        return emb.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = self._get_model()
        if model == "fallback":
            return [self._deterministic_fallback_embed(t) for t in texts]
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]

