"""Freeze refused metadata preparation and its actual root evidence only."""
from pathlib import Path
root=Path(__file__).resolve().parents[3];h=root/'experiments/m193c-output-grid'
names=(
 'work/prepare-sensor-white-coverage-release-1.py',
 'independent-sensor-white-coverage-preparation-source-review.md',
 'coverage-preparation-1-refusal.md',
 'work/sensor-white-coverage-prior-work-1.json',
 'work/sensor-white-coverage-carry-1-basis.json',
 'work/sensor-white-coverage-preparation-1-console.txt',
 'work/sensor-white-coverage-preparation-1-exit.txt',
 'work/sensor-white-coverage-preparation-1-outer.json',
 'work/read-sensor-white-coverage-release-1.py',
 'work/archive-coverage-preparation-1.py',
)
paths=[h/n for n in names];assert all(p.is_file() for p in paths)
assert not (h/'sensor-white-coverage-release-1.json').exists()
assert not (h/'work/sensor-white-coverage-release-1-preparation.json').exists()
assert not (h/'sensor-white-coverage-1').exists()
(h/'work/archive-coverage-preparation-1.nul').write_bytes(b'\0'.join(p.relative_to(root).as_posix().encode() for p in paths)+b'\0')
print('Prepared10 exact refused-preparation source/metadata paths; no registration or image artifacts.')
