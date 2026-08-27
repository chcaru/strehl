"""tonecheck.py -- audit of V-NOISE2's own TONE arm, before it is allowed to
withdraw anything.

WHY THIS FILE EXISTS.  Running hd2.py on subject 113 reproduced M127's ratios
to the digit (1.540 / 1.763 / 1.538) and its scene/noise decomposition exactly
(0.05187 noise, 0.12151 scene, 15.4%).  One thing did NOT reproduce: the TONE
arm.  M127 measured -153.05% explained for `enfuse`; this lane's TONE arm
measured +60.17% and declared the ratios a tone measurement.  A guard that
flips sign between two runs of the same statistic on the same pixels is making
a claim about the instrument, not about the image, and it does not get to
withdraw a headline until that claim is settled.

THE THREE PREDICTIONS, registered before running (sec.0 of PREREGISTRATION.md
governs: blind to the data, not to the hypothesis).

  P1  BASELINE MISMATCH.  hd2.py compares s_st = the INTEGER-SHIFT CORRECTED
      strehl sigma against s_tn = half_sigma_y of the toned halves with NO
      shift applied.  Those are two estimators of different quantities.  On a
      consistently RAW basis the 113/enfuse fraction should be strongly
      NEGATIVE, near M127's -153%.

  P2  NEGCTL, whose answer is fixed by construction, returns 0%.  Its target
      is strehl PLUS NOISE: it differs from strehl by nothing but noise, so
      its true tone content is identically zero at every noise level.  A
      non-zero answer is the arm scoring its own circularity -- a quantile map
      fitted from a clean image to a noisy one can take slope from the noise.

  P3  POSCTL, whose answer is also fixed by construction, returns 100%.  Its
      target is strehl put through a KNOWN gamma: it differs from strehl by
      nothing but tone, so a tone fit must account for all of the gap.

P2 without P3 is the failure this project has been bitten by before -- an arm
commissioned only against a planted defect passes trivially if it is blind.
NEGCTL alone cannot distinguish "the arm is sound" from "the arm always
returns a small number".  POSCTL is the arm that can only be passed by an
instrument that actually responds to tone.

Usage:  python tonecheck.py [113|119|fba|bee]
"""
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "V-NOISE"))
from noisefree import Arm, opponent, coarse4, EDGE                 # noqa: E402
from halfdiff import half_sigma                                    # noqa: E402
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
from gradetest import fit_map, apply_map                           # noqa: E402
from hd2 import (SUBJECTS, paths_for, scales_for, bits_of,         # noqa: E402
                 half_sigma_y)

ROOT = r"C:\dev\strehl-out\V-NOISE2"
GAMMA = 0.75          # POSCTL's known tone curve on [0,1] luma
PLANT = (0.5, 1.0, 2.0)   # NEGCTL noise, as multiples of strehl's own sigma


def arm_gain(SA, SB, tgt_lum, live):
    """The TONE arm's one degree of freedom: fit strehl->target on 4x4 blocks,
    apply to BOTH strehl halves, report what it did to strehl's half-diff.

    `tgt_lum(y, x)` returns the target's luma tile.  Everything the arm ever
    reads from a comparator is its luma, so a synthetic target is a function,
    not an image on disk.
    """
    xs, ys = [], []
    for (y, x) in live:
        ya, _, _ = opponent(SA.rgb(y, x))
        xs.append(coarse4(ya).ravel())
        ys.append(coarse4(tgt_lum(y, x)).ravel())
    mp = fit_map(np.concatenate(xs), np.concatenate(ys))

    base, toned = [], []
    for (y, x) in live:
        ya, _, _ = opponent(SA.rgb(y, x))
        yb, _, _ = opponent(SB.rgb(y, x))
        base.append(half_sigma_y(ya, yb))
        toned.append(half_sigma_y(apply_map(mp, ya), apply_map(mp, yb)))
    b = float(np.nanmedian(base))
    t = float(np.nanmedian(toned))
    return b, t, (t / b if b > 0 else float("nan"))


def explained(gain, s_st, s_tg):
    """Fraction of the strehl->target gap that the fitted tone map accounts
    for, on one consistent basis."""
    gap = s_tg - s_st
    return (s_st * gain - s_st) / gap if abs(gap) > 1e-12 else float("nan")


