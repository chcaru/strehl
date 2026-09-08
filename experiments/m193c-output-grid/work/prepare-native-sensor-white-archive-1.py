"""Exact camera-white source/release freeze; prepared coverage remains unexecuted."""
from pathlib import Path
root = Path(__file__).resolve().parents[3]
here = root / 'experiments/m193c-output-grid'
names = [
    'native-sensor-white-derivative-run.py','independent-sensor-white-derivative-read.py',
    'sensor-white-reader-preregister.md','independent-sensor-white-source-review.md',
    'independent-sensor-white-native-parent-source-review.md',
    'independent-native-sensor-white-preparation-source-review.md',
    'independent-native-sensor-white-release-1-review.md',
    'native-sensor-white-derivative-release-1.json',
    'work/prepare-native-sensor-white-release-1.py',
    'work/native-sensor-white-release-1-preparation.json',
    'work/read-native-sensor-white-release-1.py',
    'work/prepare-native-sensor-white-archive-1.py',
    'coverage-sensor-white-run.py','sensor-white-coverage-preregister.md',
    'independent-sensor-white-coverage-source-review.md',
]
paths = [here/name for name in names]
assert all(p.is_file() and p.suffix.lower() not in ('.arw','.raw','.tif','.tiff') for p in paths)
relative = sorted(p.relative_to(root).as_posix() for p in paths)
assert len(relative) == len(set(relative)) == 15
(here/'work/archive-native-sensor-white-1.nul').write_bytes(b'\0'.join(p.encode() for p in relative)+b'\0')
print('Prepared15 exact reviewed source/metadata paths; no image payloads.')
