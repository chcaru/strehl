"""Commissioning for `flib`: cycle consistency by span and radius.

House rule 9 -- the instrument is commissioned before it is trusted. House rule
35 -- a checker carrying its own answer tests nothing, so every control here is
either a closed form derived independently of the code path it checks, or a
comparison against the shipping Rust binary, or a plant.

Controls pair an invariance arm with a sensitivity arm wherever the algebra
permits one, because a control that can only pass is worthless.

Run: python p4_controls.py
"""

import os
import sys

import numpy as np

import flib

PASS, FAIL = [], []
CAUGHT, MISSED = [], []


def record(name, ok, detail):
    (PASS if ok else FAIL).append(name)
    print("  %-8s %-42s %s" % ("PASS" if ok else "FAIL", name, detail))


def caught(name, ok, detail):
    (CAUGHT if ok else MISSED).append(name)
    print("  %-8s %-42s %s" % ("CAUGHT" if ok else "MISSED", name, detail))


PLANE = (3516, 2344)


# ---------------------------------------------------------------------------
# C-N  a self-consistent edge set must read zero, and a perturbed one must not
# ---------------------------------------------------------------------------

def c_n_null_and_sensitivity():
    rng = np.random.default_rng(1)
    edges, _ = flib.synth_consistent(12, rng, PLANE)
    r = flib.cycle_errors(edges, PLANE)
    worst = float(r["err"].max())
    ok_null = worst < 1e-9 and len(r["err"]) > 100
    record("C-N null: consistent set reads zero", ok_null,
           "%d triples, worst %.3e plane px" % (len(r["err"]), worst))

    # Sensitivity arm: the same set with ONE edge moved must not read zero.
    e2 = dict(edges)
    a, b = e2[(0, 5)]
    e2[(0, 5)] = (a, b + complex(0.25, 0.0))
    r2 = flib.cycle_errors(e2, PLANE)
    hit = r2["err"] > 1e-9
    ok_sens = hit.any()
    record("C-N sensitivity: one moved edge shows", ok_sens,
           "%d/%d triples nonzero, worst %.4f plane px"
           % (int(hit.sum()), len(hit), float(r2["err"].max())))


# ---------------------------------------------------------------------------
# C-P  a planted translation error is recovered exactly
# ---------------------------------------------------------------------------

def c_p_planted_translation_is_exact():
    rng = np.random.default_rng(2)
    edges, _ = flib.synth_consistent(8, rng, PLANE)
    shift = complex(0.3, -0.4)
    e2 = dict(edges)
    a, b = e2[(2, 5)]
    e2[(2, 5)] = (a, b + shift)
    r = flib.cycle_errors(e2, PLANE)
    # Triples whose DIRECT edge is the planted one read |shift| exactly, because
    # a pure translation offset moves every corner by the same vector.
    sel = (r["i"] == 2) & (r["k"] == 5)
    got = r["err"][sel]
    ok = sel.any() and np.allclose(got, abs(shift), rtol=0, atol=1e-12)
    record("C-P planted translation recovered", ok,
           "%d triples, all %.12f vs |shift| %.12f"
           % (int(sel.sum()), float(got[0]) if sel.any() else -1, abs(shift)))


# ---------------------------------------------------------------------------
# C-R  err_at_radius(corner_radius) bounds corner_err, and equals it when the
#      scale part is zero (pure translation reaches its max in every direction)
# ---------------------------------------------------------------------------

def c_r_radius_relation():
    rng = np.random.default_rng(3)
    edges, _ = flib.synth_consistent(9, rng, PLANE)
    e2 = dict(edges)
    for key in list(e2)[:20]:
        a, b = e2[key]
        e2[key] = (a * (1 + rng.normal(0, 1e-4)), b + rng.normal(0, 0.2))
    rc = flib.corner_radius(PLANE)
    r = flib.cycle_errors(e2, PLANE, radii=[rc])
    at = r["at_radius"][:, 0]
    ok_bound = bool(np.all(at >= r["err"] - 1e-9))
    record("C-R err_at_radius bounds corner_err", ok_bound,
           "max shortfall %.3e plane px" % float(np.max(r["err"] - at)))

    # Pure-translation arm: with no scale error the two must agree exactly.
    e3 = dict(edges)
    a, b = e3[(1, 4)]
    e3[(1, 4)] = (a, b + complex(0.31, 0.17))
    r3 = flib.cycle_errors(e3, PLANE, radii=[rc])
    sel = (r3["i"] == 1) & (r3["k"] == 4)
    ok_eq = bool(np.allclose(r3["at_radius"][sel, 0], r3["err"][sel], atol=1e-12))
    record("C-R pure translation: equal exactly", ok_eq,
           "%d triples, max gap %.3e"
           % (int(sel.sum()),
              float(np.max(np.abs(r3["at_radius"][sel, 0] - r3["err"][sel])))))

    # Sensitivity: a pure SCALE error must grow with radius, not be flat.
    e4 = dict(edges)
    a, b = e4[(1, 4)]
    e4[(1, 4)] = (a * (1 + 2e-4), b)
    r4 = flib.cycle_errors(e4, PLANE, radii=[rc * 0.25, rc])
    sel4 = (r4["i"] == 1) & (r4["k"] == 4)
    near = float(r4["at_radius"][sel4, 0][0])
    far = float(r4["at_radius"][sel4, 1][0])
    ok_grow = far > 3.5 * near > 0
    record("C-R scale error grows with radius", ok_grow,
           "r/4 -> %.4f, r -> %.4f, ratio %.3f" % (near, far, far / max(near, 1e-12)))


