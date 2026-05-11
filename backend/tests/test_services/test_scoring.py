"""Tests for scoring service."""
import pytest

from app.models.problem import AttemptScoreTier
from app.services.scoring import compute_final_score, find_score_tier


class MockTier:
    def __init__(self, min_attempts, max_attempts, score_ratio):
        self.min_attempts = min_attempts
        self.max_attempts = max_attempts
        self.score_ratio = score_ratio


class TestFindScoreTier:
    def test_find_tier_first_attempt(self):
        tiers = [
            MockTier(1, 5, 100),
            MockTier(6, 10, 80),
            MockTier(11, None, 60),
        ]
        tier = find_score_tier(1, tiers)
        assert tier is not None
        assert tier.score_ratio == 100

    def test_find_tier_middle_range(self):
        tiers = [
            MockTier(1, 5, 100),
            MockTier(6, 10, 80),
            MockTier(11, None, 60),
        ]
        tier = find_score_tier(7, tiers)
        assert tier is not None
        assert tier.score_ratio == 80

    def test_find_tier_unbounded_max(self):
        tiers = [
            MockTier(1, 5, 100),
            MockTier(6, 10, 80),
            MockTier(11, None, 60),
        ]
        tier = find_score_tier(100, tiers)
        assert tier is not None
        assert tier.score_ratio == 60

    def test_find_tier_exact_boundary(self):
        tiers = [
            MockTier(1, 5, 100),
            MockTier(6, 10, 80),
        ]
        tier = find_score_tier(5, tiers)
        assert tier is not None
        assert tier.score_ratio == 100

        tier = find_score_tier(6, tiers)
        assert tier is not None
        assert tier.score_ratio == 80

    def test_find_tier_no_match(self):
        tiers = [
            MockTier(5, 10, 100),
        ]
        tier = find_score_tier(1, tiers)
        assert tier is None

    def test_find_tier_single_tier(self):
        tiers = [MockTier(1, None, 100)]
        tier = find_score_tier(1, tiers)
        assert tier is not None
        assert tier.score_ratio == 100


class TestComputeFinalScore:
    def test_compute_with_tier(self):
        tier = MockTier(1, 5, 100)
        score = compute_final_score(100.0, tier)
        assert score == 100.0

    def test_compute_with_ratio_80(self):
        tier = MockTier(6, 10, 80)
        score = compute_final_score(100.0, tier)
        assert score == 80.0

    def test_compute_with_ratio_60(self):
        tier = MockTier(11, None, 60)
        score = compute_final_score(100.0, tier)
        assert score == 60.0

    def test_compute_with_custom_max_points(self):
        tier = MockTier(1, 5, 100)
        score = compute_final_score(50.0, tier)
        assert score == 50.0

    def test_compute_with_none_tier(self):
        score = compute_final_score(100.0, None)
        assert score == 0.0

    def test_compute_rounding(self):
        tier = MockTier(1, None, 33.3)
        score = compute_final_score(100.0, tier)
        assert score == 33.3
