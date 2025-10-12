""""
Test utility helper function
"""

import pytest
from qdrant_client.models import ScoredPoint
from unittest.mock import MagicMock
from rich.panel import Panel

from fitness_assistant.rag.helper import (
    load_data,
    clean_data,
    create_document,
    format_vector_db_context,
    display_rag_response,
)


def test_load_data_utf8(tmp_path):
    """Tests loading a standard UTF-8 encoded CSV file."""
    file_path = tmp_path / "test_utf8.csv"
    csv_content = "col1,col2\nval1,val2"
    file_path.write_text(csv_content, encoding="utf-8")

    df = load_data(file_path)
    assert not df.empty
    assert list(df.columns) == ["col1", "col2"]
    assert df.iloc[0]["col1"] == "val1"


def test_load_data_cp1252(tmp_path):
    """Tests the fallback to 'cp1252' encoding if UTF-8 fails."""
    file_path = tmp_path / "test_cp1252.csv"
    # Use a character that fails in UTF-8 but works in cp1252
    csv_content = "col1,col2\nval1,val’2"
    file_path.write_text(csv_content, encoding="cp1252")

    df = load_data(file_path)
    assert not df.empty
    assert df.iloc[0]["col2"] == "val’2"


def test_load_data_file_not_found():
    """Tests that FileNotFoundError is raised for a non-existent file."""
    with pytest.raises(FileNotFoundError):
        load_data("non_existent_file.csv")


def test_clean_data(sample_dataframe):
    """
    Tests cleaning the DataFrame:
    1. Drops duplicates based on 'Exercise Name'.
    2. Converts column names to lowercase and replaces spaces with underscores.
    """
    cleaned_df = clean_data(sample_dataframe)

    # Check for duplicate removal
    assert len(cleaned_df) == 2
    assert cleaned_df["exercise_name"].tolist() == ["Push-Up", "Squat"]

    # Check for column name cleaning
    expected_columns = ["exercise_name", "type_of_activity", "body_part"]
    assert list(cleaned_df.columns) == expected_columns


def test_create_document(cleaned_dataframe):
    """Tests the conversion of a DataFrame to a list of dictionaries."""
    document_list = create_document(cleaned_dataframe)

    assert isinstance(document_list, list)
    assert len(document_list) == 2
    assert isinstance(document_list[0], dict)
    assert document_list[0]["exercise_name"] == "Push-Up"
    assert document_list[1]["exercise_name"] == "Squat"


def test_format_vector_db_context():
    """Tests the formatting of ScoredPoint objects into a readable string."""
    mock_points = [
        ScoredPoint(
            id=1,
            version=1,
            score=0.9,
            payload={
                "exercise_name": "Bicep Curl",
                "type_of_activity": "Strength",
                "type_of_equipment": "Dumbbell",
                "body_part": "Arms",
                "instructions": "Curl the weight up.",
                "video_link": "http://example.com/bicep",
            },
            vector=None,
        ),
        ScoredPoint(
            id=2,
            version=1,
            score=0.85,
            payload={
                "exercise_name": "Tricep Extension",
                "body_part": "Arms",
                "instructions": "Extend the weight.",
            },
            vector=None,
        ),
    ]

    formatted_string = format_vector_db_context(mock_points)

    # Check that the output contains the expected formatted text
    assert "Exercise: Bicep Curl" in formatted_string
    assert "Instructions: Curl the weight up." in formatted_string
    assert "Video link: http://example.com/bicep" in formatted_string

    # # Check handling of missing fields (should show 'N/A')
    assert "Equipment: N/A" in formatted_string
    assert "Type of activity: N/A" in formatted_string

    # # Check the separator between points
    assert "\n\n---\n\n" in formatted_string


@pytest.mark.parametrize(
    "is_context, expected_title",
    [
        (False, "Assistant's Answer"),
        (True, "Context from Vector DB"),
    ],
)
def test_display_rag_response(is_context, expected_title):
    """Tests that display_rag_response prints a panel with the correct title."""
    # Arrange
    mock_console = MagicMock()
    test_answer = "This is a test answer."

    # Act
    display_rag_response(
        console_instance=mock_console, answer=test_answer, is_context=is_context
    )

    # Assert
    mock_console.print.assert_called_once()
    printed_object = mock_console.print.call_args[0][0]

    assert isinstance(printed_object, Panel)
    assert printed_object.title == expected_title
    assert printed_object.renderable.plain == test_answer
