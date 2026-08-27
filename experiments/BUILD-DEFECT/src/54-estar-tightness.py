"""54-estar-tightness.py -- how loose is E* as a bound on true alignment error?

THE QUESTION, AND WHY IT OUTRANKS ANY SOLVER CHANGE
===================================================
`E*` (`heldout_error`, `align_cmd.rs:618`) trains a global pose solve on SHORT
edges and scores it against LONG ones. Both sides are produced by the SAME
estimator. That makes it a **consistency** statistic. It has been reported, and
was used as the shipping gate for M23 and M78, as though it were an **accuracy**
statistic. Until the gap between those two things is known, no alignment result
this project has produced can be graded -- including the ones already published.

The pre-registration is `experiments/BUILD-DEFECT/PREREG-estar.txt`, committed
at e732cfb8 before any outcome number for this question existed.

WHY P4 CAN ANSWER IT AND A REAL STACK CANNOT
--------------------------------------------
`p4-warp-{edges,truth}.csv` is 105 frames synthesised from ONE real coffee-bean
frame by a KNOWN smooth similarity sequence plus a growing depth-dependent blur
(M10 P4): planted total drift 98.6 plane px, -4.574% scale, matched to M6's
real coffee-bean drift. **The truth is the plant.** It is not a product of the
estimator, which is precisely the property `M86:451-454` says the real held-out
set lacks -- there, the "truth" the test edges supply is another reading from
the same biased instrument.

THE ALGEBRA, TRANSCRIBED FROM THE SHIPPED SOURCE
------------------------------------------------
`crates/strehl-core/src/align.rs`:
  Similarity{a, b} acts as `p -> a*p + b`, complex, plane-centre origin (:284).
  from_params: `a = (1+g) + i*rot`, `b = ax + i*ay`  (:253) -- note this is the
    LINEARISED small-angle form, not `(1+g)*exp(i*rot)`.
  then(self, other) = apply self first: `a = self.a*other.a`,
    `b = other.a*self.b + other.b`  (:314)
  relative(gi, gj) = gi.invert().then(gj) = gj o gi^-1  (:324)
  so an edge satisfies `T_j = t_ij o T_i`, which is exactly the pair of rows
  `solve_global` pushes (:2085-2098):
      A-system:  t.a * a_i - a_j =  0      with a_0 = 1
      B-system:  t.a * b_i - b_j = -t.b    with b_0 = 0
  corner_err(x, y) = max over the four plane corners of |da*p + db|  (:335)
  corner_radius = hypot(w, h)/2  (:393)

This file re-derives the solve independently in numpy rather than calling the
Rust. That is deliberate: a sympathetic re-reading of the source cannot catch a
misunderstanding of it, and gate G0 below scores my re-derivation against a
number M10 published from a different implementation.

COMMISSIONING GATE G0 -- nothing downstream is readable if this fails
---------------------------------------------------------------------
Solving with ALL 761 edges, unweighted, and scoring against truth must
reproduce M10's published S3-ba-unit median of **0.622 corner px** to within
0.05 px -- M10's own number, from a different implementation, and the same
0.05 px bar `m86-align.rs` uses for its own G0 gate.
"""

import csv
import sys

import numpy as np

EDGES = r"experiments\m10-deep-align\data\p4-warp-edges.csv"
TRUTH = r"experiments\m10-deep-align\data\p4-warp-truth.csv"

MIN_SPAN = 40  # align_cmd.rs:624
MIN_USED = 12  # align_cmd.rs:625

M10_BA_UNIT_MEDIAN = 0.622  # M10 P4 table, strategy S3-ba-unit
G0_BAR = 0.05  # same bar m86-align.rs uses for its own G0

M23_SPAN1_R = 0.526  # M23's measured response on real span-1 edges


def load():
    edges, truth = [], {}
    counts = {"total": 0, "ok": 0, "not_ok": 0}
    with open(EDGES, newline="") as fh:
        for r in csv.DictReader(fh):
            counts["total"] += 1
            if r["status"] != "ok":
                counts["not_ok"] += 1
                continue
            counts["ok"] += 1
            edges.append(
                {
                    "i": int(r["ref"]),
                    "j": int(r["mov"]),
                    "span": int(r["span"]),
                    "used": int(r["used"]),
                    "a": complex(1.0 + float(r["g"]), float(r["rot"])),
                    "b": complex(float(r["ax"]), float(r["ay"])),
                    "pw": int(r["plane_w"]),
                    "ph": int(r["plane_h"]),
                }
            )
    with open(TRUTH, newline="") as fh:
        for r in csv.DictReader(fh):
            truth[int(r["frame"])] = (
                complex(1.0 + float(r["g"]), float(r["rot"])),
                complex(float(r["ax"]), float(r["ay"])),
            )
    return edges, truth, counts


