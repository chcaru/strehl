"""Exact checkpoint of completed source diagnosis and marigold reference."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
paths = []
for name in ('chip-source-support', 'marigold-comparator'):
    for p in (ROOT/'experiments'/name).rglob('*'):
        if not p.is_file() or p.suffix not in {'.py', '.md', '.json', '.log', '.txt'}:
            continue
        if p.parent.name == 'developed' and p.name.startswith('frame-'):
            continue  # Aggregated final receipt retains every per-frame record.
        paths.append(p)
paths.extend(ROOT/p for p in (
    'crates/strehl-cli/examples/marigold-batch-develop.rs',
    'docs/proposals/2026-09-quality-path.md',
    'experiments/quality-september25/marigold-production-discriminator.md',
    'experiments/quality-september25/marigold-comparator-feasibility.md',
    'experiments/quality-september25/chip-projective-triage.md',
    'experiments/quality-september25/dense-registration-feasibility.md',
    'experiments/quality-september25/prepare-comparator-commit.py',
))
paths = sorted(set(paths))
assert all(p.is_relative_to(ROOT) and p.stat().st_size < 8 << 20 for p in paths)
relative = [p.relative_to(ROOT).as_posix() for p in paths]
(HERE/'comparator-commit-files.txt').write_bytes(b''.join(p.encode()+b'\0' for p in relative))
(HERE/'comparator-commit-files.json').write_text(json.dumps(dict(
    paths=relative, total_bytes=sum(p.stat().st_size for p in paths)), indent=2)+'\n')
print(json.dumps(dict(files=len(paths), bytes=sum(p.stat().st_size for p in paths))))
