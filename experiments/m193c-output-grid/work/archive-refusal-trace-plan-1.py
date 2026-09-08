"""Freeze only the reviewed saved-correspondence refusal trace."""
from pathlib import Path
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid'
names=('refusal-trace-run.py', 'work/real-precise-refusal-diagnostic-preregister.md', 'independent-refusal-trace-source-review.md', 'work/prepare-refusal-trace-plan-1.py', 'work/independent-refusal-trace-plan-preparation-read.md', 'refusal-trace-plan-1.json', 'work/refusal-trace-prior-work-1.json', 'work/refusal-trace-preparation-1-console.txt', 'work/refusal-trace-preparation-1-exit.txt', 'work/refusal-trace-preparation-1-outer.json', 'work/refusal-trace-preparation-inventory-1.json', 'work/refusal-trace-plan-1-review.md', 'work/archive-refusal-trace-plan-1.py', 'work/independent-refusal-trace-1-audit.py')
paths=[h/n for n in names];assert not(h/'refusal-trace-1').exists() and all(p.is_file() for p in paths)
(h/'work/archive-refusal-trace-plan-1.nul').write_bytes(b'\0'.join(p.relative_to(root).as_posix().encode() for p in paths)+b'\0')
print('Exact saved-trace release paths:',len(paths))
