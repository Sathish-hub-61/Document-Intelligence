"""
Domain entities and enumerations for University Document Intelligence.
Pure Python dataclasses with zero framework or database dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class Role(str, Enum):
    ADMIN = "admin"
    STUDENT = "student"
    FACULTY = "faculty"
    STAFF = "staff"


class VersionStatus(str, Enum):
    DRAFT = "draft"
    CURRENT = "current"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class JobStatus(str, Enum):
    QUEUED = "queued"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class User:
    email: str
    password_hash: str
    role: Role
    name: str
    user_id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Document:
    title: str
    document_type: str  # regulation, circular, calendar, guideline, procedure
    created_by: UUID
    department: Optional[str] = None
    document_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    allowed_roles: List[Role] = field(default_factory=list)


@dataclass
class DocumentVersion:
    document_id: UUID
    version_number: int
    file_path: str
    file_sha256: str
    mime_type: str
    uploaded_by: UUID
    version_id: UUID = field(default_factory=uuid4)
    page_count: Optional[int] = None
    status: VersionStatus = VersionStatus.DRAFT
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    uploaded_at: datetime = field(default_factory=datetime.utcnow)
    supersedes_id: Optional[UUID] = None
    scope: Optional[Dict[str, Any]] = None


@dataclass
class DocumentChunk:
    version_id: UUID
    chunk_index: int
    page_start: int
    page_end: int
    chunk_text: str
    token_count: int
    chunk_id: UUID = field(default_factory=uuid4)
    section_heading: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None


@dataclass
class IngestionJob:
    version_id: UUID
    job_id: UUID = field(default_factory=uuid4)
    status: JobStatus = JobStatus.QUEUED
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


@dataclass
class ChatSession:
    user_id: UUID
    session_id: UUID = field(default_factory=uuid4)
    title: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Citation:
    n: int
    chunk_id: UUID
    document_id: UUID
    document_title: str
    version_number: int
    page_start: int
    snippet: str
    section_heading: Optional[str] = None


@dataclass
class ChatMessage:
    session_id: UUID
    question_redacted: str
    answer: str
    abstained: bool = False
    message_id: UUID = field(default_factory=uuid4)
    model: Optional[str] = None
    latency_ms: Optional[int] = None
    feedback: Optional[int] = None  # 1 (helpful) or -1 (unhelpful)
    citations: List[Citation] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RetrievalTrace:
    message_id: UUID
    allowed_versions: int
    vector_hits: List[Dict[str, Any]] = field(default_factory=list)
    keyword_hits: List[Dict[str, Any]] = field(default_factory=list)
    fused: List[Dict[str, Any]] = field(default_factory=list)
    sent_to_llm: List[UUID] = field(default_factory=list)


@dataclass
class AuditLog:
    action: str
    user_id: Optional[UUID] = None
    target_id: Optional[UUID] = None
    detail: Optional[Dict[str, Any]] = None
    audit_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

