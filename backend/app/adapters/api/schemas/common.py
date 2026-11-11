"""
Pydantic schemas matching Blueprint Section 8.2.
"""
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.domain.entities import Role, VersionStatus, JobStatus


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class UserOut(BaseModel):
    user_id: UUID
    name: str
    email: str
    role: Role
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: Role


class UploadMeta(BaseModel):
    title: str
    document_type: str
    department: Optional[str] = None
    allowed_roles: List[Role]
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class DocumentOut(BaseModel):
    document_id: UUID
    title: str
    document_type: str
    department: Optional[str] = None
    created_by: UUID
    created_at: datetime
    allowed_roles: List[Role]
    current_version: Optional[Dict[str, Any]] = None


class VersionOut(BaseModel):
    version_id: UUID
    document_id: UUID
    version_number: int
    status: VersionStatus
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    uploaded_at: datetime
    uploaded_by: UUID
    supersedes_id: Optional[UUID] = None


class CitationOut(BaseModel):
    n: int
    chunk_id: UUID
    document_id: UUID
    document_title: str
    version_number: int
    page_start: int
    section_heading: Optional[str] = None
    snippet: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    session_id: Optional[UUID] = None


class ChatResponse(BaseModel):
    message_id: UUID
    session_id: UUID
    answer: str
    abstained: bool
    citations: List[CitationOut]
    latency_ms: int


class HealthResponse(BaseModel):
    status: str
    database: str
    chroma: str
    llm: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
