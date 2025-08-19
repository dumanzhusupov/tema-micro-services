#!/usr/bin/env python3
"""
Replace all occurrences of "$$" with "$" in JSONL files.

Usage examples:
  - Single file:
      python scripts/replace_double_dollars.py --path data/retrieved_jsonl/retrieved.jsonl
  - Folder (recursive over *.jsonl):
      python scripts/replace_double_dollars.py --path data/retrieved_jsonl
  - Dry run (no writes):
      python scripts/replace_double_dollars.py --path data/retrieved_jsonl --dry-run
  - Create .bak backups:
      python scripts/replace_double_dollars.py --path data/retrieved_jsonl --backup
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import re


def replace_in_file(file_path: Path, dry_run: bool = False, backup: bool = False) -> int:
    """Replace all occurrences of $$. Returns number of replacements."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[SKIP] {file_path} (read error: {e})")
        return 0

    before = len(re.findall(r"\$\$", text))
    if before == 0:
        print(f"[OK]   {file_path} — no $$ found")
        return 0

    new_text = text.replace("$$", "$")
    after = len(re.findall(r"\$\$", new_text))
    replaced = before - after

    if dry_run:
        print(f"[DRY]  {file_path} — would replace {replaced} occurrence(s)")
        return replaced

    try:
        if backup:
            bak = file_path.with_suffix(file_path.suffix + ".bak")
            bak.write_text(text, encoding="utf-8")
        file_path.write_text(new_text, encoding="utf-8")
        print(f"[DONE] {file_path} — replaced {replaced} occurrence(s)")
        return replaced
    except Exception as e:
        print(f"[FAIL] {file_path} (write error: {e})")
        return 0


def iter_target_files(root: Path):
    if root.is_file():
        if root.suffix.lower() == ".jsonl":
            yield root
        else:
            print(f"[SKIP] {root} — not a .jsonl file")
        return

    for p in root.rglob("*.jsonl"):
        if p.is_file():
            yield p


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replace all '$$' with '$' in JSONL files")
    parser.add_argument("--path", required=True, help="Path to a .jsonl file or a folder")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files, just report")
    parser.add_argument("--backup", action="store_true", help="Create .bak backups before writing")
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.exists():
        print(f"Path not found: {root}")
        return 2

    total = 0
    count_files = 0
    for f in iter_target_files(root):
        count_files += 1
        total += replace_in_file(f, dry_run=args.dry_run, backup=args.backup)

    if count_files == 0:
        print("No .jsonl files found to process.")
    else:
        print(f"Summary: processed {count_files} file(s), {total} replacement(s) total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
