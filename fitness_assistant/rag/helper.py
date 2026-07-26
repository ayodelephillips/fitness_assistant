import json
import pandas as pd
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from fitness_assistant.rag.settings import QdrantConfig
from qdrant_client.models import ScoredPoint


def _join_list_field(value) -> str:
    """Join list values into a comma-separated string; pass through scalars."""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item)
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)


def load_data(file_path: Path) -> pd.DataFrame:
    """
    Load exercise data from CSV or JSON based on file extension.

    :params file_path - location of file
    """
    suffix = Path(file_path).suffix.lower()
    if suffix == ".json":
        return load_json_data(file_path)
    return load_csv_data(file_path)


def load_csv_data(file_path: Path) -> pd.DataFrame:
    """
    Load a CSV exercise dataset.

    :params file_path - location of file
    """
    try:
        return pd.read_csv(file_path, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="cp1252")  # windows


def load_json_data(file_path: Path) -> pd.DataFrame:
    """
    Load and normalize the V2 JSON exercise dataset into a flat DataFrame.

    Expected JSON shape:
        {
          "categories": [...],
          "equipment": [...],
          "exercises": [
            {
              "name": str,
              "category": str,
              "description": str,
              "equipment": [str, ...],
              "instructions": [str, ...],
              "primary_muscles": [str, ...],
              "secondary_muscles": [str, ...],
              "variations_on": [str, ...],
              "video": str
            },
            ...
          ]
        }

    Output columns (normalized to the pipeline schema):
        exercise_name, type_of_activity, type_of_equipment, body_part,
        type, muscle_groups_activated, instructions, video_link,
        description, variations_on
    """
    with open(file_path, encoding="utf-8") as f:
        payload = json.load(f)

    exercises = payload.get("exercises", payload if isinstance(payload, list) else [])
    if not exercises:
        raise ValueError(f"No exercises found in JSON file: {file_path}")

    records = []
    for exercise in exercises:
        primary = exercise.get("primary_muscles") or []
        secondary = exercise.get("secondary_muscles") or []
        all_muscles = list(primary) + [m for m in secondary if m not in primary]

        # body_part is derived from primary muscles (best available signal in V2)
        body_part = (
            _join_list_field(primary) if primary else _join_list_field(all_muscles)
        )

        records.append(
            {
                "exercise_name": exercise.get("name", ""),
                "type_of_activity": exercise.get("category", ""),
                "type_of_equipment": _join_list_field(exercise.get("equipment")),
                "body_part": body_part,
                "type": exercise.get("category", ""),
                "muscle_groups_activated": _join_list_field(all_muscles),
                "instructions": _join_list_field(exercise.get("instructions")),
                "video_link": exercise.get("video", "") or "",
                "description": exercise.get("description", "") or "",
                "variations_on": _join_list_field(exercise.get("variations_on")),
            }
        )

    return pd.DataFrame(records)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean exercise DataFrame:
    - Drop duplicates on exercise name (supports both raw CSV and normalized JSON columns)
    - Lowercase column names and replace spaces with underscores
    """
    # Determine the exercise-name column before/after normalization
    name_col = None
    for candidate in ("Exercise Name", "exercise_name", "name"):
        if candidate in df.columns:
            name_col = candidate
            break

    if name_col:
        df = df.drop_duplicates(subset=name_col)

    # lower column names, replace space with underscore
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    return df.reset_index(drop=True)


def create_document(df: pd.DataFrame) -> list[dict]:
    """
    convert dataframe to records
    """
    return df.to_dict(orient="records")


def format_vector_db_context(context_points: list[ScoredPoint]):
    """
    Convert vector db context into readable context

    :params - context - A list of context vectors retrieved from vector db
    """
    context_mapping = QdrantConfig().context_mapping
    context_texts = []

    for point in context_points:
        payload = point.payload or {}

        formatted_context = "".join(
            f"{v}: {payload.get(k, 'N/A')}\n" for k, v in context_mapping.items()
        )
        context_texts.append(formatted_context)

    return "\n\n---\n\n".join(context_texts)


def display_rag_response(
    console_instance: Console, answer: str, is_context: bool = False
) -> None:
    """Pretty-print the RAG output using rich panels.
    :params - console_instance -  the instance of the console to use
    :params - answer - LLM response
    :params - is_context - boolean to check if the answer is vector db context or the llm response
    """
    console_instance.print(
        Panel(
            Text(answer, style="magenta"),
            title="Assistant's Answer" if not is_context else "Context from Vector DB",
            border_style="magenta",
        )
    )


if __name__ == "__main__":
    from fitness_assistant.rag.settings import DataFileNames

    data_path = (
        Path(__file__)
        .resolve()
        .parent.joinpath("data", DataFileNames.DETAILED_EXERCISE_DATASET_V2)
    )
    df = load_data(data_path)
    print(df.head())
    print(f"Loaded {len(df)} exercises")
    print(df.columns.tolist())
