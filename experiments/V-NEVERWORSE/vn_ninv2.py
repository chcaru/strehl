"""N-invariance, re-measured after this lane found its own noise gauge wrong.

WHAT THIS REPLACES AND WHY
--------------------------
`vn_ninv.py` divided every arm's band power by a "noise twin" whose noise was
injected at `vn_pyr.fit_variance`'s level. That fit returns gain = 0 and a flat
sigma = 91.73 DN on coffee-bubbles; the measured value is 55.58 DN (paired fit)
against an independent model-free upper bound of 60.42 DN. The twin therefore
carried 2.72x too much noise VARIANCE, and every "noise-corrected" softening
number in section 9.17-9.22 of RESULT.md is contaminated by it.

The contamination was VISIBLE and was not looked at. Decomposing band power
into scene + noise gives a NEGATIVE scene term in 12 of 12 cells on
coffee-bubbles under the old gauge -- the twin's 0.30-0.35 noise reading 145%
to 345% of the TOTAL power in the real merge. Noise cannot exceed total. That
is the same degeneracy the tone lane caught in its own decomposition, and like
that lane's first version, this one printed a verdict over it.

So this file does three things the previous one did not:

1. Injects noise at a MEASURED level (`vn_noise.fit_variance_paired`), with the
   old level available as a sensitivity arm rather than as an assumption.
2. Computes scene = total - noise EXPLICITLY and REFUSES any cell where the
   result is not positive, instead of reporting a ratio built on it. Counts
   partition: cells = measured + refused.
3. Carries sharpness on the same pixels as every blotch number, as a
   noise-SUBTRACTED fine-band scene power, so an arm cannot buy a better mid
   band by blurring.

It also audits the argmax control that carried the previous report's central
refutation, because that control returns exactly 1.000 and a control returning
a round number has to be shown to be a prediction rather than a short circuit.
"""
import io
import json
import os
import sys

import numpy as np

import vn_pyr as VP
from vn_confexp import merge_confident
from vn_manuf import synth
from vn_noise import commission as noise_commission
from vn_noise import fit_variance_paired
from vn_plateau import BETA, SHIP, blotch
from vn_snrref import flatness, load, normalised

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\ninv2"
# NOTE ON WHAT THESE BANDS ARE IN PIXELS, because this lane got it wrong once.
# A frequency f cyc/px is a period of 1/f px, so 0.02-0.05 cyc/px is the
# 20-50 PX band -- the mid-scale mottle band the convictions live in, and the
# band `vn_plateau.blotch` measures at 50-400 px sits just coarser than it.
# `vn_ninv.spectrum` used exactly this band as its NORMALISING REFERENCE, i.e.
# it divided the fine-grain power by the defect under investigation, and that
# reference grew 113.6% from N=4 to N=19 on coffee-bubbles/shipping. Here it is
# a measured band like any other and nothing is divided by it.
MOTTLE = (0.02, 0.05)
MID = (0.30, 0.35)
FINE = (0.40, 0.45)
BANDS = (MOTTLE, (0.10, 0.15), (0.20, 0.25), MID, FINE)
ARMS = ("shipping", "confidence", "argmax", "mean")


def _hann2(h, w):
    return np.outer(np.hanning(h), np.hanning(w))


def band_power(img, bands=BANDS):
    """Un-normalised radial band power in DN^2.

    Deliberately NOT divided by a low-frequency reference. `vn_ninv.spectrum`
    normalised by 0.02-0.05 cyc/px as a defence against measuring exposure, and
    that reference turned out to be the least stable quantity in the
    measurement: on coffee-bubbles/shipping it GREW 113.6% from N=4 to N=19
    while the 0.30-0.35 band it was dividing grew 47.6%, so the reported
    "31% softer" was almost entirely the denominator moving. Exposure is
    handled here by subtracting a measured noise term instead, and by
    reporting the level so any residual gain is visible.
    """
    g = img[:, :, 1].astype(np.float64)
    g = g - g.mean()
    h, w = g.shape
    F = np.fft.rfft2(g * _hann2(h, w))
    p = F.real ** 2 + F.imag ** 2
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    rad = np.sqrt(fy ** 2 + fx ** 2)
    return {"%.2f-%.2f" % (lo, hi): float(p[(rad >= lo) & (rad < hi)].mean())
            for lo, hi in bands}


def pick(n, k):
    """Matched-range decimation: endpoints always retained."""
    return sorted(set(np.linspace(0, n - 1, k).round().astype(int).tolist()))