# ---------------------------------------------------------------------------
# C-T  triple enumeration matches the Rust enumeration on a known graph
# ---------------------------------------------------------------------------

def c_t_triple_enumeration():
    # Complete graph on n nodes has C(n,3) triples i<j<k.
    rng = np.random.default_rng(4)
    for n in (5, 7, 10):
        edges, _ = flib.synth_consistent(n, rng, PLANE)
        want = n * (n - 1) * (n - 2) // 6
        got = len(flib.triples(edges))
        if got != want:
            record("C-T triple count on complete graph", False,
                   "n=%d got %d want %d" % (n, got, want))
            return
    # A sparse graph: only spans in {1,2} -> triples are exactly (i, i+1, i+2).
    sparse = {}
    edges, _ = flib.synth_consistent(12, np.random.default_rng(5), PLANE)
    for (i, j), v in edges.items():
        if j - i in (1, 2):
            sparse[(i, j)] = v
    trip = flib.triples(sparse)
    ok = all(j == i + 1 and k == i + 2 for (i, j, k) in trip) and len(trip) == 10
    record("C-T triple count on complete graph", True,
           "C(n,3) exact for n=5,7,10; sparse span<=2 gives %d triples" % len(trip))
    record("C-T sparse graph enumerates correctly", ok,
           "%d triples, all (i, i+1, i+2): %s" % (len(trip), ok))


# ---------------------------------------------------------------------------
# C-U  the plane -> sensor factor is applied exactly once
# ---------------------------------------------------------------------------

def c_u_units():
    ok = (flib.PLANE_TO_SENSOR == 2.0
          and float(flib.to_sensor(np.array([0.5]))[0]) == 1.0)
    record("C-U plane px -> sensor px is x2", ok,
           "0.5 plane px -> %.3f sensor px" % float(flib.to_sensor(np.array([0.5]))[0]))


# ---------------------------------------------------------------------------
# C-V  compose() matches the Rust `then` on a case computed by hand
# ---------------------------------------------------------------------------

def c_v_compose_matches_rust():
    # align.rs: (self then other).a = self.a*other.a ; .b = other.a*self.b + other.b
    t1 = (complex(1.5, 0.5), complex(2.0, -1.0))
    t2 = (complex(0.5, -0.25), complex(-3.0, 4.0))
    want_a = complex(1.5, 0.5) * complex(0.5, -0.25)
    want_b = complex(0.5, -0.25) * complex(2.0, -1.0) + complex(-3.0, 4.0)
    got = flib.then(t1, t2)
    ok = abs(got[0] - want_a) < 1e-15 and abs(got[1] - want_b) < 1e-15
    record("C-V then() matches align.rs formula", ok,
           "a %s b %s" % (got[0], got[1]))

    # Sensitivity: the OTHER order must differ, or the test proves nothing.
    other = flib.then(t2, t1)
    ok2 = abs(other[1] - got[1]) > 1e-9
    record("C-V composition is not commutative", ok2,
           "|b difference| %.4f" % abs(other[1] - got[1]))


# ---------------------------------------------------------------------------
# C-C  cross-language: reproduce the binary's own printed cycle-floor
# ---------------------------------------------------------------------------

def c_c_cross_language(edge_csv, expect, cfg=None, tol=5e-3):
    if not os.path.exists(edge_csv):
        record("C-C reproduce binary cycle-floor", False,
               "SKIPPED: %s absent -- see p4_controls.py header" % edge_csv)
        return
    edges = flib.load_edges(edge_csv, cfg=cfg)
    plane = flib.plane_of(edge_csv)
    r = flib.cycle_errors(edges, plane, max_triples=4000)
    got = float(np.median(r["err"]))
    ok = abs(got - expect) <= tol
    record("C-C reproduce binary cycle-floor", ok,
           "python %.4f vs binary %.4f plane px (%d triples)"
           % (got, expect, len(r["err"])))


# ---------------------------------------------------------------------------
# plants
# ---------------------------------------------------------------------------

