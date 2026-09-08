"""Exact source/metadata freeze only; large image payloads excluded."""
from pathlib import Path
root = Path(__file__).resolve().parents[3]
here = root / 'experiments/m193c-output-grid'
names = [
    'native-sensor-derivative-run.py', 'independent-sensor-derivative-read.py',
    'sensor-domain-reader-preregister.md', 'independent-sensor-domain-source-review.md',
    'independent-sensor-native-parent-source-review.md',
    'independent-native-sensor-preparation-source-review.md',
    'independent-native-sensor-release-1-review.md', 'native-sensor-derivative-release-1.json',
    'work/prepare-native-sensor-release-1.py', 'work/native-sensor-release-1-preparation.json',
    'work/read-native-sensor-release-1.py', 'work/prepare-native-sensor-archive-1.py',
]
paths = [here / name for name in names]
paths.append(root / 'docs/proposals/2026-09-sota-program.md')
assert all(p.is_file() and p.suffix.lower() not in ('.arw','.tif','.tiff') for p in paths)
relative = sorted(p.relative_to(root).as_posix() for p in paths)
assert len(relative) == len(set(relative)) == 13
(here/'work/archive-native-sensor-1.nul').write_bytes(b'\0'.join(p.encode() for p in relative)+b'\0')
print('Prepared 13 exact source and metadata paths; no payload files.')
