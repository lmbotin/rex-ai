# Sprint 1 - Deliverable #2: Multimodal Extraction Pipeline v1

**Status:** ✅ COMPLETE

## Overview

Implemented a complete multimodal extraction pipeline that takes text descriptions and images as input and produces validated PropertyDamageClaim objects with full provenance tracking.

**Key Features:**
- Modular architecture with clear separation of concerns
- LLM integration (Claude/OpenAI) with mock fallback for testing
- Baseline image analyzer with swappable interface for future vision models
- Automatic provenance generation for all extracted fields
- Evidence completeness and consistency checking
- CLI interface for easy usage
- 32 comprehensive pytest tests (all passing)

---

## Architecture

### Module Structure

```
src/fnol/
├── config.py           # Configuration and API key management
├── text_extractor.py   # LLM-based text extraction
├── image_analyzer.py   # Image classification (baseline + interface)
├── fusion.py           # Combines text + images with provenance
├── pipeline.py         # Main pipeline orchestration
├── cli.py              # Command-line interface
├── __main__.py         # Module entry point
└── schema.py           # Pydantic models (from Deliverable #1)
```

### Pipeline Flow

```
Input: text + images
    ↓
[1] Text Extraction (LLM or Mock)
    → Structured fields + confidence scores
    ↓
[2] Image Analysis (Baseline heuristics)
    → Image type classification + damage detection
    ↓
[3] Fusion
    → Combines text + images
    → Generates provenance for each field
    → Builds evidence checklist
    → Detects consistency issues
    ↓
Output: PropertyDamageClaim (validated against schema)
```

---

## Files Created

### 1. Configuration Module
**File:** [src/fnol/config.py](../src/fnol/config.py)

**Purpose:** Manages LLM provider configuration and API keys

**Key Classes:**
- `ExtractionConfig`: Configuration with provider selection (claude | openai | mock)
- Automatic API key detection from environment variables
- Validation and fallback to mock when no API keys available

**Example:**
```python
# Use Claude
config = ExtractionConfig(
    llm_provider="claude",
    llm_model="claude-3-5-sonnet-20241022"
)

# Use mock (no API key needed)
config = ExtractionConfig(llm_provider="mock")
```

---

### 2. Text Extractor Module
**File:** [src/fnol/text_extractor.py](../src/fnol/text_extractor.py)

**Purpose:** Extracts structured information from text descriptions

**Key Classes:**
- `TextExtractor` (ABC): Base interface for all extractors
- `LLMTextExtractor`: Uses Claude/OpenAI for extraction
  - Structured prompting with JSON output
  - Conservative confidence scoring
  - Error handling with safe defaults
- `MockTextExtractor`: Deterministic keyword-based heuristics
  - No API calls required
  - Fast for testing and development
  - Uses regex and keyword matching

**Extraction Output:**
```python
{
    'incident_date': datetime | None,
    'incident_date_confidence': float [0-1],
    'incident_location': str | None,
    'incident_location_confidence': float [0-1],
    'incident_description': str | None,
    'incident_description_confidence': float [0-1],
    'damage_type': str (enum value),
    'damage_type_confidence': float [0-1],
    'property_type': str (enum value),
    'property_type_confidence': float [0-1],
    'room_location': str | None,
    'room_location_confidence': float [0-1],
    'estimated_repair_cost': float | None,
    'estimated_repair_cost_confidence': float [0-1],
    'damage_severity': str (enum value),
    'damage_severity_confidence': float [0-1],
    'extraction_time_ms': float
}
```

**No Hallucination Policy:**
- Uses 'unknown' enum values when uncertain
- Sets confidence < 0.5 for uncertain extractions
- Returns None for missing optional fields

---

### 3. Image Analyzer Module
**File:** [src/fnol/image_analyzer.py](../src/fnol/image_analyzer.py)

**Purpose:** Analyzes images to classify types and detect damage

