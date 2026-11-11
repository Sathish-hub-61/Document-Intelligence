"""
Access policy rules for University Document Intelligence.
Pure domain logic that determines document accessibility and enforces the dual-layer
permission security model.
"""
from typing import List, Set
from uuid import UUID

from app.domain.entities import Document, DocumentChunk, DocumentVersion, Role, VersionStatus


STANDARD_ABSTAIN_MESSAGE = (
    "I cannot find sufficient evidence in the official university documents to answer your question. "
    "Please check your phrasing or contact the relevant university administrative office."
)


def can_user_access_document(user_role: Role, document: Document) -> bool:
    """
    Determines whether a user role has permission to read a document.
    Admins can access everything.
    Other roles require explicit presence in allowed_roles.
    """
    if user_role == Role.ADMIN:
        return True
    return user_role in document.allowed_roles


def get_allowed_document_ids(user_role: Role, documents: List[Document]) -> Set[UUID]:
    """
    Returns the set of document UUIDs accessible to the given user role.
    """
    if user_role == Role.ADMIN:
        return {doc.document_id for doc in documents}
    return {doc.document_id for doc in documents if user_role in doc.allowed_roles}


def is_version_active_for_retrieval(version: DocumentVersion) -> bool:
    """
    Baseline rule: Only versions with status CURRENT participate in active retrieval.
    """
    return version.status == VersionStatus.CURRENT


def filter_authorized_chunks(
    user_role: Role,
    allowed_version_ids: Set[UUID],
    chunks: List[DocumentChunk],
) -> List[DocumentChunk]:
    """
    Post-merge authoritative filter: drops any chunk that does not belong
    to an approved version for this user role.
    """
    if user_role == Role.ADMIN:
        return chunks
    return [chunk for chunk in chunks if chunk.version_id in allowed_version_ids]

