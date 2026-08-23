"""M41 step 4 -- REPLACES the arm-A implementation used in a2_run.py.

What was wrong with a2_run.py's arm A (rule 15: new name, new script, say what
broke).  Two things, both read out of crates/strehl-core/src/merge.rs and
crates/strehl-cli/src/merge_cmd.rs AFTER a2_run.py had already run:

  1. THE FOCUS OPERATOR.  a2_run.py used a box mean of the SQUARED gradient
     (Tenengrad).  The shipped operator is a box mean of the sigma-NORMALISED
     gradient MAGNITUDE -- merge.rs:104-131 states the response is a mean of
     |grad|/sigma, Rayleigh with scale 0.125*sqrt(12) = 0.4330 per sample.
     Different operator, different gate units.
  2. THE GATE.  a2_run.py admitted frames within 50% of PEAK HEIGHT, a
     FRACTIONAL rule.  The shipped rule (merge.rs:140-186) is ABSOLUTE and
     noise-scaled: admit when `best - focus <= t * sqrt(2) * FOCUS_NOISE_SD`
     with FOCUS_NOISE_SD = 0.015214.  A fractional gate is not the shipped
     merge; it admitted n_eff = 10.4 and 15.6 frames where the project's
     calibration target (fact 212) is n_eff = 3.

Neither merge.rs nor through_focus.rs was edited -- M40 owns both.  The two
constants and the two rules were READ and re-implemented here, which is what the
M41 brief permits and asks to be disclosed.

This script also runs the check that a2_run.py could not: push a PURE NOISE
plane through this Python operator and read the sd of the regularised interior
response.  The shipped constant is 0.015214.  If Python does not reproduce it
the re-implementation is wrong and the arm-A column is not the shipped merge.
That control CAN fail.
"""
import os, sys, glob, json, time
import numpy as np
import rawpy
from scipy.ndimage import uniform_filter, sobel
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m41lib as L
from a2_run import load_two, core, oor, PAD

OUT = L.OUT
FOCUS_NOISE_SD = 0.015214          # merge.rs:131, MEASURED there
SQRT2 = np.sqrt(2.0)
WIN = 27                           # WINDOW_RADIUS 13
REG = 17                           # REGULARISER_RADIUS 8
FINE = 5                           # FINE_WINDOW_RADIUS 2


def shipped_focus(plane, g, rn_e, w=WIN):
    """Box mean of the sigma-normalised gradient magnitude.
    Rule 23: `plane` is already 2-D; sobel is never given a cube."""
    gx = sobel(plane, axis=1) / 8.0
    gy = sobel(plane, axis=0) / 8.0
    mag = np.sqrt(gx * gx + gy * gy)
    m = uniform_filter(plane, w)
    sig = np.sqrt(np.maximum(0.5 * (g * np.maximum(m, 0.0) + (rn_e * g) ** 2), 1e-9))
    return uniform_filter(mag / sig, w)


def fields(cube, g, rn_e):
    n = cube.shape[0]
    fine = np.empty_like(cube); reg = np.empty_like(cube)
    for k in range(n):
        fine[k] = shipped_focus(cube[k], g, rn_e, FINE)
        reg[k] = uniform_filter(shipped_focus(cube[k], g, rn_e, WIN), REG)
    return fine, reg


def arm_A_shipped(cube, reg, t):
    best = reg.max(0)
    acc = (best[None] - reg) <= (t * SQRT2 * FOCUS_NOISE_SD)
    n = acc.sum(0).astype(np.float32)
    return (cube * acc).sum(0) / np.maximum(n, 1.0), float(n.mean())


def solve_gate(cube, reg, target=3.0):
    lo, hi = 0.0, 200.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        _, ne = arm_A_shipped(cube, reg, mid)
        if ne < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def noise_constant_check(p):
    """The control that can fail: pure noise through this operator."""
    rng = np.random.default_rng(41)
    sds = []
    for _ in range(6):
        g, rn = 0.11447, 4.20
        level = 2000.0
        sig = np.sqrt(0.5 * (g * level + (rn * g) ** 2))
        plane = level + rng.normal(0, sig, (512, 512)).astype(np.float32)
        r = uniform_filter(shipped_focus(plane, g, rn, WIN), REG)
        sds.append(float(r[64:-64, 64:-64].std()))
    return float(np.mean(sds)), float(np.std(sds))


