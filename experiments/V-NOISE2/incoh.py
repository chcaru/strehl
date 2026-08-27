"""INCOH -- the half-to-half discriminator ORCH asked all three lanes to compute.

THE QUESTION.  Fixing the merge exponent caps at 57% of the excess blotch on one
subject, so ~43% is unexplained and three lanes are candidates: depth dilution,
half-stack incoherence (mine), and alignment drift.  ORCH's discriminator: a
noise-driven SELECTION is not reproducible across two independent half-stacks,
whereas ALIGNMENT drift produces coherent error in both halves.

I cannot read the merge's per-pixel frame choice -- crates/strehl-core/src/
merge.rs is owned by a build lane and closed to me.  I read its SIGNATURE
instead, from rasters already on disk, and I read the SAME signature off
`enfuse` built from the SAME linear TIFFs and the SAME half-splits.  That
comparison is the whole design: `enfuse` is a weighted blend, not a hard
selector, so incoherence specific to OUR merge shows up as an excess over it,
while incoherence shared with it is in the inputs both arms consume -- which is
the alignment lane's territory, not mine.

THE BAND, STATED FIRST BECAUSE IT CHANGES WHAT SEC.9 MEANT.  The convicted
plateau is 20-60 px, i.e. 0.0167-0.0500 cyc/px.  Sec.9's LEVEL verdict (1.003)
sits at 0.20-0.25 cyc/px = 4-5 px features.  AN ORDER OF MAGNITUDE APART.
Sec.9 says nothing whatever about the band where the second mechanism is
suspected to live, and this lane had never measured that band.  Both are read
here and always reported side by side.

  COARSE  0.0167-0.0500 cyc/px   20-60 px   the convicted plateau band
  FINE    0.2000-0.2500 cyc/px    4-5 px    sec.9's band, for continuity

At T=256 the COARSE annulus spans radial bins ~4.3 to ~12.8, so it is estimated
from ~8 bins and is correspondingly noisier than FINE.  That is a real
limitation, it is stated rather than hidden, and the bootstrap CI carries it.

THE STATISTIC.  Per tile, per band, for an arm with half-stacks A and B:

    d = (A - B)/2      the half-disagreement field
    m = (A + B)/2      the merged-equivalent field
    phi = P_d / P_m    the incoherent fraction

BOTH P_d AND P_m ARE BAND-LIMITED TO THE SAME ANNULUS.  `P_coh = P_m - P_d` is
the only derived combination and both its terms live in that one annulus.  There
is NO full-band quantity anywhere in this file.  M127's published defect was a
full-band term subtracted from a high-pass total; it cannot recur here by
construction.

A NORMALISATION TRAP, MET AND HANDLED.  h2.contrast_fft divides a crop by its
OWN mean to reach contrast units.  The half-difference field has a mean of ~0,
so normalising it by itself either returns None or divides by noise.  Both P_d
and P_m are therefore normalised by the SAME supplied level -- the mean of m --
which is what makes their ratio meaningful.  `bandpower_at` below takes that
level as an argument precisely so it cannot be forgotten.

PHI IS PERVERSE ALONE, AND THIS WAS PRE-REGISTERED BEFORE MEASURING ANYTHING.
ORCH: "On blotch alone the worst arm wins."  The identical trap applies to phi.
A PLAIN MEAN MAKES THE TWO HALVES AGREE BY DESTROYING DETAIL, so it scores
near-zero phi while being the worst possible merge.  phi is minimised by
catastrophe.  Consequences, both enforced below:

  * phi is NEVER printed without band amplitude sqrt(P_m) on the same pixels.
  * arm PERVERSE (equal blur of BOTH halves) MUST lower phi while lowering
    amplitude.  If the harness cannot see the trap, no reading is issued.

COMMISSIONING (PREREGISTRATION.md sec.10.4), every answer fixed in advance:

  IDENT       A vs A                          phi exactly 0
  NOISE-INC   independent noise per half      phi RISES
  COH-PLANT   the SAME structure in both      phi does NOT rise   <- specificity
  SHIFT       B translated 1 px               phi rises, gradient-localised
  BLOTCH      different 20-60 px blur masks   phi rises, area-localised
  PERVERSE    equal blur of both halves       phi FALLS, amplitude FALLS

Plant potency is bounded at a/S <= 2.2, per sec.9's lesson that a plant can be
TOO POTENT to be informative: past a few times the signal, an arm measures the
estimator's variance rather than its correctness.

THE SIGNATURE SEPARATOR.  Alignment drift concentrates error on GRADIENTS;
selection disagreement concentrates it on AREAS.  So rho = spearman(|d_band|,
|grad m|) separates them, and arms SHIFT and BLOTCH pin the two ends BY
CONSTRUCTION rather than by argument.

BRANCHES, registered as 2ada7413 before this file existed.  R = phi_strehl /
phi_enfuse on DETAIL tiles in COARSE:
  SELECTION  R >= 1.5, CI excludes 1.0, rho at the BLOTCH end -> mine is a real
             second mechanism
  COMMON     R in [0.67, 1.5] -> not specific to our merge; points at the
             alignment lane
  CLEARED    R <= 0.67 -> our merge is MORE half-coherent than enfuse's
"""
import json
import os
import sys

