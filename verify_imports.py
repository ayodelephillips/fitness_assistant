#!/usr/bin/env python
"""
Quick script to verify that all imports work correctly
and the personalization module is properly integrated.
"""

import sys
import traceback

def verify_imports():
    """Verify all imports work."""
    print("=" * 60)
    print("IMPORT VERIFICATION")
    print("=" * 60)
    
    try:
        # Test user_preferences imports
        print("\n[1/4] Importing user_preferences module...")
        from fitness_assistant.rag.user_preferences import (
            UserProfile,
            PreferenceManager,
            FitnessLevel,
            filter_exercises_by_profile,
        )
        print("✓ Successfully imported: UserProfile, PreferenceManager, FitnessLevel, filter_exercises_by_profile")
        
        # Test llm_interface imports
        print("\n[2/4] Importing updated llm_interface module...")
        from fitness_assistant.rag import llm_interface
        print("✓ Successfully imported llm_interface")
        
        # Verify rag function signature
        print("\n[3/4] Verifying rag() function signature...")
        import inspect
        sig = inspect.signature(llm_interface.rag)
        params = list(sig.parameters.keys())
        print(f"✓ rag() parameters: {params}")
        assert 'user_profile' in params, "user_profile parameter missing from rag()"
        print("✓ user_profile parameter found in rag() function")
        
        # Test basic functionality
        print("\n[4/4] Testing basic functionality...")
        profile = UserProfile(
            fitness_level=FitnessLevel.INTERMEDIATE,
            goals=["strength"],
            equipment=["dumbbells"]
        )
        print(f"✓ Created UserProfile: {profile}")
        
        manager = PreferenceManager()
        created = manager.create_profile("test_user", profile)
        print(f"✓ Created profile via PreferenceManager: {created.user_id}")
        
        retrieved = manager.get_profile("test_user")
        print(f"✓ Retrieved profile: {retrieved.user_id}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ IMPORT VERIFICATION FAILED:")
        traceback.print_exc()
        return False


def main():
    """Run verification."""
    success = verify_imports()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL IMPORTS AND BASIC FUNCTIONALITY VERIFIED!")
        return 0
    else:
        print("❌ VERIFICATION FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
