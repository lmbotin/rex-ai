#!/usr/bin/env python
"""
Demo script for Evidence Completeness & Consistency Checker.

Shows how to use check_claim() with various scenarios.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta

from src.fnol import check_claim
from src.fnol.schema import (
    PropertyDamageClaim,
    ClaimantInfo,
    IncidentInfo,
    PropertyDamageInfo,
    EvidenceChecklist,
    DamageType,
    PropertyType,
    DamageSeverity,
    Provenance,
    SourceModality,
)


def print_report(title: str, report):
    """Print a formatted check report."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")
    print(f"Completeness Score: {report.completeness_score:.1%}")
    print(f"\nMissing Evidence ({len(report.missing_required_evidence)}):")
    for item in report.missing_required_evidence:
        print(f"  - {item}")
    print(f"\nContradictions ({len(report.contradictions)}):")
    for contradiction in report.contradictions:
        print(f"  - {contradiction}")
    print(f"\nRecommended Questions ({len(report.recommended_questions)}):")
    for i, question in enumerate(report.recommended_questions, 1):
        print(f"  {i}. {question}")


def demo_complete_claim():
    """Demo: Complete claim with all evidence."""
    claim = PropertyDamageClaim(
        claim_id="DEMO-001",
        claimant=ClaimantInfo(name="John Doe", policy_number="POL-123456"),
        incident=IncidentInfo(
            incident_date=datetime.utcnow() - timedelta(days=2),
            incident_location="123 Main St, San Francisco, CA",
            incident_description="Pipe burst in ceiling causing water damage",
            damage_type=DamageType.WATER,
            damage_type_provenance=Provenance(
                source_modality=SourceModality.TEXT,
                confidence=0.95,
                pointer="text_span:0-50"
            )
        ),
        property_damage=PropertyDamageInfo(
            property_type=PropertyType.CEILING,
            room_location="living room",
            estimated_repair_cost=2500.0,
            damage_severity=DamageSeverity.MODERATE
        ),
        evidence=EvidenceChecklist(
            has_damage_photos=True,
            damage_photo_count=3,
            damage_photo_ids=["img1.jpg", "img2.jpg", "img3.jpg"],
            has_repair_estimate=True
        )
    )

    report = check_claim(claim)
    print_report("✅ COMPLETE CLAIM (All Evidence)", report)


def demo_missing_photos():
    """Demo: Claim missing photos."""
    claim = PropertyDamageClaim(
        claim_id="DEMO-002",
        claimant=ClaimantInfo(name="Jane Smith"),
        incident=IncidentInfo(
            incident_date=datetime.utcnow() - timedelta(days=1),
            incident_location="456 Oak Ave, Oakland, CA",
            incident_description="Window broken by baseball",
            damage_type=DamageType.IMPACT
        ),
        property_damage=PropertyDamageInfo(
            property_type=PropertyType.WINDOW,
            estimated_repair_cost=800.0,
            damage_severity=DamageSeverity.MINOR
        ),
        evidence=EvidenceChecklist(
            has_damage_photos=False,  # Missing!
            damage_photo_count=0
        )
    )

    report = check_claim(claim)
    print_report("⚠️ MISSING PHOTOS", report)


def demo_severity_mismatch():
    """Demo: Severity doesn't match cost."""
    claim = PropertyDamageClaim(
        claim_id="DEMO-003",
        claimant=ClaimantInfo(name="Bob Johnson"),
        incident=IncidentInfo(
            incident_date=datetime.utcnow() - timedelta(days=3),
            incident_location="789 Pine St, Berkeley, CA",
            incident_description="Fire damage to kitchen",
            damage_type=DamageType.FIRE
        ),
        property_damage=PropertyDamageInfo(
            property_type=PropertyType.WALL,
            estimated_repair_cost=500.0,  # Low cost
            damage_severity=DamageSeverity.SEVERE  # But severe!
        ),
        evidence=EvidenceChecklist(
            has_damage_photos=True,
            damage_photo_count=2,
            damage_photo_ids=["fire1.jpg", "fire2.jpg"]
        )
    )

    report = check_claim(claim)
    print_report("⚠️ SEVERITY-COST MISMATCH", report)


def demo_high_cost_no_estimate():
    """Demo: High cost without repair estimate document."""
    claim = PropertyDamageClaim(
        claim_id="DEMO-004",
        claimant=ClaimantInfo(name="Alice Williams"),
        incident=IncidentInfo(
            incident_date=datetime.utcnow() - timedelta(days=5),
            incident_location="321 Elm St, San Jose, CA",
            incident_description="Storm damage to roof",
            damage_type=DamageType.WEATHER
        ),
        property_damage=PropertyDamageInfo(
            property_type=PropertyType.ROOF,
            estimated_repair_cost=8000.0,  # High cost
            damage_severity=DamageSeverity.SEVERE
        ),
        evidence=EvidenceChecklist(
            has_damage_photos=True,
            damage_photo_count=5,
            damage_photo_ids=["roof1.jpg", "roof2.jpg", "roof3.jpg", "roof4.jpg", "roof5.jpg"],
            has_repair_estimate=False  # Missing estimate doc!
        )
    )

    report = check_claim(claim)
    print_report("⚠️ HIGH COST WITHOUT ESTIMATE DOC", report)


def demo_multiple_issues():
    """Demo: Claim with multiple issues."""
    claim = PropertyDamageClaim(
        claim_id="DEMO-005",
        claimant=ClaimantInfo(),
        incident=IncidentInfo(
            incident_date=datetime.utcnow() + timedelta(days=5),  # Future!
            damage_type=DamageType.UNKNOWN  # Unknown
        ),
        property_damage=PropertyDamageInfo(
            property_type=PropertyType.UNKNOWN,  # Unknown
            damage_severity=DamageSeverity.MINOR,
            estimated_repair_cost=15000.0  # High cost for minor!
        ),
        evidence=EvidenceChecklist(
            has_damage_photos=False  # No photos
        )
    )

    report = check_claim(claim)
    print_report("❌ MULTIPLE ISSUES", report)


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("EVIDENCE COMPLETENESS & CONSISTENCY CHECKER - DEMO")
    print("=" * 60)

    demo_complete_claim()
    demo_missing_photos()
    demo_severity_mismatch()
    demo_high_cost_no_estimate()
    demo_multiple_issues()

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
