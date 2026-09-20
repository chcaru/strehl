"""Coordinate-only comparison of completed chip masters. Root executes; no RAW."""
from pathlib import Path
import argparse
import hashlib
import json
import math

import cv2
import numpy as np
import tifffile
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CURRENT = ROOT/'experiments/ca-before-mhc/full-1/current/output/image.tiff'
REGIONS = ROOT/'experiments/ca-before-mhc/inspection-1/views.json'
LABELS = {'current': 'Current', 'helicon-b': 'Helicon B R8 S4', 'helicon-c': 'Helicon C S4'}


def binding(path):
    with path.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=digest)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def read_master(path, shape):
    before = binding(path)
    with tifffile.TiffFile(path) as tf:
        assert len(tf.pages) == 1
        page = tf.pages[0]
        assert page.shape == shape and page.dtype == np.uint16
        icc = bytes(page.tags[34675].value)
        assert icc
        raw = page.asarray()
    before.update(shape=list(raw.shape), rgb16_le_sha256=hashlib.sha256(raw.astype('<u2', copy=False).tobytes()).hexdigest(),
                  icc_sha256=hashlib.sha256(icc).hexdigest())
    rgb = ((raw.astype(np.uint32)+128)//257).astype(np.uint8)
    return rgb, icc, before


def save_png(path, pixels, icc):
    Image.fromarray(pixels).save(path, icc_profile=icc)
    with Image.open(path) as check:
        assert check.info.get('icc_profile') == icc and np.array_equal(np.asarray(check), pixels)
    return binding(path)


def whole_views(out, name, rgb, icc):
    result = {'whole': save_png(out/(name+'-whole.png'), rgb, icc)}
    overview = Image.fromarray(rgb)
    overview.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
    result['overview'] = save_png(out/(name+'-overview.png'), np.asarray(overview), icc)
    return result


def features(rgb):
    small = cv2.resize(rgb, None, fx=.25, fy=.25, interpolation=cv2.INTER_AREA)
    keypoints, descriptors = cv2.SIFT_create(nfeatures=5000).detectAndCompute(cv2.cvtColor(small, cv2.COLOR_RGB2GRAY), None)
    return keypoints, descriptors


def distribution(values):
    return dict(count=len(values), median=float(np.median(values)), p90=float(np.percentile(values, 90)),
                maximum=float(np.max(values))) if len(values) else None


class MappingRefused(Exception):
    def __init__(self, reason, evidence):
        super().__init__(reason)
        self.evidence = dict(evidence, status='ambiguous', reason=reason)


def require(test, reason, evidence):
    if not test:
        raise MappingRefused(reason, evidence)


def registration(reference, target):
    kr, dr = reference
    kt, dt = target
    evidence = {}
    require(dr is not None and dt is not None and len(dt) >= 2, 'insufficient texture descriptors', evidence)
    pairs = cv2.BFMatcher().knnMatch(dr, dt, k=2)
    good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < .70*pair[1].distance]
    src = np.asarray([kr[m.queryIdx].pt for m in good], dtype=np.float64).reshape(-1, 2)*4
    dst = np.asarray([kt[m.trainIdx].pt for m in good], dtype=np.float64).reshape(-1, 2)*4
    evidence['ratio_matches'] = len(good)
    require(len(good) > 100, 'fewer than101 ratio matches', evidence)
    train = ((np.floor(src[:, 0]/384)+np.floor(src[:, 1]/384)).astype(np.int64) % 2) == 0
    evidence.update(training_matches=int(train.sum()), heldout_matches=int((~train).sum()))
    require(train.sum() > 50 and (~train).sum() > 50, 'insufficient disjoint-cell support', evidence)
    cv2.setRNGSeed(20260920)
    matrix, inliers = cv2.estimateAffinePartial2D(src[train], dst[train], method=cv2.RANSAC,
        ransacReprojThreshold=4., maxIters=10000, confidence=.999, refineIters=10)
    require(matrix is not None and inliers is not None, 'similarity fit failed', evidence)
    predicted = src@matrix[:, :2].T+matrix[:, 2]
    residual = np.linalg.norm(predicted-dst, axis=1)
    scale = float(math.hypot(matrix[0, 0], matrix[1, 0]))
    angle = float(math.degrees(math.atan2(matrix[1, 0], matrix[0, 0])))
    held = residual[~train]
    evidence.update(matrix_current_to_output=matrix.tolist(), scale=scale, angle_degrees=angle,
        training_inliers=int(inliers.sum()), training_residual_all=distribution(residual[train]),
        heldout_residual_all=distribution(held), heldout_fraction_within8=float(np.mean(held < 8)),
        source_xy=src.tolist(), target_xy=dst.tolist(), training=train.tolist(), residual_native=residual.tolist())
    require(int(inliers.sum()) > 100, 'fewer than101 training inliers', evidence)
    require(.9 < scale < 1.1 and abs(angle) < 3, 'transform outside fixed gauge bounds', evidence)
    require(np.median(held) < 3 and np.percentile(held, 90) < 12 and np.mean(held < 8) > .75,
            'held-out coordinates disagree with global similarity', evidence)
    evidence['status'] = 'global coordinate mapping accepted; local ambiguity remains possible'
    return matrix, evidence, src, residual, train


