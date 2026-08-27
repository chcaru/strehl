"""BUILD-DEFECT step 01 -- the dust map, from 18 independent flat captures.

WHY THIS SCRIPT EXISTS, AND WHAT IT IS NOT
------------------------------------------
M71 §7.2 already found dust in these flats (2,898 px, median depth -3.44%) but
it used ONE exposure group (`e0.05`, the 1/20 s pair) and a hand-set -3% cut,
and it produced a BOOLEAN MASK.  A boolean mask cannot correct anything: dust
attenuates light multiplicatively by an amount that varies across the mote, so
what a correction consumes is a GAIN FIELD, not a set of coordinates.  This
script builds the gain field and, more importantly, gives the search a floor so
that it is able to return NOTHING.

THE CONFOUND THIS SCRIPT EXISTS TO DEFEAT
-----------------------------------------
The flats were shot through a window under moving cloud.  M71 measured the
illumination NOT as a drift but as a 2.35x SWING, rising at +1.6 to +2.0 %/s.
An illumination change is a defect map's classic false positive.  Three
independent defences, each measured here rather than asserted:

  (a) PER-FRAME SCALAR.  Every frame was divided by its own per-plane spatial
      mean before entering any temporal accumulator (M71 `02-decode-flats.py`,
      whose caches this script consumes).  That removes the whole-frame level.

  (b) SPATIAL SCALE.  A cloud edge crossing the frame is a LOW-frequency
      gradient; dust is a disc of tens of plane px.  Dividing by a 61-px
      3-pass box (sigma ~15.2 plane px) removes everything above that scale.
      §2 measures how much of the raw between-tag spread each step removes.

  (c) RECURRENCE ACROSS INDEPENDENT CAPTURES.  This is the discriminator, and
      it is the one that cannot be argued with.  The 18 tags are 9 shutter
      speeds x 2 CPL states, shot over ~40 minutes with a ~4.7 minute
      intermission in every group.  No cloud is in the same place in 18
      captures spread over 40 minutes.  Dust is.  M22 §2 established recurrence
      over independently-captured groups as the correct discriminator for the
      additive half of this problem; this is the same instrument on the
      multiplicative half.

INPUT is M71's committed cache, not a re-decode: 18 tags x 4 planes of
per-pixel 20-frame normalised temporal means.  Re-decoding 360 flats costs
~25 min and would produce the same arrays.

OUTPUT
  out/dust-residual-per-tag.npy   float32 (18, 2344, 3514)  -- regenerable
  out/dust-gain.npy               float32 (2344, 3514)      -- the gain field
  data/01-dust.json               every number quoted in the report
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
M71 = HERE.parent / "M71-flat-fields"
CACHE = M71 / "out" / "cache"
OUT = HERE / "out"
DATA = HERE / "data"

PLANES = ("R", "G1", "G2", "B")
TAGS = [
    f"e{e}-{h}"
    for e in ("0.004", "0.008", "0.016666666666666666", "0.03333333333333333",
              "0.05", "0.07692307692307693", "0.1", "0.2", "8")
    for h in ("A", "B")
]
# `e8` is the 1/8 s group; M71's tag rule emits the DENOMINATOR when the
# exposure is 1/n, so `e8` is 0.125 s and `e0.2` is the 1/5 s group.
EXPOSURE_OF = {
    "e0.004": 0.004, "e0.008": 0.008, "e0.016666666666666666": 1 / 60,
    "e0.03333333333333333": 1 / 30, "e0.05": 0.05,
    "e0.07692307692307693": 1 / 13, "e0.1": 0.1, "e0.2": 0.2, "e8": 0.125,
}

# --- the operating point, all three limbs declared before any result -------
BOX = 61           # high-pass box width, plane px; 3 passes -> sigma ~15.2 px
NPASS = 3
SEED_DEPTH = 0.010     # a tag "sees" a site when its residual is <= -1.0%
RECURRENCE = 15        # ... and a site is DUST when >= 15 of the 18 tags see it
FLOOR_DEPTH = 0.015    # ... and its median depth across tags is <= -1.5%
# FLOOR_DEPTH is an ABSOLUTE floor, not a percentile.  A percentile cut always
# returns something; this one returns nothing on a clean sensor, and
# `03-commission.py` proves that on a synthetic clean flat.


def smooth(a: np.ndarray, box: int, npass: int) -> np.ndarray:
    """`npass` passes of a `box`-wide separable moving average, edge-replicated.

    Copied in behaviour from M71 `05-kappa.py::smooth` so that the residual
    this script forms is the same operator M71 §7.2 formed, and the two dust
    numbers are therefore comparable rather than merely similar.
    """
    out = a.astype(np.float32, copy=True)
    r = box // 2
    for _ in range(npass):
        for axis in (0, 1):
            pad = [(0, 0), (0, 0)]
            pad[axis] = (r, r)
            p = np.pad(out, pad, mode="edge")
            c = np.cumsum(p, axis=axis, dtype=np.float64)
            zero = np.zeros_like(np.take(c, [0], axis=axis))
            c = np.concatenate([zero, c], axis=axis)
            hi = np.take(c, np.arange(box, box + out.shape[axis]), axis=axis)
            lo = np.take(c, np.arange(0, out.shape[axis]), axis=axis)
            out = ((hi - lo) / box).astype(np.float32)
    return out


def residual_for(tag: str) -> np.ndarray:
    """Plane-averaged local relative residual of one 20-frame flat mean.

    Averaged over the four CFA planes because dust sits on the sensor stack,
    well above the colour filter array, so its shadow is achromatic to first
    order.  Averaging four planes divides the per-pixel noise by 2 and is the
    only place in this script where the planes are combined.
    """
    acc = None
    for p in PLANES:
        m = np.load(CACHE / f"{tag}-{p}-mean.npy")
        r = m / smooth(m, BOX, NPASS) - np.float32(1.0)
        acc = r if acc is None else acc + r
    return (acc / np.float32(len(PLANES))).astype(np.float32)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    res = {}

    # ---------------------------------------------------------------- 1
    print("=== 1. the 18 independent captures")
    per_tag = np.zeros((len(TAGS), 2344, 3514), np.float32)
    for i, tag in enumerate(TAGS):
        per_tag[i] = residual_for(tag)
        print(f"    {tag:24s} rms {per_tag[i].std() * 100:7.4f}%   "
              f"min {per_tag[i].min() * 100:7.3f}%   [{time.time() - t0:5.1f}s]")
        sys.stdout.flush()
    np.save(OUT / "dust-residual-per-tag.npy", per_tag)
    res["tags"] = TAGS
    res["per_tag_rms"] = [float(x) for x in per_tag.reshape(len(TAGS), -1).std(axis=1)]

    # ---------------------------------------------------------------- 2
    # Does the high-pass actually remove the illumination, or am I about to
    # map a cloud?  Measured, not asserted: compare the spread ACROSS TAGS of
    # (i) the raw block means, (ii) the same after the high-pass.  Cloud lives
    # in (i) and must be gone from (ii).
    print("\n=== 2. does the high-pass separate cloud from dust? (rule 20)")
    blk = 64
    nr, nc = 2344 // blk, 3514 // blk

    def blocks(a):
        return a[: nr * blk, : nc * blk].reshape(nr, blk, nc, blk).mean(axis=(1, 3))

    raw_blocks = np.zeros((len(TAGS), nr, nc), np.float32)
    hp_blocks = np.zeros((len(TAGS), nr, nc), np.float32)
    for i, tag in enumerate(TAGS):
        m = np.load(CACHE / f"{tag}-G1-mean.npy")
        raw_blocks[i] = blocks(m / float(m.mean()) - 1.0)
        hp_blocks[i] = blocks(per_tag[i])
    raw_spread = float(raw_blocks.std(axis=0).mean())
    hp_spread = float(hp_blocks.std(axis=0).mean())
    print(f"    between-tag sd of 64x64 block level, BEFORE high-pass: "
          f"{raw_spread * 100:.4f}%")
    print(f"    between-tag sd of 64x64 block level, AFTER  high-pass: "
          f"{hp_spread * 100:.4f}%")
    print(f"    the high-pass removes {raw_spread / hp_spread:.1f}x of the "
          f"between-capture spatial disagreement")
    # The illumination signature is a LARGE-SCALE pattern that differs between
    # captures; the dust signature is a SMALL-SCALE pattern common to them.
    # A cloud map would make the between-tag correlation of the high-passed
    # maps LOW.  Measure it.
    flat = per_tag.reshape(len(TAGS), -1)
    cen = flat - flat.mean(axis=1, keepdims=True)
    nrm = cen / np.linalg.norm(cen, axis=1, keepdims=True)
    corr = nrm @ nrm.T
    off = corr[~np.eye(len(TAGS), dtype=bool)]
    print(f"    between-tag correlation of the high-passed maps: "
          f"median {np.median(off):.4f}, min {off.min():.4f}, max {off.max():.4f}")
    res["separation"] = {
        "raw_block_spread": raw_spread, "hp_block_spread": hp_spread,
        "ratio": raw_spread / hp_spread,
        "between_tag_corr_median": float(np.median(off)),
        "between_tag_corr_min": float(off.min()),
        "between_tag_corr_max": float(off.max()),
    }

    # ---------------------------------------------------------------- 3
    print("\n=== 3. recurrence across the 18 captures")
    seen = (per_tag <= -SEED_DEPTH).sum(axis=0).astype(np.int16)
    N = seen.size
    hist = np.bincount(seen.ravel(), minlength=len(TAGS) + 1)
    # A per-tag independence baseline, exactly M22 §2's instrument: if the
    # per-tag flags were independent the recurrence histogram would be
    # Binomial(18, p) with p the observed per-tag rate.
    p_tag = float((per_tag <= -SEED_DEPTH).mean())
    from math import comb
    print(f"    per-tag flag rate p = {p_tag:.6g}")
    print(f"    {'k':>3s} {'observed':>10s} {'Binomial(18,p)':>16s}")
    chance = {}
    for k in range(len(TAGS) + 1):
        exp = comb(len(TAGS), k) * p_tag ** k * (1 - p_tag) ** (len(TAGS) - k) * N
        chance[k] = exp
        if hist[k] or exp > 1e-3:
            print(f"    {k:3d} {hist[k]:10d} {exp:16.4g}")
    res["recurrence_hist"] = [int(x) for x in hist]
    res["recurrence_chance"] = {str(k): float(v) for k, v in chance.items()}
    res["p_tag"] = p_tag

    # ---------------------------------------------------------------- 4
    print("\n=== 4. the site set, and its floors")
    median_r = np.median(per_tag, axis=0)
    recurrent = seen >= RECURRENCE
    deep = median_r <= -FLOOR_DEPTH
    site = recurrent & deep
    n_site = int(site.sum())
    print(f"    recurrent (>= {RECURRENCE}/18 at <= -{SEED_DEPTH * 100:.1f}%): "
          f"{int(recurrent.sum())}")
    print(f"    deep      (median depth <= -{FLOOR_DEPTH * 100:.1f}%):        "
          f"{int(deep.sum())}")
    print(f"    BOTH -> dust sites:                          {n_site}"
          f"   = {n_site / N * 100:.5f}% of the plane")
    if n_site:
        d = median_r[site]
        print(f"    depth at sites: median {np.median(d) * 100:.3f}%, "
              f"worst {d.min() * 100:.3f}%, shallowest {d.max() * 100:.3f}%")

    # ROLL CONTROL.  Rolling by an even number of PLANE rows preserves every
    # spatial statistic and the CFA phase, and destroys per-pixel
    # correspondence.  If cloud or paper texture were driving this, the rolled
    # pair would agree just as often.
    rolled = np.roll(per_tag, 157, axis=1)
    seen_roll = (rolled <= -SEED_DEPTH)
    # roll only HALF the tags, so the conjunction is between two genuinely
    # non-corresponding populations
    mix = np.concatenate([per_tag[:9], rolled[9:]], axis=0)
    seen_mix = (mix <= -SEED_DEPTH).sum(axis=0)
    med_mix = np.median(mix, axis=0)
    n_mix = int(((seen_mix >= RECURRENCE) & (med_mix <= -FLOOR_DEPTH)).sum())
    print(f"    ROLL CONTROL (9 of 18 tags rolled 157 plane rows): {n_mix} sites"
          f"   -> {'PASS' if n_mix <= max(1, 0.01 * n_site) else 'FAIL'}")
    del rolled, seen_roll, mix, seen_mix, med_mix

    res["sites"] = {
        "n_recurrent": int(recurrent.sum()), "n_deep": int(deep.sum()),
        "n_site": n_site, "frac": n_site / N,
        "roll_control_sites": n_mix,
        "roll_pass": bool(n_mix <= max(1, 0.01 * n_site)),
        "seed_depth": SEED_DEPTH, "recurrence": RECURRENCE,
        "floor_depth": FLOOR_DEPTH, "box": BOX, "npass": NPASS,
    }
    if n_site:
        d = median_r[site]
        res["sites"].update(median_depth=float(np.median(d)),
                            worst_depth=float(d.min()),
                            shallowest_depth=float(d.max()))

    # ---------------------------------------------------------------- 5
    # The gain field.  A boolean mask cannot correct: the mote has a profile.
    # Grow the site set to its DISC by admitting every connected pixel that is
    # itself recurrent at a lower depth, so that the corrected region covers
    # the whole shadow rather than only its core.
    print("\n=== 5. the gain field")
    from scipy import ndimage
    halo_seen = (per_tag <= -SEED_DEPTH / 2).sum(axis=0) >= RECURRENCE
    halo_deep = median_r <= -FLOOR_DEPTH / 3
    halo = halo_seen & halo_deep
    lab, nlab = ndimage.label(halo)
    keep_labels = np.unique(lab[site])
    keep_labels = keep_labels[keep_labels > 0]
    foot = np.isin(lab, keep_labels)
    n_foot = int(foot.sum())
    print(f"    halo candidates (>= {RECURRENCE}/18 at <= -{SEED_DEPTH * 50:.2f}% "
          f"and median <= -{FLOOR_DEPTH / 3 * 100:.2f}%): {int(halo.sum())}")
    print(f"    connected components touching a core site: {len(keep_labels)}"
          f" of {nlab}")
    print(f"    corrected footprint: {n_foot} plane px = {n_foot / N * 100:.5f}%"
          f" of the plane")
    sizes = ndimage.sum_labels(foot, lab, keep_labels)
    if len(sizes):
        print(f"    component size: median {np.median(sizes):.0f} px, "
              f"max {sizes.max():.0f} px, min {sizes.min():.0f} px")

    gain = np.ones((2344, 3514), np.float32)
    gain[foot] = (1.0 / (1.0 + median_r[foot])).astype(np.float32)
    print(f"    gain at footprint: median {np.median(gain[foot]):.5f}, "
          f"max {gain[foot].max():.5f}")
    np.save(OUT / "dust-gain.npy", gain)
    np.save(OUT / "dust-footprint.npy", foot)
    np.save(OUT / "dust-median-residual.npy", median_r)
    np.save(OUT / "dust-seen.npy", seen)
    res["gain"] = {
        "n_halo": int(halo.sum()), "n_components": int(len(keep_labels)),
        "n_components_total": int(nlab), "n_footprint": n_foot,
        "footprint_frac": n_foot / N,
        "median_component_px": float(np.median(sizes)) if len(sizes) else 0.0,
        "max_component_px": float(sizes.max()) if len(sizes) else 0.0,
        "median_gain": float(np.median(gain[foot])) if n_foot else 1.0,
        "max_gain": float(gain[foot].max()) if n_foot else 1.0,
    }

    (DATA / "01-dust.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\nwrote {DATA / '01-dust.json'}   [{time.time() - t0:.1f}s]")


if __name__ == "__main__":
    main()
