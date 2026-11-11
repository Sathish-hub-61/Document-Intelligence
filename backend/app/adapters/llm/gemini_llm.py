"""
Gemini LLM Adapter implementing LLMPort with strict grounded prompt contract.
Enforces structured JSON responses containing answer, citation indices, and sufficiency flag.
"""
import json
from typing import Any, Dict, List, Optional, Tuple

from app.application.ports import LLMPort
from app.composition.settings import get_settings
from app.domain.entities import DocumentChunk
from app.domain.errors import LLMUnavailableError

SYSTEM_PROMPT = """You are the official University Document Intelligence Assistant.
Your job is to answer user questions truthfully and accurately based SOLELY on the numbered document excerpts provided.

Strict Rules:
1. Answer ONLY using the facts stated in the numbered passages below.
2. DO NOT use external knowledge, ungrounded assumptions, or personal opinions.
3. If the provided passages do not contain adequate evidence to answer the question, you MUST set "sufficient": false, "citations": [], and provide a clear statement in "answer" that official university documents do not contain this information.
4. When evidence is sufficient, cite the source passages inline using brackets like [1], [2], and populate the "citations" list with the integer numbers corresponding to each passage you cited.
5. You MUST return ONLY valid JSON matching this exact schema:
{
  "answer": "string",
  "citations": [1, 2],
  "sufficient": true
}
"""


class GeminiLLM(LLMPort):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key
        self.model_name = model_name or settings.llm_model
        self.temperature = settings.llm_temperature
        self._client = None

    def _init_client(self):
        if self._client is None:
            if not self.api_key:
                raise LLMUnavailableError("Gemini API key is not configured in settings")
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "temperature": self.temperature,
                    "response_mime_type": "application/json",
                },
            )
        return self._client

    def generate_answer(
        self,
        question: str,
        numbered_chunks: List[Tuple[int, DocumentChunk]],
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        if not numbered_chunks:
            return {
                "answer": "I cannot find sufficient evidence in the official university documents to answer your question.",
                "citations": [],
                "sufficient": False,
            }

        client = self._init_client()

        # Build context blocks
        context_parts = []
        for num, chunk in numbered_chunks:
            heading = f" - Section: {chunk.section_heading}" if chunk.section_heading else ""
            context_parts.append(
                f"--- Source [{num}] (Page {chunk.page_start}{heading}) ---\n{chunk.chunk_text}"
            )
        context_str = "\n\n".join(context_parts)

        user_content = f"{SYSTEM_PROMPT}\n\nContext Passages:\n{context_str}\n\nUser Question:\n{question}"

        try:
            response = client.generate_content(user_content)
            raw_text = response.text.strip()
            data = json.loads(raw_text)
            return {
                "answer": data.get("answer", ""),
                "citations": data.get("citations", []),
                "sufficient": data.get("sufficient", False),
            }
        except Exception as e:
            raise LLMUnavailableError(f"Gemini API call failed: {str(e)}")

    def rewrite_followup(
        self,
        question: str,
        history: List[Dict[str, str]],
    ) -> str:
        if not history:
            return question

        client = self._init_client()
        turns_text = "\n".join(
            f"User: {t.get('question', '')}\nAssistant: {t.get('answer', '')}"
            for t in history[-3:]
        )
        prompt = (
            "Given the conversation history and the follow-up question below, rewrite the follow-up question "
            "into a standalone search question. Do not answer it, only output the rewritten question string.\n\n"
            f"History:\n{turns_text}\n\nFollow-up question: {question}\nStandalone question:"
        )
        try:
            resp = client.generate_content(prompt)
            return resp.text.strip() or question
        except Exception:
            return question

