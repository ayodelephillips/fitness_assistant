#!/usr/bin/env python
"""
Integration test for personalization foundation.
Tests the end-to-end workflow with sample data.
"""

from fitness_assistant.rag.user_preferences import (
    UserProfile,
    PreferenceManager,
    FitnessLevel,
    filter_exercises_by_profile,
)


def test_integration_personalization():
    """Test end-to-end personalization workflow."""
    
    # Create a sample user profile
    profile = UserProfile(
        fitness_level=FitnessLevel.BEGINNER,
        goals=["weight loss", "cardio improvement"],
        equipment=["dumbbells", "bodyweight"],
        restrictions=["bad knee"]
    )
    print(f"✓ Created user profile: {profile}")
    
    # Test PreferenceManager
    manager = PreferenceManager()
    created = manager.create_profile("user001", profile)
    print(f"✓ Created profile in manager: {created.user_id}")
    
    retrieved = manager.get_profile("user001")
    assert retrieved is not None
    print(f"✓ Retrieved profile from manager")
    
    # Update profile
    updated_profile = UserProfile(
        fitness_level=FitnessLevel.INTERMEDIATE,
        goals=["muscle gain"],
        equipment=["dumbbells", "barbell"],
        restrictions=[]
    )
    manager.update_profile("user001", updated_profile)
    print(f"✓ Updated profile in manager")
    
    # Test exercise filtering
    sample_exercises = [
        {
            "exercise_name": "dumbbell squat",
            "body_part": "legs",
            "muscle_groups_activated": "quadriceps, glutes",
            "instructions": "hold dumbbells and squat",
            "equipment": "dumbbells",
            "difficulty": "beginner"
        },
        {
            "exercise_name": "pushup",
            "body_part": "chest",
            "muscle_groups_activated": "chest, shoulders, triceps",
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
            "exercise_name": "dumbbell bench press",
            "body_part": "chest",
            "muscle_groups_activated": "chest, shoulders, triceps",
            "instructions": "hold dumbbells and press",
            "equipment": "dumbbells",
            "difficulty": "beginner"
        }
    ]
    
    # Test with beginner profile with knee restriction
    beginner_profile = UserProfile(
        fitness_level=FitnessLevel.BEGINNER,
        restrictions=["knee"]
    )
    filtered = filter_exercises_by_profile(sample_exercises, beginner_profile)
    print(f"✓ Filtered exercises for beginner with knee restriction: {len(filtered)} exercises")
    exercise_names = [ex["exercise_name"] for ex in filtered]
    assert "leg press" not in exercise_names  # Should exclude leg exercises
    assert "pushup" in exercise_names
    
    # Test with equipment restriction
    limited_equipment_profile = UserProfile(
        fitness_level=FitnessLevel.BEGINNER,
        equipment=["dumbbells"]
    )
    filtered = filter_exercises_by_profile(sample_exercises, limited_equipment_profile)
    print(f"✓ Filtered exercises for limited equipment: {len(filtered)} exercises")
    exercise_names = [ex["exercise_name"] for ex in filtered]
    assert "leg press" not in exercise_names  # Requires machine
    
    # Test advanced fitness level allows more exercises
    advanced_profile = UserProfile(fitness_level=FitnessLevel.ADVANCED)
    filtered = filter_exercises_by_profile(sample_exercises, advanced_profile)
    print(f"✓ Filtered exercises for advanced user: {len(filtered)} exercises")
    assert len(filtered) == len(sample_exercises)
    
    print("\n✅ All integration tests passed!")


if __name__ == "__main__":
    test_integration_personalization()
