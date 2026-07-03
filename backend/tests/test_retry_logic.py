import pytest
from app.retry_logic import compute_backoff_seconds


def test_fixed_strategy():
    assert compute_backoff_seconds("fixed", base_delay=10, attempt_count=1) == 10


def test_linear_strategy():
    assert compute_backoff_seconds("linear", base_delay=10, attempt_count=3) == 30


def test_exponential_strategy():
    assert compute_backoff_seconds("exponential", base_delay=10, attempt_count=3) == 40


def test_unknown_strategy_raises():
    with pytest.raises(ValueError):
        compute_backoff_seconds("magic", base_delay=10, attempt_count=1)