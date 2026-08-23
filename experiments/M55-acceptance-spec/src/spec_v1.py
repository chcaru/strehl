"""M55b -- DETAIL METRIC ACCEPTANCE SPECIFICATION, version 1.  EXECUTABLE.

Written and committed BEFORE any candidate metric exists.  That ordering is the
point: a battery written after the candidates can be tuned to them.

A candidate is anything that answers "did this merge deliver less real detail
than that one?".  It must supply a Candidate object (see class docstring) and
must survive every battery below.  Batteries are pass/fail with the thresholds
stated here; nothing in this file may be relaxed to admit a candidate.

Ten batteries.  B0 B1 B2 B3 B4 B5 B6 B7 B8 B9.  Kill conditions are in
KILL_CONDITIONS and are quoted verbatim in the report.

Provenance of every threshold is in docs/research/M55-acceptance-spec.md.
Nothing here imports a candidate; references in ref_metrics.py exist only to
prove the battery has power (rule 39) and that it is passable at all.
"""
import numpy as np

F_SIG = 0.2762
NBIN = 64
N = 512


# --------------------------------------------------------------------------
# THRESHOLDS.  Provenance for every one is in the report; none may be relaxed.
TH = dict(
    # B1 monotonicity
    b1_mtf_hi=0.98, b1_mtf_lo=0.01, b1_min_points=16, b1_max_ratio=1.35,
    b1_nrep=8,
    # B2 homogeneity: the smallest real photometric difference measured between
    # two merge configurations of the same stack (fact 704) is 11.7 %.
    b2_gain=0.117,
    # B3 nuisance leverage
    b3_unpinned_max=0.10, b3_pinned_max=1.00,
    # B4 power
    b4_reject_frac=0.90, b4_decades=2.0,
    # B5 sign and range
    b5_inrange_frac=1.00,
    # B6 real data
    b6_min_stacks=6, b6_min_rois=4, b6_quantile=0.10,
    # The corpus offers only THREE distinct subjects across the six held-out
    # stacks (see RENAMED below).  Six stacks is not six scenes.
    b6_min_subjects=3,
    # B7 stability
    b7_reps=(1, 2, 4, 8, 16, 32, 64), b7_max_headline_swing=0.05,
    # B8 calibration
    b8_factors=(0.5, 0.9, 1.1, 2.0),
    # Plant noise, in electrons per half-merge.  DERIVED from the corpus: a
    # half-merge of ~16 accepted frames at 250 DN with g = 1.14469 DN/e- has
    # shot sd 14.8 e- per frame -> 3.7 e- after averaging, plus 1.47/4 e- read.
    # A battery run at ZERO noise makes the two half-merges the SAME image and
    # silently degenerates every cross-power statistic into an auto-power; that
    # defect was found in this battery by its own PR27 falsifier.
    plant_noise_e=3.7,
    # B1c bounded adversary.  The shared component a NON-GENERATIVE merge can
    # inject between two disjoint half-stacks is bounded by the sensor's fixed
    # pattern: 0.2888 DN MEASURED (fact 698) against a reference merge high-pass
    # sd of 59.47 DN MEASURED -> 0.486 %.
    b1_cap_frac=0.004857,
    # B9 null discipline: a reading with |z| below this against the roll-null
    # is not a reading.  MEASURED in E12: a contiguous split of a real stack
    # gives |z| <= 1.91 on all six cells -- indistinguishable from unrelated
    # images -- while a parity split gives z = 2.2 to 34.7.
    b9_min_z=3.0, b9_nroll=48, b9_minshift=64,
)

