"""M48c script 08 -- can I kill the 2.05x plateau step?

Script 06 measured the median dark excess of a FIXED set of recurrent defects at
all 11 ISOs, converted to electrons through this profile's gain relation
`g = max(iso, 100) / 436.8`, and found two flat plateaus:

    ISO   50-250 :  5.90 - 6.67 e-   (mean 6.28, CV ~5%)
    ISO 400-2000 :  2.92 - 3.17 e-   (mean 3.06, CV ~3%)
    ratio 2.05, stepping exactly at second_base_iso = 400

Dark current is a rate of thermally generated electrons in silicon. It is set by
temperature and integration time, both of which are identical across these 11
groups (same sensor, all 1/100 s). It is generated at the photodiode, BEFORE the
analogue gain stage. It therefore CANNOT depend on the ISO dial. If the same
pixels imply twice as many electrons below the dual-gain switch as above it,
the gain relation used to convert DN to electrons must be wrong across that
switch by that factor -- `profile.rs` models the switch as a pure read-noise
change (`second_base_iso` selects `read_noise_e_*` and nothing else) while
`gain_dn_per_e` runs continuously through it.

That is a large claim about a constant I myself re-derived, so this script tries
to destroy it four ways. Each is a way the step could be an artefact of how the
defect set was chosen or measured rather than a property of the sensor.

  1. OUT-OF-SAMPLE SELECTION, BOTH DIRECTIONS. The worry: the recurrent set is
     chosen using detections at all 11 ISOs, so a pixel can enter the set by a
     noise excursion at the very ISO where I then measure it, inflating that
     ISO's value. Fix: select using ONLY high-mode detections (>=5 of the 7 ISOs
     >= 400) and measure the low-mode plateau, which is then entirely
     out-of-sample; then do the mirror image. If the step is selection bias it
     must shrink or inverct when the selection basis moves. If it is gain, it
     cannot move at all.

  2. AMPLITUDE STRATA. The worry: at ISO 50 the median defect is 1.42 DN against
     a noise sigma of 0.4448 DN, so the low-mode measurement is low-SNR and a
     skewed noise tail could lift a median. Fix: restrict to strong defects,
     where even the low-mode measurement is high-SNR. A noise artefact must
     weaken with amplitude; a gain error is scale-free and must not.

  3. RECURRENCE THRESHOLD SWEEP. If the step depends on how strictly I define
     "recurrent", it is a property of my criterion, not the sensor.

  4. A NULL SET. Random non-defect pixels have no dark-current excess, so their
     "plateau ratio" measures what this pipeline reports when there is nothing
     to report. It is the placebo for the whole construction.

I am not stating which way I expect these to come out. Two pre-registered
predictions in this milestone have already been refuted, and one measurement
(scripts 04/05) was run against the wrong pixel set entirely because a uint16
bitmask silently bitwise-ANDed to bit 0.

Reads only D:\\macro-dark-frames (READ-ONLY) and this milestone's own maps.
"""

from __future__ import annotations

import json
import pathlib

import exifread
import numpy as np
import rawpy

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
DARKS = pathlib.Path(r"D:\macro-dark-frames")

GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
SECOND_BASE_ISO = 400.0
SETTLING = 2
QUAD = {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)}
RNG = np.random.default_rng(48)


def highpass(a: np.ndarray) -> np.ndarray:
    up, dn = a[:-2, 1:-1], a[2:, 1:-1]
    lf, rt = a[1:-1, :-2], a[1:-1, 2:]
    return a[1:-1, 1:-1] - np.median(np.stack([up, dn, lf, rt]), axis=0)


def iso_dirs() -> list[tuple[int, pathlib.Path]]:
    out = []
    for d in sorted(DARKS.iterdir()):
        if not d.is_dir():
            continue
        arws = sorted(d.glob("*.ARW"))
        if not arws:
            continue
        with open(arws[0], "rb") as fh:
            tags = exifread.process_file(fh, stop_tag="ISOSpeedRatings")
        out.append((int(str(tags["EXIF ISOSpeedRatings"])), d))
    return sorted(out)


def plateau_ratio(isos: np.ndarray, e_by_iso: np.ndarray) -> tuple[float, float, float]:
    lo = e_by_iso[isos < SECOND_BASE_ISO]
    hi = e_by_iso[isos >= SECOND_BASE_ISO]
    return float(lo.mean()), float(hi.mean()), float(lo.mean() / hi.mean())


