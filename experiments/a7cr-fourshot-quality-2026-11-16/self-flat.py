"""R1 and R2: a response map from the stack's own raw frames, and the stack's
exposure.

  python -X utf8 self-flat.py OUT.json STACK_CACHE BURST_MAP.npy [--sigma 2] [--gate 1.25]
                              [--save MAP.npy] [--limit N] [--planes A-B] [--min-samples 50]
                              [--pattern KR,KG1,KG2,KB]

--soft replaces the hard gate by weights 1 / (local energy seen), so textured
samples count little instead of not at all and no threshold sits on the
pattern's own energy.

--pattern adds the pattern's own variance (kappa per plane, fraction of
level) to the energy the gate expects: without it a bright smooth area,
where the pattern is a quarter of the noise energy, sits at the threshold
and is mostly rejected.

--planes builds the map from part of the stack only, so that fpn-raw.py
--apply can test it on raw frames it has not seen (far enough in focus that
no scene detail is shared).

STACK_CACHE: a four-shot run exported by a7cr-export-members (every member is
a raw frame in sensor coordinates). BURST_MAP.npy: prnu.py --save-map's
response map from a defocused burst of another scene on another day
([4, H/2, W/2] R, G1, G2, B relative residual at the same sigma; its
`-halves.npy` and `-level.npy` are read beside it).

Self map. For every raw frame and CFA plane: r = M / gauss(M, sigma) - 1.
A photosite's samples are kept where the frame is locally smooth: the local
energy gauss(r^2, 4) at most `gate` times the injected noise model's value
there (0.4040 DN/e-, 1.334 DN; the high-pass's own factor included), the
level above 150 DN and no sample within 12 plane px above 13 500 DN. Kept
samples are averaged with inverse-variance weights. Odd planes and even
planes are accumulated apart: two maps with independent photon noise.

Scores, per CFA plane, over photosites with at least 100 kept samples, by
radius zone (the scene barely moves on the sensor near the centre, so scene
detail would survive there first):
  self-self   cov(odd, even)                 pattern (plus anything else fixed to the sensor frame in both)
  burst-burst cov(burst odd, burst even)     the other day's pattern, same photosites
  self-burst  cov(self all, burst all)       what the two share
  placebo     cov(roll(self all, (5, 3)), burst all)
  correlation self-burst / sqrt(self-self x burst-burst)
  slope       self-burst / burst-burst       1 = the self map has the pattern at full size
  left        1 - 2 self-burst / burst-burst + var(self all) / burst-burst
              the share of the pattern's power that dividing by the self map
              would leave, counting the self map's own noise and any scene it
              absorbed (an upper bound: the burst is a day older than the stack)
The same `left` for the stored burst map applied to this stack is
1 - correlation_stack_burst^2 plus the burst map's noise (round 1: about a tenth).

Exposure (R2). Histogram of every raw sample of the stack per CFA colour:
percentiles, and the share above 9 500 DN (where the photon-transfer slope
starts to fall) and above 95 % of white.

Fooled by: scene detail that stays on the same photosites in most frames and
passes the smoothness gate (the radius zones and the correlation with the
burst expose it); a gate that follows noise (it removes high-|r| samples and
would shrink the map: the slope exposes it).
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp

GAIN, READ = 0.4040, 1.334
PLANES = ((0, 0, 'R'), (1, 0, 'G1'), (0, 1, 'G2'), (1, 1, 'B'))
WHITE_DN = 14848.0


def arg(name, default=None):
    for i, tok in enumerate(sys.argv):
        if tok == name:
            return sys.argv[i + 1]
        if tok.startswith(name + '='):
            return tok.split('=', 1)[1]
    return default


def main():
    out, cache, burst = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    sigma, gate = float(arg('--sigma', '2')), float(arg('--gate', '1.25'))
    limit = int(arg('--limit', '0'))
    min_samples = int(arg('--min-samples', '50'))
    soft = '--soft' in sys.argv
    pattern_var = [float(v) ** 2 for v in arg('--pattern', '0,0,0,0').split(',')]
    run = fp.Run(cache)
    dev = fp.DEV
    P, H, W = run.P, run.H, run.W
    h, w = H // 2, W // 2
    # high-pass factor on white noise: 1 - 2 k0 + sum k^2 for the 2-D Gaussian
    t = torch.arange(-int(np.ceil(3.5 * sigma)), int(np.ceil(3.5 * sigma)) + 1, dtype=torch.float64)
    k1 = torch.exp(-0.5 * (t / sigma) ** 2)
    k1 /= k1.sum()
    hp = float(1 - 2 * k1.max() ** 2 + (k1 ** 2).sum() ** 2)
    num = torch.zeros(2, 4, h, w, device=dev)
    den = torch.zeros(2, 4, h, w, device=dev)
    cnt = torch.zeros(2, 4, h, w, device=dev, dtype=torch.int16)
    hist = torch.zeros(4, 512, dtype=torch.float64, device=dev)
    kept = [0.0, 0.0]
    planes = run.planes[:limit] if limit else run.planes
    if arg('--planes'):
        lo_p, hi_p = (int(v) for v in arg('--planes').split('-'))
        planes = [p for p in planes if lo_p <= p <= hi_p]
    frames = 0
    for p in planes:
        mem = run.members(p)[:, P:P + H, P:P + W]
        half = p % 2
        for k in range(mem.shape[0]):
            frames += 1
            for pi, (dx, dy, _) in enumerate(PLANES):
                M = mem[k, dy::2, dx::2]
                hist[pi] += torch.histc(M.clamp(-512, WHITE_DN + 511), bins=512, min=-512.0, max=WHITE_DN + 512.0).double()
                s = fp.gauss(M, sigma).clamp(min=1.0)
                r = M / s - 1.0
                v = (GAIN * s + READ ** 2) / (s * s) * hp
                e = fp.gauss(r * r, 4.0)
                ev = fp.gauss(v, 4.0)
                near_clip = torch.nn.functional.max_pool2d(M[None, None], 25, 1, 12)[0, 0] > 13500.0
                if soft:
                    # no hard gate: every sample weighted by the inverse of the local energy actually seen
                    # (noise, pattern and whatever scene detail is there), never above the model's weight
                    ok = (s > 150.0) & ~near_clip
                    wt = ok.float() / (torch.maximum(e, ev) / hp)
                else:
                    ok = (e <= gate * (ev + pattern_var[pi] * hp)) & (s > 150.0) & ~near_clip
                    wt = ok.float() / v
                num[half, pi] += wt * r
                den[half, pi] += wt
                cnt[half, pi] += ok.to(torch.int16)
                kept[0] += float(ok.float().mean())
                kept[1] += 1.0
        del mem
        if p % 20 == 0:
            print(f'plane {p}: {frames} raw frames, kept share so far {kept[0] / kept[1]:.3f}', flush=True)
    self_h = num / den.clamp(min=1e-20)
    self_all = (num[0] + num[1]) / (den[0] + den[1]).clamp(min=1e-20)
    n_all = (cnt[0].int() + cnt[1].int())
    bmap = torch.from_numpy(np.load(burst).astype(np.float32)).to(dev)
    bh = torch.from_numpy(np.load(burst.replace('.npy', '-halves.npy')).astype(np.float32)).to(dev)
    blevel = torch.from_numpy(np.load(burst.replace('.npy', '-level.npy')).astype(np.float32)).to(dev)
    yy = (torch.arange(h, device=dev).float() - (h - 1) / 2)[:, None]
    xx = (torch.arange(w, device=dev).float() - (w - 1) / 2)[None, :]
    rad = torch.sqrt(xx * xx + yy * yy) / float(np.hypot(h / 2, w / 2))
    zones = [(0.0, 0.1), (0.1, 0.3), (0.3, 0.6), (0.6, 1.01), (0.0, 1.01)]
    report = {'frames': frames, 'sigma': sigma, 'gate': gate, 'kept_share': kept[0] / kept[1], 'planes': {}, 'exposure': {}}
    edges = torch.linspace(-512.0, WHITE_DN + 512.0, 513, dtype=torch.float64)
    centres = (0.5 * (edges[:-1] + edges[1:])).numpy()
    for pi, (_, _, name) in enumerate(PLANES):
        hcum = (hist[pi] / hist[pi].sum()).cumsum(0).cpu().numpy()
        pct = {q: float(centres[np.searchsorted(hcum, q / 100)]) for q in (50, 90, 99, 99.9, 99.99, 99.999)}
        above = lambda dn: float(hist[pi][torch.from_numpy(centres > dn)].sum() / hist[pi].sum())
        report['exposure'][name] = {'percentiles_dn': pct, 'share_above_9500': above(9500.0), 'share_above_95pct_white': above(0.95 * WHITE_DN)}
        print(f'{name:2s} raw exposure: p50 {pct[50]:.0f}, p99 {pct[99]:.0f}, p99.9 {pct[99.9]:.0f}, p99.99 {pct[99.99]:.0f}, p99.999 {pct[99.999]:.0f} DN of {WHITE_DN:.0f}; '
              f'above 9500 DN {100 * above(9500.0):.4f} %, above 95 % of white {100 * above(0.95 * WHITE_DN):.5f} %')
    for pi, (_, _, name) in enumerate(PLANES):
        rows = {}
        for lo, hi in zones:
            msk = (rad >= lo) & (rad < hi) & (cnt[0, pi] >= min_samples) & (cnt[1, pi] >= min_samples) & (blevel[pi] > 300)
            msk[:16], msk[-16:], msk[:, :16], msk[:, -16:] = False, False, False, False
            k = int(msk.sum())
            if k < 10000:
                continue
            so, se, sa = self_h[0, pi][msk].double(), self_h[1, pi][msk].double(), self_all[pi][msk].double()
            bo, be, ba = bh[0, pi][msk].double(), bh[1, pi][msk].double(), bmap[pi][msk].double()
            c_ss, c_bb, c_sb = float((so * se).mean()), float((bo * be).mean()), float((sa * ba).mean())
            c_pl = float((torch.roll(self_all[pi], (5, 3), (0, 1))[msk].double() * ba).mean())
            var_s = float((sa * sa).mean())
            noise_s = float(((so - se) ** 2).mean()) / 4
            rows[f'{lo}-{hi}'] = {
                'photosites': k, 'share_of_zone': k / int(((rad >= lo) & (rad < hi)).sum()),
                'median_samples': float(n_all[pi][msk].float().median()),
                'self_self_pct': 100 * float(np.sign(c_ss) * np.sqrt(abs(c_ss))), 'burst_burst_pct': 100 * float(np.sqrt(max(c_bb, 0))),
                'self_burst_pct': 100 * float(np.sign(c_sb) * np.sqrt(abs(c_sb))), 'placebo_pct': 100 * float(np.sign(c_pl) * np.sqrt(abs(c_pl))),
                'correlation': c_sb / np.sqrt(max(c_ss * c_bb, 1e-30)), 'slope': c_sb / c_bb,
                'self_noise_pct': 100 * float(np.sqrt(noise_s)), 'left': 1 - 2 * c_sb / c_bb + var_s / c_bb}
        report['planes'][name] = rows
        for z, r in rows.items():
            print(f'{name:2s} zone {z:9s}: {r["photosites"]:9d} sites ({100 * r["share_of_zone"]:.0f} %), median {r["median_samples"]:.0f} samples; '
                  f'self-self {r["self_self_pct"]:.3f} %, burst-burst {r["burst_burst_pct"]:.3f} %, self-burst {r["self_burst_pct"]:.3f} % '
                  f'(placebo {r["placebo_pct"]:+.3f} %); correlation {r["correlation"]:.3f}, slope {r["slope"]:.3f}, '
                  f'self-map noise {r["self_noise_pct"]:.3f} %, pattern power left {r["left"]:.3f}')
    out.write_text(json.dumps(report, indent=1) + '\n')
    save = arg('--save')
    if save:
        np.save(save, self_all.cpu().numpy().astype(np.float16))
        np.save(save.replace('.npy', '-halves.npy'), self_h.cpu().numpy().astype(np.float16))
        np.save(save.replace('.npy', '-count.npy'), n_all.cpu().numpy().astype(np.int16))
        # the accumulators themselves, so that shrunk maps can be formed without another pass (self-flat-shrink.py)
        np.save(save.replace('.npy', '-num.npy'), (num[0] + num[1]).cpu().numpy())
        np.save(save.replace('.npy', '-den.npy'), (den[0] + den[1]).cpu().numpy())


if __name__ == '__main__':
    with torch.no_grad():
        main()
