#!/usr/bin/env python
"""
Test runner to verify personalization module works correctly.
Run this to validate all components.
"""

import sys
import traceback


def run_import_tests():
    """Test that all modules can be imported."""
    print("=" * 60)
    print("IMPORT TESTS")
    print("=" * 60)
    
    try:
        from fitness_assistant.rag.user_preferences import (
            UserProfile,
            PreferenceManager,
            FitnessLevel,
            filter_exercises_by_profile,
        )
        print("✓ Successfully imported user_preferences module")
        
        from fitness_assistant.rag.llm_interface import rag
        print("✓ Successfully imported updated llm_interface module")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False


def run_basic_tests():
    """Run basic functionality tests."""
    print("\n" + "=" * 60)
    print("BASIC FUNCTIONALITY TESTS")
    print("=" * 60)
    
    try:
        from fitness_assistant.rag.user_preferences import (
            UserProfile,
            PreferenceManager,
            FitnessLevel,
            filter_exercises_by_profile,
        )
        
        # Test 1: Create UserProfile
        profile = UserProfile(
            fitness_level=FitnessLevel.INTERMEDIATE,
            goals=["strength", "endurance"],
            equipment=["dumbbells", "barbell"],
            restrictions=[]
        )
        print("✓ Test 1: Created UserProfile successfully")
        
        # Test 2: PreferenceManager create
        manager = PreferenceManager()
        manager.create_profile("test_user", profile)
        print("✓ Test 2: PreferenceManager.create_profile() works")
        
        # Test 3: PreferenceManager get
        retrieved = manager.get_profile("test_user")
        assert retrieved is not None
        print("✓ Test 3: PreferenceManager.get_profile() works")
        
        # Test 4: Filter exercises
        exercises = [
            {
                "exercise_name": "squat",
                "body_part": "legs",
                "equipment": "barbell",
                "difficulty": "beginner"
            },
            {
                "exercise_name": "deadlift",
                "body_part": "back",
                "equipment": "barbell",
                "difficulty": "intermediate"
            }
        ]
        filtered = filter_exercises_by_profile(exercises, profile)
        assert len(filtered) > 0
        print("✓ Test 4: filter_exercises_by_profile() works")
        
        # Test 5: Profile validation
        try:
            bad_profile = UserProfile(fitness_level="invalid")
            print("✗ Test 5: Profile validation failed - should reject invalid fitness level")
            return False
        except ValueError:
            print("✓ Test 5: Profile validation rejects invalid fitness level")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        traceback.print_exc()
        return False


def run_edge_case_tests():
    """Run edge case tests."""
    print("\n" + "=" * 60)
    print("EDGE CASE TESTS")
    print("=" * 60)
    
    try:
        from fitness_assistant.rag.user_preferences import (
            UserProfile,
            PreferenceManager,
            FitnessLevel,
            filter_exercises_by_profile,
        )
        
        # Test 1: Empty profile
        profile = UserProfile()
        assert profile.goals == []
        assert profile.equipment == []
        print("✓ Test 1: Empty profile creation works")
        
        # Test 2: Case normalization
        profile = UserProfile(
            goals=["WEIGHT LOSS", "  Muscle Gain  "],
            equipment=["DumbBells", "  BARBELL  "]
        )
        assert profile.goals == ["weight loss", "muscle gain"]
        assert profile.equipment == ["dumbbells", "barbell"]
        print("✓ Test 2: Case normalization works")
        
        # Test 3: Filter with empty exercises
        filtered = filter_exercises_by_profile([], profile)
        assert filtered == []
        print("✓ Test 3: Filter empty exercises works")
        
        # Test 4: Multiple restrictions
        profile = UserProfile(restrictions=["knee", "shoulder"])
        exercises = [
            {"body_part": "chest", "muscle_groups_activated": "chest"},
            {"body_part": "legs", "muscle_groups_activated": "quadriceps"},
            {"body_part": "shoulders", "muscle_groups_activated": "deltoids"}
        ]
        filtered = filter_exercises_by_profile(exercises, profile)
        assert len(filtered) == 1  # Only chest should pass
        print("✓ Test 4: Multiple restrictions work")
        
        return True
        
    except Exception as e:
        print(f"✗ Edge case test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " PERSONALIZATION MODULE TEST SUITE ".center(58) + "║")
    print("╚" + "=" * 58 + "╝")
    
    results = []
    
    # Run test suites
    results.append(("Import Tests", run_import_tests()))
    results.append(("Basic Functionality Tests", run_basic_tests()))
    results.append(("Edge Case Tests", run_edge_case_tests()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name}: {status}")
    
    print(f"\nTotal: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {total - passed} test suite(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
