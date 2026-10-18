import unittest
from datetime import datetime
from unittest.mock import patch, mock_open, MagicMock
from bs4 import BeautifulSoup
from update_gist import validate_data_integrity, clean_wikitext_value, sanitize_name, normalize_cjk_name, normalize_patch_date, parse_local_js_array, execute_auto_update, fetch_fandom_schedules_and_patches, serialize_js_file, contains_cjk, _format_summary_text, parse_warp_list_tables

class TestFormatSummaryText(unittest.TestCase):
    def test_empty_logs(self):
        result = _format_summary_text([], [], [], [], [])
        self.assertEqual(result, "")

    def test_some_logs(self):
        result = _format_summary_text(
            ["2.0上", "2.0下"],
            [],
            ["新角色A", "新角色B"],
            [],
            []
        )
        expected = "🆕 新增版本 (2 個): 2.0上, 2.0下\n✨ 發現新角色 (2 位):\n  • 新角色A\n  • 新角色B"
        self.assertEqual(result, expected)

    def test_all_logs(self):
        result = _format_summary_text(
            ["1.0上"],
            ["1.0上日期校正"],
            ["角色A"],
            ["角色B登場"],
            ["角色C繁體化"]
        )
        expected = (
            "🆕 新增版本 (1 個): 1.0上\n"
            "📅 版本日期校正 (1 項):\n  • 1.0上日期校正\n"
            "✨ 發現新角色 (1 位):\n  • 角色A\n"
            "📅 新增排程登場 (1 項):\n  • 角色B登場\n"
            "🔄 名稱繁體中文化 (1 位):\n  • 角色C繁體化"
        )
        self.assertEqual(result, expected)

class TestParseLocalJsArray(unittest.TestCase):
    @patch('os.path.exists', return_value=False)
    def test_file_not_found(self, mock_exists):
        result = parse_local_js_array("dummy.js", "MY_VAR")
        self.assertEqual(result, [])

    @patch('os.path.exists', return_value=True)
    def test_variable_not_found(self, mock_exists):
        js_content = "const OTHER_VAR = [];"
        with patch('builtins.open', mock_open(read_data=js_content)):
            result = parse_local_js_array("dummy.js", "MY_VAR")
            self.assertEqual(result, [])

    @patch('os.path.exists', return_value=True)
    def test_valid_js_array_simple(self, mock_exists):
        js_content = """
        const MY_VAR = [
            { id: 1, name: 'Alice' },
            { id: 2, name: "Bob" }
        ];
        """
        with patch('builtins.open', mock_open(read_data=js_content)):
            result = parse_local_js_array("dummy.js", "MY_VAR")
            self.assertEqual(result, [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}])

    @patch('os.path.exists', return_value=True)
    def test_valid_js_array_complex(self, mock_exists):
        js_content = """
        const MY_VAR = [
            {
                name: "CharA",
                runs: ["1.0上", "1.1下"],
                info: { path: "Destruction", elem: 'Fire' }
            },
            {
                name: 'CharB',
                runs: ['2.0上'],
                info: { path: 'Erudition', elem: "Ice" }
            }
        ];
        const OTHER = [];
        """
        with patch('builtins.open', mock_open(read_data=js_content)):
            result = parse_local_js_array("dummy.js", "MY_VAR")
            expected = [
                {
                    'name': 'CharA',
                    'runs': ['1.0上', '1.1下'],
                    'info': {'path': 'Destruction', 'elem': 'Fire'}
                },
                {
                    'name': 'CharB',
                    'runs': ['2.0上'],
                    'info': {'path': 'Erudition', 'elem': 'Ice'}
                }
            ]
            self.assertEqual(result, expected)

    @patch('os.path.exists', return_value=True)
    def test_unclosed_array(self, mock_exists):
        js_content = """
        const MY_VAR = [
            { id: 1, name: 'Alice' },
            { id: 2, name: "Bob" }
        """
        with patch('builtins.open', mock_open(read_data=js_content)):
            result = parse_local_js_array("dummy.js", "MY_VAR")
            self.assertEqual(result, [])

    @patch('os.path.exists', return_value=True)
    def test_json_parse_error(self, mock_exists):
        js_content = """
        const MY_VAR = [
            { id: 1, name: 'Alice', },
            invalid_syntax:::
        ];
        """
        with patch('builtins.open', mock_open(read_data=js_content)):
            result = parse_local_js_array("dummy.js", "MY_VAR")
            self.assertEqual(result, [])

    @patch('os.path.exists', return_value=True)
    def test_brackets_inside_strings(self, mock_exists):
        js_content = """
        const MY_VAR = [
            { name: "[test]" },
            { name: "]" }
        ];
        """
        with patch('builtins.open', mock_open(read_data=js_content)):
            result = parse_local_js_array("dummy.js", "MY_VAR")
            self.assertEqual(result, [{'name': '[test]'}, {'name': ']'}])


