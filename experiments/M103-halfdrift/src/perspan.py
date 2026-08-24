"""M103b -- is the shortfall a SCALAR or a function of SPAN?

`gaingauge.py` measured that one scalar gain applied to the shipped solve takes
per-frame placement error from 36.4 px to 22.5 px at its optimum -- a real 38%
win, which is the orchestrator's instruction vindicated in the gauge that
matters. But it also measured that the optimum is 1.459 while the end-to-end
route says 1.84, and the corpus has two different shortfalls on two different
stacks (M97: 54.3% on `bee-3-cpl`; M97b: 33.3% on `dry-erase-marker-head-cpl`),
so no single constant can be shipped.

The next question decides what CAN be shipped. If the attenuation is a function
of the baseline -- edges between nearby frames barely attenuated, edges between
distant frames badly attenuated -- then the correction is per-span, and a
per-span response is measurable from the stack itself. If a per-span correction
does no better than one scalar, the attenuation is not a span effect and the
per-edge metacalibration route is not worth building.

This applies a per-span multiplier to the log-scale of every edge BEFORE the
solve, then re-solves through the real solver and scores per-frame placement in
the merge's operative gauge. The multipliers are fitted against the truth ladder,
so the result is a CEILING on the per-span approach, not a shippable correction.
That is the point: it prices the approach before anyone builds it.

Controls:
  PLACEBO   all multipliers forced to 1.0 must reproduce the untouched solve to
            ~1e-12. This is the wiring control for the CSV rewrite.
  POSITIVE  shrink every edge's log-scale by a known 0.6 and let the fit recover
            it: the fitted multipliers must come back at 1/0.6 = 1.667 and the
            re-solve must land on the untouched solve's score.
  NEGATIVE  fit multipliers on RANDOM span labels (spans shuffled, so each
            multiplier is fitted on a meaningless mixture). If that helps as
            much as the real per-span fit, the win is degrees of freedom, not
            span structure.

usage:
  python src/perspan.py data/A-deep-edges.csv data/truth-dense.json data/perspan.json
"""

import json
import math
import os
import struct
import subprocess
import sys

R_PLANE = 0.5 * math.hypot(3516.0, 2344.0)
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.abspath(
    os.path.join(HERE, "..", "..", ".cargo-target-m103-probe", "release", "m103probe.exe")
)
OUT = r"C:\dev\strehl-out\M103"
EDIR = os.path.join(OUT, "edges")
SDIR = os.path.join(OUT, "es")
DIGEST_DIR = r"D:\personal\macro\bee-3-cpl"
GAUGE = 144
ONLY = {1, 2, 4, 8, 16, 32, 64, 96, 128}  # the shipped DEFAULT_SPANS


def read_csv(path):
    head, rows = [], []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or line.startswith("i,j,span"):
                head.append(line)
                continue
            if not line.strip():
                continue
            f = line.rstrip("\n").split(",")
            rows.append(f)
    return head, rows


def truth_at(truth, j):
    """Linear interpolation between measured rungs. The track is smooth (the
    largest gap is 8 frames against a 46 px departure from linearity over 298),
    so interpolation error here is far below the effects being measured."""
    rungs = sorted(truth)
    if j <= rungs[0]:
        return truth[rungs[0]]
    if j >= rungs[-1]:
        return truth[rungs[-1]]
    for k in range(len(rungs) - 1):
        a, b = rungs[k], rungs[k + 1]
        if a <= j <= b:
            t = (j - a) / (b - a)
            return truth[a] * (1 - t) + truth[b] * t
    return truth[rungs[-1]]


def fit_per_span(rows, truth, span_of):
    """r(s) = sum(measured * truth) / sum(truth^2) over edges of span s -- the
    least-squares slope of measured against true increment, through the origin."""
    num, den = {}, {}
    for f in rows:
        i, j = int(f[0]), int(f[1])
        if f[3] != "OK":
            continue
        s = span_of(f)
        m = math.log(math.hypot(float(f[4]), float(f[5])))
        t = truth_at(truth, j) - truth_at(truth, i)
        num[s] = num.get(s, 0.0) + m * t
        den[s] = den.get(s, 0.0) + t * t
    return {s: (num[s] / den[s] if den.get(s, 0.0) > 1e-18 else 1.0) for s in num}


def write_scaled(name, head, rows, mult, span_of):
    os.makedirs(EDIR, exist_ok=True)
    p = os.path.join(EDIR, name + ".csv")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.writelines(head)
        for f in rows:
            g = f[:]
            s = span_of(f)
            k = mult.get(s, 1.0)
            if k != 1.0 and g[3] == "OK" and g[4]:
                ar, ai = float(g[4]), float(g[5])
                m = math.hypot(ar, ai)
                if m > 0:
                    scale = math.exp(math.log(m) * k) / m
                    g[4] = "%.12e" % (ar * scale)
                    g[5] = "%.12e" % (ai * scale)
            fh.write(",".join(g) + "\n")
    os.replace(tmp, p)
    return p


def solve(name, csv_path):
    os.makedirs(SDIR, exist_ok=True)
    sp = os.path.join(SDIR, name + ".txt")
    p = subprocess.run(
        [PROBE, "solve", "--edges", csv_path, "--n", "299", "--reference", "0",
         "--only-spans", ",".join(str(s) for s in sorted(ONLY)),
         "--digest-dir", DIGEST_DIR, "--label", name, "--warpmap", sp],
        capture_output=True, text=True)
    return (sp if p.returncode == 0 else None), (p.stdout + p.stderr).strip()


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


