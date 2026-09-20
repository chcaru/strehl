"""Independent native views of completed outputs; no merge, RAW or quality metric."""
from pathlib import Path
import hashlib
import json

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE / 'spatial-full-1'
VIEWS = RUN / 'photo-comparison-1'
OLD = HERE / 'full-1/photo-comparison-1'
OUT = HERE / 'spatial-review-1'
HREC = ROOT / 'experiments/helicon-current/photo-comparison-1/coordinate-receipt.json'
REGIONS = ROOT / 'experiments/quality-september19/vitamin-c-review-1/regions.json'
ZOOMS = [('facet-core-boundary', [2533, 2846, 160, 160]),
         ('dark-core-boundary', [3011, 2097, 160, 160]),
         ('competing-structure', [3180, 2010, 120, 120])]
SEGMENTS = [((2624, 2906), (2602, 2945)), ((3080, 2150), (3102, 2203)),
            ((3240, 2070), (3240, 2070))]


def bind(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def main():
    assert not OUT.exists(), 'Review directory must be new'
    arrays, inputs = {}, {}
    profile = None
    paths = [('baseline', VIEWS / 'baseline.png'), ('old-candidate', OLD / 'candidate.png'),
             ('spatial-candidate', VIEWS / 'candidate.png'),
             ('helicon-b', ROOT / 'experiments/helicon-current/vitamin-c-b-2/whole-stack.tiff'),
             ('old-late', OLD / 'late.png'), ('spatial-late', VIEWS / 'late.png')]
    for label, path in paths:
        if label == 'helicon-b':
            with tifffile.TiffFile(path) as tf:
                raw = tf.asarray()
                icc = tf.pages[0].tags[34675].value
            array = ((raw.astype(np.uint32) + 128) // 257).astype(np.uint8)
            del raw
        else:
            with Image.open(path) as im:
                array, icc = np.array(im), im.info.get('icc_profile')
        if profile is None:
            profile = icc
        assert profile is not None and icc == profile
        arrays[label], inputs[label] = array, bind(path)
    matrix = np.array(json.loads(HREC.read_text())['registrations']['helicon-b']['matrix_baseline_to_output'])
    regions = json.loads(REGIONS.read_text())['regions']
    labels = {'baseline': 'Baseline', 'old-candidate': 'Original coefficient-mask donors',
              'spatial-candidate': 'Spatial AC donors 28/33/25', 'helicon-b': 'Helicon B (scale1.0107)',
              'old-late': 'Original coefficient-mask late69', 'spatial-late': 'Spatial AC late69'}
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
    rows, outputs = [], []
    OUT.mkdir()
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
                image.save(path, icc_profile=profile)
                outputs.append(bind(path))
        path = OUT / f'{name}-board.png'
        board.save(path, icc_profile=profile)
        outputs.append(bind(path)); rows.append(row)
        if zoom > 1:
            overlay = Image.fromarray(arrays['baseline'][y:y + h, x:x + w]).resize((tw, th), Image.Resampling.NEAREST)
            od = ImageDraw.Draw(overlay)
            gy, gx = np.mgrid[y:y + h, x:x + w]
            for a, b in SEGMENTS:
                vx, vy = b[0] - a[0], b[1] - a[1]
                norm = vx * vx + vy * vy
                t = np.clip(((gx - a[0]) * vx + (gy - a[1]) * vy) / norm, 0, 1) if norm else 0
                distance = np.hypot(gx - a[0] - t * vx, gy - a[1] - t * vy)
                for radius, colour in [(16, (255, 255, 0)), (24, (255, 0, 255))]:
                    for py, px in np.argwhere(np.abs(distance - radius) < .55):
                        od.rectangle((int(px) * zoom, int(py) * zoom, int(px) * zoom + zoom - 1,
                                      int(py) * zoom + zoom - 1), fill=colour)
            path = OUT / f'{name}-mask-outline.png'
            overlay.save(path, icc_profile=profile); outputs.append(bind(path))
    result = dict(helper=bind(Path(__file__)), inputs=inputs, outputs=outputs, rows=rows,
                  canonical_regions=bind(REGIONS), helicon_registration=bind(HREC),
                  current_coordinates=bind(VIEWS / 'coordinate-receipt.json'),
                  original_coordinates=bind(OLD / 'coordinate-receipt.json'),
                  scope='Existing rendered outputs only. No RAW, merge, image interpolation or quality metric. '
                        'Native crops, optional 3x nearest replication, common exact sRGB ICC; no tone change. '
                        'Helicon native scale difference retained. Separate radius16/24 outlines are geometry only.')
    (OUT / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(output=str(OUT), boards=len(rows), helper=result['helper'])))


if __name__ == '__main__':
    main()
