"""Whole generated scenes under the fixed optical-output display; no scoring."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('free_display_optical', HERE / 'in-focus-controls.py')
optical = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = optical
spec.loader.exec_module(optical)
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
source, out = args.source.resolve(), args.out.resolve()
assert out.is_relative_to(HERE) and not out.exists()
out.mkdir()
records = []
for case in ('flat', 'layered', 'far-only', 'angular-mismatch'):
    folder = HERE / 'screen-1/output' / case
    paths = [folder / 'truth-rgb-f32.npy', source / case / 'original/in-focus-rgb-f32.npy',
             source / case / 'matrix/in-focus-rgb-f32.npy', folder / 'mean-rgb-f32.npy']
    labels = ('in-focus truth', 'free visibility, original Huber', 'free visibility, matrix', 'observed mean (unchanged)')
    canvas = Image.new('RGB', (1600, 448), '#202124')
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 10), case + ': complete 96x96 generated scenes; yellow box is supported domain; not photographs', fill='white')
    for index, (path, label) in enumerate(zip(paths, labels)):
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        array = np.load(path, allow_pickle=False)
        assert array.shape == (96, 96, 3) and array.dtype == np.float32 and np.isfinite(array).all()
        if index == 0:
            array = optical.optical(array)
        value = np.arcsinh(np.maximum(array, 0)/np.float32(2048))/np.float32(np.arcsinh(32000/2048))
        pixels = np.rint(np.clip(value, 0, 1)*255).astype(np.uint8)
        panel = Image.fromarray(pixels).resize((384, 384), Image.Resampling.NEAREST)
        x, y = 8 + index*400, 52
        canvas.paste(panel, (x, y))
        draw.text((x, y-21), label, fill='white')
        draw.rectangle((x+64, y+64, x+319, y+319), outline='#ffe080', width=1)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before
        records.append(dict(path=str(path), sha256=before))
    canvas.save(out / ('complete-' + case + '.png'))
(out / 'sources.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
