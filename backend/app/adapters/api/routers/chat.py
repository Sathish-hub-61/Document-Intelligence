"""
Chat and Q&A API endpoints matching Blueprint Section 8.1.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.adapters.api.dependencies import get_current_user
from app.adapters.api.schemas.common import ChatRequest, ChatResponse, CitationOut
from app.adapters.embeddings.sentence_transformers import SentenceTransformerEmbeddingAdapter
from app.adapters.llm.fake_llm import FakeLLM
from app.adapters.llm.gemini_llm import GeminiLLM
from app.adapters.persistence.chat_repo import SqlAlchemyChatRepo
from app.adapters.persistence.database import get_db
from app.adapters.persistence.repositories import SqlAlchemyDocumentRepo
from app.adapters.pii.regex_redactor import RegexPiiRedactor
from app.adapters.search.pg_fulltext import PostgresFullTextSearch
from app.adapters.vector.chroma_store import ChromaVectorStore
from app.application.use_cases.answer_question import AnswerQuestionUseCase
from app.composition.settings import get_settings
from app.domain.entities import Role, User
from app.domain.errors import EntityNotFoundError, ForbiddenError

router = APIRouter(prefix="/api/chat", tags=["Chat"])


def _get_llm_adapter():
    settings = get_settings()
    if settings.llm_provider == "gemini" and settings.llm_api_key:
        return GeminiLLM()
    return FakeLLM()


@router.post("", response_model=ChatResponse)
def ask_question(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc_repo = SqlAlchemyDocumentRepo(db)
    chat_repo = SqlAlchemyChatRepo(db)
    embedder = SentenceTransformerEmbeddingAdapter()
    vstore = ChromaVectorStore()
    keyword_index = PostgresFullTextSearch(db)
    llm = _get_llm_adapter()
    pii_redactor = RegexPiiRedactor()

    use_case = AnswerQuestionUseCase(
        doc_repo=doc_repo,
        chat_repo=chat_repo,
        embedding_adapter=embedder,
        vector_store=vstore,
        keyword_index=keyword_index,
        llm=llm,
        pii_redactor=pii_redactor,
    )

    message = use_case.execute(
        question=request.question,
        user=current_user,
        session_id=request.session_id,
    )

    citations_out = [
        CitationOut(
            n=c.n,
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_title=c.document_title,
            version_number=c.version_number,
            page_start=c.page_start,
            section_heading=c.section_heading,
            snippet=c.snippet,
        )
        for c in message.citations
    ]

    return ChatResponse(
        message_id=message.message_id,
        session_id=message.session_id,
        answer=message.answer,
        abstained=message.abstained,
        citations=citations_out,
        latency_ms=message.latency_ms or 0,
    )


@router.get("/sessions")
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat_repo = SqlAlchemyChatRepo(db)
    sessions = chat_repo.list_sessions_for_user(current_user.user_id)
    return [
        {
            "session_id": str(s.session_id),
            "title": s.title,
            "created_at": s.created_at,
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
def get_session_messages(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat_repo = SqlAlchemyChatRepo(db)
    session = chat_repo.get_session(session_id)
    if not session:
        raise EntityNotFoundError("Chat session not found")

    if session.user_id != current_user.user_id and current_user.role != Role.ADMIN:
        raise ForbiddenError("Not authorized to view this session")

    messages = chat_repo.get_messages_for_session(session_id)
    out = []
    for m in messages:
        citations = [
            CitationOut(
                n=c.n,
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_title=c.document_title,
                version_number=c.version_number,
                page_start=c.page_start,
                section_heading=c.section_heading,
                snippet=c.snippet,
            )
            for c in m.citations
        ]
        out.append({
            "message_id": str(m.message_id),
            "question": m.question_redacted,
            "answer": m.answer,
            "abstained": m.abstained,
            "citations": citations,
            "latency_ms": m.latency_ms,
            "feedback": m.feedback,
            "created_at": m.created_at,
        })
    return out


@router.post("/messages/{message_id}/feedback")
def submit_feedback(
    message_id: UUID,
    feedback: int,  # 1 for helpful, -1 for unhelpful
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat_repo = SqlAlchemyChatRepo(db)
    chat_repo.update_message_feedback(message_id, feedback)
    return {"status": "ok", "message_id": str(message_id), "feedback": feedback}

