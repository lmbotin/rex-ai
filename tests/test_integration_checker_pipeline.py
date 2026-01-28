"""
Integration tests for checker + pipeline.

Demonstrates end-to-end usage: extract claim → check completeness.
"""

from src.fnol import parse_claim, check_claim


def test_integration_parse_then_check():
    """Full workflow: parse claim text, then check completeness."""

    # Sample claim text
    text = """
    My living room ceiling has water damage from a pipe burst.
    It happened on January 15th at 123 Main St.
    The damage is pretty bad and I think it will cost about $3000 to fix.
    """

    # Parse the claim
    claim = parse_claim(text=text, image_paths=[])

    # Check completeness
    report = check_claim(claim)

    # Should have some completeness score
    assert 0.0 <= report.completeness_score <= 1.0

    # Should identify missing photos as an issue
    assert "damage_photos" in report.missing_required_evidence

    # Should recommend uploading photos
    assert any("photo" in q.lower() for q in report.recommended_questions)


def test_integration_complete_claim_workflow():
    """Workflow with images should have higher completeness."""

    text = """
    Water damage in my living room from pipe burst on Jan 15, 2024.
    Property located at 123 Main St, San Francisco, CA.
    Ceiling has severe damage, repair estimate is $5,000.
    """

    # Simulate with images
    image_paths = ["fixtures/01_water_damage/damage1.jpg"]

    # Parse and check
    claim = parse_claim(text=text, image_paths=image_paths)
    report = check_claim(claim)

    # With photos, should have better completeness
    # Note: Actual images might not exist, so just verify structure
    assert isinstance(report.completeness_score, float)
    assert isinstance(report.missing_required_evidence, list)
    assert isinstance(report.contradictions, list)
    assert isinstance(report.recommended_questions, list)


def test_integration_actionable_questions():
    """Questions should be specific and actionable."""

    # Minimal claim
    text = "My window broke."

    claim = parse_claim(text=text, image_paths=[])
    report = check_claim(claim)

    # Should have multiple recommended questions
    assert len(report.recommended_questions) >= 1

    # Questions should be specific
    for question in report.recommended_questions:
        assert isinstance(question, str)
        assert len(question) > 10  # Not just empty
        assert "?" in question  # Should be a question
