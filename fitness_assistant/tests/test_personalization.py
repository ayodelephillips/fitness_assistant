"""
Comprehensive tests for personalization module (user_preferences.py).

Tests cover user profile creation, validation, filtering, and edge cases.
"""

import pytest
from fitness_assistant.rag.user_preferences import (
    UserProfile,
    PreferenceManager,
    FitnessLevel,
    filter_exercises_by_profile,
)


class TestUserProfileModel:
    """Tests for UserProfile Pydantic model."""

    def test_create_user_profile_minimal(self):
        """Test creating a user profile with minimal fields."""
        profile = UserProfile()
        assert profile.fitness_level == FitnessLevel.BEGINNER
        assert profile.goals == []
        assert profile.equipment == []
        assert profile.restrictions == []
        assert profile.user_id is None

    def test_create_user_profile_full(self):
        """Test creating a user profile with all fields."""
        profile = UserProfile(
            user_id="user123",
            fitness_level=FitnessLevel.INTERMEDIATE,
            goals=["muscle gain", "strength"],
            equipment=["dumbbells", "barbell"],
            restrictions=["bad knee"]
        )
        assert profile.user_id == "user123"
        assert profile.fitness_level == FitnessLevel.INTERMEDIATE
        assert profile.goals == ["muscle gain", "strength"]
        assert profile.equipment == ["dumbbells", "barbell"]
        assert profile.restrictions == ["bad knee"]

    def test_fitness_level_case_insensitive(self):
        """Test that fitness level validation is case insensitive."""
        profile = UserProfile(fitness_level="ADVANCED")
        assert profile.fitness_level == FitnessLevel.ADVANCED

        profile2 = UserProfile(fitness_level="BeGiNnEr")
        assert profile2.fitness_level == FitnessLevel.BEGINNER

    def test_invalid_fitness_level(self):
        """Test that invalid fitness level raises ValueError."""
        with pytest.raises(ValueError, match="Invalid fitness level"):
            UserProfile(fitness_level="expert")

    def test_goals_normalization(self):
        """Test that goals are lowercased and stripped."""
        profile = UserProfile(goals=["  Weight Loss  ", "MUSCLE GAIN"])
        assert profile.goals == ["weight loss", "muscle gain"]

    def test_equipment_normalization(self):
        """Test that equipment is lowercased and stripped."""
        profile = UserProfile(equipment=["  DumbBells  ", "BARBELL"])
        assert profile.equipment == ["dumbbells", "barbell"]

    def test_restrictions_normalization(self):
        """Test that restrictions are lowercased and stripped."""
        profile = UserProfile(restrictions=["  Bad KNEE  ", "SHOULDER INJURY"])
        assert profile.restrictions == ["bad knee", "shoulder injury"]

    def test_empty_string_in_list_rejected(self):
        """Test that empty strings in lists are rejected."""
        with pytest.raises(ValueError):
            UserProfile(goals=["valid goal", "  "])

    def test_non_string_in_list_rejected(self):
        """Test that non-string items in lists are rejected."""
        with pytest.raises(ValueError):
            UserProfile(goals=["valid goal", 123])

    def test_profile_validation_error(self):
        """Test that profile validation fails for non-list equipment."""
        with pytest.raises(ValueError):
            UserProfile(equipment="dumbbells")


