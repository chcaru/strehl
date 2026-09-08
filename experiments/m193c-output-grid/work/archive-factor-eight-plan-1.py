"""Freeze the factor-eight source release and independent coordinate review."""
from pathlib import Path
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid'
names=('factor-eight-prototype.py','factor-eight-proposal.md','factor-eight-run.py','factor-eight-preregister.md',
'independent-factor-eight-source-review.md','independent-factor-eight-runner-review.md',
'work/independent-factor-eight-plan-preparation-read.md','work/prepare-factor-eight-plan-1.py',
'factor-eight-plan-1.json','work/factor-eight-prior-work-1.json',
'work/factor-eight-preparation-1-console.txt','work/factor-eight-preparation-1-exit.txt','work/factor-eight-preparation-1-outer.json',
'work/factor-eight-preparation-inventory-1.json','work/factor-eight-plan-1-review.md',
'work/factor-eight-localization-hypothesis.md','work/independent-coordinate-sites-1.py','work/independent-coordinate-sites-1.json',
'work/independent-coordinate-sites-1.md','work/archive-factor-eight-plan-1.py')
paths=[h/n for n in names]+[root/'docs/research/M193c-output-grid.md']
assert not(h/'factor-eight-1').exists() and all(p.is_file() for p in paths)
(h/'work/archive-factor-eight-plan-1.nul').write_bytes(b'\0'.join(p.relative_to(root).as_posix().encode() for p in paths)+b'\0')
print('Exact factor-eight release paths:',len(paths))
