"""
Unit and integration tests for Phase 1: Authentication, Argon2, JWT, and Role Guards.
"""
import sys
from pathlib import Path
from datetime import timedelta
import pytest

backend_path = Path(__file__).resolve().parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from app.adapters.security.password import hash_password, verify_password
from app.adapters.security.jwt_service import create_access_token, decode_access_token
from app.domain.entities import Role, User
from app.domain.errors import AuthenticationError, ValidationError
from app.main import app

client = TestClient(app)


def test_argon2_hashing_and_verification():
    pw = "SuperSecurePassword123!"
    hashed = hash_password(pw)
    assert hashed.startswith("$argon2")
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False

    # Password shorter than 10 chars must fail
    with pytest.raises(ValidationError):
        hash_password("short9!")


def test_jwt_token_flow():
    from uuid import uuid4
    uid = uuid4()
    token = create_access_token(uid)
    decoded_uid = decode_access_token(token)
    assert decoded_uid == uid

    # Expired token test
    expired_token = create_access_token(uid, expires_delta=timedelta(seconds=-1))
    with pytest.raises(AuthenticationError):
        decode_access_token(expired_token)


def test_api_login_success():
    response = client.post(
        "/api/auth/login",
        json={"email": "student@university.edu", "password": "StudentPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "student"
    assert data["user"]["email"] == "student@university.edu"


def test_api_login_invalid_password():
    response = client.post(
        "/api/auth/login",
        json={"email": "student@university.edu", "password": "WrongPassword999!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_api_auth_me_endpoint():
    # Login as faculty
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "faculty@university.edu", "password": "FacultyPass123!"},
    )
    token = login_resp.json()["access_token"]

    # Call /api/auth/me
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    user_data = me_resp.json()
    assert user_data["email"] == "faculty@university.edu"
    assert user_data["role"] == "faculty"


def test_require_role_admin_authorization():
    # Login as student
    student_login = client.post(
        "/api/auth/login",
        json={"email": "student@university.edu", "password": "StudentPass123!"},
    )
    student_token = student_login.json()["access_token"]

    # Student tries to register a new user -> forbidden (403)
    reg_attempt = client.post(
        "/api/auth/register",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "name": "New Person",
            "email": "new@university.edu",
            "password": "ValidPassword123!",
            "role": "student",
        },
    )
    assert reg_attempt.status_code == 403
    assert reg_attempt.json()["error"]["code"] == "forbidden"

    # Login as admin
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@university.edu", "password": "AdminPass123!"},
    )
    admin_token = admin_login.json()["access_token"]

    # Admin registers a new user -> success (200)
    admin_reg = client.post(
        "/api/auth/register",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "New Faculty Member",
            "email": "newfaculty@university.edu",
            "password": "ValidPassword123!",
            "role": "faculty",
        },
    )
    assert admin_reg.status_code == 200
    assert admin_reg.json()["email"] == "newfaculty@university.edu"
