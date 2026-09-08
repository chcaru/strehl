"""Freeze the reviewed fixed real precise diagnostic only."""
from pathlib import Path
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid'
names=('real-precise-run.py','real-precise-preregister.md','independent-real-precise-source-review.md',
'work/prepare-real-precise-plan-1.py','work/independent-real-precise-plan-preparation-read.md',
'real-precise-plan-1.json','work/real-precise-prior-work-1.json',
'work/real-precise-preparation-1-console.txt','work/real-precise-preparation-1-exit.txt','work/real-precise-preparation-1-outer.json',
'work/real-precise-preparation-inventory-1.json','work/real-precise-plan-1-review.md','work/archive-real-precise-plan-1.py','work/precise-upscale-conditional-next.md','work/independent-real-precise-1-audit.py')
paths=[h/n for n in names];assert not(h/'real-precise-1').exists() and all(p.is_file() for p in paths)
(h/'work/archive-real-precise-plan-1.nul').write_bytes(b'\0'.join(p.relative_to(root).as_posix().encode() for p in paths)+b'\0')
print('Exact canonical release paths:',len(paths))
