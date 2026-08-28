"""Is a sub-gate band coefficient real signal, or pure noise?

`pyramid.rs` asks this question of itself, at the pin, in the doc comment on
`Fallback` (L759-773 of `git show 9b05d0b7:crates/strehl-core/src/pyramid.rs`):

    `den[j] <= 0.0` means no frame's smoothed band energy cleared
    `gate * beta * var`. The shipped answer is the unweighted mean over all
    frames. That is correct for the DC base band ... and a far stronger claim
    for a BAND-PASS coefficient, where the detail exists only in the handful
    of frames that have that pixel in focus. A mean over `N` frames then
    returns roughly `n_focus / N` of it, an attenuation that worsens as the
    stack deepens.

    Whether that is a defect turns on something not yet measured: whether a
    sub-gate coefficient is real signal or pure noise. If it is noise, the
    mean is the correct estimator and the only one that gets below
    single-frame noise. This enum exists so the two readings can be told
    apart by measurement instead of argued.

This is that measurement. It matters because the sub-gate fraction is not a
corner case: on `bee-2-cpl` 99.89% of the FINEST band's coefficients have
nothing admitted, so to three significant figures the whole fine band of that
master is the unweighted mean of every frame in the stack.

THE DISCRIMINATOR. Split the stack into two INTERLEAVED halves, so both halves
span the same focus range and differ only in which frames they contain. At a
sub-gate location each half's mean band coefficient is

    m = S + noise,   noise independent between halves, S common to both.

So the Pearson correlation between the two half-means is

    r = var(S) / (var(S) + var(noise_half))

which is zero for pure noise and positive for real content, and inverts to a
signal-to-noise ratio r/(1-r). Nothing about this needs a merge change, and it
cannot be moved by the selection law, because it never consults the weights.

COMMISSIONING, BOTH DIRECTIONS, AGAINST KNOWN ANSWERS.

  S1 PURE NOISE. Frames are independent noise over one constant scene. The
     band coefficient is pure noise, so r must be ~0. A statistic that cannot
     read zero here would convict the fallback on every subject.
  S2 KNOWN SIGNAL FRACTION. Frames are (fixed pattern) + (independent noise)
     mixed at a known ratio, so the true r is known in closed form and must be
     recovered. This is the planted IMPROVEMENT: a statistic that only reads
     low is as useless as one that only reads high.
  S3 MONOTONE RESPONSE. r must rise with the planted signal fraction across a
     sweep, and must not short-circuit -- the zero-signal rung is required to
     be near zero and the response strictly increasing.

Reads cached bundles only. Never writes to D:.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vn_pyr as VP  # noqa: E402
from vn_plateau import BETA, SHIP  # noqa: E402

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\dilute"
NB = 7
GATE = SHIP["gate"]
# Per-band exponent ladder, exactly as pyramid.rs builds it: the shipping
# `exponent` scaled by `sharpen_per_octave` per step toward the fine bands and
# clamped at MAX_EXPONENT. Measured as [8.00, 8.00, 7.68, 5.49, 3.92, 2.80,
# 2.00] at nb=7 in RESULT.md section 9.
EXPO = [VP.exponent_at(k, NB, SHIP["exponent"], SHIP["sharpen"])
        for k in range(NB)]
MIN_PX = 64
# Per-frame band amplitude of the commissioning stack, in DN. Held constant
# across the whole signal-fraction sweep so the gate decision does not move.
SIG = 40.0


def corr(a, b):
    a = a.astype(np.float64).ravel()
    b = b.astype(np.float64).ravel()
    if a.size < 8:
        return float("nan")
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    if d <= 0.0:
        return float("nan")
    return float((a * b).sum() / d)


def halfsplit(n, mode="interleave"):
    """Two halves that span the same focus range and differ only in membership.

    A first-half/second-half split would give the two arms DIFFERENT focus
    ranges, and the correlation between them would then measure how alike the
    near and far ends of the stack are rather than whether a coefficient is
    real. The arms must differ only in which frames they hold.

    `interleave` takes even/odd indices. That is the tightest possible focus
    match, but it has one failure mode: if anything in the capture ALTERNATES
    frame to frame -- flash recycle, rail settle, exposure toggling -- then
    every such frame lands in the same half and the two halves differ
    systematically. `pair` puts adjacent frames in the SAME half (0,1 | 2,3 |
    4,5 ...), so an alternation cannot separate the arms, at the cost of a
    slightly coarser focus match. Disagreement between the two splits on the
    same stack is a common-cause artifact, not a merge property.
    """
    if mode == "pair":
        A = [i for i in range(n) if (i // 2) % 2 == 0]
        B = [i for i in range(n) if (i // 2) % 2 == 1]
        return A, B
    return list(range(0, n, 2)), list(range(1, n, 2))


def subgate(frames, nb=NB, var0=None, split="interleave"):
    """Per band: coherence of two disjoint half-stacks, sub-gate and
    above-gate, for the shipping weighting AND for the plain mean.

    One streaming pass. `dead` is computed from the FULL stack, because that
    is the condition under which the shipping merge takes the fallback, and
    holding the pixel set fixed is what lets the two weighting laws be
    compared on the same pixels.

    Three quantities per band, all on identical pixel sets:

      r_subgate   plain half-mean coherence where NOTHING was admitted. This
                  is the shipping output there, because Fallback::Mean is the
                  default, so it is simultaneously a property of the merge and
                  of the frames.
      r_merge     SHIPPING-WEIGHTED half coherence above the gate.
      r_mean      plain half-mean coherence above the gate. THE CONTROL. It
                  contains no selection at all, so anything that moves both
                  arms together is a property of the frames -- misregistration
                  or genuine scene difference -- and cannot be charged to the
                  weighting law.

    The first version of this function computed only the plain half-mean and
    called it `r_abovegate`. The name implied a statement about the merge's
    above-gate behaviour; the quantity could not see the merge at all. It is
    kept here as `r_mean` under a name that says what it is.
    """
    n = len(frames)
    if var0 is None:
        var0 = VP.fit_variance(frames[0])[0]
    varp = VP.gauss_pyr(var0, nb)
    A, B = halfsplit(n, split)
    setA = set(A)
    sA = [np.zeros(varp[k].shape) for k in range(nb)]
    sB = [np.zeros(varp[k].shape) for k in range(nb)]
    wlA = [np.zeros(varp[k].shape) for k in range(nb)]
    wlB = [np.zeros(varp[k].shape) for k in range(nb)]
    wA = [np.zeros(varp[k].shape) for k in range(nb)]
    wB = [np.zeros(varp[k].shape) for k in range(nb)]
    adm = [np.zeros(varp[k].shape) for k in range(nb)]
    for i, f in enumerate(frames):
        lap, _ = VP.lap_pyr(f, nb)
        inA = i in setA
        for k in range(nb):
            floor = np.maximum(GATE * BETA[k] * np.maximum(varp[k], 0.0), 1.0)
            ex = VP.smooth5(lap[k] ** 2) - floor
            ok = ex > 0.0
            adm[k] += ok
            r = np.where(ok, ex / floor / VP.SNR_REF, 0.0)
            w = np.where(ok, r ** EXPO[k], 0.0)
            if inA:
                sA[k] += lap[k]
                wlA[k] += w * lap[k]
                wA[k] += w
            else:
                sB[k] += lap[k]
                wlB[k] += w * lap[k]
                wB[k] += w
    rows = []
    for k in range(nb):
        mA = sA[k] / max(len(A), 1)
        mB = sB[k] / max(len(B), 1)
        # Reconstruct each half exactly as pyramid.rs does: weighted mean
        # where anything was admitted, unweighted mean where nothing was.
        gA = np.where(wA[k] > 0.0, wlA[k] / np.where(wA[k] > 0.0, wA[k], 1.0),
                      mA)
        gB = np.where(wB[k] > 0.0, wlB[k] / np.where(wB[k] > 0.0, wB[k], 1.0),
                      mB)
        dead = adm[k] <= 0.0
        live = ~dead
        nd, nl = int(dead.sum()), int(live.sum())
        # A correlation over a handful of coefficients is not a reading. The
        # first version gated `scored` on the BAND's size rather than on the
        # number of sub-gate coefficients in it, so a band with 8 dead pixels
        # printed an r beside a band with 800,000 and nothing distinguished
        # them. A skipped band must not read as a measured one.
        r_dead = corr(mA[dead], mB[dead]) if nd >= MIN_PX else float("nan")
        r_live = corr(gA[live], gB[live]) if nl >= MIN_PX else float("nan")
        r_ctl = corr(mA[live], mB[live]) if nl >= MIN_PX else float("nan")
        rows.append(dict(
            band=k, px_total=int(dead.size), px_dead=nd,
            px_live=nl, dead_frac=float(dead.mean()),
            r_subgate=r_dead, r_merge=r_live, r_mean=r_ctl,
            sel_cost=(r_ctl - r_live)
            if r_live == r_live and r_ctl == r_ctl else float("nan"),
            snr_subgate=(r_dead / (1.0 - r_dead))
            if r_dead == r_dead and r_dead < 1.0 else float("nan"),
            scored=bool(nd >= MIN_PX),
            scored_live=bool(nl >= MIN_PX)))
    return rows, dict(n=n, half_a=len(A), half_b=len(B), split=split)


def synth(n, sig_frac, size=192, seed=3):
    """A fixed pattern plus independent per-frame noise, at CONSTANT total
    per-frame variance.

    `sig_frac` is the fraction of per-frame band variance that is common
    scene. The pattern is normalised to unit variance and mixed as
    `sqrt(sig)*pat + sqrt(1-sig)*noise`, so the total per-frame variance --
    and therefore whether a coefficient clears the gate -- is the same at
    every rung. Without that normalisation the sweep changes the gate decision
    as well as the signal fraction, and the arms differ in two things at once.
    That is the error this project has now made in three lanes, so the sweep
    reports its own dead fraction and the commissioning gate requires it to
    stay sub-gate.
    """
    rng = np.random.default_rng(seed)
    # A BROADBAND common field, not a sinusoid. The first version used a
    # single spatial frequency at 0.31/0.27 cyc/px, which lands almost
    # entirely in L0; bands L1-L5 then contained no planted signal at all, the
    # median across bands measured those noise-only bands, and a correctly
    # working discriminator read 0.077 where 0.923 was predicted. A fixed
    # white-noise realisation puts the same signal fraction in every band, so
    # the closed form applies to each of them.
    pat = np.random.default_rng(seed + 991).normal(0, 1.0, (size, size))
    pat = (pat - pat.mean()) / pat.std()
    out = []
    a, b = np.sqrt(sig_frac) * SIG, np.sqrt(1.0 - sig_frac) * SIG
    for _ in range(n):
        out.append(2000.0 + a * pat + b * rng.normal(0, 1.0, (size, size)))
    return out


def commission():
    res, ok = {}, True
    n = 24
    # S1 PURE NOISE: r must be within sampling error of 0 at every scored
    # band. The bar is per band and derived, not a flat constant: the standard
    # error of a correlation over m independent samples is about 1/sqrt(m),
    # and the coarse bands hold only a few hundred coefficients, so a flat
    # 0.08 bar failed a correct instrument on L4 at 144 pixels.
    rows, _ = subgate(synth(n, 0.0), var0=None)
    sc = [x for x in rows
          if x["scored"] and x["r_subgate"] == x["r_subgate"]]
    over = [dict(band=x["band"], r=x["r_subgate"], px=x["px_dead"],
                 bar=4.0 / np.sqrt(x["px_dead"]))
            for x in sc if abs(x["r_subgate"]) > 4.0 / np.sqrt(x["px_dead"])]
    res["S1_pure_noise"] = dict(
        r=[x["r_subgate"] for x in sc], n_scored=len(sc),
        n_skipped=len(rows) - len(sc), n_bands=len(rows),
        max_abs=max(abs(x["r_subgate"]) for x in sc) if sc else None,
        exceeding=over)
    if not sc or over:
        ok = False

    # S2 KNOWN ANSWER. With per-frame band variance split sig_frac / (1 -
    # sig_frac) and half-means over n/2 frames, the noise term averages down
    # by n/2, so
    #     r_true = sig / (sig + (1 - sig) / (n / 2)).
    # That is a closed form, not a fitted constant, and it must be recovered.
    sweep = []
    for sf in (0.0, 0.02, 0.1, 0.5, 0.9):
        rows, meta = subgate(synth(n, sf))
        pred = (sf / (sf + (1.0 - sf) / (n / 2.0))) if sf > 0 else 0.0
        sc = [x for x in rows
              if x["scored"] and x["r_subgate"] == x["r_subgate"]]
        got = [x["r_subgate"] for x in sc]
        sweep.append(dict(sig_frac=sf, r_pred=pred,
                          r_med=float(np.median(got)) if got else float("nan"),
                          n_scored=len(got), n_bands=len(rows),
                          n_skipped=len(rows) - len(sc),
                          dead_frac_med=float(np.median(
                              [x["dead_frac"] for x in sc])) if sc else
                          float("nan")))
    res["S2_sweep"] = sweep
    for s in sweep:
        if s["n_scored"] < 3:
            ok = False
        if s["sig_frac"] in (0.5, 0.9):
            if not (s["r_med"] == s["r_med"]
                    and abs(s["r_med"] - s["r_pred"]) <= 0.10):
                ok = False

    # S3 MONOTONE and non-short-circuit.
    v = [s["r_med"] for s in sweep]
    res["S3_monotone"] = dict(r=v,
                              monotone=bool(all(v[i] < v[i + 1]
                                                for i in range(len(v) - 1))),
                              zero_rung_near_zero=bool(abs(v[0]) < 0.05))
    if not (res["S3_monotone"]["monotone"]
            and res["S3_monotone"]["zero_rung_near_zero"]):
        ok = False

    # S4 THE SELECTION-COST CONTROL, BOTH DIRECTIONS. `sel_cost` is the
    # coherence the shipping weighting LOSES against the plain mean on the
    # same pixels, differing in the weighting law and nothing else.
    #
    # The first version of this gate demanded a large cost on a pure-noise
    # arm. That is unsatisfiable: with no common content the plain mean
    # already reads r = -0.007, so there is no coherence for selection to
    # destroy. A gate that requires a fall from a quantity sitting at its
    # floor can only ever refuse.
    #
    # The correct prediction is an INTERIOR MAXIMUM. At sig_frac = 0 there is
    # nothing to lose; at sig_frac = 1 selection and averaging agree because
    # every frame carries the same content; in between, per-frame noise elects
    # a winner that the other half does not elect, and the cost peaks. Both
    # endpoints near zero AND an interior peak is a two-sided gate that a
    # statistic stuck high, stuck low, or short-circuited cannot pass.
    lo = np.full(synth(4, 0.0)[0].shape, 1e-6)
    fr = (0.0, 0.01, 0.03, 0.10, 0.30, 0.60, 0.90, 0.99)
    s4 = dict(sweep=[])
    for sf in fr:
        rows, _ = subgate(synth(n, sf), var0=lo)
        live = [x for x in rows if x["scored_live"]
                and x["sel_cost"] == x["sel_cost"]]
        s4["sweep"].append(dict(
            sig_frac=sf, n_scored=len(live), n_bands=len(rows),
            n_skipped=len(rows) - len(live),
            sel_cost_med=float(np.median([x["sel_cost"] for x in live]))
            if live else float("nan"),
            r_merge_med=float(np.median([x["r_merge"] for x in live]))
            if live else float("nan"),
            r_mean_med=float(np.median([x["r_mean"] for x in live]))
            if live else float("nan")))
    cost = [d["sel_cost_med"] for d in s4["sweep"]]
    imax = int(np.argmax(cost))
    s4.update(argmax_index=imax, argmax_sig_frac=fr[imax],
              peak=cost[imax], end_lo=cost[0], end_hi=cost[-1],
              interior_peak=bool(0 < imax < len(cost) - 1),
              ends_near_zero=bool(abs(cost[0]) < 0.02
                                  and abs(cost[-1]) < 0.02),
              peak_clears_ends=bool(cost[imax] > 0.15),
              all_scored=bool(all(d["n_scored"] >= 3 for d in s4["sweep"])))
    s4["separates"] = bool(s4["interior_peak"] and s4["ends_near_zero"]
                           and s4["peak_clears_ends"] and s4["all_scored"])
    res["S4_selection_cost"] = s4
    if not s4["separates"]:
        ok = False
    res["ok"] = ok
    return res


def main():
    import vn_gbundle as GB
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ladder = "--ladder" in sys.argv[1:]
    subs = args or ["coffee-bubbles"]
    os.makedirs(OUT, exist_ok=True)
    print("COMMISSIONING THE SIGNAL/NOISE DISCRIMINATOR (both directions)")
    c = commission()
    print("  S1 pure noise: %d scored + %d skipped = %d bands, max |r| %.4f, "
          "bands exceeding their own 4/sqrt(m) bar: %s"
          % (c["S1_pure_noise"]["n_scored"], c["S1_pure_noise"]["n_skipped"],
             c["S1_pure_noise"]["n_bands"], c["S1_pure_noise"]["max_abs"],
             c["S1_pure_noise"]["exceeding"] or "none"))
    print("  S2 known-answer sweep:")
    for s in c["S2_sweep"]:
        print("       signal fraction %.2f  r predicted %.4f  r measured "
              "%.4f  (%d scored + %d skipped = %d bands, median sub-gate "
              "fraction %.4f)"
              % (s["sig_frac"], s["r_pred"], s["r_med"], s["n_scored"],
                 s["n_skipped"], s["n_bands"], s["dead_frac_med"]))
    print("  S3 monotone %s, zero rung near zero %s"
          % (c["S3_monotone"]["monotone"],
             c["S3_monotone"]["zero_rung_near_zero"]))
    s4 = c["S4_selection_cost"]
    print("  S4 selection cost above the gate (control = plain mean, same "
          "pixels, weighting law is the only difference):")
    for d in s4["sweep"]:
        print("       signal fraction %.2f  r_mean %7.4f  r_merge %7.4f  "
              "sel_cost %+7.4f  (%d scored + %d skipped = %d bands)"
              % (d["sig_frac"], d["r_mean_med"], d["r_merge_med"],
                 d["sel_cost_med"], d["n_scored"], d["n_skipped"],
                 d["n_bands"]))
    print("       interior peak %s at signal fraction %.2f (cost %+.4f); "
          "ends %+.4f / %+.4f near zero %s; peak clears 0.15 %s -> "
          "separates %s"
          % (s4["interior_peak"], s4["argmax_sig_frac"], s4["peak"],
             s4["end_lo"], s4["end_hi"], s4["ends_near_zero"],
             s4["peak_clears_ends"], s4["separates"]))
    print("  commissioning ok: %s" % c["ok"])
    if not c["ok"]:
        print("\nREFUSED: discriminator failed commissioning; "
              "no measurement reported")
        return 1

    res = dict(commission=c, subjects={})
    for s in subs:
        rule = None
        if "@" in s:
            s, rule = s.split("@", 1)
        try:
            frames, kept, meta = GB.load(s, rule=rule)
        except (IOError, OSError) as e:
            print("\n%s NOT EXAMINED: %s" % (s, e))
            res["subjects"][s] = {"state": "NOT EXAMINED", "why": str(e)}
            continue
        key = s if rule is None else "%s@%s" % (s, rule)
        if ladder:
            from vn_dilute import make_rungs
            rungs = [v for _, v in sorted(make_rungs(len(frames)).items(),
                                          key=lambda kv: len(kv[1]))]
            print("\n%s LADDER: rule %s, index span %d..%d, rungs %s"
                  % (key, meta.get("admit_rule"), kept[0], kept[-1],
                     [len(r) for r in rungs]))
            # Every rung must span the SAME focus range, or the ladder
            # measures depth and frame count at once. Verified, not asserted.
            spans = [(kept[r[0]], kept[r[-1]]) for r in rungs]
            same = all(sp == spans[0] for sp in spans)
            print("   matched range across rungs: %s  %s"
                  % (same, spans if not same else spans[0]))
            lad = []
            for r in rungs:
                row2 = {}
                for sp in ("interleave", "pair"):
                    rows, m2 = subgate([frames[i] for i in r], split=sp)
                    row2[sp] = rows
                lad.append(dict(n=len(r), span=[int(kept[r[0]]),
                                                int(kept[r[-1]])],
                                rows=row2["interleave"],
                                rows_pair=row2["pair"]))
                for sp in ("interleave", "pair"):
                    print("   N=%-4d %-10s " % (len(r), sp)
                          + "  ".join("L%d %+0.3f" % (x["band"],
                                                      x["sel_cost"])
                                      for x in row2[sp]))
            res["subjects"][key] = dict(state="LADDER", matched_range=bool(
                same), spans=[[int(a), int(b)] for a, b in spans], rungs=lad)
            del frames
            continue
        rows, meta2 = subgate(list(frames))
        res["subjects"][key] = dict(state="MEASURED", rows=rows, **meta2)
        print("\n%s: N=%d (halves %d/%d), rule %s, index span %d..%d"
              % (key, len(frames), meta2["half_a"], meta2["half_b"],
                 meta.get("admit_rule"), kept[0], kept[-1]))
        print("   band  dead_frac   px_dead  r_subgate  SNR_subgate  "
              "  r_merge    r_mean  sel_cost")
        for x in rows:
            skip = ("" if x["scored"] else "  [SUBGATE SKIPPED px<%d]"
                    % MIN_PX)
            print("   L%-4d %9.4f %9d %10.4f %12.3f %9.4f %9.4f %9.4f%s"
                  % (x["band"], x["dead_frac"], x["px_dead"], x["r_subgate"],
                     x["snr_subgate"], x["r_merge"], x["r_mean"],
                     x["sel_cost"], skip))
        del frames
    p = os.path.join(OUT, "subgate-ladder.json" if ladder else "subgate.json")
    json.dump(res, io.open(p, "w", encoding="utf-8"), default=float)
    print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
