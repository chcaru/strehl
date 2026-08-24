"""M87 step 61 -- does the veil OVERSHOOT the background? A blend cannot.

WHY THIS IS THE DECIDING TEST OF THE MECHANISM. My whole model of the halo is
the two-layer composite

    I_k = alpha_k (F conv PSF_k) + (1 - alpha_k) (B conv PSF_k)

which is a CONVEX combination. Convexity has a hard consequence that can be
checked on the render with no ground truth at all: the veil's value must lie
BETWEEN the subject's level and the background's, for every alpha in [0,1] and
every frame. It may approach the background asymptote; it may not pass it.

Looking at the island-0035 and island-0074 crops, the bright band hugging the
silhouette appears BRIGHTER than the open background beside it. If that is real
and not a perceptual effect of the surround, the halo is not a blend of the two
layers, and a fix built on unmixing two layers is fitting the wrong model.

REGISTERED, before running:
  O1  BLEND. The signed-distance profile rises monotonically from the subject
      level to the far-background asymptote and never exceeds it by more than
      3 standard errors of the bin.
  O2  OVERSHOOT. Some band of signed distance exceeds the far-background
      asymptote by > 3 SE. This FALSIFIES the convex two-layer model as the
      sole mechanism and implicates the SELECTION -- an argmax over frames of a
      contrast statistic is a biased estimator and can return a value above
      both layers, which no single frame's blend can be.
  O1 and O2 are exclusive and exhaustive, so this cannot fail to discriminate.

CONTROLS:
  C-FRAME  the same profile on the elected frame index. If an overshoot band
           coincides with a jump in which frame is elected, it is selection.
  C-NULL   the same profile taken across a REFLECTANCE edge at a single depth
           -- the dark filaments inside the subject -- where there is no
           occlusion. A blend model predicts no overshoot there either, so an
           overshoot at the silhouette but NOT here localises the effect to
           occluding boundaries rather than to edges in general.
  C-BROKEN registered broken arm: the identical profile on a mask boundary
           drawn at random inside the open background, where by construction
           there is no edge. Any overshoot reported there is the estimator's
           own bias and the headline must be reduced by it.
"""

import json
import pathlib

import numpy as np
from scipy import ndimage as ndi

CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"

DMAX = 60
WIDE = 260
FAR = 400
RNG = np.random.default_rng(6101)


