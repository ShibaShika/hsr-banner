import unittest
from update_gist import validate_data_integrity, clean_wikitext_value, sanitize_name

class TestSanitizeName(unittest.TestCase):
    def test_empty_or_none(self):
        self.assertEqual(sanitize_name(""), "")
        self.assertEqual(sanitize_name(None), "")

    def test_normal_alphanumeric(self):
        self.assertEqual(sanitize_name("Name123"), "name123")
        self.assertEqual(sanitize_name("test"), "test")

    def test_mixed_case(self):
        self.assertEqual(sanitize_name("CaMeLcAsE"), "camelcase")
        self.assertEqual(sanitize_name("UPPER"), "upper")

    def test_special_characters(self):
        self.assertEqual(sanitize_name("name!@#$%^*()_+-="), "name")
        self.assertEqual(sanitize_name("name with spaces"), "namewithspaces")
        self.assertEqual(sanitize_name("name.with.dots"), "namewithdots")
        self.assertEqual(sanitize_name("name-with-dashes"), "namewithdashes")

    def test_ampersand(self):
        self.assertEqual(sanitize_name("Tom & Jerry"), "tomandjerry")
        self.assertEqual(sanitize_name("A&B&C"), "aandbandc")

    def test_non_string_types(self):
        self.assertEqual(sanitize_name(12345), "12345")
        self.assertEqual(sanitize_name(3.14159), "314159")
        self.assertEqual(sanitize_name(True), "true")

class TestValidateDataIntegrity(unittest.TestCase):
    def setUp(self):
        self.original_chars = [
            {'name': 'CharA', 'runs': ['1.0上']},
            {'name': 'CharB', 'runs': ['1.0下']}
        ]
        self.original_patches = [
            {'patch': '1.0上', 'date': '23/04/26'},
            {'patch': '1.0下', 'date': '23/05/17'}
        ]

        self.valid_new_chars = [
            {'name': 'CharA', 'runs': ['1.0上', '1.1上']},
            {'name': 'CharB', 'runs': ['1.0下']},
            {'name': 'CharC', 'runs': ['1.1上']}
        ]
        self.valid_new_patches = [
            {'patch': '1.0上', 'date': '23/04/26'},
            {'patch': '1.0下', 'date': '23/05/17'},
            {'patch': '1.1上', 'date': '23/06/07'}
        ]

    def test_rule_1_character_count(self):
        # Pass fewer new characters than original characters
        new_chars_fewer = [{'name': 'CharA', 'runs': ['1.0上']}]
        with self.assertRaises(AssertionError) as context:
            validate_data_integrity(
                self.original_chars,
                self.original_patches,
                new_chars_fewer,
                self.valid_new_patches
            )
        self.assertIn("門檻 1 失敗：角色總數異常減少", str(context.exception))

    def test_rule_2_patch_count(self):
        # Pass fewer new patches than original patches
        new_patches_fewer = [{'patch': '1.0上', 'date': '23/04/26'}]
        with self.assertRaises(AssertionError) as context:
            validate_data_integrity(
                self.original_chars,
                self.original_patches,
                self.valid_new_chars,
                new_patches_fewer
            )
        self.assertIn("門檻 2 失敗：版本總數異常減少", str(context.exception))

    def test_rule_3_invalid_patch_name(self):
        # Pass a patch with an invalid name
        new_patches_invalid_name = self.valid_new_patches.copy()
        new_patches_invalid_name.append({'patch': 'invalid_name', 'date': '23/06/28'})
        with self.assertRaises(AssertionError) as context:
            validate_data_integrity(
                self.original_chars,
                self.original_patches,
                self.valid_new_chars,
                new_patches_invalid_name
            )
        self.assertIn("門檻 3 失敗：版本名稱不合規", str(context.exception))

    def test_rule_3_invalid_patch_date(self):
        # Pass a patch with an invalid date
        new_patches_invalid_date = self.valid_new_patches.copy()
        new_patches_invalid_date.append({'patch': '1.1下', 'date': 'invalid_date'})
        with self.assertRaises(AssertionError) as context:
            validate_data_integrity(
                self.original_chars,
                self.original_patches,
                self.valid_new_chars,
                new_patches_invalid_date
            )
        self.assertIn("門檻 3 失敗：版本日期不合規", str(context.exception))

    def test_rule_3_duplicate_patch(self):
        # Pass duplicate patch names
        new_patches_duplicate = self.valid_new_patches.copy()
        new_patches_duplicate.append({'patch': '1.0上', 'date': '23/04/26'})
        with self.assertRaises(AssertionError) as context:
            validate_data_integrity(
                self.original_chars,
                self.original_patches,
                self.valid_new_chars,
                new_patches_duplicate
            )
        self.assertIn("門檻 3 失敗：版本重複定義", str(context.exception))

    def test_rule_4_orphan_run(self):
        # Pass a character with a run that doesn't exist in new_patches
        new_chars_orphan = self.valid_new_chars.copy()
        new_chars_orphan.append({'name': 'CharD', 'runs': ['9.9上']})
        with self.assertRaises(AssertionError) as context:
            validate_data_integrity(
                self.original_chars,
                self.original_patches,
                new_chars_orphan,
                self.valid_new_patches
            )
        self.assertIn("門檻 4 失敗", str(context.exception))
        self.assertIn("不存在於版本清單中", str(context.exception))

    def test_rule_5_missing_historical_run(self):
        # Pass a character that is missing a run present in original_chars
        new_chars_missing_run = [
            {'name': 'CharA', 'runs': []}, # Missing '1.0上'
            {'name': 'CharB', 'runs': ['1.0下']}
        ]
        with self.assertRaises(AssertionError) as context:
            validate_data_integrity(
                self.original_chars,
                self.original_patches,
                new_chars_missing_run,
                self.valid_new_patches
            )
        self.assertIn("門檻 5 失敗", str(context.exception))
        self.assertIn("歷史排程遺失", str(context.exception))

    def test_happy_path(self):
        # Pass valid data that should not raise any exceptions
        try:
            validate_data_integrity(
                self.original_chars,
                self.original_patches,
                self.valid_new_chars,
                self.valid_new_patches
            )
        except AssertionError as e:
            self.fail(f"validate_data_integrity raised AssertionError unexpectedly: {e}")


