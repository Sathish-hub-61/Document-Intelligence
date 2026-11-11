"""
Unit and integration tests for Phase 3: Knowledge Base, Embeddings and Search Indexing.
"""
import sys
from pathlib import Path
from uuid import uuid4
import pytest

backend_path = Path(__file__).resolve().parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from app.adapters.embeddings.sentence_transformers import SentenceTransformerEmbeddingAdapter
from app.adapters.vector.chroma_store import ChromaVectorStore
from app.adapters.search.pg_fulltext import PostgresFullTextSearch
from app.adapters.persistence.database import SessionLocal
from app.domain.entities import DocumentChunk, Role, VersionStatus
from app.main import app

client = TestClient(app)


def test_embedding_dimensions():
    embedder = SentenceTransformerEmbeddingAdapter()
    query_vec = embedder.embed_query("minimum attendance rules for exams")
    assert len(query_vec) == 384

    doc_vecs = embedder.embed_documents(["First chunk text", "Second chunk text"])
    assert len(doc_vecs) == 2
    assert len(doc_vecs[0]) == 384
    assert len(doc_vecs[1]) == 384


def test_chroma_role_filtering(tmp_path):
    chroma_dir = str(tmp_path / "test_chroma")
    vstore = ChromaVectorStore(persist_directory=chroma_dir)

    embedder = SentenceTransformerEmbeddingAdapter()

    v1_id = uuid4()
    doc_id = uuid4()

    # Public chunk (student & admin)
    c1 = DocumentChunk(
        version_id=v1_id,
        chunk_index=0,
        page_start=1,
        page_end=1,
        section_heading="Public Calendar",
        chunk_text="Semester commences on August 15 with orientation week.",
        token_count=12,
    )
    # Confidential faculty chunk (faculty & admin only)
    c2 = DocumentChunk(
        version_id=v1_id,
        chunk_index=1,
        page_start=2,
        page_end=2,
        section_heading="Faculty Appraisal Rubric",
        chunk_text="Confidential promotion guidelines and research point scoring rubric.",
        token_count=12,
    )

    embs = embedder.embed_documents([c1.chunk_text, c2.chunk_text])
    vstore.upsert_chunks(
        chunks=[c1, c2],
        embeddings=embs,
        allowed_roles_per_chunk=[[Role.STUDENT, Role.ADMIN], [Role.FACULTY, Role.ADMIN]],
        status=VersionStatus.CURRENT,
        document_id=doc_id,
    )

    q_vec = embedder.embed_query("promotion guidelines and scoring rubric")

    # Faculty search sees c2
    faculty_hits = vstore.search(q_vec, user_role=Role.FACULTY, top_k=5)
    faculty_chunk_ids = [h[0] for h in faculty_hits]
    assert c2.chunk_id in faculty_chunk_ids

    # Student search CANNOT see c2 (confidential faculty chunk)
    student_hits = vstore.search(q_vec, user_role=Role.STUDENT, top_k=5)
    student_chunk_ids = [h[0] for h in student_hits]
    assert c2.chunk_id not in student_chunk_ids


def test_keyword_search_filtering():
    db = SessionLocal()
    try:
        from app.adapters.persistence.repositories import SqlAlchemyDocumentRepo
        repo = SqlAlchemyDocumentRepo(db)

        v_allowed = uuid4()
        v_forbidden = uuid4()

        c_allowed = DocumentChunk(
            version_id=v_allowed,
            chunk_index=0,
            page_start=1,
            page_end=1,
            section_heading="Attendance Regulation",
            chunk_text="Minimum attendance requirement is strictly seventy-five percent.",
            token_count=10,
        )
        c_forbidden = DocumentChunk(
            version_id=v_forbidden,
            chunk_index=0,
            page_start=1,
            page_end=1,
            section_heading="Staff Attendance Rules",
            chunk_text="Staff biometric attendance policy and leave accrual details.",
            token_count=10,
        )

        repo.save_chunks([c_allowed])
        repo.save_chunks([c_forbidden])

        searcher = PostgresFullTextSearch(db)
        results = searcher.search("attendance", allowed_version_ids={v_allowed}, top_k=10)

        hit_ids = [r[0] for r in results]
        assert c_allowed.chunk_id in hit_ids
        assert c_forbidden.chunk_id not in hit_ids
    finally:
        db.close()


def test_api_reindex_endpoint():
    # Login as admin
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@university.edu", "password": "AdminPass123!"},
    )
    admin_token = admin_login.json()["access_token"]

    # Student login
    student_login = client.post(
        "/api/auth/login",
        json={"email": "student@university.edu", "password": "StudentPass123!"},
    )
    student_token = student_login.json()["access_token"]

    # Get a version from existing documents
    docs = client.get("/api/documents", headers={"Authorization": f"Bearer {admin_token}"}).json()
    assert len(docs) > 0
    doc_id = docs[0]["document_id"]

    db = SessionLocal()
    from app.adapters.persistence.repositories import SqlAlchemyDocumentRepo
    repo = SqlAlchemyDocumentRepo(db)
    from uuid import UUID
    versions = repo.list_versions(UUID(doc_id))
    db.close()

    if versions:
        ver_id = str(versions[0].version_id)

        # Student cannot reindex (403)
        student_reindex = client.post(
            f"/api/versions/{ver_id}/reindex",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert student_reindex.status_code == 403

        # Admin reindexes -> 202 Accepted
        admin_reindex = client.post(
            f"/api/versions/{ver_id}/reindex",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_reindex.status_code == 202
        assert admin_reindex.json()["status"] == "queued"

