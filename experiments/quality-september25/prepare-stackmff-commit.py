"""Exact first-stage comparison checkpoint; external downloads/images excluded."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EXPERIMENT = ROOT/'experiments/stackmff-v4-evaluation'
receipts = EXPERIMENT/'fetch-receipts'
receipts.mkdir(exist_ok=True)
for source, destination in (('upstream-1/refusal.json', 'sandbox-refusal.json'),
                            ('upstream-1/started.json', 'sandbox-invocation.json'),
                            ('upstream-2/manifest.json', 'completed-manifest.json'),
                            ('upstream-2/started.json', 'completed-invocation.json')):
    shutil.copyfile(EXPERIMENT/source, receipts/destination)
paths = [p for p in EXPERIMENT.iterdir() if p.is_file() and p.suffix in ('.py', '.md')]
for folder in ('pilot-1', 'job-1', 'fetch-receipts'):
    paths += [p for p in (EXPERIMENT/folder).iterdir()
              if p.is_file() and p.suffix in ('.json', '.log')]
paths += [ROOT/p for p in ('docs/proposals/2026-09-quality-path.md',
    'experiments/quality-september25/prepare-stackmff-commit.py',
    'experiments/quality-september25/chip-planarity-triage.md',
    'experiments/chip-focus-front/decision.md')]
paths = sorted(set(paths))
assert all(p.is_file() and p.is_relative_to(ROOT) and p.stat().st_size < 4 << 20 for p in paths)
relative = [p.relative_to(ROOT).as_posix() for p in paths]
(HERE/'stackmff-commit-files.txt').write_bytes(b''.join(p.encode()+b'\0' for p in relative))
(HERE/'stackmff-commit-files.json').write_text(json.dumps(dict(paths=relative,
    total_bytes=sum(p.stat().st_size for p in paths)), indent=2)+'\n')
print(json.dumps(dict(files=len(paths), bytes=sum(p.stat().st_size for p in paths))))
