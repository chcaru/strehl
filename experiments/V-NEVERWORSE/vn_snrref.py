# -*- coding: utf-8 -*-
"""ORCH asks 1 and 2, measured rather than argued.

ASK 1  Does SNR_REF = 64.0 cancel in the normalised weight w_i / sum_j w_j?
       ORCH believes it does, making it an overflow guard and not a threshold.
       The pinned source says both halves of the answer, so this measures which
       one is operative on real data: the merge is run at several SNR_REF values
       and the outputs are compared exactly.

ASK 2  In a FLAT region of a convicted subject, is the per-band weight
       concentrated on a single frame per pixel, and is that choice spatially
       incoherent? Flatness is computed from the source frames WITHOUT the gate,
       so it cannot inherit the gate's own decisions.

Commissioned in both directions before either is reported.
"""
import io
import json
import os
import sys

import numpy as np
from scipy import ndimage

import vn_pyr as VP
from vn_plateau import BETA, SHIP, blotch, sharpness

BUNDLE = r"C:\dev\strehl-out\V-NEVERWORSE\bundle"
OUT = r"C:\dev\strehl-out\V-NEVERWORSE\snrref"


def load(subj):
    z = np.load(os.path.join(BUNDLE, "%s.npz" % subj))
    meta = json.load(io.open(os.path.join(BUNDLE, "%s.json" % subj),
                             encoding="utf-8"))
    ok = {r["frame"] for r in meta["rows"] if r["state"] == "OK"}
    keys = [k for k in sorted(z.files)
            if k.startswith("b") and k != "bw" and int(k[1:]) in ok]
    return [z[k].astype(np.float64) for k in keys]


# --------------------------------------------------------------------------
# ASK 1
# --------------------------------------------------------------------------
def snrref_arm(frames, var0, ref, nb=7):
    """Run the shipping merge with SNR_REF forced to `ref`."""
    old = VP.SNR_REF
    VP.SNR_REF = float(ref)
    try:
        cfg = dict(SHIP)
        cfg["_clamp"] = {}
        rec, W = VP.merge(frames, cfg, BETA, var0, nb=nb)
        return rec, W, cfg["_clamp"]
    finally:
        VP.SNR_REF = old


def normalised(W):
    """The quantity ORCH asked about: w_i / sum_j w_j, per pixel."""
    den = W.sum(axis=0)
    return np.where(den > 0.0, W / np.maximum(den, 1e-300), 0.0)


def ask1(frames, var0, nb=7):
    rows = []
    base = None
    for ref in (64.0, 1.0, 4096.0):
        rec, W, cl = snrref_arm(frames, var0, ref, nb)
        nrm = [normalised(w) for w in W]
        bind = 0.0
        if cl.get("total"):
            bind = cl["binding"] / float(cl["total"])
        if base is None:
            base = (rec, nrm)
            dmax = wmax = 0.0
        else:
            dmax = float(np.abs(rec - base[0]).max())
            wmax = max(float(np.abs(a - b).max())
                       for a, b in zip(nrm, base[1]))
        rows.append(dict(snr_ref=ref, clamp_binding_frac=bind,
                         max_abs_pixel_delta=dmax,
                         max_abs_normalised_weight_delta=wmax))
        print("  SNR_REF %8.1f  clamp binds %.6f of coeffs  "
              "max |dpixel| %.3e  max |dw_norm| %.3e"
              % (ref, bind, dmax, wmax))
    return rows


def ask1_commission(frames, var0, nb=7):
    """A cancellation claim needs a POSITIVE control: force the clamp to bind
    and require the same comparison to come apart. Otherwise 'identical' is
    indistinguishable from a comparison that cannot see a difference."""
    ok, bad = [], []
    old, oldclip = VP.SNR_REF, VP._CLAMP
    try:
        # Arm P: shrink the clamp bound so it binds hard. SNR_REF must then
        # STOP cancelling, because the clamp is what breaks the algebra.
        VP._CLAMP = 1.0
        r1, _, c1 = snrref_arm(frames, var0, 64.0, nb)
        r2, _, _ = snrref_arm(frames, var0, 1.0, nb)
        d = float(np.abs(r1 - r2).max())
        (ok if d > 0 else bad).append(
            "POSITIVE CONTROL: with the clamp forced to bind (bound 1.0, "
            "binding %.3f of coeffs), SNR_REF stops cancelling: "
            "max |dpixel| %.4g" % (c1.get("binding", 0)
                                   / max(c1.get("total", 1), 1), d))
        # Arm N: the comparison must report exactly ZERO for a genuine no-op.
        VP._CLAMP = oldclip
        r4, _, _ = snrref_arm(frames, var0, 64.0, nb)
        r5, _, _ = snrref_arm(frames, var0, 64.0, nb)
        d0 = float(np.abs(r4 - r5).max())
        (ok if d0 == 0.0 else bad).append(
            "NULL CONTROL: rerunning the same SNR_REF gives max |dpixel| "
            "%.4g (must be exactly 0)" % d0)
    finally:
        VP.SNR_REF, VP._CLAMP = old, oldclip
    return ok, bad


