"""BUILD-DEFECT step 02 -- the failed roll control, and what the sites actually are.

`01-dust-from-flats.py` reported 14,073 sites and a ROLL CONTROL of 9,966,
i.e. an enrichment of 1.41x where the control should have read ~0.  That is a
RED result and this script exists to find out which of two things it means.

  (i) MY CONTROL IS BROKEN.  01 rolled 9 of the 18 tags and left 9 real.  The
      site criterion is the MEDIAN over 18 values, so 9 real deep values put
      the median exactly at the 9th/10th order statistic -- half the tags are
      still corresponding, and half is enough to drag a median.  A control
      that leaves half the signal in place is not a control.
      REPAIR: roll EVERY tag, each by a DIFFERENT offset.  Then no two tags
      correspond at all and recurrence can only arise by chance.

  (ii) THE SITES ARE NOT PER-PIXEL FIXED.  If the repaired control still
      fires, the statistic is reading something that survives losing
      correspondence, and no amount of thresholding will fix that.

Then, whichever it is, LOOK AT THE DATA (rule: a number without a picture has
never once been enough in this project).  Renders every map to PNG and reports
the connected-component structure, because the object being claimed -- a dust
mote -- has a KNOWN SHAPE.  At f/5.6 through a 2x teleconverter a mote sitting
~2 mm above the photosites throws a shadow of order 20-45 plane px across; a
PRNU outlier or a low-sensitivity photosite is ONE pixel.  Those are different
objects and only the first is dust.

Outputs: out/*.png, data/02-diagnosis.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import ndimage

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "out"
DATA = HERE / "data"
SEED_DEPTH = 0.010
RECURRENCE = 15
FLOOR_DEPTH = 0.015
NT = 18


def png(a: np.ndarray, path: Path, lo: float, hi: float, step: int = 4) -> None:
    """Write a greyscale PNG of `a` decimated by `step`, windowed to [lo, hi]."""
    from PIL import Image
    b = a[::step, ::step]
    v = np.clip((b - lo) / (hi - lo), 0.0, 1.0)
    Image.fromarray((v * 255).astype(np.uint8), mode="L").save(path)


def main() -> None:
    res = {}
    per_tag = np.load(OUT / "dust-residual-per-tag.npy")
    assert per_tag.shape[0] == NT, per_tag.shape
    med = np.median(per_tag, axis=0)
    N = med.size
    rng = np.random.default_rng(20260827)

    def sites_of(stack: np.ndarray) -> np.ndarray:
        seen = (stack <= -SEED_DEPTH).sum(axis=0)
        return (seen >= RECURRENCE) & (np.median(stack, axis=0) <= -FLOOR_DEPTH)

    real = sites_of(per_tag)
    n_real = int(real.sum())

    # ------------------------------------------------------------- 1
    print("=== 1. the roll control, repaired")
    print("    01's control rolled 9 of 18 tags. The site test is a MEDIAN over")
    print("    18, so 9 corresponding tags still set it. Roll ALL of them, each")
    print("    by its own offset, and correspondence is gone entirely.")
    counts = []
    for trial in range(3):
        rolled = np.empty_like(per_tag)
        for i in range(NT):
            dy = int(rng.integers(200, 2100))
            dx = int(rng.integers(200, 3300))
            rolled[i] = np.roll(per_tag[i], (dy, dx), axis=(0, 1))
        n = int(sites_of(rolled).sum())
        counts.append(n)
        print(f"    trial {trial}: all 18 tags rolled independently -> {n} sites")
        del rolled
    print(f"    real {n_real}   control mean {np.mean(counts):.1f}"
          f"   enrichment {n_real / max(np.mean(counts), 1e-9):.1f}x")
    # 01's broken control, reproduced so the repair is visible as a delta
    half = np.concatenate([per_tag[:9], np.roll(per_tag[9:], 157, axis=1)], axis=0)
    n_half = int(sites_of(half).sum())
    print(f"    01's HALF-ROLLED control, reproduced: {n_half} sites"
          f"   -> the control was the defect")
    del half
    res["roll"] = {"real": n_real, "full_roll_trials": counts,
                   "full_roll_mean": float(np.mean(counts)),
                   "half_roll_reproduced": n_half,
                   "enrichment": n_real / max(float(np.mean(counts)), 1e-9)}

    # ------------------------------------------------------------- 2
    print("\n=== 2. what shape are the sites?  (dust is a DISC; PRNU is a POINT)")
    lab, nlab = ndimage.label(real)
    sizes = np.bincount(lab.ravel())[1:]
    print(f"    connected components of the site set: {nlab}")
    for lo, hi in ((1, 1), (2, 4), (5, 20), (21, 100), (101, 500),
                   (501, 5000), (5001, 10 ** 9)):
        n = int(((sizes >= lo) & (sizes <= hi)).sum())
        px = int(sizes[(sizes >= lo) & (sizes <= hi)].sum())
        print(f"    size {lo:6d}-{hi if hi < 10**9 else 'inf':>6}: "
              f"{n:6d} components, {px:8d} px")
    res["components"] = {"n": int(nlab),
                         "singletons": int((sizes == 1).sum()),
                         "px_in_singletons": int(sizes[sizes == 1].sum()),
                         "ge5": int((sizes >= 5).sum()),
                         "px_in_ge5": int(sizes[sizes >= 5].sum()),
                         "largest": int(sizes.max()) if nlab else 0}

    # ------------------------------------------------------------- 3
    # The separator, and the point of the whole script: a BAND-PASS.  Dust
    # lives between ~2 and ~15 plane px.  Smoothing the median residual at 5 px
    # divides a singleton's amplitude by 25 while leaving a 25-px disc nearly
    # untouched.  So the same threshold on the SMOOTHED map keeps discs and
    # discards points, and the two populations become separately countable.
    print("\n=== 3. band-pass: 5x5 mean of the median residual")
    k = np.ones((5, 5), np.float32) / 25.0
    band = ndimage.convolve(med, k, mode="nearest")
    for t in (0.005, 0.0075, 0.010, 0.015, 0.020):
        m = band <= -t
        l2, n2 = ndimage.label(m)
        s2 = np.bincount(l2.ravel())[1:] if n2 else np.array([])
        big = int((s2 >= 25).sum()) if n2 else 0
        print(f"    band <= -{t * 100:5.2f}% : {int(m.sum()):7d} px, "
              f"{n2:5d} components, {big:4d} of them >= 25 px")
    res["bandpass_sweep"] = {}
    for t in (0.005, 0.0075, 0.010, 0.015, 0.020):
        m = band <= -t
        l2, n2 = ndimage.label(m)
        s2 = np.bincount(l2.ravel())[1:] if n2 else np.array([])
        res["bandpass_sweep"][str(t)] = {
            "px": int(m.sum()), "components": int(n2),
            "components_ge25": int((s2 >= 25).sum()) if n2 else 0}

    # the same on the fully-rolled stack -- the null for the band-pass
    rolled = np.empty_like(per_tag)
    for i in range(NT):
        rolled[i] = np.roll(per_tag[i],
                            (int(rng.integers(200, 2100)), int(rng.integers(200, 3300))),
                            axis=(0, 1))
    band_null = ndimage.convolve(np.median(rolled, axis=0), k, mode="nearest")
    del rolled
    print("    NULL (all 18 rolled independently):")
    for t in (0.005, 0.0075, 0.010, 0.015, 0.020):
        m = band_null <= -t
        l2, n2 = ndimage.label(m)
        s2 = np.bincount(l2.ravel())[1:] if n2 else np.array([])
        big = int((s2 >= 25).sum()) if n2 else 0
        print(f"    band <= -{t * 100:5.2f}% : {int(m.sum()):7d} px, "
              f"{n2:5d} components, {big:4d} of them >= 25 px")
        res["bandpass_sweep"][str(t)]["null_px"] = int(m.sum())
        res["bandpass_sweep"][str(t)]["null_components_ge25"] = big
    np.save(OUT / "dust-band.npy", band)

    # ------------------------------------------------------------- 4
    print("\n=== 4. renders")
    OUT.mkdir(exist_ok=True)
    png(med, OUT / "median-residual.png", -0.02, 0.02)
    png(band, OUT / "band-residual.png", -0.02, 0.02)
    png(np.load(OUT / "dust-seen.npy").astype(np.float32), OUT / "recurrence.png", 0, 18)
    print(f"    wrote {OUT / 'median-residual.png'} (whole plane, /4, -2%..+2%)")

    # zoomed crops of the deepest band-pass components, at 1:1
    m = band <= -0.0075
    l2, n2 = ndimage.label(m)
    if n2:
        s2 = np.bincount(l2.ravel())[1:]
        order = np.argsort(-s2)[:6]
        coms = ndimage.center_of_mass(m, l2, order + 1)
        crops = []
        for j, (li, (cy, cx)) in enumerate(zip(order, coms)):
            cy, cx = int(cy), int(cx)
            r = 80
            y0, x0 = max(0, cy - r), max(0, cx - r)
            sub = band[y0:y0 + 2 * r, x0:x0 + 2 * r]
            png(sub, OUT / f"mote-{j}.png", -0.04, 0.01, step=1)
            crops.append({"rank": j, "size_px": int(s2[li]),
                          "centre_plane_yx": [cy, cx],
                          "centre_sensor_yx": [2 * cy, 2 * cx],
                          "min_band": float(sub.min())})
            print(f"    mote-{j}.png  {int(s2[li]):6d} px at plane ({cy},{cx}) "
                  f"= sensor ({2 * cy},{2 * cx}), deepest {sub.min() * 100:.2f}%")
        res["motes"] = crops

    (DATA / "02-diagnosis.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\nwrote {DATA / '02-diagnosis.json'}")


if __name__ == "__main__":
    main()
