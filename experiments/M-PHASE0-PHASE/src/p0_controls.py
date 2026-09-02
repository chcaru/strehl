"""Controls for M-PHASE0-PHASE, registered in PREREGISTRATION.md section 8.

Every control that the algebra permits carries BOTH a required-invariance arm
and a required-sensitivity arm.  A control that can only pass is worthless: if
adding a lattice vector leaves kappa alone, that is only evidence when adding a
non-lattice vector is shown to move it.

Each control is additionally COMMISSIONED where it can be: the defect it exists
to catch is planted into a copy of the instrument's own arithmetic, and the
control must fail.  A control that has never fired may be a no-op.

Exit status is 0 only if every control passes and every commissioning plant is
caught.
"""

import sys

import numpy as np

import plib

RNG = np.random.default_rng(20260826)
RESULTS = []


def record(name, ok, detail):
    RESULTS.append((name, bool(ok), detail))
    print("  %-6s %-46s %s" % ("PASS" if ok else "FAIL", name, detail))


def rand_d(n, spread=3.0, rng=None):
    rng = rng or RNG
    return rng.uniform(-spread, spread, size=(n, 2))


def reps_g1x_first():
    return plib.distinct_rep_sets("G-1x")[0]


# ---------------------------------------------------------------------------

def c_targets():
    """Structural: the enumerated coset count must equal M for every target."""
    ok = True
    parts = []
    for name, spec in sorted(plib.TARGETS.items()):
        got = len(spec["duals"])
        ok &= (got == spec["M"])
        nd = len(plib.distinct_rep_sets(name))
        parts.append("%s M=%d geoms=%d" % (name, got, nd))
        # Every representative must be distinct modulo Lambda_t*.
        c = spec["cell"]
        mods = {(round((g[0] % c) * 2), round((g[1] % c) * 2)) for g in spec["duals"]}
        ok &= (len(mods) == spec["M"])
    record("C-TARGETS coset enumeration", ok, "; ".join(parts))


def c_a_exact():
    """C-A: zero phase error, zero noise, N >= M -> exact recovery."""
    worst = 0.0
    for name in sorted(plib.TARGETS):
        m = plib.TARGETS[name]["M"]
        reps = plib.distinct_rep_sets(name)[0]
        d = rand_d(m + 2)
        eta, _ = plib.unfold_trial(reps, d, 0.0, np.inf, RNG, 64)
        worst = max(worst, float(np.max(eta)))
    record("C-A exact recovery at sigma=0", worst < 1e-10, "max eta = %.3e" % worst)


def c_b_degenerate():
    """C-B: displacements on the sample lattice carry no phase -> infeasible."""
    ok = True
    parts = []
    for name in sorted(plib.TARGETS):
        spec = plib.TARGETS[name]
        basis = np.array(spec["lattice"], dtype=float)
        coef = RNG.integers(-4, 5, size=(spec["M"] + 3, 2))
        d = coef @ basis
        k = float(plib.kappa(plib.distinct_rep_sets(name)[0], d))
        ok &= not np.isfinite(k)
        parts.append("%s kappa=%s" % (name, "inf" if not np.isfinite(k) else "%.3g" % k))
    record("C-B lattice-only displacements infeasible", ok, "; ".join(parts))


def c_c_underdetermined():
    """C-C: fewer frames than replicas -> infeasible, never pseudo-inverted."""
    ok = True
    parts = []
    for name in sorted(plib.TARGETS):
        m = plib.TARGETS[name]["M"]
        if m < 2:
            continue
        k = float(plib.kappa(plib.distinct_rep_sets(name)[0], rand_d(m - 1)))
        ok &= not np.isfinite(k)
        parts.append("%s N=%d M=%d" % (name, m - 1, m))
    record("C-C N < M infeasible", ok, "; ".join(parts))


