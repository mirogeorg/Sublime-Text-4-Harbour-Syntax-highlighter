from __future__ import annotations

import re
import shutil
from pathlib import Path

from common import ROOT, write_json


DEFAULT_LOCAL = (
    ROOT
    / "local-only"
    / "archive"
    / "current-module-20260809"
)
DESTINATION = ROOT / "package" / "Harbour" / "snippets" / "OKT"
BLOCKED = [
    re.compile(rb"[A-Za-z]:\\"),
    re.compile(rb"\\\\[A-Za-z0-9_.-]+\\"),
    re.compile(rb"(?:api[_-]?key|password|secret)\s*[:=]", re.IGNORECASE),
]


def copy_reviewed(source: Path = DEFAULT_LOCAL) -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    exclusions = []
    for path in sorted(source.glob("help*.sublime-snippet"), key=lambda item: item.name.casefold()):
        data = path.read_bytes()
        reasons = [pattern.pattern.decode("ascii", errors="replace") for pattern in BLOCKED if pattern.search(data)]
        if reasons:
            exclusions.append({"name": path.name, "reasons": reasons})
            target = DESTINATION / path.name
            if target.exists():
                target.unlink()
            continue
        shutil.copy2(path, DESTINATION / path.name)
    write_json(ROOT / "catalog" / "reports" / "snippet-exclusions.json", exclusions)


if __name__ == "__main__":
    copy_reviewed()
