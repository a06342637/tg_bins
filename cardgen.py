"""Generate synthetic card numbers with a Luhn checksum, without calling any API.

A valid checksum does not imply that a number was issued or can be used to pay.
"""
import re
import secrets

MAX_COUNT = 20
PREFIX_RE = re.compile(r"[0-9]{4,6}\Z")


def luhn_valid(number):
    if not re.fullmatch(r"[0-9]{13,19}", number):
        return False
    total = 0
    for index, digit in enumerate(reversed(number)):
        value = int(digit)
        if index % 2:
            value *= 2
            value -= 9 if value > 9 else 0
        total += value
    return total % 10 == 0


def generate_numbers(prefix, count=3):
    """Keep 4–6 prefix digits; use 15 digits for Amex 34/37, otherwise 16."""
    if not isinstance(prefix, str) or not PREFIX_RE.fullmatch(prefix):
        raise ValueError("前缀必须是 4–6 位数字")
    if type(count) is not int or not 1 <= count <= MAX_COUNT:
        raise ValueError(f"生成数量必须是 1–{MAX_COUNT}")
    length = 15 if prefix.startswith(("34", "37")) else 16
    numbers = []
    seen = set()
    while len(numbers) < count:
        body = prefix + "".join(str(secrets.randbelow(10)) for _ in range(length - len(prefix) - 1))
        total = 0
        for index, digit in enumerate(reversed(body)):
            value = int(digit) * (2 if index % 2 == 0 else 1)
            total += value - 9 if value > 9 else value
        number = body + str((-total) % 10)
        if number not in seen:
            seen.add(number)
            numbers.append(number)
    return numbers
