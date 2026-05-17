"""
Fallback strategies for RAG retrieval when vector search quality is low.

This module implements a FallbackRetriever that tries semantic (vector) search first,
then falls back to keyword-based search if quality scores are below a threshold.
"""

import logging
from dataclasses import dataclass
from enum import Enum
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from fitness_assistant.rag.logging_config import RAGLogger


class RetrievalStrategy(str, Enum):
    """Enumeration of available retrieval strategies."""

    VECTOR = "vector"
    KEYWORD = "keyword"


@dataclass
class RetrievalResult:
    """Result from a retrieval operation."""

    points: list
    strategy_used: RetrievalStrategy
    quality_score: float
    clarifying_questions: list[str]


class FallbackRetriever:
    """
    A retriever that implements fallback strategies for RAG queries.

    Tries semantic (vector) search first, then falls back to keyword search
    if the quality score falls below a threshold. Can also generate clarifying
    questions when retrieval quality is low.
    """

    def __init__(
        self,
        vector_search_fn,
        documents: list[dict] | None = None,
        quality_threshold: float = 0.5,
        clarifying_threshold: float = 0.5,
        max_results: int = 5,
    ):
        """
        Initialize the FallbackRetriever.

        Args:
            vector_search_fn: Function that performs vector search (takes query and returns results)
            documents: Optional list of documents for keyword search indexing
            quality_threshold: Score below which fallback is triggered (0-1)
            clarifying_threshold: Score below which clarifying questions are generated (0-1)
            max_results: Maximum number of results to return
        """
        self.vector_search_fn = vector_search_fn
        self.documents = documents or []
        self.quality_threshold = quality_threshold
        self.clarifying_threshold = clarifying_threshold
        self.max_results = max_results
        self.logger = logging.getLogger(__name__)
        self._build_keyword_index()

    def _build_keyword_index(self):
        """Build TF-IDF index for keyword search."""
        if not self.documents:
            self.tfidf_vectorizer = None
            self.tfidf_matrix = None
            return

        try:
            doc_texts = [self._extract_document_text(doc) for doc in self.documents]

            if not doc_texts:
                self.tfidf_vectorizer = None
                self.tfidf_matrix = None
                return

            self.tfidf_vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                max_features=1000,
                analyzer="word",
                ngram_range=(1, 2),
            )
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(doc_texts)
            self.logger.info(
                f"Built TF-IDF keyword index for {len(doc_texts)} documents"
            )
        except Exception as e:
            self.logger.warning(f"Failed to build keyword index: {e}")
            self.tfidf_vectorizer = None
            self.tfidf_matrix = None

    @staticmethod
    def _extract_document_text(doc: dict) -> str:
        """Extract searchable text from a document."""
        parts = []

        key_fields = [
            "exercise_name",
            "muscle_groups_activated",
            "body_part",
            "instructions",
        ]

        for field in key_fields:
            if field in doc and doc[field]:
                parts.append(str(doc[field]).lower())

        return " ".join(parts)

    def retrieve_with_fallback(self, query: str, trace_id: str = "") -> RetrievalResult:
        """
        Retrieve documents using vector search, with keyword fallback if needed.

        First attempts semantic search via vector_search_fn. If the quality score
        is below the threshold, attempts keyword-based BM25-style search as fallback.

        Args:
            query: User's search query
            trace_id: Optional trace ID for logging

        Returns:
            RetrievalResult containing points, strategy used, quality score, and
            any clarifying questions if needed
        """
        if not trace_id:
            import uuid

            trace_id = str(uuid.uuid4())

        rag_logger = RAGLogger(trace_id)

        try:
            results = self.vector_search_fn(query, trace_id=trace_id)

            points = results.points if hasattr(results, "points") else results
            quality_score = self.calculate_quality_score(points)

            self.logger.info(
                f"Vector search returned {len(points) if points else 0} results "
                f"with quality score: {quality_score:.3f}"
            )

            clarifying_questions = []
            strategy = RetrievalStrategy.VECTOR

            if quality_score < self.quality_threshold:
                self.logger.info(
                    f"Quality score {quality_score:.3f} below threshold "
                    f"{self.quality_threshold}. Attempting keyword fallback."
                )

                keyword_points = self._keyword_search(query)
                keyword_quality = self.calculate_quality_score(keyword_points)

                self.logger.info(
                    f"Keyword search returned {len(keyword_points)} results "
                    f"with quality score: {keyword_quality:.3f}"
                )

                if keyword_quality > quality_score:
                    points = keyword_points
                    quality_score = keyword_quality
                    strategy = RetrievalStrategy.KEYWORD

            if quality_score < self.clarifying_threshold:
                clarifying_questions = self.generate_clarifying_questions(query)
                self.logger.info(
                    f"Generated {len(clarifying_questions)} clarifying questions"
                )

            rag_logger.logger.info(
                f"Retrieval strategy used: {strategy.value}, "
                f"quality_score: {quality_score:.3f}, "
                f"results: {len(points) if points else 0}"
            )

            return RetrievalResult(
                points=points or [],
                strategy_used=strategy,
                quality_score=quality_score,
                clarifying_questions=clarifying_questions,
            )

        except Exception as e:
            self.logger.error(f"Error in fallback retrieval: {e}")
            rag_logger.log_error(e, "Fallback retrieval")
            raise

    def calculate_quality_score(self, results: list) -> float:
        """
        Calculate a quality score for retrieval results (0-1).

        Scores based on:
        - Number of results (more is better, up to a limit)
        - Similarity scores (higher average score is better)
        - Result diversity

        Args:
            results: List of retrieved results/points

        Returns:
            Quality score between 0 and 1
        """
        if not results:
            return 0.0

        try:
            scores_sum = 0.0
            valid_scores = 0

            for point in results:
                if hasattr(point, "score"):
                    score = float(point.score)
                    scores_sum += score
                    valid_scores += 1

            # If no valid scores were found, return 0.0
            if valid_scores == 0:
                return 0.0

            num_results = len(results)

            avg_score = scores_sum / valid_scores if valid_scores > 0 else 0.0

            result_count_factor = min(num_results / self.max_results, 1.0)

            quality_score = (avg_score * 0.7) + (result_count_factor * 0.3)

            quality_score = max(0.0, min(1.0, quality_score))

            return quality_score

        except (AttributeError, ValueError, TypeError):
            self.logger.warning("Could not calculate quality score from results")
            return 0.0

    def _keyword_search(self, query: str) -> list:
        """
        Perform keyword-based search using TF-IDF.

        Args:
            query: Search query

        Returns:
            List of matching documents as point-like objects
        """
        if not self.tfidf_vectorizer or self.tfidf_matrix is None:
            self.logger.warning("TF-IDF index not available for keyword search")
            return []

        try:
            query_vector = self.tfidf_vectorizer.transform([query.lower()])

            similarities = cosine_similarity(query_vector, self.tfidf_matrix)[0]

            top_indices = np.argsort(similarities)[::-1][: self.max_results]

            keyword_results = []
            for idx in top_indices:
                if similarities[idx] > 0:
                    result = KeywordPoint(
                        id=idx,
                        payload=self.documents[idx],
                        score=float(similarities[idx]),
                    )
                    keyword_results.append(result)

            return keyword_results

        except Exception as e:
            self.logger.error(f"Keyword search failed: {e}")
            return []

    def generate_clarifying_questions(self, query: str) -> list[str]:
        """
        Generate clarifying questions when retrieval quality is low.

        Suggests follow-up questions to help the user refine their query
        and improve retrieval results.

        Args:
            query: The original user query

        Returns:
            List of clarifying questions (2-4 questions)
        """
        questions = []

        query_lower = query.lower()

        if "exercise" in query_lower or "workout" in query_lower:
            if "weight" not in query_lower and "cardio" not in query_lower:
                questions.append(
                    "Are you looking for a specific type of exercise "
                    "(e.g., strength training, cardio, flexibility)?"
                )
            if "body" not in query_lower:
                questions.append(
                    "Which body parts or muscle groups are you interested in targeting?"
                )
            if "level" not in query_lower and "beginner" not in query_lower:
                questions.append(
                    "What is your fitness level (beginner, intermediate, or advanced)?"
                )
        else:
            questions.append(
                "Could you clarify what type of fitness advice you're seeking?"
            )
            questions.append(
                "Are you looking for exercise recommendations, form tips, or training programs?"
            )

        if "equipment" not in query_lower and "home" not in query_lower:
            questions.append(
                "Do you have access to specific equipment (dumbbells, barbell, machines)?"
            )

        return questions[:4]


class KeywordPoint:
    """A point-like object for keyword search results."""

    def __init__(self, id: int, payload: dict, score: float):
        """
        Initialize a keyword search result point.

        Args:
            id: Document ID
            payload: Document data
            score: Similarity score (0-1)
        """
        self.id = id
        self.payload = payload
        self.score = score
