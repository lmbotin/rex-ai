"""
Tests for Property Damage Claim schema.

Tests 20+ synthetic claims with various scenarios:
- Complete claims with all fields
- Missing evidence
- Conflicting evidence
- Edge cases
- Invalid data
"""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.fnol.schema import (
    ClaimantInfo,
    ConsistencyFlags,
    DamageSeverity,
    DamageType,
    EvidenceChecklist,
    IncidentInfo,
    PropertyDamageClaim,
    PropertyDamageInfo,
    PropertyType,
    Provenance,
    SourceModality,
)


# ============================================================================
# Helper Functions
# ============================================================================


def create_provenance(modality: SourceModality, confidence: float, pointer: str) -> Provenance:
    """Helper to create provenance objects."""
    return Provenance(source_modality=modality, confidence=confidence, pointer=pointer)


# ============================================================================
# Test: Valid Claims (20 synthetic examples)
# ============================================================================


class TestValidClaims:
    """Test valid claim scenarios that should pass validation."""

    def test_claim_01_complete_water_damage(self):
        """Complete claim: water damage with all fields populated."""
        claim = PropertyDamageClaim(
            claim_id="CLM-001",
            claimant=ClaimantInfo(
                name="Alice Smith",
                policy_number="POL-001234",
                contact_phone="+1-555-0101",
                contact_email="alice@example.com"
            ),
            incident=IncidentInfo(
                incident_date=datetime(2024, 1, 15, 14, 30),
                incident_date_provenance=create_provenance(SourceModality.TEXT, 0.95, "text_span:0-20"),
                incident_location="123 Oak St, Apt 2B, San Francisco, CA",
                incident_location_provenance=create_provenance(SourceModality.TEXT, 0.98, "text_span:21-65"),
                incident_description="Pipe burst in bathroom ceiling causing water damage to living room",
                incident_description_provenance=create_provenance(SourceModality.TEXT, 0.99, "text_span:66-140"),
                damage_type=DamageType.WATER,
                damage_type_provenance=create_provenance(SourceModality.TEXT, 0.97, "text_span:66-76")
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.CEILING,
                property_type_provenance=create_provenance(SourceModality.IMAGE, 0.92, "image_id:img_001"),
                room_location="living room",
                room_location_provenance=create_provenance(SourceModality.TEXT, 0.96, "text_span:120-131"),
                estimated_repair_cost=2500.00,
                estimated_repair_cost_provenance=create_provenance(SourceModality.DOCUMENT, 0.99, "doc_page:1"),
                damage_severity=DamageSeverity.MODERATE,
                damage_severity_provenance=create_provenance(SourceModality.IMAGE, 0.88, "image_id:img_001")
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=3,
                damage_photo_ids=["img_001.jpg", "img_002.jpg", "img_003.jpg"],
                has_repair_estimate=True,
                has_incident_report=False,
                missing_evidence=["incident_report"]
            ),
            consistency=ConsistencyFlags(has_conflicts=False, conflict_details=[])
        )
        assert claim.claim_id == "CLM-001"
        assert claim.claimant.name == "Alice Smith"
        assert claim.incident.damage_type == DamageType.WATER
        assert claim.property_damage.estimated_repair_cost == 2500.00
        assert len(claim.get_missing_evidence()) == 1
        assert not claim.has_consistency_issues()

    def test_claim_02_complete_fire_damage(self):
        """Complete claim: fire damage to kitchen."""
        claim = PropertyDamageClaim(
            claim_id="CLM-002",
            claimant=ClaimantInfo(
                name="Bob Johnson",
                policy_number="POL-005678",
                contact_phone="+1-555-0102"
            ),
            incident=IncidentInfo(
                incident_date=datetime(2024, 2, 3, 8, 15),
                incident_location="456 Elm Ave, Oakland, CA",
                incident_description="Stove fire caused damage to kitchen cabinets and ceiling",
                damage_type=DamageType.FIRE
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.APPLIANCE,
                room_location="kitchen",
                estimated_repair_cost=8500.00,
                damage_severity=DamageSeverity.SEVERE
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=5,
                damage_photo_ids=["fire_01.jpg", "fire_02.jpg", "fire_03.jpg", "fire_04.jpg", "fire_05.jpg"],
                has_repair_estimate=True,
                has_incident_report=True,
                missing_evidence=[]
            )
        )
        assert claim.claim_id == "CLM-002"
        assert claim.incident.damage_type == DamageType.FIRE
        assert claim.property_damage.damage_severity == DamageSeverity.SEVERE
        assert len(claim.get_missing_evidence()) == 0

    def test_claim_03_minimal_required_fields(self):
        """Minimal claim: only required fields populated."""
        claim = PropertyDamageClaim(
            claim_id="CLM-003",
            claimant=ClaimantInfo(),
            incident=IncidentInfo(),
            property_damage=PropertyDamageInfo(),
            evidence=EvidenceChecklist()
        )
        assert claim.claim_id == "CLM-003"
        assert claim.incident.damage_type == DamageType.UNKNOWN
        assert claim.property_damage.property_type == PropertyType.UNKNOWN

    def test_claim_04_broken_window(self):
        """Impact damage: broken window."""
        claim = PropertyDamageClaim(
            claim_id="CLM-004",
            claimant=ClaimantInfo(name="Carol White", policy_number="POL-009999"),
            incident=IncidentInfo(
                incident_date=datetime(2024, 3, 10, 16, 45),
                incident_location="789 Pine St, Berkeley, CA",
                incident_description="Baseball broke living room window",
                damage_type=DamageType.IMPACT
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.WINDOW,
                room_location="living room",
                estimated_repair_cost=450.00,
                damage_severity=DamageSeverity.MINOR
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=2,
                damage_photo_ids=["window_01.jpg", "window_02.jpg"],
                has_repair_estimate=True,
                missing_evidence=[]
            )
        )
        assert claim.incident.damage_type == DamageType.IMPACT
        assert claim.property_damage.estimated_repair_cost == 450.00

    def test_claim_05_weather_roof_damage(self):
        """Weather damage: storm damaged roof."""
        claim = PropertyDamageClaim(
            claim_id="CLM-005",
            claimant=ClaimantInfo(name="David Lee", policy_number="POL-111222"),
            incident=IncidentInfo(
                incident_date=datetime(2024, 1, 20, 3, 0),
                incident_location="321 Maple Dr, San Jose, CA",
                incident_description="Strong winds during storm damaged roof shingles",
                damage_type=DamageType.WEATHER
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.ROOF,
                estimated_repair_cost=5200.00,
                damage_severity=DamageSeverity.MODERATE
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=4,
                damage_photo_ids=["roof_01.jpg", "roof_02.jpg", "roof_03.jpg", "roof_04.jpg"],
                has_repair_estimate=False,
                missing_evidence=["repair_estimate"]
            )
        )
        assert claim.incident.damage_type == DamageType.WEATHER
        assert claim.property_damage.property_type == PropertyType.ROOF

    def test_claim_06_vandalism_door(self):
        """Vandalism: damaged front door."""
        claim = PropertyDamageClaim(
            claim_id="CLM-006",
            claimant=ClaimantInfo(name="Emma Davis"),
            incident=IncidentInfo(
                incident_date=datetime(2024, 2, 14, 23, 30),
                incident_location="555 Birch Ln, Palo Alto, CA",
                incident_description="Front door kicked in, lock damaged",
                damage_type=DamageType.VANDALISM
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.DOOR,
                room_location="front entrance",
                estimated_repair_cost=1200.00,
                damage_severity=DamageSeverity.MODERATE
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=3,
                damage_photo_ids=["door_01.jpg", "door_02.jpg", "door_03.jpg"],
                has_incident_report=True,
                missing_evidence=["repair_estimate"]
            )
        )
        assert claim.incident.damage_type == DamageType.VANDALISM

    def test_claim_07_floor_water_damage(self):
        """Water damage to hardwood floor."""
        claim = PropertyDamageClaim(
            claim_id="CLM-007",
            claimant=ClaimantInfo(name="Frank Miller", policy_number="POL-333444"),
            incident=IncidentInfo(
                incident_date=datetime(2024, 3, 5, 12, 0),
                incident_location="888 Cedar Ct, Mountain View, CA",
                incident_description="Dishwasher leaked overnight, damaged hardwood floor",
                damage_type=DamageType.WATER
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.FLOOR,
                room_location="kitchen",
                estimated_repair_cost=3100.00,
                damage_severity=DamageSeverity.MODERATE
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=4,
                damage_photo_ids=["floor_01.jpg", "floor_02.jpg", "floor_03.jpg", "floor_04.jpg"],
                has_repair_estimate=True
            )
        )
        assert claim.property_damage.property_type == PropertyType.FLOOR

    def test_claim_08_wall_impact_damage(self):
        """Impact damage to wall."""
        claim = PropertyDamageClaim(
            claim_id="CLM-008",
            claimant=ClaimantInfo(name="Grace Chen", policy_number="POL-555666"),
            incident=IncidentInfo(
                incident_date=datetime(2024, 2, 28, 10, 30),
                incident_description="Moving furniture, accidentally put hole in drywall",
                damage_type=DamageType.IMPACT
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.WALL,
                room_location="bedroom",
                estimated_repair_cost=250.00,
                damage_severity=DamageSeverity.MINOR
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=1,
                damage_photo_ids=["wall_01.jpg"]
            )
        )
        assert claim.property_damage.damage_severity == DamageSeverity.MINOR

    def test_claim_09_other_damage_type(self):
        """Other damage type."""
        claim = PropertyDamageClaim(
            claim_id="CLM-009",
            claimant=ClaimantInfo(name="Henry Wong"),
            incident=IncidentInfo(
                incident_description="Smoke damage from neighbor's fire",
                damage_type=DamageType.OTHER
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.CEILING,
                estimated_repair_cost=1800.00
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=2
            )
        )
        assert claim.incident.damage_type == DamageType.OTHER

    def test_claim_10_furniture_damage(self):
        """Water damage to furniture."""
        claim = PropertyDamageClaim(
            claim_id="CLM-010",
            claimant=ClaimantInfo(name="Iris Taylor", policy_number="POL-777888"),
            incident=IncidentInfo(
                incident_date=datetime(2024, 3, 12, 7, 0),
                incident_location="999 Willow Rd, Sunnyvale, CA",
                incident_description="Roof leak during rain damaged bedroom furniture",
                damage_type=DamageType.WATER
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.FURNITURE,
                room_location="bedroom",
                estimated_repair_cost=1500.00,
                damage_severity=DamageSeverity.MODERATE
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=3,
                damage_photo_ids=["furniture_01.jpg", "furniture_02.jpg", "furniture_03.jpg"]
            )
        )
        assert claim.property_damage.property_type == PropertyType.FURNITURE

    def test_claim_11_unknown_fields(self):
        """Claim with unknown damage type and property type."""
        claim = PropertyDamageClaim(
            claim_id="CLM-011",
            claimant=ClaimantInfo(name="Jack Brown"),
            incident=IncidentInfo(
                incident_description="Unclear what caused the damage",
                damage_type=DamageType.UNKNOWN
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.UNKNOWN,
                damage_severity=DamageSeverity.UNKNOWN
            ),
            evidence=EvidenceChecklist()
        )
        assert claim.incident.damage_type == DamageType.UNKNOWN
        assert claim.property_damage.property_type == PropertyType.UNKNOWN

    def test_claim_12_missing_all_evidence(self):
        """Claim with no evidence provided."""
        claim = PropertyDamageClaim(
            claim_id="CLM-012",
            claimant=ClaimantInfo(name="Karen Wilson", policy_number="POL-999000"),
            incident=IncidentInfo(
                incident_date=datetime(2024, 3, 1, 14, 0),
                incident_description="Hail damage to roof",
                damage_type=DamageType.WEATHER
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.ROOF,
                estimated_repair_cost=4200.00
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=False,
                has_repair_estimate=False,
                has_incident_report=False,
                missing_evidence=["damage_photos", "repair_estimate", "incident_report"]
            )
        )
        assert len(claim.get_missing_evidence()) == 3

    def test_claim_13_with_conflicts(self):
        """Claim with consistency conflicts flagged."""
        claim = PropertyDamageClaim(
            claim_id="CLM-013",
            claimant=ClaimantInfo(name="Laura Martinez", policy_number="POL-222333"),
            incident=IncidentInfo(
                incident_date=datetime(2024, 1, 10, 9, 0),
                incident_description="Water damage from burst pipe",
                damage_type=DamageType.WATER
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.CEILING,
                estimated_repair_cost=3000.00
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=2
            ),
            consistency=ConsistencyFlags(
                has_conflicts=True,
                conflict_details=[
                    "date mismatch: text says Jan 10, image EXIF says Jan 8",
                    "location mismatch: text says 'ceiling', image shows floor damage"
                ]
            )
        )
        assert claim.has_consistency_issues()
        assert len(claim.get_consistency_issues()) == 2

    def test_claim_14_zero_cost_estimate(self):
        """Claim with zero cost estimate (valid edge case)."""
        claim = PropertyDamageClaim(
            claim_id="CLM-014",
            claimant=ClaimantInfo(name="Mike Anderson"),
            incident=IncidentInfo(
                incident_description="Minor scratch, no repair needed",
                damage_type=DamageType.IMPACT
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.WALL,
                estimated_repair_cost=0.0,
                damage_severity=DamageSeverity.MINOR
            ),
            evidence=EvidenceChecklist(has_damage_photos=True, damage_photo_count=1)
        )
        assert claim.property_damage.estimated_repair_cost == 0.0

    def test_claim_15_high_cost_severe_damage(self):
        """Claim with high cost and severe damage."""
        claim = PropertyDamageClaim(
            claim_id="CLM-015",
            claimant=ClaimantInfo(name="Nancy Garcia", policy_number="POL-444555"),
            incident=IncidentInfo(
                incident_date=datetime(2024, 2, 20, 4, 30),
                incident_location="111 Spruce Ave, Fremont, CA",
                incident_description="Major fire in kitchen, extensive damage",
                damage_type=DamageType.FIRE
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.OTHER,
                room_location="kitchen",
                estimated_repair_cost=25000.00,
                damage_severity=DamageSeverity.SEVERE
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=10,
                has_repair_estimate=True,
                has_incident_report=True
            )
        )
        assert claim.property_damage.estimated_repair_cost == 25000.00

    def test_claim_16_all_provenance_fields(self):
        """Claim with provenance for all extracted fields."""
        claim = PropertyDamageClaim(
            claim_id="CLM-016",
            claimant=ClaimantInfo(name="Oscar Lee", policy_number="POL-666777"),
            incident=IncidentInfo(
                incident_date=datetime(2024, 3, 15, 11, 20),
                incident_date_provenance=create_provenance(SourceModality.TEXT, 0.94, "text_span:0-25"),
                incident_location="222 Ash St, Cupertino, CA",
                incident_location_provenance=create_provenance(SourceModality.TEXT, 0.97, "text_span:26-55"),
                incident_description="Washing machine overflow caused water damage",
                incident_description_provenance=create_provenance(SourceModality.TEXT, 0.98, "text_span:56-105"),
                damage_type=DamageType.WATER,
                damage_type_provenance=create_provenance(SourceModality.TEXT, 0.96, "text_span:79-84")
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.FLOOR,
                property_type_provenance=create_provenance(SourceModality.IMAGE, 0.91, "image_id:img_001"),
                room_location="laundry room",
                room_location_provenance=create_provenance(SourceModality.TEXT, 0.95, "text_span:56-68"),
                estimated_repair_cost=1800.00,
                estimated_repair_cost_provenance=create_provenance(SourceModality.DOCUMENT, 0.99, "doc_page:1"),
                damage_severity=DamageSeverity.MODERATE,
                damage_severity_provenance=create_provenance(SourceModality.IMAGE, 0.87, "image_id:img_002")
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=2,
                has_repair_estimate=True
            )
        )
        assert claim.incident.incident_date_provenance.confidence == 0.94
        assert claim.property_damage.estimated_repair_cost_provenance.source_modality == SourceModality.DOCUMENT

    def test_claim_17_no_optional_fields(self):
        """Claim with no optional fields populated."""
        claim = PropertyDamageClaim(
            claim_id="CLM-017",
            claimant=ClaimantInfo(),
            incident=IncidentInfo(damage_type=DamageType.OTHER),
            property_damage=PropertyDamageInfo(property_type=PropertyType.OTHER),
            evidence=EvidenceChecklist()
        )
        assert claim.claimant.name is None
        assert claim.incident.incident_date is None
        assert claim.property_damage.estimated_repair_cost is None

    def test_claim_18_special_characters(self):
        """Claim with special characters in text fields."""
        claim = PropertyDamageClaim(
            claim_id="CLM-018-ÄÖÜ",
            claimant=ClaimantInfo(
                name="José García-López",
                contact_email="josé.garcía@example.com"
            ),
            incident=IncidentInfo(
                incident_location="123 Rue d'Étoile, Apt #4, São Paulo",
                incident_description="Water damage: pipe burst → flooding (5-10 gallons)",
                damage_type=DamageType.WATER
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.FLOOR,
                room_location="salle de séjour"
            ),
            evidence=EvidenceChecklist()
        )
        assert "García" in claim.claimant.name

    def test_claim_19_long_description(self):
        """Claim with long, detailed description."""
        long_desc = (
            "On the morning of January 15th, 2024, I woke up to discover significant water damage "
            "in my living room. The ceiling had multiple brown water stains, and there was active "
            "dripping from two locations near the light fixture. Upon investigation, I found that "
            "the upstairs bathroom had a leaking pipe that had been dripping for an unknown period. "
            "The water had soaked through the ceiling drywall, causing it to sag and deteriorate. "
            "I immediately turned off the water supply and contacted a plumber. The plumber confirmed "
            "that the pipe had corroded and burst. I also noticed that the water had damaged the "
            "hardwood floor near the couch and the paint on the walls was starting to peel."
        )
        claim = PropertyDamageClaim(
            claim_id="CLM-019",
            claimant=ClaimantInfo(name="Paula Rodriguez", policy_number="POL-888999"),
            incident=IncidentInfo(
                incident_date=datetime(2024, 1, 15, 6, 30),
                incident_location="333 Redwood Dr, Santa Clara, CA",
                incident_description=long_desc,
                damage_type=DamageType.WATER
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.CEILING,
                room_location="living room",
                estimated_repair_cost=4500.00,
                damage_severity=DamageSeverity.SEVERE
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=6,
                has_repair_estimate=True,
                has_incident_report=False,
                missing_evidence=["incident_report"]
            )
        )
        assert len(claim.incident.incident_description) > 500

    def test_claim_20_json_serialization(self):
        """Test that claim can be serialized to/from JSON."""
        claim = PropertyDamageClaim(
            claim_id="CLM-020",
            claimant=ClaimantInfo(name="Quinn Thompson", policy_number="POL-000111"),
            incident=IncidentInfo(
                incident_date=datetime(2024, 3, 20, 15, 45),
                incident_description="Storm damage to roof",
                damage_type=DamageType.WEATHER
            ),
            property_damage=PropertyDamageInfo(
                property_type=PropertyType.ROOF,
                estimated_repair_cost=3800.00,
                damage_severity=DamageSeverity.MODERATE
            ),
            evidence=EvidenceChecklist(
                has_damage_photos=True,
                damage_photo_count=4
            )
        )

        # Serialize to JSON
        json_str = claim.json()
        json_dict = json.loads(json_str)

        # Deserialize from JSON
        claim_restored = PropertyDamageClaim.parse_obj(json_dict)

        assert claim_restored.claim_id == claim.claim_id
        assert claim_restored.claimant.name == claim.claimant.name
        assert claim_restored.property_damage.estimated_repair_cost == claim.property_damage.estimated_repair_cost


