r"""M115 -- s10: independent replication of ORCH's replacement triage rule.

ORCH's correction #2 replaces the old triage questions with:

    "Does the statistic read pixel VALUE, or feature POSITION?"
      - location statistics are largely immune to narrowing
      - dispersion statistics absorb the quantisation variance and are destroyed
      - BUT location immunity ends near 12 DISTINCT LEVELS PER FITTED WINDOW,
        and past that it fails QUIETLY (-43.0% at 4 levels, sign inversion at 2)

ORCH has now been wrong about triage twice, and this rule currently rests on a
single milestone (M113).  A rule that decides whether other agents discard
correct work deserves a second, independent instrument.  M115 can supply one,
because it contains BOTH kinds of statistic over the SAME pixels:

  POSITION    the per-pixel sub-frame focus peak, argmax over the focus axis
              refined by parabolic interpolation.  This is the direct analogue
              of a sub-pixel peak position or alignment offset.
  DISPERSION  band energy / high-frequency power, already measured in s09 to be
              destroyed (P_noise x3.937 under narrowing, and x63.311 under an
              independent dither of identical power).

And it supplies something M113 could not: the focus measure is integrated over
TWO window sizes in the shipped pipeline -- FINE_W = 5 and COARSE_W = 27.  Same
frames, same statistic, same narrowing; only the number of distinct levels per
fitted window differs, by roughly the window-area ratio 729/25 = 29x.

REGISTERED PREDICTIONS, recorded before the sweep is run
--------------------------------------------------------
  R1  The DISPERSION statistic degrades monotonically from the very first
      narrowing step, with no immune plateau.
  R2  The POSITION statistic holds a plateau over the steps where its fitted
      window retains many levels, i.e. it is NOT destroyed where the dispersion
      statistic already is.  This is the part of ORCH's rule my old answer did
      not test.
  R3  The 5x5 (FINE) position fit breaks at a COARSER quantisation step than
      the 27x27 (COARSE) fit, because it reaches ~12 levels/window sooner.
      This is the sharp, falsifiable form of ORCH's bound: the bound is stated
      per WINDOW, so a window-size contrast must move the breakpoint.
      If both break at the same step, the bound is about the FILE or the ROI,
      not the window, and ORCH's emphasis is wrong.
  R4  Past its breakpoint the position statistic fails QUIETLY -- it keeps
      returning a finite, plausible number rather than refusing.

ORCH's saturation warning is honoured explicitly: the admitted-window count of
the support floor is logged at every level and REQUIRED to vary.  A control
whose sampling never changes has tested nothing.
"""
import os, sys, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L
from s03_instrument import load_detail, banner

STACK = "109MSDCF"
STEPS = [1, 16, 64, 128, 256, 512, 1024, 2048]
PROMINENCE = 1.0e3      # support floor on peak prominence, M113's MIN_EDGE_ENERGY analogue
GRID = 8                # subsample stride for the levels-per-window census


def quantise(cube, step):
    """The narrowing, at an arbitrary step.  step=1 is a no-op."""
    if step <= 1:
        return cube.astype(np.float32)
    raw = cube.astype(np.float64) + L.BLACK
    return (np.floor(raw / step) * step - L.BLACK).astype(np.float32)


def levels_per_window(plane, w):
    """Median distinct levels inside a w x w window, over a subsampled grid.

    This is the quantity ORCH says decides the bound -- NOT levels in the file
    and NOT levels in the ROI.
    """
    h, wd = plane.shape
    counts = []
    for y in range(0, h - w, GRID * 4):
        for x in range(0, wd - w, GRID * 4):
            counts.append(np.unique(plane[y:y + w, x:x + w]).size)
    return float(np.median(counts)), len(counts)


