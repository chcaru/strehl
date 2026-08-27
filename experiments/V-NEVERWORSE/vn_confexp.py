# -*- coding: utf-8 -*-
"""ORCH ask 3: predict the ceiling of the fix the build lane is writing.

THE FIX UNDER TEST, as ORCH described it: a *confidence-dependent exponent* --
"where the between-frame band-energy differences are inside the noise of their
own estimate, selectivity collapses toward averaging; where they are
significant against the calibrated noise, it stays sharp."

This is NOT the arm (c) already reported. Arm (c) flattened the exponent
everywhere and cost 9-30% of sharpness. The fix is arm (c) applied
SELECTIVELY, so it should in principle buy the same blotch reduction for less
sharpness. That is the claim under test.

WHAT I HAD TO GUESS, stated plainly: ORCH gave the rule in words, not code, and
the build lane's constants do not exist yet. I implement the most defensible
reading and then sweep its one free parameter, so the conclusion does not rest
on my choice of it:

    confidence c = (spread of band energies across frames) / (noise of that
                   spread), squashed to [0,1]
    p_eff        = 1 + (p - 1) * c

At c=0 (differences indistinguishable from noise) p_eff = 1, which is the
gentlest selectivity the shipping code supports without becoming a mean.
At c=1 p_eff = p, i.e. shipping behaviour. Any monotone squash with those two
endpoints is the same fix; `KAPPA` sets how fast it turns on and is swept.
"""
import io
import json
import os
import sys

import numpy as np

import vn_pyr as VP
from vn_plateau import BETA, SHIP, blotch, sharpness
from vn_snrref import load

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\confexp"


def merge_confident(frames, cfg, beta, var0, nb=7, kappa=1.0, p_lo=1.0):
    """The shipping pyramid merge with a confidence-dependent exponent.

    Identical to `vn_pyr.merge` except for the three marked lines, so any
    difference in the result is attributable to the exponent rule alone.
    """
    exponent, sharpen, gate = cfg["exponent"], cfg["sharpen"], cfg["gate"]
    h, w = frames[0].shape[:2]
    plane_laps, plane_bases, laps = [], [], []
    for f in frames:
        pl, pb = [], []
        for c in range(3):
            Lc, Bc = VP.lap_pyr(f[:, :, c].astype(np.float64), nb)
            pl.append(Lc)
            pb.append(Bc)
        plane_laps.append(pl)
        plane_bases.append(pb)
        laps.append(pl[1])
        plane_bases[-1] = pb
    varp = VP.gauss_pyr(var0, nb)
    n = len(frames)
    out_lv, wstack_lv = [], []

    for k in range(nb):
        p = VP.exponent_at(k, nb, exponent, sharpen)
        vv = varp[k]
        floor = gate * beta[k] * np.maximum(vv, 0.0)
        sqs = np.stack([VP.smooth5(laps[i][k] ** 2) for i in range(n)])
        exc = np.maximum(sqs - floor, 0.0)

        # ---- THE FIX, and the only difference from vn_pyr.merge ----
        # Is the spread of band energies across frames larger than the noise
        # of those energies? `sq` is a 5-tap-smoothed square of an
        # approximately Gaussian coefficient, so its own relative sd is
        # sqrt(2/keff) where keff = 1/sum(k2d^2) = 1/(sum(K^2))^2 for the
        # separable kernel. I scale it by the MEASURED local mean band energy
        # rather than by the floor, so the confidence is not a restatement of
        # the gate I am testing.
        keff = 1.0 / float((VP.K ** 2).sum()) ** 2
        sd_est = np.sqrt(2.0 / keff) * np.maximum(sqs.mean(axis=0), 1e-12)
        spread = sqs.max(axis=0) - sqs.min(axis=0)
        conf = 1.0 - np.exp(-kappa * (spread / sd_est))
        p_eff = p_lo + (p - p_lo) * conf
        # ------------------------------------------------------------

        r = exc / np.maximum(floor, 1.0) / VP.SNR_REF
        # Reproduce select_weight's branch structure per pixel, including the
        # unclamped p==1 and p==2 fast paths, so that the two degenerate
        # limits below are EXACT identities rather than approximations. If I
        # clamped unconditionally, kappa=0 would not equal the flat-exponent
        # arm and kappa=inf would not equal shipping, and the commissioning
        # would be measuring my shortcut instead of the rule.
        pe = np.broadcast_to(p_eff, r.shape)
        W = np.zeros_like(r)
        f1 = (pe == 1.0) & (exc > 0.0)
        f2 = (pe == 2.0) & (exc > 0.0)
        gen = (exc > 0.0) & ~f1 & ~f2
        W[f1] = r[f1]
        W[f2] = r[f2] * r[f2]
        if np.any(gen):
            W[gen] = np.exp(np.clip(pe[gen] * np.log(
                np.maximum(r[gen], 1e-300)), -VP._CLAMP, VP._CLAMP))
        wstack_lv.append(W)
        den = W.sum(axis=0)
        chans = []
        for c in range(3):
            num = sum(W[i] * plane_laps[i][c][k] for i in range(n))
            usum = sum(plane_laps[i][c][k] for i in range(n))
            chans.append(np.where(den > 0.0, num / np.maximum(den, 1e-30),
                                  usum / n))
        out_lv.append(chans)

    base = [np.mean([plane_bases[i][c] for i in range(n)], axis=0)
            for c in range(3)]
    rec = np.zeros((h, w, 3))
    for c in range(3):
        R = base[c]
        for k in range(nb - 1, -1, -1):
            R = VP.expand(R, out_lv[k][c].shape) + out_lv[k][c]
        rec[:, :, c] = R
    if cfg.get("hull", True):
        lo = frames[0].astype(np.float64)
        hi = lo.copy()
        for f in frames[1:]:
            ff = f.astype(np.float64)
            np.minimum(lo, ff, out=lo)
            np.maximum(hi, ff, out=hi)
        rec = np.clip(rec, lo, hi)
    return rec, wstack_lv


