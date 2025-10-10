import pandas as pd
import pytest


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
