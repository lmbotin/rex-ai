"""Test script for FNOL module."""

from src.fnol import FNOLClaim, FNOLStateManager, LossType, ReporterRole

def test_fnol_module():
    # Test 1: Create FNOL State Manager
    print("Test 1: Creating FNOLStateManager...")
    manager = FNOLStateManager()
    print(f"  Claim ID: {manager.claim.claim_id}")
    print(f"  Completion: {manager.get_completion_percentage():.1f}%")

    # Test 2: Get next question
    print("\nTest 2: Getting next question...")
    next_q = manager.get_next_question()
    print(f"  Next field: {next_q['id']}")
    print(f"  Question: {next_q['question']}")

    # Test 3: Apply a patch (simulate extraction)
    print("\nTest 3: Applying extracted data...")
    patch = {
        "reporter.full_name": "John Smith",
        "reporter.role": "policyholder",
        "policy.policy_number": "POL-12345",
        "loss.loss_type": "collision",
        "loss.date_description": "yesterday around 3pm",
    }
    updated = manager.apply_patch(patch)
    print(f"  Updated fields: {updated}")
    print(f"  New completion: {manager.get_completion_percentage():.1f}%")

    # Test 4: Check next question after updates
    print("\nTest 4: Next question after updates...")
    next_q = manager.get_next_question()
    print(f"  Next field: {next_q['id']}")
    print(f"  Question: {next_q['question']}")

    # Test 5: Get summary
    print("\nTest 5: FNOL Summary:")
    print(manager.get_summary())

    # Test 6: Export to dict
    print("\nTest 6: Export claim data...")
    data = manager.to_dict()
    print(f"  Reporter name: {data['reporter']['full_name']}")
    print(f"  Policy number: {data['policy']['policy_number']}")
    print(f"  Loss type: {data['loss']['loss_type']}")

    print("\n" + "="*50)
    print("All FNOL module tests passed!")
    print("="*50)


if __name__ == "__main__":
    test_fnol_module()
