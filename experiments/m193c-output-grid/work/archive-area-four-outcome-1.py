"""Archive only completed fixed AREA4 outcome and reviewed disposition."""
from pathlib import Path
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid'
paths=[p for p in (h/'area-four-1').rglob('*') if p.is_file()]
assert len(paths)==53 and sum(p.stat().st_size for p in paths)==3305129
assert all(p.suffix in ('.json','.log') for p in paths)
names=('work/area-four-1-outer.json','work/area-four-1-console.txt','work/area-four-1-exit.txt','work/independent-area-four-1-audit.json','independent-area-four-1-read.md','work/continuation-2026-09-08-area-four-refused.md','work/archive-area-four-outcome-1.py','work/independent-lightglue-arm-choice.md')
paths.extend(h/n for n in names);paths.extend(root/n for n in ('AGENTS.md','docs/research/M193c-output-grid.md'))
assert len(paths)==63 and len(set(paths))==63 and all(p.is_file() for p in paths)
(h/'work/archive-area-four-outcome-1.nul').write_bytes(b'\0'.join(p.relative_to(root).as_posix().encode() for p in sorted(paths))+b'\0')
print('Exact AREA4 outcome paths:',len(paths))