def commission(frames, var0, nb=7):
    """Both directions, on the FIX itself rather than on the statistics.

    The improvement arm is the one that matters here: a confidence rule that
    silently reduces to 'always average' would improve blotch and look like a
    success, so the harness must be able to tell the two apart.
    """
    ok, bad = [], []
    # DEGRADATION: kappa -> 0 makes confidence 0 everywhere, so p_eff -> 1
    # everywhere. That is exactly arm (c), and it MUST reproduce arm (c).
    r0, _ = merge_confident(frames, SHIP, BETA, var0, nb, kappa=0.0)
    rc, _ = VP.merge(frames, dict(SHIP, exponent=1.0, sharpen=1.0), BETA,
                     var0, nb)
    d = float(np.abs(r0 - rc).max())
    (ok if d < 1e-6 else bad).append(
        "DEGENERATE LOW: kappa=0 reproduces the flat-exponent arm exactly, "
        "max |dpixel| %.3g (must be ~0)" % d)
    # IMPROVEMENT: kappa -> huge makes confidence 1 everywhere, so p_eff -> p.
    # That MUST reproduce the shipping merge exactly.
    r1, _ = merge_confident(frames, SHIP, BETA, var0, nb, kappa=1e12)
    rs, _ = VP.merge(frames, dict(SHIP), BETA, var0, nb)
    d1 = float(np.abs(r1 - rs).max())
    (ok if d1 < 1e-6 else bad).append(
        "DEGENERATE HIGH: kappa=inf reproduces the SHIPPING merge exactly, "
        "max |dpixel| %.3g (must be ~0)" % d1)
    # The two endpoints must actually differ, or the above pair is vacuous.
    d2 = float(np.abs(r0 - r1).max())
    (ok if d2 > 1.0 else bad).append(
        "ENDPOINTS DIFFER: the two limits are %.3g apart, so the rule has "
        "room to act (a vacuous rule would read 0 here)" % d2)
    return ok, bad


