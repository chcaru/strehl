"""Archive actual refused sensor-native1 and reviewed, unexecuted coverage source."""
from pathlib import Path
root = Path(__file__).resolve().parents[3]
here = root / 'experiments/m193c-output-grid'
paths = [p for p in (here/'native-sensor-derivative-1').rglob('*') if p.is_file()]
paths += [here/name for name in (
    'independent-native-sensor-1-read.md', 'work/independent-native-sensor-1-audit.py',
    'work/native-sensor-1-console.txt', 'work/native-sensor-1-exit.txt',
    'work/native-sensor-1-outer.json', 'work/native-sensor-1-checkpoint.json',
    'work/native-sensor-1-root-metadata.json',
    'work/native-sensor-1-root-metadata.first.json',
    'work/account-native-sensor-root-metadata.py',
    'coverage-sensor-run.py', 'sensor-coverage-preregister.md',
    'independent-sensor-coverage-source-review.md', 'work/archive-native-sensor-outcome-1.py',
)]
paths += [root/name for name in ('AGENTS.md','docs/research/M193c-output-grid.md',
    'docs/proposals/2026-09-sota-program.md')]
assert all(p.is_file() and p.suffix.lower() not in ('.arw','.raw','.tif','.tiff') for p in paths)
names = sorted({p.relative_to(root).as_posix() for p in paths})
(here/'work/archive-native-sensor-outcome-1.nul').write_bytes(b'\0'.join(p.encode() for p in names)+b'\0')
print(f'Prepared {len(names)} exact refused-evidence and reviewed-source paths; no image payloads.')
