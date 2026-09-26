"""Enumerate exact owned small files; never include photographic buffers or binaries."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
allowed = {'.py', '.rs', '.md', '.json', '.log', '.txt'}
paths = [ROOT/name for name in (
    'crates/strehl-cli/src/merge_cmd.rs',
    'docs/proposals/2026-09-quality-path.md',
    'experiments/quality-september25/production-audit.md',
    'experiments/quality-september25/next-consistent-reconstruction.md',
    'experiments/quality-september25/next-after-reconstruction.md',
    'experiments/quality-september25/prepare-reconstruction-commit.py',
)]
paths += [p for p in (ROOT/'experiments/consistent-reconstruction').rglob('*')
          if p.is_file() and p.suffix.lower() in allowed]
paths = sorted(set(paths))
assert all(p.is_file() and p.is_relative_to(ROOT) and p.stat().st_size < 16 << 20 for p in paths)
relative = [p.relative_to(ROOT).as_posix() for p in paths]
(HERE/'reconstruction-commit-files.txt').write_bytes(b''.join(p.encode()+b'\0' for p in relative))
(HERE/'reconstruction-commit-files.json').write_text(json.dumps(dict(
    paths=relative, total_bytes=sum(p.stat().st_size for p in paths),
    scope='Owned reconstruction source, controls, reports and execution receipts; no images, executable or CFA buffers.'
), indent=2)+'\n')
print(json.dumps(dict(files=len(paths), bytes=sum(p.stat().st_size for p in paths))))
