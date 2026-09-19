"""Star-sand adapter of the frozen September 14 green-only registrar.

Default invocation writes a patch staging plan and decodes no RAW files.
--fit STAGED_ROOT consumes saved CFA patches with an independent centre decode.
STAGED_ROOT/<roi>/receipt.json and frame-<index>-cfa.npy follow the existing
joint-raw-samples receipt schema. This script has no RAW decoder dependency.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INSPECTION = HERE / 'star-inspection-1'
MAP = HERE / 'star-baseline-1/star.warpmap.txt'
MAP_HASH = '6594d98255383218a3114fd783bfd0e2215b39b202777f1ee2e493f4b287a6a1'
REGISTRAR = ROOT / 'experiments/quality-september14/local-green-translation.py'
REGISTRAR_HASH = '5b64f7e612fd94cd8a22515bffb67addcee71021f6338f10a249c63864420196'
FRAMES = list(range(125, 134))
REFERENCE = 129


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def plan():
    assert hashlib.sha256(MAP.read_bytes()).hexdigest() == MAP_HASH
    assert hashlib.sha256(REGISTRAR.read_bytes()).hexdigest() == REGISTRAR_HASH
    warp = load('star_warp_parser', ROOT / 'experiments/M-PHASE0-PHASE/src/clib.py').parse_warpmap(str(MAP))
    assert warp['reference_index'] == REFERENCE and warp['plane'] == (3516, 2344)
    selected = json.loads((HERE / 'star-baseline-1/invocation.json').read_text())['inputs']
    assert len(selected) == 259
    assert Path(selected[REFERENCE]['path']).name == 'DSC00145.ARW'
    roi_records = json.loads((INSPECTION / 'receipt.json').read_text())['rois']
    centre = complex(3516, 2344)
    plans = []
    for roi in roi_records:
        x, y, w, h = roi['reference_sensor_xywh']
        assert (w,h) == (392,392)
        corners = np.array([complex(x,y), complex(x+w-1,y), complex(x,y+h-1), complex(x+w-1,y+h-1)])
        frames = []
        for index in FRAMES:
            a,b = warp['placements'][index]
            source = centre + a*(corners-centre) + 2*b
            # Even bounds preserve global RGGB parity; 8 native pixels extra.
            x0 = 2*int(np.floor((source.real.min()-8)/2))
            y0 = 2*int(np.floor((source.imag.min()-8)/2))
            x1 = 2*int(np.ceil((source.real.max()+9)/2))
            y1 = 2*int(np.ceil((source.imag.max()+9)/2))
            assert 0 <= x0 < x1 <= 7028 and 0 <= y0 < y1 <= 4688
            frames.append(dict(index=index, source=selected[index]['path'],
                               source_xywh=[x0,y0,x1-x0,y1-y0], a=[a.real,a.imag], b_plane=[b.real,b.imag]))
        plans.append(dict(name=roi['name'], reference_index=REFERENCE, target_origin_native=[x,y],
                          target_shape=[392,392], native_sensor_shape=[4688,7032],
                          libraw_visible_shape=[4688,7028], levels=[512,15360],
                          map_sha256=MAP_HASH, frames=frames))
    return dict(status='PLANNED_ONLY_NO_RAW_DECODE', reference_index=REFERENCE, frames=FRAMES,
                registrar_sha256=REGISTRAR_HASH, map_sha256=MAP_HASH, rois=plans,
                storage='Original u16 CFA; copy inside RawPy context; independently decode identical patches',
                required_receipt='Add raw_u16_sha256 to each frame; independently decode reference129 and record 0 differing sensels; other decoder checks may be null',
                scope='Nine preselected neighbours; local placement diagnostic, not equal-focus or quality truth')


def fit(staged_root, output, design):
    started = time.process_time()
    output.mkdir(exist_ok=False)
    reg = load('star_frozen_registrar', REGISTRAR)
    controls = reg.controls()  # Original falsifiable gates run before opening photographic CFA.
    save(output / 'controls.json', controls)
    rows = []
    for target in design['rois']:
        folder = staged_root / target['name']
        receipt = json.loads((folder / 'receipt.json').read_text())
        for key in ('reference_index','target_origin_native','target_shape','native_sensor_shape','levels','map_sha256'):
            assert receipt[key] == target[key], f'Receipt differs: {target["name"]} {key}'
        assert [r['index'] for r in receipt['frames']] == FRAMES
        guides = {}
        for record,expected in zip(receipt['frames'],target['frames']):
            for key in ('index','source','source_xywh','a','b_plane'):
                assert record[key] == expected[key], f'Staging mismatch: {key}'
            if record['index'] == REFERENCE:
                assert record['independently_decoded_different_sensels'] == 0
            else:
                assert record['independently_decoded_different_sensels'] in (None,0)
            raw = np.load(folder / f"frame-{record['index']}-cfa.npy", allow_pickle=False)
            assert raw.dtype == np.uint16 and raw.shape == tuple(reversed(record['source_xywh'][2:]))
            assert hashlib.sha256(raw.tobytes()).hexdigest() == record['raw_u16_sha256']
            black,white = map(np.float32,receipt['levels'])
            guides[record['index']] = reg.guide((raw.astype(np.float32)-black)/(white-black),
                                                record['source_xywh'][:2], raw<16383)
        centre = complex(3516,2344)
        left,right = reg.grids()
        def positions(record):
            return [reg.mapped(p,target['target_origin_native'],centre,complex(*record['a']),
                               complex(*record['b_plane']),record['source_xywh'][:2]) for p in (left,right)]
        ref_record = next(r for r in receipt['frames'] if r['index'] == REFERENCE)
        ref_left,ref_right = [reg.sample(guides[REFERENCE],p) for p in positions(ref_record)]
        results = []
        for record in receipt['frames']:
            result,_ = reg.fit(guides[record['index']],ref_left,ref_right,*positions(record))
            result.update(frame=record['index'],source_xywh=record['source_xywh'])
            before = result['before']['validation_rmse']
            result['validation_ratio'] = result['after']['validation_rmse']/before if before>0 else None
            results.append(result)
        rows.append(dict(roi=target['name'],target_origin_native=target['target_origin_native'],frames=results))
    elapsed = time.process_time()-started
    assert elapsed<60
    save(output / 'result.json', dict(status='LOCAL_TRANSLATION_DIAGNOSTIC',design=design,rois=rows,cpu_seconds=elapsed,
         interpretation='Low-pass guide prediction only; bounds are not optima; gains/biases are not image corrections'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fit', type=Path, metavar='STAGED_ROOT')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--roi', choices=('ridged-shell','porous-grain'))
    args = parser.parse_args()
    design = plan()
    if args.roi:
        design['rois'] = [r for r in design['rois'] if r['name'] == args.roi]
    if args.fit is None:
        assert args.out is None
        save(INSPECTION / 'staging-plan.json', design)
        print(json.dumps(dict(status=design['status'],rois=len(design['rois']),frames=FRAMES)))
    else:
        assert args.out is not None, '--fit requires a fresh --out directory'
        fit(args.fit.resolve(),args.out.resolve(),design)


if __name__ == '__main__':
    main()
