"""Q2: the sensor-fixed pattern in the stack's own raw frames, by scale, and
whether a flat taken on another day predicts it.

  python -X utf8 fpn-raw.py OUT.json STACK_CACHE PTC_CACHE [--planes A,B,C,D] [--group N] [--apply MAP.npy [--roll]]

--apply (round 2) divides every stack raw frame by 1 + MAP ([4, H/2, W/2]
relative response, R G1 G2 B) before the means are formed: what a flat-field
correction with that map leaves. --roll rolls the map (5, 3) plane px
(placebo: a wrong map must add pattern, not remove it). --select-raw chooses
the smooth tiles on the uncorrected means, so a map that adds structure
somewhere cannot drop those tiles from its own score.

STACK_CACHE: a four-shot run exported by a7cr-export-members (every member is
a full raw frame in sensor coordinates; the sensor moves, the photosite
indices do not). PTC_CACHE: a fixed-focus burst of a defocused scene from
another session (prnu.py's input).

Stack means: for each listed plane, the mean of that plane's and the next
N-1 planes' members (4N raw frames, each scaled to a common level per CFA
plane). The listed planes are far apart in focus, so the scene differs
between them and only what is fixed to the sensor (or to the optics) is
common. PTC means: odd and even frames.

Per CFA plane and high-pass scale sigma (plane px; r = M / gauss(M, sigma) - 1),
over 64 x 64 plane-px tiles that are bright and smooth in BOTH means (tile
variance of r under 1.5x the tile median, so in-focus texture is excluded):

  stack-stack   < r_A r_B >        the pattern common to two focus positions
  placebo       < r_A roll(r_B) >  (rolled 11, 7 plane px: must vanish)
  ptc-ptc       < r_odd r_even >   the same on the other day's burst, same tiles
  stack-ptc     < r_A r_ptc >      what the other day's flat predicts

Reported as amplitudes in percent of level, and the stack-ptc correlation
stack-ptc / sqrt(stack-stack x ptc-ptc): near 1 means one stored flat serves
later sessions; lower means part of the pattern (dust, or the optics) moved.

Fooled by: scene structure that is the same at both focus positions and
survives the smooth-tile test (a defocused background gradient passes the
high-pass only weakly; the placebo roll removes what is smooth).
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp

SIGMAS = (1.0, 2.0, 4.0, 8.0)
PLANES = ((0, 0, 'R'), (1, 0, 'G1'), (0, 1, 'G2'), (1, 1, 'B'))
TILE = 64


def cfa_planes(m):
    return torch.stack([m[dy::2, dx::2] for dx, dy, _ in PLANES]).double()


def stack_mean(run, first, group, flat=None):
    acc, n, ref = None, 0, None
    for p in range(first, first + group):
        mem = run.members(p)[:, run.P:run.P + run.H, run.P:run.P + run.W]
        for k in range(mem.shape[0]):
            pl = cfa_planes(mem[k])
            if flat is not None:
                pl = pl / (1.0 + flat)
            lvl = pl.mean((1, 2), keepdim=True)
            ref = lvl if ref is None else ref
            acc = pl * (ref / lvl) if acc is None else acc + pl * (ref / lvl)
            n += 1
    return (acc / n).float(), n


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    planes = [int(v) for v in sys.argv[sys.argv.index('--planes') + 1].split(',')] if '--planes' in sys.argv else [20, 70, 120, 170]
    group = int(sys.argv[sys.argv.index('--group') + 1]) if '--group' in sys.argv else 4
    apply = sys.argv[sys.argv.index('--apply') + 1] if '--apply' in sys.argv else None
    roll = '--roll' in sys.argv
    for flag in ('--planes', '--group', '--apply'):
        if flag in sys.argv:
            args.remove(sys.argv[sys.argv.index(flag) + 1])
    out, stack_cache, ptc_cache = Path(args[0]), args[1], args[2]
    run, ptc = fp.Run(stack_cache), fp.Run(ptc_cache)
    dev = fp.DEV
    means = []
    flat = None
    if apply:
        flat = torch.from_numpy(np.load(apply).astype(np.float32)).to(dev).double()
        if roll:
            flat = torch.roll(flat, (5, 3), (1, 2))
        print(f'dividing every stack frame by 1 + {apply}' + (' rolled (5, 3) plane px (placebo)' if roll else ''))
    select_raw = '--select-raw' in sys.argv and flat is not None
    raw_means = []
    for p in planes:
        m, n = stack_mean(run, p, group, flat)
        means.append(m)
        if select_raw:
            raw_means.append(stack_mean(run, p, group, None)[0])
        print(f'stack plane {p}..{p + group - 1}: {n} raw frames, G1 mean {float(m[1].mean()):.0f} DN')
    sums = [None, None]
    cnt = [0, 0]
    ref = None
    for i, p in enumerate(ptc.planes):
        pl = cfa_planes(ptc.members(p)[0, ptc.P:ptc.P + ptc.H, ptc.P:ptc.P + ptc.W])
        lvl = pl.mean((1, 2), keepdim=True)
        ref = lvl if ref is None else ref
        sums[i % 2] = pl * (ref / lvl) if sums[i % 2] is None else sums[i % 2] + pl * (ref / lvl)
        cnt[i % 2] += 1
    Po, Pe = (sums[0] / cnt[0]).float(), (sums[1] / cnt[1]).float()
    Pall = 0.5 * (Po + Pe)
    print(f'ptc: {cnt[0] + cnt[1]} frames, G1 mean {float(Pall[1].mean()):.0f} DN')
    pairs = [(i, j) for i in range(len(planes)) for j in range(i + 1, len(planes))]
    report = {'planes': planes, 'group': group, 'results': {}}

    def resid(M, sigma):
        return M / fp.gauss(M, sigma).clamp(min=1) - 1

    def tile_mean(x):
        return F.avg_pool2d(x[None, None], TILE)[0, 0]

    for pi, (_, _, name) in enumerate(PLANES):
        rows = {}
        for sigma in SIGMAS:
            rs = [resid(m[pi], sigma) for m in means]
            rs_sel = [resid(m[pi], sigma) for m in raw_means] if select_raw else rs
            rp_o, rp_e, rp = resid(Po[pi], sigma), resid(Pe[pi], sigma), resid(Pall[pi], sigma)
            acc = {'ss': 0.0, 'pl': 0.0, 'pp': 0.0, 'sp': 0.0, 'tiles': 0, 'level': 0.0}
            for i, j in pairs:
                a, b = rs[i], rs[j]
                la, lb = tile_mean(means[i][pi]), tile_mean(means[j][pi])
                va, vb = tile_mean(rs_sel[i] * rs_sel[i]), tile_mean(rs_sel[j] * rs_sel[j])
                bright = (la > 1500) & (lb > 1500) & (tile_mean(Pall[pi]) > 300)
                # smooth: tile variance below 1.5x the median of bright tiles, in both
                ok = bright & (va < 1.5 * va[bright].median()) & (vb < 1.5 * vb[bright].median())
                ok[:2], ok[-2:], ok[:, :2], ok[:, -2:] = False, False, False, False
                k = int(ok.sum())
                if k < 50:
                    continue
                acc['ss'] += float(tile_mean(a * b)[ok].sum())
                acc['pl'] += float(tile_mean(a * torch.roll(b, (11, 7), (0, 1)))[ok].sum())
                acc['pp'] += float(tile_mean(rp_o * rp_e)[ok].sum())
                acc['sp'] += float(0.5 * (tile_mean(a * rp)[ok].sum() + tile_mean(b * rp)[ok].sum()))
                acc['level'] += float(0.5 * (la[ok].sum() + lb[ok].sum()))
                acc['tiles'] += k
            t = max(acc['tiles'], 1)
            ss, pl, pp, sp = acc['ss'] / t, acc['pl'] / t, acc['pp'] / t, acc['sp'] / t
            amp = lambda v: 100 * float(np.sign(v) * np.sqrt(abs(v)))
            rows[str(sigma)] = {'tiles': acc['tiles'], 'level_dn': acc['level'] / t, 'stack_stack_pct': amp(ss), 'placebo_pct': amp(pl),
                                'ptc_ptc_pct': amp(pp), 'stack_ptc_pct': amp(sp),
                                'cross_session_correlation': sp / np.sqrt(max(ss * pp, 1e-30))}
        report['results'][name] = rows
        for sigma, r in rows.items():
            print(f'{name:2s} sigma {sigma:>3s} plane px: {r["tiles"]:5d} tile-pairs at {r["level_dn"]:.0f} DN; stack-stack {r["stack_stack_pct"]:.3f} % '
                  f'(placebo {r["placebo_pct"]:+.3f} %), ptc-ptc {r["ptc_ptc_pct"]:.3f} %, stack-ptc {r["stack_ptc_pct"]:.3f} %, '
                  f'cross-session correlation {r["cross_session_correlation"]:.3f}')
    out.write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