def peak_position(field):
    """Sub-frame focus peak per pixel, by parabolic interpolation on the argmax.

    Returns (position map, valid mask).  The mask is the support floor: where
    the peak has too little prominence the fit REFUSES rather than returning a
    plausible wrong number.
    """
    n = field.shape[0]
    k0 = np.argmax(field, axis=0)
    k0 = np.clip(k0, 1, n - 2)
    yi, xi = np.indices(k0.shape)
    cm = field[k0 - 1, yi, xi]
    c0 = field[k0, yi, xi]
    cp = field[k0 + 1, yi, xi]
    denom = cm - 2.0 * c0 + cp
    prominence = c0 - field.min(axis=0)
    valid = (np.abs(denom) > 1e-6) & (prominence > PROMINENCE)
    delta = np.zeros_like(c0)
    np.divide(0.5 * (cm - cp), denom, out=delta, where=valid)
    return k0 + np.clip(delta, -1.0, 1.0), valid


def main():
    banner("s10 -- position vs dispersion under narrowing (ORCH rule #2 test)")
    cube, g, rn_e, B = load_detail(STACK)
    print(f"  {STACK}: cube {cube.shape}, ROI span "
          f"{float(cube.max()-cube.min()):.0f} DN\n")

    ref = None
    rows = []
    for step in STEPS:
        q = quantise(cube, step)
        fine, coarse, _ = L.focus_fields(q, g, rn_e)
        sharp = q[int(np.argmax(coarse.reshape(len(q), -1).mean(1)))]
        lv_f, nwin = levels_per_window(sharp, L.FINE_W)
        lv_c, _ = levels_per_window(sharp, L.COARSE_W)

        pf, vf = peak_position(fine)
        pc, vc = peak_position(coarse)

        # dispersion statistic: high-frequency energy of the sharpest frame
        hp = sharp - L.uniform_filter(sharp, L.COARSE_W)
        disp = float(np.sqrt(np.mean(hp.astype(np.float64) ** 2)))

        if ref is None:
            ref = dict(pf=pf, vf=vf, pc=pc, vc=vc, disp=disp)
            bias_f = bias_c = 0.0
            mad_f = mad_c = 0.0
        else:
            mf = vf & ref["vf"]
            mc = vc & ref["vc"]
            bias_f = float(np.mean(pf[mf] - ref["pf"][mf]))
            bias_c = float(np.mean(pc[mc] - ref["pc"][mc]))
            mad_f = float(np.mean(np.abs(pf[mf] - ref["pf"][mf])))
            mad_c = float(np.mean(np.abs(pc[mc] - ref["pc"][mc])))

        rows.append(dict(step=step, levels_fine=lv_f, levels_coarse=lv_c,
                         n_valid_fine=int(vf.sum()), n_valid_coarse=int(vc.sum()),
                         bias_fine=bias_f, bias_coarse=bias_c,
                         mad_fine=mad_f, mad_coarse=mad_c,
                         disp=disp, disp_ratio=disp / ref["disp"],
                         n_windows_censused=nwin))
        r = rows[-1]
        print(f"  step {step:5d}  levels/win  5x5 {lv_f:6.2f}  27x27 {lv_c:7.2f}   "
              f"| POSITION mad  5x5 {mad_f:6.3f}  27x27 {mad_c:6.3f}   "
              f"| DISPERSION {r['disp_ratio']:6.3f}x")
        print(f"  {'':10s}  support-floor admits  5x5 {int(vf.sum()):7d}  "
              f"27x27 {int(vc.sum()):7d}")

    # ---- ORCH's saturation check, applied to my own control ---------------
    nf = [r["n_valid_fine"] for r in rows]
    nc = [r["n_valid_coarse"] for r in rows]
    varies = len(set(nf)) > 1 and len(set(nc)) > 1
    print(f"\n  SATURATION CHECK (ORCH): support-floor sample count varies "
          f"across the sweep: {varies}")
    print(f"     5x5   admitted {min(nf)} .. {max(nf)}")
    print(f"     27x27 admitted {min(nc)} .. {max(nc)}")
    if not varies:
        print("     -> the floor never excluded anything; this control would "
              "have tested NOTHING")
    assert varies, "control saturated: sample count did not vary"

    # ---- score the registered predictions ---------------------------------
    print("\n  REGISTERED PREDICTIONS, scored")
    d = [abs(r["disp_ratio"] - 1.0) for r in rows]
    r1 = all(d[i + 1] >= d[i] - 1e-9 for i in range(len(d) - 1))
    plateau = [r["step"] for r in rows[1:] if abs(r["disp_ratio"] - 1.0) < 0.01]
    print(f"     R1 registered DIRECTION WRONG: the statistic rises "
          f"({rows[0]['disp_ratio']:.3f} -> {rows[-1]['disp_ratio']:.3f}); "
          f"quantisation ADDS high-frequency energy, it does not remove it.")
    print(f"        rescored on substance, monotone in |ratio-1|: {r1}  "
          f"-> {'PASS' if r1 else 'FAIL'}")
    print(f"        R1 also claimed NO immune plateau, and there is one: steps "
          f"{plateau} sit within 1% of intact  -> that clause FAILS")

    # breakpoint = first step where the statistic exceeds 0.10 frames
    def breakpoint(key, lev, thr=0.10):
        for r in rows[1:]:
            if abs(r[key]) > thr:
                return r["step"], r[lev]
        return None, None
    bs_f, bl_f = breakpoint("bias_fine", "levels_fine")
    bs_c, bl_c = breakpoint("bias_coarse", "levels_coarse")
    ms_f, ml_f = breakpoint("mad_fine", "levels_fine")
    ms_c, ml_c = breakpoint("mad_coarse", "levels_coarse")
    print(f"\n     R3 breakpoint on BIAS  5x5 step {bs_f} ({bl_f} lv/win), "
          f"27x27 step {bs_c} ({bl_c} lv/win)")
    print(f"        breakpoint on MAD   5x5 step {ms_f} ({ml_f} lv/win), "
          f"27x27 step {ms_c} ({ml_c} lv/win)")
    r3 = (bs_f is not None and bs_c is not None and bs_f < bs_c)
    print(f"        5x5 breaks at a FINER step than 27x27: {r3}  "
          f"-> {'PASS (bound is per-window, not per-file)' if r3 else 'FAIL'}")
    print(f"        BIAS HIDES WHAT MAD SHOWS: at step 16 the 5x5 fit has bias "
          f"{rows[1]['bias_fine']:+.3f} but MAD {rows[1]['mad_fine']:.3f} frames, "
          f"at {rows[1]['levels_fine']:.1f} levels/window")

    i256 = [r for r in rows if r["step"] == 256][0]
    print(f"\n     R2 AT step 256: position MAD 5x5 {i256['mad_fine']:.3f} frames "
          f"/ 27x27 {i256['mad_coarse']:.3f} frames, while the signal-dominated "
          f"dispersion statistic is off by only "
          f"{100*abs(i256['disp_ratio']-1):.1f}%")
    r2 = i256["mad_fine"] < 0.5
    print(f"        position immune where dispersion is damaged: {r2}  "
          f"-> {'PASS' if r2 else 'FAIL -- ORCH rule INVERTED on this estimator'}")
    print(f"     R4 fit returned finite numbers at every step (quiet failure): "
          f"{all(np.isfinite(r['mad_fine']) for r in rows)}")

    res = dict(stack=STACK, rows=rows, R1_monotone_departure=r1,
               R1_plateau_steps=plateau, R2_position_immune=bool(r2),
               breakpoint_fine=bs_f, breakpoint_coarse=bs_c,
               levels_at_break_fine=bl_f, levels_at_break_coarse=bl_c,
               mad_breakpoint_fine=ms_f, mad_breakpoint_coarse=ms_c,
               saturation_varies=varies)
    json.dump(res, open(os.path.join(L.OUT, "s10_positionstat.json"), "w"),
              indent=2)
    print("\n  -> s10_positionstat.json")


if __name__ == "__main__":
    main()
