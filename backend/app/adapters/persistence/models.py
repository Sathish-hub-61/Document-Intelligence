"""
SQLAlchemy ORM models matching Blueprint Section 7.2.
Compatible with PostgreSQL 16 and SQLite.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import relationship

from app.adapters.persistence.database import Base
from app.domain.entities import JobStatus, Role, VersionStatus


class UserModel(Base):
    __tablename__ = "users"

    user_id = Column(Uuid, primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(SQLEnum(Role, native_enum=False), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    created_documents = relationship("DocumentModel", back_populates="creator")
    chat_sessions = relationship("ChatSessionModel", back_populates="user")


class DocumentModel(Base):
    __tablename__ = "documents"

    document_id = Column(Uuid, primary_key=True, default=uuid4)
    title = Column(Text, nullable=False)
    department = Column(Text, nullable=True)
    document_type = Column(String(100), nullable=False)  # regulation, circular, calendar, guideline, procedure
    created_by = Column(Uuid, ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    creator = relationship("UserModel", back_populates="created_documents")
    versions = relationship("DocumentVersionModel", back_populates="document", cascade="all, delete-orphan")
    permissions = relationship("DocumentPermissionModel", back_populates="document", cascade="all, delete-orphan")


class DocumentPermissionModel(Base):
    __tablename__ = "document_permissions"

    document_id = Column(Uuid, ForeignKey("documents.document_id", ondelete="CASCADE"), primary_key=True)
    role = Column(SQLEnum(Role, native_enum=False), primary_key=True)

    document = relationship("DocumentModel", back_populates="permissions")


class DocumentVersionModel(Base):
    __tablename__ = "document_versions"

    version_id = Column(Uuid, primary_key=True, default=uuid4)
    document_id = Column(Uuid, ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    file_path = Column(Text, nullable=False)
    file_sha256 = Column(String(64), nullable=False)
    mime_type = Column(String(100), nullable=False)
    page_count = Column(Integer, nullable=True)
    status = Column(SQLEnum(VersionStatus, native_enum=False), nullable=False, default=VersionStatus.DRAFT, index=True)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    uploaded_by = Column(Uuid, ForeignKey("users.user_id"), nullable=False)
    supersedes_id = Column(Uuid, ForeignKey("document_versions.version_id"), nullable=True)
    scope = Column(JSON, nullable=True)

    document = relationship("DocumentModel", back_populates="versions")
    chunks = relationship("DocumentChunkModel", back_populates="version", cascade="all, delete-orphan")
    jobs = relationship("IngestionJobModel", back_populates="version", cascade="all, delete-orphan")


class DocumentChunkModel(Base):
    __tablename__ = "document_chunks"

    chunk_id = Column(Uuid, primary_key=True, default=uuid4)
    version_id = Column(Uuid, ForeignKey("document_versions.version_id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_start = Column(Integer, nullable=False)
    page_end = Column(Integer, nullable=False)
    section_heading = Column(Text, nullable=True)
    chunk_text = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)
    attributes = Column(JSON, nullable=True)

    version = relationship("DocumentVersionModel", back_populates="chunks")
    citations = relationship("MessageCitationModel", back_populates="chunk")


class IngestionJobModel(Base):
    __tablename__ = "ingestion_jobs"

    job_id = Column(Uuid, primary_key=True, default=uuid4)
    version_id = Column(Uuid, ForeignKey("document_versions.version_id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(SQLEnum(JobStatus, native_enum=False), nullable=False, default=JobStatus.QUEUED, index=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    version = relationship("DocumentVersionModel", back_populates="jobs")


class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(Uuid, primary_key=True, default=uuid4)
    user_id = Column(Uuid, ForeignKey("users.user_id"), nullable=False, index=True)
    title = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("UserModel", back_populates="chat_sessions")
    messages = relationship("ChatMessageModel", back_populates="session", cascade="all, delete-orphan")


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    message_id = Column(Uuid, primary_key=True, default=uuid4)
    session_id = Column(Uuid, ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    question_redacted = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    abstained = Column(Boolean, nullable=False, default=False)
    model = Column(String(100), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    feedback = Column(SmallInteger, nullable=True)  # 1 or -1
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    session = relationship("ChatSessionModel", back_populates="messages")
    citations = relationship("MessageCitationModel", back_populates="message", cascade="all, delete-orphan")
    retrieval_trace = relationship("RetrievalTraceModel", back_populates="message", uselist=False, cascade="all, delete-orphan")


class MessageCitationModel(Base):
    __tablename__ = "message_citations"

    message_id = Column(Uuid, ForeignKey("chat_messages.message_id", ondelete="CASCADE"), primary_key=True)
    chunk_id = Column(Uuid, ForeignKey("document_chunks.chunk_id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, primary_key=True)

    message = relationship("ChatMessageModel", back_populates="citations")
    chunk = relationship("DocumentChunkModel", back_populates="citations")


class RetrievalTraceModel(Base):
    __tablename__ = "retrieval_traces"

    message_id = Column(Uuid, ForeignKey("chat_messages.message_id", ondelete="CASCADE"), primary_key=True)
    allowed_versions = Column(Integer, nullable=True)
    vector_hits = Column(JSON, nullable=True)
    keyword_hits = Column(JSON, nullable=True)
    fused = Column(JSON, nullable=True)
    sent_to_llm = Column(JSON, nullable=True)

    message = relationship("ChatMessageModel", back_populates="retrieval_trace")


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Uuid, ForeignKey("users.user_id"), nullable=True)
    action = Column(String(100), nullable=False)
    target_id = Column(Uuid, nullable=True)
    detail = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class EvalQuestionModel(Base):
    __tablename__ = "eval_questions"

    question_id = Column(Uuid, primary_key=True, default=uuid4)
    question = Column(Text, nullable=False)
    expected_document = Column(Text, nullable=True)
    expected_page = Column(Integer, nullable=True)
    expected_abstain = Column(Boolean, nullable=False, default=False)
    required_role = Column(SQLEnum(Role, native_enum=False), nullable=False)
    category = Column(String(100), nullable=True)


class EvalRunModel(Base):
    __tablename__ = "eval_runs"

    run_id = Column(Uuid, primary_key=True, default=uuid4)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_questions = Column(Integer, nullable=False, default=0)
    hit_rate_at_5 = Column(SmallInteger, nullable=True)
    citation_accuracy = Column(SmallInteger, nullable=True)
    abstain_accuracy = Column(SmallInteger, nullable=True)
    leak_count = Column(Integer, nullable=False, default=0)
    avg_latency_ms = Column(Integer, nullable=True)


class EvalResultModel(Base):
    __tablename__ = "eval_results"

    result_id = Column(Uuid, primary_key=True, default=uuid4)
    run_id = Column(Uuid, ForeignKey("eval_runs.run_id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Uuid, ForeignKey("eval_questions.question_id"), nullable=False)
    actual_answer = Column(Text, nullable=False)
    actual_abstained = Column(Boolean, nullable=False)
    hit = Column(Boolean, nullable=False)
    correct = Column(Boolean, nullable=False)
    citations_valid = Column(Boolean, nullable=False)
    leak_detected = Column(Boolean, nullable=False, default=False)
    latency_ms = Column(Integer, nullable=False)

