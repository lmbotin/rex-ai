#!/usr/bin/env python3
"""
Test script for the property damage claim processing workflow.

Demonstrates how claims are processed through:
- Validation
- Fraud analysis
- Priority determination
- Routing decisions
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from src.routing import process_completed_call


# Sample property damage claims
SAMPLE_CLAIMS = {
    "complete_water_damage": {
        "claim_id": "CLM-2024-001",
        "claimant": {
            "name": "John Smith",
            "policy_number": "POL-123456",
            "contact_phone": "555-123-4567",
            "contact_email": "john.smith@email.com",
        },
        "incident": {
            "damage_type": "water",
            "incident_date": "2024-01-15T14:30:00Z",
            "incident_location": "123 Main St, San Francisco, CA",
            "incident_description": "Pipe burst in the ceiling causing water damage to the living room. Water leaked through the ceiling and damaged the floor and furniture.",
        },
        "property_damage": {
            "property_type": "ceiling",
            "room_location": "living room",
            "damage_severity": "moderate",
            "estimated_repair_cost": 3500.00,
        },
        "evidence": {
            "has_damage_photos": True,
            "damage_photo_count": 4,
            "has_repair_estimate": True,
            "has_incident_report": False,
        },
    },
    
    "incomplete_claim": {
        "claim_id": "CLM-2024-002",
        "claimant": {
            "name": "Jane Doe",
        },
        "incident": {
            "damage_type": "unknown",
            "incident_description": "Something happened to my wall",
        },
        "property_damage": {},
    },
    
    "suspicious_fire_claim": {
        "claim_id": "CLM-2024-003",
        "claimant": {
            "name": "Bob Wilson",
            "policy_number": "POL-999999",
            "contact_phone": "555-999-8888",
        },
        "incident": {
            "damage_type": "fire",
            "incident_date": "A few months ago, I think",
            "incident_location": "Somewhere in the city",
            "incident_description": "There was a fire. Everything is completely destroyed. I need $500,000 immediately. No witnesses. I didn't report it to anyone until now.",
        },
        "property_damage": {
            "property_type": "other",
            "damage_severity": "severe",
            "estimated_repair_cost": 500000.00,
        },
        "evidence": {
            "has_damage_photos": False,
            "has_repair_estimate": False,
            "has_incident_report": False,
        },
    },
    
    "minor_window_damage": {
        "claim_id": "CLM-2024-004",
        "claimant": {
            "name": "Sarah Johnson",
            "policy_number": "POL-456789",
            "contact_phone": "555-111-2222",
            "contact_email": "sarah.j@email.com",
        },
        "incident": {
            "damage_type": "impact",
            "incident_date": "2024-01-20T10:00:00Z",
            "incident_location": "456 Oak Ave, Apt 2B, Palo Alto, CA",
            "incident_description": "A baseball from the neighbors kids broke the living room window.",
        },
        "property_damage": {
            "property_type": "window",
            "room_location": "living room",
            "damage_severity": "minor",
            "estimated_repair_cost": 350.00,
        },
        "evidence": {
            "has_damage_photos": True,
            "damage_photo_count": 2,
            "has_repair_estimate": True,
            "has_incident_report": False,
        },
    },
    
    "severe_weather_damage": {
        "claim_id": "CLM-2024-005",
        "claimant": {
            "name": "Mike Chen",
            "policy_number": "POL-789012",
            "contact_phone": "555-333-4444",
        },
        "incident": {
            "damage_type": "weather",
            "incident_date": "2024-01-18T03:00:00Z",
            "incident_location": "789 Pine St, Mountain View, CA",
            "incident_description": "Major storm caused a tree to fall on the roof. The roof is caved in and there's water damage throughout the house. We've had to evacuate.",
        },
        "property_damage": {
            "property_type": "roof",
            "room_location": "entire house",
            "damage_severity": "severe",
            "estimated_repair_cost": 45000.00,
        },
        "evidence": {
            "has_damage_photos": True,
            "damage_photo_count": 10,
            "has_repair_estimate": False,
            "has_incident_report": True,
        },
    },
}


async def test_claim(name: str, claim_data: dict):
    """Process a single test claim."""
    print(f"\n{'='*60}")
    print(f"Processing: {name}")
    print(f"{'='*60}")
    
    result = await process_completed_call(claim_data, call_sid=f"test-{name}")
    
    print(f"\nResults:")
    print(f"  Complete: {result['is_complete']}")
    if result['missing_fields']:
        print(f"  Missing: {result['missing_fields']}")
    if result['validation_errors']:
        print(f"  Errors: {result['validation_errors']}")
    print(f"  Fraud Score: {result['fraud_score']:.2f}")
    if result['fraud_indicators']:
        print(f"  Fraud Indicators:")
        for indicator in result['fraud_indicators']:
            print(f"    - {indicator}")
    print(f"  Priority: {result['priority']}")
    print(f"  Routing: {result['routing_decision']}")
    print(f"  Reason: {result['routing_reason']}")
    print(f"  Status: {result['final_status']}")
    print(f"  Next Actions:")
    for action in result['next_actions']:
        print(f"    - {action}")
    
    return result


async def main():
    """Run all test claims."""
    print("="*60)
    print("Property Damage Claim Processing Test")
    print("="*60)
    
    results = {}
    for name, claim_data in SAMPLE_CLAIMS.items():
        results[name] = await test_claim(name, claim_data)
    
    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"{'Claim':<30} {'Routing':<20} {'Fraud':<8} {'Priority':<10}")
    print("-"*70)
    for name, result in results.items():
        print(f"{name:<30} {result['routing_decision']:<20} {result['fraud_score']:.2f}     {result['priority']:<10}")


if __name__ == "__main__":
    asyncio.run(main())