def local_status(src, residual, train, centre):
    near = (~train) & (np.linalg.norm(src-centre, axis=1) < 700)
    values = residual[near]
    accepted = len(values) >= 4 and np.median(values) < 4 and np.percentile(values, 90) < 12 and np.mean(values < 8) >= .75
    return dict(status='supported' if accepted else 'ambiguous', heldout_within700=distribution(values),
                fraction_within8=float(np.mean(values < 8)) if len(values) else None)


def mapped_origin(matrix, xywh):
    x, y, w, h = xywh
    half = np.array([(w-1)/2, (h-1)/2])
    centre = np.array([x, y])+half
    mapped = matrix[:, :2]@centre+matrix[:, 2]
    origin = np.rint(mapped-half).astype(np.int64)
    return origin, centre, mapped, origin+half-mapped


def fixed_regions():
    rows = read_json(REGIONS)['regions']
    assert len(rows) == 7 and len({r['region'] for r in rows}) == 7
    return [(r['region'], r['output_native_xywh']) for r in rows]


def commission(out):
    baseline, _, bound = read_master(CURRENT, (4300, 6468, 3))
    # Native integer copy only. No interpolation is used to construct this truth.
    dx, dy = 48, -32
    translated = np.zeros_like(baseline)
    translated[:dy, dx:] = baseline[-dy:, :-dx]
    original_features = features(baseline)
    matrix, evidence, _, _, _ = registration(original_features, features(translated))
    errors, slice_equal = [], []
    for _, xywh in fixed_regions():
        origin, centre, mapped, _ = mapped_origin(matrix, xywh)
        errors.append(float(np.linalg.norm(mapped-centre-[dx, dy])))
        x, y, w, h = xywh
        xx, yy = map(int, origin)
        slice_equal.append(bool(np.array_equal(translated[yy:yy+h, xx:xx+w], baseline[y:y+h, x:x+w])))
    wrong = matrix.copy()
    wrong[:, 2] += [32, 0]
    wrong_errors = [float(np.linalg.norm(mapped_origin(wrong, r)[2]-mapped_origin(wrong, r)[1]-[dx, dy])) for _, r in fixed_regions()]
    flat_refused = False
    try:
        registration(original_features, features(np.full((512, 512, 3), 127, dtype=np.uint8)))
    except MappingRefused:
        flat_refused = True
    passed = max(errors) <= 1 and all(slice_equal) and min(wrong_errors) > 1 and flat_refused
    save(out/'result.json', dict(passed=bool(passed), helper=binding(Path(__file__)), plan=binding(HERE/'comparison-plan.md'),
        baseline=bound, regions=binding(REGIONS), translation_native=[dx, dy], coordinate_error_native=errors,
        exact_native_slices=slice_equal, wrong_plus32_errors=wrong_errors, flat_refused=flat_refused, registration=evidence,
        scope='Mapping instrument only, not photographic quality or external-gauge truth.'))
    assert passed, 'mapping commission refused; preserve receipt, no vendor comparison'


