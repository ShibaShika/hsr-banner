import unittest
from update_gist import validate_data_integrity

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

if __name__ == '__main__':
    unittest.main()
