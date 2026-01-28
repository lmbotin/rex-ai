#!/usr/bin/env python3
"""
Export JSON Schema for PropertyDamageClaim.

This script exports the canonical JSON Schema and validates example claims.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fnol.schema import PropertyDamageClaim


def export_json_schema(output_path: str = "data/claim_schema.json"):
    """Export the JSON Schema for PropertyDamageClaim."""
    schema = PropertyDamageClaim.schema()

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"✓ JSON Schema exported to: {output_file}")
    print(f"  Title: {schema['title']}")
    print(f"  Properties: {len(schema['properties'])} top-level fields")
    return schema


def validate_example_claims():
    """Validate example claim JSON files against the schema."""
    examples_dir = Path("data/examples")
    example_files = list(examples_dir.glob("claim_*.json"))

    if not example_files:
        print("⚠ No example claim files found in data/examples/")
        return

    print(f"\n{'='*60}")
    print("Validating Example Claims")
    print('='*60)

    valid_count = 0
    invalid_count = 0

    for example_file in sorted(example_files):
        print(f"\n📄 {example_file.name}")
        try:
            with open(example_file, "r", encoding="utf-8") as f:
                claim_data = json.load(f)

            # Validate using Pydantic
            claim = PropertyDamageClaim.parse_obj(claim_data)

            print(f"  ✓ Valid")
            print(f"    Claim ID: {claim.claim_id}")
            print(f"    Claimant: {claim.claimant.name}")
            print(f"    Damage Type: {claim.incident.damage_type.value}")
            print(f"    Missing Evidence: {len(claim.get_missing_evidence())} items")
            print(f"    Consistency Issues: {len(claim.get_consistency_issues())} conflicts")

            valid_count += 1

        except Exception as e:
            print(f"  ✗ Invalid: {e}")
            invalid_count += 1

    print(f"\n{'='*60}")
    print(f"Results: {valid_count} valid, {invalid_count} invalid")
    print('='*60)


def main():
    """Main entry point."""
    print("="*60)
    print("Property Damage Claim - JSON Schema Export")
    print("="*60)

    # Export JSON Schema
    schema = export_json_schema()

    # Validate example claims
    validate_example_claims()


if __name__ == "__main__":
    main()
