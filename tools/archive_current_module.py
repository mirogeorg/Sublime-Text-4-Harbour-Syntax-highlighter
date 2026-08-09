from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from common import ROOT, sha256, write_text_if_changed


DEFAULT_SOURCE = Path(r"D:\accounts\st4\Data\Packages\harbour")
ARCHIVE = ROOT / "local-only" / "archive" / "current-module-20260809"


def archive(source: Path = DEFAULT_SOURCE, replace: bool = False) -> None:
    if not source.is_dir():
        raise SystemExit(f"Current Harbour package not found: {source}")
    if (ARCHIVE / "ORIGIN.md").is_file() and not replace:
        return
    if replace and ARCHIVE.exists():
        shutil.rmtree(ARCHIVE)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for item in sorted(source.iterdir(), key=lambda value: value.name.casefold()):
        target = ARCHIVE / item.name
        if item.is_dir():
            shutil.copytree(item, target, copy_function=shutil.copy2, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)

    payload = [
        path
        for path in sorted(ARCHIVE.rglob("*"), key=lambda value: value.as_posix().casefold())
        if path.is_file() and path.name not in {"ORIGIN.md", "TREE.txt", "SHA256SUMS.txt"}
    ]
    tree = "\n".join(path.relative_to(ARCHIVE).as_posix() for path in payload)
    sums = "\n".join(
        f"{sha256(path)}  {path.relative_to(ARCHIVE).as_posix()}" for path in payload
    )
    write_text_if_changed(ARCHIVE / "TREE.txt", tree)
    write_text_if_changed(ARCHIVE / "SHA256SUMS.txt", sums)
    write_text_if_changed(
        ARCHIVE / "ORIGIN.md",
        """# Archived module origin

This directory is a byte-for-byte copy of the pre-existing Sublime Text 4
Harbour package from `D:\\accounts\\st4\\Data\\Packages\\harbour`, captured
for the 2026-08-09 migration. `TREE.txt` and `SHA256SUMS.txt` describe the
payload. The archive is excluded from package generation and installation.
""",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    archive(args.source, replace=args.replace)


if __name__ == "__main__":
    main()