class TestNormalizeCjkName(unittest.TestCase):
    def test_empty_or_none(self):
        self.assertEqual(normalize_cjk_name(""), "")
        self.assertEqual(normalize_cjk_name(None), "")

    def test_normal_cjk_name(self):
        self.assertEqual(normalize_cjk_name("丹恆"), "丹恆")

    def test_interpuncts(self):
        # Test ・ (U+30FB), · (U+00B7), • (U+2022)
        self.assertEqual(normalize_cjk_name("丹・恆"), "丹恆")
        self.assertEqual(normalize_cjk_name("丹·恆"), "丹恆")
        self.assertEqual(normalize_cjk_name("丹•恆"), "丹恆")
        self.assertEqual(normalize_cjk_name("丹・·•恆"), "丹恆")

    def test_whitespace(self):
        self.assertEqual(normalize_cjk_name("丹 恆"), "丹恆")
        self.assertEqual(normalize_cjk_name("  丹\t恆\n "), "丹恆")

    def test_combined_interpuncts_and_whitespace(self):
        self.assertEqual(normalize_cjk_name(" 丹 ・ 恆 "), "丹恆")

    def test_non_string_types(self):
        self.assertEqual(normalize_cjk_name(12345), "12345")


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

    def test_preview_chars_and_patches_can_be_adjusted_or_removed(self):
        orig_chars = self.original_chars + [
            {'name': 'PreviewChar1', 'runs': ['1.1上'], 'isPreview': True},
            {'name': 'PreviewChar2', 'runs': ['1.1下'], 'isPreview': True}
        ]
        orig_patches = self.original_patches + [
            {'patch': '1.1上', 'date': '23/06/07', 'isPreview': True},
            {'patch': '1.1下', 'date': '23/06/28', 'isPreview': True}
        ]
        # PreviewChar2 removed, PreviewChar1 schedule changed from 1.1上 to 1.1下, 1.1上 patch removed
        new_chars = self.original_chars + [
            {'name': 'PreviewChar1', 'runs': ['1.1下'], 'isPreview': True}
        ]
        new_patches = self.original_patches + [
            {'patch': '1.1下', 'date': '23/06/28', 'isPreview': True}
        ]
        try:
            validate_data_integrity(orig_chars, orig_patches, new_chars, new_patches)
        except AssertionError as e:
            self.fail(f"validate_data_integrity should allow preview adjustments, but raised: {e}")


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


class TestNormalizePatchDate(unittest.TestCase):
    def test_falsy_inputs(self):
        self.assertIsNone(normalize_patch_date(None))
        self.assertIsNone(normalize_patch_date(""))
        self.assertIsNone(normalize_patch_date("   "))

    def test_timestamp_inputs(self):
        expected_date = datetime.fromtimestamp(1682467200).strftime("%y/%m/%d")
        # Seconds
        self.assertEqual(normalize_patch_date(1682467200), expected_date)
        self.assertEqual(normalize_patch_date(1682467200.0), expected_date)
        # Milliseconds
        self.assertEqual(normalize_patch_date(1682467200000), expected_date)
        self.assertEqual(normalize_patch_date(1682467200000.0), expected_date)

    def test_string_formats(self):
        # %y/%m/%d
        self.assertEqual(normalize_patch_date("23/04/26"), "23/04/26")
        # %Y/%m/%d
        self.assertEqual(normalize_patch_date("2023/04/26"), "23/04/26")
        # %Y-%m-%d
        self.assertEqual(normalize_patch_date("2023-04-26"), "23/04/26")
        # ISO8601 full
        self.assertEqual(normalize_patch_date("2023-04-26T12:00:00.000Z"), "23/04/26")
        # ISO8601 without ms
        self.assertEqual(normalize_patch_date("2023-04-26T12:00:00Z"), "23/04/26")
        # %B %d, %Y
        self.assertEqual(normalize_patch_date("April 26, 2023"), "23/04/26")
        # %B %d %Y
        self.assertEqual(normalize_patch_date("April 26 2023"), "23/04/26")

    def test_string_with_whitespace(self):
        self.assertEqual(normalize_patch_date("  2023/04/26  "), "23/04/26")
        self.assertEqual(normalize_patch_date("\n2023-04-26\t"), "23/04/26")

    def test_invalid_string_formats(self):
        self.assertIsNone(normalize_patch_date("invalid date"))
        self.assertIsNone(normalize_patch_date("26/04/2023")) # DD/MM/YYYY is not in fmt list
        self.assertIsNone(normalize_patch_date("2023.04.26"))

    def test_value_error_handling(self):
        # Out-of-bounds dates that trigger ValueError during strptime parsing
        self.assertIsNone(normalize_patch_date("2023/13/01")) # Month 13
        self.assertIsNone(normalize_patch_date("2023/02/29")) # Not a leap year
        self.assertIsNone(normalize_patch_date("2023/04/31")) # April only has 30 days
        self.assertIsNone(normalize_patch_date("February 29, 2023"))




