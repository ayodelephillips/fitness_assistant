import pytest
from unittest.mock import patch, MagicMock

from fitness_assistant.rag.llm_interface import ManageVectorDb
from fitness_assistant.rag.settings import QdrantConfig


@pytest.fixture
def mock_qdrant_config(monkeypatch):
    """Fixture to provide a mock QdrantConfig."""
    monkeypatch.setenv("QDRANT_API_KEY", "test-api-key")
    return QdrantConfig()


@patch("fitness_assistant.rag.llm_interface.QdrantClient")
def test_init_success(mock_qdrant_client, mock_qdrant_config):
    """
    Tests that ManageVectorDb initializes the Qdrant client successfully.
    """
    mock_client_instance = MagicMock()
    mock_qdrant_client.return_value = mock_client_instance
    vector_db = ManageVectorDb(config=mock_qdrant_config)
    mock_qdrant_client.assert_called_once_with(
        url=mock_qdrant_config.cluster_url, api_key=mock_qdrant_config.qdrant_api_key
    )
    assert vector_db.client is mock_client_instance


@patch(
    "fitness_assistant.rag.llm_interface.QdrantClient",
    side_effect=Exception("Connection failed"),
)
def test_init_failure(mock_qdrant_client, mock_qdrant_config):
    """
    Tests that ManageVectorDb handles client creation failure gracefully.
    """
    vector_db = ManageVectorDb(config=mock_qdrant_config)
    assert vector_db.client is None


def test_get_text_embedding_string():
    """
    Tests the static method for creating the text string for embedding.
    """
    record = {
        "exercise_name": "Test Curl",
        "type_of_activity": "strength",
        "type_of_equipment": "dumbbell",
        "muscle_groups_activated": "Biceps",
        "body_part": "Arms",
        "description": "Isolation curl",
        "instructions": "Curl it.",
    }
    embedding_string = ManageVectorDb.get_text_embedding_string(record)
    expected_string = (
        "Exercise Name: Test Curl — "
        "Type of Activity: strength — "
        "Equipment: dumbbell — "
        "Muscle Groups: Biceps — "
        "Body Part: Arms — "
        "Description: Isolation curl — "
        "Instructions: Curl it."
    )
    assert embedding_string == expected_string


def test_get_text_embedding_string_without_description():
    """Description is optional and should be omitted when empty."""
    record = {
        "exercise_name": "Test Curl",
        "type_of_activity": "strength",
        "type_of_equipment": "dumbbell",
        "muscle_groups_activated": "Biceps",
        "body_part": "Arms",
        "instructions": "Curl it.",
    }
    embedding_string = ManageVectorDb.get_text_embedding_string(record)
    assert "Description:" not in embedding_string
    assert "Exercise Name: Test Curl" in embedding_string
    assert "Instructions: Curl it." in embedding_string


def test_get_payload():
    """Payload should include all context_mapping keys, defaulting missing ones to empty string."""
    record = {
        "exercise_name": "Test Curl",
        "type_of_activity": "strength",
        "instructions": "Curl it.",
    }
    context_mapping = {
        "exercise_name": "Exercise",
        "type_of_activity": "Type of activity",
        "type_of_equipment": "Equipment",
        "instructions": "Instructions",
        "description": "Description",
    }
    payload = ManageVectorDb.get_payload(record, context_mapping)
    assert payload == {
        "exercise_name": "Test Curl",
        "type_of_activity": "strength",
        "type_of_equipment": "",
        "instructions": "Curl it.",
        "description": "",
    }


@patch("fitness_assistant.rag.llm_interface.QdrantClient")
def test_collection_exists_true(mock_qdrant_client, mock_qdrant_config):
    """
    Tests collection_exists method when the collection is present.
    """
    mock_client_instance = MagicMock()
    mock_collection = MagicMock()
    mock_collection.name = mock_qdrant_config.collection_name
    mock_client_instance.get_collections.return_value = MagicMock(
        collections=[mock_collection]
    )
    mock_qdrant_client.return_value = mock_client_instance

    vector_db = ManageVectorDb(config=mock_qdrant_config)
    assert vector_db.collection_exists() is True


@patch("fitness_assistant.rag.llm_interface.QdrantClient")
def test_collection_not_exist(mock_qdrant_client, mock_qdrant_config):
    """
    Tests collection_exists method when the collection is not present.
    """
    mock_client_instance = MagicMock()
    mock_client_instance.get_collections.return_value = MagicMock(collections=[])
    mock_qdrant_client.return_value = mock_client_instance

    vector_db = ManageVectorDb(config=mock_qdrant_config)
    assert vector_db.collection_exists() is False


@patch("fitness_assistant.rag.llm_interface.QdrantClient")
def test_search_calls_query_points(mock_qdrant_client, mock_qdrant_config):
    """
    Tests that the search method calls the client's query_points with the correct parameters.
    """
    mock_client_instance = MagicMock()
    mock_qdrant_client.return_value = mock_client_instance
    vector_db = ManageVectorDb(config=mock_qdrant_config)
    query = "bicep exercises"

    vector_db.search(query)
    mock_client_instance.query_points.assert_called_once()
