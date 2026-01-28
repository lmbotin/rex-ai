"""
Tests for evidence completeness and consistency checker.

Verifies that check_claim() correctly:
- Calculates completeness scores based on 3-tier evidence model
- Detects contradictions and inconsistencies
- Generates targeted follow-up questions
"""

from datetime import datetime, timedelta

import pytest

from src.fnol.checker import check_claim, CheckReport
from src.fnol.schema import (
    PropertyDamageClaim,
    ClaimantInfo,
    IncidentInfo,
    PropertyDamageInfo,
    EvidenceChecklist,
    ConsistencyFlags,
    DamageType,
    PropertyType,
    DamageSeverity,
    Provenance,
    SourceModality,
)


# ============================================================================
# Helper Functions
# ============================================================================


def create_complete_claim() -> PropertyDamageClaim:
    """Create a claim with all required evidence (100% complete)."""
    return PropertyDamageClaim(
        claim_id="TEST-001",
        claimant=ClaimantInfo(
            name="John Doe",
            policy_number="POL-123456"
        ),
        incident=IncidentInfo(
            incident_date=datetime.utcnow() - timedelta(days=5),
            incident_date_provenance=Provenance(
                source_modality=SourceModality.TEXT,
                confidence=0.9,
                pointer="text_span:0-20"
            ),
            incident_location="123 Main St, San Francisco, CA",
            incident_location_provenance=Provenance(
                source_modality=SourceModality.TEXT,
                confidence=0.85,
                pointer="text_span:21-50"
            ),
            incident_description="Pipe burst in ceiling causing water damage to living room",
            incident_description_provenance=Provenance(
                source_modality=SourceModality.TEXT,
                confidence=0.95,
                pointer="text_span:51-100"
            ),
            damage_type=DamageType.WATER,
            damage_type_provenance=Provenance(
                source_modality=SourceModality.TEXT,
                confidence=0.9,
                pointer="text_span:60-65"
            )
        ),
        property_damage=PropertyDamageInfo(
            property_type=PropertyType.CEILING,
            property_type_provenance=Provenance(
                source_modality=SourceModality.TEXT,
                confidence=0.9,
                pointer="text_span:55-62"
            ),
            room_location="living room",
            estimated_repair_cost=2500.0,
            damage_severity=DamageSeverity.MODERATE
        ),
        evidence=EvidenceChecklist(
            has_damage_photos=True,
            damage_photo_count=3,
            damage_photo_ids=["img_001.jpg", "img_002.jpg", "img_003.jpg"],
            has_repair_estimate=True
        )
    )


# ============================================================================
# Completeness Score Tests
# ============================================================================


def test_complete_claim_perfect_score():
    """Complete claim with all evidence should score 1.0."""
    claim = create_complete_claim()
    report = check_claim(claim)

    assert report.completeness_score == pytest.approx(1.0, abs=0.01)
    assert len(report.missing_required_evidence) == 0


def test_missing_all_critical_evidence():
    """Missing all critical (Tier 1) evidence should score ≤0.4."""
    claim = PropertyDamageClaim(
        claim_id="TEST-002",
        claimant=ClaimantInfo(),
        incident=IncidentInfo(
            incident_date=datetime.utcnow() - timedelta(days=5),
            incident_location="123 Main St",
            damage_type=DamageType.UNKNOWN  # Missing
        ),
        property_damage=PropertyDamageInfo(
            property_type=PropertyType.UNKNOWN,  # Missing
            estimated_repair_cost=2500.0
        ),
        evidence=EvidenceChecklist(
            has_damage_photos=False,  # Missing
            has_repair_estimate=True
        )
    )

    report = check_claim(claim)

    # Missing: damage_photos, incident_description, damage_type, property_type (all Tier 1)
    # Tier 1 = 0/4 * 0.6 = 0
    # Tier 2 = 2/3 * 0.3 = 0.2 (has location, cost, date)
    # Tier 3 = 1/3 * 0.1 = 0.033 (has estimate)
    # Total ≈ 0.233

    assert report.completeness_score <= 0.4
    assert "damage_photos" in report.missing_required_evidence
    assert "incident_description" in report.missing_required_evidence
    assert "damage_type" in report.missing_required_evidence
    assert "property_type" in report.missing_required_evidence


def test_missing_important_evidence():
    """Missing important (Tier 2) evidence should have moderate impact."""
    claim = create_complete_claim()

    # Remove Tier 2 evidence
    claim.incident.incident_location = None
    claim.incident.incident_date = None
    claim.property_damage.estimated_repair_cost = None

    report = check_claim(claim)

    # Tier 1 = 4/4 * 0.6 = 0.6
    # Tier 2 = 0/3 * 0.3 = 0
    # Tier 3 = 3/3 * 0.1 = 0.1
    # Total = 0.7

    assert report.completeness_score == pytest.approx(0.7, abs=0.01)
    assert "incident_location" in report.missing_required_evidence
    assert "incident_date" in report.missing_required_evidence
    assert "estimated_repair_cost" in report.missing_required_evidence