def oracle_frontier(rec_ship, rec_flat, frames, srcb, srcs):
    """An upper bound on ANY per-pixel exponent rule, using the answer.

    A confidence-dependent exponent chooses, per pixel, somewhere between
    p_eff=1 (the flat arm) and p_eff=p (shipping). No such rule can beat an
    oracle that makes that choice in image space with the finished
    reconstructions in hand -- and the oracle is strictly stronger, because it
    selects after reconstruction rather than per band. So if the oracle still
    violates the never-worse bound, no confidence rule can rescue the subject,
    whatever the build lane writes.
    """
    d = rec_ship.mean(axis=2) - rec_flat.mean(axis=2)
    band = np.abs(VP.smooth5(d) - VP.smooth5(VP.smooth5(VP.smooth5(d))))
    out = []
    for q in (0.1, 0.25, 0.5, 0.75, 0.9):
        t = np.quantile(band, 1.0 - q)
        m = (band >= t)[:, :, None]
        rec = np.where(m, rec_flat, rec_ship)
        b, s = blotch(rec)[0], sharpness(rec)
        out.append(dict(arm="o_oracle", frac_flattened=q, blotch=b,
                        sharpness=s, blotch_vs_best_source=b / srcb,
                        sharp_vs_best_source=s / srcs))
        print("  %-18s %8.2f %6.3fx    %6.3fx"
              % ("o_oracle", q, b / srcb, s / srcs))
    return out


def frontier_gap(front, s, b):
    """Blotch of the scalar-knob frontier at sharpness `s`, minus `b`.

    Positive means the confidence rule is BELOW the scalar frontier, i.e. it
    buys blotch that no single scalar exponent buys at that sharpness. Zero or
    negative means the fix is a more complicated way to reach a point a scalar
    already reaches, which is the outcome that would refute it.
    """
    pts = sorted(front, key=lambda r: r["sharp_vs_best_source"])
    xs = [r["sharp_vs_best_source"] for r in pts]
    ys = [r["blotch_vs_best_source"] for r in pts]
    if s <= xs[0] or s >= xs[-1]:
        return None
    return float(np.interp(s, xs, ys) - b)


