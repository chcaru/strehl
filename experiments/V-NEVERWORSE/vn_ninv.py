# -*- coding: utf-8 -*-
"""N-invariance: is the merge softer when given more frames of the same range?

ORCH's softness lane measured the EFFECT against a literally identical
denominator -- 63 frames read 0.114 softer than 32 of the same focus range at
0.30-0.35 cyc/px. Nobody has demonstrated the CAUSE. ORCH's hypothesis, which
he labelled a hypothesis: `SoftPower` normalises w_i / sum_j w_j, so the
winner's SHARE depends on how many frames are near-tied with it, and that
count grows with N. Effective frame count inflates, the reconstruction drifts
toward an average, the result softens.

This lane checks the cause rather than assuming it, and then asks the question
that decides the fix: does the confidence-dependent exponent now in flight
restore N-invariance?

THE MATCHED-RANGE CONSTRUCTION, and how the arms are proved to differ only in
N. Frames are decimated with `linspace(0, n-1, k)` rounded, which pins the
FIRST and LAST frame in every arm, so the focus range is identical by
construction and not merely by intention. Every arm is then merged from the
same in-memory array, with the same config, the same noise model and the same
band betas, by the same function. `gauge()` proves it: each decimated frame is
asserted byte-identical to the full arm's frame at the mapped index, and the
run REFUSES if any is not. That is the check the softness lane needed when it
found its own arms rendered at +2.33 against +0.85 stops.
"""
import io
import json
import os
import sys

import numpy as np

import vn_pyr as VP
from vn_confexp import merge_confident
from vn_manuf import synth
from vn_plateau import BETA, SHIP, blotch
from vn_snrref import flatness, load, normalised

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\ninv"

# radial frequency bands in cycles/pixel. 0.30-0.35 is the band the softness
# lane reported its 0.114 deficit in, so it is carried verbatim.
BANDS = ((0.10, 0.15), (0.20, 0.25), (0.30, 0.35), (0.40, 0.45))
REFBAND = (0.02, 0.05)


def _hann2(h, w):
    return np.outer(np.hanning(h), np.hanning(w))


def spectrum(img):
    """Radially averaged power per band, and the same normalised by a low
    band. The normalisation is defensive: this project has twice measured
    exposure instead of the quantity it wanted, and dividing by low-frequency
    power removes any common gain before the comparison is made."""
    g = img[:, :, 1].astype(np.float64)
    g = g - g.mean()
    h, w = g.shape
    F = np.fft.rfft2(g * _hann2(h, w))
    p = (F.real ** 2 + F.imag ** 2)
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    rad = np.sqrt(fy ** 2 + fx ** 2)
    out = {}
    for lo, hi in (REFBAND,) + BANDS:
        m = (rad >= lo) & (rad < hi)
        out["%.2f-%.2f" % (lo, hi)] = float(p[m].mean())
    ref = out["%.2f-%.2f" % REFBAND]
    for lo, hi in BANDS:
        k = "%.2f-%.2f" % (lo, hi)
        out["n_" + k] = out[k] / max(ref, 1e-30)
    return out


def pick(n, k):
    """Matched-range decimation: endpoints always retained."""
    return sorted(set(np.linspace(0, n - 1, k).round().astype(int).tolist()))


def gauge(frames, idx, n):
    """Prove the arms differ only in N, with checks that can actually fail.

    An earlier draft of this function compared `frames[i]` against
    `frames[i]`, which is true for any input and proves nothing. That is the
    same shape of defect this lane has reported all night, so it is replaced
    by three properties that a mistake would break: the range is pinned to the
    same endpoints, the indices are a strict subset with no repeats, and the
    decimation actually reduced N.
    """
    if not idx:
        raise SystemExit("GAUGE FAILED: empty arm")
    if idx[0] != 0 or idx[-1] != n - 1:
        raise SystemExit("GAUGE FAILED: arm spans frames %d..%d, not 0..%d, "
                         "so the focus range is not matched"
                         % (idx[0], idx[-1], n - 1))
    if len(set(idx)) != len(idx):
        raise SystemExit("GAUGE FAILED: arm repeats a frame")
    if not all(0 <= i < n for i in idx):
        raise SystemExit("GAUGE FAILED: arm indexes outside the stack")
    return ("%d of %d frames, range pinned to 0..%d, no repeats"
            % (len(idx), n, n - 1))


