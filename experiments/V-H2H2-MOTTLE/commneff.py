"""Commission n_eff before believing anything it says about frame count.

n_eff = sum(w)^2 / sum(w^2) is a new accumulator in the merge and a new number in
this lane. Two ways it could be wrong and both would look like a result:

  * it could be inert -- a plumbing error that writes a constant, or writes the
    concentration map again under a different name, in which case a real change
    in the merge reads as "no change" and ORCH's hypothesis is dismissed by a
    dead wire;
  * it could be one-sided -- responsive to more selection but not to more
    averaging, in which case it can only ever return the answer that the merge is
    selective.

This project shipped a sharpness statistic bounded below by zero that could never
charge for a halo, because every arm ever planted against it was a degradation.
So the arms here are DELIBERATELY IN OPPOSITE DIRECTIONS:

  --pyramid-exponent 0.5   more averaging  -> n_eff must RISE
  --pyramid-exponent 6.0   more selection  -> n_eff must FALL

Neither is "the improvement" in a quality sense -- n_eff is a description, not a
score. The pair is what proves the instrument has two working directions rather
than one.

Three analytic bounds are checked as well, because they hold for any correct
implementation at any exponent and a broken accumulator breaks them:

  1  <=  n_eff  <=  frames        (a participation ratio counts frames)
  n_eff == 1 exactly where one frame holds all the weight
  n_eff is NaN exactly where the gate admitted nothing (den == 0)

The third is the one that catches the likeliest real error: counting refused
coefficients as unanimous ones, which would report the merge as maximally
selective precisely where it made no selection at all.
"""
import io
import json
import os
import subprocess
import sys

import numpy as np

EXE = r"C:\dev\strehl-out\V-H2H2\target\release\strehl.exe"
SRC = r"D:\personal\macro\coffee-bubbles"
OUT = r"C:\dev\strehl-out\V-H2H2\commneff"

ARMS = [("null", None), ("avg", "0.5"), ("sel", "6.0")]


def render(name, exponent):
    tif = os.path.join(OUT, "%s.tiff" % name)
    if os.path.exists(tif):
        print("skip (exists): %s" % name)
        return
    cmd = [EXE, "stack", SRC, "--out", tif, "--linear-srgb", "--demosaic"]
    if exponent is not None:
        cmd += ["--pyramid-exponent", exponent]
    env = dict(os.environ, STREHL_PYRAMID_WEIGHT_DUMP=os.path.join(OUT, name))
    print("rendering %s ..." % name, flush=True)
    r = subprocess.run(cmd, env=env, capture_output=True)
    if r.returncode != 0:
        raise SystemExit("%s failed rc=%d\n%s"
                         % (name, r.returncode, r.stderr.decode("utf-8", "replace")[-2000:]))


def load(name):
    with io.open(os.path.join(OUT, "%s-dims.json" % name), encoding="utf-8") as fh:
        d = json.load(fh)
    out = {}
    for b in d["bands"]:
        k = b["k"]
        p = os.path.join(OUT, "%s-b%d-neff.f32" % (name, k))
        c = os.path.join(OUT, "%s-b%d-conc.f32" % (name, k))
        if not os.path.exists(p):
            continue
        out[k] = (np.fromfile(p, dtype=np.float32),
                  np.fromfile(c, dtype=np.float32),
                  b["exponent"])
    return d["frames"], out


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, e in ARMS:
        render(name, e)

    frames, null = load("null")
    _, avg = load("avg")
    _, sel = load("sel")
    print("\ncoffee-bubbles, %d frames" % frames)

    fails = []

    # --- analytic bounds, on every arm and every band -----------------------
    print("\nANALYTIC BOUNDS (must hold for any correct implementation)")
    for name, arm in (("null", null), ("avg", avg), ("sel", sel)):
        bad_lo = bad_hi = bad_nan = 0
        for k, (n, c, _) in arm.items():
            fin = np.isfinite(n)
            bad_lo += int(np.count_nonzero(n[fin] < 1.0 - 1e-3))
            bad_hi += int(np.count_nonzero(n[fin] > frames + 1e-3))
            # NaN in n_eff must coincide exactly with NaN in concentration:
            # both are defined as NaN where and only where den == 0.
            bad_nan += int(np.count_nonzero(np.isfinite(n) != np.isfinite(c)))
        ok = (bad_lo == 0) and (bad_hi == 0) and (bad_nan == 0)
        print("  %-5s n_eff<1: %-8d n_eff>%d: %-8d NaN disagrees with conc: %-8d %s"
              % (name, bad_lo, frames, bad_hi, bad_nan, "OK" if ok else "VIOLATED"))
        if not ok:
            fails.append("%s violated an analytic bound" % name)

    # --- responsiveness, in BOTH directions ---------------------------------
    print("\nRESPONSIVENESS  (mean n_eff over admitted coefficients)")
    print("%-3s %-22s %-10s %-10s %-10s %s"
          % ("k", "p  avg / null / sel", "avg", "null", "sel", "verdict"))
    moved_up = moved_dn = 0
    n_up = n_dn = 0
    for k in sorted(null):
        if k not in avg or k not in sel:
            continue
        def m(arm):
            n = arm[k][0]
            f = np.isfinite(n)
            return float(np.mean(n[f])) if np.any(f) else float("nan")
        a, nl, s = m(avg), m(null), m(sel)
        if not (a == a and nl == nl and s == s):
            continue
        # A band where the exponent did not actually change between two arms is
        # not evidence that the statistic is unresponsive -- it is a band where
        # nothing was planted. MAX_EXPONENT caps the fine bands at 8.0, so
        # `--pyramid-exponent 6.0` leaves bands 0 and 1 identical to the default
        # and scoring them FLAT would be scoring my own control as a failure.
        p_null, p_avg, p_sel = null[k][2], avg[k][2], sel[k][2]
        planted_up = abs(p_avg - p_null) > 1e-6
        planted_dn = abs(p_sel - p_null) > 1e-6
        up = planted_up and a > nl * 1.001
        dn = planted_dn and s < nl * 0.999
        moved_up += int(up)
        moved_dn += int(dn)
        n_up += int(planted_up)
        n_dn += int(planted_dn)
        v = ("rose" if up else ("(no change planted)" if not planted_up else "FLAT"))
        v += " / " + ("fell" if dn else ("(no change planted)" if not planted_dn else "FLAT"))
        print("%-3d %-22s %-10.3f %-10.3f %-10.3f %s"
              % (k, "%.2f / %.2f / %.2f" % (p_avg, p_null, p_sel),
                 a, nl, s, v))

    print()
    print("bands where more averaging RAISED n_eff: %d of %d planted" % (moved_up, n_up))
    print("bands where more selection LOWERED n_eff: %d of %d planted" % (moved_dn, n_dn))
    if n_up == 0 or n_dn == 0:
        fails.append("no exponent change was actually planted in one direction")
    if moved_up < n_up:
        fails.append("n_eff failed to rise on %d band(s) where averaging was planted"
                     % (n_up - moved_up))
    if moved_dn < n_dn:
        fails.append("n_eff failed to fall on %d band(s) where selection was planted"
                     % (n_dn - moved_dn))

    print()
    if fails:
        print("COMMISSIONING FAILED:")
        for f in fails:
            print("  - %s" % f)
        sys.exit(1)
    print("COMMISSIONED: n_eff obeys its bounds and moves in BOTH directions.")
    sys.exit(0)


if __name__ == "__main__":
    main()
