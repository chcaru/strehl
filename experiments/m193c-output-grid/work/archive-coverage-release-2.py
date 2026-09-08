"""Freeze the exact reviewed metadata preparation and coverage release package."""
from pathlib import Path
root=Path(__file__).resolve().parents[3]
h=root/'experiments/m193c-output-grid'
names=(
 'coverage-sensor-white-run.py', 'sensor-white-coverage-preregister.md',
 'independent-sensor-white-coverage-source-review.md',
 'work/prepare-sensor-white-coverage-release-2.py',
 'independent-sensor-white-coverage-preparation-2-source-review.md',
 'independent-sensor-white-coverage-release-2-review.md',
 'sensor-white-coverage-release-2.json',
 'work/sensor-white-coverage-release-2-preparation.json',
 'work/sensor-white-coverage-prior-work-2.json',
 'work/sensor-white-coverage-carry-2-basis.json',
 'work/sensor-white-coverage-preparation-2-console.txt',
 'work/sensor-white-coverage-preparation-2-exit.txt',
 'work/sensor-white-coverage-preparation-2-outer.json',
 'work/read-sensor-white-coverage-release-2.py',
 'work/independent-sensor-white-coverage-1-audit.py',
 'work/archive-coverage-release-2.py',
)
paths=[h/n for n in names]
extra=h/'independent-sensor-white-coverage-preparation-2-read.md'
if extra.is_file(): paths.append(extra)
paths+=list((h/'work/sensor-white-coverage-preparation-2-controls').iterdir())
assert all(p.is_file() and p.suffix in ('.py','.md','.json','.txt') for p in paths)
assert not (h/'sensor-white-coverage-1').exists()
relative=sorted(p.relative_to(root).as_posix() for p in paths)
assert len(relative)==len(set(relative))
(h/'work/archive-coverage-release-2.nul').write_bytes(b'\0'.join(x.encode() for x in relative)+b'\0')
print('Prepared '+str(len(relative))+' exact coverage source/metadata paths.')
