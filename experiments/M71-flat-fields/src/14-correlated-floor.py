"""
M71 step 14 — does a neighbour-correlated noise floor masquerade as PRNU?

Routed from M72: every plane correlates with its own neighbours at +0.05 to +0.16
in the read-noise domain, `noise.rs:122`'s independence assertion is false, and
the orchestrator's question is whether that contaminates my kappa:

    "your flats are exactly where a neighbour-correlated floor would masquerade
     as low-frequency PRNU structure ... If it is immaterial at your signal
     levels, say so with a number."

THE STRUCTURAL ARGUMENT FIRST (ARGUED), so the reader knows what the plant is
checking rather than discovering:

    kappa^2 = cov(D_A, D_B) / 2,  D = residual(r_G1) - residual(r_G2)

A and B are INDEPENDENT 20-frame captures (the CPL-on and CPL-off halves at
matched shutter). Temporal noise in A is independent of temporal noise in B, so
E[cov(noise_A, noise_B)] = 0 REGARDLESS of how that noise is correlated across
space. Spatial correlation of a temporal noise floor therefore inflates the
VARIANCE of my estimator and cannot bias its EXPECTATION.

That is an argument. This script measures it, because an argument is not a
measurement (M61's own words) and because facts 61-64 record four occasions where
a subtly wrong plant nearly produced a false result.

Four arms, all planted into the real cached mean images before `residual()`:

  A0 baseline           -- the real data, reproducing the committed headline
  A1 correlated floor   -- independent per-capture noise at the REAL per-mean
                           amplitude, with nearest-neighbour correlation set to
                           the measured DARK value +0.055 (a stress test: the
                           flats' own measured value is ~10-30x smaller)
  A2 stress x3          -- same, at r = +0.16, the TOP of M72's quoted range,
                           and at 3x the real noise amplitude
  A3 positive control   -- a FIXED multiplicative pattern of known amplitude
                           planted identically into A and B; kappa must rise to
                           sqrt(kappa0^2 + planted^2). If A3 fails, the estimator
                           is not measuring what I claim and A1/A2 mean nothing.

Pre-registered, before running (criterion names continue M71's series):

  PR-9a  A1 moves kappa by < 0.01 percentage points  => floor immaterial
  PR-9b  A2 moves kappa by < 0.03 percentage points  => immaterial even at 3x
         amplitude and the top of M72's correlation range
  PR-9c  A3 recovers the planted pattern to within 5% of
         sqrt(kappa0^2 + planted^2) => the estimator is live and A1/A2 are
         meaningful nulls rather than a dead instrument returning a constant
"""
import importlib.util
import json
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent
CACHE = HERE / "out" / "cache"
DATA = HERE / "data"
OUT = DATA / "14-correlated-floor.json"

spec = importlib.util.spec_from_file_location(
    "k5", pathlib.Path(__file__).resolve().parent / "05-kappa.py")
k5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(k5)

N = k5.N
residual = k5.residual
tag_of = k5.tag_of

PLANTED = 0.0020          # A3: 0.20% fixed multiplicative pattern
RNG = np.random.default_rng(20260823)


def corr_kernel(r_target):
    """3x3 cross kernel [ .a. / a1a / .a. ] giving nearest-neighbour
    correlation r_target after normalisation. For a cross of 4 arms,
    r(1,0) = a / (1 + 4a^2) to first order; solve exactly."""
    if r_target <= 0:
        return None
    # Unit-power cross kernel; lag-(1,0) overlap is h(-1,0)h(0,0) + h(0,0)h(1,0)
    # = 2a over the power 1+4a^2. The factor 2 is easy to drop -- the first run
    # of this script did drop it and delivered r = 0.111 for a requested 0.055.
    # `realised_r` exists to catch exactly that, and did.
    lo, hi = 0.0, 0.5
    for _ in range(200):
        a = 0.5 * (lo + hi)
        r = 2.0 * a / (1.0 + 4.0 * a * a)
        if r < r_target:
            lo = a
        else:
            hi = a
    a = 0.5 * (lo + hi)
    k = np.array([[0.0, a, 0.0], [a, 1.0, a], [0.0, a, 0.0]])
    return k / np.sqrt((k * k).sum())      # unit power -> preserves variance


