"""
11-quantisation-exposure.py -- re-derive quantisation exposure for M105b's
estimator, after the orchestrator withdrew the absolute-vs-ratio triage rule.

THIS DOCSTRING IS THE PRE-REGISTRATION AND IS COMMITTED BEFORE THE FIRST RUN.

======================================================================
WHY I CANNOT ANSWER THIS FROM THE SHAPE OF MY EXPRESSION
======================================================================

The withdrawn rule would have cleared me instantly and for a bad reason: my
statistic is a ratio, and the numerator is a constant. The orchestrator's
instruction is that the form of an expression is not evidence. So this file
does the two things it says are admissible: expand algebraically and see which
factor the perturbation lands in, then measure it with a dose-response control.

THE ESTIMATOR UNDER TEST (shipped, `color.rs:758-796`):

    stops = round_to_hundredths( clamp_+-6( log2( TARGET / p ) ) )
    where p = percentile_in_place(luma, 99.9), TARGET = 0.90

EXPANSION. There is exactly one measured term, `p`, and it is an ORDER
STATISTIC -- the value at rank k = nearest_rank_index(N, 99.9). A perturbation
e_i on each sample lands in `p` and nowhere else, so

    dstops = -log2(1 + dp/p),  dp = p' - p

and to first order dstops ~= -dp / (p ln2). The perturbation is divided by `p`,
NOT by the number of samples: averaging does not help me.

WHERE EACH OF THE THREE REFUTATIONS LANDS ON ME
-----------------------------------------------
V-M113 (value vs position). My statistic reads a pixel VALUE, at a rank. I am
  in the EXPOSED class on M113's axis and I do not get to claim location-
  statistic dithering. But M113's threshold is "~12 distinct levels per FITTED
  WINDOW"; my statistic fits nothing and has no window. So M113 tells me I am
  exposed without telling me how much, and I must supply my own number. I also
  report the distinct-level count in the neighbourhood of the rank, so the
  comparison to its threshold can be made rather than asserted.

M111 (term disparity D = max/min of the combined terms). D is UNDEFINED for me:
  `TARGET` is a compile-time constant carrying no error, so there are not two
  measured terms to be disparate. This is the one place I differ structurally
  from the fleet's defect-detection contrasts -- and because a structural
  argument is exactly what was just withdrawn, it is not allowed to be my
  answer. It is a reason to expect a small number, not a substitute for one.

M115 (a common floor factorises into the noise factor and reverses sign). My
  statistic contains no noise term for a floor to attach to. But the honest
  translation is not "immune": quantisation inflates variance, variance widens
  the upper tail, and p99.9 LIVES IN THE UPPER TAIL. So I should expect a
  systematic bias, not a zero-mean wobble.

======================================================================
PRE-REGISTERED PREDICTIONS -- each falsifiable, stated before the first run
======================================================================

P-A  LIPSCHITZ. Order statistics are 1-Lipschitz in sup-norm, so |dp| <=
     max_i|e_i| at EVERY dose in BOTH arms. This is the load-bearing claim; if
     it fails my expansion is wrong and nothing below is interpretable.
     FALSIFIED IF: any dose in any arm has |dp| > max|e| (beyond 1e-9 slack).

P-B  THE ORCHESTRATOR'S 16x SHOULD NOT REPRODUCE, AND SHOULD INVERT.
     Their result is that quantisation error, being deterministic in the pixel
     value, is booked as SIGNAL by a differencing noise estimator, so matched-
     power dither reads 16x noisier. A rank statistic is not a noise estimator,
     so that mechanism has nothing to act on. Instead:
       - quantisation gives dp = q*round(p/q) - p, a deterministic SAWTOOTH in
         p bounded by q/2 -- first order in q, and its SIGN OSCILLATES with
         dose rather than accumulating;
       - matched-RMS dither (uniform on [-q/2, +q/2], since RMS a/sqrt3 =
         q/sqrt12 gives a = q/2) perturbs samples independently, widening the
         tail, so dp > 0 CONSISTENTLY but only to second order.
     PREDICTION: |dp| is LARGER for QUANT than for DITHER at matched RMS at
     small dose, and QUANT's sign oscillates while DITHER's does not.
     THIS IS THE OPPOSITE ORDERING TO THE FLEET-WIDE HEADLINE. If the 16x does
     reproduce here it is a much bigger finding than my clearance and it gets
     reported as the headline instead.

P-C  AT THE PIPELINE'S REAL DOSE THE SHIPPED NUMBER DOES NOT MOVE.
     Real steps: 14-bit ARW over black 512 / white 16383 -> q_in = 1/15871 =
     6.30e-5; 16-bit output -> q_out = 1/65535 = 1.526e-5. With p ~= 0.31,
     the bound predicts |dstops| <= (q/2)/(p ln2) ~= 1.5e-4 stops, which is
     ~68x below the 0.01-stop reporting quantum of AUTO_EXPOSURE_STEPS_PER_STOP.
     PREDICTION: |dstops| < 0.01 at both real doses, i.e. the reported number
     is bit-unchanged.
     FALSIFIED IF: |dstops| >= 0.01 at either real dose.

CONTROLS -- all three must read as stated or the run is void
------------------------------------------------------------
C-NULL        dose 0 must give dstops exactly 0.0. A quiet instrument.
C-POS         plant a known gain g in {0.5, 2.0}: the estimator must recover
              dstops = -log2(g) to within one 0.01 quantum. An instrument that
              cannot see a planted 1-stop change cannot certify a null.
C-RESPONSIVE  at an absurd dose (4-bit, q = 1/15) the estimator MUST move by
              MORE than the reporting quantum. Without this, every null above
              is indistinguishable from a dead instrument -- the exact failure
              the orchestrator flagged for STREHL_FIX_CA.

KNOWN THREAT, STATED BEFORE MEASURING
-------------------------------------
The renders on disk are 16-bit TIFs, so my "dose 0" arm is ALREADY quantised at
q0 = 1/65535. I am measuring added quantisation on top of an existing floor. For
q >> q0 the ladder is clean; for q ~ q0 it is confounded and I will say so
rather than read those rows. This is itself an instance of the orchestrator's
"possibly-narrowed data" warning applied to my own instrument.

Second threat: the chooser reads linear luminance BEFORE the clamp and before
the transfer curve (M105b SS4.9, the clamp blind spot). A post-file instrument
is valid only for stacks whose implied p99.9 < 1.0, which for `bee-3-cpl` is
0.3096 -- valid. I run the ladder on the LINEAR render AND on the sRGB render;
if the conclusion is the same on both, the transfer curve is not carrying it.
"""

