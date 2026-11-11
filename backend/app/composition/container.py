"""
Dependency injection container wiring ports, adapters, and use cases.
"""
from typing import Optional
from app.application.ports import (
    ClockPort,
    LLMPort,
    PiiRedactorPort,
    FileStoragePort,
)
from app.adapters.llm.fake_llm import FakeLLM
from app.composition.settings import Settings, get_settings


class SystemClock(ClockPort):
    def now(self):
        from datetime import datetime
        return datetime.utcnow()


class Container:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.clock = SystemClock()
        self.fake_llm = FakeLLM()

    def get_llm(self) -> LLMPort:
        # Default to fake in Phase 0; actual adapters wired in Phase 5
        return self.fake_llm


_container_instance: Optional[Container] = None


def get_container() -> Container:
    global _container_instance
    if _container_instance is None:
        _container_instance = Container()
    return _container_instance

