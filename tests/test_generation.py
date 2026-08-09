from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from generate_package import CHUNK_LIMIT, regex_chunks  # noqa: E402


class GeneratedPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical = json.loads(
            (ROOT / "catalog" / "canonical.json").read_text(encoding="utf-8")
        )
        cls.summary = json.loads(
            (ROOT / "catalog" / "reports" / "summary.json").read_text(encoding="utf-8")
        )

    def test_inventory_baseline(self):
        self.assertEqual(6239, self.summary["function_rows"])
        self.assertEqual(6237, self.summary["unique_functions"])
        self.assertEqual(67, self.summary["libraries"])

    def test_schema_and_provenance(self):
        required = {
            "name", "key", "libraries", "installed", "visibility", "signature",
            "snippet", "summary", "parameters", "return", "platform", "source_version",
            "source", "review_status",
        }
        for record in self.canonical:
            self.assertEqual(required, set(record))
            self.assertEqual(record["name"].casefold(), record["key"])
            if record["review_status"] == "verified":
                self.assertTrue(record["signature"])
                self.assertTrue(record["summary"])
                self.assertIsInstance(record["source"]["line"], int)

    def test_all_public_help_has_concrete_source_backed_signatures(self):
        public = [record for record in self.canonical if record["visibility"] == "public"]
        self.assertTrue(public)
        for record in public:
            self.assertEqual("verified", record["review_status"])
            self.assertIsNotNone(record["source"])
            self.assertNotIn("(...)", record["signature"])
            if record["signature"].rstrip().endswith("()"):
                self.assertRegex(record["snippet"], r"\(\s*\)(?:\s*->.*)?$")

    def test_regex_chunks_are_bounded(self):
        chunks = regex_chunks([record["name"] for record in self.canonical])
        self.assertTrue(chunks)
        self.assertLessEqual(max(map(len, chunks)), CHUNK_LIMIT)
        self.assertFalse(any(chunk.endswith("|") or "||" in chunk for chunk in chunks))

    def test_extensions_do_not_claim_c_or_h(self):
        syntax = (ROOT / "package" / "Harbour" / "Harbour.sublime-syntax").read_text(
            encoding="utf-8"
        )
        header = syntax.split("variables:", 1)[0]
        self.assertNotIn("  - c\n", header)
        self.assertNotIn("  - h\n", header)
        for extension in ("prg", "hb", "ch", "ppo", "res", "idu"):
            self.assertIn(f"  - {extension}\n", header)

    def test_comment_forms_have_distinct_scopes_and_optional_colors(self):
        syntax = (ROOT / "package" / "Harbour" / "Harbour.sublime-syntax").read_text(
            encoding="utf-8"
        )
        for scope in (
            "comment.line.asterisk.harbour",
            "comment.line.double-ampersand.harbour",
            "comment.line.double-slash.harbour",
            "comment.block.harbour",
            "punctuation.definition.comment.asterisk.harbour",
            "punctuation.definition.comment.double-ampersand.harbour",
            "punctuation.definition.comment.double-slash.harbour",
            "punctuation.definition.comment.block.begin.harbour",
            "punctuation.definition.comment.block.end.harbour",
        ):
            self.assertIn(scope, syntax)

        scheme = json.loads(
            (
                ROOT
                / "package"
                / "Harbour"
                / "Harbour Comments.sublime-color-scheme"
            ).read_text(encoding="utf-8")
        )
        rules = {rule["scope"]: rule for rule in scheme["rules"]}
        for scope in (
            "comment.line.asterisk.harbour",
            "comment.line.double-ampersand.harbour",
            "comment.line.double-slash.harbour",
            "comment.block.harbour",
        ):
            self.assertIn(scope, rules)
            self.assertRegex(rules[scope]["foreground"], r"^#[0-9A-Fa-f]{6}$")

    def test_generated_completions_replace_buffer_word_duplicates(self):
        completion_file = json.loads(
            (
                ROOT
                / "package"
                / "Harbour"
                / "completions"
                / "Harbour.sublime-completions"
            ).read_text(encoding="utf-8")
        )
        self.assertIs(completion_file["inhibit_word_completions"], True)
        for completion in completion_file["completions"]:
            self.assertEqual(["snippet", "s"], completion["kind"][:2])
            annotation = completion.get("annotation", "")
            self.assertNotIn("help", annotation.casefold())
            self.assertNotIn("->", annotation)
            self.assertNotIn("installed", annotation)
            self.assertNotIn("Harbour core", annotation)

    def test_curated_usage_wins_for_hautoadd(self):
        completion_file = json.loads(
            (
                ROOT
                / "package"
                / "Harbour"
                / "completions"
                / "Harbour.sublime-completions"
            ).read_text(encoding="utf-8")
        )
        rows = {
            item["trigger"].casefold(): item
            for item in completion_file["completions"]
        }
        self.assertIn("HB_HAUTOADD_ALWAYS", rows["hb_hautoadd"]["details"])

    def test_return_value_is_visible_without_being_inserted(self):
        completion_file = json.loads(
            (
                ROOT
                / "package"
                / "Harbour"
                / "completions"
                / "Harbour.sublime-completions"
            ).read_text(encoding="utf-8")
        )
        rows = {item["trigger"].casefold(): item for item in completion_file["completions"]}
        sha = rows["hb_sha256"]
        self.assertEqual("<cDigest>", sha["annotation"])
        self.assertIn("hb_SHA256( &lt;cMessage&gt;, [&lt;lRaw&gt;] )", sha["details"])
        self.assertIn("-&gt; &lt;cDigest&gt;", sha["details"])
        self.assertNotIn("->", sha["contents"])

    def test_documented_result_survives_curated_snippet(self):
        completion_file = json.loads(
            (
                ROOT
                / "package"
                / "Harbour"
                / "completions"
                / "Harbour.sublime-completions"
            ).read_text(encoding="utf-8")
        )
        rows = {item["trigger"].casefold(): item for item in completion_file["completions"]}
        keys = rows["hb_hkeys"]
        self.assertEqual("<aKeys>", keys["annotation"])
        self.assertIn("-&gt; &lt;aKeys&gt;", keys["details"])

    def test_completion_details_escape_harbour_metavariables(self):
        completion_file = json.loads(
            (
                ROOT
                / "package"
                / "Harbour"
                / "completions"
                / "Harbour.sublime-completions"
            ).read_text(encoding="utf-8")
        )
        for row in completion_file["completions"]:
            self.assertNotRegex(row["details"], r"<[A-Za-z][A-Za-z0-9_]*>")

    def test_completion_details_hide_internal_provenance_notes(self):
        completion_file = json.loads(
            (
                ROOT
                / "package"
                / "Harbour"
                / "completions"
                / "Harbour.sublime-completions"
            ).read_text(encoding="utf-8")
        )
        hidden_notes = (
            "verified at the referenced source definition",
            "Curated usage signature from a reviewed completion source",
        )
        for row in completion_file["completions"]:
            for note in hidden_notes:
                self.assertNotIn(note, row["details"])


if __name__ == "__main__":
    unittest.main()
