"""M116-promotion — the scorer.

Computes exactly the metrics registered in `prereg.txt` section 5, and nothing
else. Every mask comes from the M0 arm (`--gate 0`), which is not compared, so
no mask is derived from an arm under test.

Outputs `C:\\dev\\strehl-out\\M116\\scores.json` and prints a table.
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import uniform_filter

ROOT = Path(r"C:\dev\strehl-out\M116")
MEASURE = ROOT / "measure"

# Population fractions, fixed in prereg section 5.
FLAT_FRAC = 0.20
DET_FRAC = 0.20
HP_BOX = 5
STRUCT_DOWN = 4
STRUCT_WIN = 33
CROP = 512

SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]

# Aligned arms. A0 is the reference every delta is taken against.
ALIGNED_ARMS = ["A0", "A1", "A2", "A3", "A4", "P1", "N1", "T1", "T2"]
UNALIGNED_ARMS = ["B1u", "B0"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def green(path: Path) -> np.ndarray:
    """The merge's green plane, (G1+G2)/2, as f64."""
    a = tifffile.imread(path)
    assert a.ndim == 3 and a.shape[2] == 3, f"{path} is {a.shape}, want HxWx3"
    g = a[:, :, 1].astype(np.float64)
    assert g.ndim == 2, "the plane must be extracted before any separable filter"
    return g


def highpass(g: np.ndarray) -> np.ndarray:
    """L - box5(L). `g` is 2-D by assertion above, so no non-spatial axis can be
    smoothed (AGENTS.md rule 23)."""
    return g - uniform_filter(g, size=HP_BOX, mode="nearest")


def structure(g: np.ndarray) -> np.ndarray:
    """Local sd of the mask arm at a coarse scale.

    Downsampled 4x FIRST so the ranking is driven by scene structure and not by
    the mask arm's own pixel noise, then upsampled back by nearest neighbour.
    """
    h, w = g.shape
    hh, ww = h // STRUCT_DOWN, w // STRUCT_DOWN
    blocks = g[: hh * STRUCT_DOWN, : ww * STRUCT_DOWN]
    small = blocks.reshape(hh, STRUCT_DOWN, ww, STRUCT_DOWN).mean(axis=(1, 3))
    m1 = uniform_filter(small, size=STRUCT_WIN, mode="nearest")
    m2 = uniform_filter(small * small, size=STRUCT_WIN, mode="nearest")
    sd = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    up = np.repeat(np.repeat(sd, STRUCT_DOWN, axis=0), STRUCT_DOWN, axis=1)
    out = np.zeros((h, w), dtype=np.float64)
    out[: up.shape[0], : up.shape[1]] = up[:h, :w]
    if up.shape[0] < h:
        out[up.shape[0]:, :] = out[up.shape[0] - 1, :]
    if up.shape[1] < w:
        out[:, up.shape[1]:] = out[:, up.shape[1] - 1][:, None]
    return out


def masks(struct: np.ndarray):
    flat_cut = np.quantile(struct, FLAT_FRAC)
    det_cut = np.quantile(struct, 1.0 - DET_FRAC)
    return struct <= flat_cut, struct >= det_cut


def best_window(struct: np.ndarray, want_high: bool):
    """Top-left corner of the CROPxCROP window of highest (or lowest) mean
    structure, on the plane grid.

    Index convention, because getting this wrong is silent: uniform_filter is
    centred, so integ[r, c] is the mean over rows [r-half, r+half). Slicing
    integ[half:h-half, half:w-half] therefore makes valid[i, j] the mean over
    rows [i, i+CROP) and cols [j, j+CROP) -- i and j ARE the top-left corner
    already. An earlier revision of this function subtracted CROP//2 from these,
    treating them as a centre, which slid every crop 256 plane px diagonally off
    the subject. The caller checks the returned window empirically.
    """
    h, w = struct.shape
    # cval must NOT be NaN: uniform_filter carries a running sum, so a single
    # NaN in the padding propagates to every output pixel, `valid` becomes
    # all-NaN, argmax returns 0, and every crop silently pins to the top-left
    # corner of the frame. With cval=0 the `valid` slice below is exact,
    # because every window it indexes lies wholly inside the image and so
    # never touches the padding at all.
    integ = uniform_filter(struct, size=CROP, mode="constant", cval=0.0)
    half = CROP // 2
    valid = integ[half:h - half, half:w - half]
    if not np.all(np.isfinite(valid)):
        raise SystemExit("best_window: non-finite window means")
    idx = np.argmax(valid) if want_high else np.argmin(valid)
    y, x = np.unravel_index(idx, valid.shape)
    return int(x), int(y)


def score_plane(g: np.ndarray, mflat: np.ndarray, mdet: np.ndarray) -> dict:
    hp = highpass(g)
    sd_flat = float(hp[mflat].std())
    sd_det = float(hp[mdet].std())
    n = float(np.log10(sd_flat))
    d = float(np.log10(sd_det))
    return {
        "sd_flat": sd_flat,
        "sd_det": sd_det,
        "N": n,
        "D": d,
        "Q": d - n,
    }