def main():
    os.makedirs(OUT, exist_ok=True)
    subj = sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles"
    frames = load(subj)
    var0, read2, gph = VP.fit_variance(frames[0][:, :, 1])
    if gph < 0:
        print("REFUSED: fitted photon gain is negative")
        return 2
    print("%s: %d OK frames" % (subj, len(frames)))

    print("\ncommissioning the fix (both directions):")
    ok, bad = commission(frames, var0)
    for l in ok:
        print("  ok      " + l)
    for l in bad:
        print("  FAILED  " + l)
    if bad:
        print("REFUSED: the confidence rule is not commissioned")
        return 2

    srcb = min(blotch(f)[0] for f in frames)
    srcs = max(sharpness(f) for f in frames)
    rows = []

    def arm(name, rec, **kw):
        b, s = blotch(rec)[0], sharpness(rec)
        r = dict(arm=name, blotch=b, sharpness=s,
                 blotch_vs_best_source=b / srcb,
                 sharp_vs_best_source=s / srcs, **kw)
        rows.append(r)
        return r

    print("\n  %-18s %8s %10s %10s %12s"
          % ("arm", "knob", "blotch", "sharp", "vs frontier"))

    # The scalar-knob frontier: every point reachable by turning down the
    # existing exponent, with no new code at all. The fix has to beat THIS,
    # not just beat shipping.
    front = []
    for e, sh in ((2.0, 1.4), (1.8, 1.35), (1.6, 1.3), (1.4, 1.2),
                  (1.2, 1.1), (1.0, 1.0)):
        rec, _ = VP.merge(frames, dict(SHIP, exponent=e, sharpen=sh), BETA,
                          var0)
        r = arm("u_scalar", rec, exponent=e, sharpen=sh)
        front.append(r)
        print("  %-18s %8s %6.3fx    %6.3fx" %
              ("u_scalar", "e=%.1f" % e, r["blotch_vs_best_source"],
               r["sharp_vs_best_source"]))

    gaps = []
    for kap in (0.005, 0.01, 0.05, 0.1, 0.5, 1.0):
        rec, _ = merge_confident(frames, SHIP, BETA, var0, kappa=kap)
        r = arm("e_confidence", rec, kappa=kap)
        g = frontier_gap(front, r["sharp_vs_best_source"],
                         r["blotch_vs_best_source"])
        r["frontier_gap"] = g
        if g is not None:
            gaps.append(g)
        print("  %-18s %8.3f %6.3fx    %6.3fx %12s"
              % ("e_confidence", kap, r["blotch_vs_best_source"],
                 r["sharp_vs_best_source"],
                 "n/a" if g is None else "%+.4f" % g))

    best = min((r["blotch_vs_best_source"] for r in rows
                if r["arm"] == "e_confidence"))
    ship = [r for r in front if r.get("exponent") == 2.0][0]

    rs, _ = VP.merge(frames, dict(SHIP), BETA, var0)
    rf, _ = VP.merge(frames, dict(SHIP, exponent=1.0, sharpen=1.0), BETA, var0)
    print("\n  oracle bound on any per-pixel exponent rule:")
    orc = oracle_frontier(rs, rf, frames, srcb, srcs)
    rows.extend(orc)
    obest = min(r["blotch_vs_best_source"] for r in orc)

    # COMMISSIONING THE ORACLE. It has strictly more freedom than any
    # confidence rule, so it must reach at least one point the scalar knob
    # cannot. An "oracle" that sits below the scalar frontier everywhere is
    # not an upper bound on anything and must not be quoted as one.
    og = [frontier_gap(front, r["sharp_vs_best_source"],
                       r["blotch_vs_best_source"]) for r in orc]
    og = [g for g in og if g is not None]
    if not og or max(og) <= 0.0:
        print("  REFUSED: the oracle does not dominate the scalar frontier "
              "(max gap %s), so it bounds nothing"
              % ("n/a" if not og else "%+.4f" % max(og)))
        return 2
    print("  ok      oracle dominates the scalar frontier by %+.4f blotch at "
          "matched sharpness, so it is a real upper bound" % max(og))

    print("\n  best reachable blotch under the fix : %.3fx" % best)
    print("  best reachable by the ORACLE bound  : %.3fx" % obest)
    print("  shipping                            : %.3fx"
          % ship["blotch_vs_best_source"])
    print("  excess over the never-worse bound removed: %.1f%%"
          % (100.0 * (ship["blotch_vs_best_source"] - best)
             / max(ship["blotch_vs_best_source"] - 1.0, 1e-9)))
    print("  ORACLE removes                          : %.1f%%"
          % (100.0 * (ship["blotch_vs_best_source"] - obest)
             / max(ship["blotch_vs_best_source"] - 1.0, 1e-9)))
    if obest > 1.0:
        print("  -> even the oracle still VIOLATES the never-worse bound, "
              "so no per-pixel exponent rule can clear this subject")
    if gaps:
        print("  max gain over the scalar knob at matched sharpness: %+.4f"
              % max(gaps))
        if max(gaps) <= 0.005:
            print("  -> the fix reaches no point a scalar exponent does not")

    res = dict(subject=subj, frames=len(frames), rows=rows,
               best_confidence_blotch=best, oracle_best_blotch=obest,
               shipping_blotch=ship["blotch_vs_best_source"],
               max_frontier_gap=(max(gaps) if gaps else None),
               source=dict(blotch_min=srcb, sharp_max=srcs),
               noise_fit=dict(read2=read2, gain=gph))
    p = os.path.join(OUT, "%s.json" % subj)
    json.dump(res, io.open(p, "w", encoding="utf-8"), indent=1)
    print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("\nREFUSED: crashed; no claim about the fix is measured")
        sys.exit(2)