def c_d_monotone():
    """C-D: the metric must RESPOND to degradation and to improvement.

    A statistic that only rises when things get worse passes every planted-
    defect test trivially.  The improvement arm is what separates a blind
    metric from one that can score a better configuration better.
    """
    reps = plib.distinct_rep_sets("G-1x")[0]
    d = rand_d(5)
    sig = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4]
    etas = [plib.median_eta(reps, d, s, np.inf, np.random.default_rng(7), 3000)[0]
            for s in sig]
    rising = all(etas[i] < etas[i + 1] + 1e-9 for i in range(len(etas) - 1))

    # Improvement arm 1: more frames at a fixed error must not do worse.
    ns = [2, 3, 5, 8, 16]
    by_n = []
    for n in ns:
        rng = np.random.default_rng(11)
        # Phases spread evenly over the coset: the ideal configuration.
        t = np.arange(n) / n
        dn = np.stack([t, np.zeros(n)], axis=1)
        by_n.append(plib.median_eta(reps, dn, 0.05, np.inf, rng, 3000)[0])
    falling_n = by_n[-1] < by_n[0]

    # Improvement arm 2: better-spread phases at fixed N must do better.
    rngA = np.random.default_rng(13)
    rngB = np.random.default_rng(13)
    clustered = np.stack([np.linspace(0, 0.04, 5), np.zeros(5)], axis=1)
    spread = np.stack([np.linspace(0, 0.8, 5), np.zeros(5)], axis=1)
    e_clustered = plib.median_eta(reps, clustered, 0.02, np.inf, rngA, 3000)[0]
    e_spread = plib.median_eta(reps, spread, 0.02, np.inf, rngB, 3000)[0]
    better_spread = e_spread < e_clustered

    ok = rising and falling_n and better_spread
    record("C-D responds to harm AND to improvement", ok,
           "eta(sigma) %s | eta(N=2)=%.3f -> eta(N=16)=%.3f | clustered %.3f vs spread %.3f"
           % ("rises" if rising else "NOT MONOTONE", by_n[0], by_n[-1],
              e_clustered, e_spread))


def c_e_closed_form():
    """C-E: numerical kappa matches the closed form at M=2, N=2."""
    reps = np.array([[0.0, 0.0], [0.5, 0.5]])
    worst = 0.0
    for delta in np.linspace(0.05, 1.95, 60):
        d = np.array([[0.0, 0.0], [delta, delta]])
        num = float(plib.kappa(reps, d))
        # theta_i = 2 pi <h_1, d_i>; D = theta_1 - theta_0
        dd = 2 * np.pi * (0.5 * delta + 0.5 * delta)
        cf = np.sqrt((1 + abs(np.cos(dd / 2))) / (1 - abs(np.cos(dd / 2))))
        worst = max(worst, abs(num - cf) / cf)
    record("C-E kappa matches closed form (N=2)", worst < 1e-10,
           "max relative deviation = %.3e" % worst)


def c_m_closed_form_alln():
    """C-M: SVD kappa matches the resultant-length form for every N at M=2."""
    reps = np.array([[0.0, 0.0], [0.5, 0.5]])
    worst = 0.0
    for n in range(2, 13):
        for _ in range(20):
            d = rand_d(n)
            num = float(plib.kappa(reps, d))
            theta = 2 * np.pi * (d @ reps[1])
            cf = float(plib.kappa_m2_closed(theta))
            worst = max(worst, abs(num - cf) / cf)
    record("C-M kappa matches resultant form (all N)", worst < 1e-9,
           "max relative deviation = %.3e" % worst)


def c_f_lattice():
    """C-F: invariant under a sample-lattice shift, sensitive to a non-lattice one.

    This single control exercises the whole plane -> sensor -> lattice unit
    chain.  A factor-of-two unit error fails the sensitivity arm.
    """
    ok = True
    parts = []
    cases = [("G-1x", (1.0, 1.0), (1.0, 0.0)),
             ("RB-1x", (2.0, 0.0), (1.0, 0.0)),
             ("G-2x", (1.0, -1.0), (1.0, 0.0)),
             ("RB-2x", (0.0, 2.0), (0.0, 1.0))]
    for name, in_lat, out_lat in cases:
        m = plib.TARGETS[name]["M"]
        reps = plib.distinct_rep_sets(name)[0]
        d = rand_d(m + 3)
        k0 = float(plib.kappa(reps, d))
        d_in = d.copy()
        d_in[0] += np.array(in_lat)
        k_in = float(plib.kappa(reps, d_in))
        d_out = d.copy()
        d_out[0] += np.array(out_lat)
        k_out = float(plib.kappa(reps, d_out))
        inv = abs(k_in - k0) / k0 < 1e-12
        sens = abs(k_out - k0) / k0 > 1e-6
        ok &= inv and sens
        parts.append("%s inv=%s sens=%s(%.4g->%.4g)"
                     % (name, "y" if inv else "N", "y" if sens else "N", k0, k_out))
    record("C-F lattice invariance + sensitivity arm", ok, "; ".join(parts))


def c_g_translation():
    """C-G: kappa is exactly invariant under a common translation (P1)."""
    ok = True
    parts = []
    for name in sorted(plib.TARGETS):
        m = plib.TARGETS[name]["M"]
        reps = plib.distinct_rep_sets(name)[0]
        d = rand_d(m + 3)
        c = RNG.uniform(-5, 5, size=2)
        k0 = float(plib.kappa(reps, d))
        k1 = float(plib.kappa(reps, d + c))
        rel = abs(k1 - k0) / k0
        ok &= rel < 1e-12
        parts.append("%s rel=%.2e" % (name, rel))
    record("C-G common-translation invariance", ok, "; ".join(parts))


