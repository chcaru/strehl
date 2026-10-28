"""Fetch only the pinned public inference artifacts; never import them."""
from pathlib import Path
import argparse
import hashlib
import json
import urllib.request

AREA = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((AREA / 'upstream-manifest.json').read_text())
    root = args.out.resolve()
    workspace = AREA.parents[2]
    assert root.is_relative_to(workspace / 'outputs')
    root.mkdir(parents=True, exist_ok=False)
    rows = []
    for record in manifest['sources'] + [manifest['checkpoint']]:
        path = root / record['path']
        assert path.resolve().is_relative_to(root)
        request = urllib.request.Request(record['url'], headers={'User-Agent': 'Strehl-local-research'})
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read(record['bytes'] + 1)
        assert len(data) == record['bytes'], (record['path'], len(data))
        sha256 = hashlib.sha256(data).hexdigest()
        if 'git_blob_sha1' in record:
            blob = b'blob ' + str(len(data)).encode() + b'\0' + data
            assert hashlib.sha1(blob).hexdigest() == record['git_blob_sha1']
        else:
            assert sha256 == record['sha256']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        rows.append(dict(record, sha256=sha256))
        print(record['path'], len(data), sha256, flush=True)
    (root / 'download-receipt.json').write_text(json.dumps(dict(
        status='COMPLETE_PINNED_DOWNLOAD', commit=manifest['commit'], artifacts=rows,
        code_executed=False, private_data_uploaded=False), indent=2) + '\n')


if __name__ == '__main__':
    main()
