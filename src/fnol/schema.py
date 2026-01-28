"""
Canonical claim schema for Property Damage claims.

Defines Pydantic models with provenance tracking for each extracted field.
Sprint 1 focus: Simple property damage (water, fire, impact, etc.)
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


# ============================================================================
# Enums
# ============================================================================


class SourceModality(str, Enum):
    """Source of extracted information."""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"


class DamageType(str, Enum):
    """Type of damage to property."""
    WATER = "water"
    FIRE = "fire"
    IMPACT = "impact"
    WEATHER = "weather"
    VANDALISM = "vandalism"
    OTHER = "other"
    UNKNOWN = "unknown"


class PropertyType(str, Enum):
    """Type of property damaged."""
    WINDOW = "window"
    ROOF = "roof"
    CEILING = "ceiling"
    WALL = "wall"
    DOOR = "door"
    FLOOR = "floor"
    APPLIANCE = "appliance"
    FURNITURE = "furniture"
    OTHER = "other"
    UNKNOWN = "unknown"


class DamageSeverity(str, Enum):
    """Severity assessment of damage."""
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    UNKNOWN = "unknown"


# ============================================================================
# Provenance Model
# ============================================================================


class Provenance(BaseModel):
    """
    Provenance metadata for an extracted field.

    Tracks where the information came from and confidence level.
    """
    source_modality: SourceModality
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    pointer: str = Field(description="Reference to source (e.g., 'text_span:0-50', 'image_id:img_001')")

    @validator('confidence')
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


# ============================================================================
# Schema Sections
# ============================================================================


class ClaimantInfo(BaseModel):
    """Basic claimant information (minimal for Sprint 1)."""
    name: Optional[str] = Field(None, description="Claimant full name")
    policy_number: Optional[str] = Field(None, description="Insurance policy number")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    contact_email: Optional[str] = Field(None, description="Contact email address")


class IncidentInfo(BaseModel):
    """Information about the damage incident."""

    incident_date: Optional[datetime] = Field(None, description="When the damage occurred")
    incident_date_provenance: Optional[Provenance] = None

    incident_location: Optional[str] = Field(None, description="Where the damage occurred (address/location)")
    incident_location_provenance: Optional[Provenance] = None

    incident_description: Optional[str] = Field(None, description="Narrative description of what happened")
    incident_description_provenance: Optional[Provenance] = None

    damage_type: DamageType = Field(default=DamageType.UNKNOWN, description="Category of damage")
    damage_type_provenance: Optional[Provenance] = None


class PropertyDamageInfo(BaseModel):
    """Details about the damaged property."""

    property_type: PropertyType = Field(default=PropertyType.UNKNOWN, description="Type of property damaged")
    property_type_provenance: Optional[Provenance] = None

    room_location: Optional[str] = Field(None, description="Specific room or area within property")
    room_location_provenance: Optional[Provenance] = None

    estimated_repair_cost: Optional[float] = Field(None, ge=0, description="Estimated cost to repair (must be >= 0)")
    estimated_repair_cost_provenance: Optional[Provenance] = None

    damage_severity: DamageSeverity = Field(default=DamageSeverity.UNKNOWN, description="Severity assessment")
    damage_severity_provenance: Optional[Provenance] = None

    @validator('estimated_repair_cost')
    def validate_repair_cost(cls, v: Optional[float]) -> Optional[float]:
        """Ensure repair cost is non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("Estimated repair cost cannot be negative")
        return v


class EvidenceChecklist(BaseModel):
    """Tracks what evidence has been provided."""

    has_damage_photos: bool = Field(default=False, description="Whether damage photos are provided")
    damage_photo_count: int = Field(default=0, ge=0, description="Number of damage photos")
    damage_photo_ids: List[str] = Field(default_factory=list, description="IDs/paths of damage photos")

    has_repair_estimate: bool = Field(default=False, description="Whether repair estimate is provided")

    has_incident_report: bool = Field(default=False, description="Whether incident report is provided")

    missing_evidence: List[str] = Field(
        default_factory=list,
        description="List of missing required evidence (e.g., 'repair_estimate', 'damage_photos')"
    )

    @validator('damage_photo_count')
    def validate_photo_count(cls, v: int) -> int:
        """Ensure photo count is non-negative."""
        if v < 0:
            raise ValueError("Photo count cannot be negative")
        return v


class ConsistencyFlags(BaseModel):
    """Flags for evidence consistency issues."""

    has_conflicts: bool = Field(default=False, description="Whether conflicts detected")
    conflict_details: List[str] = Field(
        default_factory=list,
        description="List of specific conflicts (e.g., 'date mismatch: text says Jan 1, image EXIF says Jan 5')"
    )


# ============================================================================
# Main Claim Schema
# ============================================================================


class PropertyDamageClaim(BaseModel):
    """
    Canonical schema for a property damage claim.

    Includes provenance tracking for all extracted fields.
    """

    # Unique identifier
    claim_id: str = Field(description="Unique claim identifier")

    # Core sections
    claimant: ClaimantInfo = Field(description="Claimant information")
    incident: IncidentInfo = Field(description="Incident details")
    property_damage: PropertyDamageInfo = Field(description="Property damage details")
    evidence: EvidenceChecklist = Field(description="Evidence completeness tracking")
    consistency: ConsistencyFlags = Field(
        default_factory=ConsistencyFlags,
        description="Consistency check results"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Claim creation timestamp")
    schema_version: str = Field(default="1.0.0", description="Schema version")

    class Config:
        """Pydantic config."""
        schema_extra = {
            "examples": [
                {
                    "claim_id": "CLM-2024-001",
                    "claimant": {
                        "name": "John Doe",
                        "policy_number": "POL-123456",
                        "contact_phone": "+1-555-0100",
                        "contact_email": "john.doe@example.com"
                    },
                    "incident": {
                        "incident_date": "2024-01-15T14:30:00Z",
                        "incident_location": "123 Main St, Apt 4B, San Francisco, CA",
                        "incident_description": "Pipe burst in ceiling causing water damage",
                        "damage_type": "water"
                    },
                    "property_damage": {
                        "property_type": "ceiling",
                        "room_location": "living room",
                        "estimated_repair_cost": 2500.00,
                        "damage_severity": "moderate"
                    },
                    "evidence": {
                        "has_damage_photos": True,
                        "damage_photo_count": 3,
                        "damage_photo_ids": ["img_001.jpg", "img_002.jpg", "img_003.jpg"],
                        "has_repair_estimate": True,
                        "has_incident_report": False,
                        "missing_evidence": ["incident_report"]
                    }
                }
            ]
        }

    @validator('claim_id')
    def validate_claim_id(cls, v: str) -> str:
        """Ensure claim_id is not empty."""
        if not v or not v.strip():
            raise ValueError("claim_id cannot be empty")
        return v.strip()

    def to_json_schema(self) -> dict:
        """Export as JSON Schema."""
        return self.schema()

    def get_missing_evidence(self) -> List[str]:
        """Get list of missing required evidence."""
        return self.evidence.missing_evidence

    def has_consistency_issues(self) -> bool:
        """Check if there are any consistency issues."""
        return self.consistency.has_conflicts

    def get_consistency_issues(self) -> List[str]:
        """Get list of consistency issues."""
        return self.consistency.conflict_details
