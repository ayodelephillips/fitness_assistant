import pandas as pd
import pytest


@pytest.fixture
def sample_dataframe():
    """Provides a sample DataFrame for testing (raw CSV-style columns)."""
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


@pytest.fixture
def sample_v2_dataframe():
    """Provides a normalized V2-style DataFrame (with a duplicate name)."""
    data = {
        "exercise_name": ["Push-Up", "Squat", "Push-Up"],
        "type_of_activity": ["strength", "strength", "strength"],
        "type_of_equipment": ["none", "barbell", "none"],
        "body_part": ["chest", "quadriceps", "chest"],
        "type": ["strength", "strength", "strength"],
        "muscle_groups_activated": [
            "chest, triceps",
            "quadriceps, glutes",
            "chest, triceps",
        ],
        "instructions": [
            "Get into plank. Lower and press.",
            "Bar on back. Squat down.",
            "Get into plank. Lower and press.",
        ],
        "video_link": [
            "https://example.com/pushup",
            "https://example.com/squat",
            "https://example.com/pushup",
        ],
        "description": [
            "Bodyweight push",
            "Barbell squat",
            "Bodyweight push",
        ],
        "variations_on": ["push-up", "squat", "push-up"],
    }
    return pd.DataFrame(data)
