"""
Application Port Interfaces for University Document Intelligence.
Clean/Hexagonal Architecture: Ports define abstract interfaces implemented by Adapters.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from app.domain.entities import (
    AuditLog,
    ChatMessage,
    ChatSession,
    Citation,
    Document,
    DocumentChunk,
    DocumentVersion,
    IngestionJob,
    RetrievalTrace,
    Role,
    User,
    VersionStatus,
)


class LLMPort(ABC):
    @abstractmethod
    def generate_answer(
        self,
        question: str,
        numbered_chunks: List[Tuple[int, DocumentChunk]],
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Returns JSON dict with shape:
        { "answer": str, "citations": List[int], "sufficient": bool }
        """
        pass

    @abstractmethod
    def rewrite_followup(
        self,
        question: str,
        history: List[Dict[str, str]],
    ) -> str:
        """
        Rewrites conversational follow-up into a standalone question.
        """
        pass


class EmbeddingPort(ABC):
    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass


class VectorStorePort(ABC):
    @abstractmethod
    def upsert_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
        allowed_roles_per_chunk: List[List[Role]],
        status: VersionStatus,
    ) -> None:
        pass

    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        user_role: Role,
        top_k: int = 20,
        status: VersionStatus = VersionStatus.CURRENT,
    ) -> List[Tuple[UUID, int, float]]:
        """
        Returns list of (chunk_id, rank, score)
        """
        pass

    @abstractmethod
    def update_version_status(
        self,
        version_id: UUID,
        new_status: VersionStatus,
    ) -> None:
        pass

    @abstractmethod
    def update_document_roles(
        self,
        document_id: UUID,
        new_roles: List[Role],
    ) -> None:
        pass


class KeywordIndexPort(ABC):
    @abstractmethod
    def search(
        self,
        query_text: str,
        allowed_version_ids: Set[UUID],
        top_k: int = 20,
    ) -> List[Tuple[UUID, int, float]]:
        """
        Returns list of (chunk_id, rank, score)
        """
        pass


class FileStoragePort(ABC):
    @abstractmethod
    def save_file(self, file_bytes: bytes, original_filename: str) -> Tuple[str, str]:
        """
        Saves file under a UUID filename.
        Returns (relative_file_path, sha256_hex).
        """
        pass

    @abstractmethod
    def read_file(self, relative_path: str) -> bytes:
        pass

    @abstractmethod
    def file_exists(self, relative_path: str) -> bool:
        pass


class PiiRedactorPort(ABC):
    @abstractmethod
    def redact(self, text: str) -> str:
        """
        Redacts personal identifiable information: student IDs, registration numbers,
        emails, and phone numbers.
        """
        pass


class DocumentRepoPort(ABC):
    @abstractmethod
    def create_document(self, document: Document, allowed_roles: List[Role]) -> Document:
        pass

    @abstractmethod
    def get_document(self, document_id: UUID) -> Optional[Document]:
        pass

    @abstractmethod
    def list_documents(self, user_role: Role) -> List[Document]:
        pass

    @abstractmethod
    def update_document_permissions(self, document_id: UUID, roles: List[Role]) -> None:
        pass

    @abstractmethod
    def create_version(self, version: DocumentVersion) -> DocumentVersion:
        pass

    @abstractmethod
    def get_version(self, version_id: UUID) -> Optional[DocumentVersion]:
        pass

    @abstractmethod
    def get_current_version(self, document_id: UUID) -> Optional[DocumentVersion]:
        pass

    @abstractmethod
    def list_versions(self, document_id: UUID) -> List[DocumentVersion]:
        pass

    @abstractmethod
    def update_version_status(
        self,
        version_id: UUID,
        new_status: VersionStatus,
        supersedes_id: Optional[UUID] = None,
    ) -> None:
        pass

    @abstractmethod
    def get_allowed_version_ids(self, user_role: Role) -> Set[UUID]:
        pass

    @abstractmethod
    def save_chunks(self, chunks: List[DocumentChunk]) -> None:
        pass

    @abstractmethod
    def get_chunk(self, chunk_id: UUID) -> Optional[DocumentChunk]:
        pass

    @abstractmethod
    def get_chunks_by_ids(self, chunk_ids: List[UUID]) -> List[DocumentChunk]:
        pass

    @abstractmethod
    def get_chunks_for_version(self, version_id: UUID) -> List[DocumentChunk]:
        pass

    @abstractmethod
    def create_job(self, job: IngestionJob) -> IngestionJob:
        pass

    @abstractmethod
    def update_job(self, job: IngestionJob) -> IngestionJob:
        pass

    @abstractmethod
    def get_job_by_version(self, version_id: UUID) -> Optional[IngestionJob]:
        pass


class UserRepoPort(ABC):
    @abstractmethod
    def create_user(self, user: User) -> User:
        pass

    @abstractmethod
    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        pass

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def list_users(self) -> List[User]:
        pass


class ChatRepoPort(ABC):
    @abstractmethod
    def create_session(self, session: ChatSession) -> ChatSession:
        pass

    @abstractmethod
    def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        pass

    @abstractmethod
    def list_sessions_for_user(self, user_id: UUID) -> List[ChatSession]:
        pass

    @abstractmethod
    def create_message(
        self,
        message: ChatMessage,
        citations: List[Citation],
        trace: Optional[RetrievalTrace] = None,
    ) -> ChatMessage:
        pass

    @abstractmethod
    def get_messages_for_session(self, session_id: UUID) -> List[ChatMessage]:
        pass

    @abstractmethod
    def update_message_feedback(self, message_id: UUID, feedback: int) -> None:
        pass


class AuditRepoPort(ABC):
    @abstractmethod
    def log(self, audit: AuditLog) -> None:
        pass


class ClockPort(ABC):
    @abstractmethod
    def now(self) -> datetime:
        pass

