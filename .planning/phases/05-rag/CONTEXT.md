# Phase 5: Grounded RAG Generation, Citations and PII Redaction - Context

## Objective
Implement grounded response generation behind `LLMPort`, prompt contracts with strict JSON citation schemas, citation validation rules, neutral abstention gating, regex PII redaction on user queries, multi-turn conversation memory with follow-up query rewriting, chat session persistence, and automated security leak tests.

## Specifications (Blueprint Section 4.3, 4.4, 5.2 & 12.1)
- PII Redaction: Regex-based removal of registration numbers, emails, and phone numbers before external API transmission.
- Prompt Contract: Grounded JSON contract `{ "answer": str, "citations": [int], "sufficient": bool }`. Answers must cite only supplied context chunks.
- Citation Checker: Verifies each cited chunk number against prompt context; answers failing citation validation trigger abstention.
- Abstention: Returns neutral standard message for insufficient evidence or restricted queries, keeping restricted document existence secret.
- Conversational Memory: Rewrites follow-up questions using last 3 turns into standalone queries; each turn runs full fresh permission check.
- Automated Leak Test: Automated test querying confidential faculty/admin documents as a student, asserting zero leaks in prompt chunks, citations, or traces.

