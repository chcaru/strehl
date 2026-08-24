"""ORCH: is the lateral-CA correction better or worse as a function of field height?

Hypothesis under test (SYNTHESIS fact 1501): M107's radial CA fit is supported only
over r = 0.208..0.788; the corner is a 1.27x linear extrapolation. If the correction
over-extrapolates, the ON arm should IMPROVE fringing inside the support and DEGRADE
it outside.

Design notes, in the project's idiom:

  * Window SELECTION is done on the OFF arm only. Selection can therefore not favour
    either arm. (If we picked the windows using ON, we would be choosing the places
    where ON happens to look good.)
  * The r = 0 bin is the NULL: lateral CA is zero at the optical centre BY CONSTRUCTION
    (the model is a pure function of field height, vanishing at r = 0). If the metric
    moves there, the metric is measuring something other than lateral CA and every
    other number in the table is suspect.
  * The TIFF layout is READ FROM THE TAGS, not assumed, then memory-mapped.

This is a rough instrument written in one sitting. It has a null but no positive
control, so it can show a difference and cannot yet prove it could see a difference
of a stated size. Treat every number as ARGUED-with-a-measurement, not SETTLED.
"""

import json
import os
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

R1 = r"C:\dev\strehl-out\M114-ca-verify\r1"
OUT = r"C:\dev\strehl-out\ORCH-ca-radial"

WIN = 192          # window edge, px
EDGE_PCTL = 98.0   # keep the top 2% of |grad G| as "edge pixels"
MIN_EDGE_PX = 400  # a window with fewer edge pixels than this is not evidence
MIN_EDGE_ENERGY = 60.0  # mean |grad G| in DN; below this the window is flat and the
                        # fringe statistic is measuring noise rather than an edge

# (label, r_lo, r_hi) in normalised field height; 1.0 == half the sensel diagonal,
# matching crates/strehl-core/src/optics.rs:138-139. The bins straddle the fit's
# outer support boundary at 0.788 deliberately: that is the hypothesis under test.
BINS = [
    ("r0.04 NULL", 0.00, 0.09),
    ("r0.20     ", 0.16, 0.24),
    ("r0.35     ", 0.31, 0.39),
    ("r0.50     ", 0.46, 0.54),
    ("r0.65     ", 0.61, 0.69),
    ("r0.75 IN  ", 0.72, 0.785),
    ("r0.83 OUT ", 0.79, 0.87),
    ("r0.93 OUT ", 0.89, 0.97),
]

SUPPORT_HI = 0.788  # optics.rs:315-318 -- outer two annuli empty


def load_tiff_u16(path):
    """Return (H, W, 3) uint16 via the tags, not via an assumed layout."""
    im = Image.open(path)
    t = im.tag_v2
    w, h = im.size
    bits = t[258]
    bits = tuple(bits) if isinstance(bits, (tuple, list)) else (bits,)
    spp = t.get(277, len(bits))
    compression = t.get(259, 1)
    planar = t.get(284, 1)
    offsets = t[273]
    rows_per_strip = t.get(278, h)
    if set(bits) != {16}:
        raise SystemExit("expected 16 bits/sample, tags say %r" % (bits,))
    if spp != 3:
        raise SystemExit("expected 3 samples/pixel, tags say %r" % (spp,))
    if compression != 1:
        raise SystemExit("expected uncompressed, tags say compression=%r" % compression)
    if planar != 1:
        raise SystemExit("expected chunky planar config, tags say %r" % planar)
    if len(offsets) == 1:
        off = int(offsets[0])
    else:
        # Striped. Do not ASSUME the strips are laid out back-to-back -- check it,
        # then treat the run as one block. A gap or an out-of-order strip would make
        # a flat memmap silently return scrambled rows.
        counts = t.get(279, None)
        offs = [int(o) for o in offsets]
        row_bytes = w * 3 * 2
        exp = []
        pos = offs[0]
        for i in range(len(offs)):
            exp.append(pos)
            rows_i = min(rows_per_strip, h - i * rows_per_strip)
            pos += rows_i * row_bytes
        if offs != exp:
            bad = next(i for i in range(len(offs)) if offs[i] != exp[i])
            raise SystemExit("strips are not contiguous; first gap at strip %d "
                             "(offset %d, expected %d)" % (bad, offs[bad], exp[bad]))
        if counts is not None:
            tot = sum(int(c) for c in counts)
            if tot != h * row_bytes:
                raise SystemExit("strip byte counts sum to %d, expected %d"
                                 % (tot, h * row_bytes))
        off = offs[0]
    need = off + w * h * 3 * 2
    have = os.path.getsize(path)
    if have < need:
        raise SystemExit("file is %d bytes, pixel block needs %d" % (have, need))
    slack = have - need
    a = np.memmap(path, dtype="<u2", mode="r", offset=off, shape=(h, w, 3))
    print("  %s: %dx%d u16x3, pixels at byte %d, %d strips, %d bytes of tags"
          % (os.path.basename(path), w, h, off, len(offsets), slack))
    return a, w, h


