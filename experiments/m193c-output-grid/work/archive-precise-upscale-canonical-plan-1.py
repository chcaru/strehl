"""Freeze the reviewed canonical comparison repair only."""
from pathlib import Path
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid'
names=('precise-upscale-canonical-run.py','precise-upscale-canonical-preregister.md','independent-precise-upscale-canonical-source-review.md',
'work/prepare-precise-upscale-canonical-plan-1.py','work/independent-precise-upscale-canonical-plan-preparation-read.md',
'precise-upscale-canonical-plan-1.json','work/precise-upscale-canonical-prior-work-1.json',
'work/precise-upscale-canonical-preparation-1-console.txt','work/precise-upscale-canonical-preparation-1-exit.txt','work/precise-upscale-canonical-preparation-1-outer.json',
'work/precise-upscale-canonical-preparation-inventory-1.json','work/precise-upscale-canonical-plan-1-review.md','work/archive-precise-upscale-canonical-plan-1.py')
paths=[h/n for n in names];assert not(h/'precise-upscale-canonical-1').exists() and all(p.is_file() for p in paths)
(h/'work/archive-precise-upscale-canonical-plan-1.nul').write_bytes(b'\0'.join(p.relative_to(root).as_posix().encode() for p in paths)+b'\0')
print('Exact canonical release paths:',len(paths))
