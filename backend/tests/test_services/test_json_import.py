"""Tests for JSON import service."""
import pytest

from app.services.json_import import validate_problem_json


class TestValidateProblemJson:
    def test_valid_minimal_problem(self):
        data = {
            "title": "Test Problem",
            "description_md": "This is a test",
            "time_limit_sec": 1.0,
            "memory_limit_mb": 256,
            "max_points": 100,
            "allowed_languages": ["python3"],
            "score_tiers": [
                {"min_attempts": 1, "max_attempts": 5, "score_ratio": 100}
            ],
        }
        violations = validate_problem_json(data)
        assert violations == []

    def test_missing_required_field(self):
        data = {
            "title": "Test Problem",
            "description_md": "This is a test",
            "time_limit_sec": 1.0,
            # missing memory_limit_mb
            "max_points": 100,
            "allowed_languages": ["python3"],
            "score_tiers": [
                {"min_attempts": 1, "max_attempts": 5, "score_ratio": 100}
            ],
        }
        violations = validate_problem_json(data)
        assert any(v["field"] == "memory_limit_mb" for v in violations)

    def test_empty_title(self):
        data = {
            "title": "   ",
            "description_md": "This is a test",
            "time_limit_sec": 1.0,
            "memory_limit_mb": 256,
            "max_points": 100,
            "allowed_languages": ["python3"],
            "score_tiers": [
                {"min_attempts": 1, "max_attempts": 5, "score_ratio": 100}
            ],
        }
        violations = validate_problem_json(data)
        assert any(v["field"] == "title" for v in violations)

    def test_time_limit_too_small(self):
        data = {
            "title": "Test Problem",
            "description_md": "This is a test",
            "time_limit_sec": 0.1,
            "memory_limit_mb": 256,
            "max_points": 100,
            "allowed_languages": ["python3"],
            "score_tiers": [
                {"min_attempts": 1, "max_attempts": 5, "score_ratio": 100}
            ],
        }
        violations = validate_problem_json(data)
        assert any(v["field"] == "time_limit_sec" for v in violations)

    def test_time_limit_too_large(self):
        data = {
            "title": "Test Problem",
            "description_md": "This is a test",
            "time_limit_sec": 15.0,
            "memory_limit_mb": 256,
            "max_points": 100,
            "allowed_languages": ["python3"],
            "score_tiers": [
                {"min_attempts": 1, "max_attempts": 5, "score_ratio": 100}
            ],
        }
        violations = validate_problem_json(data)
        assert any(v["field"] == "time_limit_sec" for v in violations)

    def test_memory_limit_too_small(self):
        data = {
            "title": "Test Problem",
            "description_md": "This is a test",
            "time_limit_sec": 1.0,
            "memory_limit_mb": 16,
            "max_points": 100,
            "allowed_languages": ["python3"],
            "score_tiers": [
                {"min_attempts": 1, "max_attempts": 5, "score_ratio": 100}
            ],
        }
        violations = validate_problem_json(data)
        assert any(v["field"] == "memory_limit_mb" for v in violations)

    def test_invalid_language(self):
        data = {
            "title": "Test Problem",
            "description_md": "This is a test",
            "time_limit_sec": 1.0,
            "memory_limit_mb": 256,
            "max_points": 100,
            "allowed_languages": ["python3", "rust"],
            "score_tiers": [
                {"min_attempts": 1, "max_attempts": 5, "score_ratio": 100}
            ],
        }
        violations = validate_problem_json(data)
        assert any(v["field"] == "allowed_languages" for v in violations)

    def test_no_languages(self):
        data = {
            "title": "Test Problem",
            "description_md": "This is a test",
            "time_limit_sec": 1.0,
            "memory_limit_mb": 256,
            "max_points": 100,
            "allowed_languages": [],
            "score_tiers": [
                {"min_attempts": 1, "max_attempts": 5, "score_ratio": 100}
            ],
        }
        violations = validate_problem_json(data)
        assert any(v["field"] == "allowed_languages" for v in violations)

    def test_no_score_tiers(self):
        data = {
            "title": "Test Problem",
            "description_md": "This is a test",
            "time_limit_sec": 1.0,
            "memory_limit_mb": 256,
            "max_points": 100,
            "allowed_languages": ["python3"],
            "score_tiers": [],
        }
        violations = validate_problem_json(data)
        assert any(v["field"] == "score_tiers" for v in violations)

    def test_overlapping_score_tiers(self):
        data = {
            "title": "Test Problem",
            "description_md": "This is a test",
            "time_limit_sec": 1.0,
            "memory_limit_mb": 256,
            "max_points": 100,
            "allowed_languages": ["python3"],
            "score_tiers": [
                {"min_attempts": 1, "max_attempts": 5, "score_ratio": 100},
                {"min_attempts": 3, "max_attempts": 8, "score_ratio": 80},  # overlap
            ],
        }
        violations = validate_problem_json(data)
        assert any(v["field"] == "score_tiers" and "gap or overlap" in v["message"] for v in violations)

    def test_max_less_than_min_attempts(self):
        data = {
            "title": "Test Problem",
            "description_md": "This is a test",
            "time_limit_sec": 1.0,
            "memory_limit_mb": 256,
            "max_points": 100,
            "allowed_languages": ["python3"],
            "score_tiers": [
                {"min_attempts": 10, "max_attempts": 5, "score_ratio": 100},
            ],
        }
        violations = validate_problem_json(data)
        assert any(v["field"] == "score_tiers" and "max_attempts" in v["message"] for v in violations)

    def test_valid_with_optional_fields(self):
        data = {
            "title": "Test Problem",
            "description_md": "This is a test",
            "input_description_md": "Input format",
            "output_description_md": "Output format",
            "time_limit_sec": 1.0,
            "memory_limit_mb": 256,
            "max_points": 100,
            "allowed_languages": ["python3", "java17"],
            "score_tiers": [
                {"min_attempts": 1, "max_attempts": 5, "score_ratio": 100},
                {"min_attempts": 6, "max_attempts": 10, "score_ratio": 80},
                {"min_attempts": 11, "max_attempts": None, "score_ratio": 60},
            ],
        }
        violations = validate_problem_json(data)
        assert violations == []
