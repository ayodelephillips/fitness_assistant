""""
Test utility helper function
"""

import pandas as pd
import pytest
from qdrant_client.models import ScoredPoint

from fitness_assistant.rag.helper import (
    load_data,
    clean_data,
    create_document,
    format_vector_db_context,
)


@pytest.fixture
def sample_dataframe():
    """Provides a sample DataFrame for testing."""
    data = {
        "Exercise Name": ["Push-Up", "Squat", "Push-Up"],
        "Type of Activity": ["Strength", "Strength", "Strength"],
        "Body Part": ["Upper Body", "Lower Body", "Upper Body"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def cleaned_dataframe():
    """Provides a cleaned version of the sample DataFrame."""
    data = {
        "exercise_name": ["Push-Up", "Squat"],
        "type_of_activity": ["Strength", "Strength"],
        "body_part": ["Upper Body", "Lower Body"],
    }
    return pd.DataFrame(data)


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
    # Mock ScoredPoint objects
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
                # Missing some fields to test graceful handling
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