def compare(run, commissioned, out):
    check = read_json(commissioned/'result.json')
    assert check['passed'] and check['helper'] == binding(Path(__file__)) and check['plan'] == binding(HERE/'comparison-plan.md')
    assert check['regions'] == binding(REGIONS)
    frozen_run = read_json(run/'bindings.json')
    assert frozen_run['native_master'] == binding(CURRENT)
    paths = {'current': CURRENT, **{name: run/name/'whole-stack.tiff' for name in ('helicon-b', 'helicon-c')}}
    inputs, views, registration_receipts, outputs = {}, {}, {}, []
    patches = {name: {} for name, _ in fixed_regions()}
    base, icc, inputs['current'] = read_master(CURRENT, (4300, 6468, 3))
    assert check['baseline'] == inputs['current']
    basefeatures = features(base)
    views['current'] = whole_views(out, 'current', base, icc)
    for region, xywh in fixed_regions():
        x, y, w, h = xywh
        p = out/(region+'-current.png')
        outputs.append(save_png(p, base[y:y+h, x:x+w], icc))
        patches[region]['current'] = dict(status='reference', xywh=xywh, path=str(p))
    for name in ('helicon-b', 'helicon-c'):
        receipt_path = run/name/'output.json'
        completed = read_json(receipt_path)
        assert completed['complete_299_source_reference'] and completed['views']['master'] == binding(paths[name])
        rgb, other_icc, inputs[name] = read_master(paths[name], (4688, 7032, 3))
        assert other_icc == icc
        assert inputs[name]['rgb16_le_sha256'] == completed['views']['rgb16_le_sha256']
        inputs[name]['completion_receipt'] = binding(receipt_path)
        # Whole-field displays are produced before any local comparison crops.
        views[name] = whole_views(out, name, rgb, icc)
        try:
            matrix, evidence, src, residual, train = registration(basefeatures, features(rgb))
        except MappingRefused as refusal:
            registration_receipts[name] = refusal.evidence
            for region, _ in fixed_regions():
                patches[region][name] = dict(status='ambiguous: global mapping refused', reason=str(refusal))
            continue
        registration_receipts[name] = evidence
        for region, xywh in fixed_regions():
            origin, centre, mapped, rounding = mapped_origin(matrix, xywh)
            x, y = map(int, origin)
            _, _, w, h = xywh
            info = local_status(src, residual, train, centre)
            info.update(xywh=[x, y, w, h], mapped_centre=mapped.tolist(), rounding_native=rounding.tolist())
            if x < 0 or y < 0 or x+w > rgb.shape[1] or y+h > rgb.shape[0]:
                info['status'] = 'ambiguous: native crop outside full output'
            else:
                p = out/(region+'-'+name+'.png')
                outputs.append(save_png(p, rgb[y:y+h, x:x+w], icc))
                info['path'] = str(p)
            patches[region][name] = info
        del rgb
    for region, xywh in fixed_regions():
        _, _, w, h = xywh
        board = Image.new('RGB', (3*(w+16), h+68), (235, 235, 235))
        draw = ImageDraw.Draw(board)
        draw.text((8, 5), region+' | native crops; coordinate-only match, no resampling', fill=(0, 0, 0))
        for column, name in enumerate(LABELS):
            info = patches[region][name]
            x = column*(w+16)+8
            draw.text((x, 23), LABELS[name]+' | '+info['status'], fill=(160, 0, 0) if info['status'].startswith('ambiguous') else (0, 0, 0))
            if 'path' in info:
                with Image.open(info['path']) as patch:
                    board.paste(patch, (x, 52))
        path = out/(region+'-board.png')
        outputs.append(save_png(path, np.asarray(board), icc))
    for name, path in paths.items():
        assert binding(path) == {k: inputs[name][k] for k in ('path', 'bytes', 'sha256')}
    save(out/'coordinate-receipt.json', dict(schema=1, helper=binding(Path(__file__)), plan=binding(HERE/'comparison-plan.md'),
        commission=binding(commissioned/'result.json'), frozen_regions=binding(REGIONS), inputs=inputs, whole_views=views,
        registrations=registration_receipts, regions=patches, outputs=outputs, input_masters_unchanged=True,
        display='All RGB16 rounded(u16+128)//257, same unchanged ICC; only whole overviews resize.',
        coordinates='Current ref149. External independent gauge. Similarity selects native crop centres only; scale/angle mismatch remains.',
        limitations='SIFT correspondences can confuse repeated texture; ambiguous regions cannot support local quality claims. No metric ranks images. Whole review must check trial overlays.',
        quality_claim=False))
    lines = ['# Complete chip references', 'Inspect the entire fields before native crops. All display paths use identical RGB16 conversion and ICC.']
    for name, label in LABELS.items():
        lines += [f'## {label}', f'[RGB16 master]({paths[name].as_posix()})',
                  f'[Complete native PNG]({(out/(name+"-whole.png")).as_posix()})',
                  f'![Whole-field overview, resized]({(out/(name+"-overview.png")).as_posix()})']
    lines += ['## Fixed native regions', 'Left Current; middle Helicon B; right Helicon C. Red ambiguous labels prohibit a local quality conclusion.']
    lines += [f'![{region}]({(out/(region+"-board.png")).as_posix()})' for region, _ in fixed_regions()]
    (out/'images.md').write_text('\n\n'.join(lines)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('commission', 'compare'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--run', type=Path, default=HERE/'run-1')
    parser.add_argument('--commission', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.parent == HERE
    out.mkdir(exist_ok=False)
    cv2.setNumThreads(4)
    if args.stage == 'commission':
        commission(out)
    else:
        assert args.commission is not None
        compare(args.run.resolve(), args.commission.resolve(), out)
    print('CHIP_COMPARISON_READY', out, flush=True)


if __name__ == '__main__':
    main()