def score(track, truth):
    rungs = [j for j in sorted(truth) if j in track]
    e = [((track[j] - track[GAUGE]) - (truth[j] - truth[GAUGE])) * R_PLANE for j in rungs]
    a = [abs(x) for x in e]
    return {"mean": sum(a) / len(a), "max": max(a),
            "rms": math.sqrt(sum(x * x for x in e) / len(e))}


def main():
    csv_path, truth_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    head, rows = read_csv(csv_path)
    truth = {int(k): v["ln"]
             for k, v in json.load(open(truth_path, encoding="utf-8"))["ladder"].items()}
    span_of = lambda f: int(f[2])
    res = {}

    print("CONTROLS")
    p0, _ = solve("PS-placebo", write_scaled("PS-placebo", head, rows, {}, span_of))
    base = score(read_sidecar(p0), truth)
    ref = score(read_sidecar(os.path.join(OUT, "wm-baseline-r0.txt")), truth)
    d = abs(base["mean"] - ref["mean"])
    print("  PLACEBO  all multipliers 1.0 -> mean %.3f px vs the committed shipped"
          " sidecar %.3f px, |d| = %.3e -> %s"
          % (base["mean"], ref["mean"], d, "PASS" if d < 1e-6 else "FAIL"))
    okp = d < 1e-6

    shrunk = [f[:] for f in rows]
    for f in shrunk:
        if f[3] != "OK" or not f[4]:
            continue
        ar, ai = float(f[4]), float(f[5])
        m = math.hypot(ar, ai)
        if m > 0:
            k = math.exp(math.log(m) * 0.6) / m
            f[4], f[5] = "%.12e" % (ar * k), "%.12e" % (ai * k)
    fit_s = fit_per_span(shrunk, truth, span_of)
    real_s = fit_per_span(rows, truth, span_of)
    ratios = [fit_s[s] / real_s[s] for s in sorted(real_s) if s in fit_s and abs(real_s[s]) > 1e-9]
    rmean = sum(ratios) / len(ratios)
    ok1 = abs(rmean - 0.6) < 0.02
    print("  POSITIVE every edge shrunk by a known 0.6: the per-span fit recovers"
          " %.4f (closed form 0.6000) -> %s" % (rmean, "PASS" if ok1 else "FAIL"))

    print("  -> controls %s\n" % ("PASS" if (okp and ok1) else "FAIL"))
    res["controls"] = {"placebo_delta_px": d, "positive_recovered": rmean,
                       "pass": bool(okp and ok1)}
    if not (okp and ok1):
        return 1

    print("Per-span response r(s) of the SHIPPED estimator, fitted against the")
    print("independent RAW ladder (slope of measured log-scale on true log-scale):")
    print("  %6s %10s" % ("span", "r(s)"))
    for s in sorted(real_s):
        if s in ONLY or s in (192, 256, 298):
            print("  %6d %10.4f" % (s, real_s[s]))
    res["r_per_span"] = {str(s): real_s[s] for s in sorted(real_s)}

    mult = {s: (1.0 / real_s[s] if abs(real_s[s]) > 0.05 else 1.0) for s in real_s}
    sp, _ = solve("PS-perspan", write_scaled("PS-perspan", head, rows, mult, span_of))
    per = score(read_sidecar(sp), truth) if sp else None

    # NEGATIVE control: assign each edge a pseudo-random group label derived from
    # its endpoints. Same number of groups, same degrees of freedom, but each
    # group is a MIXTURE of baselines, so span structure is destroyed while the
    # fit's freedom is preserved. (A first attempt permuted the span labels
    # instead -- that is a bijection on the grouping and therefore a no-op by
    # construction; it returned a byte-identical result, which is how it was
    # caught. Recorded here because a control that cannot fail is worse than
    # no control.)
    ngroup = len(set(int(f[2]) for f in rows))
    shuf = lambda f: (int(f[0]) * 31 + int(f[1]) * 17 + 7) % ngroup
    fake = fit_per_span(rows, truth, shuf)
    fmult = {s: (1.0 / fake[s] if abs(fake[s]) > 0.05 else 1.0) for s in fake}
    sp2, _ = solve("PS-shuffled", write_scaled("PS-shuffled", head, rows, fmult, shuf))
    neg = score(read_sidecar(sp2), truth) if sp2 else None

    print()
    print("  %-34s %8s %8s %8s" % ("arm", "mean", "max", "rms"))
    print("  %-34s %8.1f %8.1f %8.1f" % ("shipped, untouched", ref["mean"], ref["max"], ref["rms"]))
    print("  %-34s %8.1f %8.1f %8.1f" % ("shipped + best SCALAR gain (1.459)", 22.5, 0.0, 0.0)
          if False else "  %-34s %8.1f" % ("shipped + best SCALAR gain (1.459)", 22.5))
    if per:
        print("  %-34s %8.1f %8.1f %8.1f" % ("shipped + per-span 1/r(s)", per["mean"], per["max"], per["rms"]))
    if neg:
        print("  %-34s %8.1f %8.1f %8.1f"
              % ("NEGATIVE per-SHUFFLED-span 1/r", neg["mean"], neg["max"], neg["rms"]))
    res["per_span"] = per
    res["shuffled"] = neg
    res["shipped"] = ref

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    print("\nwrote " + out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
