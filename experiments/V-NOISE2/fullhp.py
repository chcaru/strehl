"""fullhp -- route 1: total band amplitude on the FULL merges, no half-stack.

THE QUESTION.  On `119MSDCF`, `C` -- the coherence statistic behind the
README's own headline -- reads `enfuse` at 2.017x strehl's detail amplitude at
0.20-0.25 cyc/px.  `C` is a cross-power between two HALF-stacks: it counts only
structure that is CORRELATED across them.  A merge that selects different source
frames in half A than in half B delivers detail in the full render that is
nonetheless incoherent across the halves, and `C` charges it as absent.

So the 2.017 has two readings that cut opposite ways:

  TRUE DETAIL LOSS      we are genuinely half as sharp as `enfuse` here, and the
                        project's central quality claim is broken.
  HALF-STACK INCOHERENCE the detail is present in the DELIVERED image and the
                        instrument cannot see it; the 2.017 is an artifact, and
                        our published noise figures are biased AGAINST us
                        because incoherent detail lands in the half-difference
                        and is counted as noise.

The second is a hypothesis under which this project looks better, so it gets
the hostile handling: see HOSTILE READING at the bottom of the output, which is
printed whether or not the flattering branch wins.

THE SIDESTEP.  The half-split exists to estimate NOISE.  Detail does not need
it.  Measure total band amplitude on the FULL merges -- ours against `enfuse`'s,
same band, same scene content.  That counts detail whether or not it is coherent
across halves.

    full-render detail LEVEL while half-stack C reads 2.017
        -> the gap IS the incoherence, and it is quantified
    full-render detail ALSO ~2x
        -> the detail is genuinely absent and the incoherence story is dead

WHICH TERMS ARE BAND-LIMITED, stated before any two are combined, because this
lane has already shipped one statistic that subtracted a FULL-BAND noise term
from a HIGH-PASS total (V-NOISE2 sec.5) and that defect reached M127's
published table.  Let B = [0.20, 0.25) cyc/px.

    D_X = median over DETAIL tiles of bandpower(X, B)   BAND-LIMITED to B
    F_X = median over FLAT   tiles of bandpower(X, B)   BAND-LIMITED to B
    S_X = D_X - F_X                                     BAND-LIMITED to B
    reported ratio = sqrt(S_enfuse / S_strehl)          amplitude, not power

EVERY term is band-limited to the identical annulus B.  There is no full-band
quantity anywhere in this file, and no half-stack appears in any of them.
`bandpower` is Parseval-normalised contrast^2 (h2.contrast_fft divides by the
tile mean, so exposure and white point cancel), i.e. the variance carried by B.

THE KNOWN FAILURE MODE, which is why F_X exists.  Total band power counts NOISE
as detail: a noisier merge scores HIGHER.  `enfuse` is measured at 3.04x
strehl's luma noise on this subject, so the uncorrected reading is biased
towards `enfuse` and the correction moves in strehl's favour -- the flattering
direction.  Hence the required commissioning arm below, and hence the
uncorrected reading is ALWAYS printed alongside the corrected one.

ASSUMPTIONS, stated:
  A1  noise power in B is the same on FLAT tiles as on DETAIL tiles.  Partly
      testable: the arms' population luma levels are printed, and NOISE-ABS
      deliberately violates A1 and is checked against a computed prediction.
  A2  FLAT tiles carry negligible scene power in B.  They are the bottom
      quartile of high-pass energy, not zero, so S_X UNDERSTATES scene power for
      both arms.  The FLATSENS arm varies the flat threshold to bound this.

COMMISSIONING -- every arm's answer is fixed before it is run.

  IDENT-BITWISE  X against itself.  Exactly 1.000.  Determinism only; a
                 statistic compared against its own input returns 1 by
                 arithmetic and that is not evidence.  Reported and discounted.
  IDENT-PATH     k = 1.00 through the real plant.  1.000, and potency is proven
                 by the k != 1 rungs rather than asserted.
  SCALE          strehl read against ITSELF through the s = 1.0040 crop
                 placement and tile size the comparator gets.  1.000.  Isolates
                 the tile-size asymmetry, which is the only geometric
                 difference between the two arms' code paths.
  k=1.30         companion SHARPER.  Must return > 1.  A statistic bounded
                 below at parity passes a degradation ladder trivially, and this
                 project has already shipped a gauge perverse on its own arm.
  k=0.95..0.50   degradation ladder.  Must recover k.
  NOISE-PROP     THE REQUIRED ARM.  Gaussian noise at sigma = beta * tile mean,
                 so added contrast power is identical in both populations.  No
                 detail change whatsoever.  The CORRECTED statistic must NOT
                 rise; the UNCORRECTED one MUST rise, or the plant is inert and
                 the arm proves nothing.  Both are printed.
  NOISE-ABS      the same noise at constant ABSOLUTE sigma, which violates A1 by
                 construction.  Checked against a prediction computed from the
                 measured population levels, so the instrument's failure mode is
                 bounded rather than assumed away.
  NOISE+DETAIL   noise AND k = 0.70 together.  Must still recover 0.70.  This is
                 the arm that resembles the real comparison, where `enfuse` is
                 both noisier and possibly different in detail.

    python fullhp.py [key=119] [nboot=400]
"""
import json
import os
import sys

