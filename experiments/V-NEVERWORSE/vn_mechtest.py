"""Does the shipping merge's admission decision predict the measured excess?

ORCH's mechanism, re-aimed onto the code that actually ran (see vn_admit.py):
a spatially varying mixture of "averaged" and "selected" coefficients makes the
residual noise amplitude spatially varying, and at the coarse pyramid levels
that lands inside the 50-400 px band `orch_blotch` measures.

The shipping binary reports, per level, the fraction p of coefficients where no
frame cleared the noise floor and the merge averaged. A level with p = 0 or
p = 1 is spatially uniform in that decision; the mixture is maximal at p = 0.5.
So the hypothesis predicts excess should rise with the mixedness 4p(1-p).

WHAT THIS PROXY CAN AND CANNOT SEE, stated before the number. The averaged flag
is binary: it fires only where NO frame cleared the floor. Where frames did
clear it, the SoftPower weights (band power above floor)^exp still vary from
coefficient to coefficient, and n_eff varies with them. So mixedness sees only
the coarsest possible summary of the admission field and CANNOT see variation
among admitted frames. A positive result would support the mechanism; a null
result does NOT refute it, and is reported as inconclusive rather than as a
refutation. Killing the hypothesis needs the per-pixel n_eff map.

COMMISSIONING perturbs in both directions, as required:
  - excess REPLACED by a rising function of mixedness  -> rho must go strongly +
  - excess REPLACED by a falling function of mixedness -> rho must go strongly -
  - subject labels shuffled (placebo)                  -> rho ~ 0
  - mixedness shuffled (denominator)                   -> rho ~ 0
A statistic that can only ever rise under disturbance cannot tell a real
association from any association at all.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_lib as L  # noqa: E402

NULL = r"C:\dev\strehl-out\V-NEVERWORSE\report\null.json"
ADMIT = r"C:\dev\strehl-out\V-NEVERWORSE\mech\admission.json"
OUT = r"C:\dev\strehl-out\V-NEVERWORSE\mech"


def spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / d) if d > 0 else 0.0


def permp(a, b, n=20000, seed=3):
    r = spearman(a, b)
    rng = np.random.default_rng(seed)
    a = np.asarray(a, float).copy()
    c = 0
    for _ in range(n):
        rng.shuffle(a)
        if abs(spearman(a, b)) >= abs(r):
            c += 1
    return r, (c + 1) / (n + 1)


def mixedness(p):
    return 4.0 * p * (1.0 - p)


def load():
    adm = json.load(open(ADMIT))
    nul = json.load(open(NULL))
    rows, refused = {}, {}
    for s, a in adm.items():
        if s not in nul or "blotch" not in nul[s]:
            refused[s] = "no entry in null.json"
            continue
        b = nul[s]["blotch"]
        if b.get("excess") is None or not np.isfinite(b["excess"]):
            refused[s] = "blotch excess not finite"
            continue
        rows[s] = dict(mix=mixedness(a["avg"][0]), p0=a["avg"][0],
                       p1=a["avg"][1] if len(a["avg"]) > 1 else 0.0,
                       excess=b["excess"], vs_min=b["vs_min"],
                       loo=b["loo_med"], n=b.get("n"),
                       frames=a["frames"])
    return rows, refused


RATIO_DIR = r"C:\dev\strehl-out\V-NEVERWORSE\ratio"


def _master(subj, key="noise"):
    """The master's own measured noise, from the per-subject ratio record."""
    p = os.path.join(RATIO_DIR, subj + ".json")
    if not os.path.exists(p):
        return None
    try:
        return float(json.load(open(p))["master"][key])
    except (KeyError, TypeError, ValueError):
        return None


def rho_of(rows, ex=None, mix=None):
    s = sorted(rows)
    e = ex if ex is not None else [rows[k]["excess"] for k in s]
    m = mix if mix is not None else [rows[k]["mix"] for k in s]
    return spearman(e, m)


