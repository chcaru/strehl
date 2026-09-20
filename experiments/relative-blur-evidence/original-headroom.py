"""Read-only original-code headroom near fixed annotations, not a focus rule."""
from pathlib import Path
import argparse
import hashlib
import json
import struct

import numpy as np
import rawpy

HERE = Path(__file__).resolve().parent
POINTS = [('facet-core', 2624, 2906), ('dark-core', 3080, 2150),
          ('dark-column', 3080, 2212), ('nearby-structure', 3240, 2070)]


def binding(path):
    return dict(path=str(path.resolve()), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    receipt_path = HERE / 'witness-1/output/receipt.json'
    receipt = json.loads(receipt_path.read_text())
    result = dict(scope='Original integer-code headroom in fixed broad source neighbourhoods; '
                        'not an exact consumed-stencil clipping map or a physical ADC saturation calibration',
                  pipeline_white=15360, comparison_code=16383, boxes_half_extent_native=32,
                  mapping='held green similarity around active-native centre plus output crop origin; '
                          'broad box includes surrounding context, without channel-specific pull attribution',
                  bindings=[binding(receipt_path), binding(Path(__file__))], groups=[])
    for group in receipt['groups']:
        path = Path(group['source_path'])
        before = (path.stat().st_size, path.stat().st_mtime_ns)
        with rawpy.imread(str(path)) as raw:
            assert raw.raw_image.shape == (5120, 7168) and raw.sizes.top_margin == 0 and raw.sizes.left_margin == 0
            assert raw.raw_pattern.tolist() == [[0, 1], [3, 2]]
            # Visible width is7028. R awler's actual7032-wide active domain has
            # four more decoded columns, so copy the explicitly matched extent.
            original = raw.raw_image[:4688, :7032].copy()
            libraw_white = raw.white_level
            libraw_visible = list(raw.raw_image_visible.shape)
        assert hashlib.sha256(original.tobytes()).hexdigest() == group['source_active_u16_sha256']
        ar, ai, br, bi = [struct.unpack('>d', bytes.fromhex(v))[0] for v in group['transform_bits']]
        item = dict(source_index=group['source_index0'], source_path=str(path),
                    original_active_sha256=group['source_active_u16_sha256'], independent_decode_exact=True,
                    libraw_white=libraw_white, libraw_visible_shape=libraw_visible, regions=[])
        for name, x, y in POINTS:
            u, v = x + 56 - 3516, y + 38 - 2344
            sx, sy = 3516 + ar*u - ai*v + 2*br, 2344 + ai*u + ar*v + 2*bi
            x0, y0 = int(np.floor(sx-32)), int(np.floor(sy-32))
            x1, y1 = int(np.ceil(sx+32)), int(np.ceil(sy+32))
            assert 0 <= x0 < x1 < 7032 and 0 <= y0 < y1 < 4688
            patch = original[y0:y1, x0:x1]
            item['regions'].append(dict(name=name, source_centre_native=[sx, sy],
                original_xywh=[x0, y0, x1-x0, y1-y0], samples=int(patch.size),
                minimum=int(patch.min()), maximum=int(patch.max()),
                at_or_above_pipeline_white=int(np.count_nonzero(patch >= 15360)),
                exactly_pipeline_white=int(np.count_nonzero(patch == 15360)),
                at_or_above_16383=int(np.count_nonzero(patch >= 16383)),
                u16_sha256=hashlib.sha256(patch.tobytes()).hexdigest()))
        assert before == (path.stat().st_size, path.stat().st_mtime_ns)
        result['groups'].append(item)
    assert all(binding(Path(r['path'])) == r for r in result['bindings'])
    out.mkdir()
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    for item in result['groups']:
        print(item['source_index'], [(r['name'], r['maximum'], r['at_or_above_pipeline_white']) for r in item['regions']])


if __name__ == '__main__':
    main()
