"""Independent completed-output review; no RAW, render or photographic score."""
from pathlib import Path
import hashlib
import json

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE / 'corrected-full-1'
OLD_RUN = HERE / 'spatial-full-1'
VIEWS = RUN / 'photo-comparison-1'
OLD = OLD_RUN / 'photo-comparison-1'
OUT = HERE / 'corrected-review-1'
HREC = ROOT / 'experiments/helicon-current/photo-comparison-1/coordinate-receipt.json'
REGIONS = ROOT / 'experiments/quality-september19/vitamin-c-review-1/regions.json'
ZOOMS = [('facet-core-boundary', [2533, 2846, 160, 160]),
         ('dark-core-boundary', [3011, 2097, 160, 160]),
         ('competing-structure', [3180, 2010, 120, 120])]
OLD_SEGMENTS = [((2624, 2906), (2602, 2945)), ((3080, 2150), (3102, 2203)),
                ((3240, 2070), (3240, 2070))]
NEW_SEGMENTS = [((2624, 2906), (2602, 2945)), ((3080, 2150), (3080, 2212)),
                ((3240, 2070), (3240, 2070))]
ALLOWED_CHANGE = [3052, 2122, 80, 120]


def bind(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def exact_extent(arm):
    old_path, new_path = (run / 'output' / f'{arm}.tiff' for run in (OLD_RUN, RUN))
    old, new = tifffile.memmap(old_path, mode='r'), tifffile.memmap(new_path, mode='r')
    assert old.shape == new.shape == (4612, 6920, 3) and old.dtype == new.dtype == np.uint16
    x0, y0, width, height = ALLOWED_CHANGE
    changed, outside, maximum = 0, 0, 0
    bbox = [old.shape[1], old.shape[0], -1, -1]
    for y in range(0, old.shape[0], 256):
        delta = new[y:y + 256].astype(np.int32) - old[y:y + 256].astype(np.int32)
        maximum = max(maximum, int(np.abs(delta).max()))
        yy, xx = np.nonzero(np.any(delta != 0, axis=2))
        count = len(xx)
        changed += count
        if count:
            yy += y
            bbox = [min(bbox[0], int(xx.min())), min(bbox[1], int(yy.min())),
                    max(bbox[2], int(xx.max())), max(bbox[3], int(yy.max()))]
            outside += int(np.count_nonzero((xx < x0) | (xx >= x0 + width) | (yy < y0) | (yy >= y0 + height)))
    regions = {}
    for region in json.loads(REGIONS.read_text())['regions']:
        x, y, w, h = region['xywh']
        regions[region['name']] = int(np.count_nonzero(np.any(old[y:y + h, x:x + w] != new[y:y + h, x:x + w], axis=2)))
    result = dict(arm=arm, old=bind(old_path), corrected=bind(new_path),
                  changed_rgb16_pixels=changed, changed_bbox_inclusive=bbox if changed else None,
                  maximum_abs_channel_difference_dn=maximum, outside_allowed_rectangle=outside,
                  allowed_rectangle_xywh=ALLOWED_CHANGE, canonical_changed_rgb16_pixels=regions)
    del old, new
    return result


def overlay(array, box, zoom, segments):
    x, y, w, h = box
    image = Image.fromarray(array[y:y + h, x:x + w]).resize((w * zoom, h * zoom), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image)
    gy, gx = np.mgrid[y:y + h, x:x + w]
    for a, b in segments:
        vx, vy = b[0] - a[0], b[1] - a[1]
        norm = vx * vx + vy * vy
        t = np.clip(((gx - a[0]) * vx + (gy - a[1]) * vy) / norm, 0, 1) if norm else 0
        distance = np.hypot(gx - a[0] - t * vx, gy - a[1] - t * vy)
        for radius, colour in [(16, (255, 255, 0)), (24, (255, 0, 255))]:
            for py, px in np.argwhere(np.abs(distance - radius) < .55):
                draw.rectangle((int(px) * zoom, int(py) * zoom, int(px) * zoom + zoom - 1,
                                int(py) * zoom + zoom - 1), fill=colour)
    return image


def main():
    assert not OUT.exists(), 'Review directory must be new'
    OUT.mkdir()
    changes = {arm: exact_extent(arm) for arm in ('baseline', 'candidate', 'late')}
    change_receipt = dict(helper=bind(Path(__file__)), meaning='Exact RGB16 activity and support only; no quality metric',
                          conservative_dark_union_plus_mhc_xywh=ALLOWED_CHANGE, arms=changes)
    (OUT / 'change-extent.json').write_text(json.dumps(change_receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(changes), flush=True)
    assert changes['baseline']['changed_rgb16_pixels'] == 0, 'Baseline differs across runs'
    for arm in ('candidate', 'late'):
        assert changes[arm]['outside_allowed_rectangle'] == 0, f'{arm}: changes escape frozen conservative rectangle'
        assert changes[arm]['changed_rgb16_pixels'] > 0, f'{arm}: changed endpoint not exercised'
    arrays, inputs, profile = {}, {}, None
    paths = [('baseline', VIEWS / 'baseline.png'), ('old-candidate', OLD / 'candidate.png'),
             ('corrected-candidate', VIEWS / 'candidate.png'),
             ('helicon-b', ROOT / 'experiments/helicon-current/vitamin-c-b-2/whole-stack.tiff'),
             ('old-late', OLD / 'late.png'), ('corrected-late', VIEWS / 'late.png')]
    for label, path in paths:
        if label == 'helicon-b':
            with tifffile.TiffFile(path) as tf:
                raw, icc = tf.asarray(), tf.pages[0].tags[34675].value
            array = ((raw.astype(np.uint32) + 128) // 257).astype(np.uint8)
            del raw
        else:
            with Image.open(path) as im:
                array, icc = np.array(im), im.info.get('icc_profile')
        if profile is None: profile = icc
        assert profile is not None and icc == profile
        arrays[label], inputs[label] = array, bind(path)
    matrix = np.array(json.loads(HREC.read_text())['registrations']['helicon-b']['matrix_baseline_to_output'])
    labels = {'baseline': 'Baseline', 'old-candidate': 'Original-address spatial donors',
              'corrected-candidate': 'Corrected-address spatial donors', 'helicon-b': 'Helicon B (scale1.0107)',
              'old-late': 'Original-address spatial late69', 'corrected-late': 'Corrected-address spatial late69'}
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
    rows, outputs = [], []
    regions = json.loads(REGIONS.read_text())['regions']
    for name, box, zoom in [(r['name'], r['xywh'], 1) for r in regions] + [(n, b, 3) for n, b in ZOOMS]:
        x, y, w, h = box
        tw, th = w * zoom, h * zoom
        board = Image.new('RGB', (3 * (tw + 16), 2 * (th + 42) + 36), (235, 235, 235))
        draw = ImageDraw.Draw(board)
        draw.text((8, 8), name + (' | native samples' if zoom == 1 else ' | 3x nearest replication'), font=font, fill='black')
        row = dict(name=name, baseline_xywh=box, display_integer_zoom=zoom, arms={})
        for k, (arm, array) in enumerate(arrays.items()):
            if arm == 'helicon-b':
                centre = matrix @ np.array([x + (w - 1) / 2, y + (h - 1) / 2, 1.])
                xx, yy = np.rint(centre - [(w - 1) / 2, (h - 1) / 2]).astype(int)
            else:
                xx, yy = x, y
            patch = array[yy:yy + h, xx:xx + w]
            assert patch.shape == (h, w, 3)
            row['arms'][arm] = [int(xx), int(yy), w, h]
            image = Image.fromarray(patch).resize((tw, th), Image.Resampling.NEAREST)
            bx, by = (k % 3) * (tw + 16) + 8, (k // 3) * (th + 42) + 36
            draw.text((bx, by), labels[arm], font=font, fill='black')
            board.paste(image, (bx, by + 26))
            if zoom > 1:
                path = OUT / f'{name}-{arm}-zoom.png'
                image.save(path, icc_profile=profile); outputs.append(bind(path))
        path = OUT / f'{name}-board.png'
        board.save(path, icc_profile=profile); outputs.append(bind(path)); rows.append(row)
        if zoom > 1:
            for label, segments in [('old', OLD_SEGMENTS), ('corrected', NEW_SEGMENTS)]:
                path = OUT / f'{name}-{label}-mask-outline.png'
                overlay(arrays['baseline'], box, zoom, segments).save(path, icc_profile=profile)
                outputs.append(bind(path))
    result = dict(helper=bind(Path(__file__)), inputs=inputs, outputs=outputs, rows=rows,
                  change_extent=bind(OUT / 'change-extent.json'), canonical_regions=bind(REGIONS),
                  helicon_registration=bind(HREC), current_coordinates=bind(VIEWS / 'coordinate-receipt.json'),
                  old_coordinates=bind(OLD / 'coordinate-receipt.json'),
                  old_segments=OLD_SEGMENTS, corrected_segments=NEW_SEGMENTS,
                  scope='Existing outputs only. Native crops and3x nearest replication, same exact sRGB ICC, no tone change. '
                        'Helicon scale difference retained. Old/corrected radius16/24 outlines are separate geometry views. '
                        'Both long left tail and right branch must be reviewed; no photographic gate passed by this helper.')
    (OUT / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(output=str(OUT), boards=len(rows), helper=result['helper'])))


if __name__ == '__main__':
    main()
