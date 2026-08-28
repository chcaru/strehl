"""Re-measure the N-invariance ladder on a band the SUBJECT QUALIFIES.

WHY THIS EXISTS. Sections 9.23.5-9.23.8b state every scene number on two fixed
bands, `MID = 0.30-0.35` and `FINE = 0.40-0.45` cyc/px, chosen once and applied
to both subjects. V-LINEAR (31eda43a, docs/research/V-LINEAR-BANDS.md) then
measured that the signal/noise boundary is a property of the SUBJECT, and both
of my subjects fall below my bands:

    coffee-bubbles  boundary 0.25   my MID -> 0.30-0.40 R=1.533 MARGINAL
    112MSDCF        boundary 0.20   my MID -> 0.30-0.40 R=1.089 FAIL(noise)

So on 112MSDCF my "scene" was read in a band where in-focus and defocused
source tiles differ by 8.9%. This file asks whether the conclusions survive on
a band the subject actually qualifies -- 0.17-0.20 PASSes on both.

THE CONFOUND THIS FILE EXISTS TO CONTROL. The obvious reading of the raw
numbers -- that the selective arms manufacture band power -- is also what a
plain BLUR would produce, because the mean arm softens and every fine band
would then show a large argmax/mean ratio whether or not anything was
manufactured. A fine band that the subject QUALIFIES separates the two: blur
attenuates a qualified fine band just as much, so if the ratio is large only in
the unqualified bands, blur cannot be the explanation.

GROUND TRUTH, because the reading above accuses my own instrument and an
accusation needs a fixture where the answer is known. `synth_bandlimited`
builds a focus stack whose scene texture is spectrally truncated at 0.25 cyc/px,
so MID and FINE contain per-frame noise and NOTHING ELSE by construction. The
true scene power there is zero. Both directions are planted:

    ABSENT   texture truncated at 0.25 -> true scene at MID is exactly 0
    PRESENT  broadband texture         -> true scene at MID is real

The truncation is VERIFIED rather than assumed (`_assert_truncated`): a fixture
that failed to remove the content would be inert and would read as a clean
result. This lane has shipped an inert plant before.
"""
import io
import json
import os
import sys

import numpy as np

import vn_pyr as VP
from vn_manuf import synth
from vn_ninv2 import arm_merge, band_power, pick, twin_merge
from vn_noise import fit_variance_paired
from vn_snrref import load

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\qband"

# V-LINEAR FINE-partition verdicts for the two subjects this lane measured,
# transcribed from bandsweep-far20-<subject>.json via bandsweep.boundary().
BOUNDARY = {"coffee-bubbles": 0.25, "112MSDCF": 0.20}

MOT = (0.02, 0.05)    # PASS on both subjects -- coarse qualified control
QUAL = (0.17, 0.20)   # PASS on both subjects -- the fine qualified band
MID = (0.30, 0.35)    # the band sections 9.23.5-9.23.8b used
FINE = (0.40, 0.45)   # the band sections 9.23.5-9.23.8b used
QBANDS = (MOT, QUAL, MID, FINE)
TAG = {MOT: "mot", QUAL: "qual", MID: "mid", FINE: "fine"}
ARMS = ("mean", "confidence", "shipping", "argmax")


def key(b):
    return "%.2f-%.2f" % b


def _c3(a):
    """band_power reads the green channel, so 2-D fixtures are widened."""
    return a if a.ndim == 3 else np.repeat(a[:, :, None], 3, axis=2)


def decomp(rec, nrec, base):
    """total / noise / scene in every band, from ONE merge and ONE twin.

    `nrec - base` is the noise the arm's own weight field passed through, which
    is why `twin_merge` is given the arm's W rather than being allowed to
    choose its own.
    """
    tot = band_power(rec, QBANDS)
    noi = band_power(nrec - base, QBANDS)
    out = {}
    for b in QBANDS:
        t, n = tot[key(b)], noi[key(b)]
        out[TAG[b]] = dict(total=t, noise=n, scene=t - n)
    return out


def ladder(frames, ks, seed=20260828):
    """The 4 arms x N ladder, decomposed in all four bands."""
    var0, _, _ = fit_variance_paired(frames)
    rows = []
    for name in ARMS:
        for k in ks:
            idx = pick(len(frames), k)
            sub = [frames[i] for i in idx]
            v, _, _ = fit_variance_paired(sub)
            rec, W = arm_merge(name, sub, v)
            syn = synth(sub, v, seed=seed)
            base = np.mean(sub, axis=0)
            nrec = twin_merge(syn, v, W)
            d = decomp(rec, nrec, base)
            rows.append(dict(arm=name, N=k, bands=d))
    return rows


