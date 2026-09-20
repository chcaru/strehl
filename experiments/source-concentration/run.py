"""Read-only two-pass locator over held developed TIFFs, after hash preflight.

Root executes only after independent synthetic controls. No RAW decoder, image
repair, source-label consumer, target coordinates or known donor labels here.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import time
import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('source_concentration_locator', HERE / 'locator.py')
locator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(locator)
ROOT = HERE.parent.parent
QUALITY = ROOT / 'experiments/quality-september19'
SCAN = QUALITY / 'vitamin-c-source-highlights/scan-1/receipt.json'
SOURCE = QUALITY / 'vitamin-c-comparator-2/developed'
MAP = QUALITY / 'vitamin-c-baseline-1/vitamin-c.warpmap.txt'
REGIONS = QUALITY / 'vitamin-c-review-1/regions.json'
DESIGN = ROOT / 'experiments/donor-consistency/automatic-design.md'
EXPECTED_SCAN = '0cca4885f036a419549beba62d56516d033038abf19db8fe9c57d2060c3157f5'
EXPECTED_MAP = '84275850a032dc8beb88945b00514a58ebca433e267c8e10342ac55986cf830f'
EXPECTED_SOURCE_RECEIPT = '88cc56b6d56f3f055defeb48e575b533c4bf46a06a22530b4e040396bbf44bb5'
EXPECTED_REGIONS = 'ff55ed297385ff8fef5d2badce07729537e2e867701d96d328be1eaf7bcb0f4f'
SENSOR_SIZE = (7032, 4688)
SENSOR_CENTRE = (3516.0, 2344.0)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp(path):
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def pixels_sha(pixels):
    return hashlib.sha256(np.asarray(pixels, dtype='<u2').tobytes(order='C')).hexdigest()


def open_image(path):
    image = tifffile.memmap(path, mode='r')
    if image.shape != (SENSOR_SIZE[1], SENSOR_SIZE[0], 3) or image.dtype != np.uint16:
        raise ValueError('held native RGB16 TIFF shape/type changed')
    return image


def bindings():
    checks = [(SCAN, EXPECTED_SCAN), (MAP, EXPECTED_MAP), (SOURCE / 'receipt.json', EXPECTED_SOURCE_RECEIPT),
              (REGIONS, EXPECTED_REGIONS)]
    for path, expected in checks:
        if sha(path) != expected:
            raise ValueError(f'held binding changed: {path}')
    scan = json.loads(SCAN.read_text(encoding='utf-8'))
    exports = json.loads((SOURCE / 'receipt.json').read_text(encoding='utf-8'))
    if exports['status'] != '70_UNALIGNED_NATIVE_RGB16_DEVELOPED':
        raise ValueError('incomplete source export')
    for key in ('tone_bits', 'wb_bits'):
        if scan['source_' + key] != exports[key]:
            raise ValueError('source development changed')
    maps = {}
    for line in MAP.read_text(encoding='utf-8').splitlines():
        parts = line.split()
        if len(parts) > 5 and parts[0].isdigit():
            if parts[1] != 'placed' or int(parts[0]) in maps:
                raise ValueError('unplaced or duplicate map entry')
            maps[int(parts[0])] = parts[2:6]
    if sorted(maps) != list(range(70)) or len(scan['frames']) != 140:
        raise ValueError('complete70maps and140old source bindings required')
    available = {r['name']: r['xywh'] for r in json.loads(REGIONS.read_text(encoding='utf-8'))['regions']}
    names = sorted({r['region'] for r in scan['frames']})
    if len(names) != 2:
        raise ValueError('expected the two frozen scan fields')
    fields = {name: available[name] for name in names}
    records = {}
    paths = {}
    before = {}
    offsets = set()
    for r in scan['frames']:
        key = (r['index0'], r['region'])
        if key in records or r['pull_bits'] != maps[r['index0']] or r['region'] not in fields:
            raise ValueError('duplicate or mismatched scan record')
        path = Path(r['source_tiff']).resolve()
        if path.parent != SOURCE.resolve() or path.name != Path(r['original_raw_name']).with_suffix('.tiff').name:
            raise ValueError('source path binding differs')
        if path.name.casefold() == 'golden.tiff':
            raise ValueError('golden is not a source frame')
        old_stamp = (r['source_bytes'], r['source_mtime_ns'])
        if stamp(path) != old_stamp or (r['index0'] in paths and paths[r['index0']] != path):
            raise ValueError('source metadata or repeated source path differs')
        field = fields[r['region']]
        centre = np.array(field[:2]) + (np.array(field[2:]) - 1) / 2
        offset = tuple(np.asarray(r['reference_native_center']) - centre)
        offsets.add(offset)
        mx, my = locator.source_coordinates(*centre, r['pull_bits'], SENSOR_CENTRE, offset)
        if not np.allclose([mx, my], r['mapped_native_center'], rtol=0, atol=1e-9):
            raise ValueError('scan mapped centre differs')
        origin = np.floor(np.array([mx, my]) - 191.5 + 0.5).astype(int).tolist()
        if r['source_native_xywh'] != origin + [384, 384]:
            raise ValueError('scan integer crop binding differs')
        records[key], paths[r['index0']], before[r['index0']] = r, path, old_stamp
    if len(offsets) != 1 or sorted(paths) != list(range(70)) or len(set(paths.values())) != 70:
        raise ValueError('incomplete source sequence or mixed output gauge')
    if set(records) != {(i, name) for i in range(70) for name in names}:
        raise ValueError('incomplete140 source/field records')
    offset = next(iter(offsets))
    # Prove every old384 binding before computing any new locator statistic.
    for i, path in paths.items():
        image = open_image(path)
        for name in names:
            r = records[i, name]
            x, y, w, h = r['source_native_xywh']
            if pixels_sha(np.asarray(image[y:y+h, x:x+w]).copy()) != r['crop_rgb16_sha256']:
                raise ValueError('old384source pixels changed')
        del image
        if stamp(path) != before[i]:
            raise ValueError('source changed during old-crop verification')
    return scan, fields, records, paths, before, offset


def expanded_patch(image, record, field, offset):
    x, y, w, h = field
    radius = locator.MEASURE_RADIUS
    corners_x = np.array([x-radius, x+w+radius, x-radius, x+w+radius])
    corners_y = np.array([y-radius, y-radius, y+h+radius, y+h+radius])
    sx, sy = locator.source_coordinates(corners_x, corners_y, record['pull_bits'], SENSOR_CENTRE, offset)
    # Four extra genuine source pixels cover lattice boundary-neighbour checks;
    # these are context, not a changed concentration or Gaussian radius.
    margin = locator.FILTER_RADIUS + 4
    x0, y0 = int(np.floor(sx.min())) - margin, int(np.floor(sy.min())) - margin
    x1, y1 = int(np.ceil(sx.max())) + margin + 1, int(np.ceil(sy.max())) + margin + 1
    if x0 < 0 or y0 < 0 or x1 > SENSOR_SIZE[0] or y1 > SENSOR_SIZE[1]:
        raise ValueError('genuine expanded image support unavailable; no padding permitted')
    pixels = np.asarray(image[y0:y1, x0:x1]).copy()
    ox, oy, ow, oh = record['source_native_xywh']
    if not (x0 <= ox and y0 <= oy and ox+ow <= x1 and oy+oh <= y1):
        raise ValueError('expanded crop does not include original384witness')
    if pixels_sha(pixels[oy-y0:oy-y0+oh, ox-x0:ox-x0+ow]) != record['crop_rgb16_sha256']:
        raise ValueError('expanded-to-original overlap differs')
    q, ceiling = locator.local_contrast(pixels.astype(np.float64) / 65535.0)
    origin = [x0 + locator.FILTER_RADIUS, y0 + locator.FILTER_RADIUS]
    rx, ry = locator.reference_coordinates(q.shape, origin, record['pull_bits'], SENSOR_CENTRE, offset)
    evidence = {'index0': record['index0'], 'region': record['region'], 'source_tiff': record['source_tiff'],
                'expanded_source_xywh': [x0, y0, x1-x0, y1-y0], 'expanded_rgb16_sha256': pixels_sha(pixels),
                'old384_overlap_sha256': record['crop_rgb16_sha256'], 'valid_q_source_origin': origin,
                'valid_q_shape': list(q.shape), 'pull_bits': record['pull_bits']}
    return q, ceiling, rx, ry, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(HERE.resolve()):
        raise ValueError('new output directory below source-concentration required')
    started = time.perf_counter()
    scan, fields, records, paths, before, offset = bindings()
    maximum = {name: np.zeros(locator.grid_shape(field), dtype=np.float64) for name, field in fields.items()}
    seen = {name: np.zeros(values.shape, dtype=bool) for name, values in maximum.items()}
    evidence = {}
    for i in range(70):
        image = open_image(paths[i])
        for name, field in fields.items():
            q, ceiling, rx, ry, item = expanded_patch(image, records[i, name], field, offset)
            locator.accumulate_maximum(maximum[name], seen[name], q, rx, ry, field)
            evidence[i, name] = item
        del image
        if stamp(paths[i]) != before[i]:
            raise ValueError('source metadata changed in seed pass')
    seeds = {name: locator.nominate_seeds(maximum[name], seen[name], field) for name, field in fields.items()}
    tracks = {name: [[] for _ in candidates] for name, candidates in seeds.items()}
    for i in range(70):
        image = open_image(paths[i])
        for name, field in fields.items():
            q, ceiling, rx, ry, item = expanded_patch(image, records[i, name], field, offset)
            if item != evidence[i, name]:
                raise ValueError('source expanded pixels/geometry changed between passes')
            for j, seed in enumerate(seeds[name]):
                record = locator.measure_seed(q, ceiling, rx, ry, seed)
                record['index0'] = i
                tracks[name][j].append(record)
        del image
        if stamp(paths[i]) != before[i]:
            raise ValueError('source metadata changed in track pass')
    for i, path in paths.items():
        if stamp(path) != before[i]:
            raise ValueError('source metadata changed after scan')
    results = [{'region': name, 'field_native_xywh': fields[name], 'seed': seed,
                'decision': locator.nominate_track(tracks[name][j])}
               for name in fields for j, seed in enumerate(seeds[name])]
    out.mkdir()
    receipt = {'schema': 1, 'scope': 'fixed display-space discriminator; no image repair, RAW read, optical flux or calibrated noise inference',
               'command': ['python', '-I', '-B', str(Path(__file__).resolve()), '--out', str(out)],
               'run_sha256': sha(Path(__file__)), 'locator_sha256': sha(HERE / 'locator.py'), 'design_sha256': sha(DESIGN),
               'scan_receipt_sha256': EXPECTED_SCAN, 'source_receipt_sha256': EXPECTED_SOURCE_RECEIPT,
               'warpmap_sha256': EXPECTED_MAP, 'frozen_regions_sha256': EXPECTED_REGIONS,
               'tone_bits': scan['source_tone_bits'], 'wb_bits': scan['source_wb_bits'], 'output_offset_native': offset,
               'constants': {key: getattr(locator, key) for key in ('SIGMA','FILTER_RADIUS','CELL','SEED_GRID','SEED_SEPARATION',
                   'SEARCH_RADIUS','MEASURE_RADIUS','COMPONENT_FRACTION','AMBIGUITY_FRACTION','CENTROID_LIMIT',
                   'MASS_FRACTION','PEAK_FRACTION','TRACK_MARGIN','CONTRACTION_RATIO')},
               'expanded_sources': list(evidence.values()), 'seed_cell_coverage': {name: {'seen': int(seen[name].sum()),
                    'total': int(seen[name].size)} for name in fields},
               'tracks': results, 'original_developed_metadata_unchanged': True,
               'seconds': time.perf_counter() - started}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'tracks': len(results), 'nominations': sum(t['decision']['status'] == 'nominated' for t in results),
                      'seconds': receipt['seconds'], 'quality_decision': 'none'}))


if __name__ == '__main__':
    main()