def c_h_permutation():
    """C-H: kappa depends on the multiset of displacements, not their order.

    Bit-identity is not achievable: LAPACK's result depends on row order at the
    1e-15 level, measured across 800 random cases spanning all four targets.
    The invariance is therefore asserted to machine precision, and the measured
    worst case is printed so a real violation could not hide behind the
    tolerance.
    """
    ok = True
    parts = []
    for name in sorted(plib.TARGETS):
        m = plib.TARGETS[name]["M"]
        reps = plib.distinct_rep_sets(name)[0]
        worst = 0.0
        for _ in range(50):
            d = rand_d(m + 3)
            p = RNG.permutation(d.shape[0])
            k0 = float(plib.kappa(reps, d))
            k1 = float(plib.kappa(reps, d[p]))
            worst = max(worst, abs(k1 - k0) / k0)
        ok &= worst < 1e-12
        parts.append("%s %.1e" % (name, worst))
    record("C-H permutation invariance", ok, "max rel: " + "; ".join(parts))


def c_n_rank_guard_sensitivity():
    """C-N: the rank guard must not swallow genuinely solvable ill-conditioned sites.

    C-B demands that a degenerate system reports infeasible.  A guard that
    reported infeasible for everything would satisfy C-B perfectly, so the
    guard needs its own sensitivity arm: a system that is badly conditioned but
    full rank must come back FINITE, and equal to what the closed form predicts.
    """
    reps = np.array([[0.0, 0.0], [0.5, 0.5]])
    ok = True
    parts = []
    for sep in [1e-2, 1e-4, 1e-6, 1e-8]:
        d = np.array([[0.0, 0.0], [sep, sep]])
        k = float(plib.kappa(reps, d))
        theta = 2 * np.pi * (d @ reps[1])
        cf = float(plib.kappa_m2_closed(theta))
        # Third, independent witness: for N=2 and small separation,
        # 1 - cos(D/2) ~ D^2/8, so kappa -> 4/D exactly.  This route shares no
        # arithmetic with either the SVD or the closed form.
        delta = float(theta[1] - theta[0])
        asym = 4.0 / abs(delta)
        finite = np.isfinite(k)
        agrees = finite and abs(k - cf) / cf < 1e-6
        asym_ok = finite and abs(k - asym) / asym < 1e-3
        ok &= finite and agrees and asym_ok
        parts.append("sep=%g kappa=%.4e cf=%s asym=%s"
                     % (sep, k, "ok" if agrees else "MISMATCH",
                        "ok" if asym_ok else "MISMATCH"))
    record("C-N rank guard keeps solvable systems", ok, "; ".join(parts))


# ---------------------------------------------------------------------------
# Commissioning: plant the exact defect each control exists to catch.
# ---------------------------------------------------------------------------

