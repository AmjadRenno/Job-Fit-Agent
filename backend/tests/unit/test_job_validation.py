from app.domain.job_validation import (
    MIN_JOB_DESCRIPTION_LENGTH,
    validate_job_description,
)


def test_empty_job_description_is_invalid() -> None:
    result = validate_job_description(" \n\t ")

    assert result.is_valid is False
    assert result.error_code == "empty_job_description"
    assert result.normalized_text is None


def test_short_job_description_is_invalid() -> None:
    result = validate_job_description("Python developer")

    assert result.is_valid is False
    assert result.error_code == "job_description_too_short"
    assert result.normalized_text == "Python developer"


def test_description_at_minimum_length_is_valid() -> None:
    description = "x" * MIN_JOB_DESCRIPTION_LENGTH

    result = validate_job_description(description)

    assert result.is_valid is True
    assert result.error_code is None
    assert result.normalized_text == description


def test_validation_normalizes_whitespace_before_length_check() -> None:
    result = validate_job_description(
        "  We are hiring a Python engineer.\n\n Build APIs with FastAPI.  "
    )

    assert result.is_valid is True
    assert result.normalized_text == (
        "We are hiring a Python engineer. Build APIs with FastAPI."
    )
