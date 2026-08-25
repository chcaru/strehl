"""M114 r18: signed radial R-G displacement per ring, TWO scenes, ONE estimator.

ORCH's gain 1.444 comes from one scene and one estimator. Comparing my scene-2
number to ORCH's scene-1 number would confound scene with instrument, so this
measures BOTH scenes identically.

DEFINITION. Let R_off and R_on be the SIGNED radial displacement of red relative
to green, in output px, in each arm. The correction moves red by
applied = R_on - R_off and needs to move it by needed = -R_off, so

    gain = applied / needed = 1 - R_on / R_off

Correct = 1.0. Under-corrected < 1 (residual keeps its sign). Over-corrected > 1
(residual has FLIPPED sign), which is what ORCH asks to be scored signed. This
form is a ratio of two measurements of the SAME quantity type by the SAME
estimator on the SAME scene, so a multiplicative attenuation A(r) cancels
exactly -- unlike applied/needed, whose numerator is a between-arm difference
and denominator a within-arm channel difference.

ESTIMATOR. Two-stage SSD search along a unit direction on per-window
standardised gradient magnitude. Cross-channel intensity differences are removed
by standardisation; geometry is preserved because grad-mag of a shifted image is
the shifted grad-mag.

CONTROLS, all red-capable:
  V1 NULL         G vs G must read 0.000 px.
  V2 SIGN+SCALE   integer x-roll of +-1,+-2 px must be recovered with the RIGHT
                  SIGN and exact magnitude. Integer, so it cannot change
                  sharpness -- the confound that killed ORCH's first estimator.
  V3 CENTRE       lateral CA is ZERO at the optical centre by construction, so
                  the estimator must read ~0 there. ORCH's attempt 1 read -0.778
                  here and was measuring scene hue structure. Bar |d| < 0.10 px.
  V4 FLOOR        tangential displacement, which lateral CA cannot produce, is
                  the per-ring noise floor. Rings not clearing 1.5x are dropped.
"""
import json, sys
import numpy as np
import tifffile
from scipy import ndimage
from pathlib import Path

R17 = Path(r"C:\dev\strehl-out\M114-ca-verify\r17")
WIN, PER_RING = 96, 44
RINGS = [(0.10, 0.25), (0.25, 0.38), (0.38, 0.50), (0.50, 0.62),
         (0.62, 0.74), (0.74, 0.86), (0.86, 0.98)]

def gmag(a):
    return ndimage.gaussian_gradient_magnitude(a, 1.0)

def std(a):
    s = a.std()
    return (a - a.mean()) / s if s > 1e-9 else a * 0.0

def _ssd(a, b, ux, uy, ds, order):
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(np.float64)
    best, bd = None, 0.0
    for d in ds:
        w = ndimage.map_coordinates(b, [yy + d * uy, xx + d * ux], order=order, mode="nearest")
        s = float(np.mean((a - w) ** 2))
        if best is None or s < best:
            best, bd = s, float(d)
    return bd

def disp(a, b, ux, uy):
    """SIGNED displacement of a relative to b along (ux,uy), in px.

    map_coordinates samples b at x + d, which moves content LEFT by d, so a
    content shift of +k is recovered as d = -k. The negation below is that
    convention, and V2 is the bar that proves it.
    """
    c = _ssd(a, b, ux, uy, np.arange(-5.0, 5.01, 0.5), 1)
    f = _ssd(a, b, ux, uy, np.arange(c - 0.5, c + 0.501, 0.05), 3)
    return -f

def windows(g, cx, cy, RC, rlo, rhi, n, rng, thresh):
    got, tries = [], 0
    while len(got) < n and tries < 30000:
        tries += 1
        y = int(rng.integers(8, g.shape[0] - WIN - 8)); x = int(rng.integers(8, g.shape[1] - WIN - 8))
        my, mx = y + WIN / 2 - cy, x + WIN / 2 - cx
        rr = np.hypot(mx, my)
        if not (rlo <= rr / RC < rhi) or rr < 1e-6:
            continue
        sl = (slice(y, y + WIN), slice(x, x + WIN))
        if float(np.mean(gmag(g[sl]))) < thresh:
            continue
        got.append((sl, mx / rr, my / rr))
    return got