**Key Classes:**
- `ImageAnalyzer` (ABC): Base interface for all analyzers
- `ImageAnalysisResult`: Result object with classification and confidence
- `BaselineImageAnalyzer`: **v1 implementation** using filename heuristics
  - Classifies: damage_photo | receipt | document | other
  - Detects damage presence
  - Reads file metadata
  - No ML model required
- `VisionModelImageAnalyzer`: **Placeholder** for future vision model integration

**Interface Design:**
The interface is designed to allow easy swapping from baseline heuristics to real vision models (Claude Vision, GPT-4V, LLaVA) without changing the pipeline code.

**Baseline Classification Rules:**
- Files with "damage", "photo", "broken" → `damage_photo`
- Files with "receipt", "estimate", "invoice" → `receipt`
- Files with "report", "document", "police" → `document`
- Image extensions (.jpg, .png) default to `damage_photo`

---

### 4. Fusion Module
**File:** [src/fnol/fusion.py](../src/fnol/fusion.py)

**Purpose:** Combines text extraction and image analysis into final claim

**Key Classes:**
- `ClaimFusion`: Main fusion engine

**Responsibilities:**
1. **Provenance Generation**: Creates Provenance objects for each extracted field
   - Links confidence scores from text extraction
   - References source modality (TEXT | IMAGE | DOCUMENT)
   - Provides pointer to source location
2. **Evidence Checklist**: Builds EvidenceChecklist from image analysis
   - Counts damage photos
   - Detects receipts/estimates
   - Detects incident reports/documents
   - Lists missing evidence
3. **Consistency Checking**: Detects conflicts and issues
   - Low confidence extractions (< 0.3)
   - Missing critical evidence
   - Incomplete information

**Output:** Complete PropertyDamageClaim with all provenance attached

---

### 5. Pipeline Module
**File:** [src/fnol/pipeline.py](../src/fnol/pipeline.py)

**Purpose:** Main pipeline orchestration and public API

**Key Classes:**
- `ExtractionPipeline`: Orchestrates all components
- `parse_claim()`: Convenience function (main public API)

**Public API:**
```python
from src.fnol import parse_claim

claim = parse_claim(
    text="Pipe burst causing water damage to ceiling",
    image_paths=["damage1.jpg", "damage2.jpg"],
    claimant_info={"name": "John Doe", "policy_number": "POL-123"}
)

# Result: PropertyDamageClaim (validated, with provenance)
print(claim.claim_id)
print(claim.incident.damage_type)
print(claim.evidence.missing_evidence)
```

**Performance Tracking:**
- Logs latency for each stage
- Reports total processing time
- Tracks metrics (damage type, photo count, conflicts, etc.)

---

### 6. CLI Module
**File:** [src/fnol/cli.py](../src/fnol/cli.py) + [src/fnol/__main__.py](../src/fnol/__main__.py)

**Purpose:** Command-line interface for parsing claims

**Usage:**
```bash
# Inline text
python -m src.fnol --text "Water damage from burst pipe" --images img1.jpg img2.jpg

# Text file
python -m src.fnol --text-file fixtures/claim01.txt --images fixtures/*.jpg

# With claimant info
python -m src.fnol \
    --text-file fixtures/claim01.txt \
    --claimant-name "Sarah Johnson" \
    --policy-number "POL-123456" \
    --images fixtures/damage1.jpg

# Pretty print
python -m src.fnol --text "Fire damage" --pretty

# Output to file
python -m src.fnol --text "Storm damage" --output claim.json

# Verbose logging
python -m src.fnol --text "Water leak" --verbose
```

**Options:**
- `--text` / `--text-file`: Claim description (mutually exclusive)
- `--images`: Space-separated list of image paths
- `--claimant-name`, `--policy-number`, `--contact-phone`, `--contact-email`
- `--llm-provider`: claude | openai | mock (default: mock)
- `--llm-model`: Specific model to use
- `--api-key`: API key (or use environment variables)
- `--output`: Output file path
- `--pretty`: Pretty print JSON
- `--verbose`: Enable debug logging

---

