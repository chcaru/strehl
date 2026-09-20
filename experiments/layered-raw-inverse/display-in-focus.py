"""Complete generated in-focus scenes, using one display for every saved arm."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
source, out = args.source.resolve(), args.out.resolve()
assert out.is_relative_to(HERE) and not out.exists()
out.mkdir()
arms = ('truth', 'visibility', 'shot', 'cauchy', 'matrix', 'far-only', 'mean-observed', 'donor-observed')
records = []
for case in ('flat', 'layered'):
    canvas = Image.new('RGB', (1600, 866), '#202124')
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 10), case + ': complete 96x96 generated scenes; supplied in-focus PSF target; not photographs', fill='white')
    for index, arm in enumerate(arms):
        path = source / case / (arm + '-rgb-f32.npy')
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        array = np.load(path, allow_pickle=False)
        assert array.shape == (96, 96, 3) and array.dtype == np.float32 and np.isfinite(array).all()
        value = np.arcsinh(np.maximum(array, 0)/np.float32(2048))/np.float32(np.arcsinh(32000/2048))
        pixels = np.rint(np.clip(value, 0, 1)*255).astype(np.uint8)
        panel = Image.fromarray(pixels).resize((384, 384), Image.Resampling.NEAREST)
        x, y = 8 + (index % 4)*400, 52 + (index // 4)*410
        canvas.paste(panel, (x, y))
        draw.text((x, y-21), arm, fill='white')
        draw.rectangle((x+64, y+64, x+319, y+319), outline='#ffe080', width=1)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before
        records.append(dict(path=str(path), sha256=before))
    canvas.save(out / ('complete-' + case + '.png'))
(out / 'sources.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
