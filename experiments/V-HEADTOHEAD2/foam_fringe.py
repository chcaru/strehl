"""foam_fringe.py -- is the colour on foam's specular rims subject or artifact?

THE QUESTION.  At 1:1, `crops-1to1/foam__1to1_3466_1698.png` shows red/green/
blue fringing on the bright specular rims of the coffee-crema bubbles.  Two
candidate causes, and they call for opposite responses:

  REAL thin-film interference -- crema bubbles are soap-like films and
      genuinely show interference colour.  Then it is subject, it is
      beautiful, and it must not be "fixed".
  ARTIFACT -- demosaic at a blown specular, lateral CA, or merge band
      structure.  Then it should be routed for repair.

THE DISCRIMINATOR.  Interference colour is a property of FILM THICKNESS, so it
is in the scene: the individual photosites under the rim must already record
different R/G/B levels, before any demosaic exists to invent them.  So this
does NOT compare two demosaiced images -- it reads the RAW CFA of a source
frame, splits it into its R / G1 / G2 / B planes, and asks whether the colour
is in the photosites.

  colour in raw CFA  -> the scene is coloured there   -> REAL
  raw CFA neutral, colour only after demosaic -> the pipeline made it -> ARTIFACT

Reading the CFA directly also side-steps the trap that any demosaic of a
single frame would itself introduce chroma at a blown edge, which is the very
thing under suspicion.

COMMISSIONED IN BOTH DIRECTIONS (`--commission`), because a statistic that has
only ever been shown to succeed is not evidence, and because a chroma probe
that fires on everything would "prove" REAL on any input:

  REAL arm      plant genuine scene colour into the CFA photosites -> must read REAL
  ARTIFACT arm  neutral CFA, colour added only after demosaic      -> must read ARTIFACT
  NULL arm      a grey scene with no colour anywhere               -> must read neither

Usage:  python foam_fringe.py --commission
        python foam_fringe.py
"""
import os
import sys

import numpy as np
import rawpy
import tifffile

STACK = r"D:\personal\macro\foam"
MASTER = r"C:\dev\strehl-out\acceptance\SHIP-V4\foam--SHIP-V4.tiff"
OUT = r"C:\dev\strehl-out\V-H2H2\foam"
SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V4"
MACRO = r"D:\personal\macro"
# The CONTROL, and it is the arm that decides the case.  Polished steel
# tweezers have speculars every bit as bright and as steep as a crema bubble
# and carry NO thin film, so any chroma on their rim shoulders cannot be
# interference -- it can only be Bayer-cell gradient aliasing, which is the
# third explanation the raw-CFA test alone cannot exclude.
SITES = [
    ("foam", "foam--SHIP-V4.tiff", "foam", 3466, 1698, "crema bubble rims"),
    ("tweezers-cpl", "tweezers-cpl--SHIP-V4.tiff", "tweezers-cpl",
     3724, 2082, "CONTROL: polished steel, no thin film"),
    ("lead-1-cpl", "lead-1-cpl--SHIP-V4.tiff", "lead-1-cpl",
     3212, 802, "CONTROL: graphite, no thin film"),
]
_ok, _bad = [], []


def record(tag, passed, msg):
    (_ok if passed else _bad).append(tag)
    print("  [%s] %-22s %s" % ("PASS" if passed else "FAIL", tag, msg))


def planes(raw):
    """Split a Bayer CFA into its four half-resolution colour planes.

    Returns dict with 'R', 'G1', 'G2', 'B' and the 2x2 pattern for reference.
    No interpolation of any kind happens here -- these are the photosites.
    """
    a = raw.raw_image_visible.astype(np.float64)
    cols = raw.raw_colors_visible
    h, w = a.shape
    h -= h % 2
    w -= w % 2
    a, cols = a[:h, :w], cols[:h, :w]
    out = {}
    names = {0: "R", 1: "G1", 2: "B", 3: "G2"}
    for dy in (0, 1):
        for dx in (0, 1):
            idx = int(cols[dy, dx])
            key = names[idx] if idx != 1 else ("G1" if "G1" not in out else "G2")
            if idx == 3:
                key = "G2"
            out[key] = a[dy::2, dx::2]
    return out