def arm_merge(name, sub, var0, nb=7):
    """One place produces both the image and the weights for every arm."""
    if name == "confidence":
        return merge_confident(sub, SHIP, BETA, var0, nb=nb,
                               kappa=0.01, p_lo=1.0)
    cfg = dict(SHIP)
    cfg["_clamp"] = {}
    if name in ("mean", "argmax"):
        cfg["mode"] = name
    rec, W = VP.merge(sub, cfg, BETA, var0, nb=nb)
    return rec, W


def detail_stats(frames, W, level=2):
    """n_eff and winner share at REAL DETAIL pixels, from the passed-in W."""
    fl, _ = flatness(frames)
    for _ in range(level):
        fl = VP.reduce_(fl)
    Wl = W[level]
    n = float(Wl.shape[0])
    nrm = normalised(Wl)
    s = nrm.sum(axis=0)
    neff = np.where(s > 0, 1.0 / np.maximum((nrm ** 2).sum(axis=0), 1e-30), n)
    top = np.where(s > 0, nrm.max(axis=0), 1.0 / n)
    d = fl[:neff.shape[0], :neff.shape[1]]
    m = d >= np.quantile(d, 0.9)
    return float(neff[m].mean()), float(top[m].mean()), int(m.sum())


def audit_argmax(W, level=2):
    """Prove the argmax control's 1.000 is a prediction, not a short circuit.

    Two measurements, neither of which reads a derived statistic:

    a) STRUCTURE. Count the non-zero entries per pixel in the weight stack the
       merge actually produced. Winner-take-all predicts exactly 1 wherever
       anything was admitted and 0 where nothing was; any other count refutes
       the construction.
    b) RESPONSIVENESS. Break the one-hot property by hand and confirm the
       reported share MOVES. A short circuit that returns 1.0 regardless is
       identical in appearance to a correct one until this is run.
    """
    Wl = W[level]
    nz = (Wl > 0).sum(axis=0)
    den = Wl.sum(axis=0)
    admitted = den > 0
    exactly_one = int((nz[admitted] == 1).sum())
    total_adm = int(admitted.sum())
    zero_where_abstained = int((nz[~admitted] == 0).sum())
    total_abs = int((~admitted).sum())

    hurt = Wl.copy().astype(np.float64)
    win = hurt.argmax(axis=0)
    second = (win + 1) % hurt.shape[0]
    np.put_along_axis(hurt, second[None], 0.25, axis=0)
    nrm0 = normalised(Wl)
    nrm1 = normalised(hurt)
    s0 = float(nrm0.max(axis=0)[admitted].mean()) if total_adm else float("nan")
    s1 = float(nrm1.max(axis=0)[admitted].mean()) if total_adm else float("nan")
    return dict(exactly_one=exactly_one, admitted=total_adm,
                zero_where_abstained=zero_where_abstained,
                abstained=total_abs, share_intact=s0, share_broken=s1,
                moved=abs(s0 - s1))


def twin_merge(syn_sub, var0, W, nb=7):
    """Push a noise-only stack through the weight field an arm actually chose.

    This is the noise the arm passes through, not the noise a differently
    weighted merge of the same frames would have produced.
    """
    cfg = dict(SHIP)
    cfg["_clamp"] = {}
    rec, _ = VP.merge(syn_sub, cfg, BETA, var0, nb=nb, fixedW=W)
    return rec


def commission_fixedw(frames, var0):
    """The fixedW path is new code, so it is commissioned like a statistic.

    IDENTITY is a real prediction: replaying an arm's own weights over its own
    frames must reproduce its own output bit for bit. RESPONSIVENESS is the
    test that makes IDENTITY meaningful -- if fixedW were quietly ignored, the
    identity check would pass just as cleanly, so a deliberately wrong weight
    field must change the answer.
    """
    ok, bad = [], []
    sub = frames[:5]
    rec, W = arm_merge("shipping", sub, var0)
    same = twin_merge(sub, var0, W)
    d0 = float(np.abs(same - rec).max())
    (ok if d0 < 1e-9 else bad).append(
        "IDENTITY: replaying an arm's own weights over its own frames "
        "reproduces it to %.3g DN (must be under 1e-9)" % d0)
    Wr = [w[::-1].copy() for w in W]
    other = twin_merge(sub, var0, Wr)
    d1 = float(np.abs(other - rec).max())
    (ok if d1 > 1e-6 else bad).append(
        "RESPONSIVENESS: reversing the frame order inside the weight stack "
        "changes the output by %.4g DN (must be non-zero, or fixedW is being "
        "ignored and IDENTITY proved nothing)" % d1)
    return ok, bad


