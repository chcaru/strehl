"""M41 step 2 -- run the six pre-registered arms + controls on the real stacks.

Kill condition committed in PREREGISTRATION.md (commit f809772) before this ran.
Reads only; never writes to C:\\dev\\macro or D:\\.
"""
import os, sys, glob, json, time
import numpy as np
import rawpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m41lib as L

OUT = L.OUT
PAD = 32


def load_two(files, roiA, roiB, pad=PAD):
    """One decode pass, two crops.  Decode is the dominant cost; do not pay twice."""
    def bounds(r):
        x, y, w, h = r
        return x - pad, y - pad, x + w + pad, y + h + pad
    ax0, ay0, ax1, ay1 = bounds(roiA)
    bx0, by0, bx1, by1 = bounds(roiB)
    A = np.empty((len(files), ay1 - ay0, ax1 - ax0), np.float32)
    B = np.empty((len(files), by1 - by0, bx1 - bx0), np.float32)
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            v = r.raw_image_visible
            for dst, (x0, y0, x1, y1) in ((A, (ax0, ay0, ax1, ay1)), (B, (bx0, by0, bx1, by1))):
                g1 = v[2 * y0:2 * y1:2, 2 * x0 + 1:2 * x1 + 1:2].astype(np.float32)
                g2 = v[2 * y0 + 1:2 * y1 + 1:2, 2 * x0:2 * x1:2].astype(np.float32)
                dst[i] = 0.5 * (g1 + g2) - L.BLACK
    return A, B


def core(cube):
    return cube[PAD:-PAD, PAD:-PAD] if cube.ndim == 2 else cube[:, PAD:-PAD, PAD:-PAD]


def build_arms(cube, g, rn_e, s, order=None):
    fine, coarse, reg = L.focus_fields(cube, g, rn_e)
    out = {}
    a, wA, nA = L.arm_A(cube, coarse, reg)
    out["A"] = a
    out["B"] = L.arm_B(cube, fine)[0]
    out["C"] = L.arm_C(cube)
    out["D"] = L.arm_wiener(cube, reg, g, rn_e, s, True, True, order)
    out["D'"] = L.arm_wiener(cube, reg, g, rn_e, s, False, True, order)
    out["E"] = L.arm_wiener(cube, reg, g, rn_e, s, True, False, order)
    return out, float(nA.mean()), reg


def oor(arm, cube):
    lo = cube.min(0); hi = cube.max(0)
    return float(np.mean((arm < lo - 1e-6) | (arm > hi + 1e-6)))


