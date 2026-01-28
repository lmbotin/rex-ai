"""
First Notice of Loss (FNOL) module.

Multimodal claim extraction pipeline for property damage claims.
"""

from .checker import CheckReport, check_claim
from .config import ExtractionConfig
from .extractor import PropertyClaimExtractor
from .pipeline import ExtractionPipeline, parse_claim
from .schema import (
    # Enums
    SourceModality,
    DamageType,
    PropertyType,
    DamageSeverity,
    # Models
    Provenance,
    ClaimantInfo,
    IncidentInfo,
    PropertyDamageInfo,
    EvidenceChecklist,
    ConsistencyFlags,
    PropertyDamageClaim,
)
from .state_manager import PropertyClaimStateManager

__all__ = [
    # Pipeline functions
    "parse_claim",
    "check_claim",
    # Classes
    "ExtractionPipeline",
    "ExtractionConfig",
    "CheckReport",
    "PropertyClaimStateManager",
    "PropertyClaimExtractor",
    # Enums
    "SourceModality",
    "DamageType",
    "PropertyType",
    "DamageSeverity",
    # Models
    "Provenance",
    "ClaimantInfo",
    "IncidentInfo",
    "PropertyDamageInfo",
    "EvidenceChecklist",
    "ConsistencyFlags",
    "PropertyDamageClaim",
]
