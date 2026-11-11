"""
Persistent ChromaDB vector store adapter.
Stores chunk embeddings with role metadata flags and status.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.application.ports import VectorStorePort
from app.composition.settings import get_settings
from app.domain.entities import DocumentChunk, Role, VersionStatus


class ChromaVectorStore(VectorStorePort):
    def __init__(self, persist_directory: Optional[str] = None):
        settings = get_settings()
        self.persist_dir = persist_directory or settings.chroma_path
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="chunks",
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
        allowed_roles_per_chunk: List[List[Role]],
        status: VersionStatus,
        document_id: Optional[UUID] = None,
    ) -> None:
        if not chunks:
            return

        ids = [str(c.chunk_id) for c in chunks]
        metadatas: List[Dict[str, Any]] = []

        for i, chunk in enumerate(chunks):
            roles = allowed_roles_per_chunk[i] if i < len(allowed_roles_per_chunk) else []
            meta = {
                "chunk_id": str(chunk.chunk_id),
                "version_id": str(chunk.version_id),
                "document_id": str(document_id) if document_id else "",
                "page_start": chunk.page_start,
                "status": status.value,
                "role_admin": True,
                "role_student": Role.STUDENT in roles,
                "role_faculty": Role.FACULTY in roles,
                "role_staff": Role.STAFF in roles,
            }
            metadatas.append(meta)

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        query_vector: List[float],
        user_role: Role,
        top_k: int = 20,
        status: VersionStatus = VersionStatus.CURRENT,
    ) -> List[Tuple[UUID, int, float]]:
        # ChromaDB requires $and when filtering on multiple fields
        filters: List[Dict[str, Any]] = [{"status": status.value}]
        if user_role != Role.ADMIN:
            filters.append({f"role_{user_role.value}": True})

        where_filter: Dict[str, Any]
        if len(filters) == 1:
            where_filter = filters[0]
        else:
            where_filter = {"$and": filters}

        count = self.collection.count()
        if count == 0:
            return []

        actual_k = min(top_k, count)
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=actual_k,
            where=where_filter,
            include=["metadatas", "distances"],
        )

        hits: List[Tuple[UUID, int, float]] = []
        if results and results.get("ids") and results["ids"][0]:
            chunk_ids = results["ids"][0]
            distances = results["distances"][0] if results.get("distances") else []
            for rank, cid in enumerate(chunk_ids):
                # Cosine distance in Chroma: score = 1.0 - distance
                dist = distances[rank] if rank < len(distances) else 0.5
                score = max(0.0, 1.0 - dist)
                hits.append((UUID(cid), rank + 1, score))

        return hits

    def update_version_status(
        self,
        version_id: UUID,
        new_status: VersionStatus,
    ) -> None:
        results = self.collection.get(where={"version_id": str(version_id)}, include=["metadatas"])
        if results and results.get("ids"):
            ids = results["ids"]
            metas = results["metadatas"]
            for m in metas:
                m["status"] = new_status.value
            self.collection.update(ids=ids, metadatas=metas)

    def update_document_roles(
        self,
        document_id: UUID,
        new_roles: List[Role],
    ) -> None:
        results = self.collection.get(where={"document_id": str(document_id)}, include=["metadatas"])
        if results and results.get("ids"):
            ids = results["ids"]
            metas = results["metadatas"]
            for m in metas:
                m["role_student"] = Role.STUDENT in new_roles
                m["role_faculty"] = Role.FACULTY in new_roles
                m["role_staff"] = Role.STAFF in new_roles
            self.collection.update(ids=ids, metadatas=metas)
