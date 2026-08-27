r"""Is there a PERIODIC TILE GRID in the master that the source frames do not have?

The 460-px contact sheets from vr_novel.py show a faint blocky texture in the
master's band-pass panel (112MSDCF, coffee-bubbles). The merge stages that could
make one are tiled: outlier.rs uses tile:32 in eleven places, align.rs uses
coarse_tile 32 / fine_tile 128. So this asks the question numerically.

STATISTIC.  On the gate's own flattest 900x900 window, take the mean absolute
first difference along x (and y), averaged over all 900 rows (columns), divided
by the window mean:  g(x) = <|L[y,x+1]-L[y,x]|>_y / <L>.  Random subject edges
average away; a seam that repeats every p pixels does not.  For each candidate
pitch p and phase phi, comb(p,phi) = mean of g over x = phi (mod p); the score
is max_phi comb / median(g).  A field with no grid scores ~1.

THIS TEST CAN FAIL, three ways:
  NULL      the same scan on a randomly permuted profile, 200 draws.  The
            reported score must beat the 99.5th percentile of that null or it
            is not a detection.  (Scanning 150 pitches x many phases for a
            maximum is a multiple-comparison machine; this prices it in.)
  POSITIVE  --plant A injects a real p=32 seam grid of amplitude A*mean into
            the master window.  The scan must return p=32 and rise with A.
  CONTROLS  the same scan on (a) the strehl single-frame render, which passes
            through the pyramid but has NO election and NO outlier stage, and
            (b) a rawpy linear decode, which touches no strehl code at all.

  python vr_grid.py SUBJECT [--frame=K] [--plant=0.001] [--pmax=160]
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
from orch_blotch import boxblur, LO_R, HI_R                   # noqa: E402

PMIN, PMAXD = 8, 160


def profile(L, axis):
    """Mean |first difference| along `axis`, averaged over the other axis."""
    d = np.abs(np.diff(L.astype(np.float64), axis=axis))
    g = d.mean(axis=1 - axis)
    return g / max(float(np.mean(L)), 1e-12)


def comb(g, p):
    n = len(g)
    rows = int(np.ceil(n / p))
    pad = np.full(rows * p, np.nan)
    pad[:n] = g
    m = np.nanmean(pad.reshape(rows, p), axis=0)
    phi = int(np.argmax(m))
    return float(m[phi] / max(float(np.median(g)), 1e-12)), phi


def scan(g, pmax):
    out = [(comb(g, p)[0], p, comb(g, p)[1]) for p in range(PMIN, pmax + 1)]
    out.sort(reverse=True)
    return out


def null(g, pmax, trials=200, seed=7):
    rng = np.random.default_rng(seed)
    return np.array([scan(rng.permutation(g), pmax)[0][0] for _ in range(trials)])


def report(tag, L, pmax, nulls=True):
    line = []
    for axis, nm in ((1, "x"), (0, "y")):
        g = profile(L, axis)
        top = scan(g, pmax)
        s, p, phi = top[0]
        if nulls:
            nl = null(g, pmax)
            thr = float(np.percentile(nl, 99.5))
            verdict = "DETECT" if s > thr else "none"
        else:
            thr, verdict = float("nan"), ""
        line.append("%s: best p=%3d phase=%3d score=%.4f  null99.5=%.4f  %s"
                    % (nm, p, phi, s, thr, verdict))
        line.append("      runners-up " + ", ".join("p=%d:%.3f" % (q, v)
                                                    for v, q, _ in top[1:5]))
    print("%-34s %s" % (tag, line[0]))
    for l in line[1:]:
        print("%-34s %s" % ("", l))
    return line


def plant_grid(L, amp, p=32):
    """A real seam grid: every p-th row and column steps by amp*mean."""
    m = float(np.mean(L))
    out = L.astype(np.float32).copy()
    step = np.zeros(L.shape[1], np.float32)
    step[::p] = 1.0
    out += (amp * m) * step[None, :]
    step2 = np.zeros(L.shape[0], np.float32)
    step2[::p] = 1.0
    out += (amp * m) * step2[:, None]
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1")
                for a in sys.argv[1:] if a.startswith("--"))
    subj = args[0]
    pmax = int(opts.get("pmax", PMAXD))
    import json
    with open(os.path.join(V.OUT, "source_%s.json" % subj)) as fh:
        S = json.load(fh)
    wy, wx = S["master"]["blotch"]["y"], S["master"]["blotch"]["x"]
    W = V.BWIN
    m = V.lum_of(V.read_rgb(V.master_path(subj)))[wy:wy + W, wx:wx + W]
    print("SUBJECT %s   window (%d,%d) %dx%d   mean %.1f DN" % (subj, wy, wx, W, W, m.mean()))
    report("MASTER", m, pmax)

    if "plant" in opts:
        for a in [float(x) for x in opts["plant"].split(",")]:
            report("  +PLANTED p=32 amp=%.4f" % a, plant_grid(m, a), pmax, nulls=(a == 0))
        return

    k = int(opts.get("frame", S["rows"][0]["frame"]))
    ok = [r for r in S["rows"] if r["state"] == "OK"]
    if "frame" not in opts and ok:
        k = sorted(ok, key=lambda r: -r["blotch"])[0]["frame"]
    tif = os.path.join(V.OUT, "%s--grid-f%04d.tiff" % (subj, k))
    if not os.path.exists(tif):
        V.render_frame(subj, k, tif)
    import vr_reg2 as R
    ks = 1.0
    lg = tif + ".log"
    src = V.lum_of(V.read_rgb(tif))
    km = R.master_cover(subj)
    A, d = R.register_best(V.lum_of(V.read_rgb(V.master_path(subj))), src, km / ks, wy, wx, W)
    # UNWARPED: take the source window in the SOURCE's own pixel grid, so no
    # interpolation can smear or invent a grid.  A maps master->source coords.
    cy, cx = A[:, :2] @ np.array([wy + W / 2, wx + W / 2])[::-1][::-1] + 0, 0
    pt = A @ np.array([wx + W / 2, wy + W / 2, 1.0])
    sx, sy = int(round(pt[0] - W / 2)), int(round(pt[1] - W / 2))
    sx = max(0, min(src.shape[1] - W, sx))
    sy = max(0, min(src.shape[0] - W, sy))
    print("  source frame %d, same scene window at (%d,%d) in its OWN grid (ncc %.3f)"
          % (k, sy, sx, d["ncc_context"]))
    report("SINGLE-FRAME RENDER f%d" % k, src[sy:sy + W, sx:sx + W], pmax)
    os.remove(tif)

    try:
        import rawpy
        raws = V.raw_paths(subj)
        with rawpy.imread(raws[k]) as rp:
            rgb = rp.postprocess(gamma=(1, 1), no_auto_bright=True, output_bps=16,
                                 use_camera_wb=True)
        rl = V.lum_of(rgb.astype(np.float32))
        h, w = rl.shape
        fy = int(sy * h / src.shape[0])
        fx = int(sx * w / src.shape[1])
        fy = max(0, min(h - W, fy))
        fx = max(0, min(w - W, fx))
        report("RAWPY LINEAR f%d (no strehl)" % k, rl[fy:fy + W, fx:fx + W], pmax)
    except Exception as e:
        print("  rawpy control unavailable: %r" % (e,))


if __name__ == "__main__":
    main()
