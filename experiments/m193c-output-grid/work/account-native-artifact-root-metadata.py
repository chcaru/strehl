"""Actual independent-audit/root metadata against the native 192-KiB allowance."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[3]
here=root/'experiments/m193c-output-grid'
names=(
 'independent-native-sensor-white-artifact-release-1-review.md',
 'work/read-native-sensor-white-artifact-release-1.py',
 'work/prepare-native-sensor-white-artifact-archive-1.py',
 'work/archive-native-sensor-white-artifact-1.nul',
 'work/native-sensor-white-artifact-1-console.txt',
 'work/native-sensor-white-artifact-1-exit.txt',
 'work/native-sensor-white-artifact-1-outer.json',
 'work/native-sensor-white-artifact-1-checkpoint.json',
 'work/independent-native-sensor-white-artifact-1-audit.py',
 'work/independent-native-sensor-white-artifact-1-audit.json',
 'independent-native-sensor-white-artifact-1-read.md',
 'work/continuation-2026-09-07-native-nine.md',
 'work/archive-native-artifact-outcome-1.py',
 'work/account-native-artifact-root-metadata.py',
)
rows=[]
for name in names:
 p=here/name;b=p.read_bytes()
 rows.append(dict(path=p.relative_to(root).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
prep=json.loads((here/'work/native-sensor-white-artifact-release-1-preparation.json').read_bytes())
admins=[]
for v in prep['administrative_files']:
 base=v['current'];b=(root/base['path']).read_bytes()
 admins.append(dict(path=base['path'],baseline=base,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),charged_growth_bytes=max(0,len(b)-base['bytes'])))
actual=sum(v['bytes'] for v in rows)+sum(v['charged_growth_bytes'] for v in admins)
value=dict(schema='m193c-root-metadata-reservation-read-v1',reserved_bytes=196608,
 actual_named_and_growth_bytes=actual,record_archive_checkpoint_growth_upper_bytes=32768,
 metadata_files=rows,administrative_files=admins,
 scope='Actual independent audit source/Markdown/structured JSON and root metadata, with positive live-document growth. Remaining reservation covers this record, exact archive NUL and later checkpoint updates. New coverage preparation/source/carry is separately covered by its two-MiB allowance. No refund or exact write-I/O claim.')
raw=(json.dumps(value,indent=2)+'\n').encode()
assert len(raw)<16384 and actual+32768<196608
with (here/'work/native-sensor-white-artifact-1-root-metadata.json').open('xb') as s:assert s.write(raw)==len(raw)
print(json.dumps(dict(status='ROOT_METADATA_RESERVATION_FITS',actual_named_and_growth_bytes=actual,remaining_growth_upper_bytes=32768,reserved_bytes=196608)))
