"""Freeze exact small source/report/receipt paths for the current quality batch."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
folders = [
    'experiments/real-source-contributions',
    'experiments/opal-headroom',
    'experiments/chip-stock-selectivity',
    'experiments/quality-september25/mineral-repair-review',
    'experiments/garnet-spatial-trace/ore102-delivery-1',
    'experiments/garnet-spatial-trace/rutile105-delivery-1',
    'experiments/garnet-spatial-trace/opal103-delivery-1',
    'outputs/quality-september25/ore-102',
    'outputs/quality-september25/rutile-105',
    'outputs/quality-september25/opal-103',
]
explicit = [
    'crates/strehl-core/src/pyramid.rs',
    'crates/strehl-cli/src/merge_cmd.rs',
    'crates/strehl-cli/src/image_out.rs',
    'experiments/full-stack-source-prior/adapter.rs',
    'experiments/garnet-spatial-trace/mineral-delivery-check.py',
    'experiments/chip-differential-blur/resampling-audit.md',
    'docs/proposals/2026-09-quality-path.md',
    'experiments/quality-september25/prepare-current-commit.py',
]
allowed = {'.py', '.rs', '.md', '.json', '.log', '.txt'}
paths = [ROOT / p for p in explicit]
for folder in folders:
    parent = ROOT / folder
    assert parent.is_dir(), parent
    paths += [p for p in parent.rglob('*') if p.is_file() and p.suffix.lower() in allowed]
paths = sorted(set(paths))
assert all(p.is_file() and p.is_relative_to(ROOT) for p in paths)
assert all(p.stat().st_size < 16 << 20 for p in paths)
relative = [p.relative_to(ROOT).as_posix() for p in paths]
(HERE / 'current-commit-files.txt').write_bytes(b''.join(p.encode()+b'\0' for p in relative))
(HERE / 'current-commit-files.json').write_text(json.dumps(dict(
    paths=relative, total_bytes=sum(p.stat().st_size for p in paths),
    scope='Exact owned source, report and receipt files; no images, executables, CFA arrays or original RAWs.'
), indent=2)+'\n')
print(json.dumps(dict(files=len(paths), bytes=sum(p.stat().st_size for p in paths))))
