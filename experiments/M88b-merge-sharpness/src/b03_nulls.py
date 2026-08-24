"""M88b b03 — THE NULLS, MEASURED BEFORE ANY TREATMENT.

M57's `dsig` recovered a planted blur to -0.04% and was exactly degree 0 in
gain, and it still died -- because it failed its own noise null at 0.343 px
per 512^2 ROI where truth is exactly zero.  M82's 15 finite prices then maxed
out at 51.1% of that bound and all 18 rows abstained.  An instrument whose
null is not measured cannot price anything.

So the null comes first, on the real merge planes, before the treatment arm
exists.

  N0  determinism   two byte-identical merges.  Delta must be EXACTLY 0.
  N1  noise         the same plane with two independent noise realisations at
                    the merge's own measured noise level.  The sd of Delta is
                    the instrument's floor -- the M57 analogue.
  N2  photometry    a global gain difference between arms.  M24 measured real
                    stacks drifting 6.84% and 8.93% with CONSTANT EXIF, and
                    the merge fits no per-frame gain term, so this is a live
                    nuisance and not a hypothetical one.
  N3  offset        a global pedestal difference between arms.
  N4  translation   a whole-image sub-pixel shift.  Alignment moves the image,
                    so the ON arm's edge is not at the OFF arm's coordinates.
                    This tests that refitting the edge per arm absorbs it.
  N5  interpolation the price the ON arm pays merely for being resampled: an
                    IDENTITY warp through the same spline.  This is a BIAS,
                    not a null, and it biases AGAINST alignment.

Writes out/b03_nulls.json.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88blib as B  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "out"

N_SEED = 32

# PRE-DECLARED ROI ADMISSION BAR.  An ROI is admitted to the treatment only if
# its noise null is small enough for a treatment effect to be visible above it.
# 1.0 um is about 3% of a typical 32 um merge-plane rise.  Declared here,
# before any treatment arm exists, and applied without exception.
ADMIT_P95_UM = 1.0


def load_rois():
    surv = json.loads((OUT / "b01_survey.json").read_text(encoding="utf-8"))
    rois = []
    for label, d in surv["stacks"].items():
        for c in d["chosen"]:
            rois.append((label, c["name"], (c["row"], c["col"], c["win"],
                                            c["win"]), c["axis"]))
    return rois


TIF = {
    "bee-3-cpl": "bee3_gate4.tiff",
    "bee-2-cpl": "bee_2_cpl_gate4.tiff",
    "109MSDCF": "109_gate4.tiff",
    "ruler": "highly_angled_ruler_mm_cpl_gate4.tiff",
    "tweezers": "tweezers_cpl_gate4.tiff",
    "wtext1": "wrapped_text_1_gate4.tiff",
}


def round_trip(plane, n, step=0.5):
    """Resample n times out and n times back: net zero shift, 2n interpolations.

    An IDENTITY warp is NOT a test of the interpolator -- scipy's spline shift
    at an exactly integer offset is exact, so an earlier version of this
    control read 0.0000 for every ROI and measured nothing.  A round trip at a
    half-pixel phase exercises the kernel while leaving the geometry unmoved,
    so any width it adds is purely the price of resampling.
    """
    p = plane
    for _ in range(n):
        p = B.shift_subpixel(p, step, step)
        p = B.shift_subpixel(p, -step, -step)
    return p


def measure_flat_noise(plane, n=24, win=64):
    """Robust per-pixel noise sd, from the flattest windows of the plane.

    An earlier version rejected a window when the mean |gradient| exceeded a
    fixed 4.0 DN/px.  Merge planes run to tens of thousands of DN, so that
    threshold rejected every window and returned nan.  The flatness test is
    now RELATIVE to the window level, and the noise itself is estimated from
    the first difference -- sd = 1.4826 * MAD(diff) / sqrt(2) -- which is
    insensitive to the smooth structure that survives the flatness test.
    """
    h, w = plane.shape
    rng = np.random.default_rng(0)
    sds, means = [], []
    for _ in range(600):
        r = int(rng.integers(0, h - win))
        c = int(rng.integers(0, w - win))
        p = plane[r:r + win, c:c + win]
        mu = float(p.mean())
        if mu <= 0:
            continue
        gy, gx = np.gradient(p)
        if (np.abs(gy).mean() + np.abs(gx).mean()) / mu > 0.02:
            continue
        d = np.diff(p, axis=1).ravel()
        mad = float(np.median(np.abs(d - np.median(d))))
        sds.append(1.4826 * mad / np.sqrt(2.0))
        means.append(mu)
    if not sds:
        return float("nan"), float("nan")
    k = np.argsort(sds)[:n]
    return (float(np.median(np.array(sds)[k])),
            float(np.median(np.array(means)[k])))


def main():
    rois = load_rois()
    planes = {k: B.read_merge_plane(DATA / v, "G") for k, v in TIF.items()}
    report = {"n_seed": N_SEED, "rois": [
        dict(stack=s, name=n, roi=list(r), axis=a) for s, n, r, a in rois]}

    print("=" * 78)
    print("N0  DETERMINISM: two byte-identical merges of the same input")
    print("=" * 78)
    a = DATA / "109_gate4.tiff"
    b = DATA / "109_gate4_rerun.tiff"
    ha = hashlib.sha256(a.read_bytes()).hexdigest()
    hb = hashlib.sha256(b.read_bytes()).hexdigest()
    pa, pb = B.read_merge_plane(a, "G"), B.read_merge_plane(b, "G")
    print(f"  sha256 A  {ha[:32]}")
    print(f"  sha256 B  {hb[:32]}")
    print(f"  byte identical: {ha == hb}")
    n0 = []
    for s, name, roi, axis in rois:
        if s != "109MSDCF":
            continue
        d = B.paired_delta(pa, pb, roi, axis)
        n0.append(d["delta_um"])
        print(f"  {name:>5}  rise_off {d['rise_off_um']:7.3f}  "
              f"rise_on {d['rise_on_um']:7.3f}  delta {d['delta_um']:+.6f} um")
    n0_max = float(np.max(np.abs(n0))) if n0 else float("nan")
    print(f"\n  |delta|max = {n0_max:.9f} um   "
          f"-> {'EXACTLY ZERO' if n0_max == 0.0 else 'NOT ZERO'}")
    report["N0"] = dict(sha_a=ha, sha_b=hb, byte_identical=ha == hb,
                        deltas_um=n0, max_abs_um=n0_max)

    print()
    print("=" * 78)
    print("N1  NOISE FLOOR: independent noise realisations, no sharpness change")
    print("=" * 78)
    noise = {}
    for k, p in planes.items():
        sd, mean = measure_flat_noise(p)
        noise[k] = sd
        print(f"  {k:>10}: flat-window noise sd {sd:7.2f} DN "
              f"at mean level {mean:8.0f} DN")
    n1_rows = []
    for s, name, roi, axis in rois:
        p = planes[s]
        sd = noise[s]
        ds, nfail = [], 0
        for seed in range(N_SEED):
            rng = np.random.default_rng(1000 + seed)
            pa2 = p + rng.normal(0.0, sd, p.shape)
            pb2 = p + rng.normal(0.0, sd, p.shape)
            v = B.paired_delta(pa2, pb2, roi, axis)["delta_um"]
            if np.isfinite(v):
                ds.append(v)
            else:
                nfail += 1
        ds = np.array(ds)
        ok = ds.size >= N_SEED // 2
        p95 = float(np.percentile(np.abs(ds), 95)) if ok else float("inf")
        admit = ok and nfail == 0 and p95 <= ADMIT_P95_UM
        n1_rows.append(dict(stack=s, name=name, n_ok=int(ds.size),
                            n_fail=nfail,
                            mean_um=float(ds.mean()) if ok else float("nan"),
                            sd_um=float(ds.std(ddof=1)) if ok else float("nan"),
                            p95_abs_um=p95, admitted=bool(admit)))
        print(f"  {name:>5}  n_ok {ds.size:3d}  fail {nfail:2d}  "
              f"mean {ds.mean() if ok else float('nan'):+8.4f}  "
              f"sd {ds.std(ddof=1) if ok else float('nan'):8.4f}  "
              f"p95|d| {p95:8.4f}  "
              f"{'ADMIT' if admit else 'REJECT'}")
    adm = [r for r in n1_rows if r["admitted"]]
    if not adm:
        raise SystemExit("no ROI passes the pre-declared null gate")
    floor = float(np.max([r["p95_abs_um"] for r in adm]))
    pooled = float(np.sqrt(np.mean([r["sd_um"] ** 2 for r in adm])))
    print(f"\n  admitted {len(adm)} of {len(n1_rows)} ROIs "
          f"at the pre-declared bar p95|delta| <= {ADMIT_P95_UM} um")
    print(f"  pooled sd over admitted   = {pooled:.4f} um")
    print(f"  worst admitted p95|delta| = {floor:.4f} um   <- INSTRUMENT FLOOR")
    report["N1"] = dict(noise_sd_dn=noise, rows=n1_rows,
                        admit_bar_um=ADMIT_P95_UM,
                        n_admitted=len(adm),
                        pooled_sd_um=pooled, floor_um=floor)
    rois = [(s, n, r, a) for (s, n, r, a) in rois
            if any(x["name"] == n and x["admitted"] for x in n1_rows)]

    print()
    print("=" * 78)
    print("N2-N5  NUISANCE ARMS: perturbations that are NOT sharpness changes")
    print("=" * 78)
    arms = {
        "N2_gain_+8.93pct": lambda p: p * 1.0893,
        "N2_gain_-6.84pct": lambda p: p * 0.9316,
        "N3_pedestal_+200dn": lambda p: p + 200.0,
        "N4_shift_0.37px": lambda p: B.shift_subpixel(p, 0.37, -0.21),
        "N4_shift_int_3px": lambda p: B.shift_subpixel(p, 3.0, -2.0),
        "N5_roundtrip_x1": lambda p: round_trip(p, 1),
        "N5_roundtrip_x2": lambda p: round_trip(p, 2),
        "N5_roundtrip_x4": lambda p: round_trip(p, 4),
    }
    n_rows = []
    print(f"  {'arm':>19} {'max|delta|':>11} {'mean delta':>11} "
          f"{'vs floor':>9}  {'registered':>10}")
    for arm, fn in arms.items():
        for reg, tag in ((False, "fixed-win"), (True, "registered")):
            ds, shifts = [], []
            for s, name, roi, axis in rois:
                p = planes[s]
                q = fn(p)
                if reg:
                    d = B.paired_delta_registered(p, q, roi, axis)
                    shifts.append((d.get("shift_dy"), d.get("shift_dx")))
                else:
                    d = B.paired_delta(p, q, roi, axis)
                if np.isfinite(d["delta_um"]):
                    ds.append(d["delta_um"])
            ds = np.array(ds)
            mx = float(np.max(np.abs(ds)))
            n_rows.append(dict(arm=arm, registered=reg,
                               deltas_um=ds.tolist(), max_abs_um=mx,
                               mean_um=float(ds.mean()),
                               ratio_to_floor=mx / floor,
                               shifts=shifts))
            print(f"  {arm:>19} {mx:11.4f} {ds.mean():+11.4f} "
                  f"{mx / floor:8.2f}x  {tag:>10}")
    report["N2_N5"] = n_rows

    print()
    print("  DOES REGISTRATION REMOVE THE DISPLACEMENT ARTIFACT?")
    for arm in ("N4_shift_0.37px", "N4_shift_int_3px"):
        a = next(x for x in n_rows if x["arm"] == arm and not x["registered"])
        b = next(x for x in n_rows if x["arm"] == arm and x["registered"])
        print(f"    {arm:>18}: fixed-window {a['max_abs_um']:7.4f} um "
              f"-> registered {b['max_abs_um']:7.4f} um "
              f"({a['max_abs_um'] / max(b['max_abs_um'], 1e-9):5.1f}x better)")

    print()
    print("  N5 is a BIAS, not a null: it is the width the ON arm pays purely")
    print("  for being resampled, and it makes alignment look WORSE than it is.")
    print("  Delta is rise(OFF) - rise(RESAMPLED), so a NEGATIVE mean means")
    print("  resampling widened the edge, which is the expected direction.")
    for k in ("N5_roundtrip_x1", "N5_roundtrip_x2", "N5_roundtrip_x4"):
        r = next(x for x in n_rows if x["arm"] == k and x["registered"])
        n_int = 2 * int(k[-1])
        print(f"    {k:>18}: {n_int:2d} interpolations -> "
              f"mean {r['mean_um']:+.4f} um, "
              f"per interpolation {r['mean_um'] / n_int:+.4f} um")
    r1 = next(x for x in n_rows
              if x["arm"] == "N5_roundtrip_x1" and x["registered"])
    report["interp_penalty_per_resample_um"] = float(r1["mean_um"] / 2.0)

    OUT.mkdir(exist_ok=True)
    (OUT / "b03_nulls.json").write_text(json.dumps(report, indent=1),
                                        encoding="utf-8")
    print("\nwrote out/b03_nulls.json")


if __name__ == "__main__":
    main()
