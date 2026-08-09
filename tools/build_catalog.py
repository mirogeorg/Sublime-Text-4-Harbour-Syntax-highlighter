from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from c_api_inference import CApi, scan_c_text
from common import ROOT, write_json, write_text_if_changed


DEFAULT_HBMK2 = Path(r"D:\accounts\hb32_64_zig_v3\bin\hbmk2.exe")
DEFAULT_SOURCE = Path(r"D:\accounts\hb32_64src")
DEFAULT_LOCAL = (
    ROOT
    / "local-only"
    / "archive"
    / "current-module-20260809"
    / "Harbour.sublime-completions"
)
DEFAULT_ASISTEX = ROOT / "local-only" / ".cache" / "asistex" / "harbour"
NAME_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
LIBRARY_RE = re.compile(r"^(.+?) \((not installed|installed)\):$")
FIELD_RE = re.compile(
    r"^\s*(?:/\*+|\*+|//)?\s*\$(\w+)\$\s*(?:\*/)?\s*$"
)
PRG_DEF_RE = re.compile(
    r"^\s*(?:(?:static|init|exit)\s+)?(?:function|procedure)\s+"
    r"([A-Za-z_$][A-Za-z0-9_$]*)\s*(\([^\r\n]*\))?",
    re.IGNORECASE,
)
PRG_CLASS_RE = re.compile(
    r"^\s*(?:create\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)\b"
    r"(?:.*?\bfunction\s+([A-Za-z_$][A-Za-z0-9_$]*))?",
    re.IGNORECASE,
)
@dataclass(frozen=True)
class Evidence:
    path: str
    line: int
    kind: str
    signature: str = ""
    summary: str = ""
    returns: str = ""
    platform: str = "all"


def decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def run_inventory(
    hbmk2: Path,
) -> tuple[str, dict[str, dict[str, object]], int, set[str]]:
    if not hbmk2.is_file():
        raise SystemExit(f"hbmk2 not found: {hbmk2}")
    result = subprocess.run(
        [str(hbmk2), "-find", "*"], capture_output=True, check=True
    )
    text = decode(result.stdout).replace("\r\n", "\n")
    records: dict[str, dict[str, object]] = {}
    current_library = ""
    installed = False
    function_rows = 0
    library_headers: set[str] = set()
    for raw_line in text.splitlines():
        library = LIBRARY_RE.match(raw_line)
        if library:
            current_library = library.group(1)
            installed = library.group(2) == "installed"
            library_headers.add(current_library)
            continue
        candidate = raw_line.strip()
        if not candidate.endswith("()"):
            continue
        name = candidate[:-2]
        if not current_library or not NAME_RE.fullmatch(name):
            continue
        function_rows += 1
        key = name.casefold()
        record = records.setdefault(
            key, {"name": name, "key": key, "libraries": []}
        )
        libraries = record["libraries"]
        assert isinstance(libraries, list)
        item = {"name": current_library, "installed": installed}
        if item not in libraries:
            libraries.append(item)
    for record in records.values():
        record["libraries"] = sorted(
            record["libraries"], key=lambda item: str(item["name"]).casefold()
        )
    return text, records, function_rows, library_headers


def clean_field(lines: list[str]) -> str:
    parts = []
    for line in lines:
        value = re.sub(r"^\s*(?:\*|//)?\s?", "", line).strip()
        if value:
            parts.append(value)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def names_from_doc(fields: dict[str, list[str]]) -> set[str]:
    values = (
        fields.get("FUNCNAME", [])
        + fields.get("NAME", [])
        + fields.get("SYNTAX", [])[:1]
    )
    found: set[str] = set()
    for value in values:
        for match in re.finditer(r"\b([A-Za-z_$][A-Za-z0-9_$]*)\s*\(", value):
            found.add(match.group(1))
    return found


def scan_docs(source: Path) -> dict[str, list[Evidence]]:
    result: dict[str, list[Evidence]] = defaultdict(list)
    candidates = list((source / "doc" / "en").rglob("*.txt"))
    candidates += list((source / "contrib").glob("*/doc/en/*.txt"))
    for path in sorted(set(candidates), key=lambda value: value.as_posix().casefold()):
        lines = decode(path.read_bytes()).splitlines()
        in_doc = False
        start = 0
        fields: dict[str, list[str]] = defaultdict(list)
        field = ""
        for index, line in enumerate(lines, 1):
            token = FIELD_RE.match(line)
            marker = token.group(1).upper() if token else ""
            if marker == "DOC":
                in_doc, start, fields, field = True, index, defaultdict(list), ""
                continue
            if not in_doc:
                continue
            if marker == "END":
                syntax = clean_field(fields.get("SYNTAX", []))
                summary = clean_field(
                    fields.get("ONELINER", []) or fields.get("PURPOSE", [])
                )
                returns = clean_field(fields.get("RETURNS", []))
                platform = clean_field(fields.get("PLATFORMS", [])) or "all"
                for name in names_from_doc(fields):
                    result[name.casefold()].append(
                        Evidence(
                            path=path.relative_to(source).as_posix(),
                            line=start,
                            kind="harbour-doc",
                            signature=syntax,
                            summary=summary,
                            returns=returns,
                            platform=platform,
                        )
                    )
                in_doc, field = False, ""
                continue
            if marker:
                field = marker
            elif field:
                fields[field].append(line)
    return result


