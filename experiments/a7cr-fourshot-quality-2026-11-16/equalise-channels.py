"""R10: bring red's and blue's contrast to green's with the per-channel
transfer measured on the neutral slide, and see what that does to the
colour of rims on the scarab.

  python -X utf8 equalise-channels.py OUT.tif IN.tif TRANSFER.json [--invert] [--max-gain 1.6] [--upto 0.30]

TRANSFER.json is channel-transfer.py's report (amplitude of red and blue
relative to green by frequency, magnitude form). Each of red and blue is
filtered by the radial gain 1 / ratio(f), linearly interpolated between the
report's bin centres, held at 1 below the first bin, tapered back to 1 from
`upto` to `upto` + 0.1 cycles/px (above about 0.3 the red ratio is not a
clean transfer: it contains the displaced green-band share), and capped at
--max-gain. Green is untouched. One full-frame FFT per channel.

--invert applies ratio(f) instead (placebo: rims must get worse).

This is a linear filter per channel: it changes noise by the same gain.
The slide was lit by room light and sits at one focus position; the ratios
are borrowed, not measured on the scarab's own light.
"""
import json
import sys

import numpy as np
import tifffile
import torch


def arg(name, default=None):
    for i, tok in enumerate(sys.argv):
        if tok == name:
            return sys.argv[i + 1]
    return default


def main():
    dst, src, tr = sys.argv[1], sys.argv[2], json.loads(open(sys.argv[3]).read())
    invert = '--invert' in sys.argv
    cap, upto = float(arg('--max-gain', '1.6')), float(arg('--upto', '0.30'))
    dev = torch.device('cuda')
    img = torch.from_numpy(tifffile.imread(src).astype(np.float32)).to(dev)
    H, W, _ = img.shape
    fy = torch.fft.fftfreq(H, device=dev)[:, None]
    fx = torch.fft.rfftfreq(W, device=dev)[None, :]
    fr = torch.sqrt(fx * fx + fy * fy).cpu().numpy()
    centres = np.array(tr['centres'])
    taper = np.clip((upto + 0.1 - fr) / 0.1, 0.0, 1.0)
    out = img.clone()
    for c, name in ((0, 'R'), (2, 'B')):
        ratio = np.array(tr['channels'][name]['magnitude_vs_green'])
        r = np.interp(fr, np.r_[0.0, centres], np.r_[1.0, ratio])
        gain = np.clip(r if invert else 1.0 / r, 1.0 / cap, cap)
        gain = 1.0 + (gain - 1.0) * taper
        g = torch.from_numpy(gain.astype(np.float32)).to(dev)
        out[..., c] = torch.fft.irfft2(torch.fft.rfft2(img[..., c]) * g, s=(H, W))
        print(f'{name}: gain at 0.05 / 0.10 / 0.15 / 0.20 / 0.30 cycles/px: '
              + ' / '.join(f'{float(np.interp(f, fr[0], gain[0])):.3f}' for f in (0.05, 0.10, 0.15, 0.20, 0.30)))
    tifffile.imwrite(dst, out.clamp(0, 65535).round().cpu().numpy().astype(np.uint16))
    print('wrote', dst, '(placebo: inverted)' if invert else '')


if __name__ == '__main__':
    with torch.no_grad():
        main()
