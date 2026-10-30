"""Offline package checks for the three instruction-only skills; no runtime setup."""
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

NAMES = ("job-search", "job-fit-review", "application-prep")
ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]\n]+\]\((<[^>\n]+>|[^)\s]+)\)")


def validate_package(directory):
    """Validate this project's two-scalar frontmatter and local reference closure.

    This is deliberately not a general YAML parser or a semantic agent evaluator.
    Check copied packages in isolation so a repository sibling cannot mask a
    missing dependency. Reject symlinks even if their targets currently exist.
    """
    directory = Path(directory)
    failures = []
    if directory.is_symlink():
        return ["skill directory is a symlink"]
    entry = directory / "SKILL.md"
    if not entry.is_file():
        return ["missing SKILL.md"]
    files = list(directory.rglob("*"))
    if any(path.is_symlink() for path in files):
        return ["symlink inside skill package"]
    text = entry.read_text(encoding="utf-8")
    match = re.match(r"\A---\nname: ([a-z0-9]+(?:-[a-z0-9]+)*)\ndescription: ([^\n]+)\n---\n", text)
    if not match:
        failures.append("expected nonempty scalar name/description frontmatter")
    else:
        name, description = match.groups()
        if name != directory.name or len(name) > 64:
            failures.append("skill name does not match directory or exceeds 64 characters")
        if len(description) > 1024:
            failures.append("description exceeds 1024 characters")
    for path in files:
        if path.is_file() and path.suffix not in {".md", ".yaml"}:
            failures.append(f"unreviewed package file type: {path.name}")
        if not path.is_file() or path.suffix != ".md":
            continue
        body = path.read_text(encoding="utf-8")
        for raw in LINK.findall(body):
            target = raw.strip("<>")
            parts = urlsplit(target)
            if parts.scheme or target.startswith("#"):
                continue
            resolved = (path.parent / unquote(parts.path)).resolve()
            if not resolved.is_relative_to(directory.resolve()):
                failures.append(f"reference escapes package: {path.name}: {target}")
            elif not resolved.is_file():
                failures.append(f"missing reference: {path.name}: {target}")
    return failures


def main():
    failed = False
    for name in NAMES:
        errors = validate_package(ROOT / ".agents/skills" / name)
        print(f"{name}: " + ("; ".join(errors) if errors else "package checks passed"))
        failed |= bool(errors)
    print("Checks cover package structure and local links, not model behavior or live integrations.")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