def plants():
    rng = np.random.default_rng(11)
    edges, _ = flib.synth_consistent(10, rng, PLANE)

    # 1: composition order reversed.  The edge set must be built with the REAL
    #    composition and only then checked with the broken one -- building it
    #    with the broken one makes generator and checker share the defect, which
    #    cancels exactly and leaves the plant inert (house rule 35).  That is not
    #    hypothetical: this plant read MISSED until it was written this way.
    def bad_then(t1, t2):
        return (t1[0] * t2[0], t1[0] * t2[1] + t1[1])
    e1, _ = flib.synth_consistent(10, np.random.default_rng(11), PLANE)
    clean = float(flib.cycle_errors(e1, PLANE)["err"].max())
    real, flib.then = flib.then, bad_then
    try:
        worst = float(flib.cycle_errors(e1, PLANE)["err"].max())
    finally:
        flib.then = real
    caught("plant 1 wrong composition order", worst > 1e-9 and clean < 1e-9,
           "same set reads %.4f plane px broken vs %.3e correct" % (worst, clean))

    # 2: corner offsets taken from the origin, not the centre
    real_c = flib.corners
    flib.corners = lambda p: np.array([complex(0, 0), complex(p[0], 0),
                                       complex(0, p[1]), complex(p[0], p[1])])
    try:
        e2 = dict(edges)
        a, b = e2[(1, 6)]
        e2[(1, 6)] = (a * (1 + 3e-4), b)
        bad = float(flib.cycle_errors(e2, PLANE)["err"].max())
    finally:
        flib.corners = real_c
    e2 = dict(edges)
    a, b = e2[(1, 6)]
    e2[(1, 6)] = (a * (1 + 3e-4), b)
    good = float(flib.cycle_errors(e2, PLANE)["err"].max())
    caught("plant 2 corners not centred", abs(bad - good) > 1e-6,
           "off-centre %.4f vs centred %.4f plane px" % (bad, good))

    # 3: unit factor dropped
    real_f = flib.PLANE_TO_SENSOR
    flib.PLANE_TO_SENSOR = 1.0
    try:
        bad = float(flib.to_sensor(np.array([0.5]))[0])
    finally:
        flib.PLANE_TO_SENSOR = real_f
    caught("plant 3 plane/sensor factor dropped", abs(bad - 0.5) < 1e-15,
           "0.5 plane px read as %.3f sensor px, should be 1.0" % bad)

    # 4: triples enumerated without requiring all three edges present
    sparse = {k: v for k, v in edges.items() if (k[1] - k[0]) in (1, 2)}
    n_ok = len(flib.triples(sparse))
    n_all = len(flib.triples(edges))
    caught("plant 4 missing edges must drop triples", n_ok < n_all,
           "sparse graph %d triples vs complete %d" % (n_ok, n_all))

    # 5: an IMPROVEMENT must be scorable, not just a degradation.  Halving a
    #    planted error must halve the reading; a metric bounded below by its
    #    own noise would not move.
    e5 = dict(edges)
    a, b = e5[(3, 7)]
    e5[(3, 7)] = (a, b + complex(0.4, 0.0))
    big = float(flib.cycle_errors(e5, PLANE)["err"].max())
    e5[(3, 7)] = (a, b + complex(0.2, 0.0))
    small = float(flib.cycle_errors(e5, PLANE)["err"].max())
    caught("plant 5 improvement is scorable", abs(big / max(small, 1e-12) - 2.0) < 1e-6,
           "0.4 -> %.4f, 0.2 -> %.4f, ratio %.6f" % (big, small, big / max(small, 1e-12)))

    # 6: status!=ok rows must be excluded by load_edges
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".csv", text=True)
    with os.fdopen(fd, "w", newline="") as f:
        f.write("case,cfg,ref,mov,span,status,g,rot,ax,ay,plane_w,plane_h\n")
        f.write("t,m10,0,1,1,ok,0,0,1,0,3516,2344\n")
        f.write("t,m10,0,2,2,refused,0,0,999,0,3516,2344\n")
    try:
        got = flib.load_edges(path)
        ok = (0, 2) not in got and (0, 1) in got
    finally:
        os.unlink(path)
    caught("plant 6 refused edges excluded", ok,
           "loaded keys %s" % sorted(got))


def main():
    print("=" * 78)
    print("flib commissioning: cycle consistency by span and radius")
    print("=" * 78)
    c_n_null_and_sensitivity()
    c_p_planted_translation_is_exact()
    c_r_radius_relation()
    c_t_triple_enumeration()
    c_u_units()
    c_v_compose_matches_rust()
    c_c_cross_language(os.path.join("..", "out", "edges", "coffee-bubbles.csv"),
                       expect=0.3325)
    print("-" * 78)
    print("  controls PASS %d / FAIL %d" % (len(PASS), len(FAIL)))
    print()
    print("commissioning (each plant must be caught)")
    print("-" * 78)
    plants()
    print("-" * 78)
    print("  plants CAUGHT %d / MISSED %d / total %d"
          % (len(CAUGHT), len(MISSED), len(CAUGHT) + len(MISSED)))
    print("=" * 78)
    green = not FAIL and not MISSED
    print("VERDICT: %s" % ("GREEN" if green else "RED"))
    return 0 if green else 1


if __name__ == "__main__":
    sys.exit(main())
