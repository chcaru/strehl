"""Exact byte fallback on existing A7C II lossless ARWs; no camera operation."""
import hashlib
import io
import json
from pathlib import Path
import time
from wire import encode_iter, layout, receive


def main():
    folders = sorted(Path('D:/StrehlCaptures').glob('stack-*'))
    files = [f for folder in folders for f in sorted(folder.glob('*.ARW'))[:1]][-3:]
    assert len(files) == 3
    for file in files:
        data = file.read_bytes()
        assert layout(data) is None, 'Expected already-compressed ARW fallback'
        start = time.perf_counter()
        packet = b''.join(encode_iter(data, 'cfa', workers=4))
        enc = time.perf_counter() - start
        start = time.perf_counter()
        out = io.BytesIO()
        receipt = receive(io.BytesIO(packet), out)
        assert out.getvalue() == data
        print(json.dumps({'file': str(file), 'input_bytes': len(data),
                          'wire_bytes': len(packet), 'encode_s': enc,
                          'decode_s': time.perf_counter()-start,
                          'sha256': hashlib.sha256(data).hexdigest(),
                          'workers': 4, 'fallback': 'whole-byte-zstd-chunks',
                          'exact': receipt['exact']}), flush=True)


if __name__ == '__main__':
    main()
