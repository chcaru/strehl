"""M-PHASE0-EDGE / geom — edge geometry census across the razor captures.

For each sampled frame and ROI this reports the quantities M88 s8 named as the
acceptance conditions for a slanted-edge target:

  angle_deg   fitted slant from the nearest sensor axis
  res1_px     RMS residual of the edge locus about a straight line
  res3_px     RMS residual about a cubic (lens distortion bends a straight edge)
  contrast    bright plateau minus dark floor, DN
  clip_frac   fraction of ROI samples at the container ceiling
  rise_px     model-free 10-90% rise, green-plane px, wing-ramp removed

Edge location is a 50%-crossing against plateaus read far from the edge. On this
subject the mid level (~1550 DN) sits far above the veiling-flare shoulder on the
dark side (~500 DN peak), so the crossing is unambiguous; a gradient argmax is
not, and locks onto the bevel boundary or the etched text instead.

The cubic is a pre-registered order: with ~1e3 crossings a 4-parameter fit
absorbs negligible degrees of freedom and so cannot sharpen the ESF, while a
high-order fit could. Order is fixed at 3 and reported either way.

Rule 32: `raw_image_visible` is a view into LibRaw's buffer; copy inside the
`with`. Rule 7: statistics are taken over the visible area only.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rawpy

CONTAINER_MAX_DN = 16383.0
POLY_ORDER = 3


def read_greens(path):
    """G1, G2 sublattices, black-subtracted.

    `color_desc` is b'RGBG' on Sony: pattern value 1 is the first green and
    value 3 is the second. Matching only value 1 finds a single plane.
    """
    with rawpy.imread(str(path)) as raw:
        vis = raw.raw_image_visible.astype(np.float32)
        pattern = raw.raw_pattern.copy()
        desc = raw.color_desc
        black = float(np.mean(raw.black_level_per_channel))
    g = []
    for r in range(2):
        for c in range(2):
            if desc[pattern[r, c]:pattern[r, c] + 1] == b"G":
                g.append(np.maximum(vis[r::2, c::2] - black, 0.0))
    if len(g) != 2:
        raise SystemExit(f"expected 2 green sublattices, got {len(g)} "
                         f"(pattern {pattern.tolist()}, desc {desc})")
    return g[0], g[1], black


def orient(a, mode):
    """Return the plane with the scan axis (edge normal) as axis 0."""
    if mode == "h":
        return a
    return np.ascontiguousarray(a.T)


def find_band(a):
    """Coarse [lo, hi) rows bracketing the strongest bright->dark step."""
    p = np.median(a, axis=1)
    n = len(p)
    k = 8
    sm = np.convolve(p, np.ones(k) / k, mode="same")
    row = int(np.argmin(np.diff(sm[k:n - k]))) + k
    return max(row - 220, 0), min(row + 220, n), row


def crossings(a, b0, b1, bright_first):
    """Sub-pixel 50%-crossing per column within [b0, b1)."""
    sub = a[b0:b1, :]
    n = sub.shape[0]
    q = max(6, n // 6)
    first = np.percentile(sub[:q, :], 50, axis=0)
    last = np.percentile(sub[-q:, :], 50, axis=0)
    hi = first if bright_first else last
    lo = last if bright_first else first
    mid = 0.5 * (hi + lo)

    xs, ys = [], []
    for x in range(sub.shape[1]):
        if hi[x] - lo[x] < 300.0:
            continue
        prof = sub[:, x] if bright_first else sub[::-1, x]
        m = mid[x]
        idx = np.nonzero((prof[:-1] >= m) & (prof[1:] < m))[0]
        if len(idx) != 1:
            continue                      # ambiguous column: text, glob, glare
        i = int(idx[0])
        t = (prof[i] - m) / max(prof[i] - prof[i + 1], 1e-6)
        pos = i + t
        if not bright_first:
            pos = (n - 1) - pos
        xs.append(x)
        ys.append(pos + b0)
    return np.asarray(xs, float), np.asarray(ys, float), hi, lo


def fit_poly(x, y, order, iters=4, nsig=3.0):
    keep = np.ones(len(x), bool)
    xn = (x - x.mean()) / max(x.std(), 1e-9)
    p = np.polyfit(xn, y, order)
    for _ in range(iters):
        res = y - np.polyval(p, xn)
        s = float(np.std(res[keep])) if keep.any() else 0.0
        if s <= 0:
            break
        nk = np.abs(res) <= nsig * s
        if nk.sum() < 64:
            break
        keep = nk
        p = np.polyfit(xn[keep], y[keep], order)
    res = y[keep] - np.polyval(p, xn[keep])
    return p, xn, float(np.sqrt(np.mean(res ** 2))), keep


def esf(a, x, ycurve, keep, bright_first, half=32, bin_w=0.125):
    xs = x[keep].astype(int)
    yc = ycurve[keep]
    lines, offs = [], []
    h = a.shape[0]
    for xi, y0 in zip(xs, yc):
        i0 = int(np.floor(y0)) - half
        i1 = i0 + 2 * half
        if i0 < 0 or i1 >= h:
            continue
        lines.append(a[i0:i1, xi])
        offs.append(np.arange(i0, i1) - y0)
    if len(lines) < 128:
        return None
    pos = np.concatenate(offs)
    val = np.concatenate(lines)
    if not bright_first:
        pos = -pos
    nb = int(2 * half / bin_w)
    idx = np.floor((pos + half) / bin_w).astype(int)
    ok = (idx >= 0) & (idx < nb)
    s = np.bincount(idx[ok], weights=val[ok], minlength=nb)
    c = np.bincount(idx[ok], minlength=nb)
    good = c >= 16
    cc = ((np.arange(nb) + 0.5) * bin_w - half)[good]
    ee = s[good] / c[good]
    return cc, ee, len(lines)


def rise_from_esf(cc, ee, far=14.0):
    """10-90% rise with the dark-side veiling ramp removed by a linear deramp."""
    lm = cc < -far
    rm = cc > far
    if lm.sum() < 8 or rm.sum() < 8:
        return None
    # deramp the dark side: fit a line to the far tail and subtract its
    # extrapolation from the whole ESF, so the flare wing does not move the
    # 10% level. M88 added `deramp_esf` for the same reason.
    q = np.polyfit(cc[rm], ee[rm], 1)
    base = np.polyval(q, cc)
    lvl_hi = float(np.median(ee[lm] - base[lm]))
    flat = ee - base
    lo_lvl = 0.0
    if lvl_hi <= 50:
        return None

    def cross(frac):
        t = lo_lvl + frac * (lvl_hi - lo_lvl)
        for i in range(len(flat) - 1):
            if flat[i] >= t > flat[i + 1]:
                u = (flat[i] - t) / max(flat[i] - flat[i + 1], 1e-9)
                return float(cc[i] + u * (cc[i + 1] - cc[i]))
        return None

    a90, a10 = cross(0.9), cross(0.1)
    if a90 is None or a10 is None:
        return None
    return dict(rise_px=a10 - a90, esf_hi=lvl_hi,
                ramp_dn_per_px=float(q[0]))


def do_frame(path, mode, bright_first, rois, band=None):
    g1, _g2, black = read_greens(path)
    a = orient(g1, mode)
    ceiling = CONTAINER_MAX_DN - black
    if band is None:
        b0, b1, _ = find_band(a)
    else:
        b0, b1 = band
    out = []
    for (x0, x1) in rois:
        sl = np.ascontiguousarray(a[:, x0:x1])
        x, y, hi, lo = crossings(sl, b0, b1, bright_first)
        rec = dict(roi=[x0, x1], band=[b0, b1], n_cross=int(len(x)),
                   n_cols=int(x1 - x0))
        if len(x) < 128:
            rec["status"] = "too few clean columns"
            out.append(rec)
            continue
        p1, xn1, r1, k1 = fit_poly(x, y, 1)
        p3, xn3, r3, k3 = fit_poly(x, y, POLY_ORDER)
        rec.update(angle_deg=float(np.degrees(np.arctan(
                       np.polyfit(x[k1], y[k1], 1)[0]))),
                   res1_px=r1, res3_px=r3, n_keep=int(k3.sum()),
                   hi_dn=float(np.median(hi)), lo_dn=float(np.median(lo)),
                   contrast_dn=float(np.median(hi) - np.median(lo)))
        core = sl[b0:b1, :]
        rec["clip_frac"] = float(np.mean(core >= ceiling - 0.5))
        e = esf(sl, x, np.polyval(p3, xn3), k3, bright_first)
        if e:
            cc, ee, nl = e
            r = rise_from_esf(cc, ee)
            if r:
                rec.update(rise_px=r["rise_px"], esf_hi=r["esf_hi"],
                           ramp=r["ramp_dn_per_px"], n_lines=nl)
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stack")
    ap.add_argument("--orient", choices=["h", "v"], required=True)
    ap.add_argument("--bright-first", action="store_true")
    ap.add_argument("--rois", nargs="+", type=int, required=True)
    ap.add_argument("--band", nargs=2, type=int, default=None)
    ap.add_argument("--frames", nargs="+", type=int, default=None)
    ap.add_argument("--every", type=int, default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    arws = sorted(Path(args.stack).glob("*.ARW"))
    if not arws:
        raise SystemExit(f"no ARW under {args.stack}")
    if args.frames:
        picks = [(i, arws[i]) for i in args.frames if i < len(arws)]
    elif args.every:
        picks = list(enumerate(arws))[::args.every]
    else:
        picks = list(enumerate(arws))
    rois = list(zip(args.rois[0::2], args.rois[1::2]))

    print(f"# {Path(args.stack).name}: {len(arws)} frames, sampling {len(picks)}, "
          f"{len(rois)} ROI(s), poly order {POLY_ORDER}")
    results = []
    for i, f in picks:
        recs = do_frame(f, args.orient, args.bright_first, rois, args.band)
        parts = []
        for r in recs:
            r["frame"] = f.name
            r["index"] = i
            if "rise_px" in r:
                parts.append(
                    f"x{r['roi'][0]}: ang {r['angle_deg']:+.4f} "
                    f"r1 {r['res1_px']:.3f} r3 {r['res3_px']:.3f} "
                    f"rise {r['rise_px']:6.3f} ctr {r['contrast_dn']:5.0f} "
                    f"clip {100 * r['clip_frac']:.3f}% n {r['n_keep']}")
            else:
                parts.append(f"x{r['roi'][0]}: {r.get('status', 'no esf')} "
                             f"({r['n_cross']}/{r['n_cols']} cols)")
        results.extend(recs)
        print(f"  [{i:3d}] {f.name}  " + "  |  ".join(parts))
        sys.stdout.flush()
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(results, indent=1))
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
