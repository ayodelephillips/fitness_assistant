"""
User preferences and personalization module for fitness assistant RAG.

This module handles user profile management and filtering exercises based on
user preferences, fitness level, equipment availability, and restrictions.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum


class FitnessLevel(str, Enum):
    """Enumeration of fitness levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class UserProfile(BaseModel):
    """
    Pydantic model for user profile containing fitness preferences.
    """
    user_id: Optional[str] = Field(None, description="Unique user identifier")
    fitness_level: FitnessLevel = Field(
        FitnessLevel.BEGINNER,
        description="User's fitness level"
    )
    goals: List[str] = Field(
        default_factory=list,
        description="List of fitness goals (e.g., 'weight loss', 'muscle gain', 'endurance')"
    )
    equipment: List[str] = Field(
        default_factory=list,
        description="List of available equipment (e.g., 'dumbbells', 'barbell', 'cardio machine')"
    )
    restrictions: List[str] = Field(
        default_factory=list,
        description="List of physical restrictions or limitations (e.g., 'bad knee', 'shoulder injury')"
    )

    @validator("fitness_level", pre=True)
    def validate_fitness_level(cls, v):
        """Validate fitness level is one of the allowed values."""
        if isinstance(v, str):
            try:
                return FitnessLevel(v.lower())
            except ValueError:
                raise ValueError(
                    f"Invalid fitness level: {v}. Must be one of {[fl.value for fl in FitnessLevel]}"
                )
        return v

    @validator("goals", "equipment", "restrictions")
    def validate_non_empty_strings(cls, v):
        """Validate that lists contain only non-empty strings."""
        if not isinstance(v, list):
            raise ValueError("Must be a list")
        for item in v:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("List items must be non-empty strings")
        return [item.lower().strip() for item in v]


class PreferenceManager:
    """
    Manages user profiles and applies preference-based filtering to exercises.
    """

    def __init__(self):
        """Initialize the preference manager with empty profile storage."""
        self._profiles: Dict[str, UserProfile] = {}

    def create_profile(self, user_id: str, profile: UserProfile) -> UserProfile:
        """
        Create a new user profile.

        :param user_id: Unique identifier for the user
        :param profile: UserProfile instance
        :return: The created UserProfile with user_id set
        """
        if user_id in self._profiles:
            raise ValueError(f"Profile for user {user_id} already exists")

        profile.user_id = user_id
        self._profiles[user_id] = profile
        return profile

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Retrieve a user profile by ID.

        :param user_id: Unique identifier for the user
        :return: UserProfile if exists, None otherwise
        """
        return self._profiles.get(user_id)

    def update_profile(self, user_id: str, profile: UserProfile) -> UserProfile:
        """
        Update an existing user profile.

        :param user_id: Unique identifier for the user
        :param profile: Updated UserProfile instance
        :return: The updated UserProfile
        :raises ValueError: If profile doesn't exist
        """
        if user_id not in self._profiles:
            raise ValueError(f"Profile for user {user_id} does not exist")

        profile.user_id = user_id
        self._profiles[user_id] = profile
        return profile

    def delete_profile(self, user_id: str) -> bool:
        """
        Delete a user profile.

        :param user_id: Unique identifier for the user
        :return: True if deleted, False if profile didn't exist
        """
        if user_id in self._profiles:
            del self._profiles[user_id]
            return True
        return False


def filter_exercises_by_profile(
    exercises: List[Dict[str, Any]],
    profile: UserProfile
) -> List[Dict[str, Any]]:
    """
    Filter exercises based on user profile preferences.

    Filters exercises by:
    - Equipment availability
    - Fitness level appropriateness
    - Physical restrictions

    :param exercises: List of exercise dictionaries
    :param profile: UserProfile to filter against
    :return: Filtered list of exercises
    """
    if not exercises or not profile:
        return exercises

    filtered = []

    for exercise in exercises:
        # Check if exercise is in restrictions (e.g., avoid exercises that hurt bad knees)
        if _has_restricted_exercises(exercise, profile.restrictions):
            continue

        # Check if exercise matches available equipment
        if profile.equipment and not _has_matching_equipment(exercise, profile.equipment):
            continue

        # Check if exercise matches fitness level
        if not _matches_fitness_level(exercise, profile.fitness_level):
            continue

        filtered.append(exercise)

    return filtered


def _has_restricted_exercises(exercise: Dict[str, Any], restrictions: List[str]) -> bool:
    """
    Check if exercise conflicts with user restrictions.

    :param exercise: Exercise dictionary
    :param restrictions: List of user restrictions
    :return: True if exercise should be restricted, False otherwise
    """
    if not restrictions:
        return False

    exercise_body_parts = str(exercise.get("body_part", "")).lower()
    exercise_muscle_groups = str(exercise.get("muscle_groups_activated", "")).lower()
    exercise_instructions = str(exercise.get("instructions", "")).lower()

    for restriction in restrictions:
        restriction_lower = restriction.lower()
        if (restriction_lower in exercise_body_parts or
            restriction_lower in exercise_muscle_groups or
            restriction_lower in exercise_instructions):
            return True

    return False


def _has_matching_equipment(exercise: Dict[str, Any], equipment: List[str]) -> bool:
    """
    Check if exercise requires only available equipment.

    :param exercise: Exercise dictionary
    :param equipment: List of available equipment
    :return: True if exercise can be performed with available equipment
    """
    if not equipment:
        return True

    required_equipment = str(exercise.get("equipment", "")).lower()
    exercise_name = str(exercise.get("exercise_name", "")).lower()

    if not required_equipment and not exercise_name:
        return True

    required_lower = required_equipment.replace(",", " ").split()
    available_lower = [e.lower() for e in equipment]

    for req in required_lower:
        if req and req not in available_lower and req != "bodyweight":
            for avail in available_lower:
                if req not in avail and avail not in req:
                    continue
            return False

    return True


def _matches_fitness_level(
    exercise: Dict[str, Any],
    fitness_level: FitnessLevel
) -> bool:
    """
    Check if exercise is appropriate for user's fitness level.

    :param exercise: Exercise dictionary
    :param fitness_level: User's fitness level
    :return: True if exercise matches fitness level
    """
    difficulty = str(exercise.get("difficulty", "intermediate")).lower()

    level_mapping = {
        FitnessLevel.BEGINNER: ["beginner", "easy"],
        FitnessLevel.INTERMEDIATE: ["beginner", "intermediate", "moderate"],
        FitnessLevel.ADVANCED: ["beginner", "intermediate", "advanced", "hard"]
    }

    allowed_difficulties = level_mapping.get(fitness_level, [])
    return any(diff in difficulty for diff in allowed_difficulties)
