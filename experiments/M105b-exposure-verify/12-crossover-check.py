"""
12-crossover-check.py -- chase the two numbers in 11 that did not fit.

PRE-REGISTERED BEFORE RUNNING. 11-quantisation-exposure.py returned all three
controls PASS and all three predictions CONFIRMED. That is precisely when a
result should be distrusted, so this file attacks the two rows that looked wrong
inside an otherwise clean table.

ANOMALY 1 -- AN IMPOSSIBLE-LOOKING COINCIDENCE.
  On `v5a-linear-60`, 6-bit (q = 1/63) and 4-bit (q = 1/15) produced dp =
  +5.942e-03, IDENTICAL to four significant figures, from two quantisers whose
  steps differ by 4.2x. Two different doses cannot honestly give one answer.
  HYPOTHESIS: p0 = 0.32739154 rounds onto 21/63 and onto 5/15, and BOTH ARE
  EXACTLY 1/3. The coincidence is in the grids, not in the code.
  TEST: report the landed grid value for every depth. CONFIRMED if both land on
  0.333333; FALSIFIED (and then it is a bug in my ladder) if they do not.

ANOMALY 2 -- THE ARM ORDERING INVERTS AT THE LAST DOSE.
  P-B predicted, and the aggregate reading recorded, that quantisation moves the
  percentile MORE than matched-RMS dither: 6 rows of 7 on both subjects. But the
  one row that disagrees is the LARGEST dose, on BOTH subjects, and there dither
  wins by 4x (v5a) and 3.4x (v4). An aggregate that reports 6/7 while the
  exception sits at the extreme of the ladder is hiding a crossover, and
  reporting "CONFIRMED" for it would be banking the favourable half.
  TWO CANDIDATE MECHANISMS, and they make opposite predictions:
    (a) REAL. Quantisation error is deterministic in value, so every sample near
        the rank moves TOGETHER by the distance from p0 to the nearest grid
        point -- which can be arbitrarily small. Dither's errors are
        independent, so the extreme upper tail contains samples that got nearly
        the full +q/2, and an upper percentile is dragged toward that bound.
        PREDICTS: dither attains a large and STABLE fraction of the Lipschitz
        bound q/2 at every dose, quantisation attains a fraction that varies
        wildly, and the crossover appears wherever quantisation happens to be
        near a grid point.
    (b) GRID LUCK. The 4-bit row is only special because 1/3 is on its grid.
        PREDICTS: at neighbouring depths that do not share a grid point with p0,
        quantisation returns to dominating and the crossover vanishes.
  DISCRIMINATOR: a dense depth ladder, 3..16 bits, reporting for each arm the
  fraction of the Lipschitz bound attained, |dp| / (q/2).

THE METHODOLOGICAL CLAIM THIS IS REALLY TESTING
-----------------------------------------------
The orchestrator has asked the fleet to replace shape-based triage with
dose-response. For a RANK statistic under QUANTISATION I predict that a
dose-response control is NON-MONOTONE BY CONSTRUCTION: |dp| is the distance from
p0 to the nearest multiple of q, a sawtooth in q, not a growing function of it.
A monotone slope beta would therefore be the WRONG SUMMARY for this class of
statistic, and an agent who fitted one and found it flat would wrongly conclude
immunity.
  PRE-REGISTERED: Spearman rho of |dp| against q will be HIGH for dither
  (smooth growth) and LOW for quantisation (sawtooth). Stated as a comparison
  because the absolute value depends on the ladder.
  FALSIFIED IF: quantisation's rho is within 0.15 of dither's, i.e. the two
  arms respond to dose alike and the sawtooth claim is wrong.

CONTROL -- the same one that caught my sign error in 07: a mechanism that also
explains the case it should not touch explains nothing. Dither must remain
MONOTONE. If both arms come out non-monotone, the non-monotonicity is in my
ladder or my percentile port, not in the quantiser.
"""

import json
import os

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M105"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

TARGET = 0.90
PERCENTILE = 99.9
STEPS_PER_STOP = 100.0
QUANTUM = 1.0 / STEPS_PER_STOP
LUMA_W = (0.2126729, 0.7151522, 0.0721750)
DITHER_SEEDS = 8

SUBJECTS = [("v5a-linear-60", "linear"), ("v4-plain-299", "sRGB")]