def commission(rows):
    # A population guard, because the first run of this harness certified three
    # arms on ZERO subjects: the loader read the wrong key, every list came back
    # empty, and "labels shuffled gives rho ~ 0" is trivially true of nothing at
    # all. A check that cannot fail prints the same glyph as one that passed.
    if len(rows) < 20:
        print("")
        print("REFUSED to commission: %d subjects loaded, need >= 20." % len(rows))
        print("  An empty or thin population makes the placebo arms pass")
        print("  vacuously. This guard exists because that happened.")
        return 1
    s = sorted(rows)
    mix = np.array([rows[k]["mix"] for k in s])
    rng = np.random.default_rng(17)
    base = rho_of(rows)
    arms = []
    up = 1.0 + 0.8 * mix + rng.normal(0, 0.02, len(mix))
    arms.append(("excess REPLACED by a rising fn of mixedness",
                 rho_of(rows, ex=up), "> +0.8", rho_of(rows, ex=up) > 0.8))
    dn = 1.0 - 0.8 * mix + rng.normal(0, 0.02, len(mix))
    arms.append(("excess REPLACED by a falling fn of mixedness",
                 rho_of(rows, ex=dn), "< -0.8", rho_of(rows, ex=dn) < -0.8))
    pl = []
    for _ in range(200):
        e = np.array([rows[k]["excess"] for k in s])
        rng.shuffle(e)
        pl.append(rho_of(rows, ex=e))
    v = float(np.mean(np.abs(pl)))
    arms.append(("subject labels shuffled (placebo)", v, "|mean| < 0.2", v < 0.2))
    md = mix.copy()
    rng.shuffle(md)
    arms.append(("mixedness shuffled (denominator)", rho_of(rows, mix=md),
                 "|v| < 0.5", abs(rho_of(rows, mix=md)) < 0.5))
    sd = float(np.std(pl))
    arms.append(("placebo spread is resolvable (sd %.3f)" % sd, sd,
                 "sd < 0.30", sd < 0.30))

    print("")
    print("COMMISSIONING  vn_mechtest  (%d subjects, undisturbed rho %+.3f)"
          % (len(s), base))
    print("")
    print("  %-46s %8s  %-12s %s" % ("arm", "rho", "required", ""))
    ok, bad = 0, []
    for name, val, req, p in arms:
        ok += bool(p)
        if not p:
            bad.append((name, req))
        print("  %-46s %+8.3f  %-12s %s" % (name, val, req, "ok" if p else "FAILED"))
    print("")
    print("  %d ok + %d failed = %d arms" % (ok, len(bad), len(arms)))
    for name, req in bad:
        print("  NOT COMMISSIONED: %s (required %s)" % (name, req))
    return 0 if not bad else 1


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", action="store_true")
    a = ap.parse_args(argv)
    rows, refused = load()
    if a.commission:
        return commission(rows)

    s = sorted(rows)
    mix = [rows[k]["mix"] for k in s]
    ex = [rows[k]["excess"] for k in s]
    r, p = permp(ex, mix)
    r0, p0 = permp(ex, [rows[k]["p0"] for k in s])
    print("")
    print("ADMISSION vs MEASURED EXCESS  (%d subjects)" % len(s))
    print("")
    print("  %-38s %8s %8s %8s %7s" %
          ("subject", "avg L0", "mix L0", "excess", "frames"))
    for k in sorted(s, key=lambda z: -rows[z]["excess"]):
        d = rows[k]
        print("  %-38s %7.1f%% %8.3f %8.3f %7d"
              % (k, 100 * d["p0"], d["mix"], d["excess"], d["frames"]))
    print("")
    print("  Spearman, excess vs mixedness 4p(1-p)   rho %+.3f   perm p %.4f"
          % (r, p))
    print("  Spearman, excess vs raw averaged frac   rho %+.3f   perm p %.4f"
          % (r0, p0))
    # Necessary conditions for ANY unaveraged-noise mechanism, tested on
    # quantities already in the records. Residual noise falls as 1/sqrt(n), so
    # deep stacks should be cleaner; and a noise-amplitude mottle should scale
    # with the master's own measured noise. Neither has to hold for ORCH's
    # hypothesis specifically, but if BOTH are null the mottle is not behaving
    # like unaveraged noise at all.
    extra = []
    nf = [rows[k]["frames"] for k in s]
    extra.append(("frame count (noise falls as 1/sqrt n)", permp(ex, nf)))
    nz, ex2 = [], []
    for k in s:
        q = _master(k)
        if q is not None:
            nz.append(q)
            ex2.append(rows[k]["excess"])
    if len(nz) >= 20:
        extra.append(("master's own measured noise", permp(ex2, nz)))
    else:
        extra.append(("master's own measured noise", (float("nan"),
                                                      float("nan"))))
    print("")
    print("  necessary conditions for an unaveraged-noise mechanism:")
    for name, (rr, pp) in extra:
        print("    excess vs %-38s rho %+.3f   perm p %.4f" % (name, rr, pp))
    print("")
    print("  measured %d + refused %d = %d subjects examined"
          % (len(rows), len(refused), len(rows) + len(refused)))
    for k, why in sorted(refused.items()):
        print("    refused %-28s %s" % (k, why))
    os.makedirs(OUT, exist_ok=True)
    L.jdump(dict(rho_mix=r, p_mix=p, rho_raw=r0, p_raw=p0,
                 rows={k: rows[k] for k in rows},
                 refused=refused), os.path.join(OUT, "mechtest.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