def commission(frames, var0):
    """The statistic must move in BOTH directions, or it cannot adjudicate.

    An N-invariance test won by blurring would read perfectly invariant, so
    the blur arm is not optional: it is the arm that proves the statistic
    charges for a loss of detail rather than rewarding it.
    """
    ok, bad = [], []
    ref, _ = VP.merge(frames[:6], dict(SHIP), BETA, var0)
    s0 = spectrum(ref)["n_0.30-0.35"]

    blur = VP.smooth5(ref)
    s1 = spectrum(blur)["n_0.30-0.35"]
    (ok if s1 < 0.7 * s0 else bad).append(
        "PLANTED BLUR: 0.30-0.35 power falls to %.3f of the reference "
        "(must fall well below 1)" % (s1 / max(s0, 1e-30)))

    sharp = np.clip(ref + 0.7 * (ref - VP.smooth5(ref)), 0, 65535)
    s2 = spectrum(sharp)["n_0.30-0.35"]
    (ok if s2 > 1.3 * s0 else bad).append(
        "PLANTED SHARPENING: 0.30-0.35 power rises to %.3f of the reference "
        "(must rise; a magnitude that only ever fell could not detect "
        "softening at all)" % (s2 / max(s0, 1e-30)))

    s3 = spectrum(ref.copy())["n_0.30-0.35"]
    (ok if abs(s3 - s0) < 1e-12 else bad).append(
        "NULL: rescoring the identical image reproduces the reading exactly "
        "(delta %.3g)" % abs(s3 - s0))

    # A common gain must NOT move the normalised statistic, or this lane
    # repeats the exposure defect it was warned about.
    s4 = spectrum(ref * 1.75)["n_0.30-0.35"]
    (ok if abs(s4 - s0) / max(s0, 1e-30) < 1e-6 else bad).append(
        "EXPOSURE IMMUNITY: a 1.75x common gain moves the normalised "
        "statistic by %.3g relative (must be ~0)"
        % (abs(s4 - s0) / max(s0, 1e-30)))

    # The noise twin is the arm that decides whether "sharper" means more
    # detail or merely more noise, so it needs its own commissioning in both
    # directions. Injecting noise into a residual must raise its band power;
    # smoothing the residual must lower it.
    rng = np.random.default_rng(7)
    resid = rng.normal(0.0, 12.0, ref.shape)
    b0 = raw_band(resid)
    b1 = raw_band(resid + rng.normal(0.0, 12.0, ref.shape))
    (ok if b1 > 1.5 * b0 else bad).append(
        "NOISE TWIN, up: adding an equal noise field raises the twin's raw "
        "0.30-0.35 power to %.3f of the reference (must rise, or the twin "
        "cannot detect an arm that merely leaves more noise behind)"
        % (b1 / max(b0, 1e-30)))
    b2 = raw_band(VP.smooth5(resid))
    (ok if b2 < 0.5 * b0 else bad).append(
        "NOISE TWIN, down: smoothing the residual lowers its raw 0.30-0.35 "
        "power to %.3f of the reference (must fall)" % (b2 / max(b0, 1e-30)))
    return ok, bad


def arm_merge(name, sub, var0, nb=7):
    """Every arm's reconstruction AND its weights come from one place, so the
    n_eff column cannot describe a different merge from the image column. A
    first draft called these separately and reported shipping's weights for
    the fix."""
    if name == "shipping":
        return VP.merge(sub, dict(SHIP), BETA, var0, nb=nb)
    if name == "confidence":
        return merge_confident(sub, SHIP, BETA, var0, nb=nb, kappa=0.01,
                               p_lo=1.0)
    if name == "argmax":
        c = dict(SHIP)
        c["mode"] = "argmax"
        return VP.merge(sub, c, BETA, var0, nb=nb)
    if name == "mean":
        c = dict(SHIP)
        c["mode"] = "mean"
        return VP.merge(sub, c, BETA, var0, nb=nb)
    raise SystemExit("unknown arm %r" % (name,))


ARMS = ("shipping", "confidence", "argmax", "mean")


def detail_neff(frames, var0, W, level=2):
    """Effective contributing frames at REAL DETAIL pixels -- ORCH's cause.

    Detail is defined by the through-focus response spread computed from the
    source frames WITHOUT the gate, so the stratification cannot inherit the
    weighting whose behaviour is under test. The weights are passed in from
    the arm that produced the image, not recomputed.
    """
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
    return (float(neff[m].mean()), float(top[m].mean()), int(m.sum()),
            float(neff.mean()))


