"""
Answer question use case.
Orchestrates PII redaction, conversational follow-up rewriting, hybrid retrieval,
LLM prompt generation, citation validation, abstention enforcement, and chat persistence.
"""
import time
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.application.ports import (
    ChatRepoPort,
    DocumentRepoPort,
    EmbeddingPort,
    KeywordIndexPort,
    LLMPort,
    PiiRedactorPort,
    VectorStorePort,
)
from app.application.use_cases.retrieve_chunks import HybridRetrievalUseCase
from app.composition.settings import get_settings
from app.domain.access_policy import STANDARD_ABSTAIN_MESSAGE
from app.domain.citation_rules import build_citations, validate_citations
from app.domain.entities import ChatMessage, ChatSession, DocumentChunk, Role, User


class AnswerQuestionUseCase:
    def __init__(
        self,
        doc_repo: DocumentRepoPort,
        chat_repo: ChatRepoPort,
        embedding_adapter: EmbeddingPort,
        vector_store: VectorStorePort,
        keyword_index: KeywordIndexPort,
        llm: LLMPort,
        pii_redactor: PiiRedactorPort,
    ):
        self.doc_repo = doc_repo
        self.chat_repo = chat_repo
        self.retrieval_use_case = HybridRetrievalUseCase(
            doc_repo=doc_repo,
            embedding_adapter=embedding_adapter,
            vector_store=vector_store,
            keyword_index=keyword_index,
        )
        self.llm = llm
        self.pii_redactor = pii_redactor
        self.settings = get_settings()

    def execute(
        self,
        question: str,
        user: User,
        session_id: Optional[UUID] = None,
    ) -> ChatMessage:
        start_time = time.perf_counter()
        message_id = uuid4()

        # Step 1: Redact PII from user question
        redacted_question = self.pii_redactor.redact(question)

        # Step 2: Handle session and conversational history
        if session_id:
            session = self.chat_repo.get_session(session_id)
            if not session or session.user_id != user.user_id:
                session = self.chat_repo.create_session(
                    ChatSession(session_id=session_id, user_id=user.user_id, title=redacted_question[:50])
                )
        else:
            session = self.chat_repo.create_session(
                ChatSession(user_id=user.user_id, title=redacted_question[:50])
            )
            session_id = session.session_id

        # Fetch prior turns for follow-up rewriting
        past_messages = self.chat_repo.get_messages_for_session(session_id)
        history = [
            {"question": m.question_redacted, "answer": m.answer}
            for m in past_messages[-3:]
        ]

        # Step 3: Rewrite follow-up if conversation exists
        query_to_search = (
            self.llm.rewrite_followup(redacted_question, history)
            if history
            else redacted_question
        )

        # Step 4: Hybrid Retrieval
        chunks, trace, passed_gate = self.retrieval_use_case.execute(
            query=query_to_search,
            user_role=user.role,
            message_id=message_id,
        )

        answer_text = STANDARD_ABSTAIN_MESSAGE
        abstained = True
        resolved_citations = []

        # Step 5: Grounded LLM Generation & Citation Validation
        if passed_gate and chunks:
            numbered_chunks = [(i + 1, c) for i, c in enumerate(chunks)]
            numbered_map: Dict[int, DocumentChunk] = {num: c for num, c in numbered_chunks}

            llm_result = self.llm.generate_answer(
                question=query_to_search,
                numbered_chunks=numbered_chunks,
                history=history,
            )

            is_sufficient = llm_result.get("sufficient", False)
            cited_nums = llm_result.get("citations", [])

            is_valid_cit, valid_chunks = validate_citations(cited_nums, numbered_map)

            if is_sufficient and is_valid_cit and len(valid_chunks) > 0:
                answer_text = llm_result.get("answer", "")
                abstained = False

                # Resolve metadata for citations
                version_ids = {c.version_id for c in valid_chunks}
                versions_map = {}
                documents_map = {}
                for vid in version_ids:
                    ver = self.doc_repo.get_version(vid)
                    if ver:
                        versions_map[vid] = ver
                        doc = self.doc_repo.get_document(ver.document_id)
                        if doc:
                            documents_map[doc.document_id] = doc

                resolved_citations = build_citations(
                    cited_numbers=cited_nums,
                    prompt_chunks_map=numbered_map,
                    versions_map=versions_map,
                    documents_map=documents_map,
                )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        message = ChatMessage(
            message_id=message_id,
            session_id=session_id,
            question_redacted=redacted_question,
            answer=answer_text,
            abstained=abstained,
            model=self.settings.llm_model,
            latency_ms=latency_ms,
            citations=resolved_citations,
        )

        saved_message = self.chat_repo.create_message(
            message=message,
            citations=resolved_citations,
            trace=trace,
        )

        return saved_message

