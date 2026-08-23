"""02 -- M61 PRE-REGISTRATION: conversion gain across the dual-gain switch.

=============================================================================
THIS DOCSTRING IS THE PRE-REGISTRATION.  It is committed before the script is
run.  Nothing below the docstring reads a result and changes a threshold.
=============================================================================

THE QUESTION
------------
`crates/strehl-core/src/profile.rs` converts DN to electrons with one straight
line, `gain_dn_per_e = max(iso, base_iso) / gain_divisor`, `gain_divisor =
436.8`, running unbroken across `second_base_iso = 400`.  The A7C II is a dual
conversion gain sensor.  `gain_divisor` was calibrated by a photon transfer
curve at ISO 160 (M25 fact 200 / SYNTHESIS fact 550), which is in the LOW gain
mode.  Every ISO >= 400 is extrapolation from the other mode and has never
been measured.

M48c fact 17 DERIVED, from the dark-current excess of 13,630 recurrent hot
pixels read through this relation, that the DN->electron conversion above
ISO 400 is wrong relative to the one below it by **2.174x** (6.6855 e- implied
below, 3.0765 e- above, for the same pixels at the same 1/100 s exposure).
M48c did not act on it, called a PTC at ISO 500 or 1000 "the highest-value
follow-up in this report" (fact 22, question 1), and noted that nothing has
run one.  This script is that PTC.

THE TWO HYPOTHESES, WRITTEN DOWN BEFORE THE RUN
-----------------------------------------------
Let r(ISO) = g_measured(ISO) / g_model(ISO), g_model = max(ISO,100)/436.8.

  H0  (the shipped model is right across the switch)
      r is the same constant at every ISO; in particular
      r(500)/r(low-mode plateau) = 1.000 and r(1000)/r(plateau) = 1.000.

  H1  (M48c fact 17, with the ISO-160 PTC taken as pinning the low mode)
      r(ISO >= 400) / r(ISO < 400) = 1/2.174 = **0.460**.

  H2  (the same step, attributed the other way: the HIGH mode is right and the
      low mode is the extrapolation)
      r(ISO < 400) / r(ISO >= 400) = 0.460.  H2 is distinguishable from H1
      only through the ISO-160 control, which is where the shipped constant
      was actually calibrated, so the control is load-bearing twice over.

These are 2.17x apart.  A measurement good to +-10% separates them by more
than 5x its own uncertainty, so the experiment has power if and only if the
estimator is good to ~10%.  That is what the control establishes.

THE ESTIMATOR (M61-E1)
----------------------
Photon transfer from a TEMPORAL adjacent-frame difference, per CFA plane, on
raw DN, never demosaiced and never binned across a quad.

For an adjacent pair (k, k+1) and one plane, with BLACK = 512 subtracted:

    d = F_k - F_(k+1)          s = (F_k + F_(k+1)) / 2

On 8x8 tiles of one plane (so neighbouring samples are two sensor pixels
apart and share no photosite):

    m = mean(s)   v = var(d, ddof=1) / 2   u = var(s, ddof=1)

`v` is an unbiased estimate of the per-frame temporal variance PLUS a
scene-change term, `m` of the level, and `u` of the scene texture plus
sigma^2/2.

Why a temporal difference rather than M25's spatial one:
  * PRNU / DSNU / any fixed pattern cancels exactly, so the quadratic FPN term
    that inflates a spatial PTC slope at high level is gone (M48b measured rho
    on this body; M50 measured the pattern isotropic).
  * A per-frame photometric level change eps (M24: 0.91%-11.70% peak-to-peak)
    contributes eps^2 * u to v -- i.e. it is proportional to the covariate `u`
    and is removed by the same machinery that removes texture.
  * A sub-pixel warp delta (M29: adjacent-frame warp 0.07-0.22 green px) and
    the focus step both contribute a term proportional to local structure, so
    they too load on `u`.

The key statistical property this design is built on, and it is the reason the
selection below does not bias the answer:

    for independent per-frame noise, (n_k + n_k+1)/2 and (n_k - n_k+1) are
    uncorrelated jointly-Gaussian variables, hence independent, hence the tile
    sample variance `u` is INDEPENDENT of the tile sample variance `v`.

So selecting tiles on `u` -- however aggressively -- leaves E[v] unbiased for
the noise part while suppressing the scene part.  This is exactly what M25's
estimator could not do: it took a low percentile OF THE VARIANCE ITSELF, which
is biased low by the chi-square percentile factor (5th pctile of chi2_63/63 is
0.726), and that bias then fights the texture bias in the opposite direction.
M25's own caveat -- "only the photon-transfer slope is trustworthy here, the
intercept is inflated by residual scene texture" -- is that fight showing.

Three level-resolved variance estimators are computed, and their disagreement
is a component of the reported uncertainty:

  A  "q20 mean"     : within a level bin, take the mean of v over the tiles in
                      the lowest 20% of u in that bin.
  B  "u-regression" : within a level bin, OLS of v on u over the tiles with
                      u <= median(u) in that bin, giving v = a + b*u.  Since
                      u = T + sigma^2/2 with T the texture variance, and
                      v = sigma^2 + beta*T, the zero-texture value is
                      sigma^2 = a / (1 - b/2).  This extrapolates the scene
                      term to zero rather than merely selecting against it.
  C  "q5 mean"      : as A with the lowest 5% of u.

PTC fit: 16 log-spaced level bins between the 1st and 99.5th percentile of
tile mean level, bins with fewer than 200 usable tiles dropped.  Fit
sigma^2_i = g * m_i + c by weighted least squares, weights n_i / fitted_i^2
from a first unweighted pass (using the observed v_i in the weights would
correlate the weights with the errors).  **The reported quantity is the SLOPE
g.  The intercept is reported but is NOT used for anything**, per M25's
finding that the intercept on this kind of data is untrustworthy, and per the
brief.  A forced-zero-intercept variant is printed as a check that the answer
does not depend on the intercept.

Tile rejection, fixed in advance:
  * any pixel in either frame at or above WHITE = 15360 raw (profile's white
    level; the container goes to 16383 and M26 records that split)
  * tile mean level below 3 DN above black
A whole PAIR is rejected if the two frames' plane means differ by more than 2%
(a photometric jump big enough that the eps^2*u term stops being small).

Pairs: up to 24 adjacent pairs per stack, evenly spaced through the stack.
Planes: all four of R, G1, G2, B, reported separately -- conversion gain is a
property of the readout, not of the colour filter, so four planes at four
different level ranges are four quasi-independent estimates of one number.

THE CONTROL, AND THE ACCEPTANCE CRITERION -- BOTH FIXED HERE
------------------------------------------------------------
PRIMARY CONTROL: ISO 160, `D:\personal\macro\109MSDCF`, 22 frames.  This is
where `gain_divisor` was actually calibrated by a real PTC (M25 fact 200
measured 0.3273 DN/e- against the relation's 0.36630, -10.7%, and SYNTHESIS
fact 585 adjudicated that -10.7% as licensed to stand).

  ACCEPTANCE: the estimator PASSES its control iff, on 109MSDCF at ISO 160,
  the pooled-over-planes slope satisfies

      0.80 <= g_measured / 0.36630 <= 1.20

  i.e. r(160) within +-20%.  The band is set to contain both candidate truths
  for the low mode (the relation, 1.00, and M25's PTC, 0.893) with room, while
  excluding H1's 0.460 by more than a factor of 1.7.

  IF THE CONTROL FAILS, THE MILESTONE STOPS AND REPORTS THAT.  No ISO 500 or
  ISO 1000 number is to be quoted from a failed estimator.

SECOND CONTROL (also low mode): ISO 50, `119MSDCF` (33 frames) and
`coffee-bean` (105 frames), against g_model = 0.22894 (the pulled-ISO floor
fixed by M25 fact 200 / M4 section 8.2).  Same +-20% band.  This is a second
control and not a gate: it is at a different level regime and a different
subject, so it tests level-dependence of the estimator rather than the
calibration.

THIRD CONTROL (low mode, subjects nothing has measured): ISO 100 `bee-1`,
`bee-3`, `wrapped-text-1`, against g_model = 0.22894.

TEST ARMS: ISO 500 `112MSDCF` (79), `113MSDCF` (63); ISO 1000
`coffee-bubbles` (19), `foam` (100).  ISO 400 `bee-2` (299),
`wrapped-text-2` (120) are additional high-mode arms.

`foam` is known to have subject motion and `coffee-bubbles` bubble motion.
Both inflate v, i.e. both bias the measured gain UPWARD, i.e. both bias
AGAINST H1.  That direction is stated here so it cannot be claimed afterwards:
if the result comes out near H1 anyway, motion is not the explanation; if it
comes out near H0, motion is a live alternative and the ISO-500 stacks (no
known motion) are the arms that decide.

THE MATCHED-PAIR ARM -- the one that cancels the most nuisances
--------------------------------------------------------------
`bee-2` (ISO 400, 1/20 s) and `bee-3` (ISO 100, 1/5 s) are the same subject on
the same rig 4 minutes apart, with ISO x time identical at 20 ISO*s, and their
measured plane means agree to 0.2% (2445.3 vs 2436.6 DN, script 01).  They sit
on opposite sides of the switch at a MATCHED DN LEVEL with MATCHED TEXTURE.
The ratio g(bee-2)/g(bee-3) is therefore free of any level-dependent or
texture-dependent bias in the estimator.

  H0 predicts g(bee-2)/g(bee-3) = 400/100 = 4.000
  H1 predicts 4.000 / 2.174 = 1.840

`wrapped-text-2` (ISO 400) / `wrapped-text-1` (ISO 100) is the same test on a
second subject; their levels are not matched as tightly (1811.8 vs 1461.6 DN).

THE HEADLINE STATISTIC
----------------------
r_high / r_low, where r_low is the mean of r over the low-mode stacks and
r_high is r at ISO 500 and at ISO 1000 separately.  Any multiplicative bias of
the estimator that does not depend on ISO cancels in this ratio.  H0 predicts
1.000; H1 predicts 0.460.

UNCERTAINTY -- from re-drawing and disagreement, not from propagation
--------------------------------------------------------------------
Reported as the spread of r over:
  * the four CFA planes,
  * the two stacks at each test ISO,
  * the three variance estimators A / B / C,
  * two disjoint halves of the pair list within each stack.
The quoted uncertainty on each r is the standard deviation over those
re-draws, and the quoted uncertainty on r_high/r_low is their quadrature sum.
No formal error propagation is used anywhere.

WHAT WOULD MAKE THIS AN ARTEFACT (rule 20: name the failing input first)
------------------------------------------------------------------------
1. A level-dependent bias.  The high-ISO stacks sit at lower DN than the
   low-ISO ones.  Checked by (a) refitting every stack over the COMMON level
   window 50-800 DN, (b) the matched-level bee-2/bee-3 arm, (c) reporting the
   per-bin residuals of the PTC line.
2. A texture-to-noise-dependent bias.  At fixed DN a high-ISO frame holds
   fewer electrons, so scene texture is a smaller multiple of the noise, so an
   estimator that leaks texture leaks LESS at high ISO -- which fakes H1.
   Checked by the A/B/C spread (they leak texture by very different amounts)
   and by the matched-texture bee arm.
3. Subject motion, which fakes H0.  Checked by the clean ISO-500 stacks and by
   comparing `foam` (motion) against `coffee-bubbles` (motion) against them.
4. The estimator being unable to see a gain error at all.  Checked by script
   03, a synthetic positive control that plants a known g -- including a
   planted g_model/2.174 -- and requires recovery.  Per rule 34 that plant
   validates the OPERATOR and cannot validate the calibration; it is here to
   prove the test can fail, not to prove the sensor.

DISCLOSURE, WRITTEN BEFORE THE RUN
----------------------------------
Scripts 00 and 01 were exploratory and were run before this pre-registration.
Script 01 printed, per stack, the ratio of the measured adjacent-frame
difference sigma to the shipped model's sigma on the smoothest 10% of tiles,
and I HAD SEEN THOSE NUMBERS when I wrote this file.  They are a single-level
check, not a slope, and they are reproduced by this script's section 5 so a
reader can see what I saw.  The acceptance band above is set on the CONTROL,
whose expected value was fixed by M25 and SYNTHESIS long before this
milestone; the H0/H1 decision rule is a 2.17x separation that no amount of
peeking at a 3% effect could steer.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m61-ptc-high-iso/src/02-ptc-ladder.py
"""

