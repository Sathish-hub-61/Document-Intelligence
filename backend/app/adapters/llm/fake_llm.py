"""
Fake LLM Adapter for testing and offline development.
Implements LLMPort without network calls.
"""
from typing import Any, Dict, List, Optional, Tuple

from app.application.ports import LLMPort
from app.domain.entities import DocumentChunk


class FakeLLM(LLMPort):
    def __init__(self, default_response: Optional[str] = None):
        self.default_response = default_response
        self.recorded_prompts: List[Dict[str, Any]] = []

    def generate_answer(
        self,
        question: str,
        numbered_chunks: List[Tuple[int, DocumentChunk]],
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        self.recorded_prompts.append({
            "question": question,
            "chunks": [(num, chunk.chunk_id) for num, chunk in numbered_chunks],
            "history": history,
        })

        if not numbered_chunks:
            return {
                "answer": "I cannot find sufficient evidence in the official university documents to answer your question.",
                "citations": [],
                "sufficient": False,
            }

        # Deterministic cited answer citing the first available chunk
        first_num = numbered_chunks[0][0]
        first_chunk = numbered_chunks[0][1]
        answer_text = (
            self.default_response
            or f"Based on official documents, {first_chunk.chunk_text[:120].strip()} [{first_num}]."
        )
        return {
            "answer": answer_text,
            "citations": [first_num],
            "sufficient": True,
        }

    def rewrite_followup(
        self,
        question: str,
        history: List[Dict[str, str]],
    ) -> str:
        if not history:
            return question
        last_turn = history[-1].get("question", "")
        return f"{last_turn} Context: {question}"

