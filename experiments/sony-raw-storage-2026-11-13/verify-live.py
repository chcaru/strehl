"""Read-only archive checks using the earlier research decoder and RawPy.

This is author cross-implementation verification, not independent review. No
expanded live RAW is written to disk; original hashes also bind the Pi journal.
"""
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import imagecodecs
import numpy as np
import rawpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/sony-raw-storage-2026-11-13'
sys.path.insert(0, str(ROOT / 'experiments/sony-raw-compression-2026-11-12'))
from bench import transform


def unpack(data):
    assert data[:8] == b'STRHARC1'
    length = struct.unpack_from('<Q', data, 8)[0]
    checksum = data[16:48].hex()
    assert 0 < length <= 256 * 1024**2
    assert data[48:56] == b'STRHRAW1'
    assert struct.unpack_from('<Q', data, 56)[0] == length
    at = 64; output = bytearray()
    while len(output) < length:
        n, packed, mode, width = struct.unpack_from('<IIBI', data, at); at += 13
        assert 0 < packed <= n <= 4 * 1024**2 and len(output) + n <= length
        payload = data[at:at + packed]; at += packed
        assert len(payload) == packed
        block = payload if mode == 255 else imagecodecs.zstd_decode(payload)
        assert len(block) == n and mode in [0, 8, 255]
        if mode == 8:
            assert width >= 2 and n % (width * 4) == 0
            block = transform(np.frombuffer(block, dtype='u1'), 8, inverse=True, shape=(n // (2 * width), width)).tobytes()
        else:
            assert width == 0
        output.extend(block)
    assert at == len(data) and len(output) == length
    assert hashlib.sha256(output).hexdigest() == checksum
    return output


def main():
    reference = (OUT / 'reference/frame-000001.ARW.straw').read_bytes()
    # Refusal controls before trusting the comparison.
    bad = bytearray(reference); bad[16] ^= 1
    for wrong in [bad, reference[:-1], reference + b'x']:
        try:
            unpack(wrong)
        except (AssertionError, ValueError, struct.error):
            pass
        else:
            raise AssertionError('Archive verifier accepted corruption')
    original_path = Path(r'D:\StrehlCaptures\stack-1794612335049-9932\frame-000001.ARW')
    assert unpack(reference) == original_path.read_bytes()
    run = json.loads((OUT / 'storage-group.json').read_text())
    folder = Path(run['final']['storage']['receipt']['path']).parent
    archives = sorted(folder.glob('*.ARW.straw'))
    assert len(archives) == 4 and not list(folder.glob('*.ARW')) and not list(folder.glob('*.partial'))
    receipts = {Path(r['path']).name: r for r in map(json.loads, (folder / 'transfer-receipts.jsonl').read_text().splitlines())}
    events = list(map(json.loads, (folder / 'events.jsonl').read_text().splitlines()))
    groups = [e for e in events if e['event'] == 'capture_buffered']
    assert len(groups) == 1
    group = groups[0]['data']['response']; group_ids = []; rows = []
    for i, archive in enumerate(archives):
        data = unpack(archive.read_bytes())
        sha = hashlib.sha256(data).hexdigest()
        receipt = receipts[archive.name]; binding = group['files'][i]
        assert receipt['durable'] and receipt['sha256'] == sha and receipt['bytes'] == len(data)
        assert receipt['storage_bytes'] == archive.stat().st_size == receipt['wire_bytes'] + 48
        assert binding['sha256'] == sha and binding['member_index'] == i + 1 and binding['members'] == 4
        assert binding['name'] == receipt['logical_name'] == archive.stem
        tags = subprocess.run(['exiftool', '-json', '-Model', '-Sony:PixelShiftInfo', '-ExposureTime', '-FNumber', '-ISO', '-'], input=data, capture_output=True)
        assert tags.returncode == 0, tags.stderr
        tag = json.loads(tags.stdout)[0]
        m = re.search(r'Group (\d+), Shot (\d+)/4', tag['PixelShiftInfo'])
        assert m and int(m[2]) == i + 1 and tag['Model'] == 'ILCE-7CR'
        group_ids.append(m[1])
        with rawpy.imread(io.BytesIO(data)) as raw:
            plane = raw.raw_image_visible.copy()
        assert plane.shape == (6376, 9564) and plane.dtype == np.uint16
        rows.append({'name': archive.name, 'original_bytes': len(data), 'storage_bytes': archive.stat().st_size, 'sha256': sha, 'visible_shape': list(plane.shape), 'exif': {k: v for k, v in tag.items() if k != 'SourceFile'}})
    assert len(set(group_ids)) == 1
    timings = {}
    for s in run['history']:
        r = s['storage'].get('receipt') or {}
        if folder.name in r.get('path', '') and r.get('upload_seconds'):
            timings[Path(r['path']).name] = {k: r[k] for k in ['upload_seconds', 'wire_MB_per_second', 'upload_MB_per_second', 'wire_bytes']}
    assert len(timings) == 4
    result = {'folder': str(folder), 'files': rows, 'raw_bytes': sum(r['original_bytes'] for r in rows), 'storage_bytes': sum(r['storage_bytes'] for r in rows), 'camera_seconds': group['camera_seconds'], 'member_ready_seconds': [f['seconds'] for f in group['camera_reply']['files']], 'uploads': timings, 'queue_peak': max(s['storage'].get('queue_peak', 0) for s in run['history']), 'buffer_full_samples': sum(s['storage']['state'] == 'buffer_full' for s in run['history']), 'final_pending': run['final']['storage']['pending_frames'], 'reference_exact_cross_implementation': True, 'refusal_controls': 3}
    (OUT / 'live-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}))


if __name__ == '__main__':
    main()
