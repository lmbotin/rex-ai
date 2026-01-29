#!/usr/bin/env python3
"""
Gana Insurance - FNOL Demo Script

Demonstrates all three claim input modalities:
1. Text Claims - Extract from written descriptions
2. Image Claims - Analyze damage photos
3. Voice Claims - Simulate voice conversation intake

Run with: python demo.py

Claims are automatically saved to: data/claims.db
View saved claims with: python view_claims.py
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import storage
from src.storage import save_claim, get_claim_store


def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_subheader(title: str):
    """Print a formatted subsection header."""
    print(f"\n--- {title} ---")


def print_claim_summary(claim, source: str):
    """Print a nicely formatted claim summary."""
    print(f"\n{'─' * 50}")
    print(f"Source: {source}")
    print(f"{'─' * 50}")
    
    # Claimant Info
    if claim.claimant:
        print(f"  Claimant: {claim.claimant.name or 'Unknown'}")
        if claim.claimant.policy_number:
            print(f"  Policy #: {claim.claimant.policy_number}")
        if claim.claimant.contact_phone:
            print(f"  Phone: {claim.claimant.contact_phone}")
    
    # Incident Info
    if claim.incident:
        print(f"\n  Damage Type: {claim.incident.damage_type or 'Unknown'}")
        if claim.incident.incident_date:
            print(f"  Date: {claim.incident.incident_date}")
        if claim.incident.incident_location:
            print(f"  Location: {claim.incident.incident_location}")
        if claim.incident.incident_description:
            desc = claim.incident.incident_description[:100]
            if len(claim.incident.incident_description) > 100:
                desc += "..."
            print(f"  Description: {desc}")
    
    # Property Damage
    if claim.property_damage:
        print(f"\n  Property Type: {claim.property_damage.property_type or 'Unknown'}")
        if claim.property_damage.room_location:
            print(f"  Room/Area: {claim.property_damage.room_location}")
        if claim.property_damage.damage_severity:
            print(f"  Severity: {claim.property_damage.damage_severity}")
        if claim.property_damage.estimated_repair_cost:
            print(f"  Est. Cost: ${claim.property_damage.estimated_repair_cost:,.2f}")
    
    # Evidence
    if claim.evidence:
        evidence_items = []
        if claim.evidence.has_damage_photos:
            evidence_items.append(f"Photos ({claim.evidence.damage_photo_count})")
        if claim.evidence.has_repair_estimate:
            evidence_items.append("Repair Estimate")
        if claim.evidence.has_incident_report:
            evidence_items.append("Incident Report")
        if evidence_items:
            print(f"\n  Evidence: {', '.join(evidence_items)}")


def print_check_report(report):
    """Print claim validation report."""
    print(f"\n  Completeness Score: {report.completeness_score:.0%}")
    
    if report.missing_required_evidence:
        print(f"  Missing Required: {', '.join(report.missing_required_evidence[:5])}")
    
    if report.contradictions:
        print(f"  Contradictions: {', '.join(report.contradictions)}")
    
    if report.recommended_questions:
        print("  Suggested Questions:")
        for q in report.recommended_questions[:3]:
            print(f"    - {q}")


# =============================================================================
# DEMO 1: TEXT CLAIMS
# =============================================================================

def demo_text_claims():
    """Demonstrate text-based claim extraction."""
    print_header("DEMO 1: TEXT CLAIMS")
    print("Extracting structured data from written claim descriptions...")
    
    from src.fnol import parse_claim, check_claim
    
    # Load sample text claims
    fixtures_dir = Path("fixtures")
    text_files = [
        ("Complete Water Damage", "claim01_water_damage.txt"),
        ("Minimal Info (Edge Case)", "claim06_minimal_info.txt"),
        ("Fire Damage (Detailed)", "claim03_fire_damage.txt"),
    ]
    
    results = []
    
    for name, filename in text_files:
        filepath = fixtures_dir / filename
        if filepath.exists():
            print_subheader(f"Processing: {name}")
            
            with open(filepath) as f:
                text = f.read()
            
            print(f"Input text preview: {text[:150]}...")
            
            # Extract claim
            claim = parse_claim(text=text, image_paths=[])
            
            # Print summary
            print_claim_summary(claim, f"Text: {filename}")
            
            # Validate
            report = check_claim(claim)
            print_check_report(report)
            
            # Save to database
            claim_id = save_claim(claim.model_dump(), source="text")
            print(f"\n  ✓ Saved to database: {claim_id}")
            
            results.append({
                "name": name,
                "claim": claim,
                "report": report,
                "claim_id": claim_id
            })
        else:
            print(f"  [Skipped] File not found: {filepath}")
    
    return results


# =============================================================================
# DEMO 2: IMAGE CLAIMS
# =============================================================================

def demo_image_claims():
    """Demonstrate image-based claim analysis."""
    print_header("DEMO 2: IMAGE CLAIMS")
    print("Analyzing damage photos and combining with text descriptions...")
    
    from src.fnol import parse_claim, check_claim
    
    fixtures_dir = Path("fixtures")
    
    # Test cases with images
    test_cases = [
        {
            "name": "Water Damage + Photos",
            "text": "claim01_water_damage.txt",
            "images": ["damage_ceiling.jpg", "damage_photo1.jpg"]
        },
        {
            "name": "Fire Damage + Photos",
            "text": "claim03_fire_damage.txt", 
            "images": ["fire_damage1.jpg", "fire_damage2.jpg"]
        },
        {
            "name": "Broken Window + Photo",
            "text": "claim02_broken_window.txt",
            "images": ["broken_window.jpg"]
        },
    ]
    
    results = []
    
    for case in test_cases:
        print_subheader(f"Processing: {case['name']}")
        
        # Load text
        text_path = fixtures_dir / case["text"]
        if text_path.exists():
            with open(text_path) as f:
                text = f.read()
        else:
            text = ""
        
        # Find images
        image_paths = []
        for img in case["images"]:
            img_path = fixtures_dir / img
            if img_path.exists():
                image_paths.append(str(img_path))
                print(f"  Image: {img}")
        
        if not image_paths:
            print("  [No images found - skipping]")
            continue
        
        # Extract claim
        claim = parse_claim(text=text, image_paths=image_paths)
        
        # Print summary
        print_claim_summary(claim, f"Text + {len(image_paths)} images")
        
        # Validate
        report = check_claim(claim)
        print_check_report(report)
        
        # Save to database
        claim_id = save_claim(claim.model_dump(), source="image")
        print(f"\n  ✓ Saved to database: {claim_id}")
        
        results.append({
            "name": case["name"],
            "claim": claim,
            "report": report,
            "claim_id": claim_id
        })
    
    return results


# =============================================================================
# DEMO 3: VOICE/CALL CLAIMS (Simulated)
# =============================================================================

def demo_voice_claims():
    """Demonstrate voice-based claim intake (simulated conversation)."""
    print_header("DEMO 3: VOICE CLAIMS (Simulated)")
    print("Simulating a voice conversation for claim intake...")
    print("(In production, this would be a real phone call via Twilio + OpenAI Realtime)")
    
    from src.fnol import PropertyClaimStateManager, check_claim
    
    # Simulate a conversation
    conversation_turns = [
        # Turn 1: Name
        {"claimant.name": "Maria Garcia"},
        
        # Turn 2: Policy number
        {"claimant.policy_number": "POL-789456"},
        
        # Turn 3: What happened
        {
            "incident.damage_type": "water",
            "incident.incident_description": "A pipe burst under my kitchen sink and flooded the floor"
        },
        
        # Turn 4: When
        {"incident.incident_date": "2024-01-25"},
        
        # Turn 5: Where
        {"incident.incident_location": "456 Elm Street, Apt 3A, Oakland, CA"},
        
        # Turn 6: Property details
        {
            "property_damage.property_type": "floor",
            "property_damage.room_location": "kitchen",
            "property_damage.damage_severity": "moderate"
        },
        
        # Turn 7: Cost estimate
        {"property_damage.estimated_repair_cost": 1800.00},
        
        # Turn 8: Contact
        {"claimant.contact_phone": "510-555-1234"},
    ]
    
    # Create state manager (simulates voice agent's state tracking)
    manager = PropertyClaimStateManager()
    
    print_subheader("Simulated Conversation")
    
    for i, turn_data in enumerate(conversation_turns, 1):
        # Apply the extracted data from this "turn"
        manager.apply_patch(turn_data)
        
        # Get current state
        completion = manager.get_completion_percentage()
        next_q = manager.get_next_question()
        
        # Display
        print(f"\n  Turn {i}:")
        print(f"    Extracted: {list(turn_data.keys())}")
        print(f"    Completion: {completion:.0f}%")
        if next_q and next_q.get("id") != "complete":
            print(f"    Next question: {next_q.get('question', 'N/A')[:60]}...")
    
    # Get final claim
    claim = manager.claim
    
    print_subheader("Final Extracted Claim")
    print_claim_summary(claim, "Voice conversation (8 turns)")
    
    # Validate
    report = check_claim(claim)
    print_check_report(report)
    
    # Save to database
    claim_id = save_claim(claim.model_dump(), source="voice", call_sid="demo-voice-001")
    print(f"\n  ✓ Saved to database: {claim_id}")
    
    return [{
        "name": "Voice Conversation",
        "claim": claim,
        "report": report,
        "claim_id": claim_id
    }]


# =============================================================================
# DEMO 4: FULL WORKFLOW (Validation → Fraud → Routing)
# =============================================================================

async def demo_full_workflow():
    """Demonstrate the complete claim processing workflow."""
    print_header("DEMO 4: FULL PROCESSING WORKFLOW")
    print("Processing a claim through: Validation → Fraud Analysis → Routing")
    
    from src.routing import process_completed_call
    
    # Sample claim data (as would come from voice/text extraction)
    claim_data = {
        "claim_id": f"CLM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "claimant": {
            "name": "Robert Chen",
            "policy_number": "POL-555123",
            "contact_phone": "415-555-9876",
            "contact_email": "r.chen@email.com",
        },
        "incident": {
            "damage_type": "weather",
            "incident_date": "2024-01-20T02:00:00Z",
            "incident_location": "789 Pine Ave, San Jose, CA",
            "incident_description": "Major storm caused a tree branch to crash through the bedroom window. Rain got in and damaged the carpet and wall.",
        },
        "property_damage": {
            "property_type": "window",
            "room_location": "master bedroom",
            "damage_severity": "moderate",
            "estimated_repair_cost": 4200.00,
        },
        "evidence": {
            "has_damage_photos": True,
            "damage_photo_count": 5,
            "has_repair_estimate": True,
            "has_incident_report": False,
        },
    }
    
    print_subheader("Input Claim")
    print(f"  Claimant: {claim_data['claimant']['name']}")
    print(f"  Damage: {claim_data['incident']['damage_type']}")
    print(f"  Est. Cost: ${claim_data['property_damage']['estimated_repair_cost']:,.2f}")
    
    # Save claim first
    store = get_claim_store()
    claim_id = store.save(claim_data, source="multimodal")
    print(f"\n  ✓ Saved to database: {claim_id}")
    
    # Process through full workflow
    print_subheader("Processing...")
    result = await process_completed_call(claim_data, call_sid="demo-001")
    
    print_subheader("Workflow Results")
    print("\n  1. VALIDATION")
    print(f"     Complete: {result['is_complete']}")
    if result['missing_fields']:
        print(f"     Missing: {', '.join(result['missing_fields'][:5])}")
    if result['validation_errors']:
        print(f"     Errors: {', '.join(result['validation_errors'])}")
    
    print("\n  2. FRAUD ANALYSIS")
    print(f"     Fraud Score: {result['fraud_score']:.2f} (0=clean, 1=suspicious)")
    if result['fraud_indicators']:
        print("     Indicators:")
        for indicator in result['fraud_indicators'][:3]:
            print(f"       - {indicator}")
    else:
        print("     No fraud indicators detected")
    
    print("\n  3. PRIORITY")
    print(f"     Level: {result['priority']}")
    
    print("\n  4. ROUTING DECISION")
    print(f"     Route: {result['routing_decision']}")
    print(f"     Reason: {result['routing_reason']}")
    
    print("\n  5. FINAL STATUS")
    print(f"     Status: {result['final_status']}")
    print("     Next Actions:")
    for action in result['next_actions']:
        print(f"       → {action}")
    
    # Save processing results to database
    store.save_processing_result(
        claim_id,
        validation_result={
            "is_complete": result["is_complete"],
            "missing_fields": result["missing_fields"],
            "errors": result["validation_errors"],
        },
        fraud_result={
            "score": result["fraud_score"],
            "indicators": result["fraud_indicators"],
        },
        routing_result={
            "decision": result["routing_decision"],
            "reason": result["routing_reason"],
            "priority": result["priority"],
        },
    )
    store.update_status(claim_id, result["final_status"])
    print("\n  ✓ Processing results saved to database")
    
    return result


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run all demos."""
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "       GANA INSURANCE - FNOL CLAIM PROCESSING DEMO".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    
    print("\nThis demo showcases three claim input modalities:")
    print("  1. Text Claims    - Written descriptions")
    print("  2. Image Claims   - Damage photos + text")
    print("  3. Voice Claims   - Phone conversation (simulated)")
    print("  4. Full Workflow  - Validation → Fraud → Routing")
    
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "test-key-for-import-only":
        print("\n⚠️  WARNING: No OPENAI_API_KEY found in environment.")
        print("   Some features may not work. Set it in .env file.")
    
    try:
        # Demo 1: Text
        demo_text_claims()
        
        # Demo 2: Images
        demo_image_claims()
        
        # Demo 3: Voice (simulated)
        demo_voice_claims()
        
        # Demo 4: Full workflow
        asyncio.run(demo_full_workflow())
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("  1. Installed dependencies: pip install -r requirements.txt")
        print("  2. Set OPENAI_API_KEY in .env file")
        raise
    
    print_header("DEMO COMPLETE")
    print("\nTo run with your own data:")
    print("  - Text: python -m src.fnol --text-file your_claim.txt")
    print("  - Images: python -m src.fnol --images photo1.jpg photo2.jpg")
    print("  - Voice: python run_voice_agent.py (requires Twilio setup)")
    print("\nSee README.md for more details.")


if __name__ == "__main__":
    main()