def corners(w, h):
    return np.array(
        [
            complex(-w / 2, -h / 2),
            complex(w / 2, -h / 2),
            complex(-w / 2, h / 2),
            complex(w / 2, h / 2),
        ]
    )


def corner_err(a1, b1, a2, b2, cs):
    return float(np.max(np.abs((a1 - a2) * cs + (b1 - b2))))


def solve(edges, n):
    """Unweighted global least squares, frame 0 gauged to identity.

    Two independent complex systems, exactly as `solve_global` pushes them.
    Unweighted because M10's S3-ba-unit -- the commissioning target -- is the
    unit-weight bundle adjustment.
    """
    cols = {k: k - 1 for k in range(1, n)}
    A = np.zeros((len(edges), n - 1), dtype=complex)
    ra = np.zeros(len(edges), dtype=complex)
    B = np.zeros((len(edges), n - 1), dtype=complex)
    rb = np.zeros(len(edges), dtype=complex)
    for r, e in enumerate(edges):
        i, j, ta, tb = e["i"], e["j"], e["a"], e["b"]
        # A: t.a*a_i - a_j = 0, a_0 = 1
        if i == 0:
            ra[r] -= ta * 1.0
        else:
            A[r, cols[i]] += ta
        if j == 0:
            ra[r] -= -1.0 * 1.0
        else:
            A[r, cols[j]] += -1.0
        # B: t.a*b_i - b_j = -t.b, b_0 = 0 (so frame 0 contributes nothing)
        rb[r] = -tb
        if i != 0:
            B[r, cols[i]] += ta
        if j != 0:
            B[r, cols[j]] += -1.0
    xa = np.linalg.lstsq(A, ra, rcond=None)[0]
    xb = np.linalg.lstsq(B, rb, rcond=None)[0]
    av = np.concatenate(([1.0 + 0j], xa))
    bv = np.concatenate(([0.0 + 0j], xb))
    return av, bv


def truth_gauged(truth, n):
    """Truth poses re-expressed with frame 0 as identity: relative(T0, Tk)."""
    a0, b0 = truth[0]
    av, bv = np.zeros(n, dtype=complex), np.zeros(n, dtype=complex)
    for k in range(n):
        ak, bk = truth[k]
        av[k] = ak / a0
        bv[k] = bk - ak * b0 / a0
    return av, bv


def e_true(av, bv, ta, tb, cs):
    errs = [corner_err(av[k], bv[k], ta[k], tb[k], cs) for k in range(len(av))]
    return float(np.median(errs)), errs


def e_star(edges, n, cs, parts=False):
    """The shipped statistic: train on short edges, score on long ones."""
    test = [e for e in edges if e["span"] >= MIN_SPAN and e["used"] >= MIN_USED]
    train = [e for e in edges if not (e["span"] >= MIN_SPAN and e["used"] >= MIN_USED)]
    if not test or not train:
        return None, 0, 0
    av, bv = solve(train, n)
    errs, sc, tr = [], [], []
    rho_c = float(np.max(np.abs(cs)))
    for e in test:
        i, j = e["i"], e["j"]
        # predict = relative(T_i, T_j)
        pa = av[j] / av[i]
        pb = bv[j] - av[j] * bv[i] / av[i]
        errs.append(corner_err(pa, pb, e["a"], e["b"], cs))
        sc.append(rho_c * abs(pa - e["a"]))
        tr.append(abs(pb - e["b"]))
    if parts:
        return (
            float(np.median(errs)),
            len(train),
            len(test),
            float(np.median(sc)),
            float(np.median(tr)),
        )
    return float(np.median(errs)), len(train), len(test)


def bias_log(edges, rho):
    """Attenuate each edge's LOG-scale increment by rho.

    M23 defines its response on log-scale -- R = (l+ - l-)/(log(1+d)-log(1-d)) --
    so `a -> a**rho` is the faithful model of "the estimator under-reads the
    increment by rho", not a linear scaling of g.
    """
    out = []
    for e in edges:
        f = dict(e)
        f["a"] = complex(np.exp(rho * np.log(e["a"])))
        out.append(f)
    return out


