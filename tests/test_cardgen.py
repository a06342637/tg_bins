import unittest

from cardgen import generate_numbers, luhn_valid


class CardGenerationTests(unittest.TestCase):
    def test_known_checksum_vectors(self):
        self.assertTrue(luhn_valid("4111111111111111"))
        self.assertTrue(luhn_valid("378282246310005"))
        self.assertFalse(luhn_valid("4111111111111112"))
        self.assertFalse(luhn_valid("４１１１１１１１１１１１１１１１"))

    def test_prefix_length_uniqueness_and_independent_checksum(self):
        for prefix in ("4427", "44274", "442742", "3782", "340000", "625981", "002102"):
            with self.subTest(prefix=prefix):
                numbers = generate_numbers(prefix, 20)
                self.assertEqual(len(set(numbers)), 20)
                for number in numbers:
                    self.assertTrue(number.startswith(prefix))
                    self.assertEqual(len(number), 15 if prefix[:2] in ("34", "37") else 16)
                    # Independent left-to-right Luhn calculation.
                    digits = list(map(int, number))
                    transformed = [d * 2 if i % 2 == len(digits) % 2 else d for i, d in enumerate(digits)]
                    self.assertEqual(sum(sum(divmod(d, 10)) for d in transformed) % 10, 0)
                    self.assertTrue(luhn_valid(number))

    def test_invalid_arguments(self):
        for prefix in ("123", "1234567", "abcd", "４４２７", "4427\n", "44 27"):
            with self.assertRaises(ValueError):
                generate_numbers(prefix)
        for count in (0, -1, 21, 3.0, True, "3"):
            with self.assertRaises(ValueError):
                generate_numbers("442742", count)

    def test_default_count(self):
        self.assertEqual(len(generate_numbers("442742")), 3)


if __name__ == "__main__":
    unittest.main()
