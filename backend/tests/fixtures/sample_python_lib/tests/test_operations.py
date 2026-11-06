"""Unit tests for sample math operations."""
import pytest
from sample_math_lib.operations import add, multiply, is_prime, calculate_hypotenuse


def test_add_positive_numbers():
    assert add(2, 3) == 5


def test_multiply_numbers():
    assert multiply(4, 5) == 20


def test_is_prime_true_cases():
    assert is_prime(2) is True
    assert is_prime(17) is True
    assert is_prime(19) is True


def test_is_prime_false_cases():
    assert is_prime(1) is False
    assert is_prime(4) is False
    assert is_prime(15) is False


def test_calculate_hypotenuse_valid():
    assert calculate_hypotenuse(3.0, 4.0) == 5.0


def test_calculate_hypotenuse_negative_raises():
    with pytest.raises(ValueError):
        calculate_hypotenuse(-1.0, 4.0)

