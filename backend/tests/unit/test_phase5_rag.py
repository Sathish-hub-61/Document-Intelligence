"""
Unit and integration tests for Phase 5: Grounded RAG Generation, Citations and PII Redaction.
"""
import sys
from pathlib import Path
from uuid import uuid4
import pytest

backend_path = Path(__file__).resolve().parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from app.adapters.pii.regex_redactor import RegexPiiRedactor
from app.adapters.llm.fake_llm import FakeLLM
from app.domain.entities import DocumentChunk
from app.domain.citation_rules import validate_citations
from app.main import app

client = TestClient(app)


def test_pii_redaction():
    redactor = RegexPiiRedactor()

    # Roll number / registration number redaction
    q1 = "My roll number is 2024BCSE042 and my friend's is RA2111003010123. Can we drop course?"
    r1 = redactor.redact(q1)
    assert "2024BCSE042" not in r1
    assert "RA2111003010123" not in r1
    assert "[REG_NO]" in r1

    # Email redaction
    q2 = "Please email my grade card to john.doe@university.edu or student123@gmail.com"
    r2 = redactor.redact(q2)
    assert "john.doe@university.edu" not in r2
    assert "student123@gmail.com" not in r2
    assert "[EMAIL]" in r2

    # Phone number redaction
    q3 = "Call me at +91 9876543210 or 800-555-1234 regarding fee deadline"
    r3 = redactor.redact(q3)
    assert "9876543210" not in r3
    assert "[PHONE]" in r3


def test_citation_rules_and_abstain_logic():
    c1 = DocumentChunk(
        version_id=uuid4(),
        chunk_index=0,
        page_start=1,
        page_end=1,
        section_heading="Grading",
        chunk_text="A passing grade requires at least 40 marks.",
        token_count=10,
    )
    prompt_map = {1: c1}

    # Citations match prompt
    is_valid, valid_chunks = validate_citations([1], prompt_map)
    assert is_valid is True
    assert len(valid_chunks) == 1

    # Hallucinated citation index 99
    is_valid_bad, valid_chunks_bad = validate_citations([99], prompt_map)
    assert is_valid_bad is False
    assert len(valid_chunks_bad) == 0


def test_api_chat_flow_and_feedback():
    # Login as student
    student_login = client.post(
        "/api/auth/login",
        json={"email": "student@university.edu", "password": "StudentPass123!"},
    )
    student_token = student_login.json()["access_token"]

    # Ask question
    chat_resp = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"question": "What is the minimum attendance requirement for examinations?"},
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert "message_id" in data
    assert "session_id" in data
    assert "answer" in data
    assert isinstance(data["citations"], list)
    msg_id = data["message_id"]
    sess_id = data["session_id"]

    # Check sessions list
    sess_resp = client.get(
        "/api/chat/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert sess_resp.status_code == 200
    sessions = sess_resp.json()
    assert len(sessions) >= 1

    # Check session history
    history_resp = client.get(
        f"/api/chat/sessions/{sess_id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert history_resp.status_code == 200
    messages = history_resp.json()
    assert len(messages) >= 1
    assert messages[0]["message_id"] == msg_id

    # Submit feedback (helpful: 1)
    fb_resp = client.post(
        f"/api/chat/messages/{msg_id}/feedback?feedback=1",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert fb_resp.status_code == 200
    assert fb_resp.json()["feedback"] == 1