### 7. Test Fixtures
**Directory:** [fixtures/](../fixtures/)

**Contents:**
- 10 text files with diverse claim scenarios
- 10 placeholder image files (for baseline testing)
- README with usage examples

**Test Cases:**
1. **claim01_water_damage.txt** - Complete, detailed (580 chars)
2. **claim02_broken_window.txt** - Moderate detail (338 chars)
3. **claim03_fire_damage.txt** - Severe damage, very detailed (459 chars)
4. **claim04_storm_roof.txt** - Missing cost estimate (308 chars)
5. **claim05_vandalism_door.txt** - With police report (357 chars)
6. **claim06_minimal_info.txt** - Minimal (41 chars) - edge case
7. **claim07_detailed_water.txt** - Appliance leak (429 chars)
8. **claim08_wall_damage.txt** - Minor damage (262 chars)
9. **claim09_ambiguous.txt** - Very ambiguous (130 chars) - low confidence expected
10. **claim10_no_cost.txt** - No cost provided (319 chars)

---

### 8. Comprehensive Tests
**File:** [tests/test_pipeline.py](../tests/test_pipeline.py)

**Test Coverage:** 32 tests (all passing ✅)

**Test Categories:**

1. **Schema Validation** (3 tests)
   - Basic parsing validates
   - With images validates
   - With claimant info validates

2. **Provenance** (3 tests)
   - Damage type has provenance
   - Property type has provenance
   - Optional fields have provenance when populated

3. **Latency Measurement** (3 tests)
   - Extraction time logged
   - Completes in reasonable time
   - Metrics include timing

4. **10 Fixture Tests** (10 tests)
   - Each fixture file tested individually
   - Validates schema conformance
   - Checks expected damage types
   - Verifies evidence tracking

5. **Edge Cases** (5 tests)
   - Empty text
   - Non-existent images
   - Many images (5+)
   - Unicode characters
   - Very long text (2600+ chars)

6. **Convenience API** (2 tests)
   - parse_claim() function
   - Without explicit config

7. **Evidence Checklist** (3 tests)
   - No evidence flags missing
   - Damage photos detected
   - Receipt/estimate detected

8. **Consistency Checking** (3 tests)
   - Low confidence flagged
   - Missing photos flagged
   - Complete claim has fewer issues

---

## Definition of Done ✅

✅ **Modular skeleton** with clear separation:
  - text_extractor.py (LLM + mock)
  - image_analyzer.py (baseline + swappable interface)
  - fusion.py (provenance + evidence + consistency)

✅ **LLM integration** for text extraction:
  - Claude and OpenAI support
  - Structured JSON output
  - Conservative confidence scoring

✅ **Baseline image analyzer**:
  - Filename heuristics for v1
  - Swappable interface for future vision models
  - No hallucination on missing fields

✅ **Automatic provenance** attached to every populated field:
  - source_modality (TEXT | IMAGE | DOCUMENT)
  - confidence [0.0, 1.0]
  - pointer (source reference)

✅ **10 test fixtures** (text + images)

✅ **32 pytest tests** - all passing:
  - Output validates against schema
  - Required provenance exists
  - Latency measurement logged

✅ **CLI interface**:
  - `python -m src.fnol --text ... --images ...`
  - Prints JSON output
  - Multiple input options

---

## Usage Examples

### 1. Programmatic API

```python
from src.fnol import parse_claim

# Simple example
claim = parse_claim(
    text="Water damage from burst pipe in bathroom ceiling",
    image_paths=["damage1.jpg", "damage2.jpg"]
)

print(f"Claim ID: {claim.claim_id}")
print(f"Damage Type: {claim.incident.damage_type.value}")
print(f"Property Type: {claim.property_damage.property_type.value}")
print(f"Photos: {claim.evidence.damage_photo_count}")
print(f"Missing Evidence: {claim.evidence.missing_evidence}")
print(f"Has Conflicts: {claim.consistency.has_conflicts}")

# With claimant info
claim = parse_claim(
    text="Fire damage in kitchen from unattended stove",
    image_paths=["fire1.jpg", "fire2.jpg"],
    claimant_info={
        "name": "Jane Smith",
        "policy_number": "POL-987654",
        "contact_email": "jane@example.com"
    }
)

# Export as JSON
json_output = claim.json(indent=2)
print(json_output)
```

