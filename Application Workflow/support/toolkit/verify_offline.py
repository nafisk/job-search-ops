"""Copy the exact shared allowlist into a temporary workspace and run local tests."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent


def copy_package(destination):
    """Temporary verification copy, not a distributable or installer."""
    entries = (ROOT / "SHAREABLE_FILES.txt").read_text(encoding="utf-8").splitlines()
    if not entries or len(entries) != len(set(entries)):
        raise ValueError("allowlist is empty or contains duplicate entries")
    for entry in entries:
        path = Path(entry)
        if path.is_absolute() or ".." in path.parts or not entry or path.as_posix() != entry:
            raise ValueError("allowlist contains an unsafe or noncanonical path")
    inventory = {str(path.relative_to(ROOT)) for path in ROOT.rglob("*") if path.is_file()
                 and not (path.parent.name == "__pycache__" and path.suffix == ".pyc")}
    if inventory != set(entries) or any(path.is_symlink() for path in ROOT.rglob("*")):
        raise ValueError("package inventory differs from allowlist or contains a symlink")
    destination = Path(destination).resolve()
    if destination.exists() or destination.is_relative_to(ROOT) or ROOT.is_relative_to(destination):
        raise ValueError("verification destination must be a new separate directory")
    destination.mkdir(parents=True)
    for entry in entries:
        target = destination / entry
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / entry, target)
    return destination


def main():
    try:
        with tempfile.TemporaryDirectory(prefix="job-toolkit-check-") as temporary:
            package = copy_package(Path(temporary) / "toolkit")
            print("Testing an allowlisted temporary copy with fictional data only.", flush=True)
            return subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
                                  cwd=package, check=False).returncode
    except (OSError, ValueError) as error:
        print(f"Offline verification stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
