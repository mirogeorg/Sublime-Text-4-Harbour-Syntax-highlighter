from __future__ import annotations

import re
from dataclasses import dataclass


FUNC_RE = re.compile(
    r"\bHB_FUNC(?:_STATIC)?\s*\(\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\)"
)
TRANSLATE_RE = re.compile(
    r"\bHB_FUNC_TRANSLATE\s*\(\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*,\s*"
    r"([A-Za-z_$][A-Za-z0-9_$]*)\s*\)"
)
UR_SUPER_RE = re.compile(
    r"\bHB_FUNC_UR_SUPER\s*\(\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\)"
)
EXPAT_HANDLER_RE = re.compile(
    r"\bHB_EXPAT_SETHANDLER\s*\(\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*\)"
)
EXEC_RE = re.compile(
    r"\bHB_FUNC_EXEC\s*\(\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\)"
)


@dataclass(frozen=True)
class CApi:
    name: str
    line: int
    signature: str
    returns: str
    summary: str
    target: str = ""


@dataclass
class Param:
    index: int
    types: set[str]
    names: list[str]
    optional: bool = False
    byref: bool = False


def mask_c(text: str) -> str:
    """Mask comments and literals while preserving offsets and newlines."""
    chars = list(text)
    state = "code"
    index = 0
    while index < len(chars):
        char = chars[index]
        nxt = chars[index + 1] if index + 1 < len(chars) else ""
        if state == "code":
            if char == "/" and nxt == "/":
                chars[index] = chars[index + 1] = " "
                state = "line"
                index += 2
                continue
            if char == "/" and nxt == "*":
                chars[index] = chars[index + 1] = " "
                state = "block"
                index += 2
                continue
            if char == '"':
                chars[index] = " "
                state = "string"
            elif char == "'":
                chars[index] = " "
                state = "char"
        elif state == "line":
            if char == "\n":
                state = "code"
            else:
                chars[index] = " "
        elif state == "block":
            if char == "*" and nxt == "/":
                chars[index] = chars[index + 1] = " "
                state = "code"
                index += 2
                continue
            if char != "\n":
                chars[index] = " "
        else:
            if char == "\\" and nxt:
                chars[index] = " "
                if nxt != "\n":
                    chars[index + 1] = " "
                index += 2
                continue
            if (state == "string" and char == '"') or (
                state == "char" and char == "'"
            ):
                chars[index] = " "
                state = "code"
            elif char != "\n":
                chars[index] = " "
        index += 1
    return "".join(chars)


