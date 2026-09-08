"""Root's independent metadata-only read of Socrates's actual native release."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / 'experiments/m193c-output-grid'
seen = {}

def checked(path, sha=None, size=None):
    path = Path(path)
    path = path if path.is_absolute() else ROOT / path
    path = path.resolve()
    assert path.is_relative_to(ROOT)
    assert path.suffix.lower() not in ('.arw', '.raw', '.tif', '.tiff', '.npy')
    before = path.stat()
    assert before.st_size <= 64 * 1024 * 1024
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(1024 * 1024):
            h.update(data)
    actual = dict(sha256=h.hexdigest(), bytes=before.st_size)
    assert path.stat().st_mtime_ns == before.st_mtime_ns
    assert sha is None or actual['sha256'] == sha
    assert size is None or actual['bytes'] == size
    assert seen.setdefault(str(path), actual) == actual
    return path

release_path = checked(HERE / 'native-sensor-derivative-release-1.json',
    'fb651f3b4aa5eeb891d6cef77e8719e13bb556ba086bd2dbd2add742d93505b8', 54343)
release = json.loads(release_path.read_bytes())
assert set(release) == set('schema scope source_bindings inputs commands build private_admission reader prior_work reuse_first'.split())
assert release['schema'] == 'm193c-sensor-native-derivative-release-v1'
assert release['scope'] == 'sensor-native-nine'
assert len(release['source_bindings']) == 146 and len(release['inputs']) == 93
for name, ref in release['source_bindings'].items():
    checked(name, ref['sha256'], ref['bytes'])
for ref in release['inputs']:
    checked(ref['path'], ref['sha256'], ref['bytes'])
old = json.loads((HERE / 'native-derivative-release-1.json').read_bytes())
assert all(release['source_bindings'][name] == ref for name, ref in old['source_bindings'].items())
assert all(ref in release['inputs'] for ref in old['inputs'])
assert release['prior_work'] == dict(cpu_seconds=37.71875, wall_seconds=32.1440803,
    file_bytes=240957039, metadata_bytes=4127988)
details_path = checked(HERE / 'work/native-sensor-release-1-preparation.json',
    '2ddb0d480a991a40cf00bf60a4cd2cedb7ba309a2f03e9a8d5f59e288d87ee65', 18876)
details = json.loads(details_path.read_bytes())
assert len(details['new_children']) == 17
assert [row['original_index'] for row in details['new_children'] if row['role'] == 'new-primary'] == [13,26,39,52,65,78,91,104]
assert [row['original_index'] for row in details['new_children'] if row['role'] == 'new-independent-reader'] == [0,13,26,39,52,65,78,91,104]
assert details['primary_reuse']['authority'] == release['reuse_first']
assert details['primary_reuse']['new_primary_invocation'] is False
assert details['primary_reuse']['snapshot_delete'] is False
assert sum(row['bytes'] for row in details['metadata_files']) == details['observed_metadata_bytes']
reserved = details['observed_metadata_bytes'] + details_path.stat().st_size + details['release_upper_bytes'] + details['future_root_metadata']['reserved_bytes']
assert reserved < details['reserved_bytes'] == 1048576
assert release_path.stat().st_size <= details['release_upper_bytes']
python = r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe'
output = HERE / 'native-sensor-derivative-1'
assert not output.exists()
parent = [python, '-B', '-X', 'faulthandler', '-X', 'pycache_prefix=' + str(output/'parent-cache'),
    str(HERE/'native-sensor-derivative-run.py'), '--release', str(release_path), '--release-sha256',
    'ACTUAL_EXECUTION_RELEASE_SHA256', '--output', str(output)]
assert release['commands'] == [parent]
assert len(release['reader']['commands']) == 9
for ordinal, command in enumerate(release['reader']['commands']):
    base = output / f'frame-{ordinal:02d}'
    assert command == [python, '-B', '-X', 'faulthandler', '-X', 'pycache_prefix=' + str(base/'reader-cache'),
        str(HERE/'independent-sensor-derivative-read.py'), '--request', str(base/'read-request.json'),
        '--request-sha256', 'ACTUAL_FRAME_REQUEST_SHA256', '--output', str(base/'independent')]
print(json.dumps(dict(status='PASS_METADATA_RELEASE_READ_ONLY', files=len(seen), sources=146, inputs=93,
    newly_planned_children=17, inventory_bytes=details['observed_metadata_bytes'], total_reserved_components=reserved,
    release_sha256=seen[str(release_path)]['sha256'], image_payloads_opened=0)))
