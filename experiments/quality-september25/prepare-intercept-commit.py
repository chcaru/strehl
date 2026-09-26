"""Checkpoint fixed intercept and gradient-target outcomes, excluding image data."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
suffixes = {'.md', '.rs', '.py', '.json', '.log', '.toml', '.lock'}
paths = []
for folder in ('chip-focus-intercept', 'source-gradient-target'):
    paths.extend(p for p in (ROOT/'experiments'/folder).rglob('*')
                 if p.is_file() and p.suffix in suffixes)
paths.extend(ROOT/p for p in (
    'crates/strehl-cli/src/merge_cmd.rs',
    'docs/proposals/2026-09-quality-path.md',
    'experiments/quality-september25/intercept-next-discriminator.md',
    'experiments/quality-september25/prepare-intercept-commit.py',
))
paths = sorted(set(paths))
assert all(p.is_relative_to(ROOT) and p.stat().st_size < 8 << 20 for p in paths)
relative = [p.relative_to(ROOT).as_posix() for p in paths]
(HERE/'intercept-commit-files.txt').write_bytes(b''.join(p.encode()+b'\0' for p in relative))
(HERE/'intercept-commit-files.json').write_text(json.dumps(dict(
    paths=relative, total_bytes=sum(p.stat().st_size for p in paths)), indent=2)+'\n')
print(json.dumps(dict(files=len(paths), bytes=sum(p.stat().st_size for p in paths))))