def scan_definitions(source: Path) -> dict[str, list[Evidence]]:
    result: dict[str, list[Evidence]] = defaultdict(list)
    c_apis: list[tuple[str, CApi]] = []
    roots = [source / "src", source / "contrib", source / "addons"]
    extensions = {".prg", ".hb", ".c", ".cpp", ".h"}
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*"), key=lambda value: value.as_posix().casefold()):
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            try:
                lines = decode(path.read_bytes()).splitlines()
            except OSError:
                continue
            relative = path.relative_to(source).as_posix()
            text = "\n".join(lines)
            if path.suffix.lower() in {".prg", ".hb"}:
                statement = ""
                statement_line = 0
                for index, line in enumerate(lines, 1):
                    if not statement:
                        statement_line = index
                    continued = bool(re.search(r";\s*$", line))
                    part = re.sub(r";\s*$", "", line).strip()
                    statement = (statement + " " + part).strip()
                    if continued:
                        continue
                    prg = PRG_DEF_RE.match(statement)
                    if prg:
                        name = prg.group(1)
                        signature = name + (prg.group(2) or "()")
                        result[name.casefold()].append(
                            Evidence(relative, statement_line, "prg-definition", signature)
                        )
                    class_match = PRG_CLASS_RE.match(statement)
                    if class_match:
                        class_name = class_match.group(1)
                        name = class_match.group(2) or class_name
                        article = "an" if class_name[:1].casefold() in "aeiou" else "a"
                        result[name.casefold()].append(
                            Evidence(
                                relative,
                                statement_line,
                                "prg-class",
                                name + "()",
                                "Creates {} {} object.".format(article, class_name),
                                "<o{}>".format(class_name),
                            )
                        )
                    announce = re.match(
                        r"^\s*announce\s+([A-Za-z_$][A-Za-z0-9_$]*)\b",
                        statement,
                        re.IGNORECASE,
                    )
                    if announce:
                        name = announce.group(1)
                        result[name.casefold()].append(
                            Evidence(
                                relative,
                                statement_line,
                                "link-symbol",
                                name + "()",
                                "Linker announcement symbol; it is requested, not called as a function.",
                            )
                        )
                    statement = ""
            if path.suffix.lower() in {".c", ".cpp", ".h"}:
                c_apis.extend((relative, api) for api in scan_c_text(text))

    by_name: dict[str, list[tuple[str, CApi]]] = defaultdict(list)
    for relative, api in c_apis:
        by_name[api.name.casefold()].append((relative, api))

    def arity(signature: str) -> int:
        match = re.search(r"\((.*)\)", signature)
        if not match or not match.group(1).strip():
            return 0
        return len([part for part in match.group(1).split(",") if part.strip()])

    def renamed(name: str, signature: str) -> str:
        match = re.search(r"(\([^\r\n]*\))", signature)
        return name + match.group(1) if match else name + "()"

    def resolve(api: CApi, seen: set[str]) -> CApi:
        if not api.target or api.target.casefold() in seen:
            return api
        targets = by_name.get(api.target.casefold(), [])
        if not targets:
            return api
        target = max((resolve(item, seen | {api.name.casefold()}) for _, item in targets), key=lambda item: arity(item.signature))
        signature = api.signature
        if arity(target.signature) > arity(signature):
            signature = renamed(api.name, target.signature)
        return CApi(
            name=api.name,
            line=api.line,
            signature=signature,
            returns=api.returns or target.returns,
            summary=api.summary or target.summary,
            target=api.target,
        )

    for key, candidates in by_name.items():
        relative, api = max(
            candidates,
            key=lambda item: arity(resolve(item[1], set()).signature),
        )
        api = resolve(api, set())
        result[key].append(
            Evidence(
                relative,
                api.line,
                "c-registration",
                api.signature,
                api.summary,
                api.returns,
            )
        )
    return result


