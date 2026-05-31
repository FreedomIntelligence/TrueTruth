#!/usr/bin/env python3
"""Validate evidence .md files — used by pre-commit and CI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pydantic import ValidationError
from hypertensiondb.schema.loader import load_evidence

REQUIRED_SECTIONS = {"abstract_zh", "methods", "results", "conclusion"}


def validate_file(path: Path) -> list[str]:
    """Return list of error messages. Empty list = valid."""
    errors: list[str] = []

    try:
        fm, sections = load_evidence(path)
    except ValidationError as e:
        return [f"Schema validation failed:\n{e}"]
    except Exception as e:
        return [f"Parse error: {e}"]

    # Filename check only applies to files inside evidence/ (where IDs must match names)
    if "evidence" in path.parts:
        expected_name = f"{fm.id}.md"
        if path.name != expected_name:
            errors.append(
                f"Filename mismatch: file is '{path.name}', frontmatter id is '{fm.id}' "
                f"(expected filename '{expected_name}')"
            )

    for section_key in REQUIRED_SECTIONS:
        if not sections.get(section_key, "").strip():
            errors.append(f"Required section '{section_key}' is empty or missing")

    return errors


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: validate_evidence.py <file.md> [file2.md ...]")
        sys.exit(1)

    any_failed = False
    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.suffix != ".md":
            continue
        errors = validate_file(path)
        if errors:
            any_failed = True
            print(f"FAIL: {path}")
            for e in errors:
                print(f"  {e}")
        else:
            print(f"OK:   {path}")

    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()
