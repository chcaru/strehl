"""Ring prominence: an independent re-derivation of the owner's acceptance metric.

The owner measured a bright ring just outside the silhouette -- 12.0% prominence
at d=18 px on flower-bud (dense trichome fringe), 0.23% at d=450 px on
coffee-bean (smooth convex silhouette) -- and pre-registered driving the first
toward the second as the acceptance test for any fix.

This is deliberately NOT his script. Same quantity, different binning, different
peak finder, written without reading his numbers into it, so that agreement means
something. Two things are copied on purpose because they are correct:

  * prominence is measured against the trough OUTSIDE the peak, never against the
    far field. The ring sits INSIDE the veil: brighter than its trough and still
    darker than the far field. A far-field comparison cannot see it by
    construction, and his first version returned a clean-looking NO BAND on a
    profile that visibly turns over twice.
  * the entire profile prints above the verdict. A verdict line is never the only
    output.

One thing is added, and it matters for the A/B this metric exists to serve:

  * --mask-from. The subject mask is drawn by brightness and the artifact IS
    excess brightness, so a fix that removes the ring also moves the mask, which
    moves the distance origin, which changes the profile for a reason that has
    nothing to do with the ring. In any comparison the mask must be computed once
    from a single reference arm and reused. Otherwise the metric partly measures
    its own coordinate system.

Usage:
    python ringprofile.py <linear.tif> [more.tif ...] [--mask-from <ref.tif>]
"""
import sys
import json
import pathlib
import numpy as np
import tifffile
from scipy import ndimage

# Uniform fine bins where the ring lives, coarsening outward. Deliberately
# different from the hand-placed edges in the owner's script: if a 2 px grid and
# a hand-placed grid disagree about a peak, the peak is a binning artifact.
EDGES = (list(range(0, 100, 2)) + list(range(100, 300, 10))
         + list(range(300, 700, 25)))
FAR_LO, FAR_HI = 600, 1400
MIN_PX = 400


def load_luma(path):
    img = tifffile.imread(path)
    assert img.dtype == np.uint16, f"{path}: expected uint16, got {img.dtype}"
    return img.astype(np.float32).mean(axis=2)


def subject_mask(lum):
    lo, hi = np.percentile(lum, [5, 95])
    thr = 0.5 * (lo + hi)
    m = lum < thr
    lab, n = ndimage.label(m)
    if n > 1:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (1 + int(np.argmax(sizes)))
    return m, thr, n


def signed_distance(mask):
    # Zero-pad before the EDT: distance_transform_edt saturates at array borders
    # because they are not zeros, and an unpadded transform puts spurious maxima
    # in every corner. Harmless if you only read the first few hundred px, fatal
    # if you ever argmax it.
    pad = 8
    p = np.pad(mask, pad, mode="constant", constant_values=False)
    d_out = ndimage.distance_transform_edt(~p)[pad:-pad, pad:-pad]
    d_in = ndimage.distance_transform_edt(mask)
    return d_out - d_in


def profile(lum, signed):
    ds, vals, counts = [], [], []
    for i in range(len(EDGES) - 1):
        m = (signed >= EDGES[i]) & (signed < EDGES[i + 1])
        n = int(m.sum())
        if n < MIN_PX:
            continue
        ds.append(0.5 * (EDGES[i] + EDGES[i + 1]))
        vals.append(float(np.median(lum[m])))
        counts.append(n)
    return np.array(ds), np.array(vals), np.array(counts)


def ring(ds, vals, ref):
    """Every interior local maximum, with prominence over its OUTWARD trough."""
    peaks = []
    for i in range(1, len(vals) - 1):
        if vals[i] >= vals[i - 1] and vals[i] > vals[i + 1]:
            trough = float(vals[i + 1:].min())
            peaks.append((float(ds[i]), float(vals[i]), float(vals[i] - trough)))
    if not peaks:
        return None
    d_pk, v_pk, prom = max(peaks, key=lambda p: p[2])
    return {"d": d_pk, "dn": v_pk, "prom_dn": prom,
            "prom_pct": 100.0 * prom / ref, "all": peaks}


def analyse(path, mask_src=None):
    lum = load_luma(path)
    if mask_src is None:
        mask, thr, ncomp = subject_mask(lum)
        origin = "own"
    else:
        mask, thr, ncomp = subject_mask(load_luma(mask_src))
        origin = f"borrowed from {pathlib.Path(mask_src).name}"
    signed = signed_distance(mask)
    far = (signed > FAR_LO) & (signed < FAR_HI)
    ref = float(np.median(lum[far]))
    ds, vals, counts = profile(lum, signed)

    print(f"\n{'=' * 74}\n{pathlib.Path(path).name}   {lum.shape}")
    print(f"  mask {origin}: thr={thr:.0f}, {mask.mean() * 100:.2f}% of frame, "
          f"{ncomp} components")
    print(f"  far field {FAR_LO}-{FAR_HI} px = {ref:.0f} DN over {far.sum()} px")
    print(f"\n  {'d(px)':>7} {'median DN':>11} {'vs far':>9} {'% far':>8} {'n':>10}")
    for d, v, c in zip(ds, vals, counts):
        print(f"  {d:7.0f} {v:11.0f} {v - ref:+9.0f} {100 * (v - ref) / ref:+8.2f} {c:10d}")

    r = ring(ds, vals, ref)
    print("\n  VERDICT")
    print(f"    darkening at the silhouette (0-2 px): "
          f"{vals[0] - ref:+.0f} DN = {100 * (vals[0] - ref) / ref:+.1f}%")
    if r is None:
        print("    NO interior local maximum: the backdrop rises monotonically.")
    else:
        print(f"    RING at d={r['d']:.0f} px, {r['dn']:.0f} DN, prominence "
              f"{r['prom_dn']:+.0f} DN = {r['prom_pct']:.2f}% of far field")
        print(f"    all interior peaks (d, prominence %): "
              f"{[(int(d), round(100 * p / ref, 2)) for d, _, p in r['all']]}")
    return {"file": pathlib.Path(path).name, "ref": ref,
            "darkening_pct": 100.0 * (vals[0] - ref) / ref,
            "ring": None if r is None else
            {k: r[k] for k in ("d", "dn", "prom_dn", "prom_pct")},
            "ds": ds.tolist(), "vals": vals.tolist()}


def main():
    args = [a for a in sys.argv[1:]]
    mask_src = None
    if "--mask-from" in args:
        i = args.index("--mask-from")
        mask_src = args[i + 1]
        del args[i:i + 2]
    out = [analyse(p, mask_src) for p in args]
    dest = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\ring.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