def run_stack(name, info, log):
    files = sorted(glob.glob(os.path.join(info["dir"], "*.ARW")))
    g, rn_e = info["g"], info["rn_e"]
    det, flat = tuple(info["detail_roi"]), tuple(info["flat_roi"])
    t0 = time.time()
    Dc, Fc = load_two(files, det, flat)
    log(f"[{name}] decoded {len(files)} frames, detail {det} flat {flat}, "
        f"{time.time()-t0:.1f}s")

    _, coarseD, regD = L.focus_fields(Dc, g, rn_e)
    s, fw_meas, fw_mod = L.calibrate_s(core(Dc), core(coarseD), g, rn_e, True)
    log(f"[{name}] SELF-CALIBRATED blur growth s = {s:.4f} quad px/frame "
        f"(through-focus FWHM measured {fw_meas:.1f} frames, modelled {fw_mod:.1f})")

    res = {"s": s, "fwhm_meas": fw_meas, "fwhm_model": fw_mod, "n": len(files),
           "detail_roi": det, "flat_roi": flat}

    # ---- RULE 9: the flat-ROI control runs FIRST -------------------------
    armsF, neffF, _ = build_arms(Fc, g, rn_e, s)
    midF = core(Fc[len(files) // 2])
    ref_sd, ref_hp = float(midF.std()), L.hp_sd(midF)
    log(f"[{name}] FLAT ROI, single middle frame: SPATIAL sd {ref_sd:.3f} DN, "
        f"high-pass SPATIAL sd {ref_hp:.3f} DN  (rule 10: these are SPATIAL, "
        f"never compared to a temporal sigma)")
    res["flat"] = {}
    for k, v in armsF.items():
        c = core(v)
        res["flat"][k] = dict(sd=float(c.std()), hp_sd=L.hp_sd(c),
                              sd_ratio=float(c.std()) / ref_sd,
                              hp_ratio=L.hp_sd(c) / ref_hp,
                              oor=oor(c, core(Fc)))
        log(f"    flat {k:2s}: sd {c.std():8.3f} ({res['flat'][k]['sd_ratio']:.3f}x)  "
            f"hp_sd {res['flat'][k]['hp_sd']:8.3f} ({res['flat'][k]['hp_ratio']:.3f}x)  "
            f"out-of-range {res['flat'][k]['oor']*100:.3f}%")
    res["n_eff_flat"] = neffF

    # ---- detail ROI, full-stack arms -------------------------------------
    armsD, neffD, _ = build_arms(Dc, g, rn_e, s)
    res["n_eff_detail"] = neffD
    log(f"[{name}] arm A mean accepted frame count n_eff = {neffD:.2f} (detail ROI)")
    res["detail"] = {}
    for k, v in armsD.items():
        c = core(v)
        lo, hi = L.band_power(c)
        res["detail"][k] = dict(sd=float(c.std()), hp_sd=L.hp_sd(c),
                                oor=oor(c, core(Dc)),
                                p_below=lo, p_above=hi, p_ratio=hi / max(lo, 1e-30))
        log(f"    det  {k:2s}: sd {c.std():9.2f}  hp_sd {L.hp_sd(c):8.3f}  "
            f"oor {res['detail'][k]['oor']*100:6.3f}%  "
            f"P(>f_sig)/P(<f_sig) {hi/max(lo,1e-30):.3e}")

    # ---- split-half FRC ---------------------------------------------------
    ev, od = np.arange(0, len(files), 2), np.arange(1, len(files), 2)
    aE, _, _ = build_arms(Dc[ev], g, rn_e, s)
    aO, _, _ = build_arms(Dc[od], g, rn_e, s)
    res["frc"] = {}
    for k in armsD:
        ff, fr, _ = L.frc(core(aE[k]).astype(np.float64), core(aO[k]).astype(np.float64))
        x = L.frc_cross(ff, fr)
        res["frc"][k] = dict(cross=x, curve=[float(v) for v in fr],
                             freq=[float(v) for v in ff])
        log(f"    FRC  {k:2s}: 1/7 crossing {x:.4f} cyc/px   "
            f"FRC@0.10 {np.interp(0.10, ff, fr):.3f}  FRC@0.20 {np.interp(0.20, ff, fr):.3f}  "
            f"FRC@0.35 {np.interp(0.35, ff, fr):.3f}")

    # ---- CONTROL: permutation null ---------------------------------------
    rng = np.random.default_rng(41)
    perm = rng.permutation(len(files))
    dP = L.arm_wiener(Dc, regD, g, rn_e, s, True, True, perm)
    aEp = L.arm_wiener(Dc[ev], L.focus_fields(Dc[ev], g, rn_e)[2], g, rn_e, s, True, True,
                       rng.permutation(len(ev)))
    aOp = L.arm_wiener(Dc[od], L.focus_fields(Dc[od], g, rn_e)[2], g, rn_e, s, True, True,
                       rng.permutation(len(od)))
    ffp, frp, _ = L.frc(core(aEp).astype(np.float64), core(aOp).astype(np.float64))
    res["perm"] = dict(cross=L.frc_cross(ffp, frp), hp_sd=L.hp_sd(core(dP)))
    log(f"[{name}] PERMUTATION NULL: D with shuffled frame->OTF assignment, "
        f"FRC 1/7 crossing {res['perm']['cross']:.4f} cyc/px "
        f"(D was {res['frc']['D']['cross']:.4f})")

    # ---- CONTROL: circularity (self-calibrated s vs +-2x) -----------------
    res["circ"] = {}
    for lab, ss in (("s/2", s * 0.5), ("2s", s * 2.0)):
        e2 = L.arm_wiener(Dc[ev], L.focus_fields(Dc[ev], g, rn_e)[2], g, rn_e, ss, True, True)
        o2 = L.arm_wiener(Dc[od], L.focus_fields(Dc[od], g, rn_e)[2], g, rn_e, ss, True, True)
        f2, r2, _ = L.frc(core(e2).astype(np.float64), core(o2).astype(np.float64))
        res["circ"][lab] = dict(s=ss, cross=L.frc_cross(f2, r2))
        log(f"[{name}] CIRCULARITY: s={ss:.4f} ({lab}) FRC 1/7 crossing "
            f"{res['circ'][lab]['cross']:.4f} cyc/px")
    return res


def main():
    with open(os.path.join(OUT, "rois_b.json")) as fh:
        rois = json.load(fh)
    # a1b can return a ROI flush against the active-area edge (y=0); the PAD
    # margin the focus operator needs would then run off the sensor.  Nudge the
    # origin inward by exactly PAD.  Recorded in the results so the shift is
    # visible, not silent.
    for k, v in rois.items():
        for key in ("detail_roi", "flat_roi"):
            x, y, w, h = v[key]
            v[key] = [max(PAD, x), max(PAD, y), w, h]
    fh = open(os.path.join(OUT, "a2_run.log"), "w", encoding="utf-8")

    def log(m):
        print(m); fh.write(m + "\n"); fh.flush()

    log("M41 -- six pre-registered merge arms.  Kill condition: commit f809772.")
    log(f"f_sig = {L.F_SIG} cyc/px (fact 27).  gate = {L.GATE}.  tile {L.TILE}/{L.STEP}.")
    all_res = {}
    for name in ("109MSDCF", "119MSDCF"):
        all_res[name] = run_stack(name, rois[name], log)
        log("")
    with open(os.path.join(OUT, "a2_results.json"), "w") as g:
        json.dump(all_res, g, indent=2)
    log("wrote out/a2_results.json")
    fh.close()


if __name__ == "__main__":
    main()
