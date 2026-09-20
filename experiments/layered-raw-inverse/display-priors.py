"""Complete generated scenes at one fixed display, not photographic evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
args.out.mkdir(exist_ok=False)
records = []
for case in ('flat', 'layered'):
    paths = [HERE / 'screen-1/output' / case / 'truth-rgb-f32.npy'] + [
        HERE / run / 'output' / case / 'fixed-alpha/reconstruction.npz'
        for run in ('visibility-1', 'shot-prior-1', 'cauchy-1')]
    labels = ('truth', 'original Huber, known alpha', 'shot-noise Huber, known alpha', 'Cauchy, known alpha')
    canvas = Image.new('RGB', (1600, 448), '#202124')
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 10), case + ': complete 96x96 generated scenes; yellow box is supported scoring domain', fill='white')
    for i, (path, label) in enumerate(zip(paths, labels)):
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.suffix == '.npz':
            with np.load(path, allow_pickle=False) as archive:
                a = archive['pinhole_rgb'].copy()
        else:
            a = np.load(path, allow_pickle=False)
        assert a.shape == (96, 96, 3) and a.dtype == np.float32 and np.isfinite(a).all()
        v = np.arcsinh(np.maximum(a, 0)/np.float32(2048))/np.float32(np.arcsinh(32000/2048))
        pixels = np.rint(np.clip(v, 0, 1)*255).astype(np.uint8)
        im = Image.fromarray(pixels).resize((384, 384), Image.Resampling.NEAREST)
        x, y = 8+i*400, 52
        canvas.paste(im, (x, y))
        draw.text((x, 31), label, fill='white')
        draw.rectangle((x+64, y+64, x+319, y+319), outline='#ffe080', width=1)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before
        records.append(dict(path=str(path), sha256=before))
    canvas.save(args.out / ('complete-' + case + '.png'))
(args.out / 'sources.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