def nearest_rank_index(n, percentile):
    scale = 1_000_000
    bp = int(round(min(max(percentile, 0.0), 100.0) * (scale / 100.0)))
    return min(max((-((n * bp) // -scale)) - 1, 0), n - 1)


def percentile_shipped(xs):
    k = nearest_rank_index(xs.size, PERCENTILE)
    return float(np.partition(xs, k)[k])


def stops_for(p):
    s = float(np.clip(np.float32(np.log2(TARGET / p)), -6.0, 6.0))
    return round(s * STEPS_PER_STOP) / STEPS_PER_STOP


def spearman(a, b):
    """Rank correlation, written out rather than imported so the run has no
    scipy dependency and the definition is visible."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / d) if d else float("nan")


def luminance_of(path):
    a = tifffile.imread(path)
    if np.issubdtype(a.dtype, np.integer):
        a = a.astype(np.float32) / np.float32(np.iinfo(a.dtype).max)
    lum = (np.float32(LUMA_W[0]) * a[..., 0] + np.float32(LUMA_W[1]) * a[..., 1]
           + np.float32(LUMA_W[2]) * a[..., 2])
    return np.ascontiguousarray(lum.reshape(-1))


def main():
    report = {"dither_seeds": DITHER_SEEDS, "subjects": []}
    for name, kind in SUBJECTS:
        path = os.path.join(OUT, name + ".tif")
        if not os.path.exists(path):
            report["subjects"].append({"name": name, "error": "MISSING"})
            continue
        lum = luminance_of(path)
        p0 = percentile_shipped(lum)
        s0 = stops_for(p0)
        rows = []
        for bits in range(3, 17):
            q = 1.0 / (2.0 ** bits - 1.0)
            qs = np.float32(q)
            pq = percentile_shipped((np.round(lum / qs) * qs).astype(np.float32))
            dq = pq - p0
            landed = float(np.round(p0 / q) * q)
            dvals = []
            for seed in range(DITHER_SEEDS):
                rng = np.random.default_rng(1000 + seed)
                pd = percentile_shipped(
                    lum + rng.uniform(-q / 2.0, q / 2.0, size=lum.size).astype(np.float32))
                dvals.append(pd - p0)
            dvals = np.array(dvals)
            rows.append({
                "bits": bits, "q": q, "bound_q_over_2": q / 2.0,
                "quant_dp": dq, "quant_frac_of_bound": abs(dq) / (q / 2.0),
                "quant_landed_grid_value": landed,
                "quant_dstops": round(stops_for(pq) - s0, 4),
                "dither_dp_mean": float(dvals.mean()),
                "dither_dp_sd": float(dvals.std(ddof=1)),
                "dither_frac_of_bound": float(np.abs(dvals).mean()) / (q / 2.0),
                "dither_dominates": bool(abs(float(dvals.mean())) > abs(dq)),
            })

        qs_ = [r["q"] for r in rows]
        rho_q = spearman(qs_, [abs(r["quant_dp"]) for r in rows])
        rho_d = spearman(qs_, [abs(r["dither_dp_mean"]) for r in rows])

        # Anomaly 1: did 6-bit and 4-bit land on the same grid value?
        g6 = next(r for r in rows if r["bits"] == 6)["quant_landed_grid_value"]
        g4 = next(r for r in rows if r["bits"] == 4)["quant_landed_grid_value"]
        # Anomaly 2: where does dither take over?
        cross = [r["bits"] for r in rows if r["dither_dominates"]]

        readings = {
            "ANOMALY1_same_grid_value": {
                "bits6_landed": g6, "bits4_landed": g4,
                "identical": bool(abs(g6 - g4) < 1e-12),
                "is_one_third": bool(abs(g6 - 1.0 / 3.0) < 1e-9),
                "reading": ("CONFIRMED grid coincidence"
                            if abs(g6 - g4) < 1e-12 else "FALSIFIED"),
            },
            "ANOMALY2_crossover": {
                "depths_where_dither_dominates": cross,
                "is_isolated_to_coarsest": bool(cross and max(cross) <= 5),
                "reading": ("(a) REAL: dither dominates over a contiguous coarse range"
                            if len(cross) >= 3 else
                            "(b) GRID LUCK: dither dominates only sporadically"),
            },
            "NONMONOTONE_quant": {
                "spearman_q_vs_absdp_quant": round(rho_q, 4),
                "spearman_q_vs_absdp_dither": round(rho_d, 4),
                "gap": round(rho_d - rho_q, 4),
                "reading": ("CONFIRMED: quantisation is a sawtooth in dose"
                            if (rho_d - rho_q) > 0.15 else
                            "FALSIFIED: both arms respond to dose alike"),
            },
            "CONTROL_dither_monotone": (
                "PASS" if rho_d > 0.9 else "FAIL -- non-monotonicity is in my ladder"),
        }
        report["subjects"].append({
            "name": name, "kind": kind, "p99_9": p0, "stops": s0,
            "rows": rows, "readings": readings})

    for dst in (os.path.join(OUT, "12-crossover-check.json"),
                os.path.join(DATA, "12-crossover-check.json")):
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    for s in report["subjects"]:
        if "error" in s:
            print("%-16s MISSING" % s["name"])
            continue
        print("=" * 96)
        print("%s (%s)  p99.9=%.8f  stops=%+.2f" % (s["name"], s["kind"],
                                                    s["p99_9"], s["stops"]))
        print("  %5s %11s | %12s %8s %11s | %12s %8s | %s"
              % ("bits", "q", "quant dp", "frac", "landed", "dither dp", "frac", "wins"))
        for r in s["rows"]:
            print("  %5d %11.3e | %+12.3e %8.4f %11.6f | %+12.3e %8.4f | %s"
                  % (r["bits"], r["q"], r["quant_dp"], r["quant_frac_of_bound"],
                     r["quant_landed_grid_value"], r["dither_dp_mean"],
                     r["dither_frac_of_bound"],
                     "dither" if r["dither_dominates"] else "quant"))
        print("")
        print("  " + json.dumps(s["readings"], indent=2).replace("\n", "\n  "))
    print("")
    print("wrote 12-crossover-check.json")


if __name__ == "__main__":
    main()
