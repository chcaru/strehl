"""Exact owned photometric sources and evidence, excluding binary payloads."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
paths = [ROOT/name for name in (
    'crates/strehl-cli/src/merge_cmd.rs',
    'docs/proposals/2026-09-quality-path.md',
    'experiments/quality-september25/marigold-placement-proposal.md',
    'experiments/quality-september25/stackmff-readiness.md',
    'experiments/quality-september25/prepare-photometric-commit.py',
)]
allowed = {'.py', '.rs', '.md', '.json', '.log', '.txt'}
for folder in ('native-photometric-normalization', 'marigold-local-placement'):
    paths += [p for p in (ROOT/'experiments'/folder).rglob('*')
              if p.is_file() and p.suffix.lower() in allowed]
paths = sorted(set(paths))
assert all(p.is_file() and p.is_relative_to(ROOT) and p.stat().st_size < 16 << 20 for p in paths)
relative = [p.relative_to(ROOT).as_posix() for p in paths]
(HERE/'photometric-commit-files.txt').write_bytes(b''.join(p.encode()+b'\0' for p in relative))
(HERE/'photometric-commit-files.json').write_text(json.dumps(dict(
    paths=relative, total_bytes=sum(p.stat().st_size for p in paths),
    scope='Owned photometric and marigold fit sources/evidence; no images, binaries or original RAW.'
), indent=2)+'\n')
print(json.dumps(dict(files=len(paths), bytes=sum(p.stat().st_size for p in paths))))
