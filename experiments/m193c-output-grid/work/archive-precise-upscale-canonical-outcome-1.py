"""Archive the independently verified private canonical experiment."""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid';out=h/'precise-upscale-canonical-1'
a=json.loads((h/'work/independent-precise-upscale-canonical-1-audit.json').read_bytes());assert a['status']=='PASS_SAVED_PRECISE_UPSCALE_CANONICAL_OUTCOME_AUDIT' and a['subject_complete'] is True
paths=[p for p in out.rglob('*') if p.is_file()];assert len(paths)==18 and sum(p.stat().st_size for p in paths)==1164283
assert all(p.suffix in ('.json','.log','.txt') for p in paths)
paths += [h/n for n in ('work/precise-upscale-canonical-1-outer.json','work/precise-upscale-canonical-1-console.txt','work/precise-upscale-canonical-1-exit.txt',
'work/independent-precise-upscale-canonical-1-audit.py','work/independent-precise-upscale-canonical-1-audit.json','independent-precise-upscale-canonical-1-read.md',
'work/continuation-2026-09-07-canonical-private-complete.md','work/archive-precise-upscale-canonical-outcome-1.py')]
paths += [root/'AGENTS.md',root/'docs/research/M193c-output-grid.md'];assert all(p.is_file() and p.resolve().is_relative_to(root) for p in paths)
(h/'work/archive-precise-upscale-canonical-outcome-1.nul').write_bytes(b'\0'.join(p.relative_to(root).as_posix().encode() for p in paths)+b'\0');print('Exact outcome paths:',len(paths))
