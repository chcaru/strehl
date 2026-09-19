"""List only this task's small sources, receipts, reports and photographic views."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
roots=[ROOT/'experiments/full-context-placement',HERE]
allowed={'.py','.ps1','.rs','.md','.json','.log','.txt','.png','.jpg'}
paths=[ROOT/n for n in ('crates/strehl-cli/src/align_cmd.rs','crates/strehl-cli/src/merge_cmd.rs',
                        'experiments/native-direct-planes/implementation.rs','docs/proposals/2026-09-quality-path.md')]
for folder in roots:
    paths.extend(p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in allowed
                 and p.name not in ('commit-files.json','commit-files.txt') and p.stat().st_size < 3<<20)
paths=sorted(set(paths))
relative=[p.relative_to(ROOT).as_posix() for p in paths]
assert all(p.is_relative_to(ROOT) for p in paths)
kept=relative
(HERE/'commit-files.txt').write_bytes(b''.join(p.encode('utf-8')+b'\0' for p in kept))
(HERE/'commit-files.json').write_text(json.dumps(dict(paths=kept,
    total_bytes=sum((ROOT/p).stat().st_size for p in kept),scope='Exact owned files only; no binaries, full images, f32 or original-CFA patch arrays'),indent=2)+'\n')
print(json.dumps(dict(files=len(kept),bytes=sum((ROOT/p).stat().st_size for p in kept))))
