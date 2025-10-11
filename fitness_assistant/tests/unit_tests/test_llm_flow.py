import pytest
from unittest.mock import patch, MagicMock

from fitness_assistant.rag.llm_interface import LLMFlow
from fitness_assistant.rag.settings import LlmConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)


@pytest.fixture
def mock_llm_config(monkeypatch):
    """Fixture to provide a mock LlmConfig."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    return LlmConfig()


@patch("fitness_assistant.rag.llm_interface.ChatGoogleGenerativeAI")
def test_get_prompt_from_template(mock_chat_google, mock_llm_config):
    """
    Tests that the prompt template is created correctly.
    """
    flow = LLMFlow(config=mock_llm_config)
    prompt = flow.get_prompt_from_template()
    assert isinstance(prompt, ChatPromptTemplate)
    assert any(isinstance(msg, SystemMessagePromptTemplate) for msg in prompt.messages)
    assert any(isinstance(msg, HumanMessagePromptTemplate) for msg in prompt.messages)
    assert mock_llm_config.system_prompt in str(prompt.messages[0].prompt.template)


@patch("fitness_assistant.rag.llm_interface.ChatGoogleGenerativeAI")
def test_run_invokes_chain_and_returns_content(mock_chat_google, mock_llm_config):
    """
    Tests the run method to ensure it invokes the chain and returns the content.
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.content = "This is the generated response."

    flow = LLMFlow(config=mock_llm_config)
    flow.chain = MagicMock()
    flow.chain.invoke.return_value = mock_response

    # Act
    result = flow.run(query="test query", context="test context")

    # Assert
    flow.chain.invoke.assert_called_once_with(
        {"question": "test query", "context": "test context"}
    )
    assert result == "This is the generated response."
