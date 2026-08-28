# Read the per-band weight dump and decide, on measurement, whether the gate
# does work above level 0.
#
# PRE-REGISTERED, written before the dump existed. `n_eff = sum(w)^2/sum(w^2)`
# is the number of frames effectively contributing at a coefficient. Let F be
# the frame count.
#
#   ORCH's claim -- "at levels 1-6 the gate is not gating, this is a naive
#   pyramid stacker" -- predicts n_eff at bands 1-6 close to F. A gate that
#   admits everything leaves a plain-ish weighted mean over all frames.
#
#   The alternative -- "`averaged` is blind; the gate may be selecting hard and
#   simply always leaving at least one survivor" -- predicts n_eff far below F.
#
# DECISION RULE, fixed now: report mean n_eff per band as a FRACTION of F.
#   >= 0.50 F   supports ORCH (little effective selection)
#   <= 0.10 F   refutes ORCH (strong effective selection)
#   between     neither; report as indeterminate and say so.
#
# The rule is stated before the numbers so it cannot be chosen to fit them.

import glob
import os
import re
import sys

import numpy as np

PREFIX = r"C:\dev\strehl-out\V-H2H2\wdump\leaf2"
SUPPORT, REFUTE = 0.50, 0.10


def load(path, dtype):
    a = np.fromfile(path, dtype=dtype)
    return a


def main():
    files = sorted(glob.glob(PREFIX + "-b*-neff.f32"))
    if not files:
        print("no dump files at %s-b*-neff.f32" % PREFIX)
        print("contents of %s:" % os.path.dirname(PREFIX))
        for f in sorted(glob.glob(os.path.dirname(PREFIX) + r"\*"))[:20]:
            print("   ", os.path.basename(f))
        return 2

    frames = None
    m = re.search(r"frames\s*[:=]\s*(\d+)", os.environ.get("STREHL_FRAMES", ""))
    if m:
        frames = int(m.group(1))

    print("per-band weight dump, leaf-2-cpl")
    print("%-6s %10s %9s %9s %9s %9s %9s"
          % ("band", "coeffs", "mean neff", "median", "p90", "max", "no-admit"))
    rows = []
    for f in files:
        k = int(re.search(r"-b(\d+)-neff", f).group(1))
        neff = load(f, np.float32)
        arg = load(f.replace("-neff.f32", "-arg.i32"), np.int32) \
            if os.path.exists(f.replace("-neff.f32", "-arg.i32")) else None
        live = np.isfinite(neff) & (neff > 0)
        noadmit = float((arg < 0).mean()) if arg is not None else float("nan")
        v = neff[live]
        if v.size == 0:
            rows.append((k, neff.size, float("nan"), float("nan"), float("nan"),
                         float("nan"), noadmit))
            continue
        rows.append((k, neff.size, float(v.mean()), float(np.median(v)),
                     float(np.percentile(v, 90)), float(v.max()), noadmit))
        print("%-6d %10d %9.2f %9.2f %9.2f %9.2f %8.1f%%"
              % (k, neff.size, v.mean(), np.median(v), np.percentile(v, 90),
                 v.max(), 100 * noadmit))

    # F is not in the dump; the largest n_eff observed anywhere is a hard lower
    # bound on it, and the CLI banner prints the true count. Use the observed
    # max as the scale only if the true count is unavailable, and SAY WHICH.
    obs_max = max(r[5] for r in rows if r[5] == r[5])
    if frames is None:
        frames = int(round(obs_max))
        scale_note = ("F taken as the largest n_eff observed (%d). This is a "
                      "LOWER bound on the true frame count, so every fraction "
                      "below is an OVER-estimate of participation and the test "
                      "is conservative against ORCH's claim being refuted."
                      % frames)
    else:
        scale_note = "F read from the render banner (%d)." % frames

    print("\n%s" % scale_note)
    print("\n%-6s %12s %12s   %s" % ("band", "mean neff", "as frac of F", "verdict"))
    verdicts = []
    for k, n, mean, med, p90, mx, na in rows:
        if mean != mean:
            print("%-6d %12s %12s   %s" % (k, "nan", "-", "no live coefficients"))
            verdicts.append(None)
            continue
        frac = mean / frames
        v = ("SUPPORTS ORCH" if frac >= SUPPORT
             else "REFUTES ORCH" if frac <= REFUTE else "INDETERMINATE")
        verdicts.append(v)
        print("%-6d %12.2f %12.3f   %s" % (k, mean, frac, v))

    upper = [v for (k, *_), v in zip(rows, verdicts) if k >= 1 and v]
    print("\nBands 1+: %s" % (", ".join("%s" % v for v in upper) or "none"))
    if upper and all(v == "REFUTES ORCH" for v in upper):
        print("\nCONCLUSION: at every band above level 0 the gate leaves far fewer")
        print("than F frames effectively contributing. `averaged = 0.0%` at those")
        print("bands was the signature of a gate that always leaves a survivor,")
        print("not of a gate that admits everything.")
    elif upper and all(v == "SUPPORTS ORCH" for v in upper):
        print("\nCONCLUSION: ORCH is right on measurement. The gate does little")
        print("effective selection above level 0 and the weight law is operating")
        print("close to a naive pyramid stacker there.")
    else:
        print("\nCONCLUSION: mixed or indeterminate; report per band, claim nothing")
        print("about the set as a whole.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
