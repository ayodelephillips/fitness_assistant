"""
Comprehensive tests for fallback retrieval strategies.

Tests cover vector retrieval, keyword fallback, quality scoring, clarifying questions,
and integration with the RAG pipeline.
"""

import pytest
from unittest.mock import Mock
from fitness_assistant.rag.fallback_strategies import (
    FallbackRetriever,
    RetrievalStrategy,
    RetrievalResult,
    KeywordPoint,
)


@pytest.fixture
def sample_documents():
    """Fixture providing sample exercise documents."""
    return [
        {
            "exercise_name": "dumbbell squat",
            "body_part": "legs",
            "muscle_groups_activated": "quadriceps, glutes, hamstrings",
            "instructions": "hold dumbbells at shoulder height and squat down",
        },
        {
            "exercise_name": "push up",
            "body_part": "chest",
            "muscle_groups_activated": "chest, shoulders, triceps",
            "instructions": "place hands on ground and push body up",
        },
        {
            "exercise_name": "barbell squat",
            "body_part": "legs",
            "muscle_groups_activated": "quadriceps, glutes, hamstrings, lower back",
            "instructions": "place barbell on shoulders and squat down",
        },
        {
            "exercise_name": "lat pulldown",
            "body_part": "back",
            "muscle_groups_activated": "latissimus dorsi, shoulders",
            "instructions": "pull bar down to chest height",
        },
        {
            "exercise_name": "bench press",
            "body_part": "chest",
            "muscle_groups_activated": "chest, shoulders, triceps",
            "instructions": "press barbell up from chest level",
        },
    ]


@pytest.fixture
def mock_vector_search_fn():
    """Fixture providing a mock vector search function."""

    def search(query, trace_id=""):
        mock_result = Mock()
        mock_result.points = []
        return mock_result

    return search


@pytest.fixture
def fallback_retriever(mock_vector_search_fn, sample_documents):
    """Fixture providing a FallbackRetriever instance."""
    return FallbackRetriever(
        vector_search_fn=mock_vector_search_fn,
        documents=sample_documents,
        quality_threshold=0.5,
        clarifying_threshold=0.5,
        max_results=5,
    )


class TestFallbackRetrieverInitialization:
    """Tests for FallbackRetriever initialization."""

    def test_initialization_with_defaults(self, mock_vector_search_fn):
        """Test creating retriever with default parameters."""
        retriever = FallbackRetriever(vector_search_fn=mock_vector_search_fn)
        assert retriever.quality_threshold == 0.5
        assert retriever.clarifying_threshold == 0.5
        assert retriever.max_results == 5
        assert retriever.documents == []

    def test_initialization_with_custom_thresholds(
        self, mock_vector_search_fn, sample_documents
    ):
        """Test creating retriever with custom thresholds."""
        retriever = FallbackRetriever(
            vector_search_fn=mock_vector_search_fn,
            documents=sample_documents,
            quality_threshold=0.6,
            clarifying_threshold=0.7,
            max_results=10,
        )
        assert retriever.quality_threshold == 0.6
        assert retriever.clarifying_threshold == 0.7
        assert retriever.max_results == 10

    def test_keyword_index_built_with_documents(
        self, mock_vector_search_fn, sample_documents
    ):
        """Test that keyword index is built when documents are provided."""
        retriever = FallbackRetriever(
            vector_search_fn=mock_vector_search_fn,
            documents=sample_documents,
        )
        assert retriever.tfidf_vectorizer is not None
        assert retriever.tfidf_matrix is not None

    def test_no_keyword_index_without_documents(self, mock_vector_search_fn):
        """Test that keyword index is not built without documents."""
        retriever = FallbackRetriever(vector_search_fn=mock_vector_search_fn)
        assert retriever.tfidf_vectorizer is None
        assert retriever.tfidf_matrix is None


