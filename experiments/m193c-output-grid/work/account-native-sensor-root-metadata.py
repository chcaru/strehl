"""Root artifact inventory only; the first null-sum PowerShell draft is retained."""
import hashlib
import json
from pathlib import Path
here = Path(__file__).resolve().parents[1]
names = ['independent-native-sensor-release-1-review.md',
    'work/read-native-sensor-release-1.py','work/prepare-native-sensor-archive-1.py',
    'work/archive-native-sensor-1.nul','work/native-sensor-1-console.txt',
    'work/native-sensor-1-exit.txt','work/native-sensor-1-outer.json',
    'work/native-sensor-1-checkpoint.json','work/archive-native-sensor-outcome-1.py',
    'work/archive-native-sensor-outcome-1.nul','work/continuation-2026-09-07-domain.md',
    'work/native-sensor-1-root-metadata.first.json','work/account-native-sensor-root-metadata.py']
rows = []
for name in names:
    raw = (here/name).read_bytes()
    rows.append(dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
actual = sum(row['bytes'] for row in rows)
assert type(actual) is int and actual > 0
value = dict(schema='m193c-root-metadata-reservation-read-v1',
    scope='Observed root manifest review, launch, archive and checkpoint files at this audit instant; later independent audit and program/docs/coverage sources are explicitly carried by the successor preparation.',
    first_draft='PowerShell Measure-Object over ordered dictionaries produced null; that untrusted draft is retained. This independent explicit byte sum replaces it. No subject, carry or acceptance result changed.',
    reserved_bytes=262144, actual_named_bytes=actual, record_and_archive_growth_upper_bytes=8192,
    metadata_files=rows)
raw = (json.dumps(value, indent=2)+'\n').encode()
assert len(raw) < 8192 and actual+8192 < 262144
with (here/'work/native-sensor-1-root-metadata.json').open('xb') as stream:
    assert stream.write(raw) == len(raw)
print(json.dumps(dict(status='ROOT_METADATA_RESERVATION_FITS', actual_named_bytes=actual,
    record_and_archive_growth_upper_bytes=8192, reserved_bytes=262144)))