def test_missing_supporting_evidence():
    """Missing supporting (Tier 3) evidence should have minimal impact."""
    claim = create_complete_claim()

    # Remove Tier 3 evidence
    claim.evidence.has_repair_estimate = False
    claim.property_damage.room_location = None
    claim.evidence.damage_photo_count = 1  # <2

    report = check_claim(claim)

    # Tier 1 = 4/4 * 0.6 = 0.6
    # Tier 2 = 3/3 * 0.3 = 0.3
    # Tier 3 = 0/3 * 0.1 = 0
    # Total = 0.9

    assert report.completeness_score == pytest.approx(0.9, abs=0.01)
    assert "repair_estimate_document" in report.missing_required_evidence
    assert "room_location" in report.missing_required_evidence
    assert "multiple_photos" in report.missing_required_evidence


# ============================================================================
# Contradiction Detection Tests
# ============================================================================


def test_detect_low_confidence_critical_fields():
    """Should detect low confidence (<0.3) on critical fields."""
    claim = create_complete_claim()

    # Set low confidence on damage type
    claim.incident.damage_type_provenance.confidence = 0.2

    report = check_claim(claim)

    assert any("Low confidence on damage type" in c for c in report.contradictions)


def test_detect_severity_cost_mismatch_severe_low_cost():
    """Should detect SEVERE damage with low cost (<$1k)."""
    claim = create_complete_claim()

    claim.property_damage.damage_severity = DamageSeverity.SEVERE
    claim.property_damage.estimated_repair_cost = 500.0

    report = check_claim(claim)

    assert any("SEVERE" in c and "500" in c for c in report.contradictions)


def test_detect_severity_cost_mismatch_minor_high_cost():
    """Should detect MINOR damage with high cost (>$10k)."""
    claim = create_complete_claim()

    claim.property_damage.damage_severity = DamageSeverity.MINOR
    claim.property_damage.estimated_repair_cost = 15000.0

    report = check_claim(claim)

    assert any("MINOR" in c and "15000" in c for c in report.contradictions)


def test_detect_no_photos_but_description():
    """Should detect incident description without photos."""
    claim = create_complete_claim()

    claim.evidence.has_damage_photos = False
    claim.evidence.damage_photo_count = 0

    report = check_claim(claim)

    assert any("no damage photos" in c for c in report.contradictions)


def test_detect_high_cost_without_estimate():
    """Should detect high cost (>$5k) without repair estimate doc."""
    claim = create_complete_claim()

    claim.property_damage.estimated_repair_cost = 8000.0
    claim.evidence.has_repair_estimate = False

    report = check_claim(claim)

    assert any("8000" in c and "no repair estimate document" in c for c in report.contradictions)


def test_detect_future_incident_date():
    """Should detect incident date in the future."""
    claim = create_complete_claim()

    claim.incident.incident_date = datetime.utcnow() + timedelta(days=10)

    report = check_claim(claim)

    assert any("future" in c.lower() for c in report.contradictions)


def test_detect_old_incident_date():
    """Should detect incident date >2 years old."""
    claim = create_complete_claim()

    claim.incident.incident_date = datetime.utcnow() - timedelta(days=800)  # >2 years

    report = check_claim(claim)

    assert any("2 years old" in c for c in report.contradictions)


def test_detect_location_low_confidence():
    """Should detect location provided with low confidence."""
    claim = create_complete_claim()

    claim.incident.incident_location_provenance.confidence = 0.2

    report = check_claim(claim)

    assert any("location" in c.lower() and "low confidence" in c.lower() for c in report.contradictions)


def test_multiple_contradictions():
    """Should detect multiple contradictions in a single claim."""
    claim = create_complete_claim()

    # Add multiple issues
    claim.property_damage.damage_severity = DamageSeverity.SEVERE
    claim.property_damage.estimated_repair_cost = 500.0
    claim.evidence.has_damage_photos = False
    claim.incident.incident_date = datetime.utcnow() + timedelta(days=5)

    report = check_claim(claim)

    assert len(report.contradictions) >= 3  # Should detect at least 3 issues


# ============================================================================
# Recommended Questions Tests
# ============================================================================


def test_recommend_questions_for_missing_photos():
    """Should ask for photos when missing."""
    claim = create_complete_claim()
    claim.evidence.has_damage_photos = False
    claim.evidence.damage_photo_count = 0

    report = check_claim(claim)

    assert any("photo" in q.lower() for q in report.recommended_questions)


def test_recommend_questions_for_missing_location():
    """Should ask for location when missing."""
    claim = create_complete_claim()
    claim.incident.incident_location = None

    report = check_claim(claim)

    assert any("address" in q.lower() or "location" in q.lower() for q in report.recommended_questions)


def test_recommend_questions_for_missing_date():
    """Should ask for date when missing."""
    claim = create_complete_claim()
    claim.incident.incident_date = None

    report = check_claim(claim)

    assert any("when" in q.lower() for q in report.recommended_questions)


def test_recommend_questions_for_missing_cost():
    """Should ask for cost/estimate when missing."""
    claim = create_complete_claim()
    claim.property_damage.estimated_repair_cost = None

    report = check_claim(claim)

    assert any("estimate" in q.lower() or "cost" in q.lower() for q in report.recommended_questions)