def grad_mag(g):
    gy = np.zeros_like(g)
    gx = np.zeros_like(g)
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    return np.hypot(gx, gy)


def fringe(win):
    """Lateral-CA fringe statistics on the edge pixels of one HxWx3 uint16 window."""
    f = win.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    gm = grad_mag(g)
    thr = np.percentile(gm, EDGE_PCTL)
    m = gm >= max(thr, 1e-6)
    n = int(m.sum())
    if n < MIN_EDGE_PX:
        return None
    rg = r[m] - g[m]
    bg = b[m] - g[m]
    # Lateral CA displaces R and B in OPPOSITE directions about the green edge, so the
    # (R-G) and (B-G) residuals are anti-correlated. A pure colour cast is not.
    denom = float(np.sqrt((rg * rg).mean() * (bg * bg).mean())) + 1e-9
    return {
        "n_edge": n,
        "abs_rg": float(np.abs(rg).mean()),
        "abs_bg": float(np.abs(bg).mean()),
        "amp": float((np.abs(rg).mean() + np.abs(bg).mean()) / 2.0),
        "opposition": float((rg * bg < 0).mean()),
        "corr": float((rg * bg).mean() / denom),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    off, W, H = load_tiff_u16(os.path.join(R1, "off.tif"))
    on, W2, H2 = load_tiff_u16(os.path.join(R1, "on.tif"))
    if (W, H) != (W2, H2):
        raise SystemExit("arm geometry differs")
    cx, cy = W / 2.0, H / 2.0
    half_diag = float(np.hypot(cx, cy))
    print("geometry %dx%d  centre (%.1f, %.1f)  half-diagonal %.1f px"
          % (W, H, cx, cy, half_diag))
    print("CA fit support r = 0.208..%.3f (optics.rs:315-318)\n" % SUPPORT_HI)

    rows = []
    for label, lo, hi in BINS:
        # Measure EVERY in-bounds window around the ring, not one hand-picked window.
        # A single window per radius is n=1 and cannot separate a radial trend from
        # the scene content that happens to sit at that angle.
        deltas, corr_off, corr_on, opp_off, opp_on = [], [], [], [], []
        best = None
        rmid = 0.5 * (lo + hi)
        for k in range(180):
            th = 2.0 * np.pi * k / 180.0
            px = cx + rmid * half_diag * np.cos(th)
            py = cy + rmid * half_diag * np.sin(th)
            x0 = int(round(px - WIN / 2.0))
            y0 = int(round(py - WIN / 2.0))
            if x0 < 0 or y0 < 0 or x0 + WIN > W or y0 + WIN > H:
                continue
            w_off = np.asarray(off[y0:y0 + WIN, x0:x0 + WIN, :])
            g = w_off[..., 1].astype(np.float32)
            gm = grad_mag(g)
            score = float(gm.mean())
            if score < MIN_EDGE_ENERGY:
                continue  # flat window: the statistic would be noise, not a fringe
            rr = np.hypot(x0 + WIN / 2.0 - cx, y0 + WIN / 2.0 - cy) / half_diag
            if not (lo <= rr <= hi):
                continue
            w_on = np.asarray(on[y0:y0 + WIN, x0:x0 + WIN, :])
            s_off = fringe(w_off)
            s_on = fringe(w_on)
            if s_off is None or s_on is None:
                continue
            deltas.append(100.0 * (s_on["amp"] - s_off["amp"]) / (s_off["amp"] + 1e-9))
            corr_off.append(s_off["corr"])
            corr_on.append(s_on["corr"])
            opp_off.append(s_off["opposition"])
            opp_on.append(s_on["opposition"])
            if best is None or score > best[0]:
                best = (score, x0, y0, rr, s_off, s_on)
        if best is None or len(deltas) < 3:
            print("%s : only %d usable windows in this ring -- not reporting"
                  % (label, len(deltas)))
            continue
        _, x0, y0, rr, s_off, s_on = best
        d_med = float(np.median(deltas))
        d_lo, d_hi = float(np.percentile(deltas, 25)), float(np.percentile(deltas, 75))
        worse = float(np.mean([1.0 if d > 0 else 0.0 for d in deltas]))
        side = "INSIDE " if rmid <= SUPPORT_HI else "OUTSIDE"
        rows.append(dict(label=label.strip(), r=rmid, side=side.strip(), n_win=len(deltas),
                         delta_med=d_med, delta_q1=d_lo, delta_q3=d_hi, frac_worse=worse,
                         corr_off=float(np.median(corr_off)), corr_on=float(np.median(corr_on)),
                         opp_off=float(np.median(opp_off)), opp_on=float(np.median(opp_on))))
        print("%s r~%.3f %s  n_windows=%3d" % (label, rmid, side, len(deltas)))
        print("        fringe amplitude   median %+7.2f%%   IQR [%+7.2f, %+7.2f]   worse in %.0f%% of windows"
              % (d_med, d_lo, d_hi, 100.0 * worse))
        print("        R/B correlation    OFF %+6.3f -> ON %+6.3f   (median; more negative = stronger CA signature)"
              % (np.median(corr_off), np.median(corr_on)))
        print("        R/B opposition     OFF %6.3f -> ON %6.3f" % (np.median(opp_off), np.median(opp_on)))

        w_off = np.asarray(off[y0:y0 + WIN, x0:x0 + WIN, :])
        w_on = np.asarray(on[y0:y0 + WIN, x0:x0 + WIN, :])

        # Side-by-side crop, IDENTICAL tone map for both arms (derived from OFF).
        lo_v = float(np.percentile(w_off, 1.0))
        hi_v = float(np.percentile(w_off, 99.5))
        if hi_v <= lo_v:
            hi_v = lo_v + 1.0
        def tone(a):
            v = (a.astype(np.float32) - lo_v) / (hi_v - lo_v)
            return np.clip(v, 0, 1) ** (1 / 2.2)
        pair = np.concatenate([tone(w_off), np.ones((WIN, 6, 3), np.float32), tone(w_on)], axis=1)
        img = Image.fromarray((pair * 255 + 0.5).astype(np.uint8), "RGB")
        img = img.resize((img.width * 3, img.height * 3), Image.NEAREST)
        name = "ca_r%03d_%s.png" % (round(rmid * 100), side.strip().lower())
        img.save(os.path.join(OUT, name))
        print("        wrote %s   (left = OFF, right = ON; strongest-edge window)\n" % name)

    with open(os.path.join(OUT, "ca_radial.json"), "w") as fh:
        json.dump(rows, fh, indent=2)

    print("=" * 88)
    print("%-12s %-7s %-9s %5s %11s %19s %8s" %
          ("bin", "r", "support", "n", "median d", "IQR", "worse"))
    for w in rows:
        print("%-12s %-7.3f %-9s %5d %10.2f%% [%+7.2f, %+7.2f]%%   %5.0f%%"
              % (w["label"], w["r"], w["side"], w["n_win"], w["delta_med"],
                 w["delta_q1"], w["delta_q3"], 100.0 * w["frac_worse"]))
    print("=" * 88)
    null = [w for w in rows if w["label"].startswith("r0.04")]
    if null:
        print("NULL CHECK  r=%.3f median delta = %+.2f%%, worse in %.0f%% of windows."
              % (null[0]["r"], null[0]["delta_med"], 100.0 * null[0]["frac_worse"]))
        print("            Lateral CA is zero at the optical centre BY CONSTRUCTION, so a")
        print("            large move here would invalidate every other row in the table.")


if __name__ == "__main__":
    sys.exit(main())