KILL_CONDITIONS = {
 "B0": "Any declared field missing, or the candidate ships no executable property test.",
 "B1": "Any inversion in the candidate's response to decreasing true MTF whose magnitude "
       "exceeds the candidate's own declared no_claim_floor, anywhere in MTF in "
       "[0.01, 0.98], on arm B1a (plain blur) or arm B1c (blur plus a shared component "
       "capped at the measured non-generative bound of 0.486 % of the reference "
       "high-pass sd).  Arm B1b (unbounded shared component at matched cost) is "
       "RECORDED as a declared blind spot and kills only a candidate that claims "
       "safety against generative merges.",
 "B2": "A photometric gain of 11.7 % applied to ONE input alone moves |d| by more than the "
       "candidate's own no_claim_floor; or swapping the two inputs moves the value by more "
       "than the no_claim_floor.",
 "B3": "Any nuisance the operator must choose and the spec does not pin has leverage > 0.10 "
       "relative to the reference signal step; or any pinned nuisance has leverage > 1.00.",
 "B4": "The candidate's own confirmation check accepts a planted wrong answer anywhere across "
       "two decades; or the candidate passes a battery that a known-bad reference also passes.",
 "B5": "Any held-out cell returns a value outside the declared range with Status Ok; or the "
       "comparison denominator is not bounded away from zero in every held-out cell.",
 "B6": "The 10th-percentile held-out cell fails the candidate's own decision rule on a merge "
       "pair whose true ordering is known; fewer than 6 stacks, fewer than 4 ROIs per stack, "
       "or fewer than 3 distinct SUBJECTS.  The pass fraction must additionally hold WITHIN "
       "each subject group: the held-out set contains three stacks of one subject and two of "
       "another, so a pooled fraction can be carried by one scene.  Every cell must declare "
       "its stack and ROI; b6_rollup enforces this and a candidate that cannot supply it "
       "has not run B6.",
 "B7": "The headline score moves by more than 0.05 across the REPS sweep with everything else "
       "held fixed; or the null term is within 2 standard errors of zero at the largest REPS "
       "while a ratio against it is quoted.",
 "B8": "The verdict of any other battery changes when a consumed calibration constant is "
       "perturbed by a factor of 2.",
 "B9": "Any real-data reading is quoted without its roll-null z, or is quoted at |z| < 3.0.",
}


