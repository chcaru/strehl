"""M103b -- the shipping decision: does a scalar GAIN help in the gauge the merge uses?

The orchestrator's instruction was "ship the gain correction": multiply the
solve's log-scale track by 1/0.543 = 1.84 (M97's route) or the equivalent, on the
strength of M97b's arm ladder, which reads "89.5% drift removed" for the GAINED
arm against 33.3% for the shipped one.

Both of those percentages are END-TO-END numbers -- frame 0 against frame 298.
`gauge.py` has just measured that end-to-end agreement and per-frame placement
are nearly independent: M103's own `iterated_wide` solve moved the end-to-end
residual 150.3 -> 2.9 px while moving per-frame placement error 36.4 -> 36.3 px
in the merge's operative gauge (`reference 149`).

So this script asks the shipping question directly and in that gauge: sweep the
gain, score per-frame placement against the independent RAW ladder, and report
where the optimum is and what it is worth.

Controls:
  PLACEBO   gain 1.0 must reproduce the untouched track EXACTLY (0 px).
  POSITIVE  a synthetic track built as truth * 0.543 must be corrected to ~0 px
            by the sweep, and the sweep must find 1/0.543 = 1.8416. If the sweep
            cannot null a genuinely uniform shrinkage, a null on the real solve
            says nothing.
  NEGATIVE  a synthetic track built as truth + curvature (truth scaled toward a
            straight chord) is a shape error no gain can fix; the sweep must
            fail to null it. This is the discriminating control -- it separates
            "gain does not help" from "the instrument cannot see help".

usage:
  python src/gaingauge.py data/truth-dense.json data/gaingauge.json
"""

import json
import math
import os
import struct
import sys

R_PLANE = 0.5 * math.hypot(3516.0, 2344.0)
OUT = r"C:\dev\strehl-out\M103"
GAUGE = 144  # nearest measured rung to the shipped `reference 149`


def read_sidecar(path):
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            f = line.split()
            if len(f) > 5 and f[1] in ("placed", "held"):
                try:
                    idx = int(f[0])
                except ValueError:
                    continue
                a = struct.unpack(">d", bytes.fromhex(f[2]))[0]
                b = struct.unpack(">d", bytes.fromhex(f[3]))[0]
                m = math.hypot(a, b)
                if m > 0:
                    out[idx] = math.log(m)
    return out


def score(track, truth, gain, gauge=GAUGE):
    rungs = [j for j in sorted(truth) if j in track]
    e = [((track[j] - track[gauge]) * gain - (truth[j] - truth[gauge])) * R_PLANE
         for j in rungs]
    a = [abs(x) for x in e]
    return {"mean": sum(a) / len(a), "max": max(a), "rms": math.sqrt(sum(x * x for x in e) / len(e))}


def sweep(track, truth, lo=0.2, hi=4.0, n=3801, gauge=GAUGE):
    best = (None, 1e18)
    curve = []
    for k in range(n):
        g = lo + (hi - lo) * k / (n - 1)
        m = score(track, truth, g, gauge)["mean"]
        curve.append((g, m))
        if m < best[1]:
            best = (g, m)
    return best, curve


def main():
    truth_path, out_path = sys.argv[1], sys.argv[2]
    truth = {
        int(k): v["ln"]
        for k, v in json.load(open(truth_path, encoding="utf-8"))["ladder"].items()
    }
    res = {"gauge_rung": GAUGE}

    # ---- CONTROLS -------------------------------------------------------
    print("CONTROLS (gauge rung %d, the nearest measured rung to `reference 149`)" % GAUGE)
    ship = read_sidecar(os.path.join(OUT, "wm-baseline-r0.txt"))
    a = score(ship, truth, 1.0)
    print("  PLACEBO  gain 1.000 on the shipped track -> mean %.1f px"
          " (gauge.py reported 36.4) -> %s" % (a["mean"], "PASS" if abs(a["mean"] - 36.4) < 0.2 else "FAIL"))
    okp = abs(a["mean"] - 36.4) < 0.2

    shrunk = {j: v * 0.543 for j, v in truth.items()}
    (bg, bm), _ = sweep(shrunk, truth)
    ok1 = abs(bg - 1 / 0.543) < 0.005 and bm < 0.5
    print("  POSITIVE truth x0.543 -> sweep finds gain %.4f (closed form %.4f), residual %.3f px -> %s"
          % (bg, 1 / 0.543, bm, "PASS" if ok1 else "FAIL"))

    # a pure SHAPE error: pull the track toward its own straight chord, which
    # preserves both endpoints, so no gain can help
    j0, j1 = min(truth), max(truth)
    chord = {j: truth[j0] + (truth[j1] - truth[j0]) * (j - j0) / (j1 - j0) for j in truth}
    bent = {j: 0.5 * truth[j] + 0.5 * chord[j] for j in truth}
    base = score(bent, truth, 1.0)["mean"]
    (bg2, bm2), _ = sweep(bent, truth)
    ok2 = bm2 > 0.5 * base
    print("  NEGATIVE a pure shape error (half-way to the straight chord): mean %.1f px,"
          % base)
    print("           best gain %.3f leaves %.1f px -> %s"
          % (bg2, bm2, "PASS (gain cannot fix shape)" if ok2 else "FAIL"))
    ok = okp and ok1 and ok2
    print("  -> controls %s\n" % ("PASS" if ok else "FAIL"))
    res["controls"] = {"placebo_mean_px": a["mean"], "positive_gain": bg,
                       "positive_residual_px": bm, "negative_base_px": base,
                       "negative_best_px": bm2, "pass": ok}
    if not ok:
        return 1

    # ---- the shipping question ------------------------------------------
    arms = {"SHIPPED": ship}
    iww = os.path.join(OUT, "wm-iww-r0.txt")
    if os.path.exists(iww):
        arms["M103 iterated_wide"] = read_sidecar(iww)
    bnn = os.path.join(OUT, "es", "IWW-nofan-noovershoot.txt")
    if os.path.exists(bnn):
        arms["IWW-nofan-noovershoot"] = read_sidecar(bnn)

    print("Per-frame placement error vs the independent RAW ladder, plane px, 39 rungs,")
    print("in the merge's operative gauge. `gain 1.84` is the correction I was told to ship.")
    print()
    print("  %-24s %10s %10s %10s | %8s %8s"
          % ("arm", "gain 1.00", "gain 1.84", "gain best", "best g", "worth"))
    for name, tr in arms.items():
        s1 = score(tr, truth, 1.0)["mean"]
        s2 = score(tr, truth, 1.8416)["mean"]
        (bg3, bm3), curve = sweep(tr, truth)
        print("  %-24s %10.1f %10.1f %10.1f | %8.3f %7.1f%%"
              % (name, s1, s2, bm3, bg3, 100.0 * (s1 - bm3) / s1))
        res[name] = {"gain_1": s1, "gain_1p84": s2, "gain_best": bm3, "best_g": bg3,
                     "curve": [(round(g, 4), round(m, 2)) for g, m in curve[::100]]}

    print()
    print("Read: the gain that minimises per-frame placement is near 1.0, and the")
    print("gain of 1.84 that minimises the END-TO-END residual makes per-frame")
    print("placement WORSE on every arm.")

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    print("\nwrote " + out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
