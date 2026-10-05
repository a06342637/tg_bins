import unittest

from inputparse import extract_prefixes


class InputParsingTests(unittest.TestCase):
    def test_card_first_records_ignore_trailing_fields(self):
        for line in (
            "4111111111111111|12/30|123|VISA|TEST BANK",
            "4111111111111111 12/30 123 TEST BANK",
            "4111111111111111,12/30,123,VISA",
            "4111111111111111----12/30----123",
            "4111111111111111银行说明",
            "  4111111111111111 | TEST BANK  ",
        ):
            with self.subTest(line=line):
                self.assertEqual(extract_prefixes(line), ["411111"])

    def test_grouped_cards_with_and_without_metadata(self):
        for line in (
            "4111 1111 1111 1111", "4111-1111-1111-1111",
            "4111 1111 1111 1111 | 12/30 | 123",
            "4111-1111-1111-1111 12/30 123",
            "4111\t1111\t1111\t1111|VISA",
        ):
            with self.subTest(line=line):
                self.assertEqual(extract_prefixes(line), ["411111"])
        self.assertEqual(extract_prefixes("3782 822463 10005 | AMEX"), ["378282"])

    def test_short_prefixes_do_not_consume_dates(self):
        for prefix in ("4111", "41111", "411111"):
            for suffix in ("", "|12/30|123", " 12/30 123", " 银行说明"):
                self.assertEqual(extract_prefixes(prefix + suffix), [prefix])

    def test_multiline_deduplicates_without_merging_lines(self):
        self.assertEqual(extract_prefixes(
            "4111111111111111|12/30|123\r\n"
            "TEST BANK\n"
            "378282246310005|12/30|1234\n"
            "411111|VISA\n\n"
            "6259\n"
            "4427\n"
        ), ["411111", "378282", "6259", "4427"])

    def test_non_card_leading_lines_are_ignored(self):
        for line in ("", "hello", "卡号 4111111111111111", "@username", "123|TEST", "12/30|123", "４１１１１１１１１１１１１１１１"):
            self.assertEqual(extract_prefixes(line), [])


if __name__ == "__main__":
    unittest.main()
