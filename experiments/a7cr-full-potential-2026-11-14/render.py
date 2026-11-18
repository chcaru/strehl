"""Viewing renders: the shipped stack and prototype arms through one colour
and tone transform.

  python -X utf8 render.py WORK_DIR S0_DIR EVAL_DIR NATIVE_BINNED.tif LINEAR_SRGB_BINNED.tif OUT_DIR ARM[,ARM...]

The camera-to-sRGB matrix is not taken from metadata here: it is recovered
from the shipped stacker's own outputs, by least squares between its binned
camera-native TIFF and its binned --linear-srgb TIFF of the same stack (the
same pixels through the product's matrix), over unclipped pixels; the fit's
residual is printed. Every image then gets: per-channel gain to the shipped
camera-native units (prototype arms only, evaluate.py's gains), that matrix,
one exposure gain (the shipped full-resolution stack's 99.9th-percentile
luminance to 0.90, the product's --auto-exposure rule), and the sRGB curve.

Writes OUT_DIR/shipped-srgb.tif and OUT_DIR/ARM-srgb.tif (16-bit; prototype
arms cropped to the box every plane covers, the shipped image whole), and
1/4-scale JPEG previews. For looking at, not for measuring.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import fp

work, s0dir, evd = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
native_b, linear_b, out = Path(sys.argv[4]), Path(sys.argv[5]), Path(sys.argv[6])
arms = sys.argv[7].split(',')
out.mkdir(parents=True, exist_ok=True)
a = tifffile.imread(native_b).astype(np.float64)[::3, ::3].reshape(-1, 3)
b = tifffile.imread(linear_b).astype(np.float64)[::3, ::3].reshape(-1, 3)
ok = (a.max(1) < 60000) & (b.max(1) < 60000) & (b.min(1) > 0)
M, *_ = np.linalg.lstsq(a[ok], b[ok], rcond=None)   # b = a @ M
res = b[ok] - a[ok] @ M
print('camera-native -> linear sRGB matrix (rows are output channels):')
print(np.round(M.T, 4))
print('fit residual rms %.2f of 65535 over %d pixels' % (float(np.sqrt((res ** 2).mean())), int(ok.sum())))
Mt = torch.tensor(M.T, dtype=torch.float32, device=fp.DEV)
ev = json.loads((evd / 'evaluate.json').read_text())
LUMA = torch.tensor([0.2126, 0.7152, 0.0722], device=fp.DEV)
CLIP_DN = 15360.0 - 512.0


def encode(lin):
    lin = lin.clamp(0, 1)
    return torch.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin.clamp(min=1e-9) ** (1 / 2.4) - 0.055)


def save(name, rgb_native):
    """rgb_native: [3, h, w] in shipped camera-native 16-bit units."""
    lin = torch.einsum('oc,chw->ohw', Mt, rgb_native) / 65535.0 * exposure
    v = (encode(lin) * 65535 + 0.5).clamp(0, 65535).permute(1, 2, 0).cpu().numpy().astype(np.uint16)
    tifffile.imwrite(out / f'{name}-srgb.tif', v, photometric='rgb', compression='zlib')
    Image.fromarray((v[::4, ::4] >> 8).astype(np.uint8)).save(out / f'{name}-preview.jpg', quality=92)
    print('wrote', name, v.shape)


s0 = torch.from_numpy(tifffile.imread(s0dir / 'single.tif').astype(np.float32)).to(fp.DEV).permute(2, 0, 1)
lum = torch.einsum('c,chw->hw', LUMA, torch.einsum('oc,chw->ohw', Mt, s0[:, ::4, ::4])) / 65535.0
exposure = 0.90 / float(torch.quantile(lum.flatten()[::7], 0.999))
print('exposure gain %.3f (%.2f stops)' % (exposure, np.log2(exposure)))
save('shipped', s0)
del s0
for arm in arms:
    g = torch.tensor(ev['gain_to_s0'][arm] if arm in ev['gain_to_s0'] else next(iter(ev['gain_to_s0'].values())), device=fp.DEV)
    x = torch.from_numpy(np.load(work / 'fused' / f'{arm}-all.npy')).to(fp.DEV)
    # Clipped highlights: green clips first in the RAW, so after white balance
    # a clipped highlight would turn magenta. Above 75 % of green's clip level
    # red and blue are blended toward green's own level (neutral, same
    # brightness), fully by 95 %.
    m = ((x[1] - 0.75 * CLIP_DN) / (0.20 * CLIP_DN)).clamp(0, 1)
    m = m * m * (3 - 2 * m)
    x = x * g[:, None, None]
    white = float(g[1]) * CLIP_DN
    x = (1 - m) * x.clamp(max=white) + m * x[1].clamp(max=white)
    box = json.loads((work / 'fused' / 'f2-box.json').read_text())['box']
    save(arm, x[:, box[2]:box[3] + 1, box[0]:box[1] + 1])
    del x
(out / 'render.json').write_text(json.dumps({'matrix': M.T.tolist(), 'exposure_gain': exposure, 'arms': arms}) + '\n')
