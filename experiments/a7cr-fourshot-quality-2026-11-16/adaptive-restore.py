"""R6: does a locally adaptive restoration beat the global filter?

  python -X utf8 adaptive-restore.py OUT.json MERGE_ODD.tif MERGE_EVEN.tif RESTORED_ODD.tif RESTORED_EVEN.tif [--write PREFIX]

The restoration is one linear filter per channel. Where a neighbourhood
holds no detail above noise its gain only amplifies noise. Post-merge
prototype: with D = restored - merge (what the restoration adds),

    adaptive = merge + m D,    m = max(0, 1 - 1 / z)

z being the local energy of D over its noise energy (Gaussian sigma 3 px,
pooled over the three channels; 1 for pure noise), so m is the Wiener
weight signal / (signal + noise) of the increment. The noise energy of D is
taken from the half-stack difference, as a constant times the local level
per channel (shot noise), fitted over the frame.

Arms: `self` (m from the scored half), `cross` (m from the other half: no
selection bias, and in a product the mask would come from the full stack),
`one` (m = 1: must equal the global restoration).

Classes from the even merge (green, smoothed): bright textured (local
high-pass energy in the top 30 % of bright pixels), bright smooth (bottom
30 %), dark (level under the 10th percentile).

Per arm and class, green and the three-channel mean:
  noise     var(arm_odd - arm_even) / var(restored_odd - restored_even)
  error     [mean((arm_odd - restored_even)^2) - N] / N, N the restored
            half's own noise variance: the arm's mean squared error against
            the fully restored scene, in units of the global restoration's
            noise (1 = as good as the global filter, under 1 = better)
  kept      mean(D_arm_odd D_even) / mean(D_odd D_even): share of the
            restoration's noise-free increment the arm keeps

Fooled by: `self` masks follow the noise they gate (the `cross` arm bounds
it); the classes come from the even half, so even-half noise enters the
class choice, the same for every arm.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp


def main():
    out = Path(sys.argv[1])
    dev = fp.DEV

    def load(f):
        return torch.from_numpy(tifffile.imread(f).astype(np.float32)).to(dev).permute(2, 0, 1)

    Mo, Me, Ro, Re = (load(f) for f in sys.argv[2:6])
    Do, De = Ro - Mo, Re - Me
    # noise energy of D per channel: k_c * level
    lvl = [fp.gauss(0.5 * (Mo[c] + Me[c]), 3.0).clamp(min=50.0) for c in range(3)]
    k = [float((((Do[c] - De[c]) ** 2) / 2 / lvl[c]).mean()) for c in range(3)]
    print('noise of the restoration increment, variance per unit level (R, G, B): ' + ' '.join(f'{v:.3f}' for v in k))

    def mask(D):
        z = sum(fp.gauss(D[c] ** 2, 3.0) / (k[c] * lvl[c]) for c in range(3)) / 3.0
        return (1.0 - 1.0 / z.clamp(min=1e-6)).clamp(0.0, 1.0)

    mo, me = mask(Do), mask(De)
    arms = {
        'one (control)': (Mo + Do, Me + De),
        'self': (Mo + mo * Do, Me + me * De),
        'cross': (Mo + me * Do, Me + mo * De),
    }
    g = fp.gauss(Me[1], 2.0)
    hp = fp.gauss((Me[1] - g) ** 2, 4.0) / g.clamp(min=50.0) ** 2
    gl = g.flatten()[::97]
    bright = g > torch.quantile(gl, 0.40)
    hb = hp[bright].flatten()[::97]
    classes = {
        'bright textured': bright & (hp >= torch.quantile(hb, 0.70)),
        'bright smooth': bright & (hp <= torch.quantile(hb, 0.30)),
        'dark': g < torch.quantile(gl, 0.10),
        'all': torch.ones_like(bright),
    }
    report = {'noise_k': k, 'mask_mean': {}, 'arms': {}}
    for cname, cm in classes.items():
        report['mask_mean'][cname] = float(mo[cm].mean())
    print('mean mask by class: ' + ', '.join(f'{c}: {v:.3f}' for c, v in report['mask_mean'].items()))
    for name, (ao, ae) in arms.items():
        rec = {}
        for cname, cm in classes.items():
            row = {}
            for label, chans in (('G', [1]), ('RGB', [0, 1, 2])):
                noise, err, kept = [], [], []
                for c in chans:
                    n_ref = float(((Ro[c] - Re[c])[cm] ** 2).mean()) / 2
                    noise.append(float(((ao[c] - ae[c])[cm] ** 2).mean()) / 2 / n_ref)
                    e = 0.5 * (float(((ao[c] - Re[c])[cm] ** 2).mean()) + float(((ae[c] - Ro[c])[cm] ** 2).mean())) - n_ref
                    err.append(e / n_ref)
                    num = 0.5 * (float(((ao[c] - Mo[c]) * De[c])[cm].mean()) + float(((ae[c] - Me[c]) * Do[c])[cm].mean()))
                    kept.append(num / float((Do[c] * De[c])[cm].mean()))
                row[label] = {'noise': float(np.mean(noise)), 'error': float(np.mean(err)), 'kept': float(np.mean(kept))}
            rec[cname] = row
        report['arms'][name] = rec
        print(f'{name:14s} ' + ';  '.join(f'{cname}: noise {row["G"]["noise"]:.3f}, error {row["G"]["error"]:.3f}, kept {row["G"]["kept"]:.3f} (RGB {row["RGB"]["noise"]:.3f}/{row["RGB"]["error"]:.3f}/{row["RGB"]["kept"]:.3f})'
                                          for cname, row in rec.items()))
    out.write_text(json.dumps(report, indent=1) + '\n')
    if '--write' in sys.argv:
        prefix = sys.argv[sys.argv.index('--write') + 1]
        ao = arms['cross'][0]
        tifffile.imwrite(prefix + '-cross-odd.tif', ao.clamp(0, 65535).round().permute(1, 2, 0).cpu().numpy().astype(np.uint16))
        tifffile.imwrite(prefix + '-mask.tif', (me * 65535).round().cpu().numpy().astype(np.uint16))
        print('wrote', prefix + '-cross-odd.tif')


if __name__ == '__main__':
    with torch.no_grad():
        main()