def clean_snippet(value: str) -> str:
    value = value.replace("\\n", " ").replace("\\t", " ")
    value = re.sub(r"\$\{\d+:([^}]*)\}", r"\1", value)
    value = re.sub(r"\$\{\d+\}", "", value)
    value = value.replace("\\{", "{").replace("\\}", "}")
    return re.sub(r"\s+", " ", value).strip()


def scan_completions(paths: list[Path]) -> tuple[dict[str, str], dict[str, list[Evidence]]]:
    result: dict[str, str] = {}
    evidence: dict[str, list[Evidence]] = defaultdict(list)
    pattern = re.compile(
        r'"trigger"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"\s*,\s*'
        r'"contents"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"',
        re.IGNORECASE,
    )
    for path in paths:
        if not path.is_file():
            continue
        text = decode(path.read_bytes())
        for match in pattern.finditer(text):
            trigger = bytes(match.group(1), "utf-8").decode("unicode_escape", errors="replace")
            name = trigger.split("\\t", 1)[0].split("\t", 1)[0].strip()
            if NAME_RE.fullmatch(name):
                value = bytes(match.group(2), "utf-8").decode("unicode_escape", errors="replace")
                value = clean_snippet(value)
                if value:
                    key = name.casefold()
                    result.setdefault(key, value)
                    try:
                        source_path = path.relative_to(ROOT).as_posix()
                    except ValueError:
                        source_path = path.as_posix()
                    evidence[key].append(
                        Evidence(
                            source_path,
                            text.count("\n", 0, match.start()) + 1,
                            "curated-completion",
                            value,
                            "",
                        )
                    )
    return result, evidence


