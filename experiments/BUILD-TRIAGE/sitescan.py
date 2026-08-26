"""Through-focus response at an EXACT merge pixel coordinate.

ORCH's decisive question, per site rather than per subject:

    at a site where the merge is soft, is ANY source frame sharp there?

      no frame is sharp there  -> capture-limited.  No merge can invent it.
      a frame IS sharp and the merge is soft -> merge-limited, and a violation
      of the never-worse-than-a-single-frame invariant.

This script answers ONLY the capture half, and it answers it without the merge
being involved at all.  Every frame goes through one identical decode path
(rawpy CFA green plane, black-subtracted, no demosaic, no white balance, no
matrix), so frame-versus-frame numbers are inside a single transformation and
are safe to compare.  The merge lives in a different space (linear sRGB through
the renderer) and its sharpness is NEVER compared numerically against these
values -- that comparison belongs to compare.py, which renders both arms
through the same binary and self-calibrates the alignment gather.

Locating the site is itself a cross-transformation step and is therefore
verified rather than assumed: the merge window is matched into the frame by
normalised cross-correlation over an offset and scale search, and the achieved
NCC is reported with every site.  A site that does not land above --min-ncc is
a hard error, because a probe that quietly measures the wrong 128 px of a
7040 px frame returns a confident number about nothing.

Curve shapes, and what each means:

    peak well inside the bracket, falls off both sides
        the capture resolved this site.  Ask the merge question next.
    response still climbing at an end of the bracket
        COVERAGE GAP.  The true optimum lies outside what was shot, and the
        end it is climbing towards is the end to extend.
    flat and low everywhere
        no frame ever held detail here.  Either there is no detail to hold
        (smooth subject) or the optics did not deliver it.  Not a merge defect.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import rawpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402

HALF_G = 64        # half-window in raw-green px  (= 128 merge px)
SEARCH_G = 96      # NCC offset search radius, raw-green px
SCALES = (0.96, 0.97, 0.98, 0.99, 1.00, 1.01)
MIN_NCC = 0.45


def green_plane(path: str) -> np.ndarray:
    """One frame's CFA green plane in DN, black-subtracted. No demosaic/WB/matrix."""
    with rawpy.imread(path) as r:
        cfa = r.raw_image_visible
        pat = r.raw_pattern
        black = float(np.mean(r.black_level_per_channel))
        ys, xs = np.where(pat == 1)
        g = np.zeros((cfa.shape[0] // 2, cfa.shape[1] // 2), np.float32)
        for y, x in zip(ys, xs):
            g += cfa[y::2, x::2].astype(np.float32)
        g = g / len(ys) - black
    return np.maximum(g, 0.0)


def hf_rms(win: np.ndarray) -> float:
    """Laplacian RMS in DN. Same estimator focuscurve.py uses, same units."""
    lap = (4.0 * win[1:-1, 1:-1] - win[:-2, 1:-1] - win[2:, 1:-1]
           - win[1:-1, :-2] - win[1:-1, 2:])
    return float(np.sqrt(np.mean(lap.astype(np.float64) ** 2)))


def hf_rel(win: np.ndarray) -> float:
    """Laplacian RMS divided by the window's own mean level. Dimensionless.

    THIS is the quantity the curve is classified on, and the reason is a
    measured property of this corpus rather than a preference: `flowers-cpl`
    brightens monotonically by 19.1% from its first frame to its last (1573.7
    -> 1874.1 DN, no reversal anywhere). Laplacian RMS in DN scales with
    signal level, so that exposure ramp alone manufactures a 19% rising
    through-focus response with no change in focus whatsoever -- which reads as
    "still climbing at the last frame", the exact signature of a coverage gap.
    Normalising by the window's own mean removes both that global drift and the
    local brightness difference between a dark sharp feature and a bright
    smooth one. C16 is the control that proves it.

    Absolute DN is still recorded alongside for every site: a ratio hides an
    additive bias, and this project has been bitten by that before.
    """
    m = float(np.mean(win.astype(np.float64)))
    return hf_rms(win) / max(m, 1.0)


def ncc(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(np.float64) - a.mean()
    b = b.astype(np.float64) - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d > 0 else 0.0


def locate(merge_y: np.ndarray, g: np.ndarray, x: int, y: int,
           half: int, search: int) -> dict:
    """Find merge pixel (x,y) inside the raw green plane. Verified by NCC.

    The merge is full sensor resolution and the green plane is half, so the
    nominal map is a factor of two; the residual is the alignment crop, which
    is why a small scale search is included rather than assumed away.
    """
    hm, wm = merge_y.shape
    hg, wg = g.shape
    m2 = 0.25 * (merge_y[0:2 * (hm // 2):2, 0:2 * (wm // 2):2]
                 + merge_y[1:2 * (hm // 2):2, 0:2 * (wm // 2):2]
                 + merge_y[0:2 * (hm // 2):2, 1:2 * (wm // 2):2]
                 + merge_y[1:2 * (hm // 2):2, 1:2 * (wm // 2):2])
    cy, cx = y // 2, x // 2
    assert half <= cy < m2.shape[0] - half and half <= cx < m2.shape[1] - half, \
        f"site ({x},{y}) too close to the edge for a {2*half} px window"
    tmpl = m2[cy - half:cy + half, cx - half:cx + half]

    best = {"ncc": -2.0}
    for s in SCALES:
        gy, gx = int(round(cy * s)), int(round(cx * s))
        for dy in range(-search, search + 1, 4):
            for dx in range(-search, search + 1, 4):
                yy, xx = gy + dy, gx + dx
                if not (half <= yy < hg - half and half <= xx < wg - half):
                    continue
                v = ncc(tmpl, g[yy - half:yy + half, xx - half:xx + half])
                if v > best["ncc"]:
                    best = {"ncc": v, "gy": yy, "gx": xx, "scale": s,
                            "dy": dy, "dx": dx}
    # local refinement at step 1 around the coarse optimum
    if best["ncc"] > -2.0:
        by, bx = best["gy"], best["gx"]
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                yy, xx = by + dy, bx + dx
                if not (half <= yy < hg - half and half <= xx < wg - half):
                    continue
                v = ncc(tmpl, g[yy - half:yy + half, xx - half:xx + half])
                if v > best["ncc"]:
                    best = dict(best, ncc=v, gy=yy, gx=xx)
    return best


def classify(curve: np.ndarray, floor: float) -> dict:
    """Shape of the through-focus response, and what it implies for capture."""
    f = np.asarray(curve, np.float64)
    a = int(np.argmax(f))
    fmax, fmin = float(f.max()), float(f.min())
    rng = fmax - fmin
    n = len(f)
    # Fall from the peak to each end, as a fraction of the peak's own range.
    dl = (fmax - float(f[0])) / rng if rng > 0 else 0.0
    dr = (fmax - float(f[-1])) / rng if rng > 0 else 0.0
    at_end = "end0" if a == 0 else ("endN" if a == n - 1 else "")
    # "Still climbing" is stronger than "argmax sits at an end": require the
    # response at the end to dominate the interior minimum as well, so a flat
    # noisy curve whose argmax lands on an end by chance is not called a gap.
    climbing = bool(at_end and rng > 0 and max(dl, dr) > 0.6)
    resolved = bool(fmax > floor and not climbing
                    and min(dl, dr) > 0.25 and 0 < a < n - 1)
    return {
        "argmax_sample": a, "hf_max_rel": round(fmax, 5),
        "hf_min_rel": round(fmin, 5),
        "hf_first_rel": round(float(f[0]), 5),
        "hf_last_rel": round(float(f[-1]), 5),
        "fall_to_first": round(dl, 4), "fall_to_last": round(dr, 4),
        "at_end": at_end, "still_climbing": climbing,
        "peak_resolved_inside_bracket": resolved,
        "peak_over_floor": round(fmax / floor, 3) if floor > 0 else None,
    }


def noise_model(g: np.ndarray, tiles: int = 24) -> tuple[float, float]:
    """Fit  noise_power = a * level + b  from the emptiest tiles of one frame.

    Neither raw nor level-normalised Laplacian RMS is a focus measure at a
    low-signal site, and they fail in OPPOSITE directions, which is how a
    reader can be convinced by either one:

        hf_dn   : shot noise ~ sqrt(level), signal ~ level, so the unnormalised
                  score rises with exposure and picks the BRIGHTEST frame.
        hf_rel  : noise/level ~ 1/sqrt(level), so the normalised score falls
                  with exposure and picks the DARKEST frame.

    Measured on flowers-cpl, whose bracket brightens +19.1%: hf_dn puts the
    optimum at frame 174, hf_rel puts it at frame 0, and at the bokeh sites the
    picture shows there is no optimum at all because no frame holds detail
    there. Subtracting a fitted noise power removes both biases, after which
    what is left is signal.

    Shot noise is Poisson so its variance is linear in level; b absorbs read
    noise and quantisation. The fit uses a low percentile within each level bin,
    i.e. the emptiest tiles at that brightness, which is the noise floor.
    """
    h, w = g.shape
    th, tw = h // tiles, w // tiles
    m, p = [], []
    for r in range(tiles):
        for c in range(tiles):
            t = g[r * th:(r + 1) * th, c * tw:(c + 1) * tw]
            if t.shape[0] > 4 and t.shape[1] > 4:
                m.append(float(np.mean(t)))
                p.append(hf_rms(t) ** 2)
    m = np.asarray(m, np.float64)
    p = np.asarray(p, np.float64)
    if m.size < 8:
        return 0.0, 0.0
    lo, hi = float(m.min()), float(m.max())
    if hi - lo < 1e-6:
        return 0.0, float(np.percentile(p, 10))
    edges = np.linspace(lo, hi, 13)
    bm, bp = [], []
    for i in range(12):
        sel = (m >= edges[i]) & (m <= edges[i + 1])
        if sel.sum() >= 3:
            bm.append(float(np.mean(m[sel])))
            bp.append(float(np.percentile(p[sel], 10)))
    if len(bm) < 2:
        return 0.0, float(np.percentile(p, 10))
    A = np.vstack([np.asarray(bm), np.ones(len(bm))]).T
    a, b = np.linalg.lstsq(A, np.asarray(bp), rcond=None)[0]
    return float(max(a, 0.0)), float(b)


def focus_score(win: np.ndarray, a: float, b: float) -> float:
    """Noise-subtracted, level-normalised focus measure. Dimensionless.

    sqrt(max(hf^2 - noise^2, 0)) / level.  Zero means "nothing here above the
    noise of this frame at this brightness", which is exactly the statement a
    coverage verdict needs to be able to make.
    """
    mval = float(np.mean(win.astype(np.float64)))
    sig2 = hf_rms(win) ** 2 - (a * mval + b)
    return float(np.sqrt(max(sig2, 0.0)) / max(mval, 1.0))


def noise_floor(g: np.ndarray, tiles: int = 16) -> float:
    """Residual focus score of the emptiest tiles, after noise subtraction.

    With the noise power removed this sits near zero on featureless content,
    which is what lets a coverage verdict say "no frame ever held detail here"
    rather than only "this frame held less than that one".

    NOT a corner sample. An early version read the floor off the top-left
    256 px, which happens to be blank on a ruler and happens to be the
    SHARPEST region on `flowers-cpl` -- so the floor came out above the signal
    and the commissioning plant failed.
    """
    a, b = noise_model(g)
    h, w = g.shape
    th, tw = h // tiles, w // tiles
    vals = []
    for r in range(tiles):
        for c in range(tiles):
            t = g[r * th:(r + 1) * th, c * tw:(c + 1) * tw]
            if t.shape[0] > 4 and t.shape[1] > 4:
                vals.append(focus_score(t, a, b))
    return float(np.percentile(vals, 2)) if vals else 0.0


def commission(g: np.ndarray) -> float:
    """C12-C15. An uncommissioned probe and a genuinely null result look alike.

    Anchored on real frame content, not synthetic noise, so the estimator is
    exercised on the statistics it will actually meet. Shape tests are run
    against a floor deliberately placed BELOW the anchor signal, so that a
    failure of the shape logic cannot be masked by the floor gate or vice
    versa; the floor gate then gets its own test (C15).
    """
    print("commissioning sitescan:")
    win = g[g.shape[0] // 2 - 64:g.shape[0] // 2 + 64,
            g.shape[1] // 2 - 64:g.shape[1] // 2 + 64]
    base = hf_rel(win)
    assert base > 0, "C12 anchor: centre window carries no signal at all"
    lo = 0.25 * base            # floor known to sit below the anchor

    # C12 NULL -- the same frame repeated must produce a FLAT curve. If this
    # reports a peak, every peak the instrument ever reports is suspect.
    flat = classify(np.array([base] * 21), lo)
    assert flat["hf_max_rel"] == flat["hf_min_rel"], "C12 null: repeated frame varied"
    assert not flat["peak_resolved_inside_bracket"], \
        "C12 null: found a resolved peak in a constant curve"
    assert not flat["still_climbing"], "C12 null: called a constant curve a gap"
    print(f"  C12 null      constant curve -> no peak, no gap   (hf={base:.2f} DN)")

    # C13 PLANT -- a known blur must reduce HF monotonically, and a synthetic
    # focus ramp peaked at a known index must be recovered AT that index.
    def blur(a: np.ndarray, s: float) -> np.ndarray:
        if s <= 0:
            return a
        r = int(max(1, round(3 * s)))
        x = np.arange(-r, r + 1, dtype=np.float64)
        k = np.exp(-x * x / (2 * s * s))
        k /= k.sum()
        out = np.apply_along_axis(lambda m: np.convolve(m, k, "same"), 0, a)
        return np.apply_along_axis(lambda m: np.convolve(m, k, "same"), 1, out)

    sig = [hf_rel(blur(win, s)) for s in (0.0, 0.5, 1.0, 2.0)]
    assert sig[0] > sig[1] > sig[2] > sig[3], \
        f"C13 monotonicity: blur did not reduce HF monotonically: {sig}"
    peak = 7
    ramp = np.array([hf_rel(blur(win, abs(i - peak) * 0.35)) for i in range(15)])
    cr = classify(ramp, lo)
    assert cr["argmax_sample"] == peak, \
        f"C13 plant: peak planted at {peak}, recovered at {cr['argmax_sample']}"
    assert cr["peak_resolved_inside_bracket"], \
        "C13 plant: a clean interior peak was not called resolved"
    assert not cr["still_climbing"], "C13 plant: interior peak called a gap"
    print(f"  C13 plant     blur ladder {sig[0]:.1f}>{sig[1]:.1f}>{sig[2]:.1f}"
          f">{sig[3]:.1f} DN; peak at {peak} recovered at {cr['argmax_sample']}")

    # C14 PLANT AT AN END -- a response still climbing when the bracket stops is
    # the coverage-gap signature. It must be caught, and named at the right end.
    climb = np.array([hf_rel(blur(win, (14 - i) * 0.30)) for i in range(15)])
    cc = classify(climb, lo)
    assert cc["still_climbing"] and cc["at_end"] == "endN", \
        f"C14 plant: truncated ramp not called a gap at endN: {cc}"
    drop = np.array([hf_rel(blur(win, i * 0.30)) for i in range(15)])
    cd = classify(drop, lo)
    assert cd["still_climbing"] and cd["at_end"] == "end0", \
        f"C14 plant: reversed ramp not called a gap at end0: {cd}"
    print(f"  C14 plant     truncated ramps caught at both ends "
          f"(endN fall {cc['fall_to_first']:.2f}, end0 fall {cd['fall_to_last']:.2f})")

    # C15 FLOOR GATE -- a peak that never rises above the floor is not a peak.
    hi = classify(ramp, float(ramp.max()) * 1.5)
    assert not hi["peak_resolved_inside_bracket"], \
        "C15 floor: a curve entirely below the floor was called resolved"
    fl = noise_floor(g)
    assert 0 < fl < base, \
        f"C15 floor: estimated floor {fl:.4f} not below anchor {base:.4f}"
    print(f"  C15 floor     gate holds; frame floor {fl:.4f} "
          f"< centre-window signal {base:.4f}")

    # C16 SHOT-NOISE RAMP -- the control with teeth, and the reason
    # focus_score exists. A pure multiplicative scale is NOT a faithful plant:
    # it scales signal and noise together, so hf_rel is exactly invariant under
    # it and the test would have no power. The real bracket brightens because
    # more light arrived, so signal ~ level while shot noise ~ sqrt(level).
    # Plant that, at the exact +19.1% `flowers-cpl` actually carries, on two
    # synthetic regions: one FEATURELESS (the bokeh case) and one TEXTURED.
    rng = np.random.default_rng(20240517)
    N, L, K = 1024, 1200.0, 0.55     # K = noise variance per DN of level
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    sig = 1.0 + 0.25 * (xx / N)                       # smooth: no detail
    sig[N // 2:, :] *= 1.0 + 0.35 * np.sin(xx[N // 2:, :] * 1.7)   # textured
    # Large sample regions: hf_rms has its own variance, and a +19.1% ramp
    # spread over 15 samples is only ~0.6% per step, so a small tile would let
    # the noise realisation move the argmax off the end and mask the bias.
    bok = (slice(32, N // 2 - 32), slice(32, N - 32))
    tex = (slice(N // 2 + 32, N - 32), slice(32, N - 32))

    def synth(s: float) -> np.ndarray:
        lam = sig * L * s
        return lam + rng.normal(0.0, np.sqrt(K * lam))

    lv = np.linspace(1.0, 1.191, 15)
    bok_dn, bok_rel, bok_fs, tex_fs = [], [], [], []
    for s in lv:
        f = synth(s)
        a_s, b_s = noise_model(f)
        bok_dn.append(hf_rms(f[bok]))
        bok_rel.append(hf_rel(f[bok]))
        bok_fs.append(focus_score(f[bok], a_s, b_s))
        tex_fs.append(focus_score(f[tex], a_s, b_s))
    bok_dn = np.array(bok_dn); bok_rel = np.array(bok_rel)
    bok_fs = np.array(bok_fs); tex_fs = np.array(tex_fs)

    c_dn = classify(bok_dn, 0.25 * float(bok_dn[0]))
    c_rel = classify(bok_rel, 0.25 * float(bok_rel[-1]))
    assert c_dn["still_climbing"] and c_dn["at_end"] == "endN", (
        "C16 has no power: on a featureless site under a pure +19.1% shot-noise "
        f"ramp the DN estimator did NOT report a false gap at endN ({c_dn})")
    assert c_rel["still_climbing"] and c_rel["at_end"] == "end0", (
        "C16 has no power: the level-normalised estimator did NOT report a "
        f"false gap at end0 on the same ramp ({c_rel})")
    print(f"  C16 shotnoise featureless site, +19.1% light, focus never changes:"
          f"\n                hf_dn  x{bok_dn[-1]/bok_dn[0]:.3f} -> false gap at "
          f"{c_dn['at_end']};  hf_rel x{bok_rel[-1]/bok_rel[0]:.3f} -> false gap "
          f"at {c_rel['at_end']}  (OPPOSITE ends, both wrong)")

    # ...and the metric actually used must stay silent on the same data.
    c_fs = classify(bok_fs, 0.02)
    assert not c_fs["still_climbing"], \
        f"C16: focus_score still reports a gap on a featureless ramp ({c_fs})"
    assert float(bok_fs.max()) < 0.02, (
        f"C16: focus_score {bok_fs.max():.4f} did not collapse on a site that "
        "contains no detail in any frame")
    tex_spread = float(tex_fs.max() / max(tex_fs.min(), 1e-12))
    assert tex_spread < 1.05, \
        f"C16: focus_score drifted x{tex_spread:.4f} on textured content"
    print(f"  C16 fix       focus_score: featureless -> {bok_fs.max():.5f} (no "
          f"gap called); textured -> flat to x{tex_spread:.4f}")

    # C17 NOISE FLOOR on the REAL frame -- the emptiest tile must score far
    # below the richest one. NB the reference is the richest TILE, not the
    # centre window: on `flowers-cpl` the frame centre is itself bokeh, so
    # centre-vs-corner would compare two featureless things and prove nothing.
    a0, b0 = noise_model(g)
    hh, ww = g.shape
    scores = []
    for r in range(0, hh - 256, 256):
        for c in range(0, ww - 256, 256):
            t = g[r:r + 256, c:c + 256]
            scores.append((focus_score(t, a0, b0), hf_rms(t) / max(float(t.mean()), 1.0)))
    fs_flat = min(scores, key=lambda p: p[1])[0]     # emptiest by relative HF
    fs_rich = max(s[0] for s in scores)              # richest by focus score
    assert fs_flat < 0.25 * fs_rich, (
        f"C17: noise subtraction did not separate empty from rich content "
        f"(empty={fs_flat:.5f} vs rich={fs_rich:.5f})")
    print(f"  C17 noise     emptiest real tile -> {fs_flat:.5f}; richest -> "
          f"{fs_rich:.5f} (x{fs_rich/max(fs_flat,1e-9):.1f})  "
          f"noise model a={a0:.4f} b={b0:.1f}")
    print("commissioning OK\n")
    return fl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--at", action="append", default=[], metavar="LABEL:X,Y",
                    help="probe site at exact MERGE pixel (X,Y). Repeatable.")
    ap.add_argument("--frames", type=int, default=40)
    ap.add_argument("--half", type=int, default=HALF_G)
    ap.add_argument("--loc-half", type=int, default=96,
                    help="half-window for NCC LOCATION only. Larger than the "
                         "measurement window on purpose: locating needs "
                         "context, measuring needs to isolate the feature.")
    ap.add_argument("--min-ncc", type=float, default=MIN_NCC)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    assert args.at, "no --at sites given: nothing to probe"

    sites = []
    for spec in args.at:
        label, _, xy = spec.partition(":")
        sx, _, sy = xy.partition(",")
        sites.append({"label": label, "x": int(sx), "y": int(sy)})

    d = os.path.join(tri.RAW, args.subject)
    seen: dict[str, str] = {}
    for f in os.listdir(d):          # Windows globs are case-insensitive: dedupe
        if f.lower().endswith(".arw"):
            seen.setdefault(os.path.normcase(f), f)
    files = sorted(seen.values())
    n = len(files)
    assert n > 0, f"{args.subject}: no ARW frames"
    idx = (np.unique(np.linspace(0, n - 1, min(args.frames, n)).round().astype(int))
           if n > args.frames else np.arange(n))

    merge_y = tri.luma(tri.load16(os.path.join(tri.LIN, args.subject + ".tiff")))

    # Locate every site once, in a mid-bracket frame, and verify by NCC.
    ref = green_plane(os.path.join(d, files[int(idx[len(idx) // 2])]))
    ref_floor = commission(ref)
    for s in sites:
        loc = locate(merge_y, ref, s["x"], s["y"], args.loc_half, SEARCH_G)
        s.update(loc)
        print(f"  locate {s['label']:>12s} merge({s['x']},{s['y']}) -> "
              f"green({loc['gx']},{loc['gy']}) scale={loc['scale']:.2f} "
              f"ncc={loc['ncc']:.4f}")
        if loc["ncc"] < args.min_ncc:
            raise SystemExit(
                f"{args.subject}/{s['label']}: site did not land "
                f"(ncc={loc['ncc']:.4f} < {args.min_ncc}). Refusing to report a "
                f"through-focus curve for a location I cannot confirm.")

    curves = np.zeros((len(idx), len(sites)), np.float32)
    curves_dn = np.zeros((len(idx), len(sites)), np.float32)
    levels = np.zeros((len(idx), len(sites)), np.float32)
    noise = np.zeros(len(idx), np.float32)
    h_ = args.half
    for i, k in enumerate(idx):
        g = green_plane(os.path.join(d, files[int(k)]))
        # Fit this frame's own noise power. It must be per-frame: the whole
        # point is that the frames differ in level.
        a_n, b_n = noise_model(g)
        for j, s in enumerate(sites):
            w = g[s["gy"] - h_:s["gy"] + h_, s["gx"] - h_:s["gx"] + h_]
            curves[i, j] = focus_score(w, a_n, b_n)
            curves_dn[i, j] = hf_rms(w)
            levels[i, j] = float(np.mean(w))
        # Read the floor off the whole frame, not a corner.
        noise[i] = noise_floor(g)

    floor = float(np.median(noise))
    res = {
        "subject": args.subject, "n_frames": n,
        "sampled": [int(v) for v in idx],
        "half_px_rawG": args.half, "min_ncc": args.min_ncc,
        "decode": "rawpy CFA green, black-subtracted, no demosaic/WB/matrix",
        "hf_floor_rel": round(floor, 5),
        "metric": "sqrt(max(LapRMS^2 - (a*level+b), 0)) / level -- noise power "
                  "subtracted before normalising, because LapRMS in DN is "
                  "biased toward the BRIGHTEST frame and LapRMS/level toward "
                  "the DARKEST. hf_dn and level_dn recorded alongside because "
                  "a ratio hides an additive bias",
        "note": "frame-vs-frame only; never compared numerically to the merge",
        "sites": [],
    }
    for j, s in enumerate(sites):
        c = classify(curves[:, j], floor)
        a = c["argmax_sample"]
        c.update({
            "label": s["label"], "merge_x": s["x"], "merge_y": s["y"],
            "green_x": s["gx"], "green_y": s["gy"],
            "locate_ncc": round(s["ncc"], 4), "locate_scale": s["scale"],
            "best_frame": int(idx[a]),
            "hf_dn_at_peak": round(float(curves_dn[a, j]), 2),
            "hf_dn_first": round(float(curves_dn[0, j]), 2),
            "hf_dn_last": round(float(curves_dn[-1, j]), 2),
            "level_dn_at_peak": round(float(levels[a, j]), 1),
            "level_dn_first": round(float(levels[0, j]), 1),
            "level_dn_last": round(float(levels[-1, j]), 1),
            "curve_rel": [round(float(v), 5) for v in curves[:, j]],
            "curve_dn": [round(float(v), 3) for v in curves_dn[:, j]],
        })
        res["sites"].append(c)
        verdict = ("STILL CLIMBING at " + c["at_end"] if c["still_climbing"]
                   else ("peak resolved inside bracket"
                         if c["peak_resolved_inside_bracket"]
                         else "no resolved peak (flat/low)"))
        print(f"  {s['label']:>13s} rel={c['hf_max_rel']:.4f} x{c['peak_over_floor']:<6} "
              f"({c['hf_dn_at_peak']:7.1f} DN at level {c['level_dn_at_peak']:7.1f}) "
              f"best={c['best_frame']:3d}/{n} "
              f"fall {c['fall_to_first']:.2f}/{c['fall_to_last']:.2f}  {verdict}")

    out = os.path.join(tri.OUT, "sitescan",
                       args.subject + (args.tag or "") + ".json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