class TestVectorRetrieval:
    """Tests for vector-based retrieval."""

    def test_vector_retrieval_success(self, fallback_retriever):
        """Test successful vector retrieval with high-quality results."""
        mock_point = Mock()
        mock_point.score = 0.9
        mock_point.payload = {"exercise_name": "squat"}

        def mock_search(query, trace_id=""):
            result = Mock()
            result.points = [mock_point]
            return result

        fallback_retriever.vector_search_fn = mock_search

        result = fallback_retriever.retrieve_with_fallback("leg exercises")

        assert result.strategy_used == RetrievalStrategy.VECTOR
        assert len(result.points) == 1
        assert result.quality_score > 0.5

    def test_vector_retrieval_empty_results(self, fallback_retriever):
        """Test vector retrieval returning no results."""

        def mock_search(query, trace_id=""):
            result = Mock()
            result.points = []
            return result

        fallback_retriever.vector_search_fn = mock_search

        result = fallback_retriever.retrieve_with_fallback("obscure exercise")

        assert len(result.points) == 0
        assert result.quality_score == 0.0

    def test_vector_retrieval_multiple_results(self, fallback_retriever):
        """Test vector retrieval with multiple results."""
        points = []
        for i in range(3):
            mock_point = Mock()
            mock_point.score = 0.8 - (i * 0.1)
            mock_point.payload = {"exercise_name": f"exercise_{i}"}
            points.append(mock_point)

        def mock_search(query, trace_id=""):
            result = Mock()
            result.points = points
            return result

        fallback_retriever.vector_search_fn = mock_search

        result = fallback_retriever.retrieve_with_fallback("exercises")

        assert len(result.points) == 3
        assert result.quality_score > 0.0


class TestKeywordFallback:
    """Tests for keyword-based fallback search."""

    def test_keyword_fallback_triggered(self, fallback_retriever):
        """Test that keyword fallback is triggered when vector score is low."""
        mock_point = Mock()
        mock_point.score = 0.2  # Low score triggers fallback

        def mock_search(query, trace_id=""):
            result = Mock()
            result.points = [mock_point]
            return result

        fallback_retriever.vector_search_fn = mock_search

        result = fallback_retriever.retrieve_with_fallback("squat")

        assert result.strategy_used == RetrievalStrategy.KEYWORD
        assert len(result.points) > 0

    def test_keyword_search_finds_relevant_documents(self, fallback_retriever):
        """Test that keyword search can find relevant documents."""
        keyword_results = fallback_retriever._keyword_search("squat")

        assert len(keyword_results) > 0
        exercise_names = [r.payload["exercise_name"] for r in keyword_results]
        assert any("squat" in name for name in exercise_names)

    def test_keyword_search_with_specific_muscle_group(self, fallback_retriever):
        """Test keyword search for specific muscle groups."""
        keyword_results = fallback_retriever._keyword_search("chest exercises")

        assert len(keyword_results) > 0
        muscle_groups = " ".join(
            [
                r.payload.get("muscle_groups_activated", "").lower()
                for r in keyword_results
            ]
        )
        assert "chest" in muscle_groups

    def test_keyword_search_empty_when_no_index(self, mock_vector_search_fn):
        """Test that keyword search returns empty when index not built."""
        retriever = FallbackRetriever(vector_search_fn=mock_vector_search_fn)

        keyword_results = retriever._keyword_search("squat")

        assert keyword_results == []

    def test_keyword_fallback_not_triggered_when_vector_is_good(
        self, fallback_retriever
    ):
        """Test that fallback is not triggered when vector score is high."""
        mock_point = Mock()
        mock_point.score = 0.95  # High score, no fallback needed

        def mock_search(query, trace_id=""):
            result = Mock()
            result.points = [mock_point]
            return result

        fallback_retriever.vector_search_fn = mock_search

        result = fallback_retriever.retrieve_with_fallback("squat")

        assert result.strategy_used == RetrievalStrategy.VECTOR