### 2. CLI Usage

```bash
# Basic usage
python -m src.fnol \
    --text "Ceiling water damage from pipe burst" \
    --images damage1.jpg damage2.jpg \
    --pretty

# With text file
python -m src.fnol \
    --text-file fixtures/claim01_water_damage.txt \
    --images fixtures/damage_ceiling.jpg \
    --claimant-name "Sarah Johnson" \
    --policy-number "POL-123456" \
    --verbose

# Output to file
python -m src.fnol \
    --text "Storm damage to roof" \
    --images roof1.jpg roof2.jpg \
    --output claim_output.json

# Use with real LLM (requires API key)
export ANTHROPIC_API_KEY="your-key-here"
python -m src.fnol \
    --text "Complex damage scenario..." \
    --llm-provider claude \
    --images damage1.jpg damage2.jpg
```

### 3. Run Tests

```bash
# Run all pipeline tests
pytest tests/test_pipeline.py -v

# Run specific test
pytest tests/test_pipeline.py::TestFixtures::test_fixture01_water_damage -v

# Run with coverage
pytest tests/test_pipeline.py --cov=src.fnol --cov-report=html
```

---

## Performance Metrics

**Mock Extractor (baseline, no API calls):**
- Average latency: < 1ms
- Text extraction: ~0.06ms
- Image analysis: ~0.01ms per image
- Fusion: ~0.5ms
- **Total: < 1ms per claim**

**With Real LLM (Claude/OpenAI):**
- Estimated latency: 500-2000ms
- Depends on API response time
- Text extraction dominates (API call)
- Image analysis + fusion still < 1ms

---

## Limitations & Future Work

### v1 Limitations

1. **Image Analysis**: Baseline uses filename heuristics only
   - No actual computer vision
   - Cannot assess damage severity from images
   - Cannot extract text from photos (OCR)

2. **Text Extraction**: Mock extractor is keyword-based
   - No semantic understanding
   - May miss context-dependent information
   - Real LLM required for production quality

3. **Provenance Granularity**: Pointers are coarse
   - "text_span:full" instead of exact character ranges
   - "image_id:filename" instead of bounding boxes

### Future Enhancements

**For Deliverable #3** (Evidence Completeness + Consistency Checker):
- More sophisticated conflict detection
- Cross-field validation rules
- Temporal consistency checks
- Cost reasonability checks

**Beyond Sprint 1:**
1. **Vision Model Integration**
   - Replace BaselineImageAnalyzer with VisionModelImageAnalyzer
   - Use Claude Vision / GPT-4V / LLaVA
   - Extract damage severity from images
   - OCR for receipts and documents

2. **Enhanced Provenance**
   - Exact text span extraction (start/end indices)
   - Image bounding boxes for damage locations
   - Confidence calibration

3. **Multi-document Support**
   - PDF parsing
   - Email thread parsing
   - Attachments extraction

4. **Batch Processing**
   - Process multiple claims in parallel
   - Async API calls

5. **Active Learning**
   - Flag low-confidence extractions for human review
   - Learn from corrections

---

## Dependencies

**Required:**
- pydantic (schema validation)
- Python 3.11+

**Optional (for real LLM):**
- anthropic (for Claude)
- openai (for OpenAI)

**Development:**
- pytest (testing)
- logging (built-in)

---

## Key Design Decisions

1. **Mock as Default**: Use mock extractor by default to enable testing without API keys
2. **Swappable Interfaces**: Abstract base classes allow easy component replacement
3. **Conservative Confidence**: Prefer 'unknown' + low confidence over hallucination
4. **Provenance Everywhere**: Every extracted field has associated provenance
5. **Modular Architecture**: Clear separation allows independent component testing

---

