"""Freeze only the exact reviewed artifact-parent source/release package."""
from pathlib import Path
root=Path(__file__).resolve().parents[3]
here=root/'experiments/m193c-output-grid'
names=(
 'native-sensor-white-artifact-run.py','artifact-parent-preregister.md',
 'independent-artifact-native-parent-source-review.md',
 'independent-native-sensor-white-artifact-preparation-source-review.md',
 'independent-native-sensor-white-artifact-release-1-review.md',
 'native-sensor-white-artifact-derivative-release-1.json',
 'work/prepare-native-sensor-white-artifact-release-1.py',
 'work/native-sensor-white-artifact-release-1-preparation.json',
 'work/read-native-sensor-white-artifact-release-1.py',
 'work/prepare-native-sensor-white-artifact-archive-1.py',
)
paths=[here/name for name in names]
assert all(p.is_file() and p.suffix in ('.py','.md','.json') for p in paths)
relative=sorted(p.relative_to(root).as_posix() for p in paths)
assert len(relative)==len(set(relative))==10
(here/'work/archive-native-sensor-white-artifact-1.nul').write_bytes(b'\0'.join(x.encode() for x in relative)+b'\0')
print('Prepared10 exact reviewed artifact-parent source/release paths.')
