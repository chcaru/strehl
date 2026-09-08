"""Archive actual native metadata only; all large TIFFs/RAW remain local."""
from pathlib import Path
root=Path(__file__).resolve().parents[3]
here=root/'experiments/m193c-output-grid'
out=here/'native-sensor-white-artifact-derivative-1'
images={'.arw','.raw','.tif','.tiff','.npy','.npz'}
paths=[p for p in out.rglob('*') if p.is_file() and p.suffix.lower() not in images]
assert len(paths)==163
paths += [here/name for name in (
 'independent-native-sensor-white-artifact-1-read.md',
 'work/independent-native-sensor-white-artifact-1-audit.py',
 'work/independent-native-sensor-white-artifact-1-audit.json',
 'work/native-sensor-white-artifact-1-console.txt',
 'work/native-sensor-white-artifact-1-exit.txt',
 'work/native-sensor-white-artifact-1-outer.json',
 'work/native-sensor-white-artifact-1-checkpoint.json',
 'work/native-sensor-white-artifact-1-root-metadata.json',
 'work/account-native-artifact-root-metadata.py',
 'work/archive-native-artifact-outcome-1.py',
 'work/continuation-2026-09-07-native-nine.md',
)]
paths += [root/name for name in ('AGENTS.md','docs/research/M193c-output-grid.md','docs/proposals/2026-09-sota-program.md')]
assert all(p.is_file() and p.suffix.lower() not in images for p in paths)
names=sorted({p.relative_to(root).as_posix() for p in paths})
(here/'work/archive-native-artifact-outcome-1.nul').write_bytes(b'\0'.join(x.encode() for x in names)+b'\0')
print(f'Prepared {len(names)} exact actual metadata/audit/report paths; no image payloads.')