# --------------------------------------------------------------------------
# ASK 2
# --------------------------------------------------------------------------
def flatness(frames):
    """Through-focus flatness per pixel, computed WITHOUT the gate.

    For each frame take a local high-frequency energy (the same 5-tap
    Laplacian band the merge selects on, but at full resolution), then measure
    how much that response VARIES across the stack relative to its own level.
    A pixel whose response is the same in every frame has nothing to select on.
    """
    e = np.stack([VP.smooth5((f[:, :, 1].astype(np.float64)
                              - VP.smooth5(f[:, :, 1].astype(np.float64))) ** 2)
                  for f in frames])
    mx, mn = e.max(axis=0), e.min(axis=0)
    return (mx - mn) / np.maximum(mx, 1e-12), e


def spatial_coherence(winner, n, valid=None):
    """Fraction of 4-neighbour pairs choosing the SAME frame, minus the value
    expected if the choice were independent per pixel. Positive means the
    winner field is more contiguous than chance; ~0 means incoherent.

    `valid` marks pixels where at least one frame was actually admitted.
    Where no frame clears the gate every weight is 0 and `argmax` returns
    frame 0 by convention, not by selection -- counting those as agreement
    manufactures coherence out of an abstention. My first run of this
    statistic omitted the mask and the pure-noise null read 0.60 agreement
    for that reason alone.
    """
    if valid is None:
        valid = np.ones(winner.shape, dtype=bool)
    same = 0.0
    tot = 0.0
    for (a, b), (va, vb) in (
            ((winner[1:, :], winner[:-1, :]), (valid[1:, :], valid[:-1, :])),
            ((winner[:, 1:], winner[:, :-1]), (valid[:, 1:], valid[:, :-1]))):
        m = va & vb
        same += float(np.count_nonzero((a == b) & m))
        tot += float(np.count_nonzero(m))
    if tot == 0.0:
        return None, None, 0.0
    obs = same / tot
    # chance level from the observed marginal frequencies, not from 1/n
    cnt = np.bincount(winner[valid].ravel(), minlength=n).astype(np.float64)
    p = cnt / max(cnt.sum(), 1.0)
    return obs, float((p ** 2).sum()), float(valid.mean())


def ask2(frames, var0, nb=7, level=3):
    flat, _ = flatness(frames)
    fl = flat
    for _ in range(level):
        fl = VP.reduce_(fl)
    cfg = dict(SHIP)
    rec, W = VP.merge(frames, cfg, BETA, var0, nb=nb)
    Wl = W[level]
    n = Wl.shape[0]
    nrm = normalised(Wl)
    neff = np.where(nrm.sum(axis=0) > 0,
                    1.0 / np.maximum((nrm ** 2).sum(axis=0), 1e-30), float(n))
    winner = np.argmax(Wl, axis=0).astype(np.int32)
    top = nrm.max(axis=0)

    # `flat` is 1 where the response VARIES most; invert so high = flat
    fscore = 1.0 - fl[:neff.shape[0], :neff.shape[1]]
    q = np.quantile(fscore, [0.2, 0.4, 0.6, 0.8])
    strata = np.digitize(fscore, q)
    rows = []
    for s in range(5):
        m = strata == s
        if not np.any(m):
            continue
        rows.append(dict(stratum=s, n_pixels=int(m.sum()),
                         mean_n_eff=float(neff[m].mean()),
                         mean_top_weight=float(top[m].mean()),
                         frac_single_winner=float((top[m] > 0.9).mean())))
        print("  stratum %d (%-15s) px %7d   n_eff %6.2f   top w %.3f   "
              "single-winner %.3f"
              % (s, ("most structured", "", "", "", "FLATTEST")[s],
                 m.sum(), neff[m].mean(), top[m].mean(), (top[m] > 0.9).mean()))

    obs, chance, frac = spatial_coherence(winner, n, valid=Wl.sum(axis=0) > 0)

    # THE CONFOUND CONTROL. `sq = smooth5(lap**2)` mixes neighbouring
    # coefficients, so adjacent pixels share input and their winners would
    # correlate even if no frame held a genuine focus advantage anywhere.
    # Without this null, a high coherence reading is a property of the kernel,
    # not of the selection.
    #
    # The null keeps the SCENE (so the gate admits at the same rate and the
    # comparison is like-for-like) and destroys only the between-frame focus
    # signal: every frame becomes the same mean image plus independent noise
    # at the fitted level. Any winner coherence that survives is manufactured.
    # A pure-noise null was tried first and was useless: nothing cleared the
    # gate, so `argmax` returned frame 0 everywhere by abstention.
    rng = np.random.default_rng(20260827)
    base = np.mean([f.astype(np.float64) for f in frames], axis=0)
    sd = np.sqrt(np.maximum(var0, 0.0))[:, :, None]
    nz = [base + rng.normal(0.0, 1.0, base.shape) * sd for _ in range(n)]
    _, Wn = VP.merge(nz, dict(SHIP), BETA, var0, nb=nb)
    Wnl = Wn[level]
    wnull = np.argmax(Wnl, axis=0).astype(np.int32)
    vn = Wnl.sum(axis=0) > 0
    obs_n, chance_n, frac_n = spatial_coherence(wnull, n, valid=vn)
    print("  winner-field coherence: %.4f agree, chance %.4f, EXCESS %.4f "
          "(on the %.3f of pixels where any frame is admitted)"
          % (obs, chance, obs - chance, frac))
    if obs_n is None:
        print("  pure-noise null       : NOT MEASURED -- no pixel admitted "
              "any frame, so the null carries no information")
        ex_n = None
        over = None
    else:
        ex_n = obs_n - chance_n
        over = (obs - chance) - ex_n
        print("  pure-noise null       : %.4f agree, chance %.4f, excess "
              "%.4f (on %.3f of pixels)" % (obs_n, chance_n, ex_n, frac_n))
        print("  coherence beyond what the smoothing kernel alone produces: "
              "%.4f" % over)
    return rows, dict(observed_agreement=obs, chance_agreement=chance,
                      excess=obs - chance, admitted_fraction=frac,
                      null_observed=obs_n, null_chance=chance_n,
                      null_excess=ex_n, null_admitted_fraction=frac_n,
                      excess_over_null=over,
                      level=level, n_frames=n)