from __future__ import annotations

import glob
import os
import time

import numpy as np

CORPUS = r"D:\personal\macro"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "ptc-ladder.txt")
CSV = os.path.join(HERE, "..", "data", "ptc-ladder.csv")

BLACK = 512.0
WHITE = 15360.0
GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
SECOND_BASE_ISO = 400.0
RN_LOW = 4.20
RN_HIGH = 1.2392

TILE = 8
MAX_PAIRS = 24
N_BINS = 16
MIN_TILES_PER_BIN = 200
Q_A = 20.0
Q_C = 5.0
PAIR_LEVEL_TOL = 0.02
MIN_LEVEL_DN = 3.0
COMMON_WINDOW = (50.0, 800.0)

CONTROL = ("109MSDCF", 160.0)
CONTROL_BAND = (0.80, 1.20)

STACKS = [
    ("109MSDCF", 160.0, "CONTROL   low mode, where gain_divisor was calibrated"),
    ("119MSDCF", 50.0, "control2  low mode (pulled ISO)"),
    ("coffee-bean", 50.0, "control2  low mode (pulled ISO)"),
    ("bee-1", 100.0, "control3  low mode"),
    ("bee-3", 100.0, "control3  low mode"),
    ("wrapped-text-1", 100.0, "control3  low mode"),
    ("bee-2", 400.0, "TEST      high mode, matched to bee-3"),
    ("wrapped-text-2", 400.0, "TEST      high mode"),
    ("112MSDCF", 500.0, "TEST      high mode"),
    ("113MSDCF", 500.0, "TEST      high mode"),
    ("coffee-bubbles", 1000.0, "TEST      high mode (bubble motion)"),
    ("foam", 1000.0, "TEST      high mode (subject motion)"),
]
PLANES = ("R", "G1", "G2", "B")
LINES: list[str] = []
ROWS: list[tuple] = []