def commission_decomp(frames, var0, seed=99):
    """Both directions, on the scene/noise DECOMPOSITION itself.

    The tests that matter here are invariance predictions, not monotone ones.
    Adding noise to the SOURCES raises what both the merge and its twin see, so
    the noise term must rise while the scene term stays put; a decomposition
    that cannot separate them fails that even though it would pass any
    "more noise reads higher" check. It is what caught the first version of the
    twin, which let the synthetic stack choose its own weights.
    """
    rng = np.random.default_rng(seed)
    ok, bad = [], []
    sub = frames[:6]

    def decomp(fs, v):
        base = np.mean(fs, axis=0)
        syn = synth(fs, v)
        rec, W = arm_merge("shipping", fs, v)
        nrec = twin_merge(syn, v, W)
        tot = band_power(rec)["%.2f-%.2f" % MID]
        noi = band_power(nrec - base)["%.2f-%.2f" % MID]
        return tot, noi, tot - noi

    t0, n0, s0 = decomp(sub, var0)
    (ok if s0 > 0 else bad).append(
        "NON-DEGENERATE: scene = total - noise = %.5g - %.5g = %.5g at "
        "0.30-0.35 (must be positive, or no ratio built on it is admissible)"
        % (t0, n0, s0))
    if s0 <= 0:
        return ok, bad

    # The stimulus is scaled to the subject's OWN measured sigma, not fixed in
    # DN. A flat 45 DN is a 1.66x variance bump on a 55.6 DN subject and a 4.6x
    # bump on a 23.6 DN one, so a fixed stimulus does not ask the two subjects
    # the same question -- it asks the quiet subject a much harder one, and
    # 112MSDCF failed at 45.1% on a bar coffee-bubbles cleared at 3.8%.
    #
    # Shrinking a stimulus until a subject passes is bar-shopping, so the gate
    # is only half of this test. The sweep below reports the separation error
    # at 0.5x, 1.0x and 2.0x the subject's sigma and PRINTS THE BREAKDOWN
    # POINT -- the multiple at which separation exceeds the bar -- whether or
    # not the gate passes. A limit that is published cannot be shopped for.
    sig0 = float(np.sqrt(np.maximum(var0, 0)).mean())
    sweep, brk = [], None
    for mult in (0.5, 1.0, 2.0):
        extra = mult * sig0
        noisier = [f + rng.normal(0.0, extra, f.shape) for f in sub]
        v2, _, _ = fit_variance_paired(noisier)
        t1, n1, s1 = decomp(noisier, v2)
        rel = abs(s1 - s0) / s0
        sweep.append((mult, extra, n1, s1, rel, n1 > n0))
        if brk is None and (rel >= 0.35 or n1 <= n0):
            brk = mult
    g = [s for s in sweep if abs(s[0] - 1.0) < 1e-9][0]
    (ok if g[5] and g[4] < 0.35 else bad).append(
        "UP, and SEPARATED: adding %.1f DN (1.0x this subject's own %.2f DN) "
        "to every SOURCE raises the noise term %.5g -> %.5g while the scene "
        "term moves %.5g -> %.5g (%.1f%%, must be under 35%% or the terms "
        "are not separated)"
        % (g[1], sig0, n0, g[2], s0, g[3], 100 * g[4]))
    ok.append(
        "SEPARATION BREAKDOWN (reported, not gated): scene error %s at "
        "%s x sigma; separation holds to %s"
        % (", ".join("%.1f%%" % (100 * s[4]) for s in sweep),
           "/".join("%.1f" % s[0] for s in sweep),
           "beyond 2.0x sigma, the largest stimulus tried" if brk is None
           else "under %.1fx sigma" % brk))

    sm = []
    for f in sub:
        a = f.copy()
        a[1:-1, 1:-1] = (f[:-2, 1:-1] + f[2:, 1:-1] + f[1:-1, :-2]
                         + f[1:-1, 2:] + f[1:-1, 1:-1]) / 5.0
        sm.append(a)
    v3, _, _ = fit_variance_paired(sm)
    t2, n2, s2 = decomp(sm, v3)
    (ok if s2 < s0 else bad).append(
        "DOWN: smoothing every source lowers the SCENE term %.5g -> %.5g "
        "(a planted improvement in noise must not read as more scene)"
        % (s0, s2))

    sharp = [f.astype(np.float64) for f in sub]
    for i, f in enumerate(sharp):
        lap, _ = VP.lap_pyr(f[:, :, 1], 1)
        sharp[i] = f.copy()
        sharp[i][:, :, 1] = f[:, :, 1] + 0.5 * lap[0]
    v4, _, _ = fit_variance_paired(sharp)
    t3, n3, s3 = decomp(sharp, v4)
    (ok if s3 > s0 else bad).append(
        "IMPROVEMENT: unsharp-masking every source raises the SCENE term "
        "%.5g -> %.5g (a planted gain in real structure must read as scene)"
        % (s0, s3))
    return ok, bad