class TestExecuteAutoUpdate(unittest.TestCase):
    @patch('update_gist.requests.Session')
    @patch('update_gist.parse_local_js_array')
    @patch('update_gist.fetch_fandom_schedules_and_patches')
    @patch('update_gist.fetch_fandom_upcoming_characters_and_patches')
    @patch('update_gist.fetch_starrailres_data')
    @patch('update_gist.serialize_js_file')
    @patch('update_gist.validate_data_integrity')
    @patch('builtins.open', new_callable=mock_open)
    def test_execute_auto_update_no_changes(
            self, mock_file_open, mock_validate, mock_serialize,
            mock_fetch_res, mock_fetch_upcoming, mock_fetch_fandom, mock_parse_local, mock_session):

        # Setup mocks
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        # Return empty original patches/chars
        mock_parse_local.return_value = []

        # Return empty schedules and patches from Wiki
        mock_fetch_fandom.return_value = ([], [])

        # No upcoming
        mock_fetch_upcoming.return_value = ([], [])

        # Empty starrailres
        mock_fetch_res.return_value = ({}, {})

        # Execute
        result = execute_auto_update()

        # In case where there are no valid schedules returned, function returns False (melt down protection)
        self.assertFalse(result)

    @patch('update_gist.requests.Session')
    @patch('update_gist.parse_local_js_array')
    @patch('update_gist.fetch_fandom_schedules_and_patches')
    @patch('update_gist.fetch_fandom_upcoming_characters_and_patches')
    @patch('update_gist.fetch_starrailres_data')
    @patch('update_gist.serialize_js_file')
    @patch('update_gist.validate_data_integrity')
    @patch('builtins.open', new_callable=mock_open)
    def test_execute_auto_update_with_changes(
            self, mock_file_open, mock_validate, mock_serialize,
            mock_fetch_res, mock_fetch_upcoming, mock_fetch_fandom, mock_parse_local, mock_session):

        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        # Original data
        mock_parse_local.side_effect = [
            [{'patch': '1.0上', 'date': '23/04/26'}], # patches
            [{'cid': '1001', 'name': 'March 7th', 'runs': ['1.0上']}] # chars
        ]

        # Fandom data
        mock_fetch_fandom.return_value = (
            [{'en_name': 'Dan Heng', 'run': '1.0下', 'is_collab': False}],
            [{'patch': '1.0上', 'date': '23/04/26'}, {'patch': '1.0下', 'date': '23/05/17'}]
        )

        # Upcoming data
        mock_fetch_upcoming.return_value = (
            [{'en_name': 'Kafka', 'run': '1.2上', 'is_collab': False, 'is_preview': True}],
            [{'patch': '1.2上', 'date': '23/07/19', 'isPreview': True}]
        )

        # Starrailres data
        mock_fetch_res.return_value = (
            {'danheng': {'name': 'Dan Heng'}},
            {'danheng': {'name': '丹恆', 'path': 'Hunt', 'element': 'Wind'}}
        )

        # Test execute_auto_update
        with patch('update_gist.enrich_character_info') as mock_enrich:
            mock_enrich.side_effect = [
                ('1002', '丹恆', '巡獵', '風'),
                ('1005', '卡芙卡', '虛無', '雷')
            ]
            result = execute_auto_update()

        self.assertTrue(result)
        self.assertEqual(mock_serialize.call_count, 2)
        mock_validate.assert_called_once()


