"""
First Notice of Loss (FNOL) module.

Multimodal claim extraction pipeline.
"""

from .checker import CheckReport, check_claim
from .config import ExtractionConfig
from .pipeline import ExtractionPipeline, parse_claim
from .schema import PropertyDamageClaim

__all__ = [
    "parse_claim",
    "check_claim",
    "ExtractionPipeline",
    "ExtractionConfig",
    "PropertyDamageClaim",
    "CheckReport",
]
