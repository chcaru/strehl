"""Freeze the reviewed private precise-upscale plan, without historical edits."""
from pathlib import Path
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid'
names=('precise-upscale-run.py','precise-upscale-preregister.md','independent-precise-upscale-source-review.md',
'work/prepare-precise-upscale-plan-1.py','work/independent-precise-upscale-plan-preparation-read.md',
'precise-upscale-plan-1.json','work/precise-upscale-prior-work-1.json',
'work/precise-upscale-preparation-1-console.txt','work/precise-upscale-preparation-1-exit.txt','work/precise-upscale-preparation-1-outer.json',
'work/precise-upscale-preparation-inventory-1.json','work/precise-upscale-plan-1-review.md','work/archive-precise-upscale-plan-1.py')
paths=[h/n for n in names];assert not(h/'precise-upscale-1').exists() and all(p.is_file() for p in paths)
(h/'work/archive-precise-upscale-plan-1.nul').write_bytes(b'\0'.join(p.relative_to(root).as_posix().encode() for p in paths)+b'\0')
print('Exact private release paths:',len(paths))
