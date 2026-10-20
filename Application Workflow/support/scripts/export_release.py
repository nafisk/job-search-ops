"""Create a complete, reviewed ZIP. Never export Git, credentials or private state."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

import verify_release

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from job_search_ops.config import filesystem_contains


def export(destination):
    destination = Path(destination).expanduser().absolute()
    if destination.suffix != '.zip' or destination.exists():
        raise ValueError('choose a new .zip file outside the repository')
    if any(path.is_symlink() for path in (destination, *destination.parents)):
        raise ValueError('export path must not contain symlinks')
    if filesystem_contains(verify_release.REPO_ROOT, destination):
        raise ValueError('save the export outside the repository')
    if verify_release.main():
        raise ValueError('release validation failed; no export created')
    paths = verify_release.files()
    captured = {p.relative_to(verify_release.REPO_ROOT).as_posix(): p.read_bytes() for p in paths}
    with tempfile.TemporaryDirectory(prefix='job-search-release-') as temporary:
        archive = Path(temporary) / 'release.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as out:
            for name, data in sorted(captured.items()):
                info = zipfile.ZipInfo('job-search-ops/' + name, (2026, 1, 1, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                out.writestr(info, data)
        unpacked = Path(temporary) / 'extracted'
        with zipfile.ZipFile(archive) as src:
            src.extractall(unpacked)
        script = unpacked / 'job-search-ops/Application Workflow/support/scripts/verify_release.py'
        subprocess.run([sys.executable, '-B', str(script)], check=True)
        # Refuse a source that changed while the export was being prepared.
        if verify_release.files() != paths or any(p.read_bytes() != captured[p.relative_to(verify_release.REPO_ROOT).as_posix()] for p in paths):
            raise ValueError('source changed during export; review and retry')
        data = archive.read_bytes()
        with destination.open('xb') as out:
            out.write(data)
    return {'archive': str(destination), 'sha256': hashlib.sha256(data).hexdigest(),
            'files': len(captured), 'source': 'reviewed working tree; not a Git commit',
            'validation': 'exact exported copy passed inventory, links, privacy and workbook checks'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination')
    args = parser.parse_args()
    try:
        print(json.dumps(export(args.destination), indent=2))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