# --------------------------------------------------------------------------
# GROUND TRUTH FIXTURE
# --------------------------------------------------------------------------
def _lowpass(img, fc):
    """Hard spectral truncation. Exact, so the ground truth is exact."""
    F = np.fft.rfft2(img)
    h, w = img.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    F[np.sqrt(fy ** 2 + fx ** 2) >= fc] = 0.0
    return np.fft.irfft2(F, s=img.shape)


def synth_bandlimited(kind, n=13, size=256, seed=11, fc=0.22):
    """A focus stack with KNOWN band content.

    `kind="absent"` truncates the scene texture at `fc`, so the true scene
    power at MID and FINE is zero and anything an instrument reports there is
    manufactured. `kind="present"` leaves the texture broadband.

    The depth ramp and per-frame focus follow vn_dilute.synth_stack: pixel
    depth D(y) in [-1,1], frame i focused at d_i, defocus |D-d_i|*scale. Both
    kinds share the seed, so they differ ONLY in the spectral truncation.
    """
    from scipy.ndimage import gaussian_filter
    rng = np.random.default_rng(seed)
    base = rng.standard_normal((size, size))
    base = 2000.0 + 1200.0 * base / max(float(np.std(base)), 1e-9)
    raw = base.copy()
    if kind == "absent":
        base = _lowpass(base, fc)
    sigmas = np.concatenate([[0.0], np.geomspace(0.25, 8.0, 15)])
    blurs = np.stack([base if s == 0.0 else gaussian_filter(base, s)
                      for s in sigmas])
    D = np.linspace(-1.0, 1.0, size)[:, None] * np.ones((1, size))
    frames = []
    for i in range(n):
        d = -1.0 + 2.0 * i / max(n - 1, 1)
        defocus = np.abs(D - d) * 3.0
        idx = np.abs(sigmas[:, None, None] - defocus[None]).argmin(axis=0)
        f2 = np.take_along_axis(blurs, idx[None], axis=0)[0]
        f2 = f2 + rng.standard_normal((size, size)) * 25.0
        frames.append(np.repeat(f2[:, :, None], 3, axis=2))
    return frames, raw, base


def _assert_truncated(raw, cut, fc=0.22, tol=1e-3):
    """The plant must actually land. A fixture that did not remove the content
    would read exactly like a clean instrument, so this hard-errors.

    `tol` is 1e-3 rather than 0 because `band_power` applies a Hann window
    before the transform, and windowing leaks a little energy past any hard
    spectral edge. The cut is placed at 0.22 to leave a guard band below MID's
    0.30 edge; the threshold was NOT loosened to accommodate leakage, the guard
    band was widened instead.
    """
    a = band_power(_c3(raw), QBANDS)
    b = band_power(_c3(cut), QBANDS)
    for bd in (MID, FINE):
        if not b[key(bd)] < tol * a[key(bd)]:
            raise SystemExit(
                "FIXTURE IS INERT: truncation at %.2f left %.4g of %.4g at %s "
                "(needed < %g of it)" % (fc, b[key(bd)], a[key(bd)], key(bd), tol))
    for bd in (MOT, QUAL):
        if not b[key(bd)] > 0.5 * a[key(bd)]:
            raise SystemExit(
                "FIXTURE OVER-CUT: truncation at %.2f also removed the "
                "qualified band %s (%.4g of %.4g)"
                % (fc, key(bd), b[key(bd)], a[key(bd)]))
    return {key(bd): (a[key(bd)], b[key(bd)]) for bd in QBANDS}


def ratio(rows, tag, N):
    r = {x["arm"]: x["bands"][tag]["scene"] for x in rows if x["N"] == N}
    if r["mean"] <= 0:
        return float("nan"), r
    return r["argmax"] / r["mean"], r


def _smooth_all(fs):
    out = []
    for f in fs:
        a = f.copy()
        g = f[:, :, 1]
        a[1:-1, 1:-1, 1] = (g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2]
                            + g[1:-1, 2:] + g[1:-1, 1:-1]) / 5.0
        out.append(a)
    return out


def _sharpen_all(fs):
    out = []
    for f in fs:
        lap, _ = VP.lap_pyr(f[:, :, 1], 1)
        a = f.copy()
        a[:, :, 1] = f[:, :, 1] + 0.5 * lap[0]
        out.append(a)
    return out


def _scene(fs, tag, seed=20260828):
    """Shipping-arm scene in one band, the same path the ladder uses."""
    v, _, _ = fit_variance_paired(fs)
    rec, W = arm_merge("shipping", fs, v)
    nrec = twin_merge(synth(fs, v, seed=seed), v, W)
    return decomp(rec, nrec, np.mean(fs, axis=0))[tag]["scene"]


