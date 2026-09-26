"""List this batch's exact small sources, reports and immutable receipts."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
folders = [
    'experiments/chip-shared-source-observation',
    'experiments/chromatic-source-evidence',
]
explicit = [
    'crates/strehl-core/src/pyramid.rs',
    'crates/strehl-cli/src/merge_cmd.rs',
    'docs/proposals/2026-09-quality-path.md',
    'experiments/quality-september25/prepare-source-evidence-commit.py',
]
allowed = {'.py', '.rs', '.md', '.json', '.log', '.txt'}
paths = [ROOT / p for p in explicit]
for folder in folders:
    parent = ROOT / folder
    assert parent.is_dir(), parent
    paths += [p for p in parent.rglob('*') if p.is_file() and p.suffix.lower() in allowed]
paths = sorted(set(paths))
assert all(p.is_file() and p.is_relative_to(ROOT) and p.stat().st_size < 16 << 20 for p in paths)
relative = [p.relative_to(ROOT).as_posix() for p in paths]
(HERE / 'source-evidence-commit-files.txt').write_bytes(b''.join(p.encode() + b'\0' for p in relative))
(HERE / 'source-evidence-commit-files.json').write_text(json.dumps(dict(
    paths=relative, total_bytes=sum(p.stat().st_size for p in paths),
    scope='Exact owned sources/reports/receipts; excludes images, executables, CFA arrays and original RAW.'
), indent=2) + '\n')
print(json.dumps(dict(files=len(paths), bytes=sum(p.stat().st_size for p in paths))))
