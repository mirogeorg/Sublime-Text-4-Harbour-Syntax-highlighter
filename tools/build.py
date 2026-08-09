from __future__ import annotations

from archive_current_module import ARCHIVE, DEFAULT_SOURCE, archive
from build_catalog import DEFAULT_ASISTEX, DEFAULT_HBMK2, DEFAULT_LOCAL, DEFAULT_SOURCE, build
from copy_reviewed_snippets import copy_reviewed
from generate_package import generate
from package_release import main as package_release


def main() -> None:
    if not (ARCHIVE / "ORIGIN.md").is_file():
        if DEFAULT_SOURCE.is_dir():
            archive()
        else:
            print(
                "Skipping local module snapshot: the optional source package "
                f"was not found at {DEFAULT_SOURCE}."
            )
    build(DEFAULT_HBMK2, DEFAULT_SOURCE, DEFAULT_LOCAL, DEFAULT_ASISTEX)
    generate()
    copy_reviewed()
    package_release()


if __name__ == "__main__":
    main()
