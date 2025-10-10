import pandas as pd
from pathlib import Path
from fitness_assistant.rag.settings import QdrantConfig
from qdrant_client.models import ScoredPoint


def load_data(file_path: Path) -> pd.DataFrame:
    """
    :params - location of file
    """
    try:
        return pd.read_csv(file_path, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="cp1252")  # windows


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    # remove duplicates
    df = df.drop_duplicates(subset="Exercise Name")

    # lower column names, replace space with underscore
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    return df


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