import numpy as np
from scipy.ndimage import shift as ndshift
from scipy.ndimage import uniform_filter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "V-HEADTOHEAD2"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h2                                                        # noqa: E402
from h2h2b import Comp, T                                        # noqa: E402
import hd2                                                       # noqa: E402

COARSE = (1.0 / 60.0, 1.0 / 20.0)
FINE = (0.20, 0.25)
BANDS = (("COARSE", COARSE), ("FINE", FINE))
W = (0.2126, 0.7152, 0.0722)
REG_D = 4
REG_WIN = 8
TARGET_AS = 1.0             # noise plants are sized to this multiple of baseline
BETA = 0.020                 # bounded per sec.9: a plant can be too potent
BLUR = 3                     # PERVERSE/BLOTCH blur radius, px
NBOOT = 2000


def bandpower_at(field, level, lo, hi):
    """Band power of `field` in contrast units defined by a SUPPLIED level.

    h2.contrast_fft normalises a crop by its own mean, which is meaningless for
    a half-DIFFERENCE field whose mean is ~0.  Passing the level in is what
    makes P_d and P_m commensurable, so their ratio is a fraction rather than
    an artifact of two different normalisations.
    """
    t = field.shape[0]
    if not np.isfinite(level) or level <= 1e-9:
        return None
    c = (field / level) * h2.window(t)
    f = np.fft.fft2(c)
    r = h2.radial(t)
    norm = (t * t) ** 2 * (h2.window(t) ** 2).mean()
    p = (np.abs(f) ** 2) / norm
    return float(p[(r >= lo) & (r < hi)].sum())


def band_filter(field, level, lo, hi):
    """The same annulus, back in the spatial domain, for the signature test."""
    t = field.shape[0]
    f = np.fft.fft2(field / level)
    r = h2.radial(t)
    f[~((r >= lo) & (r < hi))] = 0
    return np.real(np.fft.ifft2(f))