class TestPreferenceManager:
    """Tests for PreferenceManager class."""

    @pytest.fixture
    def manager(self):
        """Fixture providing a fresh PreferenceManager instance."""
        return PreferenceManager()

    def test_create_profile(self, manager):
        """Test creating a new user profile."""
        profile = UserProfile(
            fitness_level=FitnessLevel.INTERMEDIATE,
            goals=["weight loss"]
        )
        created = manager.create_profile("user1", profile)
        assert created.user_id == "user1"
        assert created.fitness_level == FitnessLevel.INTERMEDIATE
        assert created.goals == ["weight loss"]

    def test_create_profile_duplicate_raises_error(self, manager):
        """Test that creating duplicate profile raises error."""
        profile = UserProfile()
        manager.create_profile("user1", profile)
        with pytest.raises(ValueError, match="already exists"):
            manager.create_profile("user1", profile)

    def test_get_profile(self, manager):
        """Test retrieving an existing profile."""
        profile = UserProfile(fitness_level=FitnessLevel.ADVANCED)
        manager.create_profile("user1", profile)
        retrieved = manager.get_profile("user1")
        assert retrieved is not None
        assert retrieved.fitness_level == FitnessLevel.ADVANCED

    def test_get_profile_nonexistent(self, manager):
        """Test that getting nonexistent profile returns None."""
        assert manager.get_profile("nonexistent") is None

    def test_update_profile(self, manager):
        """Test updating an existing profile."""
        profile = UserProfile(fitness_level=FitnessLevel.BEGINNER)
        manager.create_profile("user1", profile)

        updated_profile = UserProfile(
            fitness_level=FitnessLevel.ADVANCED,
            goals=["strength"]
        )
        result = manager.update_profile("user1", updated_profile)
        assert result.fitness_level == FitnessLevel.ADVANCED
        assert result.goals == ["strength"]

    def test_update_profile_nonexistent_raises_error(self, manager):
        """Test that updating nonexistent profile raises error."""
        profile = UserProfile()
        with pytest.raises(ValueError, match="does not exist"):
            manager.update_profile("nonexistent", profile)

    def test_delete_profile(self, manager):
        """Test deleting a profile."""
        profile = UserProfile()
        manager.create_profile("user1", profile)
        assert manager.delete_profile("user1") is True
        assert manager.get_profile("user1") is None

    def test_delete_profile_nonexistent(self, manager):
        """Test that deleting nonexistent profile returns False."""
        assert manager.delete_profile("nonexistent") is False


