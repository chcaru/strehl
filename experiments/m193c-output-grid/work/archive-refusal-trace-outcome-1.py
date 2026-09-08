"""Archive only the actual saved-refusal trace outcome and reviewed conclusions."""
from pathlib import Path
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid'
paths=list((h/'refusal-trace-1').rglob('*'));paths=[p for p in paths if p.is_file()]
assert len(paths)==31 and sum(p.stat().st_size for p in paths)==1922639
assert all(p.suffix in ('.json','.log') for p in paths)
names=('work/refusal-trace-1-outer.json','work/refusal-trace-1-console.txt','work/refusal-trace-1-exit.txt',
'work/independent-refusal-trace-1-audit.json','independent-refusal-trace-1-read.md',
'work/continuation-2026-09-08-refusal-trace-complete.md','work/registration-primary-alternatives.md','work/archive-refusal-trace-outcome-1.py')
paths.extend(h/n for n in names);paths.extend(root/n for n in ('AGENTS.md','docs/research/M193c-output-grid.md'))
assert len(paths)==41 and len(set(paths))==41 and all(p.is_file() for p in paths)
(h/'work/archive-refusal-trace-outcome-1.nul').write_bytes(b'\0'.join(p.relative_to(root).as_posix().encode() for p in sorted(paths))+b'\0')
print('Exact saved-trace outcome paths:',len(paths))
