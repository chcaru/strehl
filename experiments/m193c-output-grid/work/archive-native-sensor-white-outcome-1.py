"""Exact actual white-reader success/controller refusal; no image payloads."""
from pathlib import Path
root = Path(__file__).resolve().parents[3]
here = root / 'experiments/m193c-output-grid'
paths = [p for p in (here/'native-sensor-white-derivative-1').rglob('*') if p.is_file()]
paths += [here/name for name in (
    'independent-native-sensor-white-1-read.md',
    'work/independent-native-sensor-white-1-audit.py',
    'work/native-sensor-white-1-console.txt', 'work/native-sensor-white-1-exit.txt',
    'work/native-sensor-white-1-outer.json', 'work/native-sensor-white-1-checkpoint.json',
    'work/native-sensor-white-1-root-metadata.json',
    'work/account-native-sensor-white-root-metadata.py',
    'work/archive-native-sensor-white-outcome-1.py',
)]
paths += [root/name for name in ('AGENTS.md', 'docs/research/M193c-output-grid.md',
                               'docs/proposals/2026-09-sota-program.md')]
assert all(p.is_file() and p.suffix.lower() not in ('.arw','.raw','.tif','.tiff','.npy') for p in paths)
names = sorted({p.relative_to(root).as_posix() for p in paths})
(here/'work/archive-native-sensor-white-outcome-1.nul').write_bytes(b'\0'.join(p.encode() for p in names)+b'\0')
print(f'Prepared {len(names)} exact actual-evidence/report paths; no image payloads.')