class TestFetchFandomSchedulesAndPatches(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()

    def test_fetch_success(self):
        # mock normal response
        html = """
        <table>
          <tr>
            <th colspan="2">Version 1.0 : April 26, 2023</th>
          </tr>
          <tr>
            <td>Character Event Warp</td>
            <td>
              <a title="Butterfly on Swordtip/2023-04-26" href="...">Seele</a>
            </td>
          </tr>
          <tr>
            <th colspan="2">Version 1.0 : May 17, 2023</th>
          </tr>
          <tr>
            <td>Character Event Warp</td>
            <td>
              <a title="Swirl of Heavenly Spear/2023-05-17" href="...">Jing Yuan</a>
            </td>
          </tr>
        </table>
        """
        resp_parse = MagicMock()
        resp_parse.json.return_value = {
            'parse': {
                'text': {
                    '*': html
                }
            }
        }
        resp_query = MagicMock()
        resp_query.json.return_value = {
          "query": {
            "pages": {
              "123": {
                "title": "Butterfly on Swordtip/2023-04-26",
                "revisions": [
                  {
                    "slots": {
                      "main": {
                        "*": "character_5_F = Seele"
                      }
                    }
                  }
                ]
              },
              "124": {
                "title": "Swirl of Heavenly Spear/2023-05-17",
                "revisions": [
                  {
                    "slots": {
                      "main": {
                        "*": "5{{star}} Character===\n* {{Character Intro|Jing Yuan}}"
                      }
                    }
                  }
                ]
              }
            }
          }
        }

        def side_effect(*args, **kwargs):
            params = kwargs.get('params', {})
            if params.get('action') == 'parse':
                return resp_parse
            elif params.get('action') == 'query':
                return resp_query
            return MagicMock()

        self.session.get.side_effect = side_effect

        schedules, new_patches = fetch_fandom_schedules_and_patches(self.session)

        self.assertEqual(len(schedules), 2)

        # order is not guaranteed because of set
        seele_sched = next((s for s in schedules if s['en_name'] == 'Seele'), None)
        self.assertIsNotNone(seele_sched)
        self.assertEqual(seele_sched['run'], '1.0上')
        self.assertEqual(seele_sched['is_collab'], False)
        self.assertEqual(seele_sched['patch_date'], '23/04/26')

        jing_yuan_sched = next((s for s in schedules if s['en_name'] == 'Jing Yuan'), None)
        self.assertIsNotNone(jing_yuan_sched)
        self.assertEqual(jing_yuan_sched['run'], '1.0下')
        self.assertEqual(jing_yuan_sched['is_collab'], False)
        self.assertEqual(jing_yuan_sched['patch_date'], '23/05/17')

        self.assertEqual(len(new_patches), 2)

    def test_fetch_success_multiple_phases(self):
        # mock normal response with multiple phases
        html = """
        <table>
          <tr>
            <th colspan="2">Version 1.0 : April 26, 2023</th>
          </tr>
          <tr>
            <td>Character Event Warp</td>
            <td>
              <a title="Event/Phase 1" href="...">Char 1</a>
            </td>
          </tr>
          <tr>
            <th colspan="2">Version 1.0 : May 17, 2023</th>
          </tr>
          <tr>
            <td>Character Event Warp</td>
            <td>
              <a title="Event/Phase 2" href="...">Char 2</a>
            </td>
          </tr>
          <tr>
            <th colspan="2">Version 1.0 : June 1, 2023</th>
          </tr>
          <tr>
            <td>Character Event Warp</td>
            <td>
              <a title="Event/Phase 3" href="...">Char 3</a>
            </td>
          </tr>
        </table>
        """
        resp_parse = MagicMock()
        resp_parse.json.return_value = {
            'parse': {
                'text': {
                    '*': html
                }
            }
        }
        resp_query = MagicMock()
        resp_query.json.return_value = {
          "query": {
            "pages": {
              "1": {
                "title": "Event/Phase 1",
                "revisions": [
                  {
                    "slots": {
                      "main": {
                        "*": "character_5_F = Char 1"
                      }
                    }
                  }
                ]
              },
              "2": {
                "title": "Event/Phase 2",
                "revisions": [
                  {
                    "slots": {
                      "main": {
                        "*": "character_5_F = Char 2"
                      }
                    }
                  }
                ]
              },
              "3": {
                "title": "Event/Phase 3",
                "revisions": [
                  {
                    "slots": {
                      "main": {
                        "*": "character_5_F = Char 3"
                      }
                    }
                  }
                ]
              }
            }
          }
        }

        def side_effect(*args, **kwargs):
            params = kwargs.get('params', {})
            if params.get('action') == 'parse':
                return resp_parse
            elif params.get('action') == 'query':
                return resp_query
            return MagicMock()

        self.session.get.side_effect = side_effect

        schedules, new_patches = fetch_fandom_schedules_and_patches(self.session)

        self.assertEqual(len(schedules), 3)
        self.assertEqual(len(new_patches), 3)

        char1 = next((s for s in schedules if s['en_name'] == 'Char 1'), None)
        self.assertEqual(char1['run'], '1.0上')

        char2 = next((s for s in schedules if s['en_name'] == 'Char 2'), None)
        self.assertEqual(char2['run'], '1.0中')

        char3 = next((s for s in schedules if s['en_name'] == 'Char 3'), None)
        self.assertEqual(char3['run'], '1.0下')

    def test_fetch_no_html(self):
        resp_parse = MagicMock()
        resp_parse.json.return_value = {}
        self.session.get.return_value = resp_parse

        schedules, new_patches = fetch_fandom_schedules_and_patches(self.session)

        self.assertEqual(schedules, [])
        self.assertEqual(new_patches, [])

    def test_fetch_no_tables(self):
        resp_parse = MagicMock()
        resp_parse.json.return_value = {
            'parse': {
                'text': {
                    '*': '<html><body><h1>No Tables Here!</h1></body></html>'
                }
            }
        }
        self.session.get.return_value = resp_parse

        schedules, new_patches = fetch_fandom_schedules_and_patches(self.session)

        self.assertEqual(schedules, [])
        self.assertEqual(new_patches, [])

class TestSerializeJsFile(unittest.TestCase):
    @patch('update_gist.datetime')
    def test_serialize_js_file(self, mock_datetime):
        mock_date = datetime(2023, 10, 25)
        mock_datetime.now.return_value = mock_date

        var_name = "TEST_DATA"
        data = [
            {"name": "Seeley", "element": "Quantum"},
            {"name": "Kafka", "element": "Lightning"}
        ]
        filepath = "test_output.js"

        expected_js_str = '[\n    {\n        name: "Seeley",\n        element: "Quantum"\n    },\n    {\n        name: "Kafka",\n        element: "Lightning"\n    }\n]'
        expected_content = f"// 更新日期: 2023/10/25\n\nconst {var_name} = {expected_js_str};\n"

        m = mock_open()
        with patch('builtins.open', m):
            serialize_js_file(var_name, data, filepath)

        m.assert_called_once_with(filepath, 'w', encoding='utf-8')
        m().write.assert_called_once_with(expected_content)

    @patch('update_gist.datetime')
    def test_serialize_js_file_raw_characters_includes_last_updated(self, mock_datetime):
        mock_date = datetime(2023, 10, 25)
        mock_datetime.now.return_value = mock_date

        var_name = "RAW_CHARACTERS"
        data = [{"name": "希兒", "elem": "量子"}]
        filepath = "js/characters.js"

        expected_js_str = '[\n    {\n        name: "希兒",\n        elem: "量子"\n    }\n]'
        expected_content = (
            '// 更新日期: 2023/10/25\n'
            'const LAST_UPDATED = "2023/10/25";\n\n'
            f'const {var_name} = {expected_js_str};\n'
        )

        m = mock_open()
        with patch('builtins.open', m):
            serialize_js_file(var_name, data, filepath)

        m.assert_called_once_with(filepath, 'w', encoding='utf-8')
        m().write.assert_called_once_with(expected_content)

class TestContainsCjk(unittest.TestCase):
    def test_empty_and_none(self):
        self.assertFalse(contains_cjk(""))
        self.assertFalse(contains_cjk(None))

    def test_non_cjk_strings(self):
        self.assertFalse(contains_cjk("Hello World!"))
        self.assertFalse(contains_cjk("1234567890"))
        self.assertFalse(contains_cjk("!@#$%^&*()_+"))
        self.assertFalse(contains_cjk("   "))
        self.assertFalse(contains_cjk("   \n \t "))
        self.assertFalse(contains_cjk("Ruan Mei"))

    def test_pure_cjk_strings(self):
        self.assertTrue(contains_cjk("漢字"))  # Chinese
        self.assertTrue(contains_cjk("卡芙卡")) # Chinese
        self.assertTrue(contains_cjk("丹恆"))   # Chinese

    def test_mixed_strings(self):
        self.assertTrue(contains_cjk("Ruan Mei 阮•梅"))
        self.assertTrue(contains_cjk("Kafka 卡芙卡 1.2"))
        self.assertTrue(contains_cjk("Dan Heng 丹恆"))

    def test_boundary_characters(self):
        self.assertTrue(contains_cjk("\u4e00"))
        self.assertTrue(contains_cjk("\u9fff"))
        self.assertTrue(contains_cjk("\u3400"))
        self.assertTrue(contains_cjk("\u4dbf"))
        self.assertTrue(contains_cjk("\uf900"))
        self.assertTrue(contains_cjk("\ufaff"))
        self.assertTrue(contains_cjk("\U00020000"))
        self.assertTrue(contains_cjk("\U0002A6DF"))
        self.assertTrue(contains_cjk("\U0002A700"))
        self.assertTrue(contains_cjk("\U0002B73F"))
        self.assertTrue(contains_cjk("\U0002B740"))
        self.assertTrue(contains_cjk("\U0002B81F"))
        self.assertTrue(contains_cjk("\U0002B820"))
        self.assertTrue(contains_cjk("\U0002CEAF"))
        self.assertTrue(contains_cjk("\U0002CEB0"))
        self.assertTrue(contains_cjk("\U0002EBEF"))
        self.assertTrue(contains_cjk("\U0002F800"))
        self.assertTrue(contains_cjk("\U0002FA1F"))


class TestParseWarpListTables(unittest.TestCase):
    def parse_date(self, value):
        dates = {
            'April 26, 2023': datetime(2023, 4, 26),
            'January 1, 2025': datetime(2025, 1, 1)
        }
        return dates.get(value)

    def test_empty_tables(self):
        self.assertEqual(parse_warp_list_tables([], self.parse_date), ([], {}))

    def test_standard_and_collaboration_records(self):
        html = """
        <table>
            <tr><th colspan="2">Version 1.0 : Since April 26, 2023</th></tr>
            <tr><td>Character Event Warp</td><td><a title="Banner/1.0">Banner</a></td></tr>
        </table>
        <table>
            <tr><th colspan="2">Version 3.0 : Since January 1, 2025 (Collaboration/Indefinite)</th></tr>
            <tr><td>Character Event Warp</td><td><a title="Collab/3.0">Collab</a></td></tr>
        </table>
        """
        records, version_dates = parse_warp_list_tables(
            BeautifulSoup(html, 'html.parser').find_all('table'),
            self.parse_date
        )

        self.assertEqual(records, [
            {
                'warp_page': 'Banner/1.0',
                'version': '1.0',
                'start_dt': datetime(2023, 4, 26),
                'is_collab': False
            },
            {
                'warp_page': 'Collab/3.0',
                'version': '3.0',
                'start_dt': datetime(2025, 1, 1),
                'is_collab': True
            }
        ])
        self.assertEqual(version_dates, {'1.0': {datetime(2023, 4, 26)}})

    def test_limits_tables_and_skips_non_character_or_invalid_links(self):
        html = """
        <table>
            <tr><th colspan="2">Version 1.0 : Since April 26, 2023</th></tr>
            <tr><td>Light Cone Event Warp</td><td><a title="Light Cone/1.0">Light Cone</a></td></tr>
            <tr><td>Character Event Warp</td><td>
                <a title="File:Character.png">Image</a>
                <a title="NoSlashTitle">Invalid</a>
                <a title="Valid/Title">Valid</a>
            </td></tr>
        </table>
        """ + ''.join(
            f"""
            <table>
                <tr><th colspan="2">Version 1.{index} : Since April 26, 2023</th></tr>
                <tr><td>Character Event Warp</td><td><a title="Warp/{index}">Warp</a></td></tr>
            </table>
            """
            for index in range(1, 5)
        )

        records, _ = parse_warp_list_tables(
            BeautifulSoup(html, 'html.parser').find_all('table'),
            self.parse_date
        )

        self.assertEqual([record['warp_page'] for record in records], ['Valid/Title', 'Warp/1', 'Warp/2'])


class TestWikiQueryPerformanceOptimization(unittest.TestCase):
    @patch('update_gist.fetch_starrailres_data')
    def test_batch_query_optimization(self, mock_fetch_res):
        """
        Verify that processing multiple missing characters triggers a single batched query
        instead of N+1 individual queries.
        """
        from update_gist import _merge_characters

        mock_fetch_res.return_value = ({}, {})

        session = MagicMock()
        session.get.return_value.json.return_value = {
            'query': {
                'pages': {
                    '1': {
                        'title': 'A',
                        'revisions': [{'slots': {'main': {'*': '|zht = A繁體'}}}]
                    },
                    '2': {
                        'title': 'B',
                        'revisions': [{'slots': {'main': {'*': '|zht = B繁體'}}}]
                    },
                    '3': {
                        'title': 'C',
                        'revisions': [{'slots': {'main': {'*': '|zht = C繁體'}}}]
                    }
                }
            }
        }

        original_chars = []
        all_incoming_schedules = [
            {'en_name': 'A', 'run': '1.0上'},
            {'en_name': 'B', 'run': '1.0下'},
            {'en_name': 'C', 'run': '1.1上'}
        ]

        _merge_characters(original_chars, all_incoming_schedules, session)

        # Verify that only 1 batch request was made instead of 3 individual requests
        self.assertEqual(session.get.call_count, 1)

        # Verify the requested titles contains all 3 characters combined
        call_args = session.get.call_args[1]
        titles = call_args['params']['titles']
        self.assertIn('A', titles.split('|'))
        self.assertIn('B', titles.split('|'))
        self.assertIn('C', titles.split('|'))


class TestPreviewOverwriteAndThreePhase(unittest.TestCase):
    @patch('update_gist.fetch_starrailres_data')
    def test_merge_characters_overwrites_preview_runs(self, mock_fetch_res):
        from update_gist import _merge_characters

        mock_fetch_res.return_value = (
            {
                '1001': {'name': 'Seele'},
                '1514': {'name': 'Aha'}
            },
            {
                '1001': {'name': '希兒', 'path': 'Hunt', 'element': 'Quantum'},
                '1514': {'name': '星神★阿哈', 'path': 'Elation', 'element': 'Quantum'}
            }
        )
        session = MagicMock()

        original_chars = [
            {'cid': '1001', 'name': '希兒', 'path': '巡獵', 'elem': '量子', 'runs': ['1.0上']},
            {'cid': '1514', 'name': '星神★阿哈', 'path': '歡愉', 'elem': '量子', 'runs': ['4.7上'], 'isPreview': True}
        ]
        # Preview character schedule adjusted from 4.7上 to 4.7下, while official character gains a rerun
        incoming_schedules = [
            {'en_name': 'Seele', 'run': '1.4下', 'is_collab': False, 'is_preview': False},
            {'en_name': 'Aha', 'run': '4.7下', 'is_collab': False, 'is_preview': True}
        ]

        merged_chars, _, runs_added_log, _ = _merge_characters(original_chars, incoming_schedules, session)
        seele = next(c for c in merged_chars if c['name'] == '希兒')
        aha = next(c for c in merged_chars if c['name'] == '星神★阿哈')

        self.assertEqual(seele['runs'], ['1.0上', '1.4下'])
        self.assertEqual(aha['runs'], ['4.7下'])
        self.assertTrue(aha.get('isPreview'))
        self.assertIn('星神★阿哈 ➡️ 4.7下', runs_added_log)

    def test_three_phase_upcoming_patch_extrapolation(self):
        from update_gist import fetch_fandom_upcoming_characters_and_patches

        session = MagicMock()
        # Mock empty collaboration and upcoming categories
        session.get.return_value.json.return_value = {'query': {'categorymembers': []}}

        _, gen_patches = fetch_fandom_upcoming_characters_and_patches(session, '3.8中', '26/01/07')
        self.assertGreaterEqual(len(gen_patches), 1)
        self.assertEqual(gen_patches[0]['patch'], '3.8下')
        self.assertEqual(gen_patches[0]['date'], '26/01/28')
        self.assertTrue(gen_patches[0]['isPreview'])


class TestRealProjectDataIntegrity(unittest.TestCase):
    def test_actual_project_js_files_pass_validation(self):
        import os
        patches_path = os.path.join('js', 'patches.js')
        chars_path = os.path.join('js', 'characters.js')

        patches = parse_local_js_array(patches_path, 'PATCH_DATA')
        chars = parse_local_js_array(chars_path, 'RAW_CHARACTERS')

        self.assertGreater(len(patches), 0, "PATCH_DATA 不可為空")
        self.assertGreater(len(chars), 0, "RAW_CHARACTERS 不可為空")

        # 驗證實際專案資料通過五道防護門檻
        validate_data_integrity(chars, patches, chars, patches)

        # 驗證 characters.js 具備 LAST_UPDATED 常數供前端首屏直接讀取
        with open(chars_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertRegex(content, r'const\s+LAST_UPDATED\s*=\s*"\d{4}/\d{2}/\d{2}";')


class TestDynamicPathAndBuffAdaptation(unittest.TestCase):
    def test_validate_data_integrity_allows_new_paths_and_buff_modes(self):
        old_patches = [{'patch': f'1.{i}上', 'date': f'23/0{i+1}/01'} for i in range(6)]
        old_chars = [
            {'name': f'舊角色{i}', 'path': '毀滅', 'elem': '火', 'runs': ['1.0上']}
            for i in range(10)
        ]
        new_chars = old_chars + [
            {
                'name': '阿基維利',
                'path': '開拓',
                'elem': '虛數',
                'runs': ['1.5上'],
                'buffs': ['1.5上'],
                'buffTypes': {'1.5上': '星軌共鳴'}
            },
            {
                'name': '未來旅者',
                'path': 'Singularity',
                'elem': '量子',
                'runs': ['1.5上']
            }
        ]
        audit = validate_data_integrity(old_chars, old_patches, new_chars, old_patches)
        self.assertIn('開拓', audit['dynamic_paths'])
        self.assertIn('Singularity', audit['dynamic_paths'])
        self.assertIn('星軌共鳴', audit['introduced_buff_types'])

    def test_mediawiki_parser_handles_piped_and_unconfigured_paths(self):
        from update_gist import query_wiki_character_pages_batch, normalize_path_name

        session = MagicMock()
        session.get.return_value.json.return_value = {
            'query': {
                'pages': {
                    '10': {
                        'title': 'Akivili',
                        'revisions': [{
                            'slots': {
                                'main': {
                                    '*': '|zht = 阿基維利\n|path = [[Path/Trailblaze|The Trailblaze]]\n|combatType = [[Combat Types#Imaginary|Imaginary]]'
                                }
                            }
                        }]
                    },
                    '11': {
                        'title': 'Zero',
                        'revisions': [{
                            'slots': {
                                'main': {
                                    '*': '|zht = 零號\n|path = [[Singularity]]\n|element = Quantum'
                                }
                            }
                        }]
                    }
                }
            }
        }

        result = query_wiki_character_pages_batch(['Akivili', 'Zero'], session)
        self.assertEqual(result['Akivili']['cht_name'], '阿基維利')
        self.assertEqual(result['Akivili']['path'], 'The Trailblaze')
        self.assertEqual(normalize_path_name(result['Akivili']['path']), '開拓')
        self.assertEqual(result['Akivili']['elem'], 'Imaginary')
        self.assertEqual(result['Zero']['cht_name'], '零號')
        self.assertEqual(normalize_path_name(result['Zero']['path']), 'Singularity')
        self.assertEqual(result['Zero']['elem'], 'Quantum')

    @patch('update_gist.fetch_starrailres_data')
    def test_merge_characters_integrates_new_paths_and_buff_modes(self, mock_fetch_res):
        from update_gist import _merge_characters, extract_buff_marker

        self.assertEqual(extract_buff_marker('|buff_mode = 星魂共鳴'), '星魂共鳴')
        self.assertEqual(extract_buff_marker('{{Enhancement|星魂共鳴}}'), '星魂共鳴')
        self.assertEqual(extract_buff_marker('(Enhanced: 破界覺醒)'), '破界覺醒')
        self.assertEqual(extract_buff_marker('{{Nova Buff|礪爍新輝}}'), '礪爍新輝')

        mock_fetch_res.return_value = (
            {
                '1001': {'name': 'Seele'},
                '1999': {'name': 'Akivili'}
            },
            {
                '1001': {'name': '希兒', 'path': 'Hunt', 'element': 'Quantum'},
                '1999': {'name': '阿基維利', 'path': 'Trailblaze', 'element': 'Imaginary'}
            }
        )
        session = MagicMock()

        original_chars = [
            {'cid': '1001', 'name': '希兒', 'path': '巡獵', 'elem': '量子', 'runs': ['1.0上']}
        ]
        incoming_schedules = [
            {'en_name': 'Seele', 'run': '5.0上', 'buff_type': '星魂共鳴'},
            {'en_name': 'Akivili', 'run': '5.0上', 'buff_type': '礪爍新輝'}
        ]

        merged_chars, new_chars_log, _, _ = _merge_characters(original_chars, incoming_schedules, session)
        seele = next(c for c in merged_chars if c['name'] == '希兒')
        akivili = next(c for c in merged_chars if c['name'] == '阿基維利')

        self.assertIn('5.0上', seele['buffs'])
        self.assertEqual(seele.get('buffTypes', {}).get('5.0上'), '星魂共鳴')
        self.assertEqual(akivili['path'], '開拓')
        self.assertIn('5.0上', akivili['buffs'])
        self.assertNotIn('buffTypes', akivili)
        self.assertTrue(any('阿基維利 (開拓/虛數)' in log for log in new_chars_log))


if __name__ == '__main__':
    unittest.main()