def say(s: str = "") -> None:
    print(s, flush=True)
    LINES.append(s)


def g_model(iso: float) -> float:
    return max(iso, BASE_ISO) / GAIN_DIVISOR


def rn_model(iso: float) -> float:
    return RN_HIGH if iso >= SECOND_BASE_ISO else RN_LOW


def plane_of(raw: np.ndarray, name: str) -> np.ndarray:
    if name == "R":
        return raw[0::2, 0::2]
    if name == "G1":
        return raw[0::2, 1::2]
    if name == "G2":
        return raw[1::2, 0::2]
    return raw[1::2, 1::2]


def read_raw(path: str) -> np.ndarray:
    """Copy inside the `with`, per rule 32 -- the view dies with the context."""
    import rawpy

    with rawpy.imread(path) as rr:
        return np.asarray(rr.raw_image_visible, dtype=np.uint16).copy()


def tile_stats(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, ...]:
    """(m, v, u, ok) per TILE x TILE tile of one plane, both frames raw DN."""
    h, w = a.shape
    h -= h % TILE
    w -= w % TILE
    af = a[:h, :w].astype(np.float32) - BLACK
    bf = b[:h, :w].astype(np.float32) - BLACK
    good = (a[:h, :w] < WHITE) & (b[:h, :w] < WHITE)
    sh = (h // TILE, TILE, w // TILE, TILE)
    d = (af - bf).reshape(sh)
    s = (0.5 * (af + bf)).reshape(sh)
    ok = good.reshape(sh).all(axis=(1, 3)).ravel()
    m = s.mean(axis=(1, 3)).ravel()
    v = s.var(axis=(1, 3), ddof=1).ravel()
    dv = d.var(axis=(1, 3), ddof=1).ravel() / 2.0
    ok &= m > MIN_LEVEL_DN
    return m, dv, v, ok


def bin_estimates(m, v, u, lo, hi):
    """Level-resolved variance by the three pre-registered estimators."""
    edges = np.geomspace(max(lo, MIN_LEVEL_DN), hi, N_BINS + 1)
    out = []
    for i in range(N_BINS):
        sel = (m >= edges[i]) & (m < edges[i + 1])
        n = int(sel.sum())
        if n < MIN_TILES_PER_BIN:
            continue
        mb, vb, ub = m[sel], v[sel], u[sel]
        ta = ub <= np.percentile(ub, Q_A)
        tc = ub <= np.percentile(ub, Q_C)
        va = float(vb[ta].mean())
        ma = float(mb[ta].mean())
        vc = float(vb[tc].mean())
        mc = float(mb[tc].mean())
        tb = ub <= np.percentile(ub, 50.0)
        x, y = ub[tb], vb[tb]
        xm, ym = x.mean(), y.mean()
        den = float(((x - xm) ** 2).sum())
        if den <= 0:
            vbb, mbb = va, ma
        else:
            beta = float(((x - xm) * (y - ym)).sum() / den)
            icpt = float(ym - beta * xm)
            vbb = icpt / (1.0 - beta / 2.0) if beta < 1.9 else np.nan
            mbb = float(mb[tb].mean())
        out.append((n, ma, va, mbb, vbb, mc, vc))
    return out


def wls_slope(x, y, w):
    A = np.vstack([x, np.ones_like(x)]).T
    W = np.diag(w)
    try:
        coef = np.linalg.solve(A.T @ W @ A, A.T @ W @ y)
    except np.linalg.LinAlgError:
        return np.nan, np.nan
    return float(coef[0]), float(coef[1])


def fit_ptc(pts):
    """pts = list of (n, m, v).  Two-pass WLS; returns (slope, icpt, resid%)."""
    pts = [p for p in pts if np.isfinite(p[1]) and np.isfinite(p[2])]
    if len(pts) < 4:
        return np.nan, np.nan, np.nan, 0
    n = np.array([p[0] for p in pts], float)
    x = np.array([p[1] for p in pts], float)
    y = np.array([p[2] for p in pts], float)
    s0, c0 = wls_slope(x, y, n)
    fit = s0 * x + c0
    w = n / np.maximum(fit, 1e-6) ** 2
    s1, c1 = wls_slope(x, y, w)
    pred = s1 * x + c1
    resid = float(np.max(np.abs(y / pred - 1.0))) * 100.0
    return s1, c1, resid, len(pts)


def zero_icpt_slope(pts):
    pts = [p for p in pts if np.isfinite(p[1]) and np.isfinite(p[2])]
    if len(pts) < 3:
        return np.nan
    n = np.array([p[0] for p in pts], float)
    x = np.array([p[1] for p in pts], float)
    y = np.array([p[2] for p in pts], float)
    w = n / np.maximum(x, 1e-6) ** 2
    return float((w * x * y).sum() / (w * x * x).sum())


def measure_stack(name: str, iso: float) -> dict:
    d = os.path.join(CORPUS, name)
    fs = sorted(glob.glob(os.path.join(d, "*.ARW")))
    npairs = min(MAX_PAIRS, len(fs) - 1)
    starts = np.unique(np.linspace(0, len(fs) - 2, npairs).astype(int))
    acc = {p: {"m": [], "v": [], "u": [], "half": []} for p in PLANES}
    skipped = 0
    for j, k in enumerate(starts):
        a = read_raw(fs[k])
        b = read_raw(fs[k + 1])
        for p in PLANES:
            pa, pb = plane_of(a, p), plane_of(b, p)
            ma = float(pa.mean()) - BLACK
            mb = float(pb.mean()) - BLACK
            if ma <= 0 or mb <= 0 or abs(ma / mb - 1.0) > PAIR_LEVEL_TOL:
                skipped += 1
                continue
            m, v, u, ok = tile_stats(pa, pb)
            acc[p]["m"].append(m[ok].astype(np.float32))
            acc[p]["v"].append(v[ok].astype(np.float32))
            acc[p]["u"].append(u[ok].astype(np.float32))
            acc[p]["half"].append(
                np.full(int(ok.sum()), j % 2, dtype=np.int8))
        del a, b
    res = {"name": name, "iso": iso, "npairs": int(starts.size),
           "skipped": skipped, "planes": {}}
    for p in PLANES:
        if not acc[p]["m"]:
            continue
        m = np.concatenate(acc[p]["m"])
        v = np.concatenate(acc[p]["v"])
        u = np.concatenate(acc[p]["u"])
        hf = np.concatenate(acc[p]["half"])
        lo = float(np.percentile(m, 1.0))
        hi = float(np.percentile(m, 99.5))
        est = bin_estimates(m, v, u, lo, hi)
        arms = {}
        for tag, i_m, i_v in (("A", 1, 2), ("B", 3, 4), ("C", 5, 6)):
            pts = [(e[0], e[i_m], e[i_v]) for e in est]
            s, c, rr, nb = fit_ptc(pts)
            arms[tag] = {"g": s, "c": c, "resid": rr, "nbins": nb,
                         "g0": zero_icpt_slope(pts)}
        cw = (m >= COMMON_WINDOW[0]) & (m <= COMMON_WINDOW[1])
        if cw.sum() > MIN_TILES_PER_BIN * 4:
            estc = bin_estimates(m[cw], v[cw], u[cw], *COMMON_WINDOW)
            arms["common"] = {"g": fit_ptc([(e[0], e[1], e[2])
                                            for e in estc])[0]}
        else:
            arms["common"] = {"g": np.nan}
        halves = []
        for hv in (0, 1):
            sel = hf == hv
            if sel.sum() < MIN_TILES_PER_BIN * 4:
                halves.append(np.nan)
                continue
            eh = bin_estimates(m[sel], v[sel], u[sel], lo, hi)
            halves.append(fit_ptc([(e[0], e[1], e[2]) for e in eh])[0])
        arms["halves"] = halves
        arms["lo"], arms["hi"], arms["ntiles"] = lo, hi, int(m.size)
        smooth = u <= np.percentile(u, 10.0)
        pred = np.sqrt(g_model(iso) * m[smooth] + (rn_model(iso)
                                                   * g_model(iso)) ** 2)
        arms["sigma_ratio"] = float(np.median(np.sqrt(v[smooth]) / pred))
        res["planes"][p] = arms
    return res


def report_stack(res: dict) -> float:
    gm = g_model(res["iso"])
    say(f"--- {res['name']:<15} ISO {res['iso']:>6.0f}   "
        f"g_model {gm:.5f} DN/e-   pairs {res['npairs']} "
        f"(plane-pairs skipped {res['skipped']})")
    say(f"    {'plane':<5} {'levels DN':>15} {'gA':>8} {'gB':>8} {'gC':>8} "
        f"{'gA0':>8} {'gcw':>8} {'rA':>7} {'resid%':>7} {'sig/mod':>8}")
    rs = []
    for p in PLANES:
        if p not in res["planes"]:
            continue
        a = res["planes"][p]
        rA = a["A"]["g"] / gm
        rs.append(rA)
        say(f"    {p:<5} {a['lo']:>7.0f}-{a['hi']:<7.0f} "
            f"{a['A']['g']:>8.4f} {a['B']['g']:>8.4f} {a['C']['g']:>8.4f} "
            f"{a['A']['g0']:>8.4f} {a['common']['g']:>8.4f} "
            f"{rA:>7.3f} {a['A']['resid']:>7.2f} {a['sigma_ratio']:>8.3f}")
        ROWS.append((res["name"], res["iso"], p, gm, a["A"]["g"], a["B"]["g"],
                     a["C"]["g"], a["A"]["g0"], a["common"]["g"],
                     a["halves"][0], a["halves"][1], a["A"]["c"],
                     a["A"]["resid"], a["sigma_ratio"], a["ntiles"]))
    r = float(np.nanmean(rs))
    sd = float(np.nanstd(rs))
    say(f"    => r = g_measured / g_model = {r:.4f} +- {sd:.4f} "
        f"(sd over {len(rs)} planes, estimator A)")
    say()
    return r


def main() -> int:
    t0 = time.time()
    say("M61 -- conversion gain across the dual-gain switch, measured")
    say(f"estimator M61-E1, pre-registered in this file's docstring")
    say(f"TILE={TILE}  MAX_PAIRS={MAX_PAIRS}  N_BINS={N_BINS}  "
        f"qA={Q_A}  qC={Q_C}  black={BLACK}  white={WHITE}")
    say()

    say("=" * 78)
    say("SECTION 1 -- THE CONTROL, RUN AND REPORTED FIRST (rule 9)")
    say("=" * 78)
    cres = measure_stack(*CONTROL)
    r_ctrl = report_stack(cres)
    ok = CONTROL_BAND[0] <= r_ctrl <= CONTROL_BAND[1]
    say(f"pre-registered band {CONTROL_BAND[0]:.2f} <= r <= "
        f"{CONTROL_BAND[1]:.2f}   measured r = {r_ctrl:.4f}   "
        f"=> {'PASS' if ok else 'FAIL'}")
    say()
    if not ok:
        say("THE ESTIMATOR FAILED ITS CONTROL.  Per the pre-registration the "
            "milestone stops here and no test-arm number is quoted.")
        with open(OUT, "w", encoding="utf-8") as fh:
            fh.write("\n".join(LINES) + "\n")
        return 1

    say("=" * 78)
    say("SECTION 2 -- THE LADDER")
    say("=" * 78)
    results = {CONTROL[0]: (cres, r_ctrl)}
    for name, iso, label in STACKS:
        if name == CONTROL[0]:
            continue
        say(f"[{label}]")
        res = measure_stack(name, iso)
        results[name] = (res, report_stack(res))

    say("=" * 78)
    say("SECTION 3 -- r BY ISO")
    say("=" * 78)
    by_iso: dict[float, list[tuple[str, float]]] = {}
    for name, iso, _ in STACKS:
        by_iso.setdefault(iso, []).append((name, results[name][1]))
    for iso in sorted(by_iso):
        vals = [v for _, v in by_iso[iso]]
        say(f"  ISO {iso:>6.0f}  g_model {g_model(iso):.5f}   "
            f"r = {np.mean(vals):.4f}   "
            f"({', '.join(f'{n} {v:.4f}' for n, v in by_iso[iso])})")
    low = [v for iso in by_iso if iso < SECOND_BASE_ISO
           for _, v in by_iso[iso]]
    r_low = float(np.mean(low))
    sd_low = float(np.std(low))
    say()
    say(f"  low-mode plateau  r_low  = {r_low:.4f} +- {sd_low:.4f} "
        f"(sd over {len(low)} stacks)")
    for iso in sorted(i for i in by_iso if i >= SECOND_BASE_ISO):
        vals = [v for _, v in by_iso[iso]]
        rh = float(np.mean(vals))
        sd = float(np.std(vals))
        say(f"  ISO {iso:>6.0f}         r_high = {rh:.4f} +- {sd:.4f}    "
            f"r_high / r_low = {rh / r_low:.4f}      "
            f"H0 predicts 1.000, H1 predicts 0.460")
    say()

    say("=" * 78)
    say("SECTION 4 -- THE MATCHED-PAIR ARM")
    say("=" * 78)
    for hi_name, lo_name in (("bee-2", "bee-3"), ("wrapped-text-2",
                                                  "wrapped-text-1")):
        gh = np.nanmean([results[hi_name][0]["planes"][p]["A"]["g"]
                         for p in PLANES])
        gl = np.nanmean([results[lo_name][0]["planes"][p]["A"]["g"]
                         for p in PLANES])
        iso_ratio = results[hi_name][0]["iso"] / results[lo_name][0]["iso"]
        say(f"  {hi_name} / {lo_name}: measured g ratio "
            f"{gh / gl:.4f}   ISO ratio {iso_ratio:.1f}   "
            f"H0 predicts {iso_ratio:.3f}, H1 predicts "
            f"{iso_ratio / 2.174:.3f}")
    say()

    say("=" * 78)
    say("SECTION 5 -- the single-level check script 01 printed, reproduced")
    say("=" * 78)
    say("  median over smoothest-10% tiles of "
        "sqrt(var(d)/2) / model sigma; H0 ~ 1.00, H1 ~ 0.68 above ISO 400")
    for name, iso, _ in STACKS:
        v = [results[name][0]["planes"][p]["sigma_ratio"] for p in PLANES
             if p in results[name][0]["planes"]]
        say(f"  {name:<15} ISO {iso:>6.0f}   {np.mean(v):.4f}")
    say()
    say(f"[{time.time() - t0:.0f}s]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    with open(CSV, "w", encoding="utf-8") as fh:
        fh.write("stack,iso,plane,g_model,gA,gB,gC,gA_zero_icpt,g_common,"
                 "g_half0,g_half1,icptA,resid_pct,sigma_ratio,ntiles\n")
        for r in ROWS:
            fh.write(",".join(str(x) for x in r) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    print(f"wrote {os.path.normpath(CSV)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
