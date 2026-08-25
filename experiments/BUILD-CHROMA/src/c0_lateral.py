"""Commissioning the self-measured lateral-CA estimator.

Mirrors `b0_validate.py`, which commissioned the axial estimator. The contract
is two-sided and both sides are required:

  * plant a known radial scale -> require exact recovery;
  * force it where no aberration exists -> require it to return zero, not a
    confident wrong answer.

The first version of this suite FAILED, and the failures are kept in the record
because they set the design:

  * The green null on real sky returned rms 8.05 plane px against a truth of 0,
    with 35% of tiles more than 3 px out. Phase correlation does not degrade
    gracefully on a low-structure tile -- it returns a confident wrong answer,
    the same pathology Phase 1 hit when a registration track reported 91/-51 px
    where the truth was exactly zero. The residual is 0.054 px on the top
    structure quintile and 8 px on the bottom, so the fix is a **gate on green
    gradient energy**, swept as a ladder rather than chosen.
  * A planted translation of 0.25 px on a real plane recovered as 0.16 px. A CFA
    plane samples at half the sensel rate and is aliased, so cubic-spline
    resampling of one is not an exact sub-pixel translation: the *plant* was
    wrong, not only the estimator. The plant is therefore validated on a
    genuinely band-limited field before being trusted on real data.

TESTS

  T0  identity        plane against itself -> exactly (0, 0)
  T1  band-limited    plant on a field with no energy near Nyquist. Isolates the
                      estimator from plant error. Shift ladder and scale ladder.
  T2  zero dose       no aberration at all -> eps 0, and the CI must contain 0
  T3  green null      G1 vs G2 on real sky, as a function of the gate. Two
                      lattices, one wavelength: eps must be 0 and the lattice
                      offset must be recovered. This is the on-sky floor.
  T4  gate ladder     eps_R and eps_B vs gate threshold. Required flat, with the
                      surviving tiles' radial span reported alongside -- a gate
                      that eats the radial lever arm invalidates the fit even if
                      eps looks stable (rule 4).
  T5  real ladder     dose planted ON TOP of the real red signal. Slope must be
                      1.000 and the intercept must equal the native coefficient.
                      T1 proves the estimator can read a scale; T5 proves it
                      stays linear in the regime the headline number lives in.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import lateral

TILE = 160
MARGIN = 40
STACK = "tweezers-cpl"
FRAME = 50
PPM = 1e6

# Gate thresholds swept in T3/T4, in mean-Sobel-energy units. The ladder spans
# 0 (no gate at all) to a level that keeps only the top few per cent of tiles.
GATES = [0.0, 2e4, 5e4, 1e5, 2e5, 4e5, 8e5]


def banner(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def radial_span(u):
    r = np.hypot(u[:, 0], u[:, 1])
    return float(r.min()), float(r.max())


def main():
    out = {}
    fs = common.frames(STACK)
    cfa = common.read_cfa(fs[FRAME])
    sensel_shape = cfa.shape
    planes = common.planes_of(cfa)
    shape = planes["G1"].shape
    tiles = lateral.tile_corners(shape, TILE, MARGIN)
    half_diag = float(np.hypot(*sensel_shape) / 4.0)
    print(f"{STACK}: {len(fs)} frames, using frame {FRAME}")
    print(f"sensel {sensel_shape}  plane {shape}  tiles {len(tiles)}  "
          f"tile {TILE}  margin {MARGIN}")
    print(f"normalised field height 1.0 = {half_diag:.1f} plane px "
          f"(half the full-resolution sensel diagonal, as optics.rs defines it)")
    out["setup"] = {
        "stack": STACK, "frame": FRAME, "tile": TILE, "margin": MARGIN,
        "n_tiles": len(tiles), "sensel_shape": list(sensel_shape),
        "plane_shape": list(shape), "half_diag_plane_px": half_diag,
    }
    g1 = planes["G1"]

    # ---- T0 identity -----------------------------------------------------
    banner("T0  identity: a plane correlated against itself")
    ds = np.array([lateral.subpix(g1[y:y + TILE, x:x + TILE],
                                  g1[y:y + TILE, x:x + TILE])
                   for (y, x) in tiles[:40]])
    print(f"max |dy| {np.abs(ds[:,0]).max():.6f}   max |dx| {np.abs(ds[:,1]).max():.6f}  plane px")
    assert np.abs(ds).max() < 1e-9
    out["T0"] = {"max_abs": float(np.abs(ds).max())}
    print("PASS")

    # ---- T1 band-limited plant -------------------------------------------
    banner("T1  band-limited synthetic: estimator isolated from plant error")
    synth = lateral.synth_bandlimited(shape, sigma=2.0, seed=7)
    su = np.array([lateral.field_position(y, x, TILE, "G1", sensel_shape)
                   for (y, x) in tiles])

    print("\nT1a  pure translation")
    print(f"{'planted dy':>11} {'planted dx':>11} {'fit ty':>9} {'fit tx':>9} "
          f"{'err dy':>9} {'err dx':>9} {'eps ppm':>9}")
    t1a = []
    for (py, px) in [(0.0, 0.0), (0.25, -0.10), (-0.50, 0.75), (1.30, -1.10)]:
        moved = lateral.plant_scale(synth, 0.0, ty=py, tx=px)
        d = np.array([lateral.subpix(synth[y:y + TILE, x:x + TILE],
                                     moved[y:y + TILE, x:x + TILE])
                      for (y, x) in tiles])
        f = lateral.fit_model(su, d)
        print(f"{py:11.3f} {px:11.3f} {f['ty']:9.4f} {f['tx']:9.4f} "
              f"{f['ty']+py:9.4f} {f['tx']+px:9.4f} {f['eps']*PPM:9.2f}")
        t1a.append({"planted": [py, px], **f})
    sgn = -1.0 if t1a[3]["ty"] < 0 else 1.0
    print(f"\nsign: the fit reports the displacement of the REFERENCE relative to "
          f"the moving image,\nso a plant of +dy reads as {'-' if sgn < 0 else '+'}dy. "
          f"Everything downstream is negated once, here,\nand nowhere else.")

    print("\nT1b  radial scale ladder")
    print(f"{'planted ppm':>12} {'raw fit ppm':>12} {'negated ppm':>12} "
          f"{'residual ppm':>13} {'rms px':>8} {'R2':>8}")
    t1b = []
    for e in [0.0, -2000e-6, -1000e-6, -500e-6, -200e-6, 200e-6, 500e-6,
              1000e-6, 2000e-6]:
        moved = lateral.plant_scale(synth, e)
        d = np.array([lateral.subpix(synth[y:y + TILE, x:x + TILE],
                                     moved[y:y + TILE, x:x + TILE])
                      for (y, x) in tiles])
        f = lateral.fit_model(su, d)
        neg = -f["eps"]
        print(f"{e*PPM:12.1f} {f['eps']*PPM:12.2f} {neg*PPM:12.2f} "
              f"{(neg-e)*PPM:13.3f} {f['rms']:8.4f} {f['r2']:8.4f}")
        t1b.append({"planted": e, "recovered": neg, **f})
    pl = np.array([r["planted"] for r in t1b])
    fi = np.array([r["recovered"] for r in t1b])
    A = np.stack([pl, np.ones_like(pl)], 1)
    slope, icpt = np.linalg.lstsq(A, fi, rcond=None)[0]
    worst = float(np.max(np.abs(fi - pl)))
    print(f"\nrecovery slope {slope:.6f}   intercept {icpt*PPM:+.4f} ppm   "
          f"worst |error| {worst*PPM:.3f} ppm")
    out["T1"] = {"shift": t1a, "scale": t1b, "slope": float(slope),
                 "intercept": float(icpt), "worst_abs_err": worst, "sign": sgn}

    print("\nT1c  normalisation transfer function (why norm=None is the default)")
    print("A whitened cross-power spectrum shrinks small displacements toward")
    print("zero. That is disqualifying here specifically, because red's")
    print("coefficient is ~10x blue's: a magnitude-dependent transfer would read")
    print("the two arms on two different scales and the R-vs-B comparison would")
    print("be an artefact of the estimator.\n")
    print(f"{'planted ppm':>12} {'norm=None ppm':>14} {'ratio':>7} "
          f"{'norm=phase ppm':>15} {'ratio':>7}")
    t1c = []
    for e in [100e-6, 200e-6, 500e-6, 1000e-6, 2000e-6]:
        moved = lateral.plant_scale(synth, e)
        got = {}
        for nm in (None, "phase"):
            d = np.array([lateral.subpix(synth[y:y + TILE, x:x + TILE],
                                         moved[y:y + TILE, x:x + TILE], norm=nm)
                          for (y, x) in tiles])
            got[str(nm)] = -lateral.fit_model(su, d)["eps"]
        print(f"{e*PPM:12.1f} {got['None']*PPM:14.2f} {got['None']/e:7.3f} "
              f"{got['phase']*PPM:15.2f} {got['phase']/e:7.3f}")
        t1c.append({"planted": e, "none": got["None"], "phase": got["phase"]})
    out["T1c_normalisation"] = t1c

    # ---- T2 zero dose ----------------------------------------------------
    banner("T2  zero dose: forced to answer where no aberration exists")
    print("Two arms. (a) a band-limited field against an untouched copy of itself:")
    print("    a true zero; the estimator must not invent a coefficient.")
    print("(b) the SAME field resampled through plant_scale at eps=0, so the cubic")
    print("    spline runs but plants nothing -- separates 'returns zero' from")
    print("    'the resampler happens to be the identity'.")
    d2a = np.array([lateral.subpix(synth[y:y + TILE, x:x + TILE],
                                   synth[y:y + TILE, x:x + TILE].copy())
                    for (y, x) in tiles])
    f2a = lateral.boot_fit(su, d2a)
    zero_resampled = lateral.plant_scale(synth, 0.0)
    d2b = np.array([lateral.subpix(synth[y:y + TILE, x:x + TILE],
                                   zero_resampled[y:y + TILE, x:x + TILE])
                    for (y, x) in tiles])
    f2b = lateral.boot_fit(su, d2b)
    print(f"\n{'arm':>18} {'eps ppm':>10} {'CI lo':>10} {'CI hi':>10} "
          f"{'ty':>10} {'tx':>10} {'rms px':>9}")
    for nm, f in (("(a) exact copy", f2a), ("(b) resampled @0", f2b)):
        print(f"{nm:>18} {-f['eps']*PPM:10.4f} {-f['eps_hi']*PPM:10.4f} "
              f"{-f['eps_lo']*PPM:10.4f} {f['ty']:10.5f} {f['tx']:10.5f} {f['rms']:9.6f}")
    out["T2"] = {"exact_copy": f2a, "resampled_zero": f2b}

    # ---- T3 green null on real sky, as a function of the gate ------------
    banner("T3  green null on real sky: G1 vs G2, gate ladder")
    ly, lx = lateral.lattice_offset("G2")
    print(f"truth: eps = 0 exactly (one wavelength), lattice offset "
          f"(dy, dx) = ({ly:+.3f}, {lx:+.3f}) plane px")
    print("'med dy/dx' is the median residual AFTER the lattice term is removed, "
          "so it should be 0.\n")
    disp, struct = lateral.measure_frame(planes, tiles, TILE,
                                         arms=("R", "G2", "B"))
    print(f"{'gate':>9} {'n':>5} {'r span (plane px)':>20} "
          f"{'eps ppm':>10} {'CI lo':>9} {'CI hi':>9} {'rms px':>9} "
          f"{'med dy':>9} {'med dx':>9}")
    t3 = []
    for gate in GATES:
        u, d, _ = lateral.rows_for("G2", disp, tiles, TILE, sensel_shape,
                                   struct=struct, gate=gate)
        if len(u) < 12:
            print(f"{gate:9.0f} {len(u):5d}   too few tiles to fit")
            continue
        f = lateral.boot_fit(u, d, robust=True)
        r0, r1 = radial_span(u)
        print(f"{gate:9.0f} {len(u):5d} {r0:9.0f}..{r1:<10.0f} "
              f"{-f['eps']*PPM:10.3f} {-f['eps_hi']*PPM:9.3f} {-f['eps_lo']*PPM:9.3f} "
              f"{f['rms']:9.4f} {np.median(d[:,0]):9.4f} {np.median(d[:,1]):9.4f}")
        t3.append({"gate": gate, "n": len(u), "r_min": r0, "r_max": r1,
                   "eps": -f["eps"], "eps_lo": -f["eps_hi"],
                   "eps_hi": -f["eps_lo"], "rms": f["rms"],
                   "med_dy": float(np.median(d[:, 0])),
                   "med_dx": float(np.median(d[:, 1]))})
    out["T3"] = t3

    # ---- T4 gate ladder on the treatment arms ----------------------------
    banner("T4  gate ladder on the treatment arms (R and B vs green)")
    print("The gate is computed on GREEN ONLY and so carries no chromatic")
    print("information: selection on an input, not on an outcome. The radial span")
    print("is printed beside every row because a gate that eats the radial lever")
    print("arm invalidates the fit even when eps looks stable (rule 4).\n")
    t4 = {}
    for arm in ("R", "B"):
        print(f"--- {arm} vs G1 ---")
        print(f"{'gate':>9} {'n':>5} {'r span':>19} {'eps OLS':>10} "
              f"{'eps robust':>11} {'CI lo':>9} {'CI hi':>9} {'rms px':>8} {'R2':>7}")
        rows = []
        for gate in GATES:
            u, d, _ = lateral.rows_for(arm, disp, tiles, TILE, sensel_shape,
                                       struct=struct, gate=gate)
            if len(u) < 12:
                continue
            f = lateral.boot_fit(u, d, robust=True)
            fo = lateral.fit_model(u, d, robust=False)
            r0, r1 = radial_span(u)
            print(f"{gate:9.0f} {len(u):5d} {r0:8.0f}..{r1:<9.0f} "
                  f"{-fo['eps']*PPM:10.2f} {-f['eps']*PPM:11.2f} "
                  f"{-f['eps_hi']*PPM:9.2f} {-f['eps_lo']*PPM:9.2f} "
                  f"{f['rms']:8.4f} {f['r2']:7.4f}")
            rows.append({"gate": gate, "n": len(u), "r_min": r0, "r_max": r1,
                         "eps_ols": -fo["eps"], "eps_robust": -f["eps"],
                         "eps_lo": -f["eps_hi"], "eps_hi": -f["eps_lo"],
                         "rms": f["rms"], "r2": f["r2"],
                         "ty": f["ty"], "tx": f["tx"]})
        t4[arm] = rows
        print()
    out["T4"] = t4

    # ---- T5 dose ladder on top of the real red signal --------------------
    banner("T5  dose ladder ON TOP of real R (the regime the answer lives in)")
    gate = 2e5
    print(f"gate {gate:.0f}, read off the T3/T4 plateau rather than assumed\n")
    u0, d0, _ = lateral.rows_for("R", disp, tiles, TILE, sensel_shape,
                                 struct=struct, gate=gate)
    base = lateral.fit_model(u0, d0, robust=True)
    keep = [(y, x) for (y, x) in tiles if struct[(y, x)] >= gate]
    print(f"native (undosed) eps_R = {-base['eps']*PPM:+.2f} ppm over {len(u0)} tiles\n")
    print(f"{'planted ppm':>12} {'fit ppm':>10} {'fit-native ppm':>15} "
          f"{'residual ppm':>13} {'rms px':>8}")
    t5 = [{"planted": 0.0, "recovered": -base["eps"], **base}]
    print(f"{0.0:12.1f} {-base['eps']*PPM:10.2f} {0.0:15.2f} {0.0:13.2f} "
          f"{base['rms']:8.4f}")
    lyr, lxr = lateral.lattice_offset("R")
    for e in [-1000e-6, -500e-6, -200e-6, 200e-6, 500e-6, 1000e-6]:
        dosed = lateral.plant_scale(planes["R"], e)
        u, d = [], []
        for (y, x) in keep:
            dy, dx = lateral.subpix(g1[y:y + TILE, x:x + TILE],
                                    dosed[y:y + TILE, x:x + TILE])
            u.append(lateral.field_position(y, x, TILE, "G1", sensel_shape))
            d.append((dy - lyr, dx - lxr))
        f = lateral.fit_model(np.array(u), np.array(d), robust=True)
        got = -f["eps"]
        delta = got - (-base["eps"])
        print(f"{e*PPM:12.1f} {got*PPM:10.2f} {delta*PPM:15.2f} "
              f"{(delta-e)*PPM:13.2f} {f['rms']:8.4f}")
        t5.append({"planted": e, "recovered": got, **f})
    pl = np.array([r["planted"] for r in t5])
    fi = np.array([r["recovered"] for r in t5])
    A = np.stack([pl, np.ones_like(pl)], 1)
    slope, icpt = np.linalg.lstsq(A, fi, rcond=None)[0]
    print(f"\nrecovery slope {slope:.6f}   intercept {icpt*PPM:+.2f} ppm  "
          f"(native {-base['eps']*PPM:+.2f} ppm)")
    out["T5"] = {"gate": gate, "ladder": t5, "slope": float(slope),
                 "intercept": float(icpt), "native": -base["eps"]}

    common.dump("c0_lateral", out)
    print("\nwrote c0_lateral.json")


if __name__ == "__main__":
    main()