def source_version(source: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "Harbour 3.2.1dev (r2026-07-07)"


def preferred_evidence(items: list[Evidence]) -> Evidence | None:
    if not items:
        return None
    priority = {"harbour-doc": 0, "prg-definition": 1, "prg-class": 2, "c-registration": 3, "link-symbol": 4}
    return sorted(items, key=lambda item: (priority.get(item.kind, 9), item.path, item.line))[0]


def normalize_signature(name: str, value: str) -> str:
    value = html.unescape(value).strip()
    value = re.sub(r"\s+", " ", value)
    match = re.search(rf"\b{re.escape(name)}\s*(\([^\r\n]*?\))", value, re.IGNORECASE)
    return name + match.group(1) if match else f"{name}(...)"


def result_from_usage(value: str) -> str:
    match = re.search(
        r"--?>\s*(<[^<>\r\n]+>|[A-Za-z][A-Za-z0-9_]*)",
        html.unescape(value),
    )
    return match.group(1).strip() if match else ""


def parameters(signature: str) -> list[str]:
    match = re.search(r"\((.*)\)", signature)
    if not match or not match.group(1).strip() or match.group(1).strip() == "...":
        return []
    return [part.strip() for part in match.group(1).split(",") if part.strip()]


def signature_arity(signature: str) -> int:
    return len(parameters(signature))


def build(hbmk2: Path, source: Path, local: Path, asistex: Path) -> None:
    raw, inventory, function_rows, library_headers = run_inventory(hbmk2)
    docs = scan_docs(source)
    definitions = scan_definitions(source)
    completion_files = [local]
    if asistex.is_dir():
        completion_files.extend(sorted(asistex.glob("*.sublime-completions")))
    curated, completion_evidence = scan_completions(completion_files)
    version = source_version(source)
    canonical: list[dict[str, object]] = []
    missing: list[dict[str, str]] = []

    for key in sorted(inventory):
        raw_record = inventory[key]
        name = str(raw_record["name"])
        evidence_items = docs.get(key, []) + definitions.get(key, []) + completion_evidence.get(key, [])
        evidence = preferred_evidence(evidence_items)
        internal = name.upper().startswith("__HBEXTERN__")
        link_symbol = any(item.kind == "link-symbol" for item in evidence_items) or name.upper().startswith(
            ("HB_CODEPAGE_", "HB_LANG_", "HB_GT_")
        ) or name.upper() == "SYSINIT"
        visibility = "internal" if internal else "link-symbol" if link_symbol else "public"
        if evidence:
            suggested = curated.get(key, "")
            priority = {"harbour-doc": 0, "prg-definition": 1, "prg-class": 2, "c-registration": 3, "curated-completion": 4, "link-symbol": 5}
            ranked = sorted(
                evidence_items,
                key=lambda item: (priority.get(item.kind, 9), item.path, item.line),
            )
            usable = [
                (item, normalize_signature(name, item.signature))
                for item in ranked
                if not normalize_signature(name, item.signature).endswith("(...)")
            ]
            if usable:
                signature_evidence, signature = usable[0]
            elif suggested and not normalize_signature(name, suggested).endswith("(...)"):
                signature_evidence, signature = evidence, normalize_signature(name, suggested)
            else:
                signature_evidence, signature = evidence, normalize_signature(name, evidence.signature)
            curated_signature = normalize_signature(name, suggested) if suggested else ""
            if curated_signature and signature_arity(curated_signature) > signature_arity(signature):
                signature = curated_signature
            descriptive = [item for item, _ in usable]
            summary_evidence = next((item for item in descriptive if item.summary), None)
            return_evidence = next((item for item in descriptive if item.returns), None)
            platform_evidence = next(
                (item for item in descriptive if item.platform and item.platform != "all"),
                signature_evidence,
            )
            summary = (
                summary_evidence.summary
                if summary_evidence
                else f"Harbour function {name}."
            )
            returns = return_evidence.returns if return_evidence else signature_evidence.returns
            usage = suggested or signature
            documented_result = next(
                (
                    result_from_usage(item.signature)
                    for item in descriptive
                    if result_from_usage(item.signature)
                ),
                "",
            )
            if not result_from_usage(usage):
                if documented_result:
                    usage += " -> " + documented_result
                elif re.fullmatch(r"<[A-Za-z][A-Za-z0-9_]*>", returns):
                    usage += " -> " + returns
            record = {
                **raw_record,
                "installed": any(bool(item["installed"]) for item in raw_record["libraries"]),
                "visibility": visibility,
                "signature": signature,
                "snippet": usage,
                "summary": summary,
                "parameters": parameters(signature),
                "return": returns,
                "platform": platform_evidence.platform,
                "source_version": version,
                "source": {
                    "path": signature_evidence.path,
                    "line": signature_evidence.line,
                    "evidence": signature_evidence.kind,
                },
                "review_status": "verified",
            }
        else:
            suggested = curated.get(key, "")
            suggested_signature = normalize_signature(name, suggested) if suggested else f"{name}()"
            if suggested_signature.endswith("(...)"):
                suggested_signature = f"{name}()"
            record = {
                **raw_record,
                "installed": any(bool(item["installed"]) for item in raw_record["libraries"]),
                "visibility": visibility,
                "signature": suggested_signature,
                "snippet": suggested or suggested_signature,
                "summary": (
                    "Linker registration symbol; it is requested, not called as a function."
                    if link_symbol
                    else "Reported by hbmk2; detailed source documentation is pending."
                ),
                "parameters": parameters(suggested_signature),
                "return": "",
                "platform": "",
                "source_version": version,
                "source": None,
                "review_status": "missing-source",
            }
            missing.append({"name": name, "reason": "No direct source or documentation evidence found."})
        canonical.append(record)

    libraries = sorted(library_headers, key=str.casefold)
    write_text_if_changed(ROOT / "catalog" / "raw" / "hbmk2-find.txt", raw)
    write_json(ROOT / "catalog" / "raw" / "inventory.json", list(inventory.values()))
    write_json(ROOT / "catalog" / "canonical.json", canonical)
    write_json(ROOT / "catalog" / "reports" / "source-missing.json", missing)
    write_json(
        ROOT / "catalog" / "reports" / "summary.json",
        {
            "function_rows": function_rows,
            "unique_functions": len(canonical),
            "libraries": len(libraries),
            "source_verified": len(canonical) - len(missing),
            "source_missing": len(missing),
            "source_version": version,
        },
    )
    public_records = [item for item in canonical if item["visibility"] == "public"]
    write_json(
        ROOT / "catalog" / "reports" / "help-quality.json",
        {
            "public_callables": len(public_records),
            "source_verified_public": sum(
                item["review_status"] == "verified" for item in public_records
            ),
            "placeholder_signatures": sum(
                "(...)" in str(item["signature"]) for item in public_records
            ),
            "no_parameter_signatures": sum(
                bool(re.search(r"\(\s*\)$", str(item["signature"])))
                for item in public_records
            ),
            "return_descriptions": sum(bool(item["return"]) for item in public_records),
            "link_symbols_excluded": sum(
                item["visibility"] == "link-symbol" for item in canonical
            ),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hbmk2", type=Path, default=DEFAULT_HBMK2)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--local-completions", type=Path, default=DEFAULT_LOCAL)
    parser.add_argument("--asistex", type=Path, default=DEFAULT_ASISTEX)
    args = parser.parse_args()
    build(args.hbmk2, args.source, args.local_completions, args.asistex)


if __name__ == "__main__":
    main()
