"""Archive the independently verified complete real23 refusal population."""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid';out=h/'real-precise-1'
a=json.loads((h/'work/independent-real-precise-1-audit.json').read_bytes());assert a['status']=='PASS_SAVED_REAL_PRECISE_OUTCOME_AUDIT' and a['subject_complete'] is True
paths=[p for p in out.rglob('*') if p.is_file()];assert len(paths)==54 and sum(p.stat().st_size for p in paths)==5578203
assert all(p.suffix in ('.json','.log','.txt') for p in paths)
paths += [h/n for n in ('work/real-precise-1-outer.json','work/real-precise-1-console.txt','work/real-precise-1-exit.txt',
'work/independent-real-precise-1-audit.json','independent-real-precise-1-read.md',
'work/continuation-2026-09-07-real-precise-refused.md','work/archive-real-precise-outcome-1.py')]
paths += [root/'AGENTS.md',root/'docs/research/M193c-output-grid.md'];assert all(p.is_file() and p.resolve().is_relative_to(root) for p in paths)
(h/'work/archive-real-precise-outcome-1.nul').write_bytes(b'\0'.join(p.relative_to(root).as_posix().encode() for p in paths)+b'\0');print('Exact outcome paths:',len(paths))
