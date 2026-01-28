# Test Fixtures for FNOL Extraction Pipeline

This directory contains test fixtures for the multimodal claim extraction pipeline.

## Text Files (10 test cases)

1. **claim01_water_damage.txt** - Complete, detailed water damage claim with all info
2. **claim02_broken_window.txt** - Impact damage (broken window), moderate detail
3. **claim03_fire_damage.txt** - Severe fire damage, very detailed
4. **claim04_storm_roof.txt** - Weather damage, missing cost estimate
5. **claim05_vandalism_door.txt** - Vandalism with police report mention
6. **claim06_minimal_info.txt** - Minimal information (edge case)
7. **claim07_detailed_water.txt** - Detailed water damage from appliance leak
8. **claim08_wall_damage.txt** - Minor wall damage, simple case
9. **claim09_ambiguous.txt** - Very ambiguous description (low confidence expected)
10. **claim10_no_cost.txt** - No cost estimate provided

## Image Files (Placeholder)

Image files are placeholders for v1. The baseline image analyzer uses filename heuristics:

- `damage_*.jpg` - Classified as damage photos
- `*_photo*.jpg` - Classified as damage photos
- `receipt_*.jpg` - Classified as receipts/estimates
- `*_report.jpg` - Classified as documents

Actual images:
- damage_photo1.jpg
- damage_photo2.jpg
- damage_ceiling.jpg
- broken_window.jpg
- fire_damage1.jpg
- fire_damage2.jpg
- roof_damage.jpg
- door_damage.jpg
- floor_damage.jpg
- receipt_estimate.jpg

## Usage

```bash
# CLI with fixtures
python -m src.fnol --text-file fixtures/claim01_water_damage.txt --images fixtures/damage_photo1.jpg

# Programmatic
from src.fnol import parse_claim
with open('fixtures/claim01_water_damage.txt') as f:
    text = f.read()
claim = parse_claim(text, ['fixtures/damage_photo1.jpg'])
```
