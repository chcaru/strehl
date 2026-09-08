"""Archive saved registration refusal and exact metadata; keep TIFF payloads local."""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[3]
h=root/'experiments/m193c-output-grid'
out=h/'sensor-white-coverage-1'
result=json.loads((out/'result.json').read_bytes())
audit=json.loads((h/'work/independent-sensor-white-coverage-1-audit.json').read_bytes())
assert result['status']=='REFUSED' and audit['subject_complete'] is False
assert audit['status']=='PASS_SAVED_COVERAGE_OUTCOME_AUDIT'
paths=[p for p in out.rglob('*') if p.is_file() and p.suffix in ('.json','.py','.log','.txt','.md')]
paths += [h/n for n in (
 'work/sensor-white-coverage-1-console.txt','work/sensor-white-coverage-1-exit.txt','work/sensor-white-coverage-1-outer.json',
 'work/independent-sensor-white-coverage-1-audit.py','work/independent-sensor-white-coverage-1-audit.json',
 'independent-sensor-white-coverage-1-read.md','work/archive-coverage-outcome-1.py',
 'work/registration-refusal-branch-proposal.md',
)]
paths += [root/n for n in ('AGENTS.md','docs/research/M193c-output-grid.md','docs/proposals/2026-09-sota-program.md')]
assert all(p.is_file() and p.resolve().is_relative_to(root) for p in paths)
names=sorted(p.relative_to(root).as_posix() for p in paths)
assert len(names)==len(set(names))
(h/'work/archive-coverage-outcome-1.nul').write_bytes(b'\0'.join(p.encode() for p in names)+b'\0')
print('Exact saved-outcome paths:',len(names))
