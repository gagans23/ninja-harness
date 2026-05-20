"""Abstract base class for trace adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ninja_harness.schemas import AgentRun


class TraceAdapter(ABC):
    """
    Contract for converting a raw trace dict into a Ninja Harness AgentRun.

    To add support for a new framework:
    1. Subclass TraceAdapter.
    2. Implement can_parse() to detect the trace format.
    3. Implement parse() to map native fields to AgentRun.
    4. Register the adapter in adapters/__init__.py ADAPTER_REGISTRY.
    """

    @abstractmethod
    def can_parse(self, raw: dict) -> bool:
        """Return True if this adapter knows how to parse *raw*."""

    @abstractmethod
    def parse(self, raw: dict) -> AgentRun:
        """
        Convert *raw* into an AgentRun.

        Raise ValueError with a clear message if required fields are missing.
        """

    @property
    def adapter_name(self) -> str:
        return self.__class__.__name__