def test_recommend_questions_for_unknown_damage_type():
    """Should ask to clarify damage type when unknown."""
    claim = create_complete_claim()
    claim.incident.damage_type = DamageType.UNKNOWN

    report = check_claim(claim)

    assert any("caused" in q.lower() or "damage" in q.lower() for q in report.recommended_questions)


def test_recommend_questions_for_unknown_severity():
    """Should ask for severity clarification when unknown."""
    claim = create_complete_claim()
    claim.property_damage.damage_severity = DamageSeverity.UNKNOWN

    report = check_claim(claim)

    assert any("severity" in q.lower() for q in report.recommended_questions)


def test_recommended_questions_limited_to_three():
    """Should limit recommended questions to 3 max."""
    claim = PropertyDamageClaim(
        claim_id="TEST-MANY-MISSING",
        claimant=ClaimantInfo(),
        incident=IncidentInfo(
            damage_type=DamageType.UNKNOWN
        ),
        property_damage=PropertyDamageInfo(
            property_type=PropertyType.UNKNOWN,
            damage_severity=DamageSeverity.UNKNOWN
        ),
        evidence=EvidenceChecklist(
            has_damage_photos=False
        )
    )

    report = check_claim(claim)

    assert len(report.recommended_questions) <= 3


def test_complete_claim_no_questions():
    """Complete claim with no issues should have no questions."""
    claim = create_complete_claim()
    report = check_claim(claim)

    # Should have no or very few questions
    assert len(report.recommended_questions) <= 1


# ============================================================================
# Edge Cases
# ============================================================================


def test_claim_with_no_provenance():
    """Should handle claim with no provenance data."""
    claim = PropertyDamageClaim(
        claim_id="TEST-NO-PROV",
        claimant=ClaimantInfo(),
        incident=IncidentInfo(
            incident_description="Water damage",
            damage_type=DamageType.WATER
        ),
        property_damage=PropertyDamageInfo(
            property_type=PropertyType.CEILING,
            estimated_repair_cost=2000.0
        ),
        evidence=EvidenceChecklist(
            has_damage_photos=True,
            damage_photo_count=2
        )
    )

    report = check_claim(claim)

    assert isinstance(report, CheckReport)
    assert 0.0 <= report.completeness_score <= 1.0


def test_empty_claim():
    """Should handle minimal/empty claim gracefully."""
    claim = PropertyDamageClaim(
        claim_id="TEST-EMPTY",
        claimant=ClaimantInfo(),
        incident=IncidentInfo(),
        property_damage=PropertyDamageInfo(),
        evidence=EvidenceChecklist()
    )

    report = check_claim(claim)

    assert isinstance(report, CheckReport)
    assert report.completeness_score < 0.5
    assert len(report.missing_required_evidence) > 0


def test_check_report_json_serializable():
    """CheckReport should be JSON serializable."""
    claim = create_complete_claim()
    report = check_claim(claim)

    # Should not raise
    json_data = report.dict()
    assert isinstance(json_data, dict)
    assert "completeness_score" in json_data
    assert "missing_required_evidence" in json_data
    assert "contradictions" in json_data
    assert "recommended_questions" in json_data


# ============================================================================
# Integration Tests
# ============================================================================


def test_detection_rate_on_known_issues():
    """Verify ≥80% detection rate on injected issues."""

    # Create claims with known issues
    test_cases = [
        ("no_photos", lambda c: setattr(c.evidence, "has_damage_photos", False)),
        ("unknown_damage_type", lambda c: setattr(c.incident, "damage_type", DamageType.UNKNOWN)),
        ("unknown_property_type", lambda c: setattr(c.property_damage, "property_type", PropertyType.UNKNOWN)),
        ("no_description", lambda c: setattr(c.incident, "incident_description", None)),
        ("no_location", lambda c: setattr(c.incident, "incident_location", None)),
        ("no_date", lambda c: setattr(c.incident, "incident_date", None)),
        ("no_cost", lambda c: setattr(c.property_damage, "estimated_repair_cost", None)),
        ("future_date", lambda c: setattr(c.incident, "incident_date", datetime.utcnow() + timedelta(days=10))),
        ("old_date", lambda c: setattr(c.incident, "incident_date", datetime.utcnow() - timedelta(days=800))),
        ("severe_low_cost", lambda c: (
            setattr(c.property_damage, "damage_severity", DamageSeverity.SEVERE),
            setattr(c.property_damage, "estimated_repair_cost", 500.0)
        )),
    ]

    detected = 0
    total = len(test_cases)

    for issue_name, inject_issue in test_cases:
        claim = create_complete_claim()
        inject_issue(claim)
        report = check_claim(claim)

        # Check if issue was detected (either in missing evidence or contradictions)
        issue_detected = (
            len(report.missing_required_evidence) > 0
            or len(report.contradictions) > 0
        )

        if issue_detected:
            detected += 1

    detection_rate = detected / total
    assert detection_rate >= 0.8, f"Detection rate {detection_rate:.2%} is below 80%"
