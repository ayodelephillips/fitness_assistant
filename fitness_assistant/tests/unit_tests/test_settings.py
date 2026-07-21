from unittest.mock import patch
from pathlib import Path
import os
from fitness_assistant.rag.settings import GenAIModels, QdrantConfig, LlmConfig
from langchain_google_genai import HarmCategory, HarmBlockThreshold


def test_genai_models_enum():
    """Tests the values of the GenAIModels enum."""
    assert GenAIModels.gemini_2_5_flash == "gemini-2.5-flash"
    assert GenAIModels.gemini_2_5_pro == "gemini-2.5-pro"


@patch("dotenv.load_dotenv")
def test_qdrant_config_defaults(mock_load_dotenv, monkeypatch):
    """
    Tests QdrantConfig default values are loaded correctly.
    A dummy API key is provided to satisfy the required field.
    """
    monkeypatch.setenv("QDRANT_API_KEY", "test-key")
    config = QdrantConfig()

    assert config.collection_name == "exercise_collection"
    assert config.embedding_model == "jinaai/jina-embeddings-v2-small-en"
    assert config.embedding_dimension == 512
    assert config.response_limit == 3
    assert config.recreate_collection is False
    assert config.create_vectors is False
    assert config.qdrant_api_key == "test-key"


@patch("dotenv.load_dotenv")
def test_qdrant_config_env_override(mock_load_dotenv, monkeypatch):
    """Tests that QdrantConfig values can be overridden by environment variables."""
    monkeypatch.setenv("QDRANT_API_KEY", "override-key")
    monkeypatch.setenv("COLLECTION_NAME", "override_collection")
    monkeypatch.setenv("RESPONSE_LIMIT", "5")
    monkeypatch.setenv("RECREATE_COLLECTION", "true")

    config = QdrantConfig()

    assert config.qdrant_api_key == "override-key"
    assert config.collection_name == "override_collection"
    assert config.response_limit == 5
    assert config.recreate_collection is True


@patch("dotenv.load_dotenv")
def test_qdrant_config_document_location(mock_load_dotenv, monkeypatch):
    """Tests that the document_location path points at the V2 JSON dataset."""
    monkeypatch.setenv("QDRANT_API_KEY", "test-key")
    config = QdrantConfig()
    assert str(config.document_location).endswith(
        "rag/data/detailed_exercise_dataset_v2.json".replace("/", os.path.sep)
    )
    assert isinstance(config.document_location, Path)


@patch("dotenv.load_dotenv")
def test_qdrant_config_context_mapping_includes_v2_fields(
    mock_load_dotenv, monkeypatch
):
    """context_mapping should expose description and variations from V2."""
    monkeypatch.setenv("QDRANT_API_KEY", "test-key")
    config = QdrantConfig()
    assert "description" in config.context_mapping
    assert "variations_on" in config.context_mapping
    assert config.context_mapping["description"] == "Description"
    assert config.context_mapping["variations_on"] == "Variations"


def test_llm_config_defaults(monkeypatch):
    """
    Tests LlmConfig default values are loaded correctly.
    A dummy API key is provided to satisfy the required field.
    The __init__ calls load_dotenv, so we let it run.
    """
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    config = LlmConfig()

    assert config.model_name == GenAIModels.gemini_2_5_flash
    assert config.temperature == 0.4
    assert config.top_p == 1
    assert config.top_k == 1
    assert config.max_output_tokens == 4000
    assert config.google_api_key == "test-google-key"
    assert "You're a fitness instructor" in config.system_prompt


def test_llm_config_env_override(monkeypatch):
    """Tests that LlmConfig values can be overridden by environment variables."""
    monkeypatch.setenv("GOOGLE_API_KEY", "override-google-key")
    monkeypatch.setenv("MODEL_NAME", "gemini-2.5-flash")
    monkeypatch.setenv("TEMPERATURE", "0.9")

    config = LlmConfig()

    assert config.google_api_key == "override-google-key"
    assert config.model_name == GenAIModels.gemini_2_5_flash
    assert config.temperature == 0.9


def test_llm_config_safety_settings(monkeypatch):
    """Tests the default safety_settings factory."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    config = LlmConfig()

    expected_settings = {
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_VIOLENCE: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_SEXUAL: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }
    assert config.safety_settings == expected_settings


@patch("fitness_assistant.rag.settings.load_dotenv")
def test_llm_config_init_calls_load_dotenv(mock_load_dotenv, monkeypatch):
    """Tests that LlmConfig's __init__ calls load_dotenv."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    LlmConfig()
    mock_load_dotenv.assert_called_once()