def main():
    key = "113"
    for a in sys.argv[1:]:
        if a in SUBJECTS:
            key = a
    meta = SUBJECTS[key]
    census, spec = paths_for(key)
    SC = scales_for(key)
    z = np.load(census)
    live = [tuple(c) for c in z["cells"][z["flat"]]]

    print("=" * 100)
    print(f"TONE-ARM AUDIT for {key} = {meta['name']}   ({meta['n']} frames, "
          f"{meta['depth']}, {meta['regime']}-dominated)")
    print("=" * 100)

    P = {k: (v[0], v[1]) for k, v in spec.items()}
    arms = {k: (Arm(pa, SC.get(k, 1.0), bits_of(pa), k),
                Arm(pb, SC.get(k, 1.0), bits_of(pb), k))
            for k, (pa, pb) in P.items()}
    SA, SB = arms["strehl"]

    good = []
    for (y, x) in live:
        if all(A.rgb(y, x) is not None and B.rgb(y, x) is not None
               and A.rgb(y, x).shape == B.rgb(y, x).shape
               for A, B in arms.values()):
            good.append((y, x))
    live = good
    print(f"  {len(live)} FLAT tiles deliverable by every arm")

    raw, cor = {}, {}
    for k, (A, B) in arms.items():
        sh = (k == "strehl")
        raw[k] = float(np.median([half_sigma(A.rgb(y, x), B.rgb(y, x),
                                             shift=False)[0] for (y, x) in live]))
        cor[k] = float(np.median([half_sigma(A.rgb(y, x), B.rgb(y, x),
                                             shift=sh)[0] for (y, x) in live]))

    print("\n--- P1: the two baselines hd2.py's TONE arm mixed ---")
    print(f"  {'arm':10s} {'RAW (no shift)':>16s} {'SHIFT-CORRECTED':>18s}")
    for k in arms:
        print(f"  {k:10s} {raw[k]:16.5f} {cor[k]:18.5f}")
    print(f"\n  hd2.py subtracted the CORRECTED strehl sigma {cor['strehl']:.5f}"
          f" from an UNSHIFTED\n  toned sigma.  The like-for-like baseline is "
          f"{raw['strehl']:.5f}, larger by "
          f"{(raw['strehl'] / cor['strehl'] - 1) * 100:.1f}%.")

    rng = np.random.default_rng(20260824)
    out = {"key": key, "raw": raw, "cor": cor, "gamma": GAMMA, "arms": {},
           "negctl": [], "posctl": None}

    print("\n--- P2: NEGCTL -- target is strehl PLUS NOISE.  TRUE ANSWER = 0%. ---")
    neg_gains = []
    for mult in PLANT:
        # level-scaled plant so the planted sigma is uniform in the units the
        # statistic reports, and the achieved ratio matches the intent.
        def tgt(y, x, m=mult):
            r = SA.rgb(y, x)
            return opponent(r + rng.normal(0.0, m * raw["strehl"] * r.mean(),
                                           r.shape))[0]
        sy = []
        for (y, x) in live:
            ra, rb = SA.rgb(y, x), SB.rgb(y, x)
            s = mult * raw["strehl"]
            na = ra + rng.normal(0.0, s * ra.mean(), ra.shape)
            nb = rb + rng.normal(0.0, s * rb.mean(), rb.shape)
            sy.append(half_sigma_y(opponent(na)[0], opponent(nb)[0]))
        s_tg = float(np.nanmedian(sy))
        b, t, g = arm_gain(SA, SB, tgt, live)
        f = explained(g, raw["strehl"], s_tg)
        neg_gains.append(g)
        out["negctl"].append({"mult": mult, "s_tg": s_tg, "gain": g, "frac": f})
        print(f"  plant {mult:4.1f}x strehl sigma -> target sigma {s_tg:.5f} "
              f"(ratio {s_tg / raw['strehl']:5.3f})   gain {g:.4f}"
              f"   explained {f * 100:8.2f}%")
    BIAS = float(np.median(neg_gains))
    print(f"\n  NEGCTL gain across a {min(PLANT)}x-{max(PLANT)}x noise sweep: "
          f"{', '.join(f'{g:.4f}' for g in neg_gains)}")
    print(f"  spread {(max(neg_gains) / min(neg_gains) - 1) * 100:.2f}% -- the "
          f"arm's gain is {'INSENSITIVE' if max(neg_gains)/min(neg_gains) < 1.02 else 'SENSITIVE'}"
          f" to how noisy the target is.")
    print(f"  BIAS = {BIAS:.4f}: what this arm does to strehl when there is NO "
          f"tone to find.")

    print(f"\n--- P3: POSCTL -- target is strehl through a KNOWN gamma "
          f"{GAMMA}.  TRUE ANSWER = 100%. ---")

    def tgt_pos(y, x):
        return np.clip(opponent(SA.rgb(y, x))[0], 0, None) ** GAMMA
    sy = []
    for (y, x) in live:
        ga = np.clip(opponent(SA.rgb(y, x))[0], 0, None) ** GAMMA
        gb = np.clip(opponent(SB.rgb(y, x))[0], 0, None) ** GAMMA
        sy.append(half_sigma_y(ga, gb))
    s_pos = float(np.nanmedian(sy))
    b, t, g_pos = arm_gain(SA, SB, tgt_pos, live)
    f_pos = explained(g_pos, raw["strehl"], s_pos)
    f_pos_c = explained(g_pos / BIAS, raw["strehl"], s_pos)
    out["posctl"] = {"s_tg": s_pos, "gain": g_pos, "frac": f_pos,
                     "frac_biascorr": f_pos_c}
    print(f"  gamma target sigma {s_pos:.5f} (ratio "
          f"{s_pos / raw['strehl']:5.3f})   gain {g_pos:.4f}")
    print(f"  explained {f_pos * 100:7.2f}%   bias-corrected "
          f"{f_pos_c * 100:7.2f}%   (true 100%)")
    pos_ok = abs(f_pos_c - 1.0) <= 0.25
    print(f"  {'PASS -- the arm can see a real tone difference' if pos_ok else 'FAIL -- THE ARM IS BLIND TO TONE'}")

    print("\n--- the real comparators, bias-corrected against NEGCTL ---")
    for k in arms:
        if k == "strehl":
            continue
        b, t, g = arm_gain(SA, SB, lambda y, x, kk=k: opponent(arms[kk][0].rgb(y, x))[0],
                           live)
        f_raw = explained(g, raw["strehl"], raw[k])
        gc = g / BIAS
        f_cor = explained(gc, cor["strehl"], cor[k])
        out["arms"][k] = {"gain": g, "gain_corr": gc,
                          "frac_raw_basis": f_raw, "frac_corrected": f_cor}
        print(f"  {k:9s} gain {g:.4f} / bias {BIAS:.4f} = {gc:.4f}"
              f"   raw-basis explained {f_raw * 100:8.2f}%"
              f"   -> corrected, verdict basis {f_cor * 100:7.2f}%")

    print("\n--- DC TONE AUDIT (noise-immune): per-tile mean luma ---")
    for k in arms:
        if k == "strehl":
            continue
        rs = []
        for (y, x) in live:
            a = float(opponent(SA.rgb(y, x))[0][EDGE:-EDGE, EDGE:-EDGE].mean())
            c = float(opponent(arms[k][0].rgb(y, x))[0][EDGE:-EDGE, EDGE:-EDGE].mean())
            if a > 1e-6:
                rs.append(c / a)
        rs = np.array(rs)
        out["arms"][k]["dc_tone"] = [float(np.median(rs)), float(rs.min()),
                                     float(rs.max())]
        print(f"  {k:9s} mean-luma ratio comp/strehl  median "
              f"{np.median(rs):.4f}   range [{rs.min():.4f}, {rs.max():.4f}]")

    worst = max(abs(d["frac"]) for d in out["negctl"])
    print("\n" + "-" * 100)
    print(f"  NEGCTL worst |explained| = {worst * 100:.1f}% (true 0%)")
    print(f"  POSCTL bias-corrected    = {f_pos_c * 100:.1f}% (true 100%)")
    if not pos_ok:
        print("  VERDICT: the arm is BLIND to tone.  It cannot clear anything,")
        print("  and its passes on other subjects mean nothing either.")
    elif max(neg_gains) / min(neg_gains) >= 1.02:
        print("  VERDICT: the arm's gain MOVES with the target's noise.  It is")
        print("  circular and cannot be bias-corrected by a single constant.")
    else:
        print("  VERDICT: the arm carries a FIXED multiplicative bias that is")
        print("  independent of the target's noise, and it responds correctly to")
        print("  a real tone difference.  Divide the bias out and it adjudicates.")
    d = os.path.join(ROOT, key)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "tonecheck.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(f"  written {os.path.join(d, 'tonecheck.json')}")


if __name__ == "__main__":
    main()
