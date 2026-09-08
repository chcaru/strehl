"""Archive the independently verified failed rotation control; no image payloads."""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid';out=h/'factor-eight-1'
r=json.loads((out/'result.json').read_bytes());a=json.loads((h/'work/independent-factor-eight-1-audit.json').read_bytes())
assert r['status']=='REFUSED' and a['status']=='PASS_SAVED_FACTOR_EIGHT_OUTCOME_AUDIT' and a['subject_complete'] is False
paths=[p for p in out.rglob('*') if p.is_file()];assert len(paths)==17 and sum(p.stat().st_size for p in paths)==728511
assert all(p.suffix in ('.json','.log','.txt') for p in paths)
paths += [h/n for n in ('work/factor-eight-1-outer.json','work/factor-eight-1-console.txt','work/factor-eight-1-exit.txt',
'work/independent-factor-eight-1-audit.py','work/independent-factor-eight-1-audit.json','independent-factor-eight-1-read.md',
'work/continuation-2026-09-07-factor-eight.md','work/archive-factor-eight-outcome-1.py')]
paths += [root/'AGENTS.md',root/'docs/research/M193c-output-grid.md']
assert all(p.is_file() and p.resolve().is_relative_to(root) for p in paths)
(h/'work/archive-factor-eight-outcome-1.nul').write_bytes(b'\0'.join(p.relative_to(root).as_posix().encode() for p in paths)+b'\0')
print('Exact outcome paths:',len(paths),'unrelated program title/file excluded')
