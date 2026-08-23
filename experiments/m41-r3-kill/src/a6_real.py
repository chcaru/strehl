"""M41 step 6 -- THE RUN OF RECORD.  Six arms, both stacks, all controls.

Supersedes a2_run.py entirely.  a2_run.py had two defects, both found and
documented before this script was written:
  * its arm A used a fractional gate and a squared-gradient focus operator,
    neither of which is the shipped rule (see a4_shipped_gate.py docstring);
  * its tiled Wiener had a broken overlap-add normalisation (see m41lib2.py
    docstring), caught by the planted positive control at -7.1 dB.
Every arm-A/D/D'/E number in out/a2_run.log is VOID.  Arms B and C are
unaffected by both defects but are recomputed here anyway so that one script
produces the whole table.

Arm A is validated against the shipped code by a control that could fail:
a4_shipped_gate.noise_constant_check pushes pure noise through this Python
operator and reads 0.015367 +- 0.000359 against merge.rs's MEASURED
FOCUS_NOISE_SD = 0.015214, a ratio of 1.0101x.

Read-only corpora are never written.
"""
import os, sys, glob, json, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m41lib as L
import m41lib2 as L2
from a2_run import load_two, core, oor, PAD
from a4_shipped_gate import fields, arm_A_shipped, solve_gate, noise_constant_check

OUT = L.OUT
STACKS = ("109MSDCF", "119MSDCF")


def all_arms(cube, g, rn_e, s, t, order=None):
    fine, reg = fields(cube, g, rn_e)
    a, ne = arm_A_shipped(cube, reg, t)
    return {
        "A": a,
        "B": np.take_along_axis(cube, np.argmax(fine, 0)[None], 0)[0],
        "C": cube.mean(0),
        "D": L2.arm_wiener2(cube, reg, g, rn_e, s, True, True, order),
        "D'": L2.arm_wiener2(cube, reg, g, rn_e, s, False, True, order),
        "E": L2.arm_wiener2(cube, reg, g, rn_e, s, True, False, order),
    }, ne, reg


