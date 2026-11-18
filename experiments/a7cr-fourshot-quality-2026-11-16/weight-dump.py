"""R5: how many frames the default election averages into each coefficient.

  python -X utf8 weight-dump.py OUT.json PREFIX RENDER.tif

PREFIX is a `STREHL_PYRAMID_WEIGHT_DUMP` prefix (raw arrays per band on the
plane grid, half the output resolution at band 0): `neff` is the
participation ratio sum(w)^2 / sum(w^2) of the frame weights (NaN where the
noise gate admitted no frame and the merge took the plain mean of all
frames, counted here as the frame count), `arg` the winning frame.

RENDER is the render the dump came from; its green plane, reduced to each
band's grid, classifies coefficients:
  bright textured : level above the 40th percentile, local high-pass energy
                    in the top 30 % (the scoring tiles' kind of content)
  bright smooth   : level above the 40th percentile, energy in the bottom 30 %
  dark            : level below the 10th percentile
Reported per band and class: share averaged outright, median participation
ratio among selected coefficients, and the noise-equivalent frame count
1 / mean(1 / neff) over all coefficients of the class (independent equal
noise assumed; selection bias makes the true figure somewhat worse).

Control: a one-group render's dump must read 1 everywhere it selects.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch
import torch.nn.functional as F


def main():
    out, prefix, render = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    dims = json.loads(Path(prefix + '-dims.json').read_text())
    frames = dims['frames']
    g = torch.from_numpy(tifffile.imread(render)[..., 1].astype(np.float32)).cuda()[None, None]
    report = {'frames': frames, 'bands': []}
    print(f'{frames} frames')
    for b in dims['bands']:
        k, w, h = b['k'], b['w'], b['h']
        neff = np.fromfile(f'{prefix}-b{k}-neff.f32', dtype='<f4').reshape(h, w)
        arg = np.fromfile(f'{prefix}-b{k}-arg.i32', dtype='<i4').reshape(h, w)
        gk = F.interpolate(g, size=(h, w), mode='area')[0, 0]
        # local energy of this band's scale: value minus a 2 px Gaussian on this grid
        t = torch.arange(-7, 8, dtype=torch.float32, device=gk.device)
        kern = torch.exp(-0.5 * (t / 2.0) ** 2)
        kern = (kern / kern.sum())
        blur = F.conv2d(F.pad(gk[None, None], (7, 7, 0, 0), mode='reflect'), kern.view(1, 1, 1, -1))
        blur = F.conv2d(F.pad(blur, (0, 0, 7, 7), mode='reflect'), kern.view(1, 1, -1, 1))[0, 0]
        hp2 = (gk - blur) ** 2
        e = F.conv2d(F.pad(hp2[None, None], (7, 7, 0, 0), mode='reflect'), kern.view(1, 1, 1, -1))
        e = F.conv2d(F.pad(e, (0, 0, 7, 7), mode='reflect'), kern.view(1, 1, -1, 1))[0, 0]
        rel = (e / (blur.clamp(min=1.0) ** 2)).cpu().numpy()
        lvl = blur.cpu().numpy()
        bright = lvl > np.percentile(lvl, 40)
        classes = {
            'all': np.ones_like(bright),
            'bright textured': bright & (rel >= np.percentile(rel[bright], 70)),
            'bright smooth': bright & (rel <= np.percentile(rel[bright], 30)),
            'dark': lvl < np.percentile(lvl, 10),
        }
        averaged = ~np.isfinite(neff)
        n = np.where(averaged, float(frames), neff)
        rec = {'k': k, 'w': w, 'h': h, 'exponent': b['exponent'], 'classes': {}}
        line = []
        for name, m in classes.items():
            sel = m & ~averaged
            r = {'share_averaged': float(averaged[m].mean()),
                 'median_neff_selected': float(np.median(neff[sel])) if sel.any() else None,
                 'p10_p90_neff_selected': [float(v) for v in np.percentile(neff[sel], [10, 90])] if sel.any() else None,
                 'noise_equivalent_frames': float(1.0 / (1.0 / n[m]).mean())}
            rec['classes'][name] = r
            med = r['median_neff_selected']
            line.append(f"{name}: averaged {100 * r['share_averaged']:.1f} %, median {med if med is None else round(med, 2)}, "
                        f"noise-equivalent {r['noise_equivalent_frames']:.2f}")
        report['bands'].append(rec)
        print(f'band {k} ({w}x{h}, exponent {b["exponent"]}): ' + ';  '.join(line))
    out.write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