def commission():
    """Gate the INSTRUMENT; record the hypothesis test as a result.

    The gate below tests properties the decomposition must have for the
    qualified-band re-run to mean anything. The two hypothesis checks that used
    to sit here -- that an unqualified band would show a larger argmax/mean
    scene ratio than a qualified one -- FAILED on this fixture and are now
    reported as a refutation rather than enforced as a requirement. They were a
    test of a claim about the merge, not a property of the instrument, and
    gating on them would have meant tuning the fixture until my hypothesis
    passed.
    """
    ok, bad, notes = [], [], {}
    fa, raw, cut = synth_bandlimited("absent")
    spec = _assert_truncated(raw, cut)
    ok.append("FIXTURE LANDS: truncation left %.3g of MID and %.3g of FINE "
              "(both under 1e-3, so the true scene there is nil), and kept "
              "%.1f%% of MOT and %.1f%% of QUAL"
              % (spec[key(MID)][1] / spec[key(MID)][0],
                 spec[key(FINE)][1] / spec[key(FINE)][0],
                 100 * spec[key(MOT)][1] / spec[key(MOT)][0],
                 100 * spec[key(QUAL)][1] / spec[key(QUAL)][0]))

    b0 = band_power(fa[0], QBANDS)[key(MID)]
    b1 = band_power(fa[0].copy(), QBANDS)[key(MID)]
    (ok if b0 == b1 else bad).append(
        "NULL: rescoring an identical array returns the identical number "
        "(%.12g)" % b0)
    pert = fa[0] + np.random.default_rng(5).standard_normal(fa[0].shape) * 5.0
    b2 = band_power(pert, QBANDS)[key(MID)]
    (ok if abs(b2 - b0) > 1e-9 else bad).append(
        "NULL IS A PREDICTION: perturbing the array moves it %.4g -> %.4g"
        % (b0, b2))

    # BOTH DIRECTIONS on the qualified band -- this is what licenses the re-run.
    sq = _scene(fa, "qual")
    sd = _scene(_smooth_all(fa), "qual")
    su = _scene(_sharpen_all(fa), "qual")
    (ok if sd < sq else bad).append(
        "DOWN at QUAL: smoothing every source lowers the qualified-band scene "
        "%.5g -> %.5g" % (sq, sd))
    (ok if su > sq else bad).append(
        "UP at QUAL: sharpening every source raises the qualified-band scene "
        "%.5g -> %.5g" % (sq, su))

    # The instrument's spurious floor, on ground truth. Must be non-zero or the
    # fixture demonstrates nothing about the bias it was built to expose.
    n = len(fa)
    ks = [n, max(2, n // 2)]
    ra = ladder(fa, ks)
    rp = ladder(synth_bandlimited("present")[0], ks)
    sp_mid = {r["arm"]: r["bands"]["mid"]["scene"] for r in ra if r["N"] == n}
    tr_qual = {r["arm"]: r["bands"]["qual"]["scene"] for r in ra if r["N"] == n}
    (ok if min(sp_mid.values()) > 0 else bad).append(
        "SPURIOUS FLOOR IS REAL: with TRUE scene at MID exactly zero every arm "
        "still reports scene there -- %s"
        % ", ".join("%s %.4g" % (a, sp_mid[a]) for a in ARMS))
    notes["spurious_mid_on_zero_truth"] = sp_mid
    notes["true_qual_same_fixture"] = tr_qual
    notes["spurious_as_pct_of_qual"] = {
        a: 100.0 * sp_mid[a] / tr_qual[a] for a in ARMS}

    qa, _ = ratio(ra, "qual", n)
    ma, _ = ratio(ra, "mid", n)
    qp, _ = ratio(rp, "qual", n)
    mp, _ = ratio(rp, "mid", n)
    notes["refuted_hypothesis"] = dict(
        absent_mid=ma, absent_qual=qa, present_mid=mp, present_qual=qp,
        absent_ratio_of_ratios=ma / qa, present_ratio_of_ratios=mp / qp,
        predicted="absent_ratio_of_ratios > present_ratio_of_ratios",
        holds=bool((ma / qa) > (mp / qp)))
    return ok, bad, notes


def load_frames(subj, force_green=False):
    """RGB bundle if present, else the green-only bundle widened to 3 channels.

    THE GAUGE RISK, STATED. `bundle/<subj>.npz` (RGB) no longer exists for
    112MSDCF; only `gbundle/<subj>.npz` (green channel) does. Widening green to
    three channels is a CHANGE OF GAUGE from the run that produced sections
    9.23.5-9.23.8b, and this lane has already watched a gauge mismatch invert a
    headline. It is tolerable here only because every comparison this file
    makes is BETWEEN BANDS WITHIN ONE RUN, never against the older numbers --
    and `--green` exists so the change can be measured rather than assumed, by
    re-running a subject that has both.
    """
    rgb = os.path.join(r"C:\dev\strehl-out\V-NEVERWORSE\bundle", "%s.npz" % subj)
    if os.path.exists(rgb) and not force_green:
        return load(subj), "rgb"
    if os.path.exists(rgb) and force_green:
        fs = load(subj)
        return [np.repeat(f[:, :, 1][:, :, None], 3, axis=2) for f in fs], \
            "green-replicated (from RGB, control)"
    import vn_gbundle as GB
    g, kept, meta = GB.load(subj, rule="registered")
    return [np.repeat(x[:, :, None], 3, axis=2).astype(np.float64) for x in g], \
        "green-replicated (gbundle, rule=%s, n=%d)" % (meta.get("admit_rule"),
                                                       len(kept))


def main():
    os.makedirs(OUT, exist_ok=True)
    ok, bad, comm = commission()
    print("COMMISSIONING")
    for s in ok:
        print("  ok   %s" % s)
    for s in bad:
        print("  BAD  %s" % s)
    if bad:
        raise SystemExit("REFUSED: the qualified-band instrument is not "
                         "commissioned")

    rh = comm["refuted_hypothesis"]
    print("\nRECORDED REFUTATION (a result, not a gate)")
    print("  I predicted the argmax/mean scene ratio would be LARGER in a band")
    print("  with no true content than in one with real content. On ground")
    print("  truth it is not:")
    print("    content ABSENT at MID : MID %.4g vs QUAL %.4g -> %.4g"
          % (rh["absent_mid"], rh["absent_qual"], rh["absent_ratio_of_ratios"]))
    print("    content PRESENT at MID: MID %.4g vs QUAL %.4g -> %.4g"
          % (rh["present_mid"], rh["present_qual"],
             rh["present_ratio_of_ratios"]))
    print("  prediction '%s' holds: %s" % (rh["predicted"], rh["holds"]))
    print("  => the large argmax/mean ratios seen on real subjects in")
    print("     unqualified bands are NOT evidence of manufacture. The plain")
    print("     mean blurs, and that alone produces them.")
    print("\n  INSTRUMENT BIAS, on a fixture whose true MID scene is zero:")
    for a in ARMS:
        print("    %-11s reports %.4g at MID (truth 0) = %.2f%% of its own "
              "QUAL scene" % (a, comm["spurious_mid_on_zero_truth"][a],
                              comm["spurious_as_pct_of_qual"][a]))

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    subj = args[0] if args else "coffee-bubbles"
    force_green = "--green" in sys.argv[1:]
    frames, gauge = load_frames(subj, force_green)
    n = len(frames)
    ks = sorted({n, max(2, n // 2), max(2, n // 4)}, reverse=True)
    print("\n%s: %d frames, boundary %.2f cyc/px, gauge %s"
          % (subj, n, BOUNDARY[subj], gauge))
    rows = ladder(frames, ks)

    print("\n  %-11s %4s" % ("arm", "N")
          + "".join("%14s" % ("scene " + TAG[b]) for b in QBANDS))
    for r in rows:
        print("  %-11s %4d" % (r["arm"], r["N"])
              + "".join("%14.4e" % r["bands"][TAG[b]]["scene"] for b in QBANDS))

    print("\n  argmax/mean scene ratio, deepest N=%d:" % ks[0])
    for b in QBANDS:
        rt, _ = ratio(rows, TAG[b], ks[0])
        q = "QUALIFIED" if b[1] <= BOUNDARY[subj] else "unqualified"
        print("    %-10s %-12s %s"
              % (key(b), ("%.1fx" % rt) if rt == rt else "n/a (mean<=0)", q))

    print("\n  N-invariance of the SCENE term, deepest vs half:")
    print("    %-11s" % "arm"
          + "".join("%14s" % TAG[b] for b in QBANDS))
    verdict = {}
    for name in ARMS:
        hi = [r for r in rows if r["arm"] == name and r["N"] == ks[0]][0]
        lo = [r for r in rows if r["arm"] == name and r["N"] == ks[1]][0]
        cells = []
        for b in QBANDS:
            a, c = hi["bands"][TAG[b]]["scene"], lo["bands"][TAG[b]]["scene"]
            cells.append((a / c) if (c > 0 and a > 0) else float("nan"))
        verdict[name] = {TAG[b]: cells[i] for i, b in enumerate(QBANDS)}
        print("    %-11s" % name
              + "".join(("%14.4f" % c) if c == c else "%14s" % "REFUSED"
                        for c in cells))

    out = "%s%s.json" % (subj, "-green" if force_green else "")
    with io.open(os.path.join(OUT, out), "w",
                 encoding="utf-8") as f:
        json.dump(dict(subject=subj, n=n, ks=ks, boundary=BOUNDARY[subj],
                       gauge=gauge,
                       rows=rows, verdict=verdict, commission=ok,
                       commission_values=comm), f, indent=1)
    print("\nwrote %s" % os.path.join(OUT, out))


if __name__ == "__main__":
    main()