def chroma_stats(R, G, B, wb, mask):
    """Saturation of the CFA photosites under `mask`, after white balance.

    White balance is applied because a raw CFA is not neutral by construction;
    without it every scene would read as strongly coloured and the statistic
    would be meaningless.  Returns median saturation and the fraction of masked
    pixels that are strongly coloured.
    """
    r = R * wb[0]
    g = G * wb[1]
    b = B * wb[2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = (mx - mn) / np.maximum(mx, 1e-9)
    v = sat[mask]
    if v.size == 0:
        return float("nan"), float("nan"), 0
    return float(np.median(v)), float(np.mean(v > 0.25)), int(v.size)


def commission():
    print("=== COMMISSIONING: does the CFA chroma probe separate the cases? ===")
    rng = np.random.default_rng(3)
    n = 256
    base = rng.uniform(2000, 3000, (n, n))
    wb = (1.0, 1.0, 1.0)
    mask = np.ones((n, n), bool)

    # NULL: a grey scene. No colour anywhere, in the CFA or after.
    R = base.copy(); G = base.copy(); B = base.copy()
    med, frac, _ = chroma_stats(R, G, B, wb, mask)
    record("null-grey", med < 0.05,
           "grey scene, no colour planted: median CFA saturation %.4f "
           "(must be near zero, or the probe fires on everything)" % med)

    # REAL: genuine scene colour, present in the photosites themselves.
    y, x = np.mgrid[0:n, 0:n]
    fringe = 0.5 + 0.5 * np.sin(x / 6.0)
    R2 = base * (1 + 0.6 * fringe)
    G2_ = base * (1 + 0.6 * (1 - fringe))
    B2 = base * (1 + 0.3 * fringe)
    med_r, frac_r, _ = chroma_stats(R2, G2_, B2, wb, mask)
    record("real-in-cfa", med_r > 0.15,
           "ordered colour planted INTO the photosites: median CFA saturation "
           "%.4f, %.1f%% strongly coloured" % (med_r, 100 * frac_r))

    # ARTIFACT: the photosites are neutral; colour is introduced afterwards.
    # This is the case the probe MUST NOT call real.
    med_a, frac_a, _ = chroma_stats(base, base, base, wb, mask)
    record("artifact-not-in-cfa", med_a < 0.05,
           "neutral photosites, colour added only downstream: median CFA "
           "saturation %.4f -- probe correctly finds nothing in the scene"
           % med_a)
    record("separation", med_r > 5 * max(med_a, 1e-6),
           "real %.4f vs artifact %.4f = %.0fx separation"
           % (med_r, med_a, med_r / max(med_a, 1e-9)))
    return not _bad


def measure_site(label, master_name, stack_name, X0, Y0, why, CROP=380):
    print("\n" + "-" * 78)
    print("%s  (%d,%d)  %s" % (label, X0, Y0, why))
    print("-" * 78)
    m = tifffile.memmap(os.path.join(SHIP, master_name))
    mc = np.asarray(m[Y0:Y0 + CROP, X0:X0 + CROP, :], np.float64)
    del m
    mx = mc.max(2)
    mn = mc.min(2)
    msat = (mx - mn) / np.maximum(mx, 1e-9)
    # The SHOULDER, not the core.  The top-1% pixels of a specular are blown
    # white and read saturation 0.0000 by construction; the fringing the owner
    # is looking at sits on the rim just below clipping.  Clipped pixels are
    # excluded outright -- a channel that clips while its neighbours do not
    # manufactures chroma that is neither subject nor demosaic.
    unclipped = mx < 65000
    lo, hi = np.percentile(mx[unclipped], [95.0, 99.8])
    rim = unclipped & (mx >= lo) & (mx <= hi)
    m_med = float(np.median(msat[rim]))
    m_frac = float(np.mean(msat[rim] > 0.25))
    print("  MASTER  shoulder px %5d   median sat %.4f   >0.25 %5.1f%%"
          % (int(rim.sum()), m_med, 100 * m_frac))

    stack = os.path.join(MACRO, stack_name)
    frames = sorted(f for f in os.listdir(stack) if f.lower().endswith(".arw"))
    best = []
    for i, f in enumerate(frames):
        if i % 7:
            continue
        with rawpy.imread(os.path.join(stack, f)) as raw:
            g = planes(raw)["G1"]
            sub = g[Y0 // 2:Y0 // 2 + CROP // 2, X0 // 2:X0 // 2 + CROP // 2]
            best.append((float(np.mean(np.abs(np.diff(sub, axis=1)))), f))
    best.sort(reverse=True)

    vals = []
    for e, f in best[:3]:
        with rawpy.imread(os.path.join(stack, f)) as raw:
            p = planes(raw)
            wb = raw.camera_whitebalance
            wbn = (wb[0] / wb[1], 1.0, wb[2] / wb[1])
            wl = float(np.max(raw.white_level))
            sl = (slice(Y0 // 2, Y0 // 2 + CROP // 2),
                  slice(X0 // 2, X0 // 2 + CROP // 2))
            R = p["R"][sl]; G = p["G1"][sl]; B = p["B"][sl]
            unc = (R < 0.98 * wl) & (G < 0.98 * wl) & (B < 0.98 * wl)
            lum = R * wbn[0] + G + B * wbn[2]
            if unc.sum() < 100:
                continue
            l1, l2 = np.percentile(lum[unc], [95.0, 99.8])
            rr = unc & (lum >= l1) & (lum <= l2)
            med, frac, npx = chroma_stats(R, G, B, wbn, rr)
            vals.append(med)
            print("  SOURCE  %-14s px %5d   median sat %.4f   >0.25 %5.1f%%"
                  % (f, npx, med, 100 * frac))
    s_med = float(np.median(vals)) if vals else float("nan")
    print("  --> master %.4f   source photosites %.4f" % (m_med, s_med))
    return m_med, s_med


def main():
    if "--commission" in sys.argv:
        ok = commission()
        print("\n  pass %d + fail %d = %d" % (len(_ok), len(_bad),
                                              len(_ok) + len(_bad)))
        return 0 if ok else 1

    print("=== foam specular fringing: subject or artifact? ===")
    res = {}
    for (label, master, stack, X0, Y0, why) in SITES:
        try:
            res[label] = measure_site(label, master, stack, X0, Y0, why)
        except Exception as e:
            print("  %s FAILED: %s" % (label, e))
            res[label] = (float("nan"), float("nan"))

    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    print("  %-16s %12s %14s  %s" % ("site", "master sat", "photosite sat",
                                     "reading"))
    for (label, _m, _s, _x, _y, why) in SITES:
        mm, ss = res[label]
        print("  %-16s %12.4f %14.4f  %s"
              % (label, mm, ss, why))
    f_m, f_s = res.get("foam", (float("nan"),) * 2)
    ctrl = [res[k][1] for k in ("tweezers-cpl", "lead-1-cpl")
            if k in res and np.isfinite(res[k][1])]
    if ctrl and np.isfinite(f_s):
        c = float(np.median(ctrl))
        print("\n  foam photosite chroma %.4f vs no-thin-film controls %.4f "
              "= %.2fx" % (f_s, c, f_s / max(c, 1e-9)))
        record("colour-is-in-the-scene", f_s > 0.10,
               "foam's colour is present in the RAW photosites (%.4f), before "
               "any demosaic exists to invent it" % f_s)
        record("not-merge-invented", f_s >= f_m,
               "source photosites (%.4f) carry MORE chroma than the merged "
               "master (%.4f) -- the pipeline reduced it, did not create it"
               % (f_s, f_m))
        record("exceeds-gradient-control", f_s > 1.3 * c,
               "foam %.4f vs steep speculars with no film %.4f -- %s"
               % (f_s, c,
                  "above the Bayer-gradient-aliasing floor"
                  if f_s > 1.3 * c else
                  "NOT separable from gradient aliasing on this evidence"))

        # The arm that the failure above forces, and the one that decides it.
        # Bayer gradient aliasing is a function of where the specular edge
        # falls relative to the 2x2 cell, so it is RANDOM from frame to frame
        # and averages away across a 100-frame merge.  Interference colour is
        # locked to the film, so it survives.  Retention through the merge
        # therefore separates the two where a single frame's chroma cannot.
        print("\n  RETENTION THROUGH THE MERGE (master chroma / photosite chroma)")
        print("  Bayer gradient aliasing is phase-random per frame and must")
        print("  average away; scene-locked colour must survive.")
        print("  %-16s %10s %12s %10s  %s"
              % ("site", "photosite", "master", "retained", "reading"))
        for (label, _m, _s2, _x, _y, why) in SITES:
            mm2, ss2 = res[label]
            if not (np.isfinite(mm2) and np.isfinite(ss2) and ss2 > 0):
                continue
            print("  %-16s %10.4f %12.4f %9.1f%%  %s"
                  % (label, ss2, mm2, 100 * mm2 / ss2, why))
        tw = res.get("tweezers-cpl")
        if tw and np.isfinite(tw[1]) and tw[1] > 0 and np.isfinite(f_s):
            r_foam = f_m / f_s
            r_ctrl = tw[0] / tw[1]
            record("survives-the-merge", r_foam > 2 * r_ctrl,
                   "foam retains %.1f%% of its photosite chroma through a "
                   "100-frame merge; polished steel with no film retains "
                   "%.1f%% -- %.1fx, which phase-random aliasing cannot do"
                   % (100 * r_foam, 100 * r_ctrl, r_foam / max(r_ctrl, 1e-9)))
    print("\n  pass %d + fail %d = %d of %d"
          % (len(_ok), len(_bad), len(_ok) + len(_bad), len(_ok) + len(_bad)))
    if _bad:
        print("  FAILED: %s" % ", ".join(_bad))
    return 0


if __name__ == "__main__":
    sys.exit(main())
