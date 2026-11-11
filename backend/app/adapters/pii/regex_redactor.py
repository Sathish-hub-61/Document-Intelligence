"""
PII Regex Redactor for user queries.
Removes registration numbers, roll numbers, emails, and telephone numbers
before questions are sent to external LLM providers or logged.
"""
import re
from app.application.ports import PiiRedactorPort


class RegexPiiRedactor(PiiRedactorPort):
    def __init__(self):
        # Email pattern
        self.email_pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )
        # Phone numbers: Indian (+91), US (+1), or standard 10-digit formats with dashes/spaces
        self.phone_pattern = re.compile(
            r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"
        )
        # University registration / roll numbers / USNs (e.g. 2024BCSE001, 1MS21CS042, RA2111003010123)
        self.reg_pattern = re.compile(
            r"\b([0-9]{4}[A-Za-z]{2,4}[0-9]{3,4}|[1-9][A-Za-z]{2}[0-9]{2}[A-Za-z]{2}[0-9]{3}|[A-Za-z]{2}[0-9]{11})\b",
            re.IGNORECASE,
        )

    def redact(self, text: str) -> str:
        if not text:
            return ""

        redacted = self.email_pattern.sub("[EMAIL]", text)
        redacted = self.reg_pattern.sub("[REG_NO]", redacted)
        redacted = self.phone_pattern.sub("[PHONE]", redacted)

        return redacted

