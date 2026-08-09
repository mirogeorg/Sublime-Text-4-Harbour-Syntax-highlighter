from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

from common import ROOT, sha256
from generate_package import CHUNK_LIMIT, generate, regex_chunks


def fail(message: str) -> None:
    raise AssertionError(message)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> None:
    canonical = load(ROOT / "catalog" / "canonical.json")
    inventory = load(ROOT / "catalog" / "raw" / "inventory.json")
    missing = load(ROOT / "catalog" / "reports" / "source-missing.json")
    summary = load(ROOT / "catalog" / "reports" / "summary.json")
    completions = load(
        ROOT / "package" / "Harbour" / "completions" / "Harbour.sublime-completions"
    )["completions"]
    help_records = load(ROOT / "package" / "Harbour" / "data" / "function_help.json")

    keys = [item["key"] for item in canonical]
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        fail("canonical names are not unique and deterministically sorted")
    if {item["key"] for item in inventory} != set(keys):
        fail("raw inventory and canonical catalog differ")
    if summary["unique_functions"] != len(canonical):
        fail("summary unique function count is stale")

    verified = {
        item["key"]
        for item in canonical
        if item["review_status"] == "verified" and item["visibility"] == "public"
    }
    public = {item["key"] for item in canonical if item["visibility"] == "public"}
    completion_keys = [item["trigger"].casefold() for item in completions]
    if len(completion_keys) != len(set(completion_keys)):
        fail("duplicate completion triggers")
    if set(completion_keys) != public or set(help_records) != public:
        fail("completion/help sets do not equal the public catalog")

    for item in canonical:
        if item["visibility"] == "public":
            if item["review_status"] != "verified" or not item["source"]:
                fail(f"public help is not source-backed: {item['name']}")
            if "(...)" in item["signature"]:
                fail(f"placeholder signature survived: {item['name']}")
            if re.search(r"\(\s*\)$", item["signature"]) and not re.search(
                r"\(\s*\)(?:\s*->.*)?$", item["snippet"]
            ):
                fail(f"no-parameter signature conflicts with usage: {item['name']}")

    for item in canonical:
        if item["review_status"] == "verified":
            if not item["signature"] or not item["summary"] or not item["source"]:
                fail(f"incomplete verified record: {item['name']}")
            if item["source"]["line"] < 1 or not item["source"]["evidence"]:
                fail(f"invalid evidence: {item['name']}")
        elif item["review_status"] != "missing-source":
            fail(f"unknown review status: {item['review_status']}")

    for completion in completions:
        for field in ("trigger", "contents", "kind", "details"):
            if not completion.get(field):
                fail(f"empty completion field {field}")
        if re.search(r"<script|javascript:", completion["details"], re.IGNORECASE):
            fail(f"unsafe completion details: {completion['trigger']}")
        if completion["kind"][:2] != ["snippet", "s"]:
            fail(f"completion is not a help snippet: {completion['trigger']}")
        annotation = completion.get("annotation", "")
        if "help" in annotation.casefold() or "->" in annotation:
            fail(f"noisy completion annotation: {completion['trigger']}")

    names = [item["name"] for item in canonical]
    chunks = regex_chunks(names)
    if any(len(chunk) > CHUNK_LIMIT for chunk in chunks):
        fail("generated regex chunk exceeds configured limit")
    syntax = (ROOT / "package" / "Harbour" / "Harbour.sublime-syntax").read_text(
        encoding="utf-8"
    )
    if "(?i)\\b(?:)\\b" in syntax or "source.js" in syntax:
        fail("empty/foreign regex survived syntax generation")
    all_functions = (
        ROOT / "package" / "Harbour" / "tests" / "syntax_test_all_functions.prg"
    ).read_text(encoding="utf-8")
    for name in names:
        if f"{name}()\n" not in all_functions:
            fail(f"all-functions fixture misses {name}")

    package = ROOT / "package" / "Harbour"
    private_patterns = [
        re.compile(r"[A-Za-z]:\\\\"),
        re.compile(r"C:/Users/", re.IGNORECASE),
        re.compile(r"D:/accounts/", re.IGNORECASE),
        re.compile(r"(?:api[_-]?key|password)\s*[:=]", re.IGNORECASE),
    ]
    for path in package.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".png", ".jpg"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in private_patterns:
            if pattern.search(text):
                fail(f"private path/secret-shaped text in package: {path}")

    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    if "asistex" not in notices or "Harbour" not in notices or "MIT" not in notices:
        fail("third-party notices are incomplete")
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "GNU GENERAL PUBLIC LICENSE" not in license_text or "Version 3" not in license_text:
        fail("complete GPL version 3 license text is missing")
    if "GPL-3.0-or-later" not in readme:
        fail("project SPDX license identifier is missing")

    generated = [
        ROOT / "package" / "Harbour" / "Harbour.sublime-syntax",
        ROOT / "package" / "Harbour" / "completions" / "Harbour.sublime-completions",
        ROOT / "package" / "Harbour" / "data" / "function_help.json",
        ROOT / "package" / "Harbour" / "tests" / "syntax_test_all_functions.prg",
    ]
    before = {path: sha256(path) for path in generated}
    generate()
    after = {path: sha256(path) for path in generated}
    if before != after:
        fail("package generation is not deterministic")

    artifact = ROOT / "local-only" / "dist" / "Harbour.sublime-package"
    if not artifact.is_file():
        fail("release artifact is missing")
    with zipfile.ZipFile(artifact) as bundle:
        names_in_zip = bundle.namelist()
        if not names_in_zip or any(name.startswith(("archive/", "catalog/", "tools/")) for name in names_in_zip):
            fail("release artifact contains non-package files")

    print(
        "validated:",
        len(canonical),
        "symbols;",
        len(public),
        "public help snippets (",
        len(verified),
        "source-verified );",
        len(missing),
        "source-pending symbols",
    )


if __name__ == "__main__":
    try:
        validate()
    except AssertionError as error:
        print(f"validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
