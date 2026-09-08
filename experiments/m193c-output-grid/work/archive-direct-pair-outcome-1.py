"""Archive the independently checked native direct-pair outcome; no RAW/TIFF."""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[3]
h=root/'experiments/m193c-output-grid'
out=h/'direct-pair-1'
result=json.loads((out/'result.json').read_bytes())
audit=json.loads((h/'work/independent-direct-pair-1-audit.json').read_bytes())
assert result['status']=='COMPLETE_DIRECT_PAIR_SUPPORT_ONLY'
assert audit['status']=='PASS_SAVED_DIRECT_PAIR_OUTCOME_AUDIT' and audit['subject_complete'] is True
paths=[p for p in out.rglob('*') if p.is_file()]
assert len(paths)==46 and sum(p.stat().st_size for p in paths)==1417587
assert all(p.suffix in ('.json','.py','.md','.log','.txt') for p in paths)
paths += [h/n for n in (
 'work/direct-pair-1-console.txt','work/direct-pair-1-exit.txt','work/direct-pair-1-outer.json',
 'work/independent-direct-pair-1-audit.py','work/independent-direct-pair-1-audit.json',
 'work/independent-direct-pair-1-inventory.json','independent-direct-pair-1-read.md',
 'work/direct-pair-coordinate-diagnosis.py','work/direct-pair-coordinate-diagnosis.json','work/direct-pair-coordinate-diagnosis.md',
 'work/direct-pair-coordinate-details.py','work/direct-pair-coordinate-details.json',
 'work/direct-pair-input-previews.png','work/direct-pair-input-previews.json',
 'work/direct-pair-fixed-site-previews.png','work/direct-pair-fixed-site-previews.json',
 'work/continuation-2026-09-07-direct-pairs.md','work/archive-direct-pair-outcome-1.py',
 'next-registration-diagnostic-decision.md',
)]
paths += [root/'AGENTS.md',root/'docs/research/M193c-output-grid.md']
assert all(p.is_file() and p.resolve().is_relative_to(root) for p in paths)
names=sorted(p.relative_to(root).as_posix() for p in paths)
assert len(names)==len(set(names))
(h/'work/archive-direct-pair-outcome-1.nul').write_bytes(b'\0'.join(p.encode() for p in names)+b'\0')
print('Exact saved-outcome paths:',len(names),'program file deliberately excluded')
