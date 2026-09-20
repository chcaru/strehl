"""Complete generated scenes at a shared display transform; no crop selection."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument('--screen', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
assert not args.out.exists()
args.out.mkdir()
records = []
for case in ('flat', 'layered', 'far-only', 'angular-mismatch'):
    labels = ('truth', 'mean', 'far-only', 'candidate', 'oracle-bound')
    canvas = Image.new('RGB', (5*400, 448), '#202124')
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 10), case + ': complete 96x96 generated scenes; yellow box is supported scoring domain', fill='white')
    for i, label in enumerate(labels):
        path = args.screen / 'output' / case / (label + '-rgb-f32.npy')
        raw = path.read_bytes()
        a = np.load(path, allow_pickle=False)
        v = np.arcsinh(np.maximum(a, 0)/np.float32(2048))/np.float32(np.arcsinh(32000/2048))
        pixels = np.rint(np.clip(v, 0, 1)*255).astype(np.uint8)
        im = Image.fromarray(pixels).resize((384, 384), Image.Resampling.NEAREST)
        x, y = 8+i*400, 52
        canvas.paste(im, (x, y))
        draw.text((x, 31), label, fill='white')
        draw.rectangle((x+64, y+64, x+319, y+319), outline='#ffe080', width=1)
        records.append(dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest()))
    canvas.save(args.out / ('complete-' + case + '.png'))
(args.out / 'sources.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