def true_edge(truth_a, truth_b, i, j):
    pa = truth_a[j] / truth_a[i]
    pb = truth_b[j] - truth_a[j] * truth_b[i] / truth_a[i]
    return pa, pb


def shrink_to_truth(edges, ta, tb, frac):
    """Move each edge a fraction of the way toward its true transform.

    frac=0.5 halves every edge's deviation from truth: a genuine, known
    IMPROVEMENT. Required by the commissioning discipline -- planting only
    degradations cannot distinguish a metric that is blind to a defect from one
    that is perverse on it.
    """
    out = []
    for e in edges:
        pa, pb = true_edge(ta, tb, e["i"], e["j"])
        f = dict(e)
        f["a"] = pa + (e["a"] - pa) * (1.0 - frac)
        f["b"] = pb + (e["b"] - pb) * (1.0 - frac)
        out.append(f)
    return out


def add_noise(edges, ta, tb, mult, seed=20260827):
    rng = np.random.default_rng(seed)
    da = np.array(
        [e["a"] - true_edge(ta, tb, e["i"], e["j"])[0] for e in edges], dtype=complex
    )
    db = np.array(
        [e["b"] - true_edge(ta, tb, e["i"], e["j"])[1] for e in edges], dtype=complex
    )
    sa, sb = np.std(da), np.std(db)
    out = []
    for k, e in enumerate(edges):
        f = dict(e)
        f["a"] = e["a"] + mult * sa * complex(rng.normal(), rng.normal()) / np.sqrt(2)
        f["b"] = e["b"] + mult * sb * complex(rng.normal(), rng.normal()) / np.sqrt(2)
        out.append(f)
    return out


