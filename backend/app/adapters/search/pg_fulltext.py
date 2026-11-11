"""
Full-text keyword search adapter.
Supports PostgreSQL websearch_to_tsquery and SQLite fallback.
"""
from typing import List, Set, Tuple
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.adapters.persistence.models import DocumentChunkModel
from app.application.ports import KeywordIndexPort
from app.composition.settings import get_settings


class PostgresFullTextSearch(KeywordIndexPort):
    def __init__(self, db: Session):
        self.db = db
        settings = get_settings()
        self.is_postgres = settings.database_url.startswith("postgresql")

    def search(
        self,
        query_text: str,
        allowed_version_ids: Set[UUID],
        top_k: int = 20,
    ) -> List[Tuple[UUID, int, float]]:
        if not allowed_version_ids or not query_text.strip():
            return []

        clean_query = query_text.strip()

        if self.is_postgres:
            # PostgreSQL full-text search with ts_rank
            sql = text("""
                SELECT chunk_id, ts_rank(tsv, websearch_to_tsquery('english', :q)) AS rank_score
                FROM document_chunks
                WHERE version_id = ANY(:vids)
                  AND tsv @@ websearch_to_tsquery('english', :q)
                ORDER BY rank_score DESC
                LIMIT :limit
            """)
            rows = self.db.execute(
                sql,
                {"q": clean_query, "vids": list(allowed_version_ids), "limit": top_k},
            ).fetchall()
            return [(UUID(str(r[0])), rank + 1, float(r[1])) for rank, r in enumerate(rows)]
        else:
            # SQLite keyword search fallback
            words = [w.lower() for w in clean_query.split() if len(w) > 2]
            if not words:
                words = [clean_query.lower()]

            chunks = (
                self.db.query(DocumentChunkModel)
                .filter(DocumentChunkModel.version_id.in_(allowed_version_ids))
                .all()
            )

            scored = []
            for c in chunks:
                heading = (c.section_heading or "").lower()
                body = c.chunk_text.lower()
                score = 0.0
                for w in words:
                    if w in heading:
                        score += 2.0
                    if w in body:
                        score += 1.0
                if score > 0:
                    scored.append((c.chunk_id, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            return [(cid, rank + 1, sc) for rank, (cid, sc) in enumerate(scored[:top_k])]

