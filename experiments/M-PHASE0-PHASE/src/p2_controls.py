"""Controls and commissioning for `clib.py`, the warpmap phase extractor.

House rule 9: the instrument is commissioned before it is believed.  `plib.py`
was commissioned by `p0_controls.py`; this is the same treatment for the half
that touches real data.

The controls are chosen so that each one can actually FAIL.  In particular the
`|d| <= 0.5` bound is not decoration: a sample lattice's offset to the nearest
lattice point cannot exceed half a period on either axis, so any unit error,
sign error or centre error large enough to matter shows up as a violation of it.

Run: python p2_controls.py
"""

import os
import struct
import sys

import numpy as np

import clib
import plib

FAILURES = []


def check(name, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    print("  [%s] %-46s %s" % (tag, name, detail))
    if not ok:
        FAILURES.append(name)
    return ok


# --------------------------------------------------------------- parse checks

def c_p_parse_matches_printed_aid(maps):
    """Re-derive g/rot/dx/dy from the hex and compare to the printed decimals.

    This is the only check that can catch a field-order error or an endianness
    error.  `warpmap.rs:649-658` prints `Similarity::to_params()`, and
    `align.rs:261-267` defines that as the **linearised** readout

        g = a.re - 1.0,  rot = a.im,  ax = b.re,  ay = b.im

    -- not `scale() = |a|` and `rotation() = arg(a)`, which are different
    functions on the same type.  Using the wrong pair costs ~1e-7 absolute on
    these stacks, which is exactly why the check is written against the source
    and not against the plausible reading.

    `{:+.6e}` carries 7 significant figures; `{:+.4}` carries 4 decimals.
    """
    worst_g = worst_r = worst_d = 0.0
    n = 0
    for path in maps:
        m = clib.parse_warpmap(path)
        for i, aid_str in m["aid"].items():
            a, b = m["placements"][i]
            aid = clib.aid_values(aid_str)
            if len(aid) != 4:
                continue
            n += 1
            worst_g = max(worst_g, abs((a.real - 1.0) - aid["g"]) / (abs(aid["g"]) + 1e-300))
            worst_r = max(worst_r, abs(a.imag - aid["rot"]) / (abs(aid["rot"]) + 1e-300))
            worst_d = max(worst_d, abs(b.real - aid["dx"]), abs(b.imag - aid["dy"]))
    ok = n > 0 and worst_g < 1e-6 and worst_r < 1e-6 and worst_d <= 5.0001e-5
    return check("C-P parse reproduces every printed decimal", ok,
                 "%d placements, rel g %.2e rot %.2e, abs b %.2e" % (n, worst_g, worst_r, worst_d))


def c_p2_endianness_is_pinned():
    """Big-endian is not a guess: little-endian gives a different number here."""
    h = "3ff02929024f86c0"
    be = struct.unpack(">d", bytes.fromhex(h))[0]
    le = struct.unpack("<d", bytes.fromhex(h))[0]
    ok = abs(be - 1.01004887) < 1e-6 and abs(le - be) > 1e-3
    return check("C-P2 f64 hex is big-endian", ok,
                 "be=%.8f le=%.3e" % (be, le))


# ------------------------------------------------------------ synthetic truth

def c_q_identity_has_zero_phase():
    pl = [(complex(1.0, 0.0), complex(0.0, 0.0))] * 5
    _, d = clib.site_phases(pl, (3516, 2344), 1000, 700)
    ok = np.max(np.abs(d)) < 1e-12
    return check("C-Q identity placement has zero phase", ok, "max|d|=%.2e" % np.max(np.abs(d)))


def c_r_sensor_integer_translation_is_invisible():
    """A whole-sensor-pixel shift is 0.5 PLANE px and must read as zero phase.

    Sensitivity half: a half-sensor-pixel shift must read as exactly 0.5.
    """
    pl_int = [(complex(1.0, 0.0), complex(0.5 * k, 0.5 * k)) for k in range(1, 6)]
    _, d0 = clib.site_phases(pl_int, (3516, 2344), 1000, 700)
    pl_half = [(complex(1.0, 0.0), complex(0.25, 0.0))] * 4
    _, d1 = clib.site_phases(pl_half, (3516, 2344), 1000, 700)
    ok = np.max(np.abs(d0)) < 1e-12 and np.allclose(np.abs(d1[:, 0]), 0.5) and np.max(np.abs(d1[:, 1])) < 1e-12
    return check("C-R sensor-integer shift invisible, half shift = 0.5", ok,
                 "int max|d|=%.2e  half |dx|=%.4f" % (np.max(np.abs(d0)), abs(d1[0, 0])))


def c_s_units_have_a_witness():
    """`frac(2t)` and `2 frac(t)` are different, and only one can be right.

    With `a=1` and `b=(0.4, 0)` plane px the frame is displaced 0.8 SENSOR px,
    so its nearest sample sits 0.2 px away, not 0.8: a displacement to the
    NEAREST lattice point cannot exceed half a period.  The wrong-units path
    returns 0.8 and is therefore falsified by arithmetic, not by preference.
    """
    pl = [(complex(1.0, 0.0), complex(0.4, 0.0))] * 3
    _, right = clib.site_phases(pl, (3516, 2344), 1000, 700)
    _, wrong = clib.site_phases_wrong_units(pl, (3516, 2344), 1000, 700)
    ok = (abs(right[0, 0] - 0.2) < 1e-12
          and abs(abs(wrong[0, 0]) - 0.8) < 1e-12
          and abs(wrong[0, 0]) > 0.5)
    return check("C-S unit choice has an arithmetic witness", ok,
                 "right dx=%+.4f  wrong dx=%+.4f (>0.5 impossible)" % (right[0, 0], wrong[0, 0]))


def c_t_bound_holds_on_real_data(maps):
    """|e| <= 0.5 per axis, exactly, on every placement of every stack.

    `e` is an offset to the NEAREST sample of a unit-period lattice, so half a
    period is a hard geometric ceiling with no tolerance to negotiate.  Any unit
    error, sign error, or scale error large enough to matter breaks it.  The
    check is written on `e` rather than on `d = -e/a` precisely so that it stays
    exact: `d` inherits a `1/a` stretch that would force a fudge factor, and a
    fudge factor is where a real violation would hide.
    """
    worst = 0.0
    n = 0
    for path in maps:
        m = clib.parse_warpmap(path)
        if m["placed_count"] < 2:
            continue
        for (px, py) in [(200, 200), (1758, 1172), (3300, 2100), (0, 0), (3515, 2343)]:
            e = clib.site_offsets(m["placements"], m["plane"], px, py)
            if e.size:
                worst = max(worst, float(np.max(np.abs(e))))
                n += e.shape[0]
    ok = n > 0 and worst <= 0.5
    return check("C-T |e| <= 0.5 exactly, all real placements", ok,
                 "%d offsets, worst %.17f" % (n, worst))


def c_u_the_a_correction_is_bounded(maps):
    """Report, do not assume, how much the exact `1/a` term actually moves d."""
    worst = 0.0
    worst_a = 0.0
    for path in maps:
        m = clib.parse_warpmap(path)
        w, h = m["plane"]
        cx, cy = w * 0.5, h * 0.5
        for p in m["placements"]:
            if p is None:
                continue
            a, b = p
            worst_a = max(worst_a, abs(1.0 / a - 1.0))
            sx, sy = clib.apply_at(a, b, 1758, 1172, cx, cy)
            s = complex(sx, sy) * clib.PLANE_TO_SENSOR
            e = complex(clib.frac_centred(s.real), clib.frac_centred(s.imag))
            applied = (-e / a) if clib.A_CORRECTION else (-e)
            worst = max(worst, abs(applied - (-e)))
    ok = worst <= 0.7072 * worst_a * 1.001 and worst > 0
    return check("C-U 1/a term is real, bounded and measured", ok,
                 "max |1/a-1|=%.3e -> max shift %.3e px" % (worst_a, worst))


def c_v_common_shift_leaves_kappa_alone(maps):
    """P1 on REAL data: kappa is a property of relative placement only."""
    path = maps[0]
    m = clib.parse_warpmap(path)
    _, d = clib.site_phases(m["placements"], m["plane"], 1758, 1172)
    if d.shape[0] < 2:
        return check("C-V common shift leaves kappa alone", False, "no placements")
    geoms = plib.distinct_rep_sets("G-1x")
    worst = 0.0
    for g in geoms:
        k0 = plib.kappa(g, d)
        for t in [np.array([0.317, -1.44]), np.array([10.0, 10.0])]:
            k1 = plib.kappa(g, d + t)
            worst = max(worst, abs(k1 - k0) / k0)
    ok = worst < 1e-9
    return check("C-V common shift leaves kappa alone (real data)", ok,
                 "max rel change %.2e" % worst)


def c_w_reference_frame_is_near_identity(maps):
    """The reference's own placement must be the identity, or near it."""
    worst_a, worst_b, n = 0.0, 0.0, 0
    for path in maps:
        m = clib.parse_warpmap(path)
        r = m["reference_index"]
        if r is None or r >= len(m["placements"]) or m["placements"][r] is None:
            continue
        a, b = m["placements"][r]
        worst_a = max(worst_a, abs(a - 1.0))
        worst_b = max(worst_b, abs(b))
        n += 1
    ok = n > 0 and worst_a < 1e-9 and worst_b < 1e-9
    return check("C-W reference index places as the identity", ok,
                 "%d maps, max|a-1|=%.2e max|b|=%.2e" % (n, worst_a, worst_b))


def c_x_duplicate_maps_agree(by_stack):
    """Recon Q5 quantified: do duplicate sidecars give the same kappa?

    Reported, not asserted -- the answer decides whether the census may pick any
    map or must pick a canonical one.
    """
    rows = []
    geoms = plib.distinct_rep_sets("G-1x")
    for stack, paths in sorted(by_stack.items()):
        ks = []
        for path in paths:
            m = clib.parse_warpmap(path)
            _, d = clib.site_phases(m["placements"], m["plane"], 1758, 1172)
            if d.shape[0] < 2:
                continue
            ks.append(max(float(plib.kappa(g, d)) for g in geoms))
        ks = [k for k in ks if np.isfinite(k)]
        if len(ks) > 1:
            rows.append((stack, len(ks), min(ks), max(ks)))
    spread = max((hi / lo for _, _, lo, hi in rows), default=1.0)
    print("      duplicate-map kappa spread, %d stacks with >1 map:" % len(rows))
    for stack, n, lo, hi in rows[:8]:
        print("        %-18s n=%-3d kappa %.3f .. %.3f  (x%.2f)" % (stack, n, lo, hi, hi / lo))
    return check("C-X duplicate maps measured (reported, not assumed)", len(rows) > 0,
                 "worst spread x%.2f" % spread)


# ------------------------------------------------------------- commissioning

def commission(maps, by_stack):
    """Plant known defects; each must be caught by a named control."""
    print("\ncommissioning: each plant must be CAUGHT by its named control")
    print("-" * 78)
    results = []

    orig_f64 = clib._f64
    orig_p2s = clib.PLANE_TO_SENSOR
    orig_sp = clib.site_phases
    orig_so = clib.site_offset

    def run(name, expect, setup, teardown):
        setup()
        try:
            global FAILURES
            saved, FAILURES = FAILURES, []
            try:
                expect()
            except Exception as e:  # a plant that crashes the control is caught
                FAILURES.append("EXCEPTION: %s" % e)
            fired, FAILURES = FAILURES, saved
        finally:
            teardown()
        caught = len(fired) > 0
        print("  [%s] %-46s %s" % ("CAUGHT" if caught else "MISSED", name,
                                   ("by " + fired[0]) if caught else "NOTHING FIRED"))
        results.append((name, caught))

    run("plant 1: little-endian f64 decode",
        lambda: c_p_parse_matches_printed_aid(maps[:20]),
        lambda: setattr(clib, "_f64", lambda h: struct.unpack("<d", bytes.fromhex(h))[0]),
        lambda: setattr(clib, "_f64", orig_f64))

    def swap_ab():
        def f(path):
            m = orig_parse(path)
            for i, p in enumerate(m["placements"]):
                if p is not None:
                    a, b = p
                    m["placements"][i] = (complex(a.imag, a.real), b)
            return m
        clib.parse_warpmap = f
    orig_parse = clib.parse_warpmap
    run("plant 2: a.re/a.im swapped",
        lambda: c_p_parse_matches_printed_aid(maps[:20]),
        swap_ab,
        lambda: setattr(clib, "parse_warpmap", orig_parse))

    def swap_b():
        def f(path):
            m = orig_parse(path)
            for i, p in enumerate(m["placements"]):
                if p is not None:
                    a, b = p
                    m["placements"][i] = (a, complex(b.imag, b.real))
            return m
        clib.parse_warpmap = f
    run("plant 3: b.re/b.im swapped",
        lambda: c_p_parse_matches_printed_aid(maps[:20]),
        swap_b,
        lambda: setattr(clib, "parse_warpmap", orig_parse))

    run("plant 4: wrong units (2*frac instead of frac(2x))",
        lambda: (c_s_units_have_a_witness(), c_t_bound_holds_on_real_data(maps[:20])),
        lambda: setattr(clib, "site_offset", clib.site_offset_wrong_units),
        lambda: setattr(clib, "site_offset", orig_so))

    run("plant 5: plane==sensor (forgot the 2x)",
        lambda: c_r_sensor_integer_translation_is_invisible(),
        lambda: setattr(clib, "PLANE_TO_SENSOR", 1.0),
        lambda: setattr(clib, "PLANE_TO_SENSOR", orig_p2s))

    run("plant 6: 1/a correction dropped",
        lambda: c_u_the_a_correction_is_bounded(maps[:20]),
        lambda: setattr(clib, "A_CORRECTION", False),
        lambda: setattr(clib, "A_CORRECTION", True))

    caught = sum(1 for _, c in results if c)
    print("-" * 78)
    print("  CAUGHT %d / MISSED %d / total %d" % (caught, len(results) - caught, len(results)))
    return caught == len(results)


def main():
    if not os.path.isdir(clib.WARPMAP_DIR):
        print("no warpmap cache at %s" % clib.WARPMAP_DIR)
        return 2
    by_stack = clib.list_maps()
    maps = sorted(p for ps in by_stack.values() for p in ps)
    print("controls: %d cached sidecars across %d stacks" % (len(maps), len(by_stack)))
    print("-" * 78)

    c_p_parse_matches_printed_aid(maps)
    c_p2_endianness_is_pinned()
    c_q_identity_has_zero_phase()
    c_r_sensor_integer_translation_is_invisible()
    c_s_units_have_a_witness()
    c_t_bound_holds_on_real_data(maps)
    c_u_the_a_correction_is_bounded(maps)
    c_v_common_shift_leaves_kappa_alone(maps)
    c_w_reference_frame_is_near_identity(maps)
    c_x_duplicate_maps_agree(by_stack)

    print("-" * 78)
    if FAILURES:
        print("CONTROLS FAILED: %s" % ", ".join(FAILURES))
        return 1
    print("all controls PASS")

    ok = commission(maps, by_stack)
    print("\nVERDICT: %s" % ("GREEN" if ok and not FAILURES else "RED"))
    return 0 if (ok and not FAILURES) else 1


if __name__ == "__main__":
    sys.exit(main())
