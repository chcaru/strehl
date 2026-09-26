"""Exact small-source checkpoint; never includes staged vendor binaries."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
experiment = ROOT/'experiments/chip-upstream-reference'
paths = [p for p in experiment.rglob('*') if p.is_file()
         and p.suffix in {'.py', '.md', '.json', '.log'}
         and 'program-1' not in p.relative_to(experiment).parts]
paths += [ROOT/'docs/proposals/2026-09-quality-path.md', Path(__file__).resolve()]
paths = sorted(set(paths))
assert all(p.is_relative_to(ROOT) and p.stat().st_size < 8 << 20 for p in paths)
relative = [p.relative_to(ROOT).as_posix() for p in paths]
(HERE/'upstream-reference-commit-files.txt').write_bytes(b''.join(p.encode()+b'\0' for p in relative))
(HERE/'upstream-reference-commit-files.json').write_text(json.dumps(dict(
    paths=relative,total_bytes=sum(p.stat().st_size for p in paths)),indent=2)+'\n')
print(json.dumps(dict(files=len(paths),bytes=sum(p.stat().st_size for p in paths))))
