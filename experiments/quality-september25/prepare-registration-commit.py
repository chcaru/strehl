"""Exact checkpoint of the two fixed learned-registration experiments."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
paths = []
for name in ('marigold-raft-translation', 'marigold-composite-registration'):
    paths.extend(p for p in (ROOT/'experiments'/name).rglob('*')
                 if p.is_file() and p.suffix in {'.py', '.md', '.json', '.log'})
paths.extend((ROOT/'docs/proposals/2026-09-quality-path.md', Path(__file__).resolve()))
paths = sorted(set(paths))
assert all(p.is_relative_to(ROOT) and p.stat().st_size < 8 << 20 for p in paths)
relative = [p.relative_to(ROOT).as_posix() for p in paths]
(HERE/'registration-commit-files.txt').write_bytes(b''.join(p.encode()+b'\0' for p in relative))
(HERE/'registration-commit-files.json').write_text(json.dumps(dict(
    paths=relative, total_bytes=sum(p.stat().st_size for p in paths)), indent=2)+'\n')
print(json.dumps(dict(files=len(paths), bytes=sum(p.stat().st_size for p in paths))))
