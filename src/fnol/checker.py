"""
Evidence Completeness & Consistency Checker for Property Damage Claims.

Analyzes a PropertyDamageClaim to:
- Calculate completeness score based on required evidence
- Detect contradictions and inconsistencies
- Generate targeted follow-up questions
"""

from datetime import datetime, timedelta
from typing import List

from pydantic import BaseModel, Field

from .schema import PropertyDamageClaim, DamageType, PropertyType, DamageSeverity


class CheckReport(BaseModel):
    """
    Report of evidence completeness and consistency checks.

    Provides actionable insights for claim adjusters to identify missing
    information and potential issues.
    """

    completeness_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall completeness score from 0 to 1"
    )

    missing_required_evidence: List[str] = Field(
        default_factory=list,
        description="List of missing required evidence items"
    )

    contradictions: List[str] = Field(
        default_factory=list,
        description="List of detected contradictions or inconsistencies"
    )

    recommended_questions: List[str] = Field(
        default_factory=list,
        description="1-3 targeted follow-up questions to improve claim quality"
    )

    class Config:
        schema_extra = {
            "examples": [
                {
                    "completeness_score": 0.75,
                    "missing_required_evidence": ["incident_location", "repair_estimate_document"],
                    "contradictions": ["High estimated cost ($8000) but no repair estimate document provided"],
                    "recommended_questions": [
                        "Can you provide the exact address where the damage occurred?",
                        "Do you have a written repair estimate from a contractor?"
                    ]
                }
            ]
        }