OUT = {}
for scene in ("bee-3-cpl", "119MSDCF"):
    off = tifffile.imread(str(R17 / (scene + "-off.tif"))).astype(np.float64)
    on = tifffile.imread(str(R17 / (scene + "-on.tif"))).astype(np.float64)
    H, W, _ = off.shape
    cx, cy, RC = W / 2.0, H / 2.0, np.hypot(W / 2.0, H / 2.0)
    G = off[:, :, 1]
    thresh = float(np.percentile([np.mean(gmag(G[y:y+WIN, x:x+WIN]))
                                  for y, x in zip(np.random.default_rng(1).integers(0, H-WIN, 400),
                                                  np.random.default_rng(2).integers(0, W-WIN, 400))], 75))
    print("\n=== %s  %dx%d  half-diag %.1f  edge gate %.1f ===" % (scene, W, H, RC, thresh), flush=True)
    rng = np.random.default_rng(1114)

    # V1 null and V2 sign/scale control
    ws = windows(G, cx, cy, RC, 0.35, 0.55, 12, rng, thresh)
    sl0 = ws[0][0]
    v1 = disp(std(gmag(G[sl0])), std(gmag(G[sl0])), 1.0, 0.0)
    rec = [disp(std(gmag(np.roll(G, k, axis=1)[sl0])), std(gmag(G[sl0])), 1.0, 0.0) for k in (-2, -1, 1, 2)]
    v2err = max(abs(r - k) for r, k in zip(rec, (-2, -1, 1, 2)))
    print("V1 null (G vs G)            : %+.4f px  -> %s" % (v1, "PASS" if abs(v1) < 0.02 else "FAIL"))
    print("V2 integer roll -2,-1,1,2   : %s  max err %.4f px -> %s"
          % (" ".join("%+.3f" % r for r in rec), v2err, "PASS" if v2err < 0.10 else "FAIL"))

    # V3 optical-centre check
    wc = windows(G, cx, cy, RC, 0.0, 0.05, 16, rng, thresh * 0.6)
    dc = np.median([disp(std(gmag(off[sl][:, :, 0])), std(gmag(off[sl][:, :, 1])), ux, uy) for sl, ux, uy in wc]) if wc else float("nan")
    print("V3 centre R-G (must be ~0)  : %+.4f px (n=%d) -> %s"
          % (dc, len(wc), "PASS" if abs(dc) < 0.10 else "FAIL"))

    rows = []
    for rlo, rhi in RINGS:
        ws = windows(G, cx, cy, RC, rlo, rhi, PER_RING, rng, thresh)
        if len(ws) < 8:
            print("r %.2f-%.2f  n=%d  SKIPPED (too few windows)" % (rlo, rhi, len(ws)))
            continue
        def med(arm, c, radial):
            v = []
            for sl, ux, uy in ws:
                u, w_ = (ux, uy) if radial else (-uy, ux)
                v.append(disp(std(gmag(arm[sl][:, :, c])), std(gmag(arm[sl][:, :, 1])), u, w_))
            return float(np.median(v)), v
        r_off, vo = med(off, 0, True)
        r_on, vn = med(on, 0, True)
        t_off, _ = med(off, 0, False)
        b_off, _ = med(off, 2, True)
        b_on, _ = med(on, 2, True)
        floor = abs(t_off)
        ok = abs(r_off) > 1.5 * max(floor, 1e-9)
        gain = 1.0 - r_on / r_off if abs(r_off) > 1e-9 else float("nan")
        boot = [1.0 - np.median(rng.choice(vn, len(vn))) / np.median(rng.choice(vo, len(vo))) for _ in range(400)]
        lo, hi = np.percentile(boot, [2.5, 97.5])
        rows.append(dict(rlo=rlo, rhi=rhi, n=len(ws), r_off=r_off, r_on=r_on,
                         applied=r_on - r_off, gain=gain, ci=[float(lo), float(hi)],
                         floor=floor, used=bool(ok), b_off=b_off, b_on=b_on))
        print("r %.2f-%.2f n=%2d  R_off %+.3f  R_on %+.3f  applied %+.3f  gain %6.3f [%.2f,%.2f]  |tan| %.3f %s"
              % (rlo, rhi, len(ws), r_off, r_on, r_on - r_off, gain, lo, hi, floor,
                 "" if ok else "<- BELOW FLOOR, DROPPED"), flush=True)
    used = [r for r in rows if r["used"] and np.isfinite(r["gain"])]
    if used:
        wsum = sum(r["n"] for r in used)
        g = sum(r["gain"] * r["n"] for r in used) / wsum
        rmid = np.array([(r["rlo"] + r["rhi"]) / 2 for r in used])
        gs = np.array([r["gain"] for r in used])
        slope = np.polyfit(rmid, gs, 1, w=np.array([r["n"] for r in used], float))[0]
        print("  WEIGHTED MEAN GAIN %.3f   radial slope %+.4f/unit r   rings used %d/%d"
              % (g, slope, len(used), len(rows)))
        bl = [r for r in rows if abs(r["b_off"]) > 1.5 * max(r["floor"], 1e-9)]
        print("  BLUE: %d/%d rings clear the floor" % (len(bl), len(rows)))
        OUT[scene] = dict(rows=rows, gain=float(g), slope=float(slope), V1=v1, V2=v2err, V3=float(dc),
                          blue_rings=len(bl))
(R17 / "r18.json").write_text(json.dumps(OUT, indent=1, default=float), encoding="utf-8")
if len(OUT) == 2:
    a, b = OUT["bee-3-cpl"]["gain"], OUT["119MSDCF"]["gain"]
    print("\n=== SCENE TRANSFER ===")
    print("scene 1 bee-3-cpl (in-sample) gain %.3f" % a)
    print("scene 2 119MSDCF  (held out)  gain %.3f" % b)
    print("difference %+.3f (%.1f%% of scene 1)" % (b - a, 100 * (b - a) / a))