def main():
    fh = open(os.path.join(OUT, "a6_run.log"), "w", encoding="utf-8")

    def p(m):
        print(m); fh.write(m + "\n"); fh.flush()

    mu, sd = noise_constant_check(None)
    p("M41 RUN OF RECORD.  Kill condition committed in f809772 before any data.")
    p(f"arm-A operator control: pure-noise regularised focus sd {mu:.6f}+-{sd:.6f} "
      f"vs shipped FOCUS_NOISE_SD 0.015214 -> {mu/0.015214:.4f}x")
    p(f"f_sig = {L.F_SIG} cyc/px (fact 27).  tile {L.TILE}/{L.STEP}.  "
      f"gate solved for n_eff = 3 (fact 212).")

    with open(os.path.join(OUT, "rois_b.json")) as g0:
        rois = json.load(g0)
    for k, v in rois.items():
        for key in ("detail_roi", "flat_roi"):
            x, y, w, h = v[key]
            v[key] = [max(PAD, x), max(PAD, y), w, h]

    res = {"operator_control": dict(measured=mu, sd=sd, shipped=0.015214)}
    for name in STACKS:
        info = rois[name]
        files = sorted(glob.glob(os.path.join(info["dir"], "*.ARW")))
        g, rn_e = info["g"], info["rn_e"]
        t0 = time.time()
        Dc, Fc = load_two(files, tuple(info["detail_roi"]), tuple(info["flat_roi"]))
        _, regD = fields(Dc, g, rn_e)
        s, fwm, fwd = L.calibrate_s(core(Dc), core(regD), g, rn_e, True)
        t = solve_gate(Dc, regD, 3.0)
        p(f"\n=== {name}: {len(files)} frames, decode {time.time()-t0:.1f}s, "
          f"detail {info['detail_roi']} flat {info['flat_roi']}")
        p(f"    self-calibrated s = {s:.4f} quad px/frame "
          f"(through-focus FWHM measured {fwm:.1f} frames, modelled {fwd:.1f}); "
          f"gate t = {t:.4f}")
        row = {"s": s, "fwhm_meas": fwm, "fwhm_model": fwd, "gate": t,
               "n": len(files)}

        # ---------------- RULE 9: flat ROI FIRST -------------------------
        armsF, neF, _ = all_arms(Fc, g, rn_e, s, t)
        mid = core(Fc[len(files) // 2])
        ref_sd, ref_hp = float(mid.std()), L.hp_sd(mid)
        p(f"    FLAT ROI single middle frame: SPATIAL sd {ref_sd:.3f} DN, "
          f"high-pass SPATIAL sd {ref_hp:.3f} DN (model sigma "
          f"{np.sqrt(0.5*(g*mid.mean()+(rn_e*g)**2)):.2f} DN)")
        p("      NOISE AXIS.  hp_ratio is the one with power: the raw sd of this "
          "ROI is dominated by residual scene structure.")
        row["flat"] = {}
        for k, v in armsF.items():
            c = core(v)
            row["flat"][k] = dict(sd=float(c.std()), sd_ratio=float(c.std()) / ref_sd,
                                  hp=L.hp_sd(c), hp_ratio=L.hp_sd(c) / ref_hp,
                                  oor=oor(c, core(Fc)))
            r = row["flat"][k]
            p(f"      {k:2s}: sd {r['sd']:9.3f} ({r['sd_ratio']:.3f}x)   "
              f"hp_sd {r['hp']:9.3f} ({r['hp_ratio']:.3f}x)   oor {r['oor']*100:7.3f}%")

        # ---------------- detail ROI --------------------------------------
        armsD, neD, _ = all_arms(Dc, g, rn_e, s, t)
        row["n_eff_detail"] = neD; row["n_eff_flat"] = neF
        p(f"    DETAIL ROI, arm A n_eff = {neD:.2f}")
        row["detail"] = {}
        for k, v in armsD.items():
            c = core(v)
            lo, hi = L.band_power(c)
            row["detail"][k] = dict(sd=float(c.std()), hp=L.hp_sd(c),
                                    oor=oor(c, core(Dc)), p_below=lo, p_above=hi,
                                    p_ratio=hi / max(lo, 1e-30))
            r = row["detail"][k]
            p(f"      {k:2s}: sd {r['sd']:10.2f}  hp_sd {r['hp']:9.3f}  "
              f"oor {r['oor']*100:7.3f}%  P(>f_sig)/P(<f_sig) {r['p_ratio']:.4e}")

        # ---------------- split-half FRC ----------------------------------
        ev, od = np.arange(0, len(files), 2), np.arange(1, len(files), 2)
        aE, _, _ = all_arms(Dc[ev], g, rn_e, s, t)
        aO, _, _ = all_arms(Dc[od], g, rn_e, s, t)
        row["frc"] = {}
        p("      DETAIL AXIS (FRC, split-half).  Rule 18: FRC is a per-ring "
          "CORRELATION and is amplitude-free, so it cannot see how much power an "
          "arm put in a band -- only whether the two halves agree there.")
        for k in armsD:
            ff, fr, _ = L.frc(core(aE[k]).astype(np.float64),
                              core(aO[k]).astype(np.float64))
            x = L.frc_cross(ff, fr)
            row["frc"][k] = dict(cross=x,
                                 at={f"{q:.2f}": float(np.interp(q, ff, fr))
                                     for q in (0.10, 0.20, 0.2762, 0.35, 0.45)},
                                 curve=[float(u) for u in fr],
                                 freq=[float(u) for u in ff])
            a = row["frc"][k]["at"]
            p(f"      {k:2s}: 1/7 crossing {x:.4f} cyc/px   "
              + "  ".join(f"@{q} {a[q]:6.3f}" for q in a))

        # ---------------- CONTROL: permutation null ------------------------
        rng = np.random.default_rng(41)
        pe = L2.arm_wiener2(Dc[ev], fields(Dc[ev], g, rn_e)[1], g, rn_e, s, True, True,
                            rng.permutation(len(ev)))
        po = L2.arm_wiener2(Dc[od], fields(Dc[od], g, rn_e)[1], g, rn_e, s, True, True,
                            rng.permutation(len(od)))
        ffp, frp, _ = L.frc(core(pe).astype(np.float64), core(po).astype(np.float64))
        pfull = L2.arm_wiener2(Dc, regD, g, rn_e, s, True, True, rng.permutation(len(files)))
        row["perm"] = dict(cross=L.frc_cross(ffp, frp), hp=L.hp_sd(core(pfull)),
                           oor=oor(core(pfull), core(Dc)),
                           at={f"{q:.2f}": float(np.interp(q, ffp, frp))
                               for q in (0.20, 0.35)})
        p(f"    PERMUTATION NULL (frame->OTF assignment shuffled): FRC 1/7 "
          f"{row['perm']['cross']:.4f} (D {row['frc']['D']['cross']:.4f}), "
          f"hp_sd {row['perm']['hp']:.3f} (D {row['detail']['D']['hp']:.3f}), "
          f"oor {row['perm']['oor']*100:.2f}% (D {row['detail']['D']['oor']*100:.2f}%)")

        # ---------------- CONTROL: circularity of the self-calibrated s ----
        row["circ"] = {}
        for lab, ss in (("0.5s", 0.5 * s), ("2s", 2.0 * s)):
            e2 = L2.arm_wiener2(Dc[ev], fields(Dc[ev], g, rn_e)[1], g, rn_e, ss, True, True)
            o2 = L2.arm_wiener2(Dc[od], fields(Dc[od], g, rn_e)[1], g, rn_e, ss, True, True)
            f2, r2, _ = L.frc(core(e2).astype(np.float64), core(o2).astype(np.float64))
            full2 = L2.arm_wiener2(Dc, regD, g, rn_e, ss, True, True)
            row["circ"][lab] = dict(s=ss, cross=L.frc_cross(f2, r2),
                                    hp=L.hp_sd(core(full2)),
                                    oor=oor(core(full2), core(Dc)),
                                    at={f"{q:.2f}": float(np.interp(q, f2, r2))
                                        for q in (0.20, 0.35)})
            c = row["circ"][lab]
            p(f"    CIRCULARITY s={ss:.4f} ({lab}): FRC 1/7 {c['cross']:.4f}  "
              f"hp_sd {c['hp']:.3f}  oor {c['oor']*100:.2f}%")
        res[name] = row

    with open(os.path.join(OUT, "a6_results.json"), "w") as g1:
        json.dump(res, g1, indent=2)
    p("\nwrote out/a6_results.json")
    fh.close()


if __name__ == "__main__":
    main()