class TestQualityScoring:
    """Tests for quality score calculation."""

    def test_quality_score_empty_results(self, fallback_retriever):
        """Test quality score for empty results."""
        score = fallback_retriever.calculate_quality_score([])
        assert score == 0.0

    def test_quality_score_single_high_score_result(self, fallback_retriever):
        """Test quality score with single high-scoring result."""
        mock_point = Mock()
        mock_point.score = 0.9

        score = fallback_retriever.calculate_quality_score([mock_point])

        assert 0.6 <= score <= 1.0

    def test_quality_score_multiple_results(self, fallback_retriever):
        """Test quality score with multiple results."""
        points = []
        for i in range(3):
            mock_point = Mock()
            mock_point.score = 0.8 - (i * 0.1)
            points.append(mock_point)

        score = fallback_retriever.calculate_quality_score(points)

        assert 0.5 <= score <= 1.0

    def test_quality_score_low_scoring_results(self, fallback_retriever):
        """Test quality score with low-scoring results."""
        mock_point = Mock()
        mock_point.score = 0.1

        score = fallback_retriever.calculate_quality_score([mock_point])

        assert score < 0.3

    def test_quality_score_result_count_factor(self, fallback_retriever):
        """Test that quality score considers number of results."""
        points_one = [Mock(score=0.8)]
        points_many = [Mock(score=0.8) for _ in range(5)]

        score_one = fallback_retriever.calculate_quality_score(points_one)
        score_many = fallback_retriever.calculate_quality_score(points_many)

        assert score_many > score_one

    def test_quality_score_result_without_score_attribute(self, fallback_retriever):
        """Test quality score calculation with results missing score attribute."""
        mock_point = Mock(spec=[])

        score = fallback_retriever.calculate_quality_score([mock_point])

        assert score == 0.0

    def test_quality_score_bounds(self, fallback_retriever):
        """Test that quality score is always between 0 and 1."""
        mock_point = Mock()
        mock_point.score = 2.0  # Invalid high score

        score = fallback_retriever.calculate_quality_score([mock_point])

        assert 0.0 <= score <= 1.0


class TestClarifyingQuestions:
    """Tests for clarifying question generation."""

    def test_clarifying_questions_for_exercise_query(self, fallback_retriever):
        """Test clarifying questions for exercise-related queries."""
        questions = fallback_retriever.generate_clarifying_questions(
            "What exercises can I do?"
        )

        assert len(questions) > 0
        assert len(questions) <= 4
        assert all(isinstance(q, str) for q in questions)

    def test_clarifying_questions_for_specific_body_part(self, fallback_retriever):
        """Test clarifying questions for body-part queries."""
        questions = fallback_retriever.generate_clarifying_questions("leg exercises")

        assert len(questions) > 0
        combined = " ".join(questions).lower()
        assert "fitness level" in combined or "equipment" in combined

    def test_clarifying_questions_non_exercise_query(self, fallback_retriever):
        """Test clarifying questions for non-exercise queries."""
        questions = fallback_retriever.generate_clarifying_questions(
            "general fitness advice"
        )

        assert len(questions) > 0
        assert any("clarify" in q.lower() or "seeking" in q.lower() for q in questions)

    def test_clarifying_questions_with_equipment(self, fallback_retriever):
        """Test that equipment questions are included when relevant."""
        questions = fallback_retriever.generate_clarifying_questions(
            "exercises for legs"
        )

        assert len(questions) > 0
        assert any("equipment" in q.lower() for q in questions)

    def test_clarifying_questions_max_count(self, fallback_retriever):
        """Test that clarifying questions don't exceed maximum count."""
        questions = fallback_retriever.generate_clarifying_questions(
            "exercise advice please"
        )

        assert len(questions) <= 4

    def test_clarifying_questions_are_unique(self, fallback_retriever):
        """Test that clarifying questions are unique."""
        questions = fallback_retriever.generate_clarifying_questions("exercises")

        assert len(questions) == len(set(questions))


