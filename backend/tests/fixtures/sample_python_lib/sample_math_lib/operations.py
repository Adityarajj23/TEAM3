"""Mathematical and arithmetic operations."""
import math


def add(a: float, b: float) -> float:
    """Returns the sum of two numbers."""
    return a + b


def multiply(a: float, b: float) -> float:
    """Returns the product of two numbers."""
    return a * b


def is_prime(n: int) -> bool:
    """Returns True if n is a prime number, False otherwise."""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def calculate_hypotenuse(a: float, b: float) -> float:
    """Calculates the hypotenuse length of a right triangle using Pythagorean theorem."""
    if a < 0 or b < 0:
        raise ValueError("Triangle sides must be non-negative")
    return math.sqrt(a * a + b * b)

