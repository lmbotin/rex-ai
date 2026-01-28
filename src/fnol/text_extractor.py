"""
Text extraction module for FNOL claims.

Extracts structured information from text descriptions using LLMs.
"""

import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from .config import ExtractionConfig
from .schema import DamageSeverity, DamageType, PropertyType, SourceModality


class TextExtractor(ABC):
    """Base class for text extraction."""

    @abstractmethod
    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extract structured information from text.

        Args:
            text: Raw text description of the claim

        Returns:
            Dictionary with extracted fields and metadata:
            {
                'incident_date': str | None,
                'incident_date_confidence': float,
                'incident_location': str | None,
                'incident_location_confidence': float,
                'incident_description': str | None,
                'incident_description_confidence': float,
                'damage_type': str,
                'damage_type_confidence': float,
                'property_type': str,
                'property_type_confidence': float,
                'room_location': str | None,
                'room_location_confidence': float,
                'estimated_repair_cost': float | None,
                'estimated_repair_cost_confidence': float,
                'damage_severity': str,
                'damage_severity_confidence': float,
                'extraction_time_ms': float
            }
        """
        pass


class LLMTextExtractor(TextExtractor):
    """LLM-based text extraction (Claude or OpenAI)."""

    def __init__(self, config: ExtractionConfig):
        """Initialize with configuration."""
        self.config = config

        # Import appropriate client
        if config.llm_provider == "claude":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=config.api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package required for Claude. "
                    "Install with: pip install anthropic"
                )
        elif config.llm_provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=config.api_key)
            except ImportError:
                raise ImportError(
                    "openai package required for OpenAI. "
                    "Install with: pip install openai"
                )
        else:
            raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")

    def _build_prompt(self, text: str) -> str:
        """Build extraction prompt."""
        return f"""You are an expert insurance claims analyst. Extract structured information from the following property damage claim description.

CLAIM DESCRIPTION:
{text}

Extract the following information. If a field is not mentioned or unclear, set it to null and use low confidence (<0.5).

Return ONLY a valid JSON object with this structure:
{{
  "incident_date": "ISO datetime string or null",
  "incident_date_confidence": 0.0-1.0,
  "incident_location": "address or location or null",
  "incident_location_confidence": 0.0-1.0,
  "incident_description": "what happened or null",
  "incident_description_confidence": 0.0-1.0,
  "damage_type": "water|fire|impact|weather|vandalism|other|unknown",
  "damage_type_confidence": 0.0-1.0,
  "property_type": "window|roof|ceiling|wall|door|floor|appliance|furniture|other|unknown",
  "property_type_confidence": 0.0-1.0,
  "room_location": "specific room/area or null",
  "room_location_confidence": 0.0-1.0,
  "estimated_repair_cost": number or null,
  "estimated_repair_cost_confidence": 0.0-1.0,
  "damage_severity": "minor|moderate|severe|unknown",
  "damage_severity_confidence": 0.0-1.0
}}