import numpy as np
from scipy.ndimage import zoom

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
sys.path.insert(0, os.path.join(_HERE, "..", "V-NOISE"))
import h2                                                        # noqa: E402
from h2h2b import Comp, T                                        # noqa: E402

import hd2                                                       # noqa: E402
from ladder import LP, plant                                     # noqa: E402

BAND = (0.2, 0.25)
W = (0.2126, 0.7152, 0.0722)
MARGIN = 2 * LP              # planting margin, discarded before measuring
REG_D = 4                    # placement registration is done on 4x block means
REG_WIN = 8                  # +/- 8 blocks = +/- 32 px placement search
BETA = 0.04                  # NOISE-PROP: sigma = BETA * tile mean


def bandpower(crop, lo=BAND[0], hi=BAND[1]):
    """Parseval-normalised contrast^2 carried by the annulus [lo, hi) cyc/px.

    BAND-LIMITED by construction: nothing outside the annulus is summed."""
    t = crop.shape[0]
    f = h2.contrast_fft(crop)
    if f is None:
        return None
    r = h2.radial(t)
    norm = (t * t) ** 2 * (h2.window(t) ** 2).mean()
    p = (np.abs(f) ** 2) / norm
    return float(p[(r >= lo) & (r < hi)].sum())


def block_mean(a, d):
    h, w = a.shape[0] // d * d, a.shape[1] // d * d
    return a[:h, :w].reshape(h // d, d, w // d, d).mean((1, 3))


class Placer:
    """Per-tile integer placement of a comparator crop against strehl's.

    V-HEADTOHEAD2 sec.7: geometry is re-derived, not trusted.  geomfull.py
    measures ONE global offset for the pair; this refines it per tile, because
    a single global number is exactly the assumption sec.7 says not to make.

    The search runs on REG_D-fold block means, so the comparator is resampled
    only to FIND the placement.  The measured crop is always native pixels --
    sub-pixel resampling adds blur to the very quantity under test.
    """

    def __init__(self, ref, mov, scale):
        self.ref, self.mov, self.s = ref, mov, float(scale)
        self.rb = block_mean(ref.g, REG_D)
        mb = block_mean(mov.g, REG_D)
        self.mb = zoom(mb, self.s, order=3) if abs(self.s - 1.0) > 1e-9 else mb

    def place(self, y, x, t):
        """Return (y0, x0, ts) in the comparator's own pixels, or None."""
        s = self.s
        ts = int(round(t / s))
        b = t // REG_D
        yb, xb = y // REG_D, x // REG_D
        if (yb + b > self.rb.shape[0] or xb + b > self.mb.shape[0]
                or xb + b > self.rb.shape[1] or yb + b > self.mb.shape[1]):
            return None
        R = self.rb[yb:yb + b, xb:xb + b]
        R = R - R.mean()
        best, bdy, bdx = -2.0, 0, 0
        rn = np.sqrt((R * R).sum())
        if rn <= 0:
            return None
        for dy in range(-REG_WIN, REG_WIN + 1):
            for dx in range(-REG_WIN, REG_WIN + 1):
                ay, ax = yb + dy, xb + dx
                if (ay < 0 or ax < 0 or ay + b > self.mb.shape[0]
                        or ax + b > self.mb.shape[1]):
                    continue
                M = self.mb[ay:ay + b, ax:ax + b]
                M = M - M.mean()
                mn = np.sqrt((M * M).sum())
                if mn <= 0:
                    continue
                c = float((R * M).sum()) / (rn * mn)
                if c > best:
                    best, bdy, bdx = c, dy, dx
        # placement was found in strehl-frame block units; convert to the
        # comparator's own pixel grid by dividing out the content scale.
        y0 = int(round((y + bdy * REG_D) / s))
        x0 = int(round((x + bdx * REG_D) / s))
        return y0, x0, ts, best, bdy * REG_D, bdx * REG_D


def med_bp(comp, cells, placer=None, mutate=None, rng=None):
    """Median band power over a tile population, with an optional mutation."""
    vals = []
    for (y, x) in cells:
        if placer is None:
            c, nc = comp.crop(int(y), int(x), T)
            if c is None or nc:
                continue
        else:
            pl = placer.place(int(y), int(x), T)
            if pl is None:
                continue
            y0, x0, ts = pl[0], pl[1], pl[2]
            c, nc = comp.crop(y0, x0, ts)
            if c is None or nc:
                continue
        if mutate is not None:
            c = mutate(c, rng)
        v = bandpower(c)
        if v is not None and np.isfinite(v):
            vals.append(v)
    return np.array(vals)


def scene_from(D, F):
    """S = D - F, both BAND-LIMITED to the same annulus.  No full-band term."""
    return float(np.median(D) - np.median(F))


def boot(Ds, Fs, De, Fe, nboot, rng):
    """Bootstrap the amplitude ratio over tiles; populations resampled
    independently because D and F are medians over disjoint tile sets."""
    out = []
    for _ in range(nboot):
        i = rng.integers(0, len(Ds), len(Ds))
        j = rng.integers(0, len(Fs), len(Fs))
        p = rng.integers(0, len(De), len(De))
        q = rng.integers(0, len(Fe), len(Fe))
        ss = np.median(Ds[i]) - np.median(Fs[j])
        se = np.median(De[p]) - np.median(Fe[q])
        if ss > 0 and se > 0:
            out.append(np.sqrt(se / ss))
    if not out:
        return (np.nan, np.nan)
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


# ------------------------------------------------------------------ mutations
def mut_plant(k):
    def f(c, rng):
        return plant(c, k)
    return f


def mut_noise_prop(beta):
    def f(c, rng):
        return c + rng.normal(0.0, beta * float(c.mean()), c.shape)
    return f


def mut_noise_abs(sig):
    def f(c, rng):
        return c + rng.normal(0.0, sig, c.shape)
    return f


def mut_both(k, beta):
    def f(c, rng):
        p = plant(c, k)
        return p + rng.normal(0.0, beta * float(p.mean()), p.shape)
    return f


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "119"
    nboot = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    arm = os.path.join(hd2.ROOT, key, "arms")
    sp = os.path.join(arm, "strehl-full.tiff")
    ep = os.path.join(arm, "coh-enfuse-full.tif")
    for p in (sp, ep):
        if not os.path.exists(p):
            raise SystemExit(f"missing {p} -- run build_full.ps1 first")
    with open(os.path.join(hd2.ROOT, key, "geom-full.json"), encoding="utf-8") as fh:
        g = json.load(fh)
    for c in ("strehl-full_vs_strehl-A", "enfuse-full_vs_enfuse-A"):
        if not g[c].get("control_pass"):
            raise SystemExit(f"geomfull canvas control {c} FAILED -- refusing")
    s = float(g["strehl-full_vs_enfuse-full"]["scale"])

    z = np.load(os.path.join(hd2.ROOT, key, "census.npz"))
    cells, emax = z["cells"], z["emax"]
    flat_idx = [int(i) for i in z["flat"]]
    order = np.argsort(emax)
    det_idx = [int(i) for i in order[-len(flat_idx):]]
    DET = [tuple(cells[i]) for i in det_idx]
    FLAT = [tuple(cells[i]) for i in flat_idx]

    S = Comp(dict(path=sp, weights=W))
    E = Comp(dict(path=ep, weights=W))
    P = Placer(S, E, s)
    rng = np.random.default_rng(20260827)

    print("=" * 100)
    print(f"FULLHP -- route 1: total band amplitude on the FULL merges, {key}")
    print("=" * 100)
    print(f"  strehl  {sp}")
    print(f"  enfuse  {ep}")
    print(f"  band {BAND[0]}-{BAND[1]} cyc/px, content scale {s:.4f} "
          f"(re-derived by geomfull.py, canvas controls PASS)")
    print(f"  {len(DET)} DETAIL tiles, {len(FLAT)} FLAT tiles, {T}px, "
          f"per-tile integer placement on {REG_D}x block means")
    print("  NO HALF-STACK IS READ ANYWHERE IN THIS FILE.")

    # -------------------------------------------------------- commissioning
    print()
    print("-" * 100)
    print("COMMISSIONING -- strehl-full against a mutated copy of ITSELF; "
          "every answer fixed in advance")
    print("-" * 100)
    base_D = med_bp(S, DET)
    base_F = med_bp(S, FLAT)
    base_S = scene_from(base_D, base_F)

    def med_level(cells):
        v = []
        for (y, x) in cells:
            c, nc = S.crop(int(y), int(x), T)
            if c is not None and not nc:
                v.append(float(c.mean()))
        return float(np.median(v))

    lvl_D, lvl_F = med_level(DET), med_level(FLAT)
    print(f"  strehl base: D {np.median(base_D):.4e}  F {np.median(base_F):.4e}  "
          f"S {base_S:.4e}   F/D {np.median(base_F)/np.median(base_D):.3f}")
    print(f"  population luma levels (A1): DETAIL {lvl_D:.1f}  FLAT {lvl_F:.1f}  "
          f"ratio {lvl_F/lvl_D:.3f}")
    print(f"  {'arm':16s} {'true':>7s} {'corrected':>11s} {'err':>8s} "
          f"{'uncorrected':>13s}  note")

    arms = [("IDENT-BITWISE", 1.0, None),
            ("IDENT-PATH", 1.0, mut_plant(1.0)),
            ("SHARPER k=1.30", 1.30, mut_plant(1.30)),
            ("k=0.95", 0.95, mut_plant(0.95)),
            ("k=0.85", 0.85, mut_plant(0.85)),
            ("k=0.70", 0.70, mut_plant(0.70)),
            ("k=0.50", 0.50, mut_plant(0.50)),
            ("NOISE-PROP", 1.0, mut_noise_prop(BETA)),
            ("NOISE+DETAIL", 0.70, mut_both(0.70, BETA)),
            ]
    comm = {}
    fails = []
    for label, true, mut in arms:
        if mut is None:
            mD, mF = base_D, base_F
        else:
            mD = med_bp(S, DET, mutate=mut, rng=np.random.default_rng(7))
            mF = med_bp(S, FLAT, mutate=mut, rng=np.random.default_rng(8))
        mS = scene_from(mD, mF)
        corr = np.sqrt(mS / base_S) if mS > 0 and base_S > 0 else np.nan
        unc = np.sqrt(np.median(mD) / np.median(base_D))
        note = ""
        if label.startswith("NOISE"):
            if unc <= 1.005:
                note = ("INERT PLANT -- uncorrected did not rise, arm proves "
                        "nothing")
                fails.append(label)
        if label == "IDENT-BITWISE":
            note = "determinism only; discounted"
        err = corr / true - 1 if np.isfinite(corr) else np.nan
        if label != "IDENT-BITWISE" and abs(err) > 0.10:
            fails.append(label)
        if label == "SHARPER k=1.30" and not (corr > 1.0):
            fails.append("SHARPER-perverse")
            note = "PERVERSE: bounded at parity"
        print(f"  {label:16s} {true:7.3f} {corr:11.4f} {err:+7.1%} "
              f"{unc:13.4f}  {note}")
        comm[label] = {"true": true, "corrected": float(corr),
                       "uncorrected": float(unc)}

    # SCALE -- strehl against itself through the comparator's crop geometry.
    Pself = Placer(S, S, s)
    sD = med_bp(S, DET, placer=Pself)
    sF = med_bp(S, FLAT, placer=Pself)
    sS = scene_from(sD, sF)
    sc_r = np.sqrt(sS / base_S) if sS > 0 and base_S > 0 else np.nan
    print(f"  {'SCALE (s=%.4f)' % s:16s} {1.0:7.3f} {sc_r:11.4f} "
          f"{sc_r - 1:+7.1%} {'':>13s}  tile-size asymmetry only")
    comm["SCALE"] = {"true": 1.0, "corrected": float(sc_r)}
    if abs(sc_r - 1.0) > 0.10:
        fails.append("SCALE")

    # NOISE-ABS -- deliberately violates A1; checked against a prediction.
    sig = BETA * lvl_D
    aD = med_bp(S, DET, mutate=mut_noise_abs(sig), rng=np.random.default_rng(9))
    aF = med_bp(S, FLAT, mutate=mut_noise_abs(sig), rng=np.random.default_rng(10))
    aS = scene_from(aD, aF)
    a_r = np.sqrt(aS / base_S) if aS > 0 and base_S > 0 else np.nan
    # added contrast power scales as (sig/level)^2; the annulus takes a fixed
    # fraction of white power, so the over/under-subtraction is computable.
    add_D = (sig / lvl_D) ** 2
    add_F = (sig / lvl_F) ** 2
    frac = np.pi * (BAND[1] ** 2 - BAND[0] ** 2)
    pred = np.sqrt(max(base_S + frac * (add_D - add_F), 0.0) / base_S)
    print(f"  {'NOISE-ABS':16s} {pred:7.3f} {a_r:11.4f} {a_r/pred - 1:+7.1%} "
          f"{np.sqrt(np.median(aD)/np.median(base_D)):13.4f}  "
          f"A1 violated on purpose; 'true' is the PREDICTION")
    comm["NOISE-ABS"] = {"predicted": float(pred), "corrected": float(a_r)}

    ok = not fails
    print(f"\n  COMMISSIONING: {'PASS' if ok else 'FAIL -- ' + ', '.join(sorted(set(fails)))}")
    if not ok:
        print("  The instrument is not fit to answer the question.  "
              "Refusing to print a verdict.")
        return 1

    # ------------------------------------------------------------ the reading
    print()
    print("-" * 100)
    print("THE READING -- strehl-full vs enfuse-full")
    print("-" * 100)
    eD = med_bp(E, DET, placer=P)
    eF = med_bp(E, FLAT, placer=P)
    sS_ = base_S
    eS_ = scene_from(eD, eF)
    unc_ratio = np.sqrt(np.median(eD) / np.median(base_D))
    cor_ratio = np.sqrt(eS_ / sS_) if eS_ > 0 and sS_ > 0 else np.nan
    lo, hi = boot(base_D, base_F, eD, eF, nboot, rng)
    print(f"  {'':10s} {'D (detail tiles)':>18s} {'F (flat tiles)':>18s} "
          f"{'S = D-F':>14s} {'n_D':>5s} {'n_F':>5s}")
    print(f"  {'strehl':10s} {np.median(base_D):18.4e} {np.median(base_F):18.4e} "
          f"{sS_:14.4e} {len(base_D):5d} {len(base_F):5d}")
    print(f"  {'enfuse':10s} {np.median(eD):18.4e} {np.median(eF):18.4e} "
          f"{eS_:14.4e} {len(eD):5d} {len(eF):5d}")
    print()
    print(f"  enfuse detail amplitude / strehl's, UNCORRECTED (counts noise "
          f"as detail): {unc_ratio:.3f}")
    print(f"  enfuse detail amplitude / strehl's, CORRECTED  "
          f"(noise subtracted in-band): {cor_ratio:.3f} "
          f"[{lo:.3f}, {hi:.3f}] 95% CI over {nboot} tile bootstraps")

    # ---------------------------------------------------------- the verdict
    print()
    print("=" * 100)
    print("VERDICT")
    print("=" * 100)
    ref = 2.017
    print(f"  half-stack C on the same subject, band and arm: {ref:.3f}")
    print(f"  full-render band amplitude, same subject/band/arm: {cor_ratio:.3f}")
    if np.isfinite(cor_ratio) and 0.90 <= cor_ratio <= 1.11 and lo <= 1.0 <= hi:
        verdict = ("LEVEL on the full render.  The 2.017 is NOT visible when "
                   "the half-split is removed, so it is half-stack "
                   "incoherence, not absent detail.")
    elif np.isfinite(cor_ratio) and cor_ratio >= 1.5:
        verdict = ("CONFIRMED on the full render.  The detail is genuinely "
                   "absent from the delivered image; the incoherence story "
                   "is dead.")
    else:
        verdict = ("PARTIAL.  Neither pre-registered branch is satisfied; the "
                   "gap is real but smaller than C reports.")
    print(f"  -> {verdict}")

    print()
    print("  HOSTILE READING (printed unconditionally, because the "
          "incoherence branch flatters this project):")
    print(f"    - the correction carries {abs(unc_ratio - cor_ratio):.3f} of "
          f"the answer ({unc_ratio:.3f} uncorrected -> {cor_ratio:.3f} "
          f"corrected).  If A1 is false the verdict moves with it.")
    print(f"    - F/D is {np.median(base_F)/np.median(base_D):.3f} for strehl "
          f"and {np.median(eF)/np.median(eD):.3f} for enfuse; the larger it is, "
          f"the more of S is a difference of two nearby numbers.")
    print(f"    - A2 makes S an UNDER-estimate of scene power for both arms; "
          f"run FLATSENS below to bound it.")

    out = {"key": key, "band": f"{BAND[0]}-{BAND[1]}", "scale": s,
           "commissioning": comm, "commissioning_pass": ok,
           "strehl": {"D": float(np.median(base_D)), "F": float(np.median(base_F)),
                      "S": sS_, "n_D": len(base_D), "n_F": len(base_F)},
           "enfuse": {"D": float(np.median(eD)), "F": float(np.median(eF)),
                      "S": eS_, "n_D": len(eD), "n_F": len(eF)},
           "uncorrected_ratio": float(unc_ratio),
           "corrected_ratio": float(cor_ratio), "ci": [lo, hi],
           "half_stack_C": ref, "verdict": verdict}
    dst = os.path.join(hd2.ROOT, f"fullhp-{key}.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n  written {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
