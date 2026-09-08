"""Freeze exactly the reviewed fixed AREA4 diagnostic release."""
from pathlib import Path
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid'
names=('area-four-run.py', 'area-four-prototype.py', 'area-four-preregister.md', 'independent-area-four-source-review.md', 'work/prepare-area-four-plan-1.py', 'work/independent-area-four-plan-preparation-read.md', 'area-four-plan-1.json', 'work/area-four-prior-work-1.json', 'work/area-four-preparation-1-console.txt', 'work/area-four-preparation-1-exit.txt', 'work/area-four-preparation-1-outer.json', 'work/area-four-preparation-inventory-1.json', 'work/area-four-plan-1-review.md', 'work/archive-area-four-plan-1.py', 'work/independent-area-four-1-audit.py', 'work/registration-2025-2026-followup.md')
paths=[h/n for n in names];assert not(h/'area-four-1').exists() and all(p.is_file() for p in paths)
(h/'work/archive-area-four-plan-1.nul').write_bytes(b'\0'.join(p.relative_to(root).as_posix().encode() for p in paths)+b'\0')
print('Exact AREA4 release paths:',len(paths))
