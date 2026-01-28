"""
Fusion module for combining text and image analysis into final claim.

Handles provenance generation, conflict detection, and schema population.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .image_analyzer import ImageAnalysisResult
from .schema import (
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


class ClaimFusion:
    """Fuses text extraction and image analysis into complete claim."""

    def __init__(self, claim_id_prefix: str = "CLM"):
        """
        Initialize fusion engine.

        Args:
            claim_id_prefix: Prefix for generated claim IDs
        """
        self.claim_id_prefix = claim_id_prefix

    def fuse(
        self,
        text_extraction: Dict[str, Any],
        image_results: List[ImageAnalysisResult],
        claimant_info: Optional[Dict[str, str]] = None
    ) -> PropertyDamageClaim:
        """
        Fuse text and image analysis into complete claim.

        Args:
            text_extraction: Results from text extractor
            image_results: Results from image analyzer
            claimant_info: Optional claimant information

        Returns:
            Complete PropertyDamageClaim with provenance
        """
        # Generate claim ID
        claim_id = self._generate_claim_id()

        # Build claimant info
        claimant = self._build_claimant(claimant_info)

        # Build incident info with provenance
        incident = self._build_incident(text_extraction)

        # Build property damage info with provenance
        property_damage = self._build_property_damage(text_extraction, image_results)

        # Build evidence checklist
        evidence = self._build_evidence_checklist(image_results)

        # Detect consistency issues
        consistency = self._detect_conflicts(text_extraction, image_results, evidence)

        # Create claim
        claim = PropertyDamageClaim(
            claim_id=claim_id,
            claimant=claimant,
            incident=incident,
            property_damage=property_damage,
            evidence=evidence,
            consistency=consistency,
            created_at=datetime.utcnow(),
            schema_version="1.0.0"
        )

        return claim

    def _generate_claim_id(self) -> str:
        """Generate unique claim ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"{self.claim_id_prefix}-{timestamp}-{unique_id}"

    def _build_claimant(self, claimant_info: Optional[Dict[str, str]]) -> ClaimantInfo:
        """Build claimant information."""
        if claimant_info:
            return ClaimantInfo(**claimant_info)
        return ClaimantInfo()

    def _build_incident(self, text_extraction: Dict[str, Any]) -> IncidentInfo:
        """Build incident information with provenance."""
        incident_data = {}

        # Incident date
        if text_extraction.get('incident_date'):
            try:
                incident_data['incident_date'] = datetime.fromisoformat(
                    text_extraction['incident_date'].replace('Z', '+00:00')
                )
                incident_data['incident_date_provenance'] = Provenance(
                    source_modality=SourceModality.TEXT,
                    confidence=text_extraction.get('incident_date_confidence', 0.5),
                    pointer="text_span:full"
                )
            except (ValueError, AttributeError):
                pass

        # Incident location
        if text_extraction.get('incident_location'):
            incident_data['incident_location'] = text_extraction['incident_location']
            incident_data['incident_location_provenance'] = Provenance(
                source_modality=SourceModality.TEXT,
                confidence=text_extraction.get('incident_location_confidence', 0.5),
                pointer="text_span:full"
            )

        # Incident description
        if text_extraction.get('incident_description'):
            incident_data['incident_description'] = text_extraction['incident_description']
            incident_data['incident_description_provenance'] = Provenance(
                source_modality=SourceModality.TEXT,
                confidence=text_extraction.get('incident_description_confidence', 0.5),
                pointer="text_span:full"
            )

        # Damage type
        damage_type_str = text_extraction.get('damage_type', 'unknown')
        try:
            incident_data['damage_type'] = DamageType(damage_type_str.lower())
        except ValueError:
            incident_data['damage_type'] = DamageType.UNKNOWN

        incident_data['damage_type_provenance'] = Provenance(
            source_modality=SourceModality.TEXT,
            confidence=text_extraction.get('damage_type_confidence', 0.5),
            pointer="text_span:full"
        )

        return IncidentInfo(**incident_data)

    def _build_property_damage(
        self,
        text_extraction: Dict[str, Any],
        image_results: List[ImageAnalysisResult]
    ) -> PropertyDamageInfo:
        """Build property damage information with provenance."""
        damage_data = {}

        # Property type
        property_type_str = text_extraction.get('property_type', 'unknown')
        try:
            damage_data['property_type'] = PropertyType(property_type_str.lower())
        except ValueError:
            damage_data['property_type'] = PropertyType.UNKNOWN

        damage_data['property_type_provenance'] = Provenance(
            source_modality=SourceModality.TEXT,
            confidence=text_extraction.get('property_type_confidence', 0.5),
            pointer="text_span:full"
        )

        # Room location
        if text_extraction.get('room_location'):
            damage_data['room_location'] = text_extraction['room_location']
            damage_data['room_location_provenance'] = Provenance(
                source_modality=SourceModality.TEXT,
                confidence=text_extraction.get('room_location_confidence', 0.5),
                pointer="text_span:full"
            )

        # Estimated repair cost
        if text_extraction.get('estimated_repair_cost') is not None:
            damage_data['estimated_repair_cost'] = float(text_extraction['estimated_repair_cost'])
            damage_data['estimated_repair_cost_provenance'] = Provenance(
                source_modality=SourceModality.TEXT,
                confidence=text_extraction.get('estimated_repair_cost_confidence', 0.5),
                pointer="text_span:full"
            )

        # Damage severity
        severity_str = text_extraction.get('damage_severity', 'unknown')
        try:
            damage_data['damage_severity'] = DamageSeverity(severity_str.lower())
        except ValueError:
            damage_data['damage_severity'] = DamageSeverity.UNKNOWN

        # Boost severity confidence if we have damage photos
        damage_photo_count = sum(1 for r in image_results if r.contains_damage)
        base_confidence = text_extraction.get('damage_severity_confidence', 0.5)
        if damage_photo_count > 0:
            # Slightly boost confidence if images support damage claim
            base_confidence = min(base_confidence + 0.1, 1.0)

        damage_data['damage_severity_provenance'] = Provenance(
            source_modality=SourceModality.TEXT,
            confidence=base_confidence,
            pointer="text_span:full"
        )

        return PropertyDamageInfo(**damage_data)

    def _build_evidence_checklist(
        self,
        image_results: List[ImageAnalysisResult]
    ) -> EvidenceChecklist:
        """Build evidence checklist from image analysis."""
        # Count damage photos
        damage_photos = [r for r in image_results if r.contains_damage]
        damage_photo_count = len(damage_photos)
        damage_photo_ids = [r.image_path for r in damage_photos]

        # Check for receipts/estimates
        has_receipt = any(r.image_type == 'receipt' for r in image_results)

        # Check for documents (incident reports)
        has_document = any(r.image_type == 'document' for r in image_results)

        # Determine missing evidence
        missing = []
        if damage_photo_count == 0:
            missing.append("damage_photos")
        if not has_receipt:
            missing.append("repair_estimate")
        if not has_document:
            missing.append("incident_report")

        return EvidenceChecklist(
            has_damage_photos=damage_photo_count > 0,
            damage_photo_count=damage_photo_count,
            damage_photo_ids=damage_photo_ids,
            has_repair_estimate=has_receipt,
            has_incident_report=has_document,
            missing_evidence=missing
        )

    def _detect_conflicts(
        self,
        text_extraction: Dict[str, Any],
        image_results: List[ImageAnalysisResult],
        evidence: EvidenceChecklist
    ) -> ConsistencyFlags:
        """
        Detect consistency conflicts.

        Checks for:
        - Missing critical evidence
        - Low confidence extractions
        - Potential mismatches
        """
        conflicts = []

        # Check for low confidence on critical fields
        if text_extraction.get('damage_type_confidence', 1.0) < 0.3:
            conflicts.append(
                "Low confidence damage type extraction "
                f"({text_extraction.get('damage_type_confidence', 0.0):.2f})"
            )

        # Check for missing damage photos
        if evidence.damage_photo_count == 0:
            conflicts.append("No damage photos provided - cannot verify damage visually")

        # Check for missing cost estimate
        if text_extraction.get('estimated_repair_cost') is None:
            conflicts.append("No estimated repair cost provided")

        # Check for incomplete location information
        if not text_extraction.get('incident_location') or \
           text_extraction.get('incident_location_confidence', 0) < 0.3:
            conflicts.append("Incident location missing or uncertain")

        return ConsistencyFlags(
            has_conflicts=len(conflicts) > 0,
            conflict_details=conflicts
        )
