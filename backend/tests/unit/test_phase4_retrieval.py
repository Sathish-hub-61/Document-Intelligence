"""
Unit tests for Phase 4: Hybrid Retrieval and Strict Permission Filtering.
"""
import sys
from pathlib import Path
from uuid import uuid4
import pytest

backend_path = Path(__file__).resolve().parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.adapters.embeddings.sentence_transformers import SentenceTransformerEmbeddingAdapter
from app.adapters.vector.chroma_store import ChromaVectorStore
from app.adapters.search.pg_fulltext import PostgresFullTextSearch
from app.adapters.persistence.database import SessionLocal
from app.adapters.persistence.repositories import SqlAlchemyDocumentRepo
from app.application.pipeline.retrieval_steps import check_evidence_gate, reciprocal_rank_fusion
from app.application.use_cases.retrieve_chunks import HybridRetrievalUseCase
from app.domain.entities import Document, DocumentChunk, DocumentVersion, Role, VersionStatus


def test_rrf_scoring_algorithm():
    id1, id2, id3 = uuid4(), uuid4(), uuid4()

    # id1 is rank 1 in vector, rank 2 in keyword
    vector_hits = [(id1, 1, 0.95), (id2, 2, 0.85)]
    keyword_hits = [(id3, 1, 1.5), (id1, 2, 1.2)]

    fused = reciprocal_rank_fusion(vector_hits, keyword_hits, k=60, top_n=3)
    assert len(fused) == 3

    # id1 should have highest fused score: 1/(60+1) + 1/(60+2)
    expected_score_id1 = (1.0 / 61) + (1.0 / 62)
    assert fused[0][0] == id1
    assert abs(fused[0][1] - expected_score_id1) < 1e-6
    assert fused[0][2]["vector_rank"] == 1
    assert fused[0][2]["keyword_rank"] == 2


def test_evidence_gate():
    id1 = uuid4()
    # High score passes
    high_candidates = [(id1, 0.025, {})]
    assert check_evidence_gate(high_candidates, min_evidence_score=0.015) is True

    # Low score rejected
    low_candidates = [(id1, 0.005, {})]
    assert check_evidence_gate(low_candidates, min_evidence_score=0.015) is False

    # Empty candidate list rejected
    assert check_evidence_gate([], min_evidence_score=0.015) is False


def test_hybrid_retrieval_role_isolation(tmp_path):
    chroma_dir = str(tmp_path / "chroma_test_retrieval")
    vstore = ChromaVectorStore(persist_directory=chroma_dir)
    embedder = SentenceTransformerEmbeddingAdapter()

    db = SessionLocal()
    try:
        repo = SqlAlchemyDocumentRepo(db)
        keyword_searcher = PostgresFullTextSearch(db)

        # 1. Create Public Student Document
        admin_id = uuid4()
        doc_student = Document(
            title="Student Exam Guidelines",
            document_type="guideline",
            created_by=admin_id,
            allowed_roles=[Role.STUDENT, Role.ADMIN],
        )
        saved_doc_student = repo.create_document(doc_student, [Role.STUDENT, Role.ADMIN])

        ver_student = DocumentVersion(
            document_id=saved_doc_student.document_id,
            version_number=1,
            file_path="storage/original_documents/sample1.pdf",
            file_sha256="hash1",
            mime_type="application/pdf",
            status=VersionStatus.CURRENT,
            uploaded_by=admin_id,
        )
        saved_ver_student = repo.create_version(ver_student)

        chunk_student = DocumentChunk(
            version_id=saved_ver_student.version_id,
            chunk_index=0,
            page_start=1,
            page_end=1,
            section_heading="Exam Hall Rules",
            chunk_text="Students must carry hall ticket and university identity card to the examination hall.",
            token_count=15,
        )
        repo.save_chunks([chunk_student])

        # 2. Create Confidential Faculty Document
        doc_faculty = Document(
            title="Confidential Question Paper Setting Rules",
            document_type="procedure",
            created_by=admin_id,
            allowed_roles=[Role.FACULTY, Role.ADMIN],
        )
        saved_doc_faculty = repo.create_document(doc_faculty, [Role.FACULTY, Role.ADMIN])

        ver_faculty = DocumentVersion(
            document_id=saved_doc_faculty.document_id,
            version_number=1,
            file_path="storage/original_documents/sample2.pdf",
            file_sha256="hash2",
            mime_type="application/pdf",
            status=VersionStatus.CURRENT,
            uploaded_by=admin_id,
        )
        saved_ver_faculty = repo.create_version(ver_faculty)

        chunk_faculty = DocumentChunk(
            version_id=saved_ver_faculty.version_id,
            chunk_index=0,
            page_start=1,
            page_end=1,
            section_heading="Question Paper Moderation",
            chunk_text="Confidential scheme of valuation and question moderation protocols for examiners.",
            token_count=15,
        )
        repo.save_chunks([chunk_faculty])

        # Upsert both into Chroma
        embs = embedder.embed_documents([chunk_student.chunk_text, chunk_faculty.chunk_text])
        vstore.upsert_chunks(
            chunks=[chunk_student, chunk_faculty],
            embeddings=embs,
            allowed_roles_per_chunk=[[Role.STUDENT, Role.ADMIN], [Role.FACULTY, Role.ADMIN]],
            status=VersionStatus.CURRENT,
            document_id=saved_doc_student.document_id,
        )

        use_case = HybridRetrievalUseCase(
            doc_repo=repo,
            embedding_adapter=embedder,
            vector_store=vstore,
            keyword_index=keyword_searcher,
        )

        # Faculty asks about examination -> retrieves chunks
        faculty_chunks, faculty_trace, faculty_passed = use_case.execute(
            query="examination hall ticket rules",
            user_role=Role.FACULTY,
        )
        assert faculty_passed is True
        assert len(faculty_chunks) >= 1

        # Student asks about question paper moderation -> CANNOT retrieve confidential faculty chunk
        student_chunks, student_trace, student_passed = use_case.execute(
            query="confidential question paper moderation and valuation scheme",
            user_role=Role.STUDENT,
        )
        # Assert confidential chunk NEVER reaches sent_to_llm for student
        student_sent_ids = [c.chunk_id for c in student_chunks]
        assert chunk_faculty.chunk_id not in student_sent_ids
        assert chunk_faculty.chunk_id not in student_trace.sent_to_llm

    finally:
        db.close()