def conv3(x, k):
    out = np.zeros_like(x)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            w = k[dy + 1, dx + 1]
            if w:
                out += w * np.roll(np.roll(x, dy, 0), dx, 1)
    return out


def realised_r(x):
    x = x - x.mean()
    v = float(np.mean(x * x))
    return float(np.mean(x[1:, :] * x[:-1, :]) / v)


def correlated_noise(shape, sd, r_target):
    k = corr_kernel(r_target)
    w = RNG.standard_normal(shape).astype(np.float64)
    if k is not None:
        w = conv3(w, k)
    w -= w.mean()
    w *= sd / w.std()
    return w


def kappa_from(g1a, g2a, g1b, g2b):
    da = residual(g1a) - residual(g2a)
    db = residual(g1b) - residual(g2b)
    c = float(np.mean((da - da.mean()) * (db - db.mean())))
    return (np.sqrt(c / 2.0) if c > 0 else -np.sqrt(-c / 2.0)), c


def main():
    frames = json.loads((DATA / "02-frames.json").read_text(encoding="utf-8"))
    prev = json.loads((DATA / "05-kappa.json").read_text(encoding="utf-8"))

    clean = []
    for exp in sorted({r["exp"] for r in frames}):
        for half in ("A", "B"):
            g = [r for r in frames if r["exp"] == exp and r["half"] == half]
            if max(max(r[f"clip_{p}"] for p in k5.PLANES) for r in g) == 0:
                mb = {p: float(np.mean([r[f"mean_{p}"] for r in g]))
                      for p in k5.PLANES}
                clean.append({"exp": exp, "half": half, "tag": tag_of(exp, half),
                              "mbar": mb})
    pairs = []
    for exp in sorted({c["exp"] for c in clean}):
        hs = [c for c in clean if c["exp"] == exp]
        if len(hs) == 2:
            pairs.append((exp, hs[0], hs[1]))
    print(f"{len(pairs)} matched-shutter pairs clean in all four planes\n")

    rows = []
    for exp, ca, cb in pairs:
        ta, tb = ca["tag"], cb["tag"]
        g1a = np.load(CACHE / f"{ta}-G1-mean.npy").astype(np.float64)
        g2a = np.load(CACHE / f"{ta}-G2-mean.npy").astype(np.float64)
        g1b = np.load(CACHE / f"{tb}-G1-mean.npy").astype(np.float64)
        g2b = np.load(CACHE / f"{tb}-G2-mean.npy").astype(np.float64)
        S = 0.5 * (ca["mbar"]["G1"] + ca["mbar"]["G2"])

        # real per-mean relative noise sd, from the measured temporal variance
        sds = []
        for t, p in ((ta, "G1"), (ta, "G2"), (tb, "G1"), (tb, "G2")):
            v = np.load(CACHE / f"{t}-{p}-var.npy").astype(np.float64)
            sds.append(np.sqrt(float(v.mean()) / N))
        sd = float(np.mean(sds))

        k0, c0 = kappa_from(g1a, g2a, g1b, g2b)

        # A1: correlated floor at the DARK correlation, real amplitude
        sh = g1a.shape
        # A1: correlated floor at the DARK correlation, real amplitude
        n1 = [correlated_noise(sh, sd, 0.055) for _ in range(4)]
        a1 = kappa_from(*[x + n for x, n in zip((g1a, g2a, g1b, g2b), n1)])[0]
        # A2: stress -- r = 0.16 (top of M72's range) and 3x amplitude
        n2 = [correlated_noise(sh, 3 * sd, 0.16) for _ in range(4)]
        a2 = kappa_from(*[x + n for x, n in zip((g1a, g2a, g1b, g2b), n2)])[0]
        r1_real = float(np.mean([realised_r(n) for n in n1]))
        r2_real = float(np.mean([realised_r(n) for n in n2]))
        # A3: positive control -- FIXED pattern, identical in A and B, and
        # opposite in sign between the greens so it survives the difference
        fixed = RNG.standard_normal(sh)
        fixed = (fixed - fixed.mean()) / fixed.std() * PLANTED / np.sqrt(2.0)
        a3 = kappa_from(g1a * (1 + fixed), g2a * (1 - fixed),
                        g1b * (1 + fixed), g2b * (1 - fixed))[0]
        expect3 = np.sqrt(k0 ** 2 + PLANTED ** 2)

        rows.append({"exp": exp, "S": S, "sd_mean_noise": sd,
                     "k0": k0, "A1": a1, "A2": a2, "A3": a3,
                     "A1_realised_r": r1_real, "A2_realised_r": r2_real,
                     "A3_expected": float(expect3)})
        print(f"  S={S:8.1f}  kappa0={100*k0:.4f}%  "
              f"A1={100*a1:.4f}% ({100*(a1-k0):+.4f}, r={r1_real:.3f})  "
              f"A2={100*a2:.4f}% ({100*(a2-k0):+.4f}, r={r2_real:.3f})  "
              f"A3={100*a3:.4f}% vs expected {100*expect3:.4f}%")

    k0m = float(np.mean([r["k0"] for r in rows]))
    d1 = float(np.mean([r["A1"] - r["k0"] for r in rows]))
    d2 = float(np.mean([r["A2"] - r["k0"] for r in rows]))
    r3 = float(np.mean([r["A3"] / r["A3_expected"] for r in rows]))

    print(f"\n  baseline kappa (mean over pairs) = {100*k0m:.4f}%  "
          f"(committed headline {100*prev['kappa']:.4f}%)")
    print(f"  A1 mean shift {100*d1:+.5f} pp   PR-9a (<0.01) "
          f"{'MET' if abs(100*d1) < 0.01 else 'FAILED'}")
    print(f"  A2 mean shift {100*d2:+.5f} pp   PR-9b (<0.03) "
          f"{'MET' if abs(100*d2) < 0.03 else 'FAILED'}")
    print(f"  A3 recovery ratio {r3:.4f}       PR-9c (within 5%) "
          f"{'MET' if abs(r3-1) < 0.05 else 'FAILED'}")

    kk = corr_kernel(0.055)
    chk = correlated_noise((512, 512), 1.0, 0.055)
    print(f"\n  plant validation: requested r(1,0)=0.055, realised "
          f"{realised_r(chk):+.4f} on a 512^2 draw")
    print("  NOTE: the FIRST run of this script had a factor-2 error in the "
          "kernel solve\n  and therefore ran A1 at r=0.111 and A2 at r=0.32 -- "
          "both passed too,\n  which is free headroom evidence above M72's "
          "quoted +0.05..+0.16 range.")

    out = {"preregistered": {"PR-9a": "A1 shift < 0.01 pp",
                             "PR-9b": "A2 shift < 0.03 pp",
                             "PR-9c": "A3 recovers within 5%"},
           "planted_amplitude": PLANTED, "rows": rows,
           "kappa_baseline_mean": k0m,
           "committed_headline": prev["kappa"],
           "A1_shift_pp": 100 * d1, "A2_shift_pp": 100 * d2,
           "A3_recovery_ratio": r3,
           "realised_r_check": realised_r(chk),
           "first_run_accidental_r": {"A1": 0.111, "A2": 0.32,
                                      "A1_shift_pp": -0.00001,
                                      "A2_shift_pp": +0.00026,
                                      "note": "factor-2 kernel bug; both passed"},
           "PR-9a": "MET" if abs(100 * d1) < 0.01 else "FAILED",
           "PR-9b": "MET" if abs(100 * d2) < 0.03 else "FAILED",
           "PR-9c": "MET" if abs(r3 - 1) < 0.05 else "FAILED"}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
