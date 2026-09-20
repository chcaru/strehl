"""Conservative CA-before-MHC source-support bound, no RAW or image reads."""
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MAP = ROOT/'experiments/quality-september14/chip-baseline-1/chip.warpmap.txt'


def native_pull(p, a, b):
    return complex(3516, 2344) + a*(p-complex(3516, 2344)) + 2*b


def bound(a, b, crop):
    x, y, w, h = crop
    points = [native_pull(complex(xx, yy), a, b)
              for xx in (2*x, 2*(x+w)-1) for yy in (2*y, 2*(y+h)-1)]
    # Catmull destination lattice reach <=2, followed by MHC radius2.
    lx, hx = min(p.real for p in points)-4, max(p.real for p in points)+4
    ly, hy = min(p.imag for p in points)-4, max(p.imag for p in points)+4
    margins = [lx, 7031-hx, ly, 4687-hy]
    for eps, phase in ((-508.4e-6, 0), (174.4e-6, 1)):
        for xx in (lx, hx):
            for yy in (ly, hy):
                q = native_pull(complex(xx, yy), 1+eps, 0)/2-phase/2*(1+1j)
                margins.extend([q.real-1.5, 3516-2.5-q.real,
                                q.imag-1.5, 2344-2.5-q.imag])
    return min(margins)


def main():
    data = MAP.read_bytes()
    assert hashlib.sha256(data).hexdigest() == 'ce8534c9e65c5c761373bad87df5352c1c46319b7eaf7f7c91477ea61b4f4922'
    rows = []
    for line in data.decode().splitlines():
        p = line.split()
        if len(p) >= 6 and p[0].isdigit():
            assert p[1] == 'placed'
            ar, ai, br, bi = [struct.unpack('>d', bytes.fromhex(v))[0] for v in p[2:6]]
            rows.append((int(p[0]), complex(ar, ai), complex(br, bi)))
    assert len(rows) == 299
    result = {'label': 'DERIVED conservative geometric bound; not image quality or an exact coverage census',
              'map_sha256': hashlib.sha256(data).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'cases': []}
    for inset in (0, 8):
        crop = [133+inset, 89+inset, 3250-2*inset, 2166-2*inset]
        margins = [(i, bound(a, b, crop)) for i, a, b in rows]
        result['cases'].append({'additional_inset_quads': inset, 'crop_quad_xywh': crop,
            'sufficient_support': all(m >= 1e-9 for _, m in margins),
            'refusing_frames': [i for i, m in margins if m < 1e-9],
            'minimum_margin_mixed_native_green_and_colour_plane_pixels': min(m for _, m in margins),
            'scope': 'Failure is inconclusive; envelope bounds a superset. Actual finite coverage remains authoritative.'})
    with (HERE/'support-preflight-1.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
