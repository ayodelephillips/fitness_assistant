"""
Monitoring module for RAG pipeline.
Tracks metrics, detects hallucinations, and monitors system health.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass
import logging
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RetrievalMetrics:
    """Metrics for a retrieval operation."""

    num_results: int
    scores: List[float]
    response_time_ms: float
    top_score: float


@dataclass
class GenerationMetrics:
    """Metrics for an LLM generation operation."""

    response_time_ms: float
    token_count: Optional[int] = None
    model_name: Optional[str] = None


@dataclass
class HallucinationResult:
    """Result of hallucination detection."""

    score: float
    is_hallucinating: bool
    threshold: float
    reasoning: str


class RAGMetricsCollector:
    """Collects and tracks RAG pipeline metrics."""

    def __init__(self, window_size_minutes: int = 60):
        """
        Initialize metrics collector.

        Args:
            window_size_minutes: Time window for metrics aggregation
        """
        self.window_size = timedelta(minutes=window_size_minutes)
        self.retrieval_metrics: List[RetrievalMetrics] = []
        self.generation_metrics: List[GenerationMetrics] = []
        self.hallucination_scores: List[float] = []
        self.query_count = 0
        self.error_count = 0
        self.last_error: Optional[str] = None

    def record_retrieval(self, metrics: RetrievalMetrics) -> None:
        """Record retrieval metrics."""
        self.retrieval_metrics.append(metrics)
        self._cleanup_old_entries()

    def record_generation(self, metrics: GenerationMetrics) -> None:
        """Record generation metrics."""
        self.generation_metrics.append(metrics)
        self._cleanup_old_entries()

    def record_hallucination(self, score: float) -> None:
        """Record hallucination score."""
        self.hallucination_scores.append(score)
        self._cleanup_old_entries()

    def record_query(self) -> None:
        """Increment query count."""
        self.query_count += 1

    def record_error(self, error_msg: str) -> None:
        """Record an error."""
        self.error_count += 1
        self.last_error = error_msg

    def _cleanup_old_entries(self) -> None:
        """Remove entries older than window_size."""
        cutoff_time = datetime.now() - self.window_size

        # Note: In a real implementation, add timestamps to track entries
        # For now, keep last 1000 entries
        if len(self.retrieval_metrics) > 1000:
            self.retrieval_metrics = self.retrieval_metrics[-1000:]
        if len(self.generation_metrics) > 1000:
            self.generation_metrics = self.generation_metrics[-1000:]
        if len(self.hallucination_scores) > 1000:
            self.hallucination_scores = self.hallucination_scores[-1000:]

    def get_retrieval_stats(self) -> Dict:
        """Get aggregated retrieval statistics."""
        if not self.retrieval_metrics:
            return {"status": "no_data"}

        response_times = [m.response_time_ms for m in self.retrieval_metrics]
        top_scores = [m.top_score for m in self.retrieval_metrics]

        return {
            "avg_response_time_ms": np.mean(response_times),
            "p95_response_time_ms": np.percentile(response_times, 95),
            "p99_response_time_ms": np.percentile(response_times, 99),
            "avg_top_score": np.mean(top_scores),
            "min_top_score": np.min(top_scores),
            "total_retrievals": len(self.retrieval_metrics),
        }

    def get_generation_stats(self) -> Dict:
        """Get aggregated generation statistics."""
        if not self.generation_metrics:
            return {"status": "no_data"}

        response_times = [m.response_time_ms for m in self.generation_metrics]

        return {
            "avg_response_time_ms": np.mean(response_times),
            "p95_response_time_ms": np.percentile(response_times, 95),
            "p99_response_time_ms": np.percentile(response_times, 99),
            "total_generations": len(self.generation_metrics),
        }

    def get_hallucination_stats(self) -> Dict:
        """Get hallucination statistics."""
        if not self.hallucination_scores:
            return {"status": "no_data"}

        scores = self.hallucination_scores
        hallucinating = sum(1 for s in scores if s > 0.5)  # threshold 0.5

        return {
            "avg_hallucination_score": np.mean(scores),
            "max_hallucination_score": np.max(scores),
            "hallucinating_count": hallucinating,
            "hallucination_rate": hallucinating / len(scores),
            "total_checks": len(scores),
        }

    def get_health_status(self) -> Dict:
        """Get overall health status."""
        return {
            "total_queries": self.query_count,
            "total_errors": self.error_count,
            "error_rate": (
                self.error_count / self.query_count if self.query_count > 0 else 0
            ),
            "last_error": self.last_error,
            "retrieval_stats": self.get_retrieval_stats(),
            "generation_stats": self.get_generation_stats(),
            "hallucination_stats": self.get_hallucination_stats(),
        }


class HallucinationDetector:
    """Detects hallucinations in LLM responses by comparing against context."""

    def __init__(self, threshold: float = 0.5):
        """
        Initialize hallucination detector.

        Args:
            threshold: Score threshold above which to flag as hallucination (0-1)
        """
        self.threshold = threshold

    def detect(
        self, response: str, context: str, context_embeddings: Optional[np.ndarray] = None
    ) -> HallucinationResult:
        """
        Detect hallucinations in response vs context.

        Args:
            response: LLM response text
            context: Retrieved context from vector DB
            context_embeddings: Pre-computed embeddings (optional)

        Returns:
            HallucinationResult with score and detection result
        """
        # Simple heuristic: check if response mostly contains information from context
        # In production, use embedding-based similarity or LLM-based checking

        response_words = set(response.lower().split())
        context_words = set(context.lower().split())

        # Calculate word overlap
        overlap = len(response_words & context_words) / len(response_words)
        hallucination_score = 1 - overlap  # Higher = more hallucination

        # More sophisticated check: look for claims not in context
        # Flag certain indicators of hallucination
        hallucination_phrases = [
            "i don't have information",
            "i'm not sure",
            "this is based on",
            "in my experience",
            "i believe",
        ]

        for phrase in hallucination_phrases:
            if phrase.lower() in response.lower():
                hallucination_score = min(1.0, hallucination_score + 0.1)

        is_hallucinating = hallucination_score > self.threshold

        reasoning = (
            f"Response overlap with context: {overlap:.2%}. "
            f"Words in response not in context: {1-overlap:.2%}"
        )

        return HallucinationResult(
            score=hallucination_score,
            is_hallucinating=is_hallucinating,
            threshold=self.threshold,
            reasoning=reasoning,
        )


class QueryRateLimiter:
    """Implements rate limiting for queries."""

    def __init__(
        self,
        max_per_minute: int = 60,
        max_per_hour: int = 1000,
        max_daily: int = 10000,
    ):
        """
        Initialize rate limiter.

        Args:
            max_per_minute: Max queries per minute
            max_per_hour: Max queries per hour
            max_daily: Max queries per day
        """
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.max_daily = max_daily

        # Track queries by user/IP (in production, use Redis)
        self.query_times: Dict[str, List[datetime]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> Tuple[bool, str]:
        """
        Check if a query is allowed for the given client.

        Args:
            client_id: Unique client identifier (user_id, IP, etc.)

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        now = datetime.now()
        client_queries = self.query_times[client_id]

        # Clean up old queries
        one_day_ago = now - timedelta(days=1)
        self.query_times[client_id] = [
            q for q in client_queries if q > one_day_ago
        ]

        # Check daily limit
        if len(self.query_times[client_id]) >= self.max_daily:
            return False, "Daily query limit exceeded"

        # Check hourly limit
        one_hour_ago = now - timedelta(hours=1)
        queries_in_hour = sum(
            1 for q in self.query_times[client_id] if q > one_hour_ago
        )
        if queries_in_hour >= self.max_per_hour:
            return False, "Hourly query limit exceeded"

        # Check per-minute limit
        one_minute_ago = now - timedelta(minutes=1)
        queries_in_minute = sum(
            1 for q in self.query_times[client_id] if q > one_minute_ago
        )
        if queries_in_minute >= self.max_per_minute:
            return False, "Per-minute query limit exceeded"

        # Record this query
        self.query_times[client_id].append(now)
        return True, "Query allowed"


# Global metrics collector
_metrics_collector = RAGMetricsCollector()


def get_metrics_collector() -> RAGMetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector
