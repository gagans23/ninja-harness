"""
Judge plug-in interface for semantic comparison metrics.

A Judge compares a predicted answer against a reference answer and returns a
score in [0.0, 1.0] plus a details dict.

v0.2 ships two judges:
- DeterministicJudge: token-overlap (Jaccard + recall). No external calls.
  This is the default and keeps scoring fully reproducible.
- EmbeddingJudge: optional cosine similarity over sentence-transformer
  embeddings. Requires `pip install ninja-harness[semantic]`. Imports lazily
  and raises a clear error if the dependency is missing.

To plug in a real LLM-as-judge, implement the Judge protocol and pass your
instance to GoalSuccessScorer(judge=...). Ninja Harness does NOT ship a
built-in LLM API integration — you provide the model client. This keeps the
core library free of network calls and API keys.
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable


@runtime_checkable
class Judge(Protocol):
    """A comparator that scores a prediction against a reference."""

    name: str

    def compare(self, prediction: str, reference: str) -> tuple[float, dict]:
        """Return (score in [0,1], details dict)."""
        ...


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\b[a-z]{2,}\b", text.lower()))


class DeterministicJudge:
    """
    Default judge: blended Jaccard similarity and recall over word sets.

    score = 0.4 * jaccard + 0.6 * recall

    This reproduces the v0.1 Goal Success behavior exactly, so swapping it in
    as the default does not change existing scores.
    """

    name = "deterministic"

    def compare(self, prediction: str, reference: str) -> tuple[float, dict]:
        pred_tokens = _tokenize(prediction)
        ref_tokens = _tokenize(reference)

        if not ref_tokens:
            return 0.0, {"reason": "reference has no scoreable tokens"}

        intersection = pred_tokens & ref_tokens
        union = pred_tokens | ref_tokens
        jaccard = len(intersection) / len(union) if union else 0.0
        recall = len(intersection) / len(ref_tokens)
        blended = 0.4 * jaccard + 0.6 * recall

        return round(blended, 4), {
            "judge": self.name,
            "jaccard": round(jaccard, 4),
            "recall": round(recall, 4),
            "blended": round(blended, 4),
            "matching_tokens": len(intersection),
            "reference_token_count": len(ref_tokens),
            "prediction_token_count": len(pred_tokens),
        }


class EmbeddingJudge:
    """
    Optional judge: cosine similarity over sentence-transformer embeddings.

    Requires the optional dependency:  pip install ninja-harness[semantic]

    The model is loaded lazily on first use. If sentence-transformers is not
    installed, a clear ImportError is raised — there is no silent fallback and
    no network call beyond the model download performed by the library itself.
    """

    name = "embedding"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - exercised only without extra
            raise ImportError(
                "EmbeddingJudge requires sentence-transformers. "
                "Install it with: pip install ninja-harness[semantic]"
            ) from exc
        self._model = SentenceTransformer(self._model_name)

    def compare(self, prediction: str, reference: str) -> tuple[float, dict]:
        self._ensure_model()
        assert self._model is not None

        embeddings = self._model.encode([prediction, reference])
        pred_vec, ref_vec = embeddings[0], embeddings[1]

        # Cosine similarity without importing numpy directly
        dot = float(sum(a * b for a, b in zip(pred_vec, ref_vec)))
        pred_norm = float(sum(a * a for a in pred_vec)) ** 0.5
        ref_norm = float(sum(b * b for b in ref_vec)) ** 0.5
        denom = pred_norm * ref_norm
        cosine = dot / denom if denom > 0 else 0.0

        # Map cosine [-1, 1] to [0, 1]
        score = max(0.0, min(1.0, (cosine + 1.0) / 2.0))

        return round(score, 4), {
            "judge": self.name,
            "model": self._model_name,
            "cosine_similarity": round(cosine, 4),
        }