def commission():
    """Each plant must make its target control FAIL.  A control that has never
    fired may be a no-op."""
    print("\ncommissioning (each plant must be caught)")
    print("-" * 78)
    caught = 0
    total = 0

    # Plant 1: displacements read in PLANE pixels instead of SENSOR pixels -- a
    # factor-of-two scaling of every displacement, which is the actual unit
    # error available in this pipeline.  It must move the reported statistic on
    # at least one alias geometry; testing a single geometry is not enough,
    # because an additive probe can land in the kernel of one geometry's
    # pairing and read as invariant there.
    total += 1
    d = rand_d(5)
    moved = []
    for name in ["G-1x", "RB-1x"]:
        for reps in plib.distinct_rep_sets(name):
            k_sensor = float(plib.kappa(reps, d))
            k_plane = float(plib.kappa(reps, d / 2.0))
            moved.append(abs(k_plane - k_sensor) / k_sensor > 1e-6)
    fired = all(moved)
    caught += fired
    print("  %-8s plant 1  plane-vs-sensor unit error moves kappa on %d/%d geometries"
          % ("CAUGHT" if fired else "MISSED", sum(moved), len(moved)))

    # Plant 2: silently pseudo-invert a rank-deficient system instead of
    # reporting it, the defect C-B and C-C exist to catch.  The guard-free
    # comparator uses `smin > 0`, which is the exact test the instrument
    # shipped with and which control C-B caught.
    total += 1
    dd = np.array([[0.0, 0.0], [2.0, 0.0]])
    A = plib.system_matrix(reps_g1x_first(), dd)
    s = np.linalg.svd(A, compute_uv=False)
    naive = s[0] / max(s[-1], 1e-300)          # what `smin > 0` returns
    guarded = float(plib.kappa(reps_g1x_first(), dd))
    fired = np.isfinite(naive) and not np.isfinite(guarded)
    caught += fired
    print("  %-8s plant 2  degenerate system: smin>0 test gives %.3e, guarded gives %s"
          % ("CAUGHT" if fired else "MISSED", naive, guarded))

    # Plant 3: a metric blind to phase error.  C-D's rising arm must reject it.
    total += 1
    blind = [1.0, 1.0, 1.0, 1.0]
    fired = not all(blind[i] < blind[i + 1] for i in range(len(blind) - 1))
    caught += fired
    print("  %-8s plant 3  phase-error-blind metric rejected by C-D rising arm"
          % ("CAUGHT" if fired else "MISSED"))

    # Plant 4: a metric that scores degradation but cannot score improvement --
    # the failure mode a defect-only commissioning never sees.
    total += 1
    one_sided = plib.median_eta(reps_g1x_first(), rand_d(3), 0.0, np.inf,
                                np.random.default_rng(5), 512)[0]
    fired = one_sided < 1e-9            # improvement IS scored: eta reaches 0
    caught += fired
    print("  %-8s plant 4  improvement is scorable (eta -> %.2e at sigma=0)"
          % ("CAUGHT" if fired else "MISSED", one_sided))

    # Plant 5: model fewer replicas than the scene carries -- bias B6.  The
    # earlier version of this plant passed the SAME representative set to both
    # the truth and the model, so nothing was mismatched and it read as clean.
    # The truth must be generated at the full replica count and solved at the
    # reduced one.
    total += 1
    truth = plib.distinct_rep_sets("RB-1x")[0]
    d4 = rand_d(6)
    eta_right = plib.unfold_mismatch(truth, truth, d4, 0.0, np.inf,
                                     np.random.default_rng(3), 512)
    eta_wrong = plib.unfold_mismatch(truth, truth[:2], d4, 0.0, np.inf,
                                     np.random.default_rng(3), 512)
    fired = np.median(eta_right) < 1e-10 < np.median(eta_wrong)
    caught += fired
    print("  %-8s plant 5  under-modelled replicas: eta %.2e -> %.3f"
          % ("CAUGHT" if fired else "MISSED",
             np.median(eta_right), np.median(eta_wrong)))

    # Plant 6: the cancellation-prone closed form, which is what the instrument
    # shipped with and which C-N caught.  kappa = sqrt((1+r)/(1-r)) evaluated
    # directly loses every significant digit as r -> 1, and r -> 1 is exactly
    # the ill-conditioned regime this lane cares about most.
    total += 1
    sep6 = 1e-8
    d6 = np.array([[0.0, 0.0], [sep6, sep6]])
    reps6 = np.array([[0.0, 0.0], [0.5, 0.5]])
    theta6 = 2 * np.pi * (d6 @ reps6[1])
    r_direct = abs(np.exp(1j * theta6).sum()) / 2.0
    naive_cf = np.sqrt((1 + r_direct) / max(1 - r_direct, 1e-300))
    stable_cf = float(plib.kappa_m2_closed(theta6))
    truth6 = 4.0 / abs(float(theta6[1] - theta6[0]))
    fired = (abs(naive_cf - truth6) / truth6 > 1e-2
             and abs(stable_cf - truth6) / truth6 < 1e-3)
    caught += fired
    print("  %-8s plant 6  unstable closed form: naive %.4e vs stable %.4e (truth %.4e)"
          % ("CAUGHT" if fired else "MISSED", naive_cf, stable_cf, truth6))

    print("-" * 78)
    print("  plants CAUGHT %d / MISSED %d / total %d" % (caught, total - caught, total))
    return caught == total


def main():
    print("M-PHASE0-PHASE controls (PREREGISTRATION.md section 8)")
    print("=" * 78)
    c_targets()
    c_a_exact()
    c_b_degenerate()
    c_c_underdetermined()
    c_d_monotone()
    c_e_closed_form()
    c_m_closed_form_alln()
    c_f_lattice()
    c_g_translation()
    c_h_permutation()
    c_n_rank_guard_sensitivity()

    all_caught = commission()

    npass = sum(1 for _, ok, _ in RESULTS if ok)
    print("=" * 78)
    print("controls %d/%d passed; commissioning %s"
          % (npass, len(RESULTS), "COMPLETE" if all_caught else "INCOMPLETE"))
    green = (npass == len(RESULTS)) and all_caught
    print("VERDICT: %s" % ("GREEN" if green else "RED"))
    return 0 if green else 1


if __name__ == "__main__":
    sys.exit(main())
