import csv
import unittest
from pathlib import Path

from render import render_result
from zh import COUNTRY_ZH, country_label, country_zh


class CountryTranslationTests(unittest.TestCase):
    def test_trinidad_and_tobago_in_rendered_result(self):
        result = render_result({
            "bin": "544382", "country_code": "TT", "country_name": "Trinidad and Tobago",
        })
        english, chinese = result.split("[中文]")
        self.assertIn("Country : Trinidad and Tobago 🇹🇹 (TT)", english)
        self.assertIn("国家    : 特立尼达和多巴哥 🇹🇹 (TT)", chinese)
        self.assertNotIn("Trinidad and Tobago", chinese)

    def test_previously_missing_countries(self):
        for code, name in {
            "TT": "特立尼达和多巴哥", "BS": "巴哈马", "BB": "巴巴多斯",
            "MU": "毛里求斯", "HR": "克罗地亚", "LV": "拉脱维亚",
        }.items():
            with self.subTest(code=code):
                self.assertEqual(country_zh(code), name)

    def test_country_code_normalization_and_existing_short_names(self):
        self.assertEqual(country_zh(" tt ", "incorrect name"), "特立尼达和多巴哥")
        self.assertEqual(country_zh("UK"), "英国")
        self.assertEqual(country_zh("EL"), "希腊")
        for code, name in {"CN": "中国", "HK": "香港", "MO": "澳门", "US": "美国"}.items():
            self.assertEqual(country_zh(code), name)

    def test_missing_code_matches_english_name_variations(self):
        for name in ("Trinidad and Tobago", "TRINIDAD AND TOBAGO", "  Trinidad & Tobago  "):
            self.assertEqual(country_zh(None, name), "特立尼达和多巴哥")
        self.assertEqual(country_zh("ZZ", "United States"), "美国")
        self.assertEqual(country_zh("", "Cote d'Ivoire"), "科特迪瓦")

    def test_unknown_country_preserves_original_instead_of_guessing(self):
        self.assertEqual(country_zh("XX", "Unlisted territory"), "Unlisted territory")
        self.assertEqual(country_zh("", "Unlisted territory"), "Unlisted territory")
        self.assertEqual(country_zh(None, None), "-")

    def test_logs_use_same_translation(self):
        self.assertEqual(country_label("Trinidad and Tobago", "TT"), "特立尼达和多巴哥/Trinidad and Tobago (TT)")
        self.assertEqual(country_label("Trinidad and Tobago", None), "特立尼达和多巴哥/Trinidad and Tobago")
        self.assertEqual(country_label("特立尼达和多巴哥", "TT"), "特立尼达和多巴哥 (TT)")
        self.assertEqual(country_label(None, "XX"), "- (XX)")

    def test_all_country_codes_in_bundled_bin_database_have_chinese_names(self):
        path = Path(__file__).resolve().parents[1] / "data" / "bin-list-data.csv"
        with path.open(encoding="utf-8", newline="") as stream:
            codes = {row["isoCode2"].strip().upper() for row in csv.DictReader(stream)} - {""}
        self.assertFalse(codes - COUNTRY_ZH.keys())
        self.assertGreaterEqual(len(COUNTRY_ZH), 249)
        for code in codes:
            self.assertRegex(country_zh(code), r"[\u4e00-\u9fff]")


if __name__ == "__main__":
    unittest.main()