def ask2_commission(frames, var0, nb=7):
    """Both directions on the two ASK-2 statistics."""
    ok, bad = [], []
    rng = np.random.default_rng(7)
    h = 256
    # coherence: a blocky field must read high, a random field ~chance
    blk = np.kron(rng.integers(0, 5, (16, 16)), np.ones((16, 16))).astype(np.int32)
    o1, c1, _ = spatial_coherence(blk, 5)
    rnd = rng.integers(0, 5, (h, h)).astype(np.int32)
    o2, c2, _ = spatial_coherence(rnd, 5)
    (ok if (o1 - c1) > 0.5 else bad).append(
        "COHERENCE, coherent input: excess %.4f (blocky field, must be high)"
        % (o1 - c1))
    (ok if abs(o2 - c2) < 0.02 else bad).append(
        "COHERENCE, incoherent input: excess %+.4f (random field, must be ~0)"
        % (o2 - c2))
    # flatness: a stack that is identical everywhere must read maximally flat;
    # a stack where one frame is IN FOCUS must not.
    # The first version of this plant added a CONSTANT block and read 0.000,
    # correctly: a constant has no high-frequency content, so it is not a
    # focus change at all. The statistic was right and the plant was wrong.
    base = [np.full((64, 64, 3), 1000.0) for _ in range(5)]
    f_same, _ = flatness(base)
    yy, xx = np.mgrid[0:64, 0:64]
    detail = (((yy + xx) % 2) * 4000.0)[:, :, None]
    var = [b.copy() for b in base]
    var[2][20:44, 20:44, :] += detail[20:44, 20:44, :]
    f_var, _ = flatness(var)
    (ok if f_same.max() < 1e-6 else bad).append(
        "FLATNESS, no through-focus variation: max response spread %.3g "
        "(must be ~0)" % f_same.max())
    (ok if f_var[32, 32] > 0.9 else bad).append(
        "FLATNESS, one frame carries fine detail: spread at that pixel %.3f "
        "(must be ~1)" % f_var[32, 32])
    return ok, bad


# --------------------------------------------------------------------------
def main():
    os.makedirs(OUT, exist_ok=True)
    subj = sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles"
    frames = load(subj)
    var0, read2, gph = VP.fit_variance(frames[0][:, :, 1])
    if gph < 0:
        print("REFUSED: fitted photon gain is negative")
        return 2
    print("%s: %d OK frames, noise var = %.1f + %.4f*S" % (subj, len(frames),
                                                           read2, gph))

    print("\ncommissioning ASK 2 statistics (both directions):")
    ok, bad = ask2_commission(frames, var0)
    for l in ok:
        print("  ok      " + l)
    for l in bad:
        print("  FAILED  " + l)
    if bad:
        print("REFUSED: ASK 2 statistics not commissioned")
        return 2

    print("\ncommissioning ASK 1 comparison (needs a POSITIVE control):")
    ok1, bad1 = ask1_commission(frames, var0)
    for l in ok1:
        print("  ok      " + l)
    for l in bad1:
        print("  FAILED  " + l)
    if bad1:
        print("REFUSED: the SNR_REF comparison is not shown to be able to fail")
        return 2

    print("\nASK 1: does SNR_REF cancel in w_i / sum_j w_j?")
    r1 = ask1(frames, var0)

    print("\nASK 2: weight concentration by through-focus flatness (L3):")
    r2, coh = ask2(frames, var0)

    res = dict(subject=subj, frames=len(frames), snr_ref=r1,
               flatness_strata=r2, coherence=coh,
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
        print("\nREFUSED: crashed; no ASK 1 or ASK 2 claim is measured")
        sys.exit(2)
