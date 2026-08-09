from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginStaticTests(unittest.TestCase):
    def test_plugin_parses(self):
        plugin = ROOT / "package" / "Harbour" / "harbour_help.py"
        tree = ast.parse(
            plugin.read_text(encoding="utf-8"),
            filename=str(plugin),
            feature_version=(3, 3),
        )
        self.assertFalse(
            any(isinstance(node, ast.JoinedStr) for node in ast.walk(tree)),
            "Sublime Text loads this plugin with Python 3.3, which has no f-strings",
        )

    def test_help_json_keys_are_casefolded(self):
        records = json.loads(
            (ROOT / "package" / "Harbour" / "data" / "function_help.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(set(records), {key.casefold() for key in records})

    def test_legacy_session_migration_is_present(self):
        plugin = (ROOT / "package" / "Harbour" / "harbour_help.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("/harbour.tmlanguage", plugin)
        self.assertIn("Packages/Harbour/Harbour.sublime-syntax", plugin)
        self.assertIn("_display_signature", plugin)
        self.assertTrue((ROOT / "package" / "Harbour" / "Harbour.tmLanguage").is_file())


if __name__ == "__main__":
    unittest.main()