def noise_decomposition(ref: dict, arm: dict) -> dict:
    """How much of DELTA-D is merely the flat-region noise change reappearing
    inside the detail mask?

    ADDED AFTER THE FIRST DATA WERE SEEN, and disclosed as post-hoc in the
    report. It is not a bar and it moves no bar. It decomposes an observed
    number, and it can go either way: if a soft gate's detail drop turned out to
    be entirely the same noise reduction seen in the flat region, that would
    RESCUE the instrument from the B1 bar rather than condemn it.

    Model: the detail mask carries structure plus noise in quadrature,
    `sd_det^2 = S^2 + n^2`, and the flat mask estimates `n`. If an arm changes
    only `n`, by the ratio it changed the flat mask by, then `sd_det` must move
    to `sqrt(S^2 + (r*n)^2)` and no further.
    """
    n0, d0 = ref["sd_flat"], ref["sd_det"]
    r = arm["sd_flat"] / n0
    s_sq = max(d0 * d0 - n0 * n0, 0.0)
    pred = np.sqrt(s_sq + (r * n0) ** 2)
    d_pred = float(np.log10(pred)) - ref["D"]
    d_obs = arm["D"] - ref["D"]
    return {
        "dD_observed": d_obs,
        "dD_explained_by_noise": d_pred,
        "dD_unexplained": d_obs - d_pred,
        "noise_share_of_detail_variance": (n0 * n0) / (d0 * d0),
    }


def run_group(subject: str, mask_arm: str, arms: list, tag: str) -> dict:
    mp = MEASURE / f"{subject}__{mask_arm}.tif"
    if not mp.exists():
        print(f"  [{tag}] mask arm {mp.name} missing, skipping group")
        return {}
    struct = structure(green(mp))
    mflat, mdet = masks(struct)
    dx_det, dy_det = best_window(struct, True)
    dx_flat, dy_flat = best_window(struct, False)

    # The crop windows are what a human will look at, so do not trust the
    # arithmetic that produced them -- measure what they actually contain. A
    # detail window that does not sit far above the flat window is a harness
    # bug, not a picture, and must not be shipped as evidence.
    det_win = struct[dy_det:dy_det + CROP, dx_det:dx_det + CROP]
    flat_win = struct[dy_flat:dy_flat + CROP, dx_flat:dx_flat + CROP]
    det_s, flat_s = float(det_win.mean()), float(flat_win.mean())
    ratio = det_s / max(flat_s, 1e-12)
    print(f"  crop check: detail window mean structure {det_s:.2f} at "
          f"{(dx_det, dy_det)}, flat {flat_s:.2f} at {(dx_flat, dy_flat)}, "
          f"ratio {ratio:.1f}x")
    if det_win.shape != (CROP, CROP) or flat_win.shape != (CROP, CROP):
        raise SystemExit(f"[{tag}] crop window fell off the grid")
    # Guard on the signature of the HARNESS bug, not on subject character. The
    # bug this caught pinned both windows to the same coordinate with identical
    # means (ratio exactly 1.00 at (0,0)); a low-but-distinct ratio is instead a
    # true fact about a subject with no structurally flat region, and foam is
    # such a subject. So: refuse degenerate windows, report the ratio.
    if (dx_det, dy_det) == (dx_flat, dy_flat):
        raise SystemExit(
            f"[{tag}] detail and flat windows are the same window at "
            f"{(dx_det, dy_det)} -- the window search is degenerate")
    if ratio < 3.0:
        print(f"  WARNING: {tag} crop windows separate by only {ratio:.2f}x; "
              "this subject has no structurally flat region, so its crops are "
              "two samples of one texture, not a detail/flat contrast")

    out = {
        "mask_arm": mask_arm,
        "mask_source": str(mp),
        "n_flat_px": int(mflat.sum()),
        "n_det_px": int(mdet.sum()),
        "crop_detail_plane_xy": [dx_det, dy_det],
        "crop_flat_plane_xy": [dx_flat, dy_flat],
        "crop_detail_struct_mean": det_s,
        "crop_flat_struct_mean": flat_s,
        "crop_separation_ratio": ratio,
        "arms": {},
    }
    for arm in arms:
        p = MEASURE / f"{subject}__{arm}.tif"
        if not p.exists():
            print(f"  [{tag}] {p.name} missing")
            continue
        s = score_plane(green(p), mflat, mdet)
        s["sha256"] = sha256(p)
        s["bytes"] = p.stat().st_size
        s["shape"] = list(green(p).shape)
        out["arms"][arm] = s
    return out


def main() -> int:
    results = {}
    for subject in SUBJECTS:
        print(f"== {subject} ==")
        aligned = run_group(subject, "M0", ALIGNED_ARMS, "aligned")
        unaligned = run_group(subject, "M0u", UNALIGNED_ARMS, "unaligned")
        results[subject] = {"aligned": aligned, "unaligned": unaligned}

        ref = aligned.get("arms", {}).get("A0")
        if ref:
            print(f"  mask separation D-N on the mask arm's own scale: "
                  f"{ref['Q']:.4f} dex "
                  f"(noise share of detail variance "
                  f"{100.0 * (ref['sd_flat'] ** 2) / (ref['sd_det'] ** 2):.3f}%)")
            print(f"  {'arm':22s} {'N':>9s} {'D':>9s} {'Q':>9s} "
                  f"{'dN':>9s} {'dD':>9s} {'dQ':>9s} {'dD_unexp':>10s}  sha")
            for arm, s in aligned["arms"].items():
                dec = noise_decomposition(ref, s)
                s["decomposition"] = dec
                print(f"  {arm:22s} {s['N']:9.5f} {s['D']:9.5f} {s['Q']:9.5f} "
                      f"{s['N'] - ref['N']:+9.5f} {s['D'] - ref['D']:+9.5f} "
                      f"{s['Q'] - ref['Q']:+9.5f} "
                      f"{dec['dD_unexplained']:+10.5f}  {s['sha256'][:12]}")
        u = unaligned.get("arms", {})
        if "B0" in u and "B1u" in u:
            print(f"  M85: D(merge,unaligned) - D(single frame) = "
                  f"{u['B1u']['D'] - u['B0']['D']:+.5f} dex")

    (ROOT / "scores.json").write_text(json.dumps(results, indent=2))
    print(f"\nwrote {ROOT / 'scores.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