def check_claim(claim: PropertyDamageClaim) -> CheckReport:
    """
    Analyze a claim for completeness and consistency.

    Args:
        claim: The PropertyDamageClaim to check

    Returns:
        CheckReport with completeness score, missing evidence, contradictions,
        and recommended follow-up questions
    """

    missing_evidence = []
    contradictions = []

    # ========================================================================
    # Check Required Evidence (3 tiers)
    # ========================================================================

    # Tier 1 (Critical - 60% weight)
    tier1_items = []
    tier1_present = []

    # Damage photos (≥1)
    tier1_items.append("damage_photos")
    if claim.evidence.has_damage_photos and claim.evidence.damage_photo_count >= 1:
        tier1_present.append("damage_photos")
    else:
        missing_evidence.append("damage_photos")

    # Incident description
    tier1_items.append("incident_description")
    if claim.incident.incident_description and claim.incident.incident_description.strip():
        tier1_present.append("incident_description")
    else:
        missing_evidence.append("incident_description")

    # Damage type (not unknown)
    tier1_items.append("damage_type")
    if claim.incident.damage_type != DamageType.UNKNOWN:
        tier1_present.append("damage_type")
    else:
        missing_evidence.append("damage_type")

    # Property type (not unknown)
    tier1_items.append("property_type")
    if claim.property_damage.property_type != PropertyType.UNKNOWN:
        tier1_present.append("property_type")
    else:
        missing_evidence.append("property_type")

    # Tier 2 (Important - 30% weight)
    tier2_items = []
    tier2_present = []

    # Incident location
    tier2_items.append("incident_location")
    if claim.incident.incident_location and claim.incident.incident_location.strip():
        tier2_present.append("incident_location")
    else:
        missing_evidence.append("incident_location")

    # Estimated repair cost
    tier2_items.append("estimated_repair_cost")
    if claim.property_damage.estimated_repair_cost is not None:
        tier2_present.append("estimated_repair_cost")
    else:
        missing_evidence.append("estimated_repair_cost")

    # Incident date
    tier2_items.append("incident_date")
    if claim.incident.incident_date is not None:
        tier2_present.append("incident_date")
    else:
        missing_evidence.append("incident_date")

    # Tier 3 (Supporting - 10% weight)
    tier3_items = []
    tier3_present = []

    # Repair estimate document
    tier3_items.append("repair_estimate_document")
    if claim.evidence.has_repair_estimate:
        tier3_present.append("repair_estimate_document")
    else:
        missing_evidence.append("repair_estimate_document")

    # Room location
    tier3_items.append("room_location")
    if claim.property_damage.room_location and claim.property_damage.room_location.strip():
        tier3_present.append("room_location")
    else:
        missing_evidence.append("room_location")

    # Multiple photos (≥2)
    tier3_items.append("multiple_photos")
    if claim.evidence.damage_photo_count >= 2:
        tier3_present.append("multiple_photos")
    else:
        missing_evidence.append("multiple_photos")

    # Calculate completeness score
    tier1_score = (len(tier1_present) / len(tier1_items)) * 0.6 if tier1_items else 0.0
    tier2_score = (len(tier2_present) / len(tier2_items)) * 0.3 if tier2_items else 0.0
    tier3_score = (len(tier3_present) / len(tier3_items)) * 0.1 if tier3_items else 0.0

    completeness_score = tier1_score + tier2_score + tier3_score

    # ========================================================================
    # Detect Contradictions
    # ========================================================================

    # 1. Low confidence (<0.3) on critical fields
    if claim.incident.damage_type_provenance and claim.incident.damage_type_provenance.confidence < 0.3:
        contradictions.append("Low confidence on damage type classification (confidence < 0.3)")

    if claim.property_damage.property_type_provenance and claim.property_damage.property_type_provenance.confidence < 0.3:
        contradictions.append("Low confidence on property type classification (confidence < 0.3)")

    if claim.incident.incident_description_provenance and claim.incident.incident_description_provenance.confidence < 0.3:
        contradictions.append("Low confidence on incident description extraction (confidence < 0.3)")

    # 2. Severity vs cost mismatches
    severity = claim.property_damage.damage_severity
    cost = claim.property_damage.estimated_repair_cost

    if severity == DamageSeverity.SEVERE and cost is not None and cost < 1000:
        contradictions.append(f"Severity marked as SEVERE but estimated cost is only ${cost:.2f} (expected >$1000)")

    if severity == DamageSeverity.MINOR and cost is not None and cost > 10000:
        contradictions.append(f"Severity marked as MINOR but estimated cost is ${cost:.2f} (expected <$10000)")

    # 3. No photos but claims damage
    if not claim.evidence.has_damage_photos and claim.incident.incident_description:
        contradictions.append("Incident description provided but no damage photos uploaded")

    # 4. High cost (>$5k) without estimate doc
    if cost is not None and cost > 5000 and not claim.evidence.has_repair_estimate:
        contradictions.append(f"High estimated cost (${cost:.2f}) but no repair estimate document provided")

    # 5. Incident date in future or >2 years old
    if claim.incident.incident_date:
        now = datetime.utcnow()
        incident_date = claim.incident.incident_date
        
        # Handle string dates (convert to datetime if needed)
        if isinstance(incident_date, str):
            try:
                incident_date = datetime.fromisoformat(incident_date.replace('Z', '+00:00').replace('+00:00', ''))
            except ValueError:
                # Can't parse date string, skip this check
                incident_date = None

        if incident_date is not None:
            if incident_date > now:
                contradictions.append(f"Incident date is in the future: {incident_date.isoformat()}")
            elif incident_date < now - timedelta(days=730):  # 2 years
                contradictions.append(f"Incident date is more than 2 years old: {incident_date.isoformat()}")

    # 6. Location provided but confidence <0.3
    if claim.incident.incident_location and claim.incident.incident_location_provenance:
        if claim.incident.incident_location_provenance.confidence < 0.3:
            contradictions.append("Incident location provided but with very low confidence (confidence < 0.3)")

    # ========================================================================
    # Generate Recommended Questions (1-3 targeted follow-ups)
    # ========================================================================

    recommended_questions = []

    # Prioritize critical missing items first
    if "damage_photos" in missing_evidence:
        recommended_questions.append("Can you upload photos showing the damage?")

    if "incident_description" in missing_evidence:
        recommended_questions.append("Can you describe what happened and how the damage occurred?")

    if "damage_type" in missing_evidence or (
        claim.incident.damage_type == DamageType.UNKNOWN
        or (claim.incident.damage_type_provenance and claim.incident.damage_type_provenance.confidence < 0.3)
    ):
        recommended_questions.append("Can you clarify what caused the damage? (water, fire, impact, weather, etc.)")

    if "property_type" in missing_evidence:
        recommended_questions.append("What part of the property was damaged? (window, roof, ceiling, wall, etc.)")

    # Then important items
    if "incident_location" in missing_evidence:
        recommended_questions.append("Can you provide the exact address where the damage occurred?")

    if "incident_date" in missing_evidence:
        recommended_questions.append("When did the damage occur?")

    if "estimated_repair_cost" in missing_evidence:
        recommended_questions.append("Do you have a repair estimate or expected cost range?")

    # If severity is unclear or cost seems off
    if severity == DamageSeverity.UNKNOWN:
        recommended_questions.append("How would you describe the severity of the damage? (minor, moderate, or severe)")

    # Limit to 3 most relevant questions
    recommended_questions = recommended_questions[:3]

    return CheckReport(
        completeness_score=completeness_score,
        missing_required_evidence=missing_evidence,
        contradictions=contradictions,
        recommended_questions=recommended_questions
    )
