"""
Unit tests for Phase 0 setup: domain entities, access policy, citation rules, and health API.
"""
import sys
from pathlib import Path
from uuid import uuid4

# Ensure backend root is on sys.path
backend_path = Path(__file__).resolve().parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from app.domain.entities import (
    Document,
    DocumentChunk,
    DocumentVersion,
    Role,
    User,
    VersionStatus,
)
from app.domain.access_policy import (
    can_user_access_document,
    filter_authorized_chunks,
    get_allowed_document_ids,
)
from app.domain.citation_rules import build_citations, validate_citations
from app.adapters.llm.fake_llm import FakeLLM
from app.main import app


def test_domain_entity_creation():
    user_id = uuid4()
    user = User(
        user_id=user_id,
        name="Test Admin",
        email="admin@test.edu",
        password_hash="hashed_pw",
        role=Role.ADMIN,
    )
    assert user.role == Role.ADMIN
    assert user.is_active is True

    doc = Document(
        title="Academic Regulations 2026",
        document_type="regulation",
        created_by=user_id,
        department="Academic Affairs",
        allowed_roles=[Role.STUDENT, Role.FACULTY],
    )
    assert len(doc.allowed_roles) == 2
    assert Role.STUDENT in doc.allowed_roles


def test_domain_access_policy():
    admin_id = uuid4()
    doc_student = Document(
        title="Student Handbook",
        document_type="guideline",
        created_by=admin_id,
        allowed_roles=[Role.STUDENT],
    )
    doc_faculty = Document(
        title="Faculty Senate By-laws",
        document_type="regulation",
        created_by=admin_id,
        allowed_roles=[Role.FACULTY],
    )

    # Admin accesses everything
    assert can_user_access_document(Role.ADMIN, doc_student) is True
    assert can_user_access_document(Role.ADMIN, doc_faculty) is True

    # Student accesses only student allowed docs
    assert can_user_access_document(Role.STUDENT, doc_student) is True
    assert can_user_access_document(Role.STUDENT, doc_faculty) is False

    # Faculty accesses only faculty allowed docs
    assert can_user_access_document(Role.FACULTY, doc_student) is False
    assert can_user_access_document(Role.FACULTY, doc_faculty) is True

    allowed_for_student = get_allowed_document_ids(Role.STUDENT, [doc_student, doc_faculty])
    assert doc_student.document_id in allowed_for_student
    assert doc_faculty.document_id not in allowed_for_student


def test_post_merge_authoritative_filter():
    v1_id = uuid4()
    v2_id = uuid4()

    c1 = DocumentChunk(
        version_id=v1_id,
        chunk_index=0,
        page_start=1,
        page_end=1,
        chunk_text="Public rule text",
        token_count=10,
    )
    c2 = DocumentChunk(
        version_id=v2_id,
        chunk_index=0,
        page_start=1,
        page_end=1,
        chunk_text="Restricted rule text",
        token_count=10,
    )

    allowed_versions = {v1_id}
    # Student sees only v1 chunks
    filtered = filter_authorized_chunks(Role.STUDENT, allowed_versions, [c1, c2])
    assert len(filtered) == 1
    assert filtered[0].chunk_id == c1.chunk_id

    # Admin sees both chunks
    admin_filtered = filter_authorized_chunks(Role.ADMIN, allowed_versions, [c1, c2])
    assert len(admin_filtered) == 2


def test_citation_validation():
    c1 = DocumentChunk(
        version_id=uuid4(),
        chunk_index=0,
        page_start=3,
        page_end=3,
        chunk_text="Attendance requirement is 75% minimum.",
        token_count=10,
        section_heading="3.2 Minimum Attendance",
    )
    prompt_map = {1: c1}

    # Valid citation [1]
    is_valid, chunks = validate_citations([1], prompt_map)
    assert is_valid is True
    assert len(chunks) == 1

    # Invalid citation [2] (not in prompt)
    is_valid_bad, chunks_bad = validate_citations([2], prompt_map)
    assert is_valid_bad is False
    assert len(chunks_bad) == 0

    # Empty citation
    is_valid_empty, _ = validate_citations([], prompt_map)
    assert is_valid_empty is False


def test_fake_llm_behavior():
    fake = FakeLLM()
    c1 = DocumentChunk(
        version_id=uuid4(),
        chunk_index=0,
        page_start=1,
        page_end=1,
        chunk_text="Course drop deadline is Week 4.",
        token_count=10,
    )
    result = fake.generate_answer("When is drop deadline?", [(1, c1)])
    assert result["sufficient"] is True
    assert 1 in result["citations"]
    assert "[1]" in result["answer"]

    # When no chunks are provided, FakeLLM returns sufficient=False
    empty_result = fake.generate_answer("Unknown question", [])
    assert empty_result["sufficient"] is False


def test_api_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["database"] == "ok"