import hashlib
import json
import os

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M105"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

TARGET = 0.90
PERCENTILE = 99.9
MAX_STOPS = 6.0
STEPS_PER_STOP = 100.0
QUANTUM = 1.0 / STEPS_PER_STOP

# color.rs:440, SRGB_TO_XYZ_D65[1] -- the luminance row.
LUMA_W = (0.2126729, 0.7151522, 0.0721750)

# The pipeline's two real quantisation steps.
Q_ARW = 1.0 / (16383.0 - 512.0)
Q_TIF = 1.0 / 65535.0

SUBJECTS = [
    ("v5a-linear-60", "linear (the measurement output)"),
    ("v4-plain-299", "sRGB (the viewing output)"),
]


def nearest_rank_index(n, percentile):
    """Port of color.rs:489. Basis-point integer rank, ceiling division."""
    if n == 0:
        return None
    scale = 1_000_000
    bp = int(round(min(max(percentile, 0.0), 100.0) * (scale / 100.0)))
    rank = -((n * bp) // -scale)  # div_ceil
    return min(max(rank - 1, 0), n - 1)


def percentile_shipped(xs, percentile=PERCENTILE):
    k = nearest_rank_index(xs.size, percentile)
    if k is None:
        return None
    return float(np.partition(xs, k)[k])


def stops_for(p, target=TARGET):
    """Port of color.rs:775-796 from the percentile onward."""
    if p is None or not np.isfinite(p) or p <= 0.0:
        return None
    s = np.log2(target / p)
    if not np.isfinite(s):
        return None
    s = float(np.clip(np.float32(s), -MAX_STOPS, MAX_STOPS))
    return round(s * STEPS_PER_STOP) / STEPS_PER_STOP


def luminance_of(path):
    a = tifffile.imread(path)
    info = {"shape": list(a.shape), "dtype": str(a.dtype)}
    if np.issubdtype(a.dtype, np.integer):
        full = float(np.iinfo(a.dtype).max)
        info["container_max"] = full
        a = a.astype(np.float32) / np.float32(full)
    else:
        info["container_max"] = None
        a = a.astype(np.float32)
    lum = (np.float32(LUMA_W[0]) * a[..., 0]
           + np.float32(LUMA_W[1]) * a[..., 1]
           + np.float32(LUMA_W[2]) * a[..., 2])
    return np.ascontiguousarray(lum.reshape(-1)), info


def run_dose(lum, q, rng, arm):
    """Return (p', max|e|) for one dose in one arm."""
    if q <= 0.0:
        return percentile_shipped(lum), 0.0
    if arm == "quant":
        pert = (np.round(lum / np.float32(q)) * np.float32(q)).astype(np.float32)
    elif arm == "dither":
        # matched RMS: uniform on [-q/2, +q/2] has RMS q/sqrt(12), the same as
        # round-to-nearest quantisation error. This is the model the
        # orchestrator says is invalid; measuring HOW invalid is the point.
        pert = lum + rng.uniform(-q / 2.0, q / 2.0, size=lum.size).astype(np.float32)
    else:
        raise ValueError(arm)
    e = float(np.max(np.abs(pert - lum)))
    return percentile_shipped(pert), e


def main():
    rng = np.random.default_rng(20260824)
    report = {"subjects": [], "target": TARGET, "percentile": PERCENTILE,
              "report_quantum_stops": QUANTUM,
              "q_arw_14bit": Q_ARW, "q_tif_16bit": Q_TIF}

    doses = [
        ("real: 16-bit output", Q_TIF),
        ("real: 14-bit ARW", Q_ARW),
        ("12-bit", 1.0 / 4095.0),
        ("10-bit", 1.0 / 1023.0),
        ("8-bit", 1.0 / 255.0),
        ("6-bit", 1.0 / 63.0),
        ("4-bit", 1.0 / 15.0),
    ]

    for name, kind in SUBJECTS:
        path = os.path.join(OUT, name + ".tif")
        if not os.path.exists(path):
            report["subjects"].append({"name": name, "error": "MISSING " + path})
            continue
        with open(path, "rb") as fh:
            sha = hashlib.sha256(fh.read()).hexdigest().upper()
        lum, info = luminance_of(path)
        p0 = percentile_shipped(lum)
        s0 = stops_for(p0)
        k = nearest_rank_index(lum.size, PERCENTILE)

        # How many distinct levels sit in the neighbourhood of the rank? This is
        # the quantity M113's "~12 distinct levels" threshold is stated in.
        srt = np.partition(lum, [max(k - 5000, 0), min(k + 5000, lum.size - 1)])
        band = np.sort(srt[max(k - 5000, 0): min(k + 5000, lum.size - 1)])
        levels_near_rank = int(np.unique(band).size)

        subj = {
            "name": name, "kind": kind, "sha256": sha, "tif": info,
            "n_samples": int(lum.size), "rank_index": int(k),
            "p99_9": p0, "stops": s0,
            "distinct_levels_in_10k_window_at_rank": levels_near_rank,
            "controls": {}, "ladder": [],
        }

        # ---- C-NULL -------------------------------------------------------
        p_null, e_null = run_dose(lum, 0.0, rng, "quant")
        subj["controls"]["C_NULL"] = {
            "dstops": stops_for(p_null) - s0,
            "reading": "PASS" if stops_for(p_null) - s0 == 0.0 else "FAIL",
        }

        # ---- C-POS --------------------------------------------------------
        pos = []
        for g in (0.5, 2.0):
            sg = stops_for(percentile_shipped(lum * np.float32(g)))
            want = -np.log2(g)
            got = sg - s0
            pos.append({"planted_gain": g, "expected_dstops": round(want, 4),
                        "measured_dstops": round(got, 4),
                        "reading": "PASS" if abs(got - want) <= QUANTUM + 1e-9 else "FAIL"})
        subj["controls"]["C_POS"] = pos

        # ---- the ladder ---------------------------------------------------
        for label, q in doses:
            row = {"dose": label, "q": q, "q_over_p": q / p0 if p0 else None}
            for arm in ("quant", "dither"):
                p1, emax = run_dose(lum, q, rng, arm)
                s1 = stops_for(p1)
                dp = p1 - p0
                row[arm] = {
                    "p": p1, "dp": dp, "max_abs_e": emax,
                    "dstops": None if s1 is None else round(s1 - s0, 4),
                    "lipschitz_ok": bool(abs(dp) <= emax + 1e-9),
                }
            subj["ladder"].append(row)

        # ---- C-RESPONSIVE -------------------------------------------------
        worst = subj["ladder"][-1]
        subj["controls"]["C_RESPONSIVE"] = {
            "dose": worst["dose"],
            "quant_dstops": worst["quant"]["dstops"],
            "reading": "PASS" if abs(worst["quant"]["dstops"]) > QUANTUM else "FAIL",
        }

        # ---- readings on the pre-registered predictions --------------------
        lip = [(r["dose"], a) for r in subj["ladder"] for a in ("quant", "dither")
               if not r[a]["lipschitz_ok"]]
        real = [r for r in subj["ladder"] if r["dose"].startswith("real:")]
        subj["readings"] = {
            "P_A_lipschitz": "CONFIRMED" if not lip else "FALSIFIED " + repr(lip),
            "P_C_real_dose_unmoved": (
                "CONFIRMED" if all(abs(r[a]["dstops"]) < QUANTUM
                                   for r in real for a in ("quant", "dither"))
                else "FALSIFIED"),
        }
        # P-B: compare |dp| between arms at matched RMS, and count sign changes.
        cmp_rows, signs = [], []
        for r in subj["ladder"]:
            qd, dd = abs(r["quant"]["dp"]), abs(r["dither"]["dp"])
            cmp_rows.append({"dose": r["dose"], "abs_dp_quant": qd,
                             "abs_dp_dither": dd,
                             "ratio_quant_over_dither": (qd / dd) if dd else None})
            signs.append(np.sign(r["quant"]["dp"]))
        larger = sum(1 for c in cmp_rows
                     if c["ratio_quant_over_dither"] is not None
                     and c["ratio_quant_over_dither"] > 1.0)
        sign_changes = sum(1 for i in range(1, len(signs))
                           if signs[i] != signs[i - 1] and signs[i] != 0)
        subj["readings"]["P_B_quant_larger_than_dither"] = {
            "rows_where_quant_larger": larger, "rows": len(cmp_rows),
            "quant_sign_changes_across_ladder": int(sign_changes),
            "reading": "CONFIRMED" if larger > len(cmp_rows) / 2 else "FALSIFIED",
        }
        subj["arm_comparison"] = cmp_rows
        report["subjects"].append(subj)

    for dst in (os.path.join(OUT, "11-quantisation-exposure.json"),
                os.path.join(DATA, "11-quantisation-exposure.json")):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    for s in report["subjects"]:
        if "error" in s:
            print("%-16s %s" % (s["name"], s["error"]))
            continue
        print("=" * 78)
        print("%s  --  %s" % (s["name"], s["kind"]))
        print("  n=%d  rank=%d  p99.9=%.8f  stops=%+.2f  distinct levels near rank=%d"
              % (s["n_samples"], s["rank_index"], s["p99_9"], s["stops"],
                 s["distinct_levels_in_10k_window_at_rank"]))
        print("  C_NULL       %s" % s["controls"]["C_NULL"]["reading"])
        for c in s["controls"]["C_POS"]:
            print("  C_POS g=%-4s expected %+.4f  measured %+.4f  %s"
                  % (c["planted_gain"], c["expected_dstops"],
                     c["measured_dstops"], c["reading"]))
        print("  C_RESPONSIVE %s (%s -> %+.4f stops)"
              % (s["controls"]["C_RESPONSIVE"]["reading"],
                 s["controls"]["C_RESPONSIVE"]["dose"],
                 s["controls"]["C_RESPONSIVE"]["quant_dstops"]))
        print("")
        print("  %-20s %10s | %12s %10s | %12s %10s"
              % ("dose", "q", "dp quant", "dstops", "dp dither", "dstops"))
        for r in s["ladder"]:
            print("  %-20s %10.3e | %+12.3e %+10.4f | %+12.3e %+10.4f"
                  % (r["dose"], r["q"], r["quant"]["dp"], r["quant"]["dstops"],
                     r["dither"]["dp"], r["dither"]["dstops"]))
        print("")
        print("  " + json.dumps(s["readings"], indent=2).replace("\n", "\n  "))
    print("")
    print("wrote 11-quantisation-exposure.json")


if __name__ == "__main__":
    main()
