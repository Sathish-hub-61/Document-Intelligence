# Product Requirements Document (PRD): University Document Intelligence

## 1. Problem Statement
University rules sit in many PDFs and DOCX files. Students and staff lose time finding the right clause, and miss that a document was revised. The product answers a question in plain language and shows exactly which document, version, and page the answer came from.

## 2. Users and Roles
- **Administrator**: Uploads, versions, and permissions documents; reviews usage and runs evaluations.
- **Student**: Asks questions about regulations, calendars, procedures.
- **Faculty**: Asks about regulations, guidelines, project, and exam rules.
- **Staff**: Asks about administrative policies and procedures.

## 3. Goals (v1)
- Correct cited answers grounded strictly in official documents.
- Strict role-based access control where unauthorized content never enters LLM prompts.
- Version history with effective dates and status tracking (draft, current, superseded, archived).
- Honest abstention when evidence is insufficient.

## 4. Non-Goals (v1)
- No personal records (student/faculty transcripts, grades).
- No university SSO integration in v1.
- No document editing by non-admins.
- No mobile app.
- No multilingual translation.
- No fine-tuned models.

## 5. Functional Requirements
- **F1 (P0)**: Admin uploads PDF and DOCX with title, type, department, allowed roles, effective date.
- **F2 (P0)**: System extracts text with page numbers and section headings.
- **F3 (P0)**: System chunks text, keeping document, version, page, and heading on every chunk.
- **F4 (P0)**: Hybrid search: vector search in ChromaDB plus PostgreSQL full-text, merged with Reciprocal Rank Fusion.
- **F5 (P0)**: Grounded answer from the LLM with numbered citations (document, version, page, heading).
- **F6 (P0)**: Abstain with clear neutral message when evidence is insufficient or access is restricted.
- **F7 (P0)**: Login with roles; every API call checks the role on the backend.
- **F8 (P0)**: Role filter applied inside retrieval, before any text reaches the LLM.
- **F9 (P1)**: Document versions with effective date and status (current, superseded, draft, archived).
- **F10 (P1)**: Chat history per user; follow-up questions rewrite into standalone queries.
- **F11 (P1)**: Admin dashboard: documents, versions, ingestion status, reindex, usage.
- **F12 (P1)**: PII redaction on typed questions before any LLM call.
- **F13 (P2)**: OCR for scanned PDFs.
- **F14 (P2)**: Feedback (helpful or not) on each answer.
- **F15 (P1)**: Evaluation runner that scores a gold question set.