IMPORTANT:
- incident_date must be ISO 8601 format if present (e.g., "2024-01-15T14:30:00")
- Use "unknown" for enums when uncertain
- Be conservative with confidence scores
- Return ONLY the JSON, no explanations"""

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response and extract JSON."""
        # Try to find JSON in response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        else:
            raise ValueError(f"No JSON found in LLM response: {response}")

    def extract(self, text: str) -> Dict[str, Any]:
        """Extract structured information using LLM."""
        start_time = datetime.utcnow()

        prompt = self._build_prompt(text)

        try:
            if self.config.llm_provider == "claude":
                response = self.client.messages.create(
                    model=self.config.llm_model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text
            else:  # openai
                response = self.client.chat.completions.create(
                    model=self.config.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                )
                result_text = response.choices[0].message.content

            # Parse response
            extracted = self._parse_llm_response(result_text)

            # Add extraction time
            end_time = datetime.utcnow()
            extracted['extraction_time_ms'] = (end_time - start_time).total_seconds() * 1000

            return extracted

        except Exception as e:
            # Return safe default on error
            return self._get_default_extraction(str(e))

    def _get_default_extraction(self, error_msg: str = "") -> Dict[str, Any]:
        """Return default extraction on error."""
        return {
            'incident_date': None,
            'incident_date_confidence': 0.0,
            'incident_location': None,
            'incident_location_confidence': 0.0,
            'incident_description': None,
            'incident_description_confidence': 0.0,
            'damage_type': 'unknown',
            'damage_type_confidence': 0.0,
            'property_type': 'unknown',
            'property_type_confidence': 0.0,
            'room_location': None,
            'room_location_confidence': 0.0,
            'estimated_repair_cost': None,
            'estimated_repair_cost_confidence': 0.0,
            'damage_severity': 'unknown',
            'damage_severity_confidence': 0.0,
            'extraction_time_ms': 0.0,
            'error': error_msg
        }


class MockTextExtractor(TextExtractor):
    """Mock extractor for testing (deterministic, no API calls)."""

    def extract(self, text: str) -> Dict[str, Any]:
        """Extract using simple heuristics."""
        start_time = datetime.utcnow()

        extracted = {
            'incident_date': None,
            'incident_date_confidence': 0.3,
            'incident_location': None,
            'incident_location_confidence': 0.3,
            'incident_description': text if text else None,
            'incident_description_confidence': 0.9 if text else 0.0,
            'damage_type': 'unknown',
            'damage_type_confidence': 0.5,
            'property_type': 'unknown',
            'property_type_confidence': 0.5,
            'room_location': None,
            'room_location_confidence': 0.3,
            'estimated_repair_cost': None,
            'estimated_repair_cost_confidence': 0.0,
            'damage_severity': 'unknown',
            'damage_severity_confidence': 0.4,
        }

        text_lower = text.lower()

        # Heuristic damage type detection
        if 'water' in text_lower or 'leak' in text_lower or 'flood' in text_lower or 'pipe' in text_lower:
            extracted['damage_type'] = 'water'
            extracted['damage_type_confidence'] = 0.8
        elif 'fire' in text_lower or 'burn' in text_lower or 'smoke' in text_lower:
            extracted['damage_type'] = 'fire'
            extracted['damage_type_confidence'] = 0.8
        elif 'storm' in text_lower or 'wind' in text_lower or 'hail' in text_lower or 'weather' in text_lower:
            extracted['damage_type'] = 'weather'
            extracted['damage_type_confidence'] = 0.8
        elif 'break' in text_lower or 'broken' in text_lower or 'crash' in text_lower or 'impact' in text_lower:
            extracted['damage_type'] = 'impact'
            extracted['damage_type_confidence'] = 0.7
        elif 'vandal' in text_lower:
            extracted['damage_type'] = 'vandalism'
            extracted['damage_type_confidence'] = 0.8

        # Heuristic property type detection
        if 'window' in text_lower:
            extracted['property_type'] = 'window'
            extracted['property_type_confidence'] = 0.8
        elif 'roof' in text_lower:
            extracted['property_type'] = 'roof'
            extracted['property_type_confidence'] = 0.8
        elif 'ceiling' in text_lower:
            extracted['property_type'] = 'ceiling'
            extracted['property_type_confidence'] = 0.8
        elif 'wall' in text_lower:
            extracted['property_type'] = 'wall'
            extracted['property_type_confidence'] = 0.7
        elif 'door' in text_lower:
            extracted['property_type'] = 'door'
            extracted['property_type_confidence'] = 0.8
        elif 'floor' in text_lower:
            extracted['property_type'] = 'floor'
            extracted['property_type_confidence'] = 0.8
        elif 'appliance' in text_lower or 'stove' in text_lower or 'dishwasher' in text_lower:
            extracted['property_type'] = 'appliance'
            extracted['property_type_confidence'] = 0.7

        # Heuristic severity detection
        if 'severe' in text_lower or 'major' in text_lower or 'extensive' in text_lower:
            extracted['damage_severity'] = 'severe'
            extracted['damage_severity_confidence'] = 0.7
        elif 'moderate' in text_lower or 'medium' in text_lower:
            extracted['damage_severity'] = 'moderate'
            extracted['damage_severity_confidence'] = 0.7
        elif 'minor' in text_lower or 'small' in text_lower or 'slight' in text_lower:
            extracted['damage_severity'] = 'minor'
            extracted['damage_severity_confidence'] = 0.7

        # Room detection
        rooms = ['kitchen', 'bathroom', 'bedroom', 'living room', 'dining room', 'basement', 'attic', 'garage']
        for room in rooms:
            if room in text_lower:
                extracted['room_location'] = room
                extracted['room_location_confidence'] = 0.8
                break

        # Try to extract cost
        cost_match = re.search(r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text)
        if cost_match:
            cost_str = cost_match.group(1).replace(',', '')
            try:
                extracted['estimated_repair_cost'] = float(cost_str)
                extracted['estimated_repair_cost_confidence'] = 0.6
            except ValueError:
                pass

        end_time = datetime.utcnow()
        extracted['extraction_time_ms'] = (end_time - start_time).total_seconds() * 1000

        return extracted


def create_text_extractor(config: Optional[ExtractionConfig] = None) -> TextExtractor:
    """Factory function to create appropriate text extractor."""
    if config is None:
        from .config import DEFAULT_CONFIG
        config = DEFAULT_CONFIG

    if config.llm_provider == "mock":
        return MockTextExtractor()
    else:
        return LLMTextExtractor(config)