# --------------------------------------------------------------------------
# Ring machinery.  n, nbin and f_sig are PINNED by the spec (see B3).
# --------------------------------------------------------------------------
def rings(n, nbin=NBIN):
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2)
    e = np.linspace(0, n // 2, nbin + 1)
    out = []
    for i in range(nbin):
        m = (rr >= e[i]) & (rr < e[i + 1])
        if int(m.sum()) < 8:
            continue
        out.append((m, int(m.sum()), 0.5 * (e[i] + e[i + 1]) / n))
    return out


_RC = {}


def ring_at(n, f=F_SIG, nbin=NBIN):
    k = (n, f, nbin)
    if k not in _RC:
        rs = rings(n, nbin)
        _RC[k] = rs[int(np.argmin([abs(c - f) for (_, _, c) in rs]))]
    return _RC[k]


def spec2(a):
    n = a.shape[0]
    k = np.arange(n)
    w1 = 0.5 - 0.5 * np.cos(2 * np.pi * k / (n - 1))
    return np.fft.fftshift(np.fft.fft2((a - a.mean()) * np.outer(w1, w1)))


def gauss_mtf(sd, f=F_SIG):
    """True MTF of a Gaussian blur of sd px at frequency f.  DERIVED."""
    return float(np.exp(-2.0 * np.pi ** 2 * sd ** 2 * f ** 2))


def sd_for_mtf(mtf, f=F_SIG):
    """Inverse of gauss_mtf.  The reference SIGNAL STEP is mtf = 0.90, which is
    sd = 0.2645 px.  M46's 0.05 px step is an MTF loss of 0.376 % (MEASURED)."""
    return float(np.sqrt(-np.log(mtf) / (2.0 * np.pi ** 2 * f ** 2)))


def blur(img, sd):
    if sd <= 0:
        return img.astype(np.float64).copy()
    n = img.shape[0]
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    H = np.exp(-2.0 * np.pi ** 2 * sd ** 2 * (fy ** 2 + fx ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(img) * H))


def hp_sd(img, sd=2.0):
    """Candidate-INDEPENDENT cost proxy: sd of a high-pass residual.  This is
    M46's own matched-cost currency, kept so the compensated arm B1b is matched
    in the same units the corpus already argued about."""
    return float(np.std(img - blur(img, sd)))


def roll_null(a, b, nroll=None, minshift=None, seed=5):
    """Empirical null for ANY pairwise statistic on (a, b): roll b by a large
    offset.  Preserves marginals, window and ring exactly; destroys pixel
    correspondence.  MEASURED (E12): a contiguous half-stack split sits INSIDE
    this null on 6 of 6 real cells, so this null is not a formality."""
    nroll = TH["b9_nroll"] if nroll is None else nroll
    minshift = TH["b9_minshift"] if minshift is None else minshift
    n = a.shape[0]
    rng = np.random.default_rng(seed)
    out = []
    while len(out) < nroll:
        dy, dx = int(rng.integers(0, n)), int(rng.integers(0, n))
        if min(dy, n - dy) < minshift or min(dx, n - dx) < minshift:
            continue
        out.append(np.roll(b, (dy, dx), axis=(0, 1)))
    return out


# --------------------------------------------------------------------------
# The plant.  Rule 34: the plant must NOT supply the constant the candidate
# consumes, and must not normalise by it.  `gain` comes from the caller and B8
# perturbs it from outside, so a scale-invariant statistic cannot hide here.
# --------------------------------------------------------------------------

class Plant:
    """Two half-merges of a synthetic scene.

    latent      broadband texture, frozen per seed
    mtf         true MTF at F_SIG delivered to BOTH halves
    noise_e     per-half noise in electrons (converted with `gain`, which B8
                perturbs from outside; the plant never normalises by it)
    drift       fraction of the latent that differs between the two halves --
                the effect M46's plants could not express
    common      amplitude of a fixed texture added to BOTH halves after the
                blur.  This is the PM_M adversary of fact 703.
    """

    def __init__(self, n=N, seed=0, gain=1.14469, level=250.0):
        self.n, self.gain, self.level = n, gain, level
        r = np.random.default_rng(1000 + seed)
        f = np.fft.fftfreq(n)
        rr = np.sqrt(f[:, None] ** 2 + f[None, :] ** 2)
        rr[0, 0] = 1e-6
        sh = np.fft.fft2(r.standard_normal((n, n))) * rr ** -1.1
        self.latent = np.real(np.fft.ifft2(sh))
        self.latent /= self.latent.std()
        sh2 = np.fft.fft2(r.standard_normal((n, n))) * rr ** -0.3
        self.alt = np.real(np.fft.ifft2(sh2)); self.alt /= self.alt.std()
        sh3 = np.fft.fft2(r.standard_normal((n, n))) * rr ** -0.6
        self.fixed = np.real(np.fft.ifft2(sh3)); self.fixed /= self.fixed.std()

    def pair(self, mtf=1.0, noise_e=0.0, drift=0.0, common=0.0, rep=0,
             gain_a=1.0, gain_b=1.0, contrast=40.0):
        sd = sd_for_mtf(mtf) if mtf < 1.0 else 0.0
        la = (1.0 - drift) * self.latent + drift * self.alt
        lb = self.latent
        a = self.level + contrast * blur(la, sd) + common * self.fixed
        b = self.level + contrast * blur(lb, sd) + common * self.fixed
        if noise_e > 0:
            r = np.random.default_rng(7000000 + 1000 * rep + int(10000.0 * mtf))
            a = a + r.standard_normal(a.shape) * (noise_e * self.gain)
            b = b + r.standard_normal(b.shape) * (noise_e * self.gain)
        return a * gain_a, b * gain_b

    def match_common(self, mtf, target_hp, noise_e=0.0, rep=0, tol=1e-4):
        """Solve the shared-texture amplitude so the merged high-pass cost
        returns to `target_hp`.  This is the fact-703 adversary, generalised."""
        lo, hi = 0.0, 400.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            a, b = self.pair(mtf=mtf, noise_e=noise_e, common=mid, rep=rep)
            if hp_sd(0.5 * (a + b)) < target_hp:
                lo = mid
            else:
                hi = mid
            if hi - lo < tol:
                break
        return 0.5 * (lo + hi)


# --------------------------------------------------------------------------
# The candidate contract.  B0 enforces every field; a missing field is a kill.
# --------------------------------------------------------------------------
REQUIRED_FIELDS = (
    "name", "version", "consumes_calibration", "uses_ground_truth",
    "declared_range", "no_claim_floor", "decision_threshold",
    "failure_direction", "nuisances", "property_tests")

class Candidate:
    """Subclass and fill in every REQUIRED_FIELD, then implement value().

    value(a, b, ctx) -> (float, status_str).  status must be "Ok" only when the
    reading is admissible; anything else must NOT be read as a number (B5).

    compare(ref, test) -> d.  Default (ref - test)/|ref|.  Override for a
    bounded metric.  `failure_direction` says which sign of d means detail lost.

    nuisances: dict name -> list of admissible values the operator could pick.
    Every entry is scored by B3 and must be declared pinned or unpinned.

    property_tests: path to an executable file asserting monotonicity,
    homogeneity, swap invariance and the negative branch.  Golden vectors pin
    values; they do not pin properties (fact 711).
    """
    name = version = None
    consumes_calibration = ()
    uses_ground_truth = False
    declared_range = None
    no_claim_floor = None
    decision_threshold = None
    failure_direction = None
    nuisances = {}
    property_tests = None

    def value(self, a, b, ctx=None):
        raise NotImplementedError

    def compare(self, ref, test):
        return (ref - test) / abs(ref) if ref != 0 else float("nan")

    def d_signed(self, ref, test):
        d = self.compare(ref, test)
        return d if self.failure_direction == "positive" else -d


# --------------------------------------------------------------------------
# B1 -- monotonicity in true resolution.
# --------------------------------------------------------------------------
def _mtf_grid():
    hi, lo, k = TH["b1_mtf_hi"], TH["b1_mtf_lo"], TH["b1_max_ratio"]
    n = max(TH["b1_min_points"], int(np.ceil(np.log(hi / lo) / np.log(k))) + 1)
    return list(np.geomspace(hi, lo, n))


def _inversion_depth(seq):
    """seq is d_signed ordered by DECREASING true MTF; it must be
    non-decreasing.  Returns the deepest violation, 0.0 if monotone."""
    worst, running_max = 0.0, -np.inf
    for v in seq:
        running_max = max(running_max, v)
        worst = max(worst, running_max - v)
    return float(worst)


def b0_declaration(cand):
    missing = [f for f in REQUIRED_FIELDS if getattr(cand, f, None) in (None, "")]
    return dict(passed=not missing, kill=f"missing {missing}" if missing else None,
                missing=missing)


def b1_monotonicity(cand, plant, noise_e=None, nrep=None):
    """Three arms, three threat models.

    B1a  plain blur.                      KILL on any resolved inversion.
    B1c  blur + a shared component capped at the measured non-generative bound
         (fact 698).                      KILL on any resolved inversion.
    B1b  blur + an UNBOUNDED shared component solved to restore the high-pass
         cost exactly -- fact 703's adversary.  A merge can only do this if it
         injects structure common to both half-stacks, i.e. if it is generative.
         RECORDED as a declared blind spot; kills only a candidate that claims
         safety against generative merges.

    RESOLVED means the inversion exceeds BOTH the candidate's own no_claim_floor
    AND three times the standard error of `d` over `nrep` noise realisations.
    A single realisation manufactures inversions out of noise: this battery's
    own first calibration run did exactly that (0.0026 on a plain blur, where
    the noiseless value is 0.0), which is rule 39 turned on the battery itself.
    """
    noise_e = TH["plant_noise_e"] if noise_e is None else noise_e
    nrep = TH["b1_nrep"] if nrep is None else nrep
    grid = _mtf_grid()
    arms = {"plain": [], "capped": [], "compensated": []}
    ses = {"plain": [], "capped": [], "compensated": []}
    cap = None
    for m in grid:
        acc = {k: [] for k in arms}
        for rep in range(nrep):
            ra, rb = plant.pair(mtf=1.0, noise_e=noise_e, rep=rep)
            ref = cand.value(ra, rb)[0]
            target = hp_sd(0.5 * (ra + rb))
            if cap is None:
                cap = TH["b1_cap_frac"] * target
            ta, tb = plant.pair(mtf=m, noise_e=noise_e, rep=rep)
            acc["plain"].append(cand.d_signed(ref, cand.value(ta, tb)[0]))
            ka, kb = plant.pair(mtf=m, noise_e=noise_e, common=cap, rep=rep)
            acc["capped"].append(cand.d_signed(ref, cand.value(ka, kb)[0]))
            c = plant.match_common(m, target, noise_e=noise_e, rep=rep)
            ca, cb = plant.pair(mtf=m, noise_e=noise_e, common=c, rep=rep)
            acc["compensated"].append(cand.d_signed(ref, cand.value(ca, cb)[0]))
        for k in arms:
            v = np.array(acc[k], float)
            arms[k].append(float(v.mean()))
            ses[k].append(float(v.std(ddof=1) / np.sqrt(nrep)) if nrep > 1 else 0.0)
    out = {"grid": grid, "cap": float(cap), "noise_e": float(noise_e), "nrep": int(nrep)}
    out.update(arms)
    for k in arms:
        out["inv_" + ("comp" if k == "compensated" else k)] = _inversion_depth(arms[k])
        out["se_" + k] = float(np.mean(ses[k]))
    res_thresh = max(cand.no_claim_floor, 3.0 * max(out["se_plain"], out["se_capped"]))
    out["resolve_threshold"] = float(res_thresh)
    worst = max(out["inv_plain"], out["inv_capped"])
    out["passed"] = worst <= res_thresh
    out["blind_spot_generative"] = bool(out["inv_comp"] > max(cand.no_claim_floor,
                                                             3.0 * out["se_compensated"]))
    out["kill"] = None if out["passed"] else (
        f"resolved inversion depth {worst:.6g} on arm "
        f"{'B1a plain' if out['inv_plain'] >= out['inv_capped'] else 'B1c capped'}"
        f" exceeds max(no_claim_floor {cand.no_claim_floor:.6g}"
        f", 3 SE) = {res_thresh:.6g}  ({worst / res_thresh:.1f}x)")
    return out


def b2_homogeneity(cand, plant, rep=0, noise_e=None):
    noise_e = TH["plant_noise_e"] if noise_e is None else noise_e
    g = 1.0 + TH["b2_gain"]
    a, b = plant.pair(mtf=1.0, noise_e=noise_e, rep=rep)
    ref = cand.value(a, b)[0]
    d_both = cand.compare(ref, cand.value(g * a, g * b)[0])
    d_one = cand.compare(ref, cand.value(g * a, b)[0])
    d_swap = cand.compare(ref, cand.value(b, a)[0])
    p_both = np.log(abs(cand.value(3 * a, 3 * b)[0] / ref)) / np.log(3.0)
    p_one = np.log(abs(cand.value(3 * a, b)[0] / ref)) / np.log(3.0)
    worst = max(abs(d_both), abs(d_one), abs(d_swap))
    return dict(passed=worst <= cand.no_claim_floor,
                kill=None if worst <= cand.no_claim_floor else (
                    f"an 11.7% one-sided gain (or a swap) moves |d| to {worst:.6g}, "
                    f"{worst / cand.no_claim_floor:.1f}x the no_claim_floor"),
                d_both=float(d_both), d_one=float(d_one), d_swap=float(d_swap),
                degree_both=float(p_both), degree_one=float(p_one), gain=g)


def b3_leverage(cand, signal_d, nuisance_ds, pinned):
    """signal_d: |d| for the reference signal step (true MTF 1.00 -> 0.90).
    nuisance_ds: {name: max |d| across that nuisance's admissible values}."""
    rows, kill = {}, None
    for k, v in nuisance_ds.items():
        L = abs(v) / abs(signal_d) if signal_d else float("inf")
        lim = TH["b3_pinned_max"] if pinned.get(k) else TH["b3_unpinned_max"]
        ok = L <= lim
        rows[k] = dict(leverage=float(L), limit=lim, pinned=bool(pinned.get(k)), passed=ok)
        if not ok and kill is None:
            kill = (f"nuisance '{k}' has leverage {L:.1f}x the reference signal step, "
                    f"over its limit of {lim:.2f} "
                    f"({'pinned' if pinned.get(k) else 'UNPINNED'})")
    return dict(passed=kill is None, kill=kill, signal_d=float(signal_d), rows=rows)


def b4_power(cand, plant, nrep=32, noise_e=None):
    """Specificity AND sensitivity, both measured, per rule 39.
    A test that fires on a no-change pair, or misses a real 10% MTF loss,
    has not passed."""
    noise_e = TH["plant_noise_e"] if noise_e is None else noise_e
    fa = det = 0
    for r in range(nrep):
        a0, b0 = plant.pair(mtf=1.0, noise_e=noise_e, rep=r)
        a1, b1 = plant.pair(mtf=1.0, noise_e=noise_e, rep=r + 500)
        if abs(cand.compare(cand.value(a0, b0)[0], cand.value(a1, b1)[0])) > (
                cand.decision_threshold):
            fa += 1
        ta, tb = plant.pair(mtf=0.9, noise_e=noise_e, rep=r)
        d = cand.d_signed(cand.value(a0, b0)[0], cand.value(ta, tb)[0])
        if d > cand.decision_threshold:
            det += 1
    spec_ = 1.0 - fa / nrep
    sens = det / nrep
    ok = spec_ >= TH["b4_reject_frac"] and sens >= TH["b4_reject_frac"]
    return dict(passed=ok, specificity=spec_, sensitivity=sens, nrep=nrep,
                kill=None if ok else (
                    f"specificity {spec_:.2f}, sensitivity {sens:.2f}; both must be >= "
                    f"{TH['b4_reject_frac']:.2f}"))


def b5_sign_range(cand, values):
    """values: iterable of (label, value, status)."""
    lo, hi = cand.declared_range
    bad = [(l, v, s) for (l, v, s) in values if s == "Ok" and not (lo <= v <= hi)]
    near0 = [(l, v, s) for (l, v, s) in values if s == "Ok" and abs(v) <= 0.0]
    ok = not bad and not near0
    return dict(passed=ok, out_of_range=bad, zero_reference=near0,
                kill=None if ok else (
                    f"{len(bad)} cells outside the declared range {cand.declared_range} with Status Ok; "
                    f"{len(near0)} cells with a zero reference"))


def b7_stability(cand, plant, blur_mtf=0.9, noise_hi=None, noise_lo=None):
    """The cheapest and most damning test in the corpus (fact 695).  Vary ONLY
    the repetition count and watch the headline move."""
    noise_hi = 2.0 * TH["plant_noise_e"] if noise_hi is None else noise_hi
    noise_lo = TH["plant_noise_e"] if noise_lo is None else noise_lo
    rows = {}
    for R in TH["b7_reps"]:
        ds, dn = [], []
        for r in range(R):
            a, b = plant.pair(mtf=1.0, noise_e=noise_hi, rep=r)
            ref = cand.value(a, b)[0]
            ta, tb = plant.pair(mtf=blur_mtf, noise_e=noise_hi, rep=r)
            ds.append(cand.d_signed(ref, cand.value(ta, tb)[0]))
            na, nb = plant.pair(mtf=1.0, noise_e=noise_lo, rep=r)
            dn.append(cand.d_signed(ref, cand.value(na, nb)[0]))
        ds, dn = np.array(ds), np.array(dn)
        se = float(dn.std(ddof=1) / np.sqrt(R)) if R > 1 else float("nan")
        S = abs(ds.mean()) / (abs(ds.mean()) + abs(dn.mean())) if (abs(ds.mean()) + abs(dn.mean())) else float("nan")
        rows[R] = dict(d_signal=float(ds.mean()), d_null=float(dn.mean()),
                       se_null=se, S=float(S),
                       null_over_se=(abs(dn.mean()) / se) if (se and se == se and se > 0) else float("nan"))
    S = [v["S"] for v in rows.values() if v["S"] == v["S"]]
    swing = float(max(S) - min(S)) if S else float("nan")
    big = rows[TH["b7_reps"][-1]]
    null_dead = big["null_over_se"] < 2.0
    ok = swing <= TH["b7_max_headline_swing"] and not null_dead
    return dict(passed=ok, swing=swing, rows=rows, null_consistent_with_zero=bool(null_dead),
                kill=None if ok else (
                    f"headline S swings {swing:.3f} across REPS (limit "
                    f"{TH['b7_max_headline_swing']})"
                    + ("; and the null is within 2 SE of zero at the largest REPS, so any ratio against it is void"
                       if null_dead else "")))


def b9_null_z(cand, a, b, seed=5):
    v = cand.value(a, b)[0]
    nul = np.array([cand.value(a, br)[0] for br in roll_null(a, b, seed=seed)])
    sd = float(nul.std(ddof=1))
    z = (v - float(nul.mean())) / sd if sd > 0 else float("inf")
    return dict(value=float(v), null_mean=float(nul.mean()), null_sd=sd, z=float(z),
                passed=abs(z) >= TH["b9_min_z"],
                kill=None if abs(z) >= TH["b9_min_z"] else (
                    f"|z| = {abs(z):.2f} against the roll-null, below {TH['b9_min_z']}; this is not a reading"))


# --------------------------------------------------------------------------
# B6 -- the held-out real-data battery.  These six stacks are NAMED HERE,
# before any candidate exists, and were never scored by this file's author.
# The ROIs are fixed by a rule so that no ROI can be chosen on its result.
# The split is PINNED to parity: a contiguous split reads inside the roll-null
# --------------------------------------------------------------------------
# RENAME, 2026-08-23, mid-milestone: the owner renamed five of these directories.
# Same files, same counts, same bytes; new names.  The mapping below was NOT taken
# on trust -- e13_rename_check.py re-read EXIF from the new directories and matched
# each to exactly one pre-rename fingerprint in out/heldout.json (n, ISO and exposure
# of first and last frame, f-number, lens), unique across all six.  Old names are kept
# here so that nobody later reads a pre-rename result as a different stack.
RENAMED = {"131MSDCF": "wrapped-text-1", "133MSDCF": "wrapped-text-2",
           "134MSDCF": "bee-1", "135MSDCF": "bee-2", "136MSDCF": "bee-3"}
HELD_OUT = ("coffee-bean", "wrapped-text-1", "wrapped-text-2", "bee-1", "bee-2", "bee-3")
# The rename revealed something the old numeric names concealed and that B6 was
# written without: these six stacks are only THREE subjects.  bee-1/-3 are ISO 100
# and bee-2 is ISO 400 of the same subject; wrapped-text-1/-2 are ISO 100 and 400 of
# another.  A pooled pass fraction over 24 cells can therefore be carried by one scene.
SUBJECT_OF = {"coffee-bean": "coffee-bean",
              "wrapped-text-1": "wrapped-text", "wrapped-text-2": "wrapped-text",
              "bee-1": "bee", "bee-2": "bee", "bee-3": "bee"}
DEV_STACKS = ("112MSDCF", "113MSDCF", "foam", "109MSDCF", "119MSDCF", "coffee-bubbles")
QUAD_W, QUAD_H = 2344, 3514
ROI_FRACTIONS = ((0.25, 0.25), (0.75, 0.25), (0.50, 0.50), (0.50, 0.80))
B6_FRAMES = 64
B6_SPLIT = "parity"


def roi_rule(side=512, pad=32):
    """ROIs by rule, not by choice.  Four per stack, same for every stack."""
    out = []
    for (fx, fy) in ROI_FRACTIONS:
        x = int(round(fx * (QUAD_W - side)))
        y = int(round(fy * (QUAD_H - side)))
        x = min(max(x, pad), QUAD_W - side - pad)
        y = min(max(y, pad), QUAD_H - side - pad)
        out.append((x, y, side, side))
    return out


def b6_cell(cand, a, b, sd=None):
    """One held-out cell.  The true ordering is KNOWN because the test pair is
    the reference pair with a real, measured blur applied: true MTF 0.90."""
    sd = sd_for_mtf(0.9) if sd is None else sd
    ref, st = cand.value(a, b)
    ta, tb = blur(a, sd), blur(b, sd)
    tst, st2 = cand.value(ta, tb)
    d = cand.d_signed(ref, tst)
    z = b9_null_z(cand, a, b)
    detected = d > cand.decision_threshold
    wrong_sign = -d > cand.decision_threshold
    return dict(ref=float(ref), test=float(tst), d=float(d), status=st, status_test=st2,
                z=z["z"], z_pass=z["passed"], detected=bool(detected),
                wrong_sign=bool(wrong_sign), passed=bool(detected and z["passed"]))


def b6_rollup(cells):
    """Roll up held-out cells.  Every cell must carry `stack` and `roi` in
    addition to what b6_cell returns -- the caller adds them, because only the
    caller knows which stack it loaded.  Coverage is ENFORCED here and not
    merely stated in KILL_CONDITIONS: an unenforced kill condition is fact
    711's disease one level up, and this function had it until 2026-08-23.
    """
    n = len(cells)
    frac = sum(c["passed"] for c in cells) / n if n else 0.0
    wrong = [c for c in cells if c["wrong_sign"]]
    reasons = []
    undeclared = [i for i, c in enumerate(cells) if "stack" not in c or "roi" not in c]
    if undeclared:
        reasons.append(f"{len(undeclared)} cells do not declare stack and roi")
    stacks = sorted({c["stack"] for c in cells if "stack" in c})
    subjects = sorted({SUBJECT_OF.get(st, st) for st in stacks})
    per_stack = {st: sum(1 for c in cells if c.get("stack") == st) for st in stacks}
    thin = {st: k for st, k in per_stack.items() if k < TH["b6_min_rois"]}
    if len(stacks) < TH["b6_min_stacks"]:
        reasons.append(f"{len(stacks)} stacks (need {TH['b6_min_stacks']})")
    if len(subjects) < TH["b6_min_subjects"]:
        reasons.append(f"{len(subjects)} distinct subjects (need {TH['b6_min_subjects']})")
    if thin:
        reasons.append(f"stacks with fewer than {TH['b6_min_rois']} ROIs: {thin}")
    by_sub = {}
    for c in cells:
        by_sub.setdefault(SUBJECT_OF.get(c.get("stack"), c.get("stack")), []).append(c)
    sub_frac = {k: (sum(x["passed"] for x in v) / len(v)) for k, v in by_sub.items()}
    need = 1.0 - TH["b6_quantile"]
    weak = {k: v for k, v in sub_frac.items() if v < need}
    if weak:
        reasons.append(f"subject groups below {100 * need:.0f}%: "
                       + ", ".join(f"{k} {100 * v:.0f}%" for k, v in sorted(weak.items())))
    if frac < need:
        reasons.append(f"{100 * frac:.0f}% of cells pass (need {100 * need:.0f}%)")
    if wrong:
        reasons.append(f"{len(wrong)} cells report the WRONG DIRECTION above the "
                       f"decision threshold")
    ok = not reasons
    return dict(passed=ok, n_cells=n, frac_passed=frac, n_wrong_sign=len(wrong),
                n_stacks=len(stacks), n_subjects=len(subjects),
                subject_frac=sub_frac, cells_per_stack=per_stack,
                kill=None if ok else "; ".join(reasons))


# --------------------------------------------------------------------------
# B8 -- calibration sensitivity.  A candidate MAY consume the sensor model,
# but then every constant it names is perturbed by x0.5, x0.9, x1.1 and x2.0
# and no battery's verdict may change.  x2.0 is not arbitrary: it is the size
# of the gain error that survived twelve milestones of this project.
# --------------------------------------------------------------------------
def b8_calibration(cand, plant, run_batteries):
    if not cand.consumes_calibration:
        return dict(passed=True, kill=None, skipped=True,
                    note="candidate consumes no calibration constant")
    base = run_batteries(cand, plant)
    rows, kill = {}, None
    for k in cand.consumes_calibration:
        for f in TH["b8_factors"]:
            old = getattr(cand, k)
            try:
                setattr(cand, k, old * f)
                r = run_batteries(cand, plant)
            finally:
                setattr(cand, k, old)
            same = all(r[bn]["passed"] == base[bn]["passed"] for bn in base)
            rows[f"{k}x{f}"] = dict(same_verdict=bool(same))
            if not same and kill is None:
                kill = (f"perturbing calibration constant '{k}' by x{f}"
                        " changes the verdict of another battery")
    return dict(passed=kill is None, kill=kill, rows=rows, skipped=False)


# --------------------------------------------------------------------------
# Runners.  B3/B5/B6/B9 need real data and are driven by the caller.
# --------------------------------------------------------------------------
PLANT_BATTERIES = ("B0", "B1", "B2", "B4", "B7")


def run_plant_batteries(cand, plant):
    return {"B0": b0_declaration(cand),
            "B1": b1_monotonicity(cand, plant),
            "B2": b2_homogeneity(cand, plant),
            "B4": b4_power(cand, plant),
            "B7": b7_stability(cand, plant)}


def verdict(results):
    dead = [k for (k, v) in results.items() if not v.get("passed")]
    return ("ACCEPTED", dead) if not dead else ("REJECTED on " + ", ".join(sorted(dead)), dead)


def _summary():
    """Print the normative content of the spec: thresholds and kill conditions."""
    out = ["M55b acceptance specification v1 -- normative thresholds", ""]
    for k in sorted(TH):
        out.append("    %-24s %s" % (k, TH[k]))
    out.append("")
    out.append("KILL CONDITIONS")
    for k in sorted(KILL_CONDITIONS):
        out.append("    %s: %s" % (k, KILL_CONDITIONS[k]))
    out.append("")
    out.append("HELD-OUT STACKS (never scored by the spec's author): %s" % (", ".join(HELD_OUT),))
    out.append("ROI RULE: %s" % (roi_rule(),))
    out.append("B6_FRAMES = %d   B6_SPLIT = %r" % (B6_FRAMES, B6_SPLIT))
    return "\n".join(out)


if __name__ == "__main__":
    print(_summary())
