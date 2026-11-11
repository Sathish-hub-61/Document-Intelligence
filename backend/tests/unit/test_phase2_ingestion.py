"""
Unit and integration tests for Phase 2: Document Ingestion, Extraction and Chunking.
"""
import io
import os
import sys
from pathlib import Path
from uuid import uuid4
import fitz
import docx
import pytest

backend_path = Path(__file__).resolve().parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from app.adapters.extraction.pymupdf_extractor import PyMuPDFExtractor
from app.adapters.extraction.docx_extractor import DocxExtractor
from app.adapters.storage.local_files import LocalFileStorage
from app.application.use_cases.chunker import DocumentChunker
from app.domain.entities import Role
from app.domain.errors import InvalidFileError
from app.main import app

client = TestClient(app)


@pytest.fixture
def sample_pdf_bytes():
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((50, 50), "Academic Regulations 2026", fontsize=16)
    page1.insert_text(
        (50, 80),
        "Section 1: Attendance Requirements\n"
        "All registered students must maintain a minimum attendance of 75 percent in each course "
        "to be eligible to appear for the end-semester examinations. Condonation up to 10 percent "
        "may be granted by the Dean on valid medical grounds.",
        fontsize=11,
    )
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Section 2: Examination and Grading", fontsize=16)
    page2.insert_text(
        (50, 80),
        "A student who secures grade F in a course must re-register and appear for the supplementary examination. "
        "The maximum permissible credits per semester is 26.",
        fontsize=11,
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def sample_docx_bytes():
    doc = docx.Document()
    doc.add_heading("Faculty Research Code of Conduct", level=1)
    doc.add_paragraph(
        "Faculty members are encouraged to submit grant proposals to external national agencies. "
        "All publications must credit the university institutional affiliation."
    )
    doc.add_heading("Sabbatical Leave Rules", level=2)
    doc.add_paragraph(
        "Permanent faculty with six years of continuous service are eligible for up to one year of sabbatical leave "
        "with full salary for advanced postdoctoral research."
    )
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_file_validation_magic_bytes(sample_pdf_bytes, sample_docx_bytes):
    storage = LocalFileStorage()

    # Valid PDF
    mime, ext = storage.validate_file(sample_pdf_bytes, "regulations.pdf")
    assert mime == "application/pdf"
    assert ext == ".pdf"

    # Valid DOCX
    mime, ext = storage.validate_file(sample_docx_bytes, "rules.docx")
    assert "wordprocessingml" in mime
    assert ext == ".docx"

    # Spoofed file (text file renamed to .pdf)
    fake_pdf = b"This is plaintext not a PDF"
    with pytest.raises(InvalidFileError):
        storage.validate_file(fake_pdf, "fake.pdf")

    # Unsupported extension
    with pytest.raises(InvalidFileError):
        storage.validate_file(b"content", "archive.zip")


def test_pdf_extraction_and_chunking(tmp_path, sample_pdf_bytes):
    pdf_file = tmp_path / "test_reg.pdf"
    pdf_file.write_bytes(sample_pdf_bytes)

    extractor = PyMuPDFExtractor()
    extracted = extractor.extract(str(pdf_file))
    assert extracted.total_pages == 2
    assert len(extracted.blocks) >= 2

    chunker = DocumentChunker(target_tokens=50, overlap_tokens=10)
    v_id = uuid4()
    chunks = chunker.chunk_document(extracted, v_id)
    assert len(chunks) >= 2
    for c in chunks:
        assert c.version_id == v_id
        assert c.token_count > 0
        assert c.page_start in (1, 2)


def test_docx_extraction_and_chunking(tmp_path, sample_docx_bytes):
    docx_file = tmp_path / "test_faculty.docx"
    docx_file.write_bytes(sample_docx_bytes)

    extractor = DocxExtractor()
    extracted = extractor.extract(str(docx_file))
    assert extracted.total_pages >= 1
    assert len(extracted.blocks) >= 2

    chunker = DocumentChunker(target_tokens=50, overlap_tokens=10)
    v_id = uuid4()
    chunks = chunker.chunk_document(extracted, v_id)
    assert len(chunks) >= 1
    assert chunks[0].section_heading is not None


def test_api_document_upload_and_role_access(sample_pdf_bytes):
    # Login as admin
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@university.edu", "password": "AdminPass123!"},
    )
    admin_token = admin_login.json()["access_token"]

    # Student cannot upload (403)
    student_login = client.post(
        "/api/auth/login",
        json={"email": "student@university.edu", "password": "StudentPass123!"},
    )
    student_token = student_login.json()["access_token"]

    upload_data = {
        "title": "Academic Regulations 2026",
        "document_type": "regulation",
        "department": "Academic Affairs",
        "allowed_roles": '["student", "faculty", "admin"]',
    }
    files = {"file": ("academic_regulations.pdf", sample_pdf_bytes, "application/pdf")}

    student_upload = client.post(
        "/api/documents",
        data=upload_data,
        files=files,
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert student_upload.status_code == 403

    # Admin uploads successfully -> 202 Accepted
    files = {"file": ("academic_regulations.pdf", sample_pdf_bytes, "application/pdf")}
    admin_upload = client.post(
        "/api/documents",
        data=upload_data,
        files=files,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_upload.status_code == 202
    resp_data = admin_upload.json()
    assert "document_id" in resp_data
    doc_id = resp_data["document_id"]
    ver_id = resp_data["version_id"]

    # Check job status endpoint
    job_resp = client.get(
        f"/api/versions/{ver_id}/jobs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] in ("queued", "extracting", "chunking", "completed")

    # Document list for student includes the doc
    student_docs = client.get(
        "/api/documents",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert student_docs.status_code == 200
    doc_ids = [d["document_id"] for d in student_docs.json()]
    assert doc_id in doc_ids