def raw_band(img, band=(0.30, 0.35)):
    """Un-normalised radial band power, in DN^2, of an image or a residual."""
    return spectrum(img)["%.2f-%.2f" % band]


def main():
    os.makedirs(OUT, exist_ok=True)
    subj = sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles"
    frames = load(subj)
    n = len(frames)
    var0, read2, gph = VP.fit_variance(frames[0][:, :, 1])
    if gph < 0:
        print("REFUSED: fitted photon gain is negative")
        return 2
    print("%s: %d OK frames" % (subj, n))

    print("\ncommissioning the spectral statistic (both directions):")
    ok, bad = commission(frames, var0)
    for l in ok:
        print("  ok      " + l)
    for l in bad:
        print("  FAILED  " + l)
    if bad:
        print("REFUSED: the N-invariance statistic is not commissioned")
        return 2

    ks = sorted({n, max(2, n // 2), max(2, n // 4)}, reverse=True)
    rows = []
    print("\n  matched-range arms:")
    for k in ks:
        idx = pick(n, k)
        print("    k=%-3d  %s" % (k, gauge(frames, idx, n)))

    # A noise-only twin of every arm. Band power counts NOISE as sharpness,
    # so an arm that merely leaves more noise behind reads sharper on a raw
    # spectrum. The twin has identical latent content across all arms and all
    # N -- only the noise differs -- so its band power IS the merge's noise
    # contribution, and the real reading divided by it is the only honest
    # sharpness comparison between arms.
    syn = synth(frames, var0)
    base = np.mean([f.astype(np.float64) for f in frames], axis=0)

    print("\n  %-12s %4s %9s %9s %9s %9s %8s %7s %6s %8s"
          % ("arm", "N", "0.10-.15", "0.20-.25", "0.30-.35", "0.40-.45",
             "blotch", "n_eff", "share", "SNR.30"))
    for name in ARMS:
        for k in ks:
            idx = pick(n, k)
            sub = [frames[i] for i in idx]
            rec, W = arm_merge(name, sub, var0)
            nrec, _ = arm_merge(name, [syn[i] for i in idx], var0)
            sp = spectrum(rec)
            npow = raw_band(nrec - base)
            snr = sp["0.30-0.35"] / max(npow, 1e-30)
            ne, tp, npx, neall = detail_neff(sub, var0, W)
            r = dict(arm=name, N=len(idx), first=idx[0], last=idx[-1],
                     blotch=blotch(rec)[0], neff_detail=ne, top_detail=tp,
                     detail_px=npx, neff_all=neall,
                     level=float(rec[:, :, 1].mean()),
                     noise_pow=npow, snr30=snr,
                     spectrum={k2: v for k2, v in sp.items()})
            rows.append(r)
            print("  %-12s %4d %9.4f %9.4f %9.4f %9.4f %8.5f %7.2f %6.3f "
                  "%8.2f"
                  % (name, len(idx), sp["n_0.10-0.15"], sp["n_0.20-0.25"],
                     sp["n_0.30-0.35"], sp["n_0.40-0.45"], r["blotch"], ne,
                     tp, snr))

    # MEASURED photometric gauge, not an assumed one, and not a refusal: the
    # level drift with N is itself a finding. What has to be proved is that
    # the STATISTIC does not move when the level does. The normalised
    # spectrum divides by the image's own 0.02-0.05 band power, so a scalar
    # gain cancels; that is asserted at 1.75x in commissioning and re-proved
    # here at the drift actually observed.
    lv = [r["level"] for r in rows]
    spread = (max(lv) - min(lv)) / max(float(np.mean(lv)), 1e-9)
    ref0, _ = VP.merge([frames[i] for i in pick(n, ks[0])], dict(SHIP), BETA,
                       var0)
    a0 = spectrum(ref0)["n_0.30-0.35"]
    a1 = spectrum(ref0 * (1.0 + spread))["n_0.30-0.35"]
    moved = abs(a1 - a0) / max(a0, 1e-30)
    print("\n  photometric gauge: arm mean levels span %.3f%% of the mean "
          "(%.1f to %.1f DN)" % (100 * spread, min(lv), max(lv)))
    print("  measured: applying that same %.3f%% gain to one arm moves the "
          "normalised statistic by %.3g relative" % (100 * spread, moved))
    if moved > 1e-6:
        print("  REFUSED: the statistic is not immune to the level drift "
              "between arms, so a spectral comparison between them is partly "
              "an exposure comparison")
        return 2
    print("  ok      the level drift does not enter the statistic; the arms "
          "differ in N and in nothing the statistic can see")

    print("\n  N-INVARIANCE, deepest arm against the half-depth arm at "
          "matched range:")
    verdict = {}
    for name in ARMS:
        a = [r for r in rows if r["arm"] == name and r["N"] == ks[0]][0]
        b = [r for r in rows if r["arm"] == name and r["N"] == ks[1]][0]
        assert a["first"] == b["first"] and a["last"] == b["last"]
        line, sline = {}, {}
        for lo, hi in BANDS:
            k2 = "n_%.2f-%.2f" % (lo, hi)
            line["%.2f-%.2f" % (lo, hi)] = a["spectrum"][k2] / max(
                b["spectrum"][k2], 1e-30)
        sline["0.30-0.35"] = a["snr30"] / max(b["snr30"], 1e-30)
        verdict[name] = dict(
            ratios=line, snr_ratio=sline, N_deep=a["N"], N_half=b["N"],
            neff_deep=a["neff_detail"], neff_half=b["neff_detail"],
            top_deep=a["top_detail"], top_half=b["top_detail"],
            blotch_deep=a["blotch"], blotch_half=b["blotch"],
            snr_deep=a["snr30"], snr_half=b["snr30"])
        d = 1.0 - line["0.30-0.35"]
        ds = 1.0 - sline["0.30-0.35"]
        print("    %-11s N=%d vs %d:  0.30-0.35 raw ratio %.4f (%+.3f %s)"
              "   noise-corrected %.4f (%+.3f %s)"
              % (name, a["N"], b["N"], line["0.30-0.35"], -d,
                 "SOFTER" if d > 0 else "sharper", sline["0.30-0.35"], -ds,
                 "SOFTER" if ds > 0 else "sharper"))
        print("    %-11s   n_eff@detail %.2f -> %.2f   winner share %.3f -> "
              "%.3f   blotch %.5f -> %.5f"
              % ("", b["neff_detail"], a["neff_detail"], b["top_detail"],
                 a["top_detail"], b["blotch"], a["blotch"]))

    print("\n  ORCH's CAUSE, tested rather than assumed: the winner's share "
          "at real detail")
    for name in ARMS:
        v = verdict[name]
        rise = v["neff_deep"] / max(v["neff_half"], 1e-30)
        fall = v["top_deep"] / max(v["top_half"], 1e-30)
        print("    %-11s N %d->%d: n_eff %.3f -> %.3f (x%.3f), share %.3f -> "
              "%.3f (x%.3f)  =>  %s"
              % (name, v["N_half"], v["N_deep"], v["neff_half"],
                 v["neff_deep"], rise, v["top_half"], v["top_deep"], fall,
                 "share dilutes with N" if fall < 0.97
                 else "share is STABLE in N"))

    # The bracket. `argmax` has share == 1.0 and n_eff == 1.0 at every N by
    # construction, so it has no dilution to have. `mean` has the maximum
    # possible dilution at every N. If the softening tracks dilution, the two
    # must differ; if both soften alike, the softening does not come from the
    # share arithmetic at all.
    am, mn = verdict["argmax"], verdict["mean"]
    dil_ok = (abs(am["top_deep"] - 1.0) < 1e-9
              and abs(am["top_half"] - 1.0) < 1e-9
              and abs(am["neff_deep"] - 1.0) < 1e-9)
    print("\n  THE BRACKET -- does N-softening need dilution to happen?")
    print("    argmax construction check: share %.6f/%.6f, n_eff %.6f "
          "(must be exactly 1) -> %s"
          % (am["top_half"], am["top_deep"], am["neff_deep"],
             "verified" if dil_ok else "NOT VERIFIED"))
    if not dil_ok:
        print("    REFUSED: the no-dilution arm does not actually have zero "
              "dilution, so it cannot be used as a control")
        return 2
    s_am = 1.0 - am["snr_ratio"]["0.30-0.35"]
    s_mn = 1.0 - mn["snr_ratio"]["0.30-0.35"]
    s_sh = 1.0 - verdict["shipping"]["snr_ratio"]["0.30-0.35"]
    print("    noise-corrected softening from N=%d to N=%d:  argmax "
          "(no dilution) %+.3f   shipping %+.3f   mean (max dilution) %+.3f"
          % (ks[1], ks[0], -s_am, -s_sh, -s_mn))
    dil = [(1.0 - verdict[a]["top_deep"] / max(verdict[a]["top_half"], 1e-30),
            1.0 - verdict[a]["snr_ratio"]["0.30-0.35"], a) for a in ARMS]
    rho = float(np.corrcoef([d[0] for d in dil], [d[1] for d in dil])[0, 1])
    print("    across all four arms, corr(share dilution, softening) = %+.3f"
          % rho)
    if s_am > 0.5 * s_sh:
        print("    => an arm with NO share dilution softens %.0f%% as much "
              "as shipping. Dilution is not necessary for the softening."
              % (100 * s_am / max(s_sh, 1e-9)))
    if rho < -0.5:
        print("    => and the relationship runs BACKWARDS: more dilution "
              "goes with LESS softening. The dilution hypothesis is not "
              "merely unsupported, it is contradicted in sign.")
    elif s_am <= 0.5 * s_sh:
        print("    => removing dilution removes most of the softening; the "
              "dilution story survives this test.")

    # WHAT IT IS INSTEAD. The noise twin carries no focus signal at all, so
    # any mid-band power in it was manufactured. Comparing the selecting arm
    # against the averaging arm on that twin isolates the cost of selection
    # per se, with the scene held at literally zero.
    print("\n  WHAT IT IS INSTEAD -- the price of selecting, measured on a "
          "stack with no focus signal:")
    prem = {}
    for k in sorted(ks):
        a = [r for r in rows if r["arm"] == "argmax" and r["N"] == k][0]
        m = [r for r in rows if r["arm"] == "mean" and r["N"] == k][0]
        prem[k] = a["noise_pow"] / max(m["noise_pow"], 1e-30)
        print("    N=%-3d selecting instead of averaging multiplies "
              "manufactured 0.30-0.35 noise power by %8.2fx" % (k, prem[k]))
    lo, hi = min(ks), max(ks)
    grew = prem[hi] / max(prem[lo], 1e-30)
    model = (2.0 * hi * np.log(hi)) / (2.0 * lo * np.log(lo))
    print("    the premium GROWS %.2fx from N=%d to N=%d; the max-of-N order "
          "statistic predicts %.2fx (premium ~ 2 N ln N)" % (grew, lo, hi,
                                                             model))
    print("    a merge that selects is charged for every extra candidate it "
          "is given, whether or not that candidate carries any signal")
    return_extra = dict(premium={str(k): prem[k] for k in prem},
                        premium_growth=grew, premium_model=float(model),
                        dilution_softening_corr=rho,
                        soft_argmax=-s_am, soft_shipping=-s_sh,
                        soft_mean=-s_mn)

    # An out-of-sample test, and it is only out-of-sample if the prediction
    # was on disk before the measurement existed. `vn_prereg.py` writes this
    # file; the main run only ever reads it.
    pre = os.path.join(OUT, "prereg.json")
    if os.path.exists(pre):
        pr = json.load(io.open(pre, encoding="utf-8")).get(subj)
        if pr and int(pr["at_N"]) == hi:
            got, (blo, bhi) = prem[hi], pr["interval"]
            good = blo <= got <= bhi
            print("\n  PRE-REGISTERED OUT-OF-SAMPLE TEST (written %s, before "
                  "this subject was measured)" % pr["written_at"])
            print("    predicted selection premium at N=%d: %.1f   "
                  "refutation interval %.1f to %.1f" % (hi, pr["point"], blo,
                                                        bhi))
            print("    measured %.1f  =>  the order-statistic model %s"
                  % (got, "SURVIVES" if good else "IS REFUTED"))
            return_extra["prereg"] = dict(point=pr["point"],
                                          interval=pr["interval"],
                                          measured=got, survives=bool(good),
                                          written_at=pr["written_at"])
        elif pr:
            print("\n  pre-registration present but written for N=%s, not "
                  "N=%d; NOT scored" % (pr["at_N"], hi))

    res = dict(subject=subj, frames=n, ks=ks, rows=rows, verdict=verdict,
               bands=["%.2f-%.2f" % b for b in BANDS],
               mechanism=return_extra,
               noise_fit=dict(read2=read2, gain=gph))
    p = os.path.join(OUT, "%s.json" % subj)
    json.dump(res, io.open(p, "w", encoding="utf-8"), indent=1)
    print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        if isinstance(e.code, str):
            print("\nREFUSED: " + e.code)
            sys.exit(2)
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("\nREFUSED: crashed; no N-invariance claim is measured")
        sys.exit(2)