class TestCleanWikitextValue(unittest.TestCase):
    def test_none_or_empty(self):
        self.assertEqual(clean_wikitext_value(None), "")
        self.assertEqual(clean_wikitext_value(""), "")

    def test_basic_text(self):
        self.assertEqual(clean_wikitext_value("Simple text"), "Simple text")

    def test_wikitext_link(self):
        self.assertEqual(clean_wikitext_value("[[Link]]"), "Link")

    def test_wikitext_link_alias(self):
        self.assertEqual(clean_wikitext_value("[[Real Page|Display Name]]"), "Display Name")

    def test_multiple_links(self):
        self.assertEqual(clean_wikitext_value("[[Page1]] and [[Page2|Alias2]]"), "Page1 and Alias2")

    def test_html_comments(self):
        self.assertEqual(clean_wikitext_value("Text <!-- hidden comment --> here"), "Text  here")
        self.assertEqual(clean_wikitext_value("<!-- hidden comment -->"), "")
        self.assertEqual(clean_wikitext_value("A<!-- comment 1 -->B<!-- comment 2 -->C"), "ABC")

    def test_strip_whitespace(self):
        self.assertEqual(clean_wikitext_value("  padded text  \n"), "padded text")

    def test_replace_bullets(self):
        self.assertEqual(clean_wikitext_value("Name·With·Dots"), "Name•With•Dots")
        self.assertEqual(clean_wikitext_value("Name・With・Japanese・Dots"), "Name•With•Japanese•Dots")

    def test_complex_combined(self):
        val = "  <!-- delete me --> [[Aeon (Path)|Aeon]]·[[Emanator]] \n"
        self.assertEqual(clean_wikitext_value(val), "Aeon•Emanator")


if __name__ == '__main__':
    unittest.main()
