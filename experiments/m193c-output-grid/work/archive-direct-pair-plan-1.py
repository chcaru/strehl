"""Freeze only the reviewed direct-pair plan and its preparation metadata."""
from pathlib import Path
root=Path(__file__).resolve().parents[3]
h=root/'experiments/m193c-output-grid'
names=(
 'direct-pair-run.py','direct-pair-preregister.md','independent-direct-pair-source-review.md',
 'direct-pair-plan-1.json','work/prepare-direct-pair-plan-1.py','work/direct-pair-prior-work-1.json',
 'work/direct-pair-plan-1-review.md','work/archive-direct-pair-plan-1.py',
 'independent-sensor-white-coverage-1-read.md',
)
paths=[h/n for n in names]
assert all(p.is_file() for p in paths) and not (h/'direct-pair-1').exists()
(h/'work/archive-direct-pair-plan-1.nul').write_bytes(b'\0'.join(p.relative_to(root).as_posix().encode() for p in paths)+b'\0')
print('Nine exact reviewed source/metadata paths; no image payloads.')