def main() -> None:
    dirs = iso_dirs()
    isos = np.array([i for i, _ in dirs], dtype=float)
    gains = np.maximum(isos, BASE_ISO) / GAIN_DIVISOR

    # Candidate superset: any pixel flagged at any ISO in any plane.
    cand = {n: np.load(DATA / f"hotcount-{n}.npy") >= 1 for n in QUAD}
    bits = {n: np.load(DATA / f"hotmask-{n}.npy") for n in QUAD}
    cnt = {n: np.load(DATA / f"hotcount-{n}.npy") for n in QUAD}
    idx = {n: np.nonzero(cand[n][1:-1, 1:-1]) for n in QUAD}
    print("candidate pixels per plane:", {n: int(idx[n][0].size) for n in QUAD})

    # One pass over the darks: excess at the candidate pixels, per ISO.
    exc = {n: np.zeros((len(dirs), idx[n][0].size)) for n in QUAD}
    nullexc = {n: np.zeros((len(dirs), 20000)) for n in QUAD}
    nr = {n: RNG.integers(0, 2340, 20000) for n in QUAD}
    nc = {n: RNG.integers(0, 3510, 20000) for n in QUAD}
    for k, (iso, d) in enumerate(dirs):
        arws = sorted(d.glob("*.ARW"))[SETTLING:]
        acc: dict[str, np.ndarray] = {}
        for p in arws:
            with rawpy.imread(str(p)) as r:
                v = r.raw_image_visible.astype(np.float64)
                v = v - float(np.mean(r.black_level_per_channel))
                for name, (ro, co) in QUAD.items():
                    pl = v[ro::2, co::2]
                    acc[name] = pl if name not in acc else acc[name] + pl
        for name in QUAD:
            hp = highpass(acc[name] / len(arws))
            exc[name][k] = hp[idx[name]]
            nullexc[name][k] = hp[nr[name], nc[name]]
        print(f"  ISO {iso:>4} read")

    # Per-candidate selection metadata, aligned with the exc columns.
    bit_lo = 0b0000000_1111  # ISO 50,100,200,250
    bit_hi = 0b1111111_0000  # ISO 400..2000
    sel_meta = {}
    for n in QUAD:
        b = bits[n][1:-1, 1:-1][idx[n]]
        sel_meta[n] = {
            "n_lo": np.bitwise_count(b & bit_lo),
            "n_hi": np.bitwise_count(b & bit_hi),
            "count": cnt[n][1:-1, 1:-1][idx[n]],
        }

    def report(label: str, pick: dict[str, np.ndarray]) -> dict[str, float]:
        per_iso = []
        ntot = sum(int(pick[n].sum()) for n in QUAD)
        for k in range(len(dirs)):
            vals = np.concatenate([exc[n][k][pick[n]] for n in QUAD])
            per_iso.append(np.median(vals) / gains[k])
        lo, hi, r = plateau_ratio(isos, np.array(per_iso))
        print(f"  {label:<44} n={ntot:>6}  lo={lo:6.3f}  hi={hi:6.3f}  ratio={r:6.3f}")
        return {"n": ntot, "low_mode_e": lo, "high_mode_e": hi, "ratio": r}

    res: dict[str, object] = {"_meta": {"gain_divisor": GAIN_DIVISOR}, "tests": {}}
    print("\n--- 1. out-of-sample selection, both directions ---")
    res["tests"]["select_high_measure_low_oos"] = report(
        "selected on ISO>=400 only (>=5 of 7)", {n: sel_meta[n]["n_hi"] >= 5 for n in QUAD}
    )
    res["tests"]["select_low_measure_high_oos"] = report(
        "selected on ISO<400 only (>=3 of 4)", {n: sel_meta[n]["n_lo"] >= 3 for n in QUAD}
    )

    print("\n--- 2. amplitude strata (on the recurrent set) ---")
    rec = {n: sel_meta[n]["count"] >= 6 for n in QUAD}
    strong_ref = {n: exc[n][-1] for n in QUAD}  # ISO 2000 excess as the amplitude proxy
    for q, lab in ((50, "median and above"), (90, "top decile")):
        thr = {n: np.percentile(strong_ref[n][rec[n]], q) for n in QUAD}
        res["tests"][f"amplitude_{q}"] = report(
            f"recurrent, {lab}", {n: rec[n] & (strong_ref[n] >= thr[n]) for n in QUAD}
        )

    print("\n--- 3. recurrence threshold sweep ---")
    for k in (3, 6, 9, 11):
        res["tests"][f"recurrence_{k}"] = report(
            f"hotcount >= {k}", {n: sel_meta[n]["count"] >= k for n in QUAD}
        )

    print("\n--- 4. null set (placebo) ---")
    per_iso = [
        np.median(np.concatenate([nullexc[n][k] for n in QUAD])) / gains[k]
        for k in range(len(dirs))
    ]
    lo, hi, r = plateau_ratio(isos, np.array(per_iso))
    print(f"  {'random non-defect pixels':<44} n= 80000  lo={lo:6.3f}  hi={hi:6.3f}  ratio={r:6.3f}")
    res["tests"]["null_random_pixels"] = {"low_mode_e": lo, "high_mode_e": hi, "ratio": r}

    ratios = [
        v["ratio"]
        for k, v in res["tests"].items()
        if k != "null_random_pixels" and np.isfinite(v["ratio"])
    ]
    print(
        f"\nplateau ratio across all {len(ratios)} defect-set variants: "
        f"{min(ratios):.3f} - {max(ratios):.3f}  (mean {np.mean(ratios):.3f})"
    )
    res["ratio_min"], res["ratio_max"] = float(min(ratios)), float(max(ratios))
    res["ratio_mean"] = float(np.mean(ratios))

    p = DATA / "plateau-robustness.json"
    p.write_text(json.dumps(res, indent=2, default=float))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
