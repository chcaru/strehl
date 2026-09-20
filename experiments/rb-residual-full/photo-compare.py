"""Prepare fixed photographic views of a completed observational pair only.

No RAW reads, merge execution, new registration, normalization or quality score.
The failed generated admission is not changed by preparing these views.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FULL_HELPER = ROOT / 'experiments/quality-september19/full-output-views.py'
REGIONS = ROOT / 'experiments/quality-september19/vitamin-c-review-1/regions.json'
HREC = ROOT / 'experiments/helicon-current/photo-comparison-1/coordinate-receipt.json'
HELICON = ROOT / 'experiments/helicon-current/vitamin-c-b-2/whole-stack.tiff'
NATIVE_SHAPE = (4612, 6920, 3)
CROP = [28, 19, 3460, 2306]
ZOOMS = [('facet-core-boundary', [2533, 2846, 160, 160]),
         ('dark-core-boundary', [3011, 2097, 160, 160]),
         ('competing-structure', [3180, 2010, 120, 120])]


def bind(path):
    with path.open('rb') as stream:
        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=sha)


def same_binding(actual, held):
    assert Path(actual['path']).resolve() == Path(held['path']).resolve()
    assert actual['bytes'] == held['bytes'] and actual['sha256'] == held['sha256']


def save_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def rgb8(raw):
    assert raw.dtype == np.uint16
    return ((raw.astype(np.uint32) + 128) // 257).astype(np.uint8)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    out = args.out.resolve() if args.out else run / 'photo-comparison-1'
    assert run.is_relative_to(HERE) and run != HERE
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    completion_path = run / 'completion.json'
    completion = json.loads(completion_path.read_text())
    assert completion['baseline_pixels_identical'] is True
    assert completion['shape'] == list(NATIVE_SHAPE)
    assert completion['photographic_promotion'] is False
    config_path = run / 'config.json'
    assert json.loads(config_path.read_text())['expected_crop'] == CROP
    receipt_path = run / 'output/receipt.json'
    same_binding(bind(receipt_path), completion['receipt'])
    hrec = json.loads(HREC.read_text())
    held_b = hrec['inputs']['helicon-b']
    matrix = np.asarray(hrec['registrations']['helicon-b']['matrix_baseline_to_output'], dtype=np.float64)
    assert matrix.shape == (2, 3) and np.all(np.isfinite(matrix))
    regions = json.loads(REGIONS.read_text())['regions']
    assert len(regions) == 5 and all(r['xywh'][2:] == [384, 384] for r in regions)
    paths = {arm: run / 'output' / f'{arm}.tiff' for arm in ('baseline', 'candidate')}
    paths['helicon-b'] = HELICON
    inputs, profile = {}, None
    for arm, path in paths.items():
        inputs[arm] = bind(path)
        same_binding(inputs[arm], held_b if arm == 'helicon-b' else completion[arm])
        with tifffile.TiffFile(path) as tf:
            page = tf.pages[0]
            expected_shape = tuple(held_b['shape']) if arm == 'helicon-b' else NATIVE_SHAPE
            assert page.shape == expected_shape and page.dtype == np.uint16
            icc = bytes(page.tags[34675].value)
        if profile is None:
            profile = icc
        assert icc == profile and len(icc) == held_b['icc_bytes']
        assert hashlib.sha256(icc).hexdigest() == held_b['icc_sha256']
    registration_reference = Path(hrec['inputs']['baseline']['path'])
    same_binding(bind(registration_reference), hrec['inputs']['baseline'])

    # Refuse missing completion, shape, colour or input binding before writing views.
    out.mkdir()
    outputs, arrays, commands = [], {}, []
    for arm in ('baseline', 'candidate'):
        command = [sys.executable, '-I', '-B', '-X', 'faulthandler', str(FULL_HELPER),
                   str(paths[arm]), str(out / f'{arm}.png')]
        child = subprocess.run(command, capture_output=True, text=True, timeout=90)
        log_path = out / f'{arm}-full-conversion.log'
        log_path.write_text(child.stdout + child.stderr, encoding='utf-8')
        commands.append(dict(argv=command, exit_code=child.returncode))
        assert child.returncode == 0, child.stderr
        conversion = json.loads((out / f'{arm}.json').read_text())
        assert conversion['source_sha256'] == inputs[arm]['sha256']
        assert conversion['shape'] == list(NATIVE_SHAPE) and conversion['icc_preserved']
        with Image.open(out / f'{arm}.png') as full:
            assert full.size == (NATIVE_SHAPE[1], NATIVE_SHAPE[0])
            assert full.info.get('icc_profile') == profile
            arrays[arm] = np.array(full)
            overview = full.copy()
        overview.thumbnail((1560, 1100), Image.Resampling.LANCZOS)
        overview.save(out / f'{arm}-overview.jpg', quality=95, icc_profile=profile)
        for suffix in ('.png', '.json', '-overview.jpg', '-full-conversion.log'):
            outputs.append(bind(out / f'{arm}{suffix}'))
    with Image.open(registration_reference) as reference:
        assert reference.info.get('icc_profile') == profile
        assert np.array_equal(arrays['baseline'], np.asarray(reference)), 'Held registration has a different baseline gauge'
    with tifffile.TiffFile(HELICON) as tf:
        helicon = tf.asarray()
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
    labels = {'baseline': 'Baseline', 'candidate': 'Guarded RAW colour detail', 'helicon-b': 'Helicon B (native scale1.0107)'}
    rows = []
    for name, box, zoom in [(r['name'], r['xywh'], 1) for r in regions] + [(n, b, 3) for n, b in ZOOMS]:
        x, y, w, h = box
        assert 0 <= x <= NATIVE_SHAPE[1] - w and 0 <= y <= NATIVE_SHAPE[0] - h
        tw, th = w * zoom, h * zoom
        board = Image.new('RGB', (3 * (tw + 16), th + 72), (235, 235, 235))
        draw = ImageDraw.Draw(board)
        draw.text((8, 8), name + (' | native samples' if zoom == 1 else ' | 3x nearest replication'), font=font, fill='black')
        row = dict(name=name, baseline_xywh=box, display_integer_zoom=zoom, arms={})
        for col, arm in enumerate(labels):
            if arm == 'helicon-b':
                centre = matrix @ np.array([x + (w - 1) / 2, y + (h - 1) / 2, 1.])
                xx, yy = np.rint(centre - [(w - 1) / 2, (h - 1) / 2]).astype(int)
                assert 0 <= xx <= helicon.shape[1] - w and 0 <= yy <= helicon.shape[0] - h
                patch = rgb8(helicon[yy:yy + h, xx:xx + w])
            else:
                xx, yy = x, y
                patch = arrays[arm][y:y + h, x:x + w]
            assert patch.shape == (h, w, 3)
            row['arms'][arm] = [int(xx), int(yy), w, h]
            image = Image.fromarray(patch)
            if zoom > 1:
                image = image.resize((tw, th), Image.Resampling.NEAREST)
            suffix = '-zoom' if zoom > 1 else ''
            patch_path = out / f'{name}-{arm}{suffix}.png'
            image.save(patch_path, icc_profile=profile)
            outputs.append(bind(patch_path))
            bx = col * (tw + 16) + 8
            draw.text((bx, 36), labels[arm], font=font, fill='black')
            board.paste(image, (bx, 62))
        board_path = out / f'{name}-board.png'
        board.save(board_path, icc_profile=profile)
        outputs.append(bind(board_path))
        rows.append(row)
    save_json(out / 'coordinate-receipt.json', dict(
        schema=1, helper=bind(Path(__file__)), full_output_helper=bind(FULL_HELPER),
        completion=bind(completion_path), config=bind(config_path), merge_receipt=bind(receipt_path),
        inputs=inputs, frozen_regions=bind(REGIONS), helicon_registration=bind(HREC),
        registration_baseline=bind(registration_reference), registration_baseline_rgb8_exact=True,
        original_crop_quads=CROP, native_shape=list(NATIVE_SHAPE),
        matrix_baseline_to_helicon_b=matrix.tolist(), regions=rows,
        icc=dict(bytes=len(profile), sha256=hashlib.sha256(profile).hexdigest(), all_exact=True),
        commands=commands, outputs=outputs,
        display='Full PNG and native crops: rounded RGB16 division by257, no tone/normalization. '
                'Centred zooms use3x nearest replication. OverviewJPEG is resized for orientation only. '
                'Helicon crops use mapped centres rounded to integer origins; native scale mismatch is retained.',
        scope='Completed saved outputs only; no RAW, merge, registration fit, score or photographic admission. '
              'The failed generated screen remains failed; this is a separate observational pair.'))
    print(json.dumps(dict(status='OBSERVATIONAL_PAIR_VIEWS_READY', out=str(out), boards=len(rows),
                          shape=list(NATIVE_SHAPE), photographic_admission=False)), flush=True)


if __name__ == '__main__':
    main()
