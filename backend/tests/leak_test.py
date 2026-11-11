"""
Automated Security Leak Test.
Asserts that queries from restricted roles NEVER return unauthorized chunks,
never place unauthorized chunks in LLM prompt context, and never leak restricted chunk IDs
in retrieval traces.
"""
import sys
from pathlib import Path
from uuid import uuid4
import pytest

backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.adapters.embeddings.sentence_transformers import SentenceTransformerEmbeddingAdapter
from app.adapters.llm.fake_llm import FakeLLM
from app.adapters.persistence.chat_repo import SqlAlchemyChatRepo
from app.adapters.persistence.database import SessionLocal
from app.adapters.persistence.repositories import SqlAlchemyDocumentRepo
from app.adapters.pii.regex_redactor import RegexPiiRedactor
from app.adapters.search.pg_fulltext import PostgresFullTextSearch
from app.adapters.vector.chroma_store import ChromaVectorStore
from app.application.use_cases.answer_question import AnswerQuestionUseCase
from app.domain.entities import Document, DocumentChunk, DocumentVersion, Role, User, VersionStatus


def test_automated_security_leak_prevention(tmp_path):
    chroma_dir = str(tmp_path / "leak_test_chroma")
    vstore = ChromaVectorStore(persist_directory=chroma_dir)
    embedder = SentenceTransformerEmbeddingAdapter()
    llm = FakeLLM()
    pii = RegexPiiRedactor()

    db = SessionLocal()
    try:
        doc_repo = SqlAlchemyDocumentRepo(db)
        chat_repo = SqlAlchemyChatRepo(db)
        keyword_searcher = PostgresFullTextSearch(db)

        # 1. Create a Confidential Faculty-Only Document
        admin_id = uuid4()
        confidential_doc = Document(
            title="Confidential Faculty Remuneration and Salary Scale",
            document_type="regulation",
            created_by=admin_id,
            allowed_roles=[Role.FACULTY, Role.ADMIN],  # Student NOT allowed
        )
        saved_doc = doc_repo.create_document(confidential_doc, [Role.FACULTY, Role.ADMIN])

        confidential_ver = DocumentVersion(
            document_id=saved_doc.document_id,
            version_number=1,
            file_path="storage/original_documents/confidential.pdf",
            file_sha256="hash_confidential",
            mime_type="application/pdf",
            status=VersionStatus.CURRENT,
            uploaded_by=admin_id,
        )
        saved_ver = doc_repo.create_version(confidential_ver)

        confidential_chunk = DocumentChunk(
            version_id=saved_ver.version_id,
            chunk_index=0,
            page_start=1,
            page_end=1,
            section_heading="Professor Executive Compensation",
            chunk_text="Professor grade salary scale begins at INR 150000 with annual special allowance of INR 25000.",
            token_count=18,
        )
        doc_repo.save_chunks([confidential_chunk])

        # Upsert into Chroma
        embs = embedder.embed_documents([confidential_chunk.chunk_text])
        vstore.upsert_chunks(
            chunks=[confidential_chunk],
            embeddings=embs,
            allowed_roles_per_chunk=[[Role.FACULTY, Role.ADMIN]],
            status=VersionStatus.CURRENT,
            document_id=saved_doc.document_id,
        )

        use_case = AnswerQuestionUseCase(
            doc_repo=doc_repo,
            chat_repo=chat_repo,
            embedding_adapter=embedder,
            vector_store=vstore,
            keyword_index=keyword_searcher,
            llm=llm,
            pii_redactor=pii,
        )

        # 2. Student queries about faculty salary scale
        student_user = User(
            user_id=uuid4(),
            name="Inquisitive Student",
            email="student@univ.edu",
            password_hash="pw",
            role=Role.STUDENT,
        )

        student_msg = use_case.execute(
            question="What is the professor grade executive compensation and salary scale?",
            user=student_user,
        )

        # Assert: Student request must ABSTAIN
        assert student_msg.abstained is True
        assert len(student_msg.citations) == 0

        # Assert: Confidential chunk ID must NEVER be cited or placed in prompt
        assert str(confidential_chunk.chunk_id) not in student_msg.answer
        for prompt_record in llm.recorded_prompts:
            if prompt_record.get("question") == student_msg.question_redacted:
                chunk_ids_in_prompt = [cid for _, cid in prompt_record["chunks"]]
                assert confidential_chunk.chunk_id not in chunk_ids_in_prompt

        # 3. Faculty queries about same topic -> Permitted and receives citations
        faculty_user = User(
            user_id=uuid4(),
            name="Authorized Faculty",
            email="faculty@univ.edu",
            password_hash="pw",
            role=Role.FACULTY,
        )

        faculty_msg = use_case.execute(
            question="What is the professor grade executive compensation and salary scale?",
            user=faculty_user,
        )

        assert faculty_msg.abstained is False
        assert len(faculty_msg.citations) >= 1
        assert faculty_msg.citations[0].chunk_id == confidential_chunk.chunk_id

    finally:
        db.close()

