from __future__ import annotations

import zipfile
from pathlib import Path

from common import ROOT, sha256, write_text_if_changed


def main() -> None:
    source = ROOT / "package" / "Harbour"
    target = ROOT / "local-only" / "dist" / "Harbour.sublime-package"
    if not source.is_dir():
        raise SystemExit("Package has not been generated")
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(source.rglob("*"), key=lambda value: value.as_posix()):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            info = zipfile.ZipInfo(path.relative_to(source).as_posix())
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes())
    write_text_if_changed(
        ROOT / "local-only" / "dist" / "SHA256SUMS.txt",
        f"{sha256(target)}  {target.name}",
    )


if __name__ == "__main__":
    main()
