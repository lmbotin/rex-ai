"""
Main extraction pipeline for FNOL claims.

Public API: parse_claim(text, image_paths) -> PropertyDamageClaim
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from .config import ExtractionConfig
from .fusion import ClaimFusion
from .image_analyzer import create_image_analyzer
from .schema import PropertyDamageClaim
from .text_extractor import create_text_extractor

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    """
    Multimodal extraction pipeline for property damage claims.

    Orchestrates text extraction, image analysis, and fusion.
    """

    def __init__(self, config: Optional[ExtractionConfig] = None):
        """
        Initialize extraction pipeline.

        Args:
            config: Extraction configuration (uses default if None)
        """
        self.config = config or ExtractionConfig.from_env()

        # Initialize components
        self.text_extractor = create_text_extractor(self.config)
        self.image_analyzer = create_image_analyzer(use_vision_model=False)
        self.fusion = ClaimFusion()

        logger.info(
            f"Initialized extraction pipeline with "
            f"LLM provider: {self.config.llm_provider}, "
            f"model: {self.config.llm_model}"
        )

    def parse_claim(
        self,
        text: str,
        image_paths: List[str],
        claimant_info: Optional[Dict[str, str]] = None
    ) -> PropertyDamageClaim:
        """
        Parse claim from text description and images.

        Args:
            text: Text description of the claim
            image_paths: List of paths to images
            claimant_info: Optional claimant information dict
                          (keys: name, policy_number, contact_phone, contact_email)

        Returns:
            PropertyDamageClaim validated against schema with provenance

        Example:
            ```python
            pipeline = ExtractionPipeline()
            claim = pipeline.parse_claim(
                text="Pipe burst in ceiling causing water damage to living room",
                image_paths=["damage1.jpg", "damage2.jpg"],
                claimant_info={"name": "John Doe", "policy_number": "POL-123"}
            )
            ```
        """
        start_time = datetime.utcnow()

        logger.info(
            f"Starting claim extraction: {len(text)} chars text, "
            f"{len(image_paths)} images"
        )

        # Step 1: Extract structured info from text
        logger.debug("Step 1: Extracting from text...")
        text_extraction = self.text_extractor.extract(text)
        logger.debug(
            f"Text extraction complete: "
            f"damage_type={text_extraction.get('damage_type')}, "
            f"extraction_time={text_extraction.get('extraction_time_ms', 0):.0f}ms"
        )

        # Step 2: Analyze images
        logger.debug(f"Step 2: Analyzing {len(image_paths)} images...")
        image_results = []
        if image_paths:
            image_results = self.image_analyzer.analyze_batch(image_paths)
            damage_count = sum(1 for r in image_results if r.contains_damage)
            logger.debug(
                f"Image analysis complete: "
                f"{damage_count}/{len(image_results)} contain damage"
            )
        else:
            logger.debug("No images provided")

        # Step 3: Fuse text + images into final claim
        logger.debug("Step 3: Fusing text and image analysis...")
        claim = self.fusion.fuse(
            text_extraction=text_extraction,
            image_results=image_results,
            claimant_info=claimant_info
        )

        end_time = datetime.utcnow()
        total_time_ms = (end_time - start_time).total_seconds() * 1000

        logger.info(
            f"Claim extraction complete: "
            f"claim_id={claim.claim_id}, "
            f"total_time={total_time_ms:.0f}ms"
        )

        # Log performance metrics
        self._log_metrics(claim, text_extraction, total_time_ms)

        return claim

    def _log_metrics(
        self,
        claim: PropertyDamageClaim,
        text_extraction: Dict,
        total_time_ms: float
    ):
        """Log performance and quality metrics."""
        metrics = {
            'total_time_ms': total_time_ms,
            'text_extraction_time_ms': text_extraction.get('extraction_time_ms', 0),
            'damage_type': claim.incident.damage_type.value,
            'property_type': claim.property_damage.property_type.value,
            'has_damage_photos': claim.evidence.has_damage_photos,
            'damage_photo_count': claim.evidence.damage_photo_count,
            'missing_evidence_count': len(claim.evidence.missing_evidence),
            'has_conflicts': claim.consistency.has_conflicts,
            'conflict_count': len(claim.consistency.conflict_details),
        }

        logger.info(f"Extraction metrics: {metrics}")


# Singleton instance for convenience
_default_pipeline: Optional[ExtractionPipeline] = None


def parse_claim(
    text: str,
    image_paths: List[str],
    claimant_info: Optional[Dict[str, str]] = None,
    config: Optional[ExtractionConfig] = None
) -> PropertyDamageClaim:
    """
    Parse claim from text and images (convenience function).

    This is the main public API for the extraction pipeline.

    Args:
        text: Text description of the claim
        image_paths: List of paths to images
        claimant_info: Optional claimant information
        config: Optional extraction configuration

    Returns:
        PropertyDamageClaim validated against schema

    Example:
        ```python
        from src.fnol.pipeline import parse_claim

        claim = parse_claim(
            text="Water damage from burst pipe in bathroom ceiling",
            image_paths=["img1.jpg", "img2.jpg"],
            claimant_info={"name": "Jane Doe"}
        )

        print(f"Claim ID: {claim.claim_id}")
        print(f"Damage Type: {claim.incident.damage_type}")
        print(f"Missing Evidence: {claim.evidence.missing_evidence}")
        ```
    """
    global _default_pipeline

    # Create pipeline if needed
    if config is not None:
        # New config provided, create new pipeline
        pipeline = ExtractionPipeline(config)
    else:
        # Use default singleton
        if _default_pipeline is None:
            _default_pipeline = ExtractionPipeline()
        pipeline = _default_pipeline

    return pipeline.parse_claim(text, image_paths, claimant_info)
