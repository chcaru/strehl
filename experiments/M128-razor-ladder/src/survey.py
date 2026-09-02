"""M-PHASE0-EDGE / survey — are the razor captures a usable slanted-edge target?

Reconnaissance, not a claim-bearing measurement. For each stack it reports, per
sampled frame and per ROI:

  - the fitted edge angle from the nearest sensor axis (M88 s8 wants 3-7 deg),
  - the straightness residual of the edge locus after a linear fit,
  - the 10-90% rise distance in green-plane px, model-free,
  - bright/dark plateau levels, contrast, and whether either is clipped.

Edge location is a 50%-crossing per scanline, not a gradient argmax: the blade
carries etched text, wax globs and scratches whose gradients exceed the edge's in
places, and a gradient argmax over the whole frame locks onto those instead (it
did, on the first attempt).

Rule 32: `raw_image_visible` is a view into LibRaw's buffer. Copy inside the
`with`. Rule 7: never compute statistics over the padded decode buffer.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rawpy

CONTAINER_MAX_DN = 16383.0


def read_green(path):
    """Return (G1, G2, black, white, meta) as f32 planes, black-subtracted."""
    with rawpy.imread(str(path)) as raw:
        vis = raw.raw_image_visible.astype(np.float32)
        pattern = raw.raw_pattern.copy()
        black = float(np.mean(raw.black_level_per_channel))
        white = float(raw.white_level)
    greens = []
    for r in range(2):
        for c in range(2):
            if pattern[r, c] == 1:
                greens.append(vis[r::2, c::2])
    if len(greens) != 2:
        raise SystemExit(f"expected 2 green sublattices, got {len(greens)}")
    g1 = np.maximum(greens[0] - black, 0.0)
    g2 = np.maximum(greens[1] - black, 0.0)
    return g1, g2, black, white, dict(clip_dn=CONTAINER_MAX_DN - black)


def edge_locus(a, band_lo, band_hi, bright_first):
    """50%-crossing index per column, within [band_lo, band_hi) of axis 0."""
    sub = a[band_lo:band_hi, :]
    n = sub.shape[0]
    k = max(4, n // 4)
    top = np.median(sub[:k, :], axis=0)
    bot = np.median(sub[-k:, :], axis=0)
    hi = top if bright_first else bot
    lo = bot if bright_first else top
    mid = 0.5 * (hi + lo)

    xs, ys = [], []
    for x in range(sub.shape[1]):
        if hi[x] - lo[x] < 50.0:
            continue
        m = mid[x]
        prof = sub[:, x]
        hit = None
        if bright_first:
            for i in range(n - 1):
                if prof[i] >= m > prof[i + 1]:
                    hit = i + (prof[i] - m) / max(prof[i] - prof[i + 1], 1e-6)
                    break
        else:
            for i in range(n - 1, 0, -1):
                if prof[i] >= m > prof[i - 1]:
                    hit = i - (prof[i] - m) / max(prof[i] - prof[i - 1], 1e-6)
                    break
        if hit is not None:
            xs.append(x)
            ys.append(hit + band_lo)
    return np.asarray(xs, float), np.asarray(ys, float), hi, lo


def fit_line(x, y, iters=4, nsig=3.0):
    keep = np.ones(len(x), bool)
    p = np.polyfit(x, y, 1)
    for _ in range(iters):
        res = y - np.polyval(p, x)
        s = np.std(res[keep]) if keep.any() else 0.0
        if s <= 0:
            break
        nk = np.abs(res) <= nsig * s
        if nk.sum() < 32:
            break
        keep = nk
        p = np.polyfit(x[keep], y[keep], 1)
    res = y[keep] - np.polyval(p, x[keep])
    return p, float(np.std(res)), int(keep.sum()), keep


def rise_10_90(a, x, p, keep, bright_first, half=24):
    """Model-free 10-90% rise distance in px of axis 0.

    Registers every scanline on the fitted line, bins to 1/8 px, averages.
    """
    xs = x[keep]
    lines, offs = [], []
    h = a.shape[0]
    for xi in xs:
        yc = np.polyval(p, xi)
        i0 = int(np.floor(yc)) - half
        i1 = i0 + 2 * half
        if i0 < 0 or i1 >= h:
            continue
        lines.append(a[i0:i1, int(xi)])
        offs.append(np.arange(i0, i1) - yc)
    if len(lines) < 64:
        return None
    pos = np.concatenate(offs)
    val = np.concatenate(lines)
    if not bright_first:
        pos = -pos
    bin_w = 0.125
    nb = int(2 * half / bin_w)
    idx = np.floor((pos + half) / bin_w).astype(int)
    ok = (idx >= 0) & (idx < nb)
    sums = np.bincount(idx[ok], weights=val[ok], minlength=nb)
    cnts = np.bincount(idx[ok], minlength=nb)
    good = cnts >= 8
    if good.sum() < nb // 2:
        return None
    centres = (np.arange(nb) + 0.5) * bin_w - half
    esf, cc = sums[good] / cnts[good], centres[good]
    if (cc < -6).sum() < 4 or (cc > 6).sum() < 4:
        return None
    hi = float(np.median(esf[cc < -6]))
    lo = float(np.median(esf[cc > 6]))
    if hi - lo < 50:
        return None

    def cross(target):
        for i in range(len(esf) - 1):
            if esf[i] >= target > esf[i + 1]:
                t = (esf[i] - target) / max(esf[i] - esf[i + 1], 1e-9)
                return cc[i] + t * (cc[i + 1] - cc[i])
        return None

    a90 = cross(lo + 0.9 * (hi - lo))
    a10 = cross(lo + 0.1 * (hi - lo))
    if a90 is None or a10 is None:
        return None
    return dict(rise_px=float(a10 - a90), hi=hi, lo=lo, n_lines=len(lines))


def survey_frame(path, orient, band, rois, bright_first):
    g1, _g2, _black, _white, meta = read_green(path)
    a = g1 if orient == "h" else np.ascontiguousarray(g1.T)
    band_lo, band_hi = band
    out = []
    for (x0, x1) in rois:
        sl = np.ascontiguousarray(a[:, x0:x1])
        x, y, hi, lo = edge_locus(sl, band_lo, band_hi, bright_first)
        if len(x) < 64:
            out.append(dict(roi=[x0, x1], status=f"no edge (n={len(x)})"))
            continue
        p, resid, nkeep, keep = fit_line(x, y)
        rec = dict(roi=[x0, x1], angle_deg=float(np.degrees(np.arctan(p[0]))),
                   resid_px=resid, n=nkeep,
                   hi_dn=float(np.median(hi)), lo_dn=float(np.median(lo)),
                   clipped=bool(np.median(hi) >= meta["clip_dn"] - 1))
        r = rise_10_90(sl, x, p, keep, bright_first)
        if r:
            rec.update(rise_px=r["rise_px"], n_lines=r["n_lines"])
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stack")
    ap.add_argument("--orient", choices=["h", "v"], required=True,
                    help="h: edge runs left-right; v: edge runs top-bottom")
    ap.add_argument("--bright-first", action="store_true",
                    help="bright side is at low index along the scan axis")
    ap.add_argument("--band", nargs=2, type=int, required=True)
    ap.add_argument("--rois", nargs="+", type=int, required=True,
                    help="flat pairs x0 x1 x0 x1 ... along the edge")
    ap.add_argument("--frames", nargs="+", type=int, default=None)
    ap.add_argument("--every", type=int, default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    arws = sorted(Path(args.stack).glob("*.ARW"))
    if not arws:
        raise SystemExit(f"no ARW under {args.stack}")
    if args.frames:
        picks = [arws[i] for i in args.frames if i < len(arws)]
    elif args.every:
        picks = arws[::args.every]
    else:
        picks = arws
    rois = list(zip(args.rois[0::2], args.rois[1::2]))

    print(f"# {Path(args.stack).name}  {len(arws)} frames, sampling {len(picks)}")
    results = []
    for f in picks:
        recs = survey_frame(f, args.orient, tuple(args.band), rois, args.bright_first)
        i = arws.index(f)
        parts = []
        for r in recs:
            r["frame"] = f.name
            r["index"] = i
            if "rise_px" in r:
                parts.append(f"x{r['roi'][0]}: ang {r['angle_deg']:+.3f} "
                             f"res {r['resid_px']:.3f} rise {r['rise_px']:6.3f} "
                             f"hi {r['hi_dn']:5.0f}{' CLIP' if r['clipped'] else ''}")
            else:
                parts.append(f"x{r['roi'][0]}: {r.get('status', 'no rise')}")
        results.extend(recs)
        print(f"  [{i:3d}] {f.name}  " + "  |  ".join(parts))
        sys.stdout.flush()
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(results, indent=1))
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
