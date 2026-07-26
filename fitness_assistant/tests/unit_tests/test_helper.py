"""
Test utility helper function
"""

import json
import pytest
from qdrant_client.models import ScoredPoint
from unittest.mock import MagicMock, patch
from rich.panel import Panel

from fitness_assistant.rag.helper import (
    load_data,
    load_csv_data,
    load_json_data,
    clean_data,
    create_document,
    format_vector_db_context,
    display_rag_response,
    _join_list_field,
)


def test_join_list_field():
    """Tests joining list fields and handling scalars/None."""
    assert _join_list_field(["a", "b", "c"]) == "a, b, c"
    assert _join_list_field([]) == ""
    assert _join_list_field(None) == ""
    assert _join_list_field("already a string") == "already a string"
    assert _join_list_field(["abs", "", "chest"]) == "abs, chest"


def test_load_csv_data_utf8(tmp_path):
    """Tests loading a standard UTF-8 encoded CSV file."""
    file_path = tmp_path / "test_utf8.csv"
    csv_content = "col1,col2\nval1,val2"
    file_path.write_text(csv_content, encoding="utf-8")

    df = load_csv_data(file_path)
    assert not df.empty
    assert list(df.columns) == ["col1", "col2"]
    assert df.iloc[0]["col1"] == "val1"


def test_load_csv_data_cp1252(tmp_path):
    """Tests the fallback to 'cp1252' encoding if UTF-8 fails."""
    file_path = tmp_path / "test_cp1252.csv"
    # Use a character that fails in UTF-8 but works in cp1252
    csv_content = "col1,col2\nval1,val’2"
    file_path.write_text(csv_content, encoding="cp1252")

    df = load_csv_data(file_path)
    assert not df.empty
    assert df.iloc[0]["col2"] == "val’2"


def test_load_data_routes_csv(tmp_path):
    """load_data should route .csv files to the CSV loader."""
    file_path = tmp_path / "test.csv"
    file_path.write_text("col1,col2\nval1,val2", encoding="utf-8")
    df = load_data(file_path)
    assert list(df.columns) == ["col1", "col2"]


def test_load_data_routes_json(tmp_path):
    """load_data should route .json files to the JSON loader."""
    file_path = tmp_path / "test.json"
    payload = {
        "categories": ["strength"],
        "equipment": ["none"],
        "exercises": [
            {
                "name": "Push-Up",
                "category": "strength",
                "description": "Bodyweight push",
                "equipment": ["none"],
                "instructions": ["Get into plank.", "Lower and press up."],
                "primary_muscles": ["chest"],
                "secondary_muscles": ["triceps", "shoulders"],
                "variations_on": ["push-up"],
                "video": "https://example.com/pushup",
            }
        ],
    }
    file_path.write_text(json.dumps(payload), encoding="utf-8")
    df = load_data(file_path)
    assert len(df) == 1
    assert df.iloc[0]["exercise_name"] == "Push-Up"


def test_load_data_file_not_found():
    """Tests that FileNotFoundError is raised for a non-existent file."""
    with pytest.raises(FileNotFoundError):
        load_data("non_existent_file.csv")


def test_load_json_data_normalizes_fields(tmp_path):
    """Tests V2 JSON normalization into the pipeline schema."""
    file_path = tmp_path / "exercises_v2.json"
    payload = {
        "categories": ["strength", "stretching"],
        "equipment": ["none", "dumbbell"],
        "exercises": [
            {
                "name": "3/4 Sit-Up",
                "category": "strength",
                "description": "Sit-Up performed 3/4 of the way up",
                "equipment": ["none"],
                "instructions": [
                    "Lie down on the floor.",
                    "Flex your hips and spine.",
                ],
                "primary_muscles": ["abs"],
                "secondary_muscles": [],
                "variations_on": ["sit-up"],
                "video": "https://www.youtube.com/watch?v=wm47Swzn_98",
            },
            {
                "name": "90/90 Hamstring",
                "category": "stretching",
                "description": "Hamstring stretch with legs split",
                "equipment": ["none", "gym mat"],
                "instructions": ["Lie on your back.", "Extend your leg."],
                "primary_muscles": ["hamstrings"],
                "secondary_muscles": ["calves"],
                "variations_on": [],
                "video": "https://www.youtube.com/watch?v=h_yZV27H684",
            },
        ],
    }
    file_path.write_text(json.dumps(payload), encoding="utf-8")

    df = load_json_data(file_path)

    assert len(df) == 2
    expected_cols = {
        "exercise_name",
        "type_of_activity",
        "type_of_equipment",
        "body_part",
        "type",
        "muscle_groups_activated",
        "instructions",
        "video_link",
        "description",
        "variations_on",
    }
    assert expected_cols.issubset(set(df.columns))

    first = df.iloc[0]
    assert first["exercise_name"] == "3/4 Sit-Up"
    assert first["type_of_activity"] == "strength"
    assert first["type_of_equipment"] == "none"
    assert first["body_part"] == "abs"
    assert first["muscle_groups_activated"] == "abs"
    assert first["instructions"] == "Lie down on the floor., Flex your hips and spine."
    assert first["video_link"] == "https://www.youtube.com/watch?v=wm47Swzn_98"
    assert first["description"] == "Sit-Up performed 3/4 of the way up"
    assert first["variations_on"] == "sit-up"

    second = df.iloc[1]
    assert second["type_of_equipment"] == "none, gym mat"
    assert second["muscle_groups_activated"] == "hamstrings, calves"
    assert second["body_part"] == "hamstrings"


def test_load_json_data_empty_raises(tmp_path):
    """Empty exercises list should raise ValueError."""
    file_path = tmp_path / "empty.json"
    file_path.write_text(json.dumps({"exercises": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="No exercises found"):
        load_json_data(file_path)


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


def test_clean_data_normalized_json(sample_v2_dataframe):
    """clean_data should drop duplicates on exercise_name for already-normalized V2 data."""
    cleaned = clean_data(sample_v2_dataframe)
    assert len(cleaned) == 2
    assert cleaned["exercise_name"].tolist() == ["Push-Up", "Squat"]


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
                "description": "Classic arm curl",
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

    with patch("fitness_assistant.rag.helper.QdrantConfig") as mock_cfg:
        mock_cfg.return_value.context_mapping = {
            "exercise_name": "Exercise",
            "type_of_activity": "Type of activity",
            "type_of_equipment": "Equipment",
            "body_part": "Body part",
            "type": "Exercise type",
            "muscle_groups_activated": "Muscle groups",
            "description": "Description",
            "instructions": "Instructions",
            "variations_on": "Variations",
            "video_link": "Video link",
        }
        # Avoid needing real env vars when constructing QdrantConfig
        formatted_string = format_vector_db_context(mock_points)

    # Check that the output contains the expected formatted text
    assert "Exercise: Bicep Curl" in formatted_string
    assert "Instructions: Curl the weight up." in formatted_string
    assert "Video link: http://example.com/bicep" in formatted_string
    assert "Description: Classic arm curl" in formatted_string

    # Check handling of missing fields (should show 'N/A')
    assert "Equipment: N/A" in formatted_string
    assert "Type of activity: N/A" in formatted_string

    # Check the separator between points
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