def main():
    fh = open(os.path.join(OUT, "a4_run.log"), "w", encoding="utf-8")

    def p(m):
        print(m); fh.write(m + "\n"); fh.flush()

    mu, sd = noise_constant_check(None)
    p("M41 step 4 -- shipped-rule arm A.  Kill condition: commit f809772.")
    p(f"CONTROL (can fail): pure-noise regularised focus sd = {mu:.6f} +- {sd:.6f}")
    p(f"                    shipped FOCUS_NOISE_SD          = {FOCUS_NOISE_SD:.6f}"
      f"   ratio {mu/FOCUS_NOISE_SD:.4f}x")
    if not (0.7 < mu / FOCUS_NOISE_SD < 1.4):
        p("  *** the re-implementation does NOT reproduce the shipped constant; "
          "arm A below is a PROXY, not the shipped merge ***")

    with open(os.path.join(OUT, "rois_b.json")) as g0:
        rois = json.load(g0)
    for k, v in rois.items():
        for key in ("detail_roi", "flat_roi"):
            x, y, w, h = v[key]
            v[key] = [max(PAD, x), max(PAD, y), w, h]

    allres = {"noise_const": dict(measured=mu, sd=sd, shipped=FOCUS_NOISE_SD)}
    for name in ("109MSDCF", "119MSDCF"):
        info = rois[name]
        files = sorted(glob.glob(os.path.join(info["dir"], "*.ARW")))
        g, rn_e = info["g"], info["rn_e"]
        Dc, Fc = load_two(files, tuple(info["detail_roi"]), tuple(info["flat_roi"]))
        _, regD = fields(Dc, g, rn_e)
        _, regF = fields(Fc, g, rn_e)
        t3 = solve_gate(Dc, regD, 3.0)
        aD, neD = arm_A_shipped(Dc, regD, t3)
        aF, neF = arm_A_shipped(Fc, regF, t3)
        p(f"\n[{name}] {len(files)} frames.  gate solved for n_eff=3 (fact 212): "
          f"t = {t3:.4f}; detail n_eff {neD:.2f}, flat n_eff {neF:.2f}")
        # also the shipped default ladder, so the reading is not one gate's luck
        for t in (0.5, 1.0, 2.0, 4.0):
            _, ne = arm_A_shipped(Dc, regD, t)
            p(f"    gate ladder t={t:>4}: detail n_eff {ne:5.2f}")

        mid = core(Fc[len(files) // 2])
        ref_sd, ref_hp = float(mid.std()), L.hp_sd(mid)
        cF = core(aF); cD = core(aD)
        row = dict(t=t3, n_eff_detail=neD, n_eff_flat=neF,
                   flat_sd=float(cF.std()), flat_sd_ratio=float(cF.std()) / ref_sd,
                   flat_hp=L.hp_sd(cF), flat_hp_ratio=L.hp_sd(cF) / ref_hp,
                   flat_oor=oor(cF, core(Fc)),
                   det_hp=L.hp_sd(cD), det_oor=oor(cD, core(Dc)),
                   ref_sd=ref_sd, ref_hp=ref_hp)
        p(f"    flat A(shipped rule): sd {row['flat_sd']:.3f} ({row['flat_sd_ratio']:.3f}x)  "
          f"hp_sd {row['flat_hp']:.3f} ({row['flat_hp_ratio']:.3f}x)  "
          f"oor {row['flat_oor']*100:.3f}%")
        # split-half FRC for the shipped-rule arm A, same protocol as a2_run
        ev, od = np.arange(0, len(files), 2), np.arange(1, len(files), 2)
        _, rE = fields(Dc[ev], g, rn_e); _, rO = fields(Dc[od], g, rn_e)
        e, _ = arm_A_shipped(Dc[ev], rE, t3); o, _ = arm_A_shipped(Dc[od], rO, t3)
        ff, fr, _ = L.frc(core(e).astype(np.float64), core(o).astype(np.float64))
        row["frc_cross"] = L.frc_cross(ff, fr)
        row["frc_at"] = {f"{q:.2f}": float(np.interp(q, ff, fr)) for q in (0.10, 0.20, 0.35, 0.45)}
        p(f"    FRC A(shipped rule): 1/7 crossing {row['frc_cross']:.4f} cyc/px  "
          + "  ".join(f"FRC@{k} {v:.3f}" for k, v in row["frc_at"].items()))
        allres[name] = row
    with open(os.path.join(OUT, "a4_results.json"), "w") as g1:
        json.dump(allres, g1, indent=2)
    p("\nwrote out/a4_results.json")
    fh.close()


if __name__ == "__main__":
    main()
