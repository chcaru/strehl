"""Q2: the A7CR's pixel response non-uniformity, from fixed-focus bursts of a
defocused scene (calibration capture 1), exported by
`a7cr-export-members.exe RUN OUT` (single-shot planes, one raw frame each).

  python -X utf8 prnu.py OUT.json CACHE [CACHE ...] [--save-map MAP.npy]

Per run and CFA plane (R, G1, G2, B; plane px = 2 photosites), the mean of
the odd frames and of the even frames (each frame first scaled to the run's
mean level per plane: the lamp drifts 0.3-1.2 % frame to frame). Relative
high-pass residual r = M / gauss(M, sigma) - 1 for sigma in SIGMAS plane px.

  fixed pattern  cov0   = < r_odd r_even >                 (temporal noise is independent between halves)
  placebo        covR   = < r_odd roll(r_even, (5, 3)) >   (a white pattern vanishes; smooth scene leak and
                                                            dust do not)
  temporal       varT   = < (r_odd - r_even)^2 > / 4       (per-half-mean... of the full mean)

in bins of signal level. kappa = sqrt(cov0 - covR) is the white
(photosite-scale) response non-uniformity; cov0 against 1/S^2 separates an
offset pattern. The temporal term is checked against the injected model
(0.4040 DN/e-, 1.334 DN read): a wrong decode or scaling shows there first.

Also: the correlation of the pattern between horizontally adjacent
same-colour sites, and between the two greens of a cell, to say how white
the pattern is; and the same measurement on a dark series if given (no
signal: must show no multiplicative pattern).

With --save-map, the all-frames relative residual at the first sigma
(R, G1, G2, B planes, float16) of the LAST cache given is saved for the
stack checks.
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp

SIGMAS = (2.0, 4.0, 8.0)
GAIN, READ = 0.4040, 1.334
PLANES = ((0, 0, 'R'), (1, 0, 'G1'), (0, 1, 'G2'), (1, 1, 'B'))


def analyse(cache, save=None):
    run = fp.Run(cache)
    P = run.P
    n = len(run.planes)
    dev = fp.DEV
    sums = [torch.zeros(4, run.H // 2, run.W // 2, dtype=torch.float64, device=dev) for _ in range(2)]
    cnt = [0, 0]
    ref = None
    for i, p in enumerate(run.planes):
        m = run.members(p)[0, P:P + run.H, P:P + run.W]
        planes = torch.stack([m[dy::2, dx::2] for dx, dy, _ in PLANES]).double()
        lvl = planes.mean((1, 2), keepdim=True)
        if ref is None:
            ref = lvl.clone()
        sums[i % 2] += planes * (ref / lvl)
        cnt[i % 2] += 1
    Mo, Me = (sums[0] / cnt[0]).float(), (sums[1] / cnt[1]).float()
    Mall = ((sums[0] + sums[1]) / n).float()
    res = {'cache': str(cache), 'frames': n, 'planes': {}}
    levels = [50, 100, 200, 400, 800, 1600, 3200, 6400, 12000]
    for pi, (_, _, name) in enumerate(PLANES):
        out = {}
        for sigma in SIGMAS:
            so, se = fp.gauss(Mo[pi], sigma), fp.gauss(Me[pi], sigma)
            ro, re = Mo[pi] / so.clamp(min=1) - 1, Me[pi] / se.clamp(min=1) - 1
            S = 0.5 * (so + se)
            rows = []
            for lo, hi in zip(levels[:-1], levels[1:]):
                msk = (S >= lo) & (S < hi)
                msk[:16], msk[-16:], msk[:, :16], msk[:, -16:] = False, False, False, False
                k = int(msk.sum())
                if k < 200000:
                    continue
                a, b = ro[msk].double(), re[msk].double()
                br = torch.roll(re, (5, 3), (0, 1))[msk].double()
                cov0, covr = float((a * b).mean()), float((a * br).mean())
                vart = float(((a - b) ** 2).mean()) / 4
                s = float(S[msk].double().mean())
                model = (GAIN * s + READ ** 2) / n / s ** 2
                # neighbours: same colour one plane px to the right
                bn = torch.roll(re, -1, 1)[msk].double()
                rows.append({'level': s, 'sites': k, 'cov0': cov0, 'cov_rolled': covr, 'kappa_pct': 100 * float(np.sqrt(max(cov0 - covr, 0))),
                             'kappa_raw_pct': 100 * float(np.sqrt(max(cov0, 0))), 'temporal_over_model': vart / model,
                             'neighbour_corr': float((a * bn).mean()) / max(cov0, 1e-30)})
            out[str(sigma)] = rows
        res['planes'][name] = out
    # the two greens of a cell: is the pattern shared between adjacent sites?
    sg = SIGMAS[0]
    r1 = Mall[1] / fp.gauss(Mall[1], sg).clamp(min=1) - 1
    r2o = Mo[2] / fp.gauss(Mo[2], sg).clamp(min=1) - 1
    r1o = Mo[1] / fp.gauss(Mo[1], sg).clamp(min=1) - 1
    r1e = Me[1] / fp.gauss(Me[1], sg).clamp(min=1) - 1
    r2e = Me[2] / fp.gauss(Me[2], sg).clamp(min=1) - 1
    msk = fp.gauss(Mall[1], sg) > 400
    res['g1_g2_cross'] = float((r1o[msk].double() * r2e[msk].double()).mean()) / max(float((r1o[msk].double() * r1e[msk].double()).mean()), 1e-30)
    print(f'{Path(cache).name}: {n} frames')
    for name, out in res['planes'].items():
        for sigma, rows in out.items():
            print(f'  {name:2s} sigma {sigma:>4s}: ' + '  '.join(
                f'{r["level"]:.0f} DN: {r["kappa_pct"]:.3f}% (raw {r["kappa_raw_pct"]:.3f}%, T/model {r["temporal_over_model"]:.2f}, nb {r["neighbour_corr"]:+.2f})' for r in rows))
    print(f'  G1 pattern shared with G2 of the same cell: {res["g1_g2_cross"]:+.3f} of G1\'s own')
    if save:
        maps = torch.stack([Mall[i] / fp.gauss(Mall[i], SIGMAS[0]).clamp(min=1) - 1 for i in range(4)])
        halves = torch.stack([torch.stack([M[i] / fp.gauss(M[i], SIGMAS[0]).clamp(min=1) - 1 for i in range(4)]) for M in (Mo, Me)])
        np.save(save, maps.cpu().numpy().astype(np.float16))
        np.save(str(save).replace('.npy', '-halves.npy'), halves.cpu().numpy().astype(np.float16))
        np.save(str(save).replace('.npy', '-level.npy'), torch.stack([fp.gauss(Mall[i], SIGMAS[0]) for i in range(4)]).cpu().numpy().astype(np.float32))
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    save = sys.argv[sys.argv.index('--save-map') + 1] if '--save-map' in sys.argv else None
    if save:
        args.remove(save)
    out = Path(args[0])
    report = [analyse(c, save if c == args[-1] else None) for c in args[1:]]
    out.write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