def main():
    os.makedirs(OUT, exist_ok=True)
    subj = sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles"
    crop = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    frames = load(subj)
    if crop:
        h, w = frames[0].shape[:2]
        y0, x0 = (h - crop) // 2, (w - crop) // 2
        frames = [f[y0:y0 + crop, x0:x0 + crop] for f in frames]
    n = len(frames)
    print("%s: %d frames, window %dx%d"
          % (subj, n, frames[0].shape[0], frames[0].shape[1]))

    var_inc, r2i, gi = VP.fit_variance(frames[0][:, :, 1])
    var0, r2p, gp = fit_variance_paired(frames)
    si = float(np.sqrt(np.maximum(var_inc, 0)).mean())
    sp = float(np.sqrt(np.maximum(var0, 0)).mean())
    print("\nnoise gauge:")
    print("  incumbent single-frame fit  read2=%.5g gain=%.5g  sigma=%.3f DN"
          % (r2i, gi, si))
    print("  paired difference fit       read2=%.5g gain=%.5g  sigma=%.3f DN"
          % (r2p, gp, sp))
    print("  the incumbent over-states the noise VARIANCE by %.3fx" %
          ((si / max(sp, 1e-9)) ** 2))

    print("\ncommissioning the noise gauge (both directions + 2 accuracy):")
    base_all = np.mean(frames, axis=0)
    ok, bad = noise_commission(base_all, frames)
    for l in ok:
        print("  ok      " + l)
    for l in bad:
        print("  FAILED  " + l)
    if bad:
        raise SystemExit("REFUSED: the noise gauge is not commissioned")

    print("\ncommissioning the scene/noise decomposition (both directions):")
    okf, badf = commission_fixedw(frames, var0)
    for l in okf:
        print("  ok      " + l)
    for l in badf:
        print("  FAILED  " + l)
    ok2, bad2 = commission_decomp(frames, var0)
    for l in ok2:
        print("  ok      " + l)
    for l in bad2:
        print("  FAILED  " + l)
    if bad2 or badf:
        raise SystemExit("REFUSED: the decomposition is not commissioned")

    ks = sorted({n, max(2, n // 2), max(2, n // 4)}, reverse=True)
    syn_all = synth(frames, var0)
    rows, measured, refused = [], 0, 0
    mk, fk = "%.2f-%.2f" % MID, "%.2f-%.2f" % FINE
    ok_ = "%.2f-%.2f" % MOTTLE
    print("\n  %-11s %4s %11s %11s %11s %11s %11s %9s %7s %6s"
          % ("arm", "N", "SCENE 20-50", "NOISE 20-50", "SCENE mid",
             "SCENE fine", "noise mid", "blotch", "n_eff", "share"))
    audits = {}
    for name in ARMS:
        for k in ks:
            idx = pick(n, k)
            sub = [frames[i] for i in idx]
            rec, W = arm_merge(name, sub, var0)
            nrec = twin_merge([syn_all[i] for i in idx], var0, W)
            tot = band_power(rec)
            # Every syn_all[i] shares the SAME latent scene `base_all`, so any
            # convex merge of a subset of them returns base_all + sum w_i n_i
            # exactly. The reference must therefore be base_all and not the
            # subset mean. A first version subtracted np.mean(sub), which is a
            # DIFFERENT focus average, so the "noise" term at every rung below
            # full N carried a real scene difference: the mean arm's noise read
            # 2.09e8 against a total of 1.575e8 at N=4 and the cell was refused
            # as degenerate for a reason that was the harness, not the merge.
            noi = band_power(nrec - base_all)
            scene = {b: tot[b] - noi[b] for b in tot}
            ne, tp, npx = detail_stats(sub, W)
            deg = scene[mk] <= 0 or scene[fk] <= 0
            if deg:
                refused += 1
            else:
                measured += 1
            if name == "argmax" and k == ks[0]:
                audits["argmax"] = audit_argmax(W)
            rows.append(dict(
                arm=name, N=k, first=idx[0], last=idx[-1],
                total_mid=tot[mk], noise_mid=noi[mk], scene_mid=scene[mk],
                total_fine=tot[fk], noise_fine=noi[fk], scene_fine=scene[fk],
                total_mot=tot[ok_], noise_mot=noi[ok_], scene_mot=scene[ok_],
                blotch=float(blotch(rec)[0]), neff=ne, share=tp, detail_px=npx,
                level=float(rec[:, :, 1].mean()), degenerate=bool(deg),
                mottle_degenerate=bool(scene[ok_] <= 0)))
            print("  %-11s %4d %11.4g %11.4g %11.4g %11.4g %11.4g %9.5f %7.2f "
                  "%6.3f%s"
                  % (name, k, scene[ok_], noi[ok_], scene[mk], scene[fk],
                     noi[mk], rows[-1]["blotch"], ne, tp,
                     "  REFUSED" if deg else ""))
    print("\n  cells: %d examined = %d measured + %d refused"
          % (len(rows), measured, refused))

    a = audits.get("argmax")
    if a:
        print("\n  ARGMAX CONTROL AUDIT -- is the 1.000 a prediction or a "
              "short circuit?")
        print("    structure:  %d of %d admitted pixels carry exactly one "
              "non-zero weight; %d of %d abstaining pixels carry none"
              % (a["exactly_one"], a["admitted"],
                 a["zero_where_abstained"], a["abstained"]))
        print("    responsiveness: share %.6f intact -> %.6f after a second "
              "frame is forced in (moved %.6f, must be non-zero)"
              % (a["share_intact"], a["share_broken"], a["moved"]))
        if a["moved"] < 1e-6:
            raise SystemExit(
                "REFUSED: the argmax share does not respond to a broken "
                "one-hot weight stack, so 1.000 is not a measurement")

    print("\n  N-INVARIANCE on the SCENE term, deepest against half depth:")
    print("  %-11s %-12s %10s %10s %10s %10s %10s"
          % ("arm", "rungs", "scene mid", "scene fine", "noise mid",
             "NOISE20-50", "blotch"))
    verdict = {}
    for name in ARMS:
        hi = [r for r in rows if r["arm"] == name and r["N"] == ks[0]][0]
        lo = [r for r in rows if r["arm"] == name and r["N"] == ks[1]][0]
        assert hi["first"] == lo["first"] and hi["last"] == lo["last"]
        if hi["degenerate"] or lo["degenerate"]:
            print("  %-11s %-12s %10s" % (name, "%d<-%d" % (ks[0], ks[1]),
                                          "REFUSED"))
            verdict[name] = dict(refused=True)
            continue
        v = dict(refused=False,
                 scene_mid=hi["scene_mid"] / lo["scene_mid"],
                 scene_fine=hi["scene_fine"] / lo["scene_fine"],
                 noise_mid=hi["noise_mid"] / lo["noise_mid"],
                 scene_mot=hi["scene_mot"] / lo["scene_mot"],
                 noise_mot=hi["noise_mot"] / lo["noise_mot"],
                 blotch=hi["blotch"] / max(lo["blotch"], 1e-30),
                 share_hi=hi["share"], share_lo=lo["share"],
                 N_hi=ks[0], N_lo=ks[1])
        verdict[name] = v
        print("  %-11s %-12s %10.4f %10.4f %10.4f %10.4f %10.4f"
              % (name, "%d<-%d" % (ks[0], ks[1]), v["scene_mid"],
                 v["scene_fine"], v["noise_mid"], v["noise_mot"],
                 v["blotch"]))

    am, mn = verdict.get("argmax"), verdict.get("mean")
    if am and mn and not am["refused"] and not mn["refused"]:
        print("\n  ORCH's CAUSE, re-tested on the corrected gauge:")
        print("    argmax share %.3f -> %.3f (no dilution by construction), "
              "scene mid ratio %.4f" % (am["share_lo"], am["share_hi"],
                                        am["scene_mid"]))
        print("    mean   share %.3f -> %.3f (maximal dilution), "
              "scene mid ratio %.4f" % (mn["share_lo"], mn["share_hi"],
                                        mn["scene_mid"]))

    with io.open(os.path.join(OUT, "%s.json" % subj), "w",
                 encoding="utf-8") as f:
        json.dump(dict(subject=subj, n=n, crop=crop, ks=ks, rows=rows,
                       verdict=verdict, audit=audits,
                       commission=dict(noise=ok, decomp=okf + ok2),
                       noise=dict(incumbent_sigma=si, paired_sigma=sp,
                                  incumbent_read2=r2i, incumbent_gain=gi,
                                  paired_read2=r2p, paired_gain=gp),
                       counts=dict(examined=len(rows), measured=measured,
                                   refused=refused)),
                  f, indent=1)
    print("\nwrote %s" % os.path.join(OUT, "%s.json" % subj))
    return 0


if __name__ == "__main__":
    sys.exit(main())
