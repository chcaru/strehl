"""List only this completed batch's small sources, reports and receipts."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
folders = [
    'experiments/alignment-sampling-control',
    'experiments/band-source-agreement',
    'experiments/garnet-spatial-trace/ore100-delivery-1',
    'outputs/quality-september25/ore-100',
]
explicit = [
    'crates/strehl-core/src/pyramid.rs',
    'crates/strehl-cli/src/merge_cmd.rs',
    'docs/proposals/2026-09-quality-path.md',
    'experiments/quality-september25/prepare-agreement-commit.py',
    'experiments/quality-september25/focusdeep-feasibility.md',
    'experiments/quality-september25/next-colour-evidence-brief.md',
    'experiments/chip-shared-source-observation/design.md',
    'experiments/chromatic-source-evidence/design.md',
    'experiments/quality-september25/mineral-repair-review/review-ore100.py',
    'experiments/quality-september25/mineral-repair-review/ore100-review.md',
    'experiments/quality-september25/mineral-repair-review/ore100-evidence.json',
]
allowed = {'.py', '.rs', '.md', '.json', '.log', '.txt'}
paths = [ROOT/p for p in explicit]
for folder in folders:
    parent = ROOT/folder
    assert parent.is_dir(), parent
    paths += [p for p in parent.rglob('*') if p.is_file() and p.suffix.lower() in allowed]
paths = sorted(set(paths))
assert all(p.is_file() and p.is_relative_to(ROOT) and p.stat().st_size < 16 << 20 for p in paths)
relative = [p.relative_to(ROOT).as_posix() for p in paths]
(HERE/'agreement-commit-files.txt').write_bytes(b''.join(p.encode()+b'\0' for p in relative))
(HERE/'agreement-commit-files.json').write_text(json.dumps(dict(
    paths=relative, total_bytes=sum(p.stat().st_size for p in paths),
    scope='Exact owned sources/reports/receipts only; no images, executables, CFA arrays or original RAW.'
), indent=2)+'\n')
print(json.dumps(dict(files=len(paths), bytes=sum(p.stat().st_size for p in paths))))