def otsu(v):
    h, e = np.histogram(v.ravel(), 512)
    h = h.astype(np.float64)
    c, m = h.cumsum(), (h * ((e[:-1] + e[1:]) / 2)).cumsum()
    tot, mt = c[-1], m[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        sb = (mt * c / tot - m) ** 2 / (c * (tot - c))
    return float(e[1:][np.nanargmax(sb)])


def signed(mask):
    """+ outside the mask, - inside. `mask` is the region we call background."""
    return (ndi.distance_transform_edt(~mask)
            - ndi.distance_transform_edt(mask))


def profile(sd, val, restrict=None, dmax=DMAX, step=1):
    rows = []
    for d in range(-dmax, dmax + 1, step):
        m = (sd >= d - 0.5 * step) & (sd < d + 0.5 * step)
        if restrict is not None:
            m &= restrict
        n = int(m.sum())
        if n < 30:
            continue
        v = val[m]
        rows.append({"d": d, "n": n, "med": float(np.median(v)),
                     "mean": float(v.mean()),
                     "se": float(v.std(ddof=1) / np.sqrt(n))})
    return rows


def overshoot(rows, asym, label):
    best = None
    for r in rows:
        z = (r["med"] - asym) / max(r["se"], 1e-12)
        if best is None or z > best[0]:
            best = (z, r)
    z, r = best
    print(f"  {label:<10} asymptote {asym:10.1f}   peak median {r['med']:10.1f}"
          f" at d={r['d']:+4d}   excess {r['med'] - asym:+9.1f}  z={z:8.1f}"
          f"   {'OVERSHOOT' if z > 3 else 'no overshoot'}")
    return {"asym": asym, "peak_med": r["med"], "peak_d": r["d"],
            "excess": r["med"] - asym, "z": z, "overshoot": bool(z > 3)}


def main():
    res = {}
    sel = np.load(CACHE / "25-flower-alone-sel.npy").astype(np.float32)
    arg = np.load(CACHE / "25-flower-alone-argbest.npy").astype(np.float32)
    tau = otsu(sel)
    bright = sel > tau
    lab, _ = ndi.label(bright)
    b = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    b.discard(0)
    bg = np.isin(lab, list(b))
    sd = signed(bg)
    # sd is NEGATIVE inside bg and POSITIVE outside it, because
    # distance_transform_edt measures distance to the nearest ZERO. So the far
    # BACKGROUND asymptote is at sd <= -FAR; sd >= +FAR is deep SUBJECT. I had
    # this inverted on the first run and it produced a nonsense z=938
    # "overshoot" that was really the background compared against the subject,
    # and an empty open-background set that crashed the broken arm. The crash
    # is the only reason I re-read it.
    asym = float(np.median(sel[sd <= -FAR]))
    subj_level = float(np.median(sel[sd >= FAR]))
    print(f"binned {sel.shape}  tau {tau:.1f}")
    print(f"  far BACKGROUND asymptote (sd<=-{FAR}) = {asym:.1f}")
    print(f"  deep SUBJECT level       (sd>=+{FAR}) = {subj_level:.1f}")
    print(f"  a convex blend of the two is bounded by [{subj_level:.1f}, {asym:.1f}]")
    res["asym_background"], res["level_subject"] = asym, subj_level

    print("\n=== the silhouette profile ===")
    rows = profile(sd, sel)
    print(f"  {'d':>5} {'n':>9} {'median':>10} {'vs asym':>9}")
    for r in rows:
        if r["d"] % 4 == 0 or abs(r["d"]) <= 12:
            print(f"  {r['d']:>+5} {r['n']:>9} {r['med']:>10.1f}"
                  f" {r['med'] - asym:>+9.1f}")
    res["profile"] = rows
    res["silhouette"] = overshoot(rows, asym, "SILHOUETTE")

    print("\n=== C-FRAME: which frame is elected, across the same boundary ===")
    frows = profile(sd, arg)
    res["profile_argbest"] = frows
    prev = None
    for r in frows:
        if r["d"] % 6 == 0:
            jump = "" if prev is None else f"  d(idx)={r['med'] - prev:+6.1f}"
            print(f"  d={r['d']:>+4}  elected median {r['med']:6.1f}{jump}")
            prev = r["med"]

    print("\n=== C-NULL: a reflectance edge at one depth (dark filaments) ===")
    # the filaments are dark structures fully inside the subject, i.e. an edge
    # with no background behind it. Their own signed distance, restricted to
    # deep interior so no silhouette contaminates the profile.
    deep = ndi.distance_transform_edt(~bg) > 120
    dark = (sel < np.percentile(sel[deep], 25)) & deep
    dark = ndi.binary_opening(dark, np.ones((3, 3)))
    sd2 = signed(dark)
    a2 = float(np.median(sel[deep & (sd2 >= 40)]))
    rows2 = profile(sd2, sel, restrict=deep)
    res["reflectance"] = overshoot(rows2, a2, "FILAMENT")

    print("\n=== C-BROKEN: an invented boundary in open background ===")
    open_bg = bg & (sd <= -FAR)
    lo = np.zeros_like(bg)
    ys, xs = np.where(open_bg)
    print(f"  open background pool: {len(ys)} px")
    for _ in range(40):
        j = RNG.integers(len(ys))
        cy, cx = int(ys[j]), int(xs[j])
        r = 60
        y0, y1 = max(cy - r, 0), min(cy + r + 1, sel.shape[0])
        x0, x1 = max(cx - r, 0), min(cx + r + 1, sel.shape[1])
        gy, gx = np.ogrid[y0:y1, x0:x1]
        lo[y0:y1, x0:x1] |= ((gy - cy) ** 2 + (gx - cx) ** 2) <= r * r
    lo &= open_bg
    sd3 = signed(lo)
    a3 = float(np.median(sel[lo & (sd3 <= -40)])) if (lo & (sd3 <= -40)).any() else asym
    rows3 = profile(sd3, sel, restrict=open_bg)
    res["broken"] = overshoot(rows3, a3, "INVENTED")

    print("\n=== the RIM, scored against the LOCAL plateau, not the far field ===")
    # O1 asked whether the veil breaches the convex bound, and it does not. But
    # the eye does not see the far field: it sees a bright band against the
    # background NEXT TO IT. Those are different references and the profile is
    # non-monotone, so both are needed. Plateau = the flat stretch at
    # d in [-60,-30], well outside the rim and well inside the broad component.
    def rim_stat(rows, label):
        plat = [r for r in rows if -60 <= r["d"] <= -30]
        if not plat:
            return None
        base = float(np.median([r["med"] for r in plat]))
        near = [r for r in rows if -25 <= r["d"] <= -1]
        if not near:
            return None
        pk = max(near, key=lambda z: z["med"])
        lift = (pk["med"] - base) / max(base, 1e-9)
        print(f"  {label:<10} local plateau {base:8.1f}  rim peak {pk['med']:8.1f}"
              f" at d={pk['d']:+4d}   lift {100 * lift:+7.2f}%")
        return {"plateau": base, "peak": pk["med"], "peak_d": pk["d"], "lift": lift}

    rim = rim_stat(rows, "SILHOUETTE")
    rim_broken = rim_stat(rows3, "INVENTED")
    res["rim"], res["rim_broken"] = rim, rim_broken
    if rim and rim_broken:
        ratio = abs(rim["lift"]) / max(abs(rim_broken["lift"]), 1e-9)
        print(f"  rim lift is {ratio:.1f}x the invented boundary's bias floor"
              f"   {'REAL' if ratio >= 3 else 'WITHIN BIAS -- not reportable'}")
        res["rim_vs_bias"] = ratio

    v = res["silhouette"]
    print("\n=== the veil's RADIAL EXTENT -- the number the annulus needs ===")
    wide = profile(sd, sel, dmax=WIDE, step=5)
    bgside = [r for r in wide if r["d"] < 0]
    bgside.sort(key=lambda z: z["d"], reverse=True)   # -5, -10, ... outward
    print(f"  {'d':>6} {'median':>9} {'% of asymptote':>15}")
    rec = {}
    for r in bgside:
        f = r["med"] / asym
        if r["d"] % 20 == 0 or r["d"] > -40:
            print(f"  {r['d']:>+6} {r['med']:>9.1f} {100 * f:>14.1f}%")
        for tgt in (0.50, 0.75, 0.90, 0.95):
            if f >= tgt and tgt not in rec:
                rec[tgt] = -r["d"]
    for tgt in (0.50, 0.75, 0.90, 0.95):
        print(f"  background recovers to {100 * tgt:.0f}% of its open level at "
              f"{rec.get(tgt, '>%d' % WIDE)} binned px from the silhouette")
    res["recovery_binned_px"] = {str(k): rec.get(k) for k in (0.50, 0.75, 0.90, 0.95)}
    res["profile_wide"] = wide

    print("\n=== VERDICT ===")
    if v["overshoot"] and not res["broken"]["overshoot"]:
        print("  O2. The veil EXCEEDS the far background by "
              f"{v['excess']:.1f} units ({100 * v['excess'] / v['asym']:.2f}%)"
              f" at d={v['peak_d']:+d}, z={v['z']:.0f}, while the invented")
        print("  boundary in open background does not. A convex two-layer blend")
        print("  CANNOT produce a value above both layers, so selection, not")
        print("  blending alone, is manufacturing the bright rim.")
    elif v["overshoot"]:
        print("  O2 but the BROKEN ARM also overshoots -- estimator bias, "
              "headline must be reduced by it.")
    else:
        print("  O1. The profile stays within the two layers: consistent with a "
              "convex blend, and my visual read of the crops was wrong.")
    res["verdict"] = "O2" if v["overshoot"] else "O1"

    json.dump(res, open(DATA / "61-overshoot.json", "w"), indent=1)
    print(f"\nwrote {DATA / '61-overshoot.json'}")


if __name__ == "__main__":
    main()
