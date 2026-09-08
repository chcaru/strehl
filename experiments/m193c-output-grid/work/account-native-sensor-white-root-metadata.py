"""Observed root metadata against the previous 192-KiB reservation."""
import hashlib
import json
from pathlib import Path
here = Path(__file__).resolve().parents[1]
names = (
    'independent-native-sensor-white-release-1-review.md',
    'work/read-native-sensor-white-release-1.py',
    'work/prepare-native-sensor-white-archive-1.py',
    'work/archive-native-sensor-white-1.nul',
    'work/native-sensor-white-1-console.txt', 'work/native-sensor-white-1-exit.txt',
    'work/native-sensor-white-1-outer.json', 'work/native-sensor-white-1-checkpoint.json',
    'work/archive-native-sensor-white-outcome-1.py',
    'work/account-native-sensor-white-root-metadata.py',
)
rows = []
for name in names:
    raw = (here/name).read_bytes()
    rows.append(dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
actual = sum(row['bytes'] for row in rows)
value = dict(schema='m193c-root-metadata-reservation-read-v1',
    scope='Actual named root artifacts after camera-white native1. The separate next preparation charges independent audit, new method/review and positive administrative growth. No subject CPU or artifact refund.',
    reserved_bytes=196608, actual_named_bytes=actual,
    record_archive_and_checkpoint_growth_upper_bytes=16384, metadata_files=rows)
raw = (json.dumps(value, indent=2)+'\n').encode()
assert len(raw)<4096 and actual+16384 <196608
with (here/'work/native-sensor-white-1-root-metadata.json').open('xb') as stream:
    assert stream.write(raw)==len(raw)
print(json.dumps(dict(status='ROOT_METADATA_RESERVATION_FITS', actual_named_bytes=actual,
    record_archive_and_checkpoint_growth_upper_bytes=16384, reserved_bytes=196608)))