# ============================================================================
# Test: Invalid Claims (should fail validation)
# ============================================================================


class TestInvalidClaims:
    """Test invalid claims that should fail validation."""

    def test_invalid_empty_claim_id(self):
        """Empty claim_id should fail validation."""
        with pytest.raises(ValidationError, match="claim_id cannot be empty"):
            PropertyDamageClaim(
                claim_id="",
                claimant=ClaimantInfo(),
                incident=IncidentInfo(),
                property_damage=PropertyDamageInfo(),
                evidence=EvidenceChecklist()
            )

    def test_invalid_whitespace_claim_id(self):
        """Whitespace-only claim_id should fail validation."""
        with pytest.raises(ValidationError, match="claim_id cannot be empty"):
            PropertyDamageClaim(
                claim_id="   ",
                claimant=ClaimantInfo(),
                incident=IncidentInfo(),
                property_damage=PropertyDamageInfo(),
                evidence=EvidenceChecklist()
            )

    def test_invalid_negative_cost(self):
        """Negative repair cost should fail validation."""
        with pytest.raises(ValidationError, match="ensure this value is greater than or equal to 0"):
            PropertyDamageClaim(
                claim_id="CLM-INVALID-1",
                claimant=ClaimantInfo(),
                incident=IncidentInfo(),
                property_damage=PropertyDamageInfo(estimated_repair_cost=-100.0),
                evidence=EvidenceChecklist()
            )

    def test_invalid_negative_photo_count(self):
        """Negative photo count should fail validation."""
        with pytest.raises(ValidationError, match="ensure this value is greater than or equal to 0"):
            PropertyDamageClaim(
                claim_id="CLM-INVALID-2",
                claimant=ClaimantInfo(),
                incident=IncidentInfo(),
                property_damage=PropertyDamageInfo(),
                evidence=EvidenceChecklist(damage_photo_count=-1)
            )

    def test_invalid_confidence_too_high(self):
        """Confidence > 1.0 should fail validation."""
        with pytest.raises(ValidationError, match="ensure this value is less than or equal to 1.0"):
            create_provenance(SourceModality.TEXT, 1.5, "text_span:0-10")

    def test_invalid_confidence_negative(self):
        """Negative confidence should fail validation."""
        with pytest.raises(ValidationError, match="ensure this value is greater than or equal to 0.0"):
            create_provenance(SourceModality.TEXT, -0.1, "text_span:0-10")


