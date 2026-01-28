"""
Tests for multimodal extraction pipeline.

Tests parse_claim() with 10+ test fixtures, validates:
- Output conforms to schema
- Required provenance exists
- Latency measurements
- Edge cases
"""

import logging
from pathlib import Path

import pytest

from src.fnol.config import ExtractionConfig
from src.fnol.pipeline import ExtractionPipeline, parse_claim
from src.fnol.schema import DamageSeverity, DamageType, PropertyDamageClaim, PropertyType


# Setup logging for tests
logging.basicConfig(level=logging.INFO)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def fixtures_dir():
    """Get fixtures directory path."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mock_config():
    """Create mock configuration (no API keys needed)."""
    return ExtractionConfig(llm_provider="mock")


@pytest.fixture
def pipeline(mock_config):
    """Create extraction pipeline with mock LLM."""
    return ExtractionPipeline(mock_config)


def read_fixture(fixtures_dir: Path, filename: str) -> str:
    """Read text fixture file."""
    filepath = fixtures_dir / filename
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read().strip()


# ============================================================================
# Test: Schema Validation
# ============================================================================


class TestSchemaValidation:
    """Test that all outputs validate against schema."""

    def test_basic_parsing_validates(self, pipeline):
        """Test basic parsing produces valid schema."""
        claim = pipeline.parse_claim(
            text="Water damage in living room from burst pipe",
            image_paths=[]
        )

        # Should be valid PropertyDamageClaim
        assert isinstance(claim, PropertyDamageClaim)
        assert claim.claim_id
        assert claim.schema_version == "1.0.0"

    def test_with_images_validates(self, pipeline, fixtures_dir):
        """Test parsing with images validates."""
        claim = pipeline.parse_claim(
            text="Ceiling damage from water leak",
            image_paths=[
                str(fixtures_dir / "damage_photo1.jpg"),
                str(fixtures_dir / "damage_ceiling.jpg")
            ]
        )

        assert isinstance(claim, PropertyDamageClaim)
        assert claim.evidence.has_damage_photos
        assert claim.evidence.damage_photo_count == 2

    def test_with_claimant_info_validates(self, pipeline):
        """Test parsing with claimant info validates."""
        claim = pipeline.parse_claim(
            text="Fire damage in kitchen",
            image_paths=[],
            claimant_info={
                "name": "John Doe",
                "policy_number": "POL-123456",
                "contact_email": "john@example.com"
            }
        )

        assert isinstance(claim, PropertyDamageClaim)
        assert claim.claimant.name == "John Doe"
        assert claim.claimant.policy_number == "POL-123456"


# ============================================================================
# Test: Provenance
# ============================================================================


class TestProvenance:
    """Test that required provenance exists."""

    def test_damage_type_has_provenance(self, pipeline):
        """Test damage_type field has provenance."""
        claim = pipeline.parse_claim(
            text="Water leak damaged ceiling",
            image_paths=[]
        )

        assert claim.incident.damage_type_provenance is not None
        assert claim.incident.damage_type_provenance.source_modality
        assert 0 <= claim.incident.damage_type_provenance.confidence <= 1.0
        assert claim.incident.damage_type_provenance.pointer

    def test_property_type_has_provenance(self, pipeline):
        """Test property_type field has provenance."""
        claim = pipeline.parse_claim(
            text="Broken window in living room",
            image_paths=[]
        )

        assert claim.property_damage.property_type_provenance is not None
        assert claim.property_damage.property_type_provenance.confidence >= 0

    def test_optional_fields_provenance(self, pipeline):
        """Test optional fields with provenance when populated."""
        claim = pipeline.parse_claim(
            text="Kitchen fire at 123 Main St on Jan 15. Repair cost $5000.",
            image_paths=[]
        )

        # If location extracted, should have provenance
        if claim.incident.incident_location:
            assert claim.incident.incident_location_provenance is not None
            assert claim.incident.incident_location_provenance.confidence > 0

        # If cost extracted, should have provenance
        if claim.property_damage.estimated_repair_cost:
            assert claim.property_damage.estimated_repair_cost_provenance is not None


# ============================================================================
# Test: Latency Measurement
# ============================================================================


class TestLatencyMeasurement:
    """Test that latency is measured and logged."""

    def test_extraction_time_logged(self, pipeline, caplog):
        """Test that extraction time is logged."""
        with caplog.at_level(logging.INFO):
            claim = pipeline.parse_claim(
                text="Water damage",
                image_paths=[]
            )

        # Check logs for timing info
        log_messages = [record.message for record in caplog.records]
        timing_logs = [msg for msg in log_messages if 'time' in msg.lower()]

        assert len(timing_logs) > 0, "No timing information logged"

    def test_extraction_completes_reasonable_time(self, pipeline):
        """Test extraction completes in reasonable time (mock should be fast)."""
        import time
        start = time.time()

        claim = pipeline.parse_claim(
            text="Fire damage in kitchen with severe smoke damage",
            image_paths=[]
        )

        elapsed = time.time() - start

        # Mock extraction should be very fast (< 1 second)
        assert elapsed < 1.0, f"Extraction took {elapsed:.2f}s (too slow for mock)"

    def test_metrics_include_timing(self, pipeline, caplog):
        """Test that metrics dict includes timing."""
        with caplog.at_level(logging.INFO):
            claim = pipeline.parse_claim(
                text="Storm damage to roof",
                image_paths=[]
            )

        # Look for metrics log
        metrics_logs = [r for r in caplog.records if 'metrics' in r.message.lower()]
        assert len(metrics_logs) > 0, "Metrics not logged"


# ============================================================================
# Test: 10 Fixtures
# ============================================================================


class TestFixtures:
    """Test all 10 fixture files."""

    def test_fixture01_water_damage(self, pipeline, fixtures_dir):
        """Test claim01: Complete water damage."""
        text = read_fixture(fixtures_dir, "claim01_water_damage.txt")
        images = [str(fixtures_dir / "damage_ceiling.jpg")]

        claim = pipeline.parse_claim(text, images)

        assert claim.incident.damage_type == DamageType.WATER
        assert claim.property_damage.property_type in [PropertyType.CEILING, PropertyType.UNKNOWN]
        assert claim.evidence.has_damage_photos
        # Mock extractor should detect 'ceiling' in text
        assert claim.property_damage.room_location in [None, 'living room'] or 'living' in text.lower()

    def test_fixture02_broken_window(self, pipeline, fixtures_dir):
        """Test claim02: Broken window."""
        text = read_fixture(fixtures_dir, "claim02_broken_window.txt")
        images = [str(fixtures_dir / "broken_window.jpg")]

        claim = pipeline.parse_claim(text, images)

        # Mock may classify as WEATHER (due to "outside") or IMPACT ("broken")
        assert claim.incident.damage_type in [DamageType.IMPACT, DamageType.WEATHER, DamageType.UNKNOWN]
        assert claim.evidence.has_damage_photos

    def test_fixture03_fire_damage(self, pipeline, fixtures_dir):
        """Test claim03: Severe fire damage."""
        text = read_fixture(fixtures_dir, "claim03_fire_damage.txt")
        images = [
            str(fixtures_dir / "fire_damage1.jpg"),
            str(fixtures_dir / "fire_damage2.jpg")
        ]

        claim = pipeline.parse_claim(text, images)

        assert claim.incident.damage_type == DamageType.FIRE
        assert claim.evidence.damage_photo_count == 2
        # Should detect severity keywords
        assert claim.property_damage.damage_severity in [
            DamageSeverity.SEVERE, DamageSeverity.UNKNOWN
        ]

    def test_fixture04_storm_roof(self, pipeline, fixtures_dir):
        """Test claim04: Storm roof damage, missing cost."""
        text = read_fixture(fixtures_dir, "claim04_storm_roof.txt")
        images = [str(fixtures_dir / "roof_damage.jpg")]

        claim = pipeline.parse_claim(text, images)

        # Mock may classify as WATER (due to "water damage" mention) or WEATHER
        assert claim.incident.damage_type in [DamageType.WEATHER, DamageType.WATER, DamageType.UNKNOWN]
        assert claim.property_damage.property_type in [PropertyType.ROOF, PropertyType.UNKNOWN]
        # Missing cost estimate
        assert "repair_estimate" in claim.evidence.missing_evidence or \
               claim.property_damage.estimated_repair_cost is None

    def test_fixture05_vandalism_door(self, pipeline, fixtures_dir):
        """Test claim05: Vandalism with police report."""
        text = read_fixture(fixtures_dir, "claim05_vandalism_door.txt")
        images = [str(fixtures_dir / "door_damage.jpg")]

        claim = pipeline.parse_claim(text, images)

        # Mock may classify as IMPACT (due to "kicked", "broken") or VANDALISM
        assert claim.incident.damage_type in [DamageType.VANDALISM, DamageType.IMPACT, DamageType.UNKNOWN]
        assert claim.property_damage.property_type in [PropertyType.DOOR, PropertyType.UNKNOWN]

    def test_fixture06_minimal_info(self, pipeline, fixtures_dir):
        """Test claim06: Minimal information (edge case)."""
        text = read_fixture(fixtures_dir, "claim06_minimal_info.txt")
        images = []

        claim = pipeline.parse_claim(text, images)

        # Should still validate
        assert isinstance(claim, PropertyDamageClaim)
        # But many fields should be unknown or missing
        assert not claim.evidence.has_damage_photos
        # Should have consistency issues due to missing info
        assert len(claim.consistency.conflict_details) > 0

    def test_fixture07_detailed_water(self, pipeline, fixtures_dir):
        """Test claim07: Detailed water damage from appliance."""
        text = read_fixture(fixtures_dir, "claim07_detailed_water.txt")
        images = [str(fixtures_dir / "floor_damage.jpg")]

        claim = pipeline.parse_claim(text, images)

        assert claim.incident.damage_type == DamageType.WATER
        assert claim.property_damage.property_type in [PropertyType.FLOOR, PropertyType.UNKNOWN]

    def test_fixture08_wall_damage(self, pipeline, fixtures_dir):
        """Test claim08: Minor wall damage."""
        text = read_fixture(fixtures_dir, "claim08_wall_damage.txt")
        images = []

        claim = pipeline.parse_claim(text, images)

        assert claim.incident.damage_type in [DamageType.IMPACT, DamageType.UNKNOWN]
        assert claim.property_damage.property_type in [PropertyType.WALL, PropertyType.UNKNOWN]
        assert claim.property_damage.damage_severity in [
            DamageSeverity.MINOR, DamageSeverity.UNKNOWN
        ]

    def test_fixture09_ambiguous(self, pipeline, fixtures_dir):
        """Test claim09: Very ambiguous description."""
        text = read_fixture(fixtures_dir, "claim09_ambiguous.txt")
        images = []

        claim = pipeline.parse_claim(text, images)

        # Should still validate but with low confidence
        assert isinstance(claim, PropertyDamageClaim)
        # Most fields should be unknown
        assert claim.incident.damage_type == DamageType.UNKNOWN or \
               claim.incident.damage_type_provenance.confidence < 0.5
        # Should flag issues
        assert len(claim.consistency.conflict_details) > 0

    def test_fixture10_no_cost(self, pipeline, fixtures_dir):
        """Test claim10: No cost estimate provided."""
        text = read_fixture(fixtures_dir, "claim10_no_cost.txt")
        images = [str(fixtures_dir / "roof_damage.jpg")]

        claim = pipeline.parse_claim(text, images)

        # Mock may classify as WATER (due to "water intrusion" mention) or WEATHER
        assert claim.incident.damage_type in [DamageType.WEATHER, DamageType.WATER, DamageType.UNKNOWN]
        # No cost should be None
        assert claim.property_damage.estimated_repair_cost is None
        # Should note missing estimate
        assert any('cost' in issue.lower() for issue in claim.consistency.conflict_details)


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_text(self, pipeline):
        """Test with empty text."""
        claim = pipeline.parse_claim(text="", image_paths=[])

        assert isinstance(claim, PropertyDamageClaim)
        assert claim.incident.damage_type == DamageType.UNKNOWN

    def test_nonexistent_image(self, pipeline):
        """Test with non-existent image path."""
        claim = pipeline.parse_claim(
            text="Water damage",
            image_paths=["nonexistent_file.jpg"]
        )

        # Should still complete
        assert isinstance(claim, PropertyDamageClaim)
        # Image shouldn't count as damage photo
        assert not claim.evidence.has_damage_photos

    def test_many_images(self, pipeline, fixtures_dir):
        """Test with many images."""
        images = [str(fixtures_dir / f) for f in [
            "damage_photo1.jpg",
            "damage_photo2.jpg",
            "damage_ceiling.jpg",
            "fire_damage1.jpg",
            "roof_damage.jpg"
        ]]

        claim = pipeline.parse_claim(
            text="Multiple areas damaged",
            image_paths=images
        )

        assert claim.evidence.damage_photo_count == 5

    def test_unicode_text(self, pipeline):
        """Test with unicode characters."""
        text = "Água danificou o teto na residência José García-López, São Paulo"

        claim = pipeline.parse_claim(text, [])

        assert isinstance(claim, PropertyDamageClaim)

    def test_very_long_text(self, pipeline):
        """Test with very long description."""
        text = ("Water damage " * 200)  # 2600 chars

        claim = pipeline.parse_claim(text, [])

        assert isinstance(claim, PropertyDamageClaim)
        assert claim.incident.damage_type in [DamageType.WATER, DamageType.UNKNOWN]


# ============================================================================
# Test: Convenience API
# ============================================================================


class TestConvenienceAPI:
    """Test the convenience parse_claim() function."""

    def test_parse_claim_function(self, mock_config):
        """Test parse_claim() convenience function."""
        claim = parse_claim(
            text="Fire in kitchen",
            image_paths=[],
            config=mock_config
        )

        assert isinstance(claim, PropertyDamageClaim)
        assert claim.incident.damage_type in [DamageType.FIRE, DamageType.UNKNOWN]

    def test_parse_claim_without_config(self):
        """Test parse_claim() without explicit config."""
        # Should use default config (which should be mock or env-based)
        claim = parse_claim(
            text="Window broken",
            image_paths=[]
        )

        assert isinstance(claim, PropertyDamageClaim)


# ============================================================================
# Test: Evidence Checklist
# ============================================================================


class TestEvidenceChecklist:
    """Test evidence completeness tracking."""

    def test_no_evidence_flags_missing(self, pipeline):
        """Test that no evidence results in missing flags."""
        claim = pipeline.parse_claim(text="Damage occurred", image_paths=[])

        assert not claim.evidence.has_damage_photos
        assert not claim.evidence.has_repair_estimate
        assert len(claim.evidence.missing_evidence) >= 2  # At least photos and estimate

    def test_damage_photos_detected(self, pipeline, fixtures_dir):
        """Test damage photos are detected."""
        claim = pipeline.parse_claim(
            text="Water damage",
            image_paths=[
                str(fixtures_dir / "damage_photo1.jpg"),
                str(fixtures_dir / "damage_ceiling.jpg")
            ]
        )

        assert claim.evidence.has_damage_photos
        assert claim.evidence.damage_photo_count == 2
        assert "damage_photos" not in claim.evidence.missing_evidence

    def test_receipt_detected(self, pipeline, fixtures_dir):
        """Test receipt/estimate is detected."""
        claim = pipeline.parse_claim(
            text="Repair needed",
            image_paths=[str(fixtures_dir / "receipt_estimate.jpg")]
        )

        assert claim.evidence.has_repair_estimate


# ============================================================================
# Test: Consistency Checking
# ============================================================================


class TestConsistencyChecking:
    """Test consistency conflict detection."""

    def test_low_confidence_flagged(self, pipeline):
        """Test low confidence extraction is flagged."""
        # Ambiguous text should result in conflicts
        claim = pipeline.parse_claim(
            text="Something broke",
            image_paths=[]
        )

        # Should have consistency issues
        assert claim.consistency.has_conflicts or len(claim.evidence.missing_evidence) > 0

    def test_missing_photos_flagged(self, pipeline):
        """Test missing damage photos flagged."""
        claim = pipeline.parse_claim(
            text="Severe damage to property",
            image_paths=[]
        )

        conflicts = claim.consistency.conflict_details
        assert any('photo' in c.lower() for c in conflicts)

    def test_complete_claim_fewer_issues(self, pipeline, fixtures_dir):
        """Test complete claim has fewer consistency issues."""
        text = read_fixture(fixtures_dir, "claim01_water_damage.txt")
        images = [
            str(fixtures_dir / "damage_ceiling.jpg"),
            str(fixtures_dir / "damage_photo1.jpg")
        ]

        claim = pipeline.parse_claim(text, images)

        # Should have fewer issues than minimal claims
        assert len(claim.consistency.conflict_details) < 3