def block_mean(a, d):
    h, w = a.shape[0] // d * d, a.shape[1] // d * d
    return a[:h, :w].reshape(h // d, d, w // d, d).mean((1, 3))


class Placer:
    """Integer placement of the comparator's crop against strehl's, copied in
    behaviour from fullhp.py AFTER its DEFECT 1 repair (the bounds test there
    crossed its axes and silently dropped the right 37% of the frame)."""

    def __init__(self, ref, mov, scale):
        from scipy.ndimage import zoom
        self.s = float(scale)
        self.rb = block_mean(ref.g, REG_D)
        mb = block_mean(mov.g, REG_D)
        self.mb = zoom(mb, self.s, order=3) if abs(self.s - 1.0) > 1e-9 else mb

    def place(self, y, x, t):
        s, b = self.s, t // REG_D
        yb, xb = y // REG_D, x // REG_D
        if yb + b > self.rb.shape[0] or xb + b > self.rb.shape[1]:
            return None
        R = self.rb[yb:yb + b, xb:xb + b]
        R = R - R.mean()
        rn = float(np.sqrt((R * R).sum()))
        if rn <= 0:
            return None
        best, bdy, bdx = -2.0, None, None
        for dy in range(-REG_WIN, REG_WIN + 1):
            ay = yb + dy
            if ay < 0 or ay + b > self.mb.shape[0]:
                continue
            for dx in range(-REG_WIN, REG_WIN + 1):
                ax = xb + dx
                if ax < 0 or ax + b > self.mb.shape[1]:
                    continue
                M = self.mb[ay:ay + b, ax:ax + b]
                M = M - M.mean()
                mn = float(np.sqrt((M * M).sum()))
                if mn <= 0:
                    continue
                c = float((R * M).sum()) / (rn * mn)
                if c > best:
                    best, bdy, bdx = c, dy, dx
        if bdy is None:
            return None
        return (int(round((y + bdy * REG_D) / s)),
                int(round((x + bdx * REG_D) / s)))


def pairs(cA, cB, cells, placer=None):
    """Aligned (a, b) crop pairs over a tile population, native pixels only."""
    out = []
    for (y, x) in cells:
        if placer is None:
            y0, x0 = int(y), int(x)
        else:
            pl = placer.place(int(y), int(x), T)
            if pl is None:
                continue
            y0, x0 = pl
        a, na = cA.crop(y0, x0, T)
        b, nb = cB.crop(y0, x0, T)
        if a is None or b is None or na or nb:
            continue
        out.append((a.astype(np.float64), b.astype(np.float64)))
    return out


def phi_of(prs, band, mutate=None, rng=None, want_rho=False):
    """(phi per tile, band amplitude per tile, edge/area concentration).

    phi and amplitude are ALWAYS returned together; sec.10.3 forbids reporting
    one without the other, because phi alone is minimised by the worst merge.

    The third return is the SIGNATURE SEPARATOR.  The first version correlated
    |d_band| against |grad m| over the whole tile and FAILED to separate: SHIFT
    read +0.490 and BLOTCH +0.426 with the unmutated baseline at +0.457, i.e.
    the calibration arms straddled the thing they were supposed to bracket.
    The cause is that |d| tracks |grad m| under EVERY mechanism, because more
    signal means more of everything.  Replaced by a CONCENTRATION ratio, which
    asks the sharper question -- is the disagreement ON the edges or BETWEEN
    them:

        E = mean(d_band^2 | top-tercile gradient)
          / mean(d_band^2 | bottom-tercile gradient)

    Alignment drift displaces edges, so its error lands on them: E large.
    Selection disagreement swaps whole patches, so its error lands in areas:
    E small.  Arms SHIFT and BLOTCH pin the two ends by construction.
    """
    lo, hi = band
    ph, am, rh = [], [], []
    for (a0, b0) in prs:
        a, b = a0, b0
        if mutate is not None:
            a, b = mutate(a0, b0, rng)
        m = (a + b) / 2.0
        d = (a - b) / 2.0
        lev = float(m.mean())
        Pm = bandpower_at(m, lev, lo, hi)
        Pd = bandpower_at(d, lev, lo, hi)
        if Pm is None or Pd is None or not np.isfinite(Pm) or Pm <= 0:
            continue
        ph.append(Pd / Pm)
        am.append(np.sqrt(max(Pm - Pd, 0.0)))
        if want_rho:
            db = band_filter(d, lev, lo, hi) ** 2
            gy, gx = np.gradient(m / lev)
            g = uniform_filter(np.hypot(gy, gx), 8)
            s = (slice(24, -24), slice(24, -24))
            db, g = db[s].ravel(), g[s].ravel()
            q1, q2 = np.percentile(g, [33.3, 66.7])
            hiE, loE = db[g >= q2], db[g <= q1]
            if len(hiE) and len(loE) and loE.mean() > 0:
                rh.append(float(hiE.mean() / loE.mean()))
    return np.array(ph), np.array(am), np.array(rh)


# ------------------------------------------------------------------ mutations
def mut_ident(a, b, rng):
    return a, a.copy()


def mut_noise_inc(beta):
    def f(a, b, rng):
        return (a + rng.normal(0, beta * a.mean(), a.shape),
                b + rng.normal(0, beta * b.mean(), b.shape))
    return f


def mut_coh_plant(beta):
    """The SAME structure into BOTH halves.  Must NOT read as incoherence."""
    def f(a, b, rng):
        s = rng.normal(0, beta * a.mean(), a.shape)
        return a + s, b + s
    return f


def mut_shift(px):
    """Alignment drift: one half translated relative to the other."""
    def f(a, b, rng):
        return a, ndshift(b, (px, px), order=1, mode="nearest")
    return f


def mut_blotch(beta):
    """Selection disagreement: each half blends a blurred copy under its OWN
    coarse random mask, so the halves disagree over 20-60 px patches."""
    def f(a, b, rng):
        out = []
        for im in (a, b):
            lp = uniform_filter(im, BLUR * 4)
            msk = uniform_filter(rng.random(im.shape), 40)
            msk = (msk - msk.mean()) / (msk.std() + 1e-12)
            w = np.clip(0.5 + 2.0 * beta * 25 * msk, 0.0, 1.0)
            out.append(im * (1 - w) + lp * w)
        return out[0], out[1]
    return f


def mut_perverse(a, b, rng):
    """ORCH's trap, instantiated: blur BOTH halves equally.  The image gets
    strictly worse and the halves agree BETTER, so phi must FALL."""
    return uniform_filter(a, BLUR * 4), uniform_filter(b, BLUR * 4)


def plant_beta(band, phi_base, pm_base, target_as=1.0):
    """The noise plant's amplitude, DERIVED per band rather than fixed.

    Sec.9 established that a plant can be too POTENT to be informative.  The
    first run of this file established the mirror image: at a fixed BETA=0.020
    the NOISE-INC arm moved COARSE phi by only +4.7% and failed its own gate.
    The cause is that white noise spreads over the whole frequency plane and the
    annulus captures only its area fraction pi*(hi^2-lo^2) -- 0.00698 for
    COARSE against 0.0707 for FINE, a factor of 10.  A SINGLE BETA IS THEREFORE
    WRONG BY CONSTRUCTION ACROSS TWO BANDS.

    Independent noise of sigma = beta*level in each half puts variance
    beta^2/2 into d after normalisation, of which `frac` lands in the annulus.
    Solving for a plant `target_as` times the baseline disagreement:

        beta = sqrt(2 * target_as * phi_base * pm_base / frac)
    """
    frac = np.pi * (band[1] ** 2 - band[0] ** 2)
    return float(np.sqrt(2.0 * target_as * phi_base * pm_base / frac)), frac


def commission(prs, band, bname, rng_seed=11):
    """Run every arm in ONE band.  A statistic commissioned in one band is not
    commissioned in another -- the plant potency alone differs 10x between
    these two -- so this runs per band and both must pass."""
    base_ph, base_am, base_rh = phi_of(prs, band, want_rho=True)
    b_phi = float(np.median(base_ph))
    b_amp = float(np.median(base_am))
    pm = b_amp ** 2 / max(1.0 - b_phi, 1e-9)
    beta, frac = plant_beta(band, b_phi, pm, TARGET_AS)
    print(f"\n  {bname} baseline: phi {b_phi:.5f}  amplitude {b_amp:.4e}  "
          f"E {np.median(base_rh):.2f}")
    print(f"  {bname} annulus area fraction {frac:.5f}; plant beta DERIVED as "
          f"{beta:.4f} to put the plant at a/S = {TARGET_AS:.1f}")
    print(f"  {'arm':12s} {'phi must':>12s} {'phi':>9s} {'d phi':>8s} "
          f"{'amplitude':>11s} {'d amp':>8s} {'E':>7s}  note")
    arms = [("IDENT", "= 0", mut_ident),
            ("NOISE-INC", "RISE", mut_noise_inc(beta)),
            ("COH-PLANT", "NOT rise", mut_coh_plant(beta)),
            ("SHIFT", "rise", mut_shift(1.0)),
            ("BLOTCH", "rise", mut_blotch(BETA)),
            ("PERVERSE", "FALL", mut_perverse)]
    fails, comm = [], {"_beta": beta, "_phi": b_phi, "_amp": b_amp}
    for label, want, mut in arms:
        ph, am, rh = phi_of(prs, band, mutate=mut,
                            rng=np.random.default_rng(rng_seed), want_rho=True)
        p_, a_ = float(np.median(ph)), float(np.median(am))
        r_ = float(np.median(rh)) if len(rh) else float("nan")
        dp, da = p_ / b_phi - 1, a_ / b_amp - 1
        note = ""
        if label == "IDENT":
            mx = float(np.max(np.abs(ph))) if len(ph) else float("nan")
            ok = mx < 1e-12
            note = f"max|phi| {mx:.2e} over {len(ph)} tiles, not a shortcut"
        elif label == "COH-PLANT":
            ok = dp <= 0.10
            note = "SPECIFICITY: a coherent change must not read as incoherence"
        elif label == "PERVERSE":
            ok = (dp < -0.05) and (da < -0.05)
            note = ("trap visible to the harness" if ok
                    else "ORCH's trap INVISIBLE: worse image did not lower phi")
        else:
            ok = dp > 0.05
            if label == "SHIFT":
                note = "alignment end of the E scale"
            if label == "BLOTCH":
                note = "selection end of the E scale"
        if not ok:
            fails.append(f"{bname}/{label}")
        print(f"  {label:12s} {want:>12s} {p_:9.5f} {dp:+8.1%} "
              f"{a_:11.4e} {da:+8.1%} {r_:7.2f}  {note}")
        comm[label] = {"phi": p_, "d_phi": dp, "amp": a_, "d_amp": da, "E": r_}
    sep = comm["SHIFT"]["E"] / comm["BLOTCH"]["E"]
    comm["_sep"] = sep
    print(f"  separator span: SHIFT E {comm['SHIFT']['E']:.2f} vs BLOTCH E "
          f"{comm['BLOTCH']['E']:.2f} = {sep:.2f}x"
          f"{'' if sep > 1.3 else '  -- TOO NARROW to discriminate, reported as such'}")
    return comm, fails


def boot_ratio(x, y, nboot, rng):
    n, m = len(x), len(y)
    v = np.empty(nboot)
    for i in range(nboot):
        v[i] = (np.median(x[rng.integers(0, n, n)]) /
                np.median(y[rng.integers(0, m, m)]))
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "119"
    arm = os.path.join(hd2.ROOT, key, "arms")
    P = {n: os.path.join(arm, f) for n, f in (
        ("sA", "strehl-A.tiff"), ("sB", "strehl-B.tiff"),
        ("sF", "strehl-full.tiff"), ("eA", "coh-enfuse-A.tif"),
        ("eB", "coh-enfuse-B.tif"), ("eF", "coh-enfuse-full.tif"))}
    for p in P.values():
        if not os.path.exists(p):
            raise SystemExit(f"missing {p}")
    with open(os.path.join(hd2.ROOT, key, "geom-full.json"), encoding="utf-8") as fh:
        g = json.load(fh)
    for c in ("strehl-full_vs_strehl-A", "enfuse-full_vs_enfuse-A"):
        if not g[c].get("control_pass"):
            raise SystemExit(f"geomfull canvas control {c} FAILED -- refusing")
    s = float(g["strehl-full_vs_enfuse-full"]["scale"])

    z = np.load(os.path.join(hd2.ROOT, key, "census.npz"))
    cells, emax = z["cells"], z["emax"]
    flat = [int(i) for i in z["flat"]]
    det = [int(i) for i in np.argsort(emax)[-len(flat):]]
    DET = [tuple(cells[i]) for i in det]
    FLAT = [tuple(cells[i]) for i in flat]

    C = {k: Comp(dict(path=v, weights=W)) for k, v in P.items()}
    pl = Placer(C["sF"], C["eF"], s)
    rng = np.random.default_rng(20260827)

    print("=" * 104)
    print(f"INCOH -- half-to-half discriminator, {key}")
    print("=" * 104)
    print(f"  COARSE {COARSE[0]:.4f}-{COARSE[1]:.4f} cyc/px (20-60 px) -- "
          f"THE CONVICTED PLATEAU BAND, never measured by this lane before")
    print(f"  FINE   {FINE[0]:.4f}-{FINE[1]:.4f} cyc/px (4-5 px)   -- sec.9's "
          f"band, where the LEVEL verdict lives")
    print(f"  content scale {s:.4f}; comparator BAND is scaled, no measured "
          f"pixel is ever resampled")
    print(f"  phi = P_d/P_m, BOTH band-limited to the same annulus.  "
          f"No full-band quantity exists in this file.")

    sD = pairs(C["sA"], C["sB"], DET)
    sF_ = pairs(C["sA"], C["sB"], FLAT)
    eD = pairs(C["eA"], C["eB"], DET, placer=pl)
    eF_ = pairs(C["eA"], C["eB"], FLAT, placer=pl)
    print(f"\n  tiles: strehl {len(sD)} DETAIL / {len(sF_)} FLAT; "
          f"enfuse {len(eD)} DETAIL / {len(eF_)} FLAT")

    # ------------------------------------------------------- commissioning
    print("\n" + "-" * 104)
    print("COMMISSIONING -- strehl's own halves, mutated; every answer fixed "
          "in advance (PREREGISTRATION.md sec.10.4)")
    print("PER BAND, because plant potency differs 10x between them and a "
          "statistic commissioned in one band is not")
    print("commissioned in another.  BOTH must pass before any reading.")
    print("-" * 104)
    comm, fails = {}, []
    for bname, band in BANDS:
        c, f = commission(sD, band, bname)
        comm[bname], _ = c, fails.extend(f)

    print(f"\n  COMMISSIONING: "
          f"{'PASS' if not fails else 'FAIL -- ' + ', '.join(fails)}")
    if fails:
        print("  Refusing to print a reading.  A statistic that cannot see "
              "its own perversity is not a measurement.")
        return 1
    # ------------------------------------------------------------ reading
    print("\n" + "-" * 104)
    print("THE READING -- strehl's half-disagreement against enfuse's, same "
          "tiles, same bands")
    print("-" * 104)
    out = {"key": key, "scale": s, "commissioning": comm,
           "commissioning_pass": True, "bands": {}}
    for bname, band in BANDS:
        print(f"\n  {bname}  {band[0]:.4f}-{band[1]:.4f} cyc/px")
        print(f"    {'arm':10s} {'pop':7s} {'phi':>9s} {'amplitude':>12s} "
              f"{'rho':>7s} {'n':>5s}")
        res = {}
        for aname, dd, ff in (("strehl", sD, sF_), ("enfuse", eD, eF_)):
            for pop, prs in (("DETAIL", dd), ("FLAT", ff)):
                ph, am, rh = phi_of(prs, band, want_rho=(pop == "DETAIL"))
                r_ = float(np.median(rh)) if len(rh) else float("nan")
                print(f"    {aname:10s} {pop:7s} {np.median(ph):9.4f} "
                      f"{np.median(am):12.4e} {r_:+7.3f} {len(ph):5d}")
                res[f"{aname}-{pop}"] = {"phi": float(np.median(ph)),
                                         "amp": float(np.median(am)),
                                         "rho": r_, "n": len(ph),
                                         "_v": ph}
        sp, ep = res["strehl-DETAIL"]["_v"], res["enfuse-DETAIL"]["_v"]
        R = float(np.median(sp) / np.median(ep))
        lo, hi = boot_ratio(sp, ep, NBOOT, rng)
        print(f"    R = phi_strehl / phi_enfuse on DETAIL: "
              f"{R:.3f} [{lo:.3f}, {hi:.3f}] 95% CI")
        for v in res.values():
            v.pop("_v")
        out["bands"][bname] = {"R": R, "ci": [lo, hi], **res}

    Rc = out["bands"]["COARSE"]["R"]
    clo, chi = out["bands"]["COARSE"]["ci"]
    rho_s = out["bands"]["COARSE"]["strehl-DETAIL"]["rho"]
    excl = not (clo <= 1.0 <= chi)
    if Rc >= 1.5 and excl:
        br = "SELECTION"
        say = ("our merge's halves disagree materially more than enfuse's on "
               "the same tiles -- this lane holds a real second mechanism.")
    elif Rc <= 0.67:
        br = "CLEARED"
        say = ("our merge is MORE half-coherent than enfuse's; this lane is "
               "not the second mechanism.")
    else:
        br = "COMMON"
        say = ("the incoherence is not specific to our merge.  It is in the "
               "inputs both arms consume, which points at the ALIGNMENT lane, "
               "not this one.")
    print("\n" + "=" * 104)
    print("VERDICT -- against branches registered as 2ada7413, before this "
          "file existed")
    print("=" * 104)
    print(f"  R (COARSE, the convicted band) = {Rc:.3f} [{clo:.3f}, {chi:.3f}]")
    print(f"  -> {br}: {say}")
    cS, cB = comm["COARSE"]["SHIFT"]["E"], comm["COARSE"]["BLOTCH"]["E"]
    sep = comm["COARSE"]["_sep"]
    print(f"\n  SIGNATURE  strehl E = {rho_s:.2f}, against calibration arms "
          f"SHIFT {cS:.2f} (alignment end) and BLOTCH {cB:.2f} (selection end)")
    if sep <= 1.3:
        print(f"  The calibration arms span only {sep:.2f}x, which is TOO "
              f"NARROW to attribute a mechanism.  The signature is reported "
              f"as UNDETERMINED,")
        print(f"  not read in whichever direction suits.  R above stands on "
              f"its own; E does not qualify it either way.")
    else:
        pos = (rho_s - cB) / (cS - cB)
        print(f"  strehl sits at {pos:.2f} on that scale "
              f"(0 = pure selection, 1 = pure alignment).")
    print(f"\n  MANDATORY PAIRING (sec.10.3): phi is minimised by the worst "
          f"possible merge, so it is never read alone.")
    print(f"  PERVERSE moved phi {comm['COARSE']['PERVERSE']['d_phi']:+.1%} while moving "
          f"amplitude {comm['COARSE']['PERVERSE']['d_amp']:+.1%} -- the trap is real and "
          f"the harness sees it.")
    out["branch"] = br
    dst = os.path.join(hd2.ROOT, f"incoh-{key}.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n  written {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
