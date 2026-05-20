"""Abstract base class for all Ninja Harness scorers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ninja_harness.schemas import AgentRun, EvaluationCase, MetricResult


class BaseScorer(ABC):
    """Contract every metric scorer must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable metric name."""

    @abstractmethod
    def score(
        self,
        run: AgentRun,
        case: Optional[EvaluationCase] = None,
    ) -> MetricResult:
        """
        Evaluate the metric against *run* (and optionally *case*).

        Returns a MetricResult with score in [0.0, 1.0], or score=-1.0 when
        the metric is not applicable (e.g. no expected output provided).
        """

    def _not_applicable(self, reason: str) -> MetricResult:
        return MetricResult(
            name=self.name,
            score=-1.0,
            passed=True,  # not applicable is neutral, not a failure
            details={"reason": reason},
        )