class TestRetrieveWithFallback:
    """Integration tests for the retrieve_with_fallback method."""

    def test_retrieve_with_fallback_triggers_fallback(self, fallback_retriever):
        """Test that fallback is triggered when vector score is low."""
        mock_point = Mock()
        mock_point.score = 0.3  # Below threshold

        def mock_search(query, trace_id=""):
            result = Mock()
            result.points = [mock_point]
            return result

        fallback_retriever.vector_search_fn = mock_search

        result = fallback_retriever.retrieve_with_fallback("squat")

        assert result.strategy_used == RetrievalStrategy.KEYWORD
        assert isinstance(result, RetrievalResult)

    def test_retrieve_with_fallback_uses_vector_when_good(self, fallback_retriever):
        """Test that vector strategy is used when score is high."""
        mock_point = Mock()
        mock_point.score = 0.95
        mock_point.payload = {"exercise_name": "squat"}

        def mock_search(query, trace_id=""):
            result = Mock()
            result.points = [mock_point]
            return result

        fallback_retriever.vector_search_fn = mock_search

        result = fallback_retriever.retrieve_with_fallback("squat")

        assert result.strategy_used == RetrievalStrategy.VECTOR
        assert result.quality_score > 0.7

    def test_retrieve_with_fallback_generates_clarifying_questions(
        self, fallback_retriever
    ):
        """Test that clarifying questions are generated when quality is low."""
        mock_point = Mock()
        mock_point.score = 0.2

        def mock_search(query, trace_id=""):
            result = Mock()
            result.points = [mock_point]
            return result

        fallback_retriever.vector_search_fn = mock_search

        result = fallback_retriever.retrieve_with_fallback("help")

        if result.quality_score < fallback_retriever.clarifying_threshold:
            assert len(result.clarifying_questions) > 0

    def test_retrieve_with_fallback_no_clarifying_questions_when_quality_good(
        self, fallback_retriever
    ):
        """Test that clarifying questions are not generated when quality is good."""
        mock_point = Mock()
        mock_point.score = 0.95

        def mock_search(query, trace_id=""):
            result = Mock()
            result.points = [mock_point]
            return result

        fallback_retriever.vector_search_fn = mock_search

        result = fallback_retriever.retrieve_with_fallback("squat")

        assert result.quality_score >= fallback_retriever.clarifying_threshold
        assert len(result.clarifying_questions) == 0

    def test_retrieve_with_fallback_handles_trace_id(self, fallback_retriever):
        """Test that trace_id is properly handled."""

        def mock_search(query, trace_id=""):
            result = Mock()
            result.points = []
            return result

        fallback_retriever.vector_search_fn = mock_search

        result = fallback_retriever.retrieve_with_fallback("query", trace_id="test-123")

        assert result.points == []

    def test_retrieve_with_fallback_handles_exception(self, fallback_retriever):
        """Test that exceptions in vector search are handled."""

        def mock_search_error(query, trace_id=""):
            raise Exception("Search failed")

        fallback_retriever.vector_search_fn = mock_search_error

        with pytest.raises(Exception):
            fallback_retriever.retrieve_with_fallback("query")


class TestKeywordPoint:
    """Tests for KeywordPoint helper class."""

    def test_keyword_point_creation(self):
        """Test creating a KeywordPoint."""
        payload = {"exercise_name": "squat"}
        point = KeywordPoint(id=0, payload=payload, score=0.85)

        assert point.id == 0
        assert point.payload == payload
        assert point.score == 0.85

    def test_keyword_point_attributes(self):
        """Test KeywordPoint has required attributes."""
        point = KeywordPoint(id=1, payload={}, score=0.5)

        assert hasattr(point, "id")
        assert hasattr(point, "payload")
        assert hasattr(point, "score")


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_extract_document_text_with_missing_fields(self, fallback_retriever):
        """Test extracting text from documents with missing fields."""
        doc = {"exercise_name": "squat"}
        text = FallbackRetriever._extract_document_text(doc)

        assert "squat" in text

    def test_extract_document_text_with_all_fields(self, fallback_retriever):
        """Test extracting text from complete documents."""
        doc = {
            "exercise_name": "squat",
            "body_part": "legs",
            "muscle_groups_activated": "quads",
            "instructions": "bend knees",
        }
        text = FallbackRetriever._extract_document_text(doc)

        assert "squat" in text.lower()
        assert "legs" in text.lower()

    def test_retrieve_with_fallback_empty_query(self, fallback_retriever):
        """Test retrieve with empty query."""

        def mock_search(query, trace_id=""):
            result = Mock()
            result.points = []
            return result

        fallback_retriever.vector_search_fn = mock_search

        result = fallback_retriever.retrieve_with_fallback("")

        assert isinstance(result, RetrievalResult)

    def test_quality_score_with_invalid_scores(self, fallback_retriever):
        """Test quality score calculation with non-numeric scores."""
        mock_point = Mock()
        mock_point.score = "invalid"

        score = fallback_retriever.calculate_quality_score([mock_point])

        assert score == 0.0

    def test_fallback_retriever_with_empty_documents(self, mock_vector_search_fn):
        """Test FallbackRetriever initialized with empty documents list."""
        retriever = FallbackRetriever(
            vector_search_fn=mock_vector_search_fn,
            documents=[],
        )

        assert retriever.tfidf_vectorizer is None
        assert retriever.tfidf_matrix is None
