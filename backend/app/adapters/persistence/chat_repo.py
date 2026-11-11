"""
SQLAlchemy Chat repository implementing ChatRepoPort.
Persists sessions, messages, citations, and retrieval traces.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.adapters.persistence.models import (
    ChatMessageModel,
    ChatSessionModel,
    DocumentChunkModel,
    DocumentModel,
    DocumentVersionModel,
    MessageCitationModel,
    RetrievalTraceModel,
)
from app.application.ports import ChatRepoPort
from app.domain.entities import ChatMessage, ChatSession, Citation, RetrievalTrace


class SqlAlchemyChatRepo(ChatRepoPort):
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, session: ChatSession) -> ChatSession:
        model = ChatSessionModel(
            session_id=session.session_id,
            user_id=session.user_id,
            title=session.title,
            created_at=session.created_at,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return ChatSession(
            session_id=model.session_id,
            user_id=model.user_id,
            title=model.title,
            created_at=model.created_at,
        )

    def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        model = self.db.query(ChatSessionModel).filter(ChatSessionModel.session_id == session_id).first()
        if not model:
            return None
        return ChatSession(
            session_id=model.session_id,
            user_id=model.user_id,
            title=model.title,
            created_at=model.created_at,
        )

    def list_sessions_for_user(self, user_id: UUID) -> List[ChatSession]:
        models = (
            self.db.query(ChatSessionModel)
            .filter(ChatSessionModel.user_id == user_id)
            .order_by(ChatSessionModel.created_at.desc())
            .all()
        )
        return [
            ChatSession(
                session_id=m.session_id,
                user_id=m.user_id,
                title=m.title,
                created_at=m.created_at,
            )
            for m in models
        ]

    def create_message(
        self,
        message: ChatMessage,
        citations: List[Citation],
        trace: Optional[RetrievalTrace] = None,
    ) -> ChatMessage:
        msg_model = ChatMessageModel(
            message_id=message.message_id,
            session_id=message.session_id,
            question_redacted=message.question_redacted,
            answer=message.answer,
            abstained=message.abstained,
            model=message.model,
            latency_ms=message.latency_ms,
            created_at=message.created_at,
        )
        self.db.add(msg_model)
        self.db.flush()

        for cit in citations:
            cit_model = MessageCitationModel(
                message_id=message.message_id,
                chunk_id=cit.chunk_id,
                position=cit.n,
            )
            self.db.add(cit_model)

        if trace:
            trace_model = RetrievalTraceModel(
                message_id=message.message_id,
                allowed_versions=trace.allowed_versions,
                vector_hits=trace.vector_hits,
                keyword_hits=trace.keyword_hits,
                fused=trace.fused,
                sent_to_llm=[str(cid) for cid in trace.sent_to_llm],
            )
            self.db.add(trace_model)

        self.db.commit()
        self.db.refresh(msg_model)

        message.citations = citations
        return message

    def get_messages_for_session(self, session_id: UUID) -> List[ChatMessage]:
        models = (
            self.db.query(ChatMessageModel)
            .filter(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.asc())
            .all()
        )
        messages: List[ChatMessage] = []
        for m in models:
            citations: List[Citation] = []
            for cm in m.citations:
                chunk = (
                    self.db.query(DocumentChunkModel)
                    .filter(DocumentChunkModel.chunk_id == cm.chunk_id)
                    .first()
                )
                if chunk:
                    ver = (
                        self.db.query(DocumentVersionModel)
                        .filter(DocumentVersionModel.version_id == chunk.version_id)
                        .first()
                    )
                    doc = (
                        self.db.query(DocumentModel)
                        .filter(DocumentModel.document_id == ver.document_id)
                        .first()
                        if ver
                        else None
                    )
                    citations.append(
                        Citation(
                            n=cm.position,
                            chunk_id=chunk.chunk_id,
                            document_id=doc.document_id if doc else chunk.version_id,
                            document_title=doc.title if doc else "Document",
                            version_number=ver.version_number if ver else 1,
                            page_start=chunk.page_start,
                            section_heading=chunk.section_heading,
                            snippet=chunk.chunk_text[:200],
                        )
                    )

            messages.append(
                ChatMessage(
                    message_id=m.message_id,
                    session_id=m.session_id,
                    question_redacted=m.question_redacted,
                    answer=m.answer,
                    abstained=m.abstained,
                    model=m.model,
                    latency_ms=m.latency_ms,
                    feedback=m.feedback,
                    citations=sorted(citations, key=lambda c: c.n),
                    created_at=m.created_at,
                )
            )
        return messages

    def update_message_feedback(self, message_id: UUID, feedback: int) -> None:
        msg = self.db.query(ChatMessageModel).filter(ChatMessageModel.message_id == message_id).first()
        if msg:
            msg.feedback = feedback
            self.db.commit()

