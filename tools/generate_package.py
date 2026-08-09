from __future__ import annotations

import html
import json
import re
from pathlib import Path

from common import ROOT, write_json, write_text_if_changed


PACKAGE = ROOT / "package" / "Harbour"
CHUNK_LIMIT = 1900


def regex_chunks(names: list[str]) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for name in names:
        escaped = re.escape(name)
        extra = len(escaped) + (1 if current else 0)
        if current and current_size + extra > CHUNK_LIMIT:
            chunks.append("|".join(current))
            current, current_size = [], 0
        current.append(escaped)
        current_size += extra
    if current:
        chunks.append("|".join(current))
    return chunks


def syntax_file(names: list[str]) -> str:
    chunks = regex_chunks(names)
    variables = "\n".join(
        f"  function_names_{index:03d}: '{chunk}'" for index, chunk in enumerate(chunks)
    )
    call_rules = "\n".join(
        "    - match: '(?i)\\b(?:{{function_names_%03d}})\\b(?=\\s*\\()'\n"
        "      scope: support.function.harbour" % index
        for index in range(len(chunks))
    )
    do_rules = "\n".join(
        "    - match: '(?i)(?<=\\bDO\\s)(?:{{function_names_%03d}})\\b'\n"
        "      scope: support.function.harbour" % index
        for index in range(len(chunks))
    )
    return f"""%YAML 1.2
---
name: Harbour
scope: source.harbour
version: 2
file_extensions:
  - prg
  - hb
  - ch
  - ppo
  - res
  - idu

variables:
  identifier: '[A-Za-z_$][A-Za-z0-9_$]*'
{variables}

contexts:
  main:
    - include: comments
    - include: preprocessor
    - include: strings
    - include: declarations
    - include: literals
    - include: dbstru
    - include: members
    - include: operators
    - include: known-function-calls
    - include: do-procedure-calls
    - include: keywords
    - include: invalid

  comments:
    - match: '^\\s*\\*(?![=*])'
      scope: punctuation.definition.comment.asterisk.harbour
      push:
        - meta_scope: comment.line.asterisk.harbour
        - match: '$'
          pop: true
    - match: '&&'
      scope: punctuation.definition.comment.double-ampersand.harbour
      push:
        - meta_scope: comment.line.double-ampersand.harbour
        - match: '$'
          pop: true
    - match: '//'
      scope: punctuation.definition.comment.double-slash.harbour
      push:
        - meta_scope: comment.line.double-slash.harbour
        - match: '$'
          pop: true
    - match: '/\\*'
      scope: punctuation.definition.comment.block.begin.harbour
      push:
        - meta_scope: comment.block.harbour
        - match: '\\*/'
          scope: punctuation.definition.comment.block.end.harbour
          pop: true

  preprocessor:
    - match: '^\\s*(#)\\s*(?i:command|xcommand|translate|xtranslate)\\b'
      captures:
        1: punctuation.definition.preprocessor.harbour
      push:
        - meta_scope: meta.preprocessor.harbour
        - match: '(<[^>]*>)'
          scope: variable.parameter.preprocessor.harbour
        - match: '(=>)'
          scope: keyword.operator.assignment.preprocessor.harbour
        - match: ';\\s*\\n'
          scope: punctuation.separator.continuation.harbour
        - match: '\\n'
          pop: true
    - match: '^\\s*(#)\\s*(?i:define|undef|include|if|ifdef|ifndef|elif|else|endif|pragma|error|warning|line)\\b'
      captures:
        1: punctuation.definition.preprocessor.harbour
      push:
        - meta_scope: meta.preprocessor.harbour
        - include: strings
        - match: ';\\s*\\n'
          scope: punctuation.separator.continuation.harbour
        - match: '\\n'
          pop: true

  strings:
    - match: '(?i:e)"'
      scope: punctuation.definition.string.begin.harbour
      push:
        - meta_scope: string.quoted.double.escape.harbour
        - match: '\\\\(?:[abefnrtv\\\\"''?]|x[0-9A-Fa-f]{{2}}|u[0-9A-Fa-f]{{4}})'
          scope: constant.character.escape.harbour
        - match: '"'
          scope: punctuation.definition.string.end.harbour
          pop: true
        - match: '$'
          scope: invalid.illegal.unclosed-string.harbour
          pop: true
    - match: "'"
      scope: punctuation.definition.string.begin.harbour
      push:
        - meta_scope: string.quoted.single.harbour
        - match: "''"
          scope: constant.character.escape.harbour
        - match: "'"
          scope: punctuation.definition.string.end.harbour
          pop: true
        - match: '$'
          scope: invalid.illegal.unclosed-string.harbour
          pop: true
    - match: '"'
      scope: punctuation.definition.string.begin.harbour
      push:
        - meta_scope: string.quoted.double.harbour
        - match: '""'
          scope: constant.character.escape.harbour
        - match: '"'
          scope: punctuation.definition.string.end.harbour
          pop: true
        - match: '$'
          scope: invalid.illegal.unclosed-string.harbour
          pop: true
    - match: '(?<![A-Za-z0-9_$)\\]])\\[(?=[^\\r\\n]*\\])'
      scope: punctuation.definition.string.begin.harbour
      push:
        - meta_scope: string.quoted.other.bracket.harbour
        - match: '\\]'
          scope: punctuation.definition.string.end.harbour
          pop: true
        - match: '$'
          scope: invalid.illegal.unclosed-string.harbour
          pop: true

  declarations:
    - match: '(?i)^\\s*((?:(?:static|init|exit)\\s+)?(?:function|procedure|func|proc))\\s+({{{{identifier}}}})'
      captures:
        1: storage.type.function.harbour
        2: entity.name.function.harbour
    - match: '(?i)^\\s*(method)\\s+({{{{identifier}}}})'
      captures:
        1: storage.type.function.harbour
        2: entity.name.function.harbour
    - match: '(?i)^\\s*(class)\\s+({{{{identifier}}}})'
      captures:
        1: storage.type.class.harbour
        2: entity.name.class.harbour
    - match: '(?i)\\b(local|static|private|public|field|memvar|parameters|default|external|request|global)\\b'
      scope: storage.type.harbour

  literals:
    - match: '\\{{\\^\\d{{4}}-\\d{{2}}-\\d{{2}}(?:[ T]\\d{{2}}:\\d{{2}}(?::\\d{{2}}(?:\\.\\d+)?)?)?\\}}'
      scope: constant.other.datetime.harbour
    - match: '(?i)\\.(?:T|F|Y|N)\\.'
      scope: constant.language.boolean.harbour
    - match: '(?i)\\bNIL\\b'
      scope: constant.language.null.harbour
    - match: '(?i)\\b0x[0-9a-f]+\\b|\\b(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:e[+-]?\\d+)?\\b'
      scope: constant.numeric.harbour

  dbstru:
    - match: '^\\s*\\$\\$\\$(?:MAIN|FILE_[A-Za-z0-9_]+)\\b'
      scope: entity.name.section.dbstru.harbour
    - match: '^\\s*###END\\b'
      scope: keyword.control.terminator.dbstru.harbour

  operators:
    - match: ':=|\\*\\*=|\\*\\*|<>|!=|==|<=|>=|->|::|\\+\\+|--|\\$|[+*/%<>=@&:-]'
      scope: keyword.operator.harbour

  members:
    - match: '(->|::|:)(?:{{{{identifier}}}})'
      captures:
        1: keyword.operator.accessor.harbour
      scope: variable.other.member.harbour

  known-function-calls:
{call_rules}

  do-procedure-calls:
{do_rules}

  keywords:
    - match: '(?i)\\b(?:if|elseif|else|endif|do|case|otherwise|endcase|switch|endswitch|while|enddo|for|each|next|loop|exit|return|begin|sequence|recover|always|try|catch|finally|throw|with|object|endwith|class|endclass|method|data|access|assign|inline|in|to|step)\\b'
      scope: keyword.control.harbour
    - match: '(?i)\\b(?:and|or|not)\\b|\\.(?i:and|or|not)\\.'
      scope: keyword.operator.logical.harbour

  invalid:
    - match: '\\*/'
      scope: invalid.illegal.stray-comment-end.harbour
    - match: '(?<![<>=!])=>'
      scope: invalid.illegal.stray-result-marker.harbour
"""


