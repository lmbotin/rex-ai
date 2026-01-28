"""
Property Claim State Manager for tracking claim intake progress.

Adapted for PropertyDamageClaim schema with provenance tracking.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from .schema import (
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


# Field definitions with priority, question text, and path
FIELD_DEFINITIONS = [
    # Priority 1: Claimant identification
    {
        "id": "claimant.name",
        "path": ["claimant", "name"],
        "priority": 1,
        "question": "May I have your full name, please?",
        "required": True,
    },
    {
        "id": "claimant.policy_number",
        "path": ["claimant", "policy_number"],
        "priority": 1,
        "question": "Could you please provide your policy number?",
        "required": True,
    },
    # Priority 2: Incident basics
    {
        "id": "incident.damage_type",
        "path": ["incident", "damage_type"],
        "priority": 2,
        "question": "What type of damage occurred? For example, was it water damage, fire, impact, or something else?",
        "required": True,
    },
    {
        "id": "incident.incident_date",
        "path": ["incident", "incident_date"],
        "priority": 2,
        "question": "When did this damage occur?",
        "required": True,
    },
    # Priority 3: Location
    {
        "id": "incident.incident_location",
        "path": ["incident", "incident_location"],
        "priority": 3,
        "question": "Where did this damage occur? Please provide the address.",
        "required": True,
    },
    # Priority 4: Description
    {
        "id": "incident.incident_description",
        "path": ["incident", "incident_description"],
        "priority": 4,
        "question": "Could you please describe what happened?",
        "required": True,
    },
    # Priority 5: Property details
    {
        "id": "property_damage.property_type",
        "path": ["property_damage", "property_type"],
        "priority": 5,
        "question": "What was damaged? For example, was it a window, roof, ceiling, wall, or something else?",
        "required": True,
    },
    {
        "id": "property_damage.room_location",
        "path": ["property_damage", "room_location"],
        "priority": 5,
        "question": "In which room or area of the property is the damage located?",
        "required": False,
    },
    # Priority 6: Severity and cost
    {
        "id": "property_damage.damage_severity",
        "path": ["property_damage", "damage_severity"],
        "priority": 6,
        "question": "How severe would you say the damage is - minor, moderate, or severe?",
        "required": False,
    },
    {
        "id": "property_damage.estimated_repair_cost",
        "path": ["property_damage", "estimated_repair_cost"],
        "priority": 6,
        "question": "Do you have an estimate of the repair cost?",
        "required": False,
    },
    # Priority 7: Contact info
    {
        "id": "claimant.contact_phone",
        "path": ["claimant", "contact_phone"],
        "priority": 7,
        "question": "What is the best phone number to reach you?",
        "required": False,
    },
    {
        "id": "claimant.contact_email",
        "path": ["claimant", "contact_email"],
        "priority": 7,
        "question": "What is your email address for claim updates?",
        "required": False,
    },
]


def _get_nested_value(obj: Any, path: list) -> Any:
    """Get a value from a nested path."""
    try:
        for key in path:
            if isinstance(key, int):
                if isinstance(obj, list) and len(obj) > key:
                    obj = obj[key]
                else:
                    return None
            else:
                obj = getattr(obj, key, None)
            if obj is None:
                return None
        return obj
    except (IndexError, AttributeError):
        return None


def _set_nested_value(obj: Any, path: list, value: Any) -> bool:
    """Set a value at a nested path. Returns True if successful."""
    try:
        for key in path[:-1]:
            if isinstance(key, int):
                if isinstance(obj, list):
                    while len(obj) <= key:
                        obj.append(None)
                    if obj[key] is None:
                        return False
                    obj = obj[key]
                else:
                    return False
            else:
                obj = getattr(obj, key, None)
                if obj is None:
                    return False
        
        final_key = path[-1]
        if isinstance(final_key, int):
            if isinstance(obj, list):
                while len(obj) <= final_key:
                    obj.append(None)
                obj[final_key] = value
            else:
                return False
        else:
            setattr(obj, final_key, value)
        return True
    except (IndexError, AttributeError, TypeError):
        return False


class PropertyClaimStateManager:
    """
    Manages the state of a property damage claim during intake.
    
    Tracks which fields have been collected and determines the next
    question to ask based on priority and conditional logic.
    """
    
    def __init__(self, call_sid: Optional[str] = None, stream_sid: Optional[str] = None):
        """Initialize a new property claim state manager."""
        self.claim = PropertyDamageClaim(
            claim_id=str(uuid.uuid4()),
            claimant=ClaimantInfo(),
            incident=IncidentInfo(),
            property_damage=PropertyDamageInfo(),
            evidence=EvidenceChecklist(),
            consistency=ConsistencyFlags(),
            created_at=datetime.utcnow(),
        )
        
        # Store call metadata separately (not in schema)
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self.call_start_time = datetime.utcnow()
        
        # Conversation tracking
        self._conversation_turn = 0
        self._asked_fields: set[str] = set()
        self._transcript: list[dict] = []
        self._extraction_history: list[dict] = []
    
    def get_missing_fields(self, include_optional: bool = True) -> list[dict]:
        """
        Return list of fields not yet filled.
        
        Args:
            include_optional: If True, include optional fields; otherwise only required.
            
        Returns:
            List of field definitions that are missing values.
        """
        missing = []
        
        for field_def in FIELD_DEFINITIONS:
            # Skip optional fields if not requested
            if not include_optional and not field_def.get("required", False):
                continue
            
            # Check if field has value
            path = field_def["path"]
            value = _get_nested_value(self.claim, path)
            
            # Check for empty/default values
            if value is None or value == "":
                missing.append(field_def)
            elif isinstance(value, DamageType) and value == DamageType.UNKNOWN:
                missing.append(field_def)
            elif isinstance(value, PropertyType) and value == PropertyType.UNKNOWN:
                missing.append(field_def)
            elif isinstance(value, DamageSeverity) and value == DamageSeverity.UNKNOWN:
                missing.append(field_def)
        
        return missing
    
    def get_next_question(self) -> Optional[dict]:
        """
        Get the next question to ask based on priority.
        
        Returns:
            Field definition dict with 'question' key, or None if all done.
        """
        missing = self.get_missing_fields(include_optional=True)
        
        if not missing:
            return None
        
        # Sort by priority (lower is higher priority)
        missing.sort(key=lambda f: f["priority"])
        
        # Return the highest priority missing field
        return missing[0]
    
    def get_completion_percentage(self) -> float:
        """Calculate how complete the claim is (required fields only)."""
        required_fields = [f for f in FIELD_DEFINITIONS if f.get("required", False)]
        if not required_fields:
            return 100.0
        
        filled = 0
        
        for field_def in required_fields:
            path = field_def["path"]
            value = _get_nested_value(self.claim, path)
            
            if value is not None and value != "":
                # Check for non-default enum values
                if isinstance(value, DamageType) and value != DamageType.UNKNOWN:
                    filled += 1
                elif isinstance(value, PropertyType) and value != PropertyType.UNKNOWN:
                    filled += 1
                elif isinstance(value, DamageSeverity) and value != DamageSeverity.UNKNOWN:
                    filled += 1
                elif not isinstance(value, (DamageType, PropertyType, DamageSeverity)):
                    filled += 1
        
        return (filled / len(required_fields)) * 100
    
    def is_complete(self) -> bool:
        """Check if all required fields have been collected."""
        missing_required = self.get_missing_fields(include_optional=False)
        return len(missing_required) == 0
    
    def apply_patch(self, patch: dict) -> list[str]:
        """
        Merge extracted data into current state.
        
        Args:
            patch: Dictionary with field paths as keys (dot notation) and values.
            
        Returns:
            List of field IDs that were updated.
        """
        updated = []
        
        for field_id, value in patch.items():
            if value is None:
                continue
            
            # Find the field definition
            field_def = next((f for f in FIELD_DEFINITIONS if f["id"] == field_id), None)
            
            if field_def:
                path = field_def["path"]
            else:
                # Try to parse the path from dot notation
                path = self._parse_path(field_id)
            
            # Convert enum values
            value = self._convert_enum_value(field_id, value)
            
            # Set the value
            if path and _set_nested_value(self.claim, path, value):
                updated.append(field_id)
                
                # Also set provenance if this is a provenance-tracked field
                self._set_provenance(field_id)
        
        # Record extraction
        if updated:
            self._extraction_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "turn": self._conversation_turn,
                "fields_updated": updated,
                "patch": patch,
            })
        
        return updated
    
    def _parse_path(self, field_id: str) -> list:
        """Parse a dot-notation field ID into a path list."""
        parts = field_id.split(".")
        path = []
        for part in parts:
            if part.isdigit():
                path.append(int(part))
            else:
                path.append(part)
        return path
    
    def _convert_enum_value(self, field_id: str, value: Any) -> Any:
        """Convert string values to appropriate enum types."""
        if not isinstance(value, str):
            return value
        
        value_lower = value.lower().strip()
        
        if field_id == "incident.damage_type":
            try:
                return DamageType(value_lower)
            except ValueError:
                return DamageType.UNKNOWN
        
        elif field_id == "property_damage.property_type":
            try:
                return PropertyType(value_lower)
            except ValueError:
                return PropertyType.UNKNOWN
        
        elif field_id == "property_damage.damage_severity":
            try:
                return DamageSeverity(value_lower)
            except ValueError:
                return DamageSeverity.UNKNOWN
        
        return value
    
    def _set_provenance(self, field_id: str) -> None:
        """Set provenance for a field extracted from voice."""
        provenance = Provenance(
            source_modality=SourceModality.VOICE,
            confidence=0.8,  # Default confidence for voice extraction
            pointer=f"voice_turn:{self._conversation_turn}",
        )
        
        # Map field IDs to provenance fields
        provenance_map = {
            "incident.incident_date": ("incident", "incident_date_provenance"),
            "incident.incident_location": ("incident", "incident_location_provenance"),
            "incident.incident_description": ("incident", "incident_description_provenance"),
            "incident.damage_type": ("incident", "damage_type_provenance"),
            "property_damage.property_type": ("property_damage", "property_type_provenance"),
            "property_damage.room_location": ("property_damage", "room_location_provenance"),
            "property_damage.estimated_repair_cost": ("property_damage", "estimated_repair_cost_provenance"),
            "property_damage.damage_severity": ("property_damage", "damage_severity_provenance"),
        }
        
        if field_id in provenance_map:
            section, prov_field = provenance_map[field_id]
            section_obj = getattr(self.claim, section, None)
            if section_obj:
                setattr(section_obj, prov_field, provenance)
    
    def add_transcript_entry(self, role: str, content: str) -> None:
        """Add an entry to the conversation transcript."""
        self._transcript.append({
            "timestamp": datetime.utcnow().isoformat(),
            "turn": self._conversation_turn,
            "role": role,
            "content": content,
        })
        if role == "user":
            self._conversation_turn += 1
    
    def mark_field_asked(self, field_id: str) -> None:
        """Mark a field as having been asked about."""
        self._asked_fields.add(field_id)
    
    def was_field_asked(self, field_id: str) -> bool:
        """Check if a field has been asked about."""
        return field_id in self._asked_fields
    
    def to_dict(self) -> dict:
        """Export current claim state as dictionary."""
        data = self.claim.model_dump(mode="json")
        # Add call metadata
        data["_call_metadata"] = {
            "call_sid": self.call_sid,
            "stream_sid": self.stream_sid,
            "call_start_time": self.call_start_time.isoformat() if self.call_start_time else None,
        }
        data["_transcript"] = self._transcript
        data["_extraction_history"] = self._extraction_history
        return data
    
    def get_summary(self) -> str:
        """Generate a human-readable summary of collected information."""
        lines = []
        
        if self.claim.claimant.name:
            lines.append(f"Claimant: {self.claim.claimant.name}")
        if self.claim.claimant.policy_number:
            lines.append(f"Policy: {self.claim.claimant.policy_number}")
        if self.claim.incident.damage_type != DamageType.UNKNOWN:
            lines.append(f"Damage Type: {self.claim.incident.damage_type.value}")
        if self.claim.incident.incident_date:
            lines.append(f"Date: {self.claim.incident.incident_date}")
        if self.claim.incident.incident_location:
            lines.append(f"Location: {self.claim.incident.incident_location}")
        if self.claim.incident.incident_description:
            lines.append(f"Description: {self.claim.incident.incident_description}")
        if self.claim.property_damage.property_type != PropertyType.UNKNOWN:
            lines.append(f"Property Type: {self.claim.property_damage.property_type.value}")
        if self.claim.property_damage.room_location:
            lines.append(f"Room: {self.claim.property_damage.room_location}")
        if self.claim.property_damage.damage_severity != DamageSeverity.UNKNOWN:
            lines.append(f"Severity: {self.claim.property_damage.damage_severity.value}")
        if self.claim.property_damage.estimated_repair_cost:
            lines.append(f"Est. Cost: ${self.claim.property_damage.estimated_repair_cost:,.2f}")
        
        completion = self.get_completion_percentage()
        lines.append(f"\nCompletion: {completion:.0f}%")
        
        return "\n".join(lines) if lines else "No information collected yet."
    
    def finalize(self) -> dict:
        """Finalize the claim and return the complete data."""
        # Update evidence checklist
        self._update_evidence_checklist()
        return self.to_dict()
    
    def _update_evidence_checklist(self) -> None:
        """Update the evidence checklist based on current state."""
        missing = []
        
        # Check what's missing
        if not self.claim.evidence.has_damage_photos:
            missing.append("damage_photos")
        if not self.claim.evidence.has_repair_estimate:
            missing.append("repair_estimate")
        if not self.claim.evidence.has_incident_report:
            missing.append("incident_report")
        
        self.claim.evidence.missing_evidence = missing


# Backwards compatibility alias
FNOLStateManager = PropertyClaimStateManager