def matching_brace(masked: str, opening: int) -> int:
    depth = 0
    for index in range(opening, len(masked)):
        if masked[index] == "{":
            depth += 1
        elif masked[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return -1


def expanded_with_local_helpers(text: str, masked: str, body: str, depth: int = 2) -> str:
    expanded = body
    pending = [body]
    visited: set[str] = set()
    controls = {"if", "for", "while", "switch", "return", "sizeof"}
    for _ in range(depth):
        following: list[str] = []
        for fragment in pending:
            for call in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", mask_c(fragment)):
                name = call.group(1)
                if name in visited or name.casefold() in controls or name.startswith(("hb_par", "hb_ret", "hb_stor")):
                    continue
                visited.add(name)
                definition = re.compile(
                    r"(?m)^[ \t]*(?:static\s+)?[A-Za-z_][A-Za-z0-9_ \t*]*\b"
                    + re.escape(name)
                    + r"\s*\([^;{}]*\)\s*\{"
                ).search(masked)
                if not definition:
                    continue
                opening = masked.find("{", definition.start(), definition.end())
                closing = matching_brace(masked, opening)
                if closing < 0:
                    continue
                helper = text[opening : closing + 1]
                expanded += "\n" + helper
                following.append(helper)
        pending = following
        if not pending:
            break
    return expanded


def type_from_item_flags(flags: str) -> str:
    found = set(re.findall(r"HB_IT_([A-Z]+)", flags.upper()))
    mapping = {
        "STRING": "c",
        "MEMO": "c",
        "NUMERIC": "n",
        "INTEGER": "n",
        "LONG": "n",
        "DOUBLE": "n",
        "LOGICAL": "l",
        "DATE": "d",
        "TIMESTAMP": "t",
        "ARRAY": "a",
        "HASH": "h",
        "BLOCK": "b",
        "OBJECT": "o",
        "POINTER": "p",
        "SYMBOL": "s",
    }
    types = {mapping[item] for item in found if item in mapping}
    return next(iter(types)) if len(types) == 1 else "x"


def type_from_accessor(accessor: str) -> str:
    value = accessor.casefold()
    if value.startswith("v"):
        return "a"
    if any(token in value for token in ("str", "astr")):
        return "c"
    if value.startswith(("c", "cx", "clen", "csiz")):
        return "c"
    if value.startswith("l"):
        return "l"
    if value.startswith(("td", "tdt")):
        return "t"
    if value.startswith(("d", "ds", "dl")):
        return "d"
    if value.startswith(("n", "ni", "nl", "nd", "ns", "nint", "nll")):
        return "n"
    if "ptr" in value or "handle" in value:
        return "p"
    if "gdimage" in value:
        return "o"
    if "gdfont" in value:
        return "o"
    return "x"


def type_from_predicate(value: str) -> str:
    mapping = {
        "CHAR": "c",
        "STRING": "c",
        "MEMO": "c",
        "NUM": "n",
        "NUMERIC": "n",
        "LOG": "l",
        "LOGICAL": "l",
        "DATE": "d",
        "DATETIME": "t",
        "TIMESTAMP": "t",
        "ARRAY": "a",
        "HASH": "h",
        "BLOCK": "b",
        "OBJECT": "o",
        "POINTER": "p",
        "SYMBOL": "s",
    }
    return mapping.get(value.upper(), "x")


def assignment_name(body: str, offset: int) -> str:
    line_start = body.rfind("\n", 0, offset) + 1
    prefix = body[line_start:offset]
    match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*$", prefix)
    return match.group(1) if match else ""


def normalized_name(variable: str, kind: str) -> str:
    if not variable:
        return ""
    value = variable.lstrip("_")
    prefixes = (
        ("psz", "c"), ("sz", "c"), ("pc", "c"),
        ("ul", "n"), ("ui", "n"), ("us", "n"),
        ("ll", "n"), ("i", "n"), ("n", "n"),
        ("f", "l"), ("b", "l"),
    )
    for prefix, replacement in prefixes:
        if value.startswith(prefix) and len(value) > len(prefix):
            stem = value[len(prefix):]
            if stem[:1].isupper() or len(prefix) > 1:
                value = replacement + stem[:1].upper() + stem[1:]
                break
    if len(value) > 1 and value[0] in "cnldtahbopsx" and value[1].isupper():
        stem = value[1:]
        return kind + stem if value[0] != kind else value
    stripped = re.sub(r"^(?:pItem|p|x)", "", value)
    if not stripped or stripped.casefold() in {
        "value", "param", "item", "result", "ptr", "data", "buffer", "buf"
    }:
        return ""
    return kind + stripped[:1].upper() + stripped[1:]


def semantic_default(function: str, index: int, kind: str) -> str:
    upper = function.upper()
    digest = any(token in upper for token in ("SHA", "MD5", "HMAC"))
    if digest:
        if kind == "c" and index == 1:
            return "cMessage"
        if kind == "c" and index == 2 and "HMAC" in upper:
            return "cKey"
        if kind == "l" and index in (2, 3):
            return "lRaw"
    if kind == "c" and index == 1:
        if "SPRINTF" in upper or "FORMAT" in upper:
            return "cFormat"
        if "FILE" in upper or "FNAME" in upper:
            return "cFileName"
        if "PATH" in upper or "DIR" in upper:
            return "cPath"
        if "JSON" in upper:
            return "cJSON"
    defaults = {
        "c": "cValue", "n": "nValue", "l": "lValue", "d": "dDate",
        "t": "tTimestamp", "a": "aArray", "h": "hHash", "b": "bBlock",
        "o": "oObject", "p": "pPointer", "s": "sSymbol", "x": "xValue",
    }
    return defaults.get(kind, "xValue")


def return_type(body: str, function: str) -> str:
    kinds: set[str] = set()
    for match in re.finditer(r"\bhb_ret([A-Za-z0-9_]*)\s*\(", body):
        suffix = match.group(1).casefold()
        if suffix.startswith(("c", "str")):
            kinds.add("c")
        elif suffix.startswith("l"):
            kinds.add("l")
        elif suffix.startswith(("td", "tdt")):
            kinds.add("t")
        elif suffix.startswith(("d", "ds", "dl")):
            kinds.add("d")
        elif suffix.startswith("n"):
            kinds.add("n")
        elif suffix.startswith("a"):
            kinds.add("a")
        elif "ptr" in suffix:
            kinds.add("p")
        elif "gdimage" in suffix:
            kinds.add("o")
        elif suffix:
            kinds.add("x")
    if re.search(r"\bhb_itemReturn(?:Release)?\s*\(", body):
        if re.search(r"hb_param\s*\(\s*\d+\s*,\s*HB_IT_HASH", body):
            kinds.add("h")
        elif re.search(r"hb_(?:itemArrayNew|arrayNew)\s*\(", body):
            kinds.add("a")
        else:
            kinds.add("x")
    for match in re.finditer(
        r"\b((?:hb|phb|hbwapi)[A-Za-z0-9_]*(?:_ret(?:_[A-Za-z0-9_]+)?|Ret))\s*\(",
        body,
        re.IGNORECASE,
    ):
        accessor = match.group(1).casefold()
        if accessor.endswith(("_l", "retl")):
            kinds.add("l")
        elif accessor.endswith(("_c", "_str", "retc")):
            kinds.add("c")
        elif any(token in accessor for token in ("_ni", "_nl", "_nd", "retn")):
            kinds.add("n")
        else:
            kinds.add("p")
    if not kinds:
        return ""
    kind = next(iter(kinds)) if len(kinds) == 1 else "x"
    upper = function.upper()
    if kind == "c" and any(token in upper for token in ("SHA", "MD5", "HMAC")):
        return "<cDigest>"
    names = {
        "c": "<cResult>", "n": "<nResult>", "l": "<lResult>",
        "d": "<dDate>", "t": "<tTimestamp>", "a": "<aArray>",
        "h": "<hHash>", "o": "<oObject>", "p": "<pPointer>",
        "x": "<xResult>",
    }
    return names[kind]


def inferred_summary(function: str) -> str:
    upper = function.upper()
    hmac = re.search(r"HMAC[_]?SHA(1|224|256|384|512)", upper)
    if hmac:
        return "Computes an HMAC-SHA{} message authentication code.".format(hmac.group(1))
    sha = re.search(r"(?:^|_)SHA(1|224|256|384|512)$", upper)
    if sha:
        return "Computes the SHA-{} digest of a message.".format(sha.group(1))
    if re.search(r"(?:^|_)MD5$", upper):
        return "Computes the MD5 digest of a message."
    if "SPRINTF" in upper:
        return "Formats values using a printf-style format string."
    return ""


def infer_api(name: str, body: str, line: int) -> CApi:
    masked = mask_c(body)
    params: dict[int, Param] = {}

    def add(index: int, kind: str, variable: str = "", optional: bool = False) -> None:
        if index <= 0:
            return
        param = params.setdefault(index, Param(index, set(), []))
        param.types.add(kind)
        candidate = normalized_name(variable, kind)
        if candidate and candidate not in param.names:
            param.names.append(candidate)
        param.optional = param.optional or optional

    for match in re.finditer(r"\bhb_par(?!am\b)([A-Za-z0-9_]*)\s*\(\s*(-?\d+)", masked):
        index = int(match.group(2))
        suffix = match.group(1)
        add(index, type_from_accessor(suffix), assignment_name(body, match.start()), "def" in suffix.casefold())

    for match in re.finditer(
        r"\bhb_par(?!am\b)([A-Za-z0-9_]*)\s*\(\s*(?!-?\d+\b)[^,\n]+,\s*(\d+)",
        masked,
    ):
        suffix = match.group(1)
        add(
            int(match.group(2)),
            type_from_accessor(suffix),
            assignment_name(body, match.start()),
            "def" in suffix.casefold(),
        )

    for match in re.finditer(
        r"\bhb_param\s*\(\s*(\d+)\s*,\s*([^\)]*)\)", masked
    ):
        add(
            int(match.group(1)),
            type_from_item_flags(match.group(2)),
            assignment_name(body, match.start()),
        )

    for match in re.finditer(r"\bHB_IS([A-Z]+)\s*\(\s*(\d+)\s*\)", masked):
        add(int(match.group(2)), type_from_predicate(match.group(1)))

    custom = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*(\d+)")
    for match in custom.finditer(masked):
        accessor = match.group(1)
        lowered = accessor.casefold()
        if lowered.startswith(("hb_par", "hb_param")):
            continue
        if lowered == "hb_usrgetareaparam":
            continue
        if not lowered.startswith(("hb_", "phb_", "hbwapi_")):
            continue
        if not ("_par" in lowered or lowered.endswith("_is") or lowered.endswith("param")):
            continue
        kind = "o" if any(token in lowered for token in ("image", "font")) else "p"
        add(int(match.group(2)), kind, assignment_name(body, match.start()))

    for match in re.finditer(r"\bhb_stor([A-Za-z0-9_]*)\s*\([^;\n]*?,\s*(\d+)\s*\)", masked):
        suffix = match.group(1)
        index = int(match.group(2))
        if index <= 0:
            continue
        add(index, type_from_accessor(suffix))
        params[index].byref = True

    area = re.search(r"\bhb_usrGetAreaParam\s*\(\s*\d+\s*\)", masked)
    if area:
        add(1, "p", assignment_name(body, area.start()))

    digest = any(token in name.upper() for token in ("SHA", "MD5", "HMAC"))
    used_names: set[str] = set()
    rendered = []
    for index in sorted(params):
        param = params[index]
        kinds = param.types - {"x"}
        kind = next(iter(kinds)) if len(kinds) == 1 else "x"
        candidate = param.names[0] if param.names else semantic_default(name, index, kind)
        upper_name = name.upper()
        if (
            any(token in upper_name for token in ("SHA", "MD5", "HMAC"))
            and ((kind == "c" and index in (1, 2)) or kind == "l")
        ) or ("SPRINTF" in upper_name and kind == "c" and index == 1):
            candidate = semantic_default(name, index, kind)
        if candidate in used_names:
            candidate += str(index)
        used_names.add(candidate)
        if param.byref and not candidate.startswith("@"):
            candidate = "@" + candidate
        value = "<{}>".format(candidate)
        optional = param.optional or (digest and kind == "l" and index > 1)
        rendered.append("[{}]".format(value) if optional else value)

    if re.search(r"\bhb_pcount\s*\(\s*\)", masked) and re.search(
        r"\bhb_param\s*\(\s*(?!\d+\b)[A-Za-z_]", masked
    ):
        rendered.append("[<xArgs>...]")

    target_match = EXEC_RE.search(masked)
    target = target_match.group(1) if target_match else ""
    signature = "{}( {} )".format(name, ", ".join(rendered)) if rendered else "{}()".format(name)
    return CApi(
        name=name,
        line=line,
        signature=signature,
        returns=return_type(masked, name),
        summary=inferred_summary(name),
        target=target,
    )


def scan_c_text(text: str) -> list[CApi]:
    masked = mask_c(text)
    records: list[CApi] = []
    translated_spans = {match.span() for match in TRANSLATE_RE.finditer(masked)}
    for match in TRANSLATE_RE.finditer(masked):
        records.append(
            CApi(
                name=match.group(1),
                line=text.count("\n", 0, match.start()) + 1,
                signature="{}()".format(match.group(1)),
                returns="",
                summary="",
                target=match.group(2),
            )
        )
    for match in EXPAT_HANDLER_RE.finditer(masked):
        line_start = masked.rfind("\n", 0, match.start()) + 1
        if masked[line_start:match.start()].lstrip().startswith("#define"):
            continue
        camel_name = match.group(2)
        records.append(
            CApi(
                name="XML_Set" + camel_name,
                line=text.count("\n", 0, match.start()) + 1,
                signature="XML_Set{}( <pParser>, <bHandler> )".format(camel_name),
                returns="",
                summary="Sets the Expat {} callback.".format(camel_name),
            )
        )
    functions = [(match, match.group(1)) for match in FUNC_RE.finditer(masked)]
    for match in UR_SUPER_RE.finditer(masked):
        line_start = masked.rfind("\n", 0, match.start()) + 1
        if masked[line_start:match.start()].lstrip().startswith("#define"):
            continue
        functions.append((match, "UR_SUPER_" + match.group(1)))
    functions = sorted(functions, key=lambda item: item[0].start())
    for position, (match, function_name) in enumerate(functions):
        if match.span() in translated_spans:
            continue
        opening = masked.find("{", match.end())
        if opening < 0:
            continue
        closing = matching_brace(masked, opening)
        boundary = functions[position + 1][0].start() if position + 1 < len(functions) else len(masked)
        if closing < 0 or closing >= boundary:
            closing = masked.rfind("}", opening, boundary)
        if closing < 0:
            continue
        line = text.count("\n", 0, match.start()) + 1
        body = text[opening : closing + 1]
        body = expanded_with_local_helpers(text, masked, body)
        records.append(infer_api(function_name, body, line))
    return records