class TestExerciseFiltering:
    """Tests for exercise filtering functionality."""

    @pytest.fixture
    def sample_exercises(self):
        """Fixture providing sample exercise data."""
        return [
            {
                "exercise_name": "dumbbell squat",
                "body_part": "legs",
                "muscle_groups_activated": "quadriceps, glutes",
                "instructions": "hold dumbbells and squat",
                "equipment": "dumbbells",
                "difficulty": "intermediate"
            },
            {
                "exercise_name": "pushup",
                "body_part": "chest",
                "muscle_groups_activated": "chest, shoulders",
                "instructions": "bodyweight exercise",
                "equipment": "bodyweight",
                "difficulty": "beginner"
            },
            {
                "exercise_name": "leg press",
                "body_part": "legs",
                "muscle_groups_activated": "quadriceps, hamstrings",
                "instructions": "machine leg press",
                "equipment": "leg press machine",
                "difficulty": "beginner"
            },
            {
                "exercise_name": "barbell squat",
                "body_part": "legs",
                "muscle_groups_activated": "quadriceps, glutes, hamstrings",
                "instructions": "hold barbell and squat",
                "equipment": "barbell",
                "difficulty": "advanced"
            },
        ]

    def test_filter_by_equipment(self, sample_exercises):
        """Test filtering exercises by equipment."""
        profile = UserProfile(equipment=["dumbbells"])
        filtered = filter_exercises_by_profile(sample_exercises, profile)

        assert len(filtered) > 0
        exercise_names = [ex["exercise_name"] for ex in filtered]
        assert "dumbbell squat" in exercise_names

    def test_filter_by_fitness_level(self, sample_exercises):
        """Test filtering exercises by fitness level."""
        profile = UserProfile(fitness_level=FitnessLevel.BEGINNER)
        filtered = filter_exercises_by_profile(sample_exercises, profile)

        assert len(filtered) > 0
        exercise_names = [ex["exercise_name"] for ex in filtered]
        assert "pushup" in exercise_names
        assert "leg press" in exercise_names

    def test_filter_by_restrictions(self, sample_exercises):
        """Test filtering exercises by restrictions."""
        profile = UserProfile(restrictions=["legs"])
        filtered = filter_exercises_by_profile(sample_exercises, profile)

        exercise_names = [ex["exercise_name"] for ex in filtered]
        assert "dumbbell squat" not in exercise_names
        assert "leg press" not in exercise_names
        assert "barbell squat" not in exercise_names
        assert "pushup" in exercise_names

    def test_filter_by_multiple_restrictions(self, sample_exercises):
        """Test filtering with multiple restrictions."""
        profile = UserProfile(restrictions=["legs", "chest"])
        filtered = filter_exercises_by_profile(sample_exercises, profile)

        assert len(filtered) == 0  # All exercises involve legs or chest

    def test_filter_combined_constraints(self, sample_exercises):
        """Test filtering with equipment and fitness level constraints."""
        profile = UserProfile(
            fitness_level=FitnessLevel.BEGINNER,
            equipment=["dumbbells"]
        )
        filtered = filter_exercises_by_profile(sample_exercises, profile)

        # Dumbbell squat is intermediate, so shouldn't be included for beginner
        exercise_names = [ex["exercise_name"] for ex in filtered]
        assert "dumbbell squat" not in exercise_names

    def test_filter_with_empty_equipment_allows_all(self, sample_exercises):
        """Test that empty equipment list doesn't filter exercises."""
        profile = UserProfile(equipment=[])
        filtered = filter_exercises_by_profile(sample_exercises, profile)

        assert len(filtered) == len(sample_exercises)

    def test_filter_empty_exercises_list(self):
        """Test filtering empty exercise list."""
        profile = UserProfile()
        filtered = filter_exercises_by_profile([], profile)
        assert filtered == []

    def test_filter_none_profile(self):
        """Test filtering with None profile."""
        exercises = [{"exercise_name": "test"}]
        filtered = filter_exercises_by_profile(exercises, None)
        assert filtered == exercises

    def test_filter_advanced_fitness_level(self, sample_exercises):
        """Test filtering for advanced fitness level."""
        profile = UserProfile(fitness_level=FitnessLevel.ADVANCED)
        filtered = filter_exercises_by_profile(sample_exercises, profile)

        exercise_names = [ex["exercise_name"] for ex in filtered]
        # Advanced should include all exercises
        assert len(filtered) == 4

    def test_filter_by_restriction_substring_match(self, sample_exercises):
        """Test that restrictions work with substring matching."""
        profile = UserProfile(restrictions=["quad"])
        filtered = filter_exercises_by_profile(sample_exercises, profile)

        exercise_names = [ex["exercise_name"] for ex in filtered]
        # All leg exercises contain quadriceps
        assert "dumbbell squat" not in exercise_names
        assert "leg press" not in exercise_names
        assert "barbell squat" not in exercise_names
        assert "pushup" in exercise_names


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_profile_with_special_characters_in_strings(self):
        """Test profile handles special characters."""
        profile = UserProfile(
            goals=["weight loss/fat burn", "build muscle-endurance"],
            equipment=["dumbbell (5lb)"]
        )
        assert len(profile.goals) == 2
        assert len(profile.equipment) == 1

    def test_filter_exercises_missing_fields(self):
        """Test filtering exercises with missing fields."""
        exercises = [
            {"exercise_name": "test exercise"},  # Missing most fields
            {"body_part": "chest"}  # Missing exercise_name
        ]
        profile = UserProfile()
        filtered = filter_exercises_by_profile(exercises, profile)
        # Should not crash
        assert isinstance(filtered, list)

    def test_profile_normalization_preserves_uniqueness(self):
        """Test that normalization doesn't lose data."""
        profile = UserProfile(
            goals=["Weight Loss", "MUSCLE GAIN", "weight loss"],
            equipment=["DUMBBELLS", "dumbbells", "Barbell"]
        )
        assert len(profile.goals) == 3  # All three entries preserved
        assert len(profile.equipment) == 3

    def test_manager_with_many_profiles(self):
        """Test manager can handle multiple profiles."""
        manager = PreferenceManager()
        for i in range(100):
            profile = UserProfile(fitness_level=FitnessLevel.BEGINNER)
            manager.create_profile(f"user{i}", profile)

        assert manager.get_profile("user50") is not None
        assert manager.get_profile("user99") is not None
        assert manager.delete_profile("user50")
        assert manager.get_profile("user50") is None