def main():
    edges, truth, counts = load()
    n = max(truth) + 1
    pw, ph = edges[0]["pw"], edges[0]["ph"]
    if any(e["pw"] != pw or e["ph"] != ph for e in edges):
        sys.exit("edge table mixes plane geometries; refusing to assume one")
    cs = corners(pw, ph)
    rho_corner = float(np.hypot(pw, ph) / 2)

    print("=" * 78)
    print("54 -- HOW LOOSE IS E*?   (prereg e732cfb8, written before any result)")
    print("=" * 78)
    print(f"  case      : P4 planted-warp, truth independent of the estimator")
    print(f"  frames    : {n}")
    print(
        f"  edge rows : {counts['total']} total = {counts['ok']} ok "
        f"+ {counts['not_ok']} not-ok"
    )
    assert counts["ok"] + counts["not_ok"] == counts["total"]
    print(f"  plane     : {pw}x{ph}, corner radius {rho_corner:.1f} px")

    ta, tb = truth_gauged(truth, n)
    z = corner_err(ta[0], tb[0], 1.0 + 0j, 0.0 + 0j, cs)
    print(f"  gauge chk : frame 0 truth-vs-identity = {z:.3e} px (must be 0)")
    if z > 1e-9:
        sys.exit("gauge alignment is wrong; every E_true below would be offset")

    # ---- GATE G0: does my independent solver reproduce M10's number? ----
    print("\n" + "-" * 78)
    print("GATE G0 -- my re-derived solver vs M10's published S3-ba-unit")
    av, bv = solve(edges, n)
    med, _ = e_true(av, bv, ta, tb, cs)
    d = abs(med - M10_BA_UNIT_MEDIAN)
    print(f"  all {len(edges)} edges, unweighted, scored against truth")
    print(f"  mine {med:.4f} px   M10 {M10_BA_UNIT_MEDIAN:.3f} px   |delta| {d:.4f} px")
    if d > G0_BAR:
        print(f"  G0 FAIL (bar {G0_BAR} px) -- nothing below this line is readable")
        return 1
    print(f"  G0 PASS (bar {G0_BAR} px)")

    # ---- the arms ----
    arms = [
        ("A null", edges),
        (f"B bias rho={M23_SPAN1_R}", bias_log(edges, M23_SPAN1_R)),
        ("C noise 1.0x", add_noise(edges, ta, tb, 1.0)),
        ("D improve 50%", shrink_to_truth(edges, ta, tb, 0.5)),
    ]
    print("\n" + "-" * 78)
    print("PRE-REGISTERED ARMS")
    print(f"  {'arm':<20} {'E*':>10} {'E_true':>12} {'Lambda':>10}  {'train/test':>12}")
    base = {}
    rows = []
    for name, ed in arms:
        es, ntr, nte = e_star(ed, n, cs)
        a2, b2 = solve(ed, n)
        et, _ = e_true(a2, b2, ta, tb, cs)
        lam = et / es if es else float("nan")
        rows.append((name, es, et, lam))
        if name.startswith("A"):
            base = {"es": es, "et": et}
        print(f"  {name:<20} {es:>10.4f} {et:>12.4f} {lam:>10.2f}  {ntr:>5}/{nte:<6}")

    print("\n" + "-" * 78)
    print("MOVEMENT vs the null arm")
    verdict = 0
    for name, es, et, lam in rows[1:]:
        ds = 100 * (es / base["es"] - 1)
        dt = 100 * (et / base["et"] - 1)
        print(f"  {name:<20} E* {ds:+9.1f}%    E_true {dt:+9.1f}%")

    print("\n" + "-" * 78)
    print("PRE-REGISTERED CHECKS")
    es_b, et_b = rows[1][1], rows[1][2]
    es_c = rows[2][1]
    es_d, et_d = rows[3][1], rows[3][2]

    c_alive = es_c > base["es"] * 1.25
    print(f"  C: E* rises on a defect it CAN see          : {'PASS' if c_alive else 'FAIL'}")
    d_ok = es_d < base["es"] * 0.9 and et_d < base["et"] * 0.9
    print(f"  D: E* falls on a genuine IMPROVEMENT        : {'PASS' if d_ok else 'FAIL'}")
    if not c_alive or not d_ok:
        print("\n  The instrument is dead or perverse; arm B's reading is not")
        print("  interpretable. Reporting that, and nothing else.")
        return 1

    b_estar_still = abs(es_b / base["es"] - 1) <= 0.25
    b_etrue_moved = et_b > base["et"] * 2
    print(f"  B: E* unchanged (<=25%) under a real bias   : {'PASS' if b_estar_still else 'FAIL'}")
    print(f"  B: E_true moved a long way (>2x)            : {'PASS' if b_etrue_moved else 'FAIL'}")

    lam_worst = max(abs(np.log2(r[3])) for r in rows)
    print(f"\n  worst |log2 Lambda| across arms = {lam_worst:.2f}  (bar 1.0)")
    if lam_worst <= 1.0:
        print("  VERDICT: E* is a usable ruler -- Lambda stayed within 2x everywhere")
    else:
        worst = max(rows, key=lambda r: abs(np.log2(r[3])))
        print(f"  VERDICT: E* is NOT a usable ruler. On '{worst[0].strip()}' the true")
        print(f"           error is {worst[3]:.1f}x what E* reports.")
        verdict = 0

    # ---- the ladder: is the perversity systematic, or a coincidence at one rho? ----
    print("\n" + "=" * 78)
    print("THE LADDER -- sweep the bias and watch the two statistics diverge")
    print("A single point could be a coincidence. A monotone ladder cannot.")
    print("=" * 78)
    print(
        f"  {'rho':>6} {'E*':>9} {'E*_scale':>10} {'E*_trans':>10} "
        f"{'E_true':>10} {'Lambda':>9}"
    )
    lad = []
    for rho in (1.0, 0.9, 0.8, 0.7, 0.6, M23_SPAN1_R, 0.4, 0.3):
        ed = bias_log(edges, rho)
        es, _, _, sc, tr = e_star(ed, n, cs, parts=True)
        a2, b2 = solve(ed, n)
        et, _ = e_true(a2, b2, ta, tb, cs)
        lad.append((rho, es, et))
        tag = "  <- M23's measured real span-1 R" if rho == M23_SPAN1_R else ""
        print(
            f"  {rho:>6.3f} {es:>9.4f} {sc:>10.4f} {tr:>10.4f} "
            f"{et:>10.4f} {lam_or_nan(et, es):>9.2f}{tag}"
        )

    es_mono = all(lad[k][1] > lad[k + 1][1] for k in range(len(lad) - 1))
    et_mono = all(lad[k][2] < lad[k + 1][2] for k in range(len(lad) - 1))
    print(f"\n  E* falls monotonically as the estimator gets worse : {es_mono}")
    print(f"  E_true rises monotonically as it gets worse        : {et_mono}")
    if es_mono and et_mono:
        print("\n  E* is not merely blind to a scale-attenuation bias. It is")
        print("  PERVERSE on it: the worse the estimator, the better the gate reads.")
        print("  A lane shipping this defect would be congratulated by the gate.")
    return verdict


def lam_or_nan(et, es):
    return et / es if es else float("nan")


if __name__ == "__main__":
    sys.exit(main())