# ============================================================================
# Test: Schema Export
# ============================================================================


class TestSchemaExport:
    """Test JSON Schema export functionality."""

    def test_export_json_schema(self):
        """Test that we can export JSON Schema."""
        claim = PropertyDamageClaim(
            claim_id="CLM-SCHEMA",
            claimant=ClaimantInfo(),
            incident=IncidentInfo(),
            property_damage=PropertyDamageInfo(),
            evidence=EvidenceChecklist()
        )

        schema = claim.to_json_schema()

        assert schema is not None
        assert "properties" in schema
        assert "claim_id" in schema["properties"]
        assert "claimant" in schema["properties"]
        assert "incident" in schema["properties"]
        assert "property_damage" in schema["properties"]
        assert "evidence" in schema["properties"]

    def test_schema_static(self):
        """Test static JSON Schema export."""
        schema = PropertyDamageClaim.schema()

        assert schema is not None
        assert schema["title"] == "PropertyDamageClaim"
        assert "required" in schema


# ============================================================================
# Test: Helper Methods
# ============================================================================


class TestHelperMethods:
    """Test helper methods on the claim model."""

    def test_get_missing_evidence(self):
        """Test get_missing_evidence method."""
        claim = PropertyDamageClaim(
            claim_id="CLM-HELPER-1",
            claimant=ClaimantInfo(),
            incident=IncidentInfo(),
            property_damage=PropertyDamageInfo(),
            evidence=EvidenceChecklist(missing_evidence=["photos", "estimate"])
        )
        missing = claim.get_missing_evidence()
        assert len(missing) == 2
        assert "photos" in missing
        assert "estimate" in missing

    def test_has_consistency_issues_true(self):
        """Test has_consistency_issues returns True when conflicts exist."""
        claim = PropertyDamageClaim(
            claim_id="CLM-HELPER-2",
            claimant=ClaimantInfo(),
            incident=IncidentInfo(),
            property_damage=PropertyDamageInfo(),
            evidence=EvidenceChecklist(),
            consistency=ConsistencyFlags(
                has_conflicts=True,
                conflict_details=["date mismatch"]
            )
        )
        assert claim.has_consistency_issues()

    def test_has_consistency_issues_false(self):
        """Test has_consistency_issues returns False when no conflicts."""
        claim = PropertyDamageClaim(
            claim_id="CLM-HELPER-3",
            claimant=ClaimantInfo(),
            incident=IncidentInfo(),
            property_damage=PropertyDamageInfo(),
            evidence=EvidenceChecklist()
        )
        assert not claim.has_consistency_issues()

    def test_get_consistency_issues(self):
        """Test get_consistency_issues method."""
        claim = PropertyDamageClaim(
            claim_id="CLM-HELPER-4",
            claimant=ClaimantInfo(),
            incident=IncidentInfo(),
            property_damage=PropertyDamageInfo(),
            evidence=EvidenceChecklist(),
            consistency=ConsistencyFlags(
                has_conflicts=True,
                conflict_details=["conflict 1", "conflict 2"]
            )
        )
        issues = claim.get_consistency_issues()
        assert len(issues) == 2
        assert "conflict 1" in issues
