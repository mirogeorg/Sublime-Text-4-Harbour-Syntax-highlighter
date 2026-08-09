# Sublime Text 4 Harbour Syntax highlighter

A source-aware Sublime Text 4 package for Harbour/xBase development. It combines
native syntax highlighting with rich completions, searchable function help,
curated snippets, generated symbol metadata and regression tests.

The installable package is `package/Harbour`. The project is licensed under
`GPL-3.0-or-later`; see [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the upstream material
used during generation.

## What it provides

- Native Sublime Text `version: 2` syntax with the `source.harbour` scope.
- Automatic syntax selection for `.prg`, `.hb`, `.ch`, `.ppo`, `.res` and
  `.idu` files. C/C++ files are deliberately left to their own syntaxes.
- Coverage for Harbour comments, strings, literals, operators, aliases,
  members, macros, by-reference expressions, declarations, preprocessor
  directives and DBSTRU `.res` files.
- Rich completions with tab stops, return annotations and short help text.
- Two Command Palette commands:
  - `Harbour: Function Help` — browse the verified function catalog.
  - `Harbour: Help for Symbol Under Cursor` — show help for the symbol at the
    caret.
- Curated snippets for common Harbour constructs and reviewed OKT database
  helpers.
- A generated catalog that records libraries, installation state, signatures,
  parameters, returns, platform, source evidence and review status.
- Source-aware C API inference that follows `HB_FUNC`, aliases, macro wrapper
  families, `hb_par*`, `hb_param()` and `hb_ret*` registrations.
- Deterministic generation, SHA-256 release checksums and automated checks for
  duplicate symbols, incomplete help, unsafe text, invalid signatures and
  package contents.

The current catalog snapshot contains 6,237 unique symbols from 67 Harbour
libraries. It exposes 6,014 source-verified public callables in completions and
help. The exact current counts are always available in
`catalog/reports/summary.json` and `catalog/reports/help-quality.json`.

## Install in Sublime Text 4

1. Close Sublime Text 4, or reload the package after copying it.
2. Copy the `package/Harbour` directory into Sublime Text's `Packages`
   directory.
3. Open a Harbour source file and use the Command Palette to run one of the
   Harbour help commands.

On Windows the destination is usually:

```text
%APPDATA%\Sublime Text\Packages\Harbour
```

The package can also be installed from the generated
`local-only/dist/Harbour.sublime-package` release bundle when a local build has
been produced.

## Build and validate

The repository contains generated package data so it can be inspected and
installed without rebuilding. Regeneration needs Python 3.10+ plus a matching
Harbour source tree and `hbmk2` executable.

On the development machine, the complete workflow is:

```powershell
python tools/build.py
python -m unittest discover -s tests -v
python tools/validate.py
```

For another machine, provide paths explicitly to the catalog builder and then
run the remaining generators:

```powershell
python tools/build_catalog.py --hbmk2 <path-to-hbmk2.exe> --source <path-to-harbour-source>
python tools/generate_package.py
python tools/copy_reviewed_snippets.py
python tools/package_release.py
python -m unittest discover -s tests -v
python tools/validate.py
```

The build refreshes the raw `hbmk2 -find "*"` inventory, verifies symbols
against Harbour documentation and source, generates the syntax/completion/help
files, creates the deterministic package bundle and validates the result.
Symbols reported by `hbmk2` without source evidence remain available for
syntax coloring but are intentionally excluded from autocomplete and help.

## Local deployment

To install the generated folder into a local Sublime Text installation:

```powershell
.\scripts\deploy-local.ps1
```

The deployment script stages and hashes the package, preserves the previous
installation, verifies the deployed tree and restores the backup if anything
fails. Restore the previous package with:

```powershell
.\scripts\rollback-local.ps1
```

## Repository layout

```text
package/Harbour/       Installable Sublime Text package
catalog/               Raw inventory, canonical records and quality reports
tools/                 Catalog, generation, packaging and validation tools
scripts/               Local install and rollback scripts
tests/                 Automated and manual syntax fixtures
PLAN.md                Design and acceptance criteria
```

`local-only/` is intentionally absent from the published repository. It is the
single ignored home for migration snapshots, source caches, deployment
manifests/rollback trees and generated `.sublime-package` bundles. Nothing in
that directory is required to use the already-generated package.

## Scope

This release focuses on Harbour editing in Sublime Text 4. It does not provide
Harbour compiler integration and does not claim `.c`, `.h`, `.hbp`, `.hbc` or
`.hbm` files. Harbour source and third-party inputs are referenced for
provenance; the Harbour source tree itself is not redistributed.
