"""Read-only clipping inventory of three independently decoded original caches."""
from pathlib import Path
import argparse
import hashlib
import json
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'experiments/raw-quality-2026-10-26/photo-review'
HASHES = {
    0: '1936869702bcbf8ae01ff4437dac0b2c715609edeaeb7ed442b2f32f4683c474',
    149: '15c33bdd558df9b4f9a303b294e3a6504ba14f1ef4d71cf8c52888111c50667f',
    298: 'c1e9c537dae84fad843fd9eaf80ba1dc15f1316bd436c04d1ed2f9ea8d87f2ca',
}


def ref(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return dict(path=str(path), sha256=h.hexdigest(), bytes=path.stat().st_size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(ROOT / 'outputs') and not out.exists()
    out.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    rows = []
    for index, expected in HASHES.items():
        folder = BASE / f'source-{index}'
        before = ref(folder / 'active-cfa-u16.npy')
        assert before['sha256'] == expected
        a = np.load(before['path'], mmap_mode='r', allow_pickle=False)
        assert a.dtype == np.uint16 and a.shape == (4688, 7028) and not a.flags.writeable
        phases = []
        for phase in range(4):
            p = a[phase // 2::2, phase % 2::2]
            phases.append(dict(phase=phase, min=int(p.min()), max=int(p.max()),
                 at_or_above_native_white=int(np.count_nonzero(p >= 15360)),
                 at_or_above_rawpy_white=int(np.count_nonzero(p >= 16383))))
        del p
        a._mmap.close()
        after = ref(before['path'])
        assert before == after
        rows.append(dict(index=index, cache=before, provenance=ref(folder / 'decode-receipt.json'),
             unchanged=True, shape=[4688, 7028], physical_phase_order=['R','G1','G2','B'],
             phases=phases, at_or_above_native_white=sum(p['at_or_above_native_white'] for p in phases),
             at_or_above_rawpy_white=sum(p['at_or_above_rawpy_white'] for p in phases)))
    result = dict(status='COMPLETE_RETAINED_ORIGINAL_CLIPPING_AUDIT', source=ref(__file__),
         numpy=np.__version__, wall_seconds=time.perf_counter()-start, sources=rows,
         scope='Three7028-wide original caches only; excludes four native columns and296 other frames.',
         RAW_reads=0, quality_claim=False)
    with (out / 'receipt.json').open('x', encoding='utf-8', newline='\n') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps([dict(index=r['index'], native_white_count=r['at_or_above_native_white'],
                          rawpy_white_count=r['at_or_above_rawpy_white']) for r in rows]))


if __name__ == '__main__':
    main()