def completion_contents(signature: str) -> str:
    match = re.match(r"([^()]*)\((.*)\)$", signature)
    if not match:
        return signature
    args = []
    for index, argument in enumerate(
        [item.strip() for item in match.group(2).split(",") if item.strip()], 1
    ):
        safe = argument.replace("$", "\\$").replace("}", "\\}")
        args.append(f"${{{index}:{safe}}}")
    return f"{match.group(1)}({', '.join(args)})"


def callable_expression(name: str, value: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\(", value, re.IGNORECASE)
    if not match:
        return f"{name}()"
    start = match.start()
    position = match.end() - 1
    depth = 0
    quote = ""
    while position < len(value):
        char = value[position]
        if quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return value[start : position + 1]
        position += 1
    return f"{name}()"


def completion_result_label(item: dict[str, object], usage: str) -> str:
    returns = str(item.get("return") or "").strip()
    match = re.search(r"<[A-Za-z][A-Za-z0-9_]*>", returns)
    if match:
        return match.group(0)
    arrow = re.search(r"--?>\s*([^—\r\n]+)$", usage)
    if arrow:
        value = arrow.group(1).strip()
        if value and len(value) <= 48:
            return value
    if returns.upper() == "NIL":
        return "NIL"
    return ""


def generate() -> None:
    canonical_path = ROOT / "catalog" / "canonical.json"
    if not canonical_path.is_file():
        raise SystemExit("Run tools/build_catalog.py first")
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    names = sorted((item["name"] for item in canonical), key=str.casefold)
    public = [
        item
        for item in canonical
        if item["visibility"] == "public"
    ]
    write_text_if_changed(PACKAGE / "Harbour.sublime-syntax", syntax_file(names))

    completions = []
    help_records = {}
    for item in public:
        usage = item["snippet"] or item["signature"] or f"{item['name']}()"
        result_label = completion_result_label(item, usage)
        completion = {
            "trigger": item["name"],
            "contents": completion_contents(callable_expression(item["name"], usage)),
            "kind": ["snippet", "s", "Help"],
            # Completion details are rendered as minihtml by Sublime Text.
            # Escape Harbour's conventional <cValue> notation so it stays
            # visible instead of being parsed as an HTML element.
            "details": html.escape(f"{usage} — {item['summary']}"),
        }
        if result_label:
            completion["annotation"] = result_label
        completions.append(completion)
        help_records[item["key"]] = item
    write_json(
        PACKAGE / "completions" / "Harbour.sublime-completions",
        {
            "scope": "source.harbour",
            "inhibit_word_completions": True,
            "completions": completions,
        },
    )
    write_json(PACKAGE / "data" / "function_help.json", help_records)

    lines = ["// SYNTAX TEST \"Packages/Harbour/Harbour.sublime-syntax\"", ""]
    for name in names:
        lines.extend(
            [
                f"{name}()",
                "// <- support.function.harbour",
            ]
        )
    write_text_if_changed(PACKAGE / "tests" / "syntax_test_all_functions.prg", "\n".join(lines))


if __name__ == "__main__":
    generate()
