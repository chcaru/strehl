"""M46 step b1 -- build the TWO-CAPTURE Fourier ring correlation on the corpus's
only same-subject independent pair, 112MSDCF / 113MSDCF.

Registered in PREREGISTRATION.md sec 4.1, committed as 2474e5d before this file
existed.  Question 118, assigned.

WHY THIS IS NOT THE SAME MEASUREMENT M41 MADE.  M41's split was even/odd frames
of ONE capture.  Both halves share the scene AND the fixed pattern, and fact 478
measured the consequence: recovery scales as (1 - rho) in the common-mode
fraction, which fact 476 measured at 0.63-0.98 on real data.  Two independent
captures share the fixed pattern ONLY.

THE THREE WAYS THIS MEASUREMENT CAN BE FAKED, and what is done about each.
Written before the run (rule 20).

  1. PHOTOMETRY.  The pair is one stop apart.  If the stop is exposure TIME the
     longer capture collected twice the photons and is genuinely quieter; if it
     is ISO it is not.  Read from EXIF, never assumed.  The photon-transfer
     model is evaluated on each capture's OWN UNSCALED DN and the variance is
     carried through the scale as c^2 var -- registered ordering.  The measured
     scale is checked against the EXIF prediction and a >5% disagreement is
     reported as a failure of this step.

  2. MISREGISTRATION.  A sub-pixel shift destroys high-frequency correlation and
     is indistinguishable from "the metric has no power".  Aligned by phase
     correlation, the shift is REPORTED, and a deliberate-misalignment ladder is
     run so the reader can see the size of the effect being guarded against.

  3. DEPTH RANGE.  Fact 50: 113 covers only 112's frames 5.5 -> 66.6 of 0 -> 78.
     Merging all of 112 against all of 113 would compare different depth ranges
     and read the difference as resolution.  112 is restricted to the overlap.

The merge is m41lib.arm_A, imported frozen and unmodified: regularised winner
field plus the merge_cmd.rs "within 50% of peak height" gate.  Its Python
re-implementation was verified at 1.0101x the Rust FOCUS_NOISE_SD (fact 460).
No gate is solved for here -- that would be one more free parameter -- and the
resulting mean n_eff is reported as an OUTPUT.
"""
import os, sys, glob, json, time
import numpy as np
import exifread
from scipy.ndimage import uniform_filter, sobel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m46lib as M
import m41lib as L1

B = 512
PAD = 32
STACKS = {"112MSDCF": r"D:\personal\macro\112MSDCF",
          "113MSDCF": r"D:\personal\macro\113MSDCF"}


def exif_of(p):
    t = exifread.process_file(open(p, "rb"), details=False)
    def g(k):
        return str(t[k]) if k in t else None
    iso = g("EXIF ISOSpeedRatings")
    return dict(iso=int(iso.split(",")[0].strip("[] ")) if iso else None,
                exposure=g("EXIF ExposureTime"), fnum=g("EXIF FNumber"),
                focal=g("EXIF FocalLength"), when=g("EXIF DateTimeOriginal"),
                model=g("Image Model"))


def frac(s):
    if s is None:
        return None
    if "/" in s:
        a, b = s.split("/")
        return float(a) / float(b)
    return float(s)


def pick_rois(files, g, rn_e):
    """a1b_rois.py's WINDOW-MEAN procedure, applied unchanged to a new stack.
    a1_rois.py scored the centre pixel and returned a 'flat' ROI carrying 50-148x
    the modelled sigma; that is the version NOT used here."""
    acc_max, acc_mean = None, None
    for f in files[::max(1, len(files) // 6)]:
        q = M.quad_green(f)
        gx = sobel(q, axis=1); gy = sobel(q, axis=0)
        e = gx * gx + gy * gy
        m = uniform_filter(q, B)
        eB = uniform_filter(e, B)
        t = eB - 24.0 * M.noise_var_dn(m, g, rn_e)
        acc_max = t if acc_max is None else np.maximum(acc_max, t)
        if acc_mean is None:
            acc_mean = m
    h, w = acc_max.shape
    half = B // 2
    valid = np.zeros_like(acc_max, bool)
    valid[half + PAD:h - half - PAD, half + PAD:w - half - PAD] = True
    lvl = (acc_mean > 120) & (acc_mean < 13000)
    sc = np.where(valid & lvl, acc_max, -np.inf)
    iy, ix = np.unravel_index(np.argmax(sc), sc.shape)
    det = (int(ix - half), int(iy - half), B, B)
    sc2 = np.where(valid & lvl, acc_max, np.inf)
    jy, jx = np.unravel_index(np.argmin(sc2), sc2.shape)
    flat = (int(jx - half), int(jy - half), B, B)
    return det, flat, (int(w), int(h))


def load_two(files, rois, pad):
    """Decode once per frame and cut BOTH ROIs out of it -- half the decodes of
    two separate load_cube passes, and byte-identical output."""
    import rawpy
    outs = []
    for (x, y, w, h) in rois:
        outs.append(np.empty((len(files), h + 2 * pad, w + 2 * pad), np.float32))
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            v = r.raw_image_visible
            for j, (x, y, w, h) in enumerate(rois):
                x0, y0, x1, y1 = x - pad, y - pad, x + w + pad, y + h + pad
                g1 = v[2 * y0:2 * y1:2, 2 * x0 + 1:2 * x1 + 1:2].astype(np.float32)
                g2 = v[2 * y0 + 1:2 * y1 + 1:2, 2 * x0:2 * x1:2].astype(np.float32)
                outs[j][i] = 0.5 * (g1 + g2) - M.BLACK
    return outs


def merge_A(cube, g, rn_e):
    fine, coarse, reg = L1.focus_fields(cube, g, rn_e)
    m, w, n = L1.arm_A(cube, coarse, reg)
    return m, float(n.mean())


def core(a, pad=PAD):
    return a[pad:-pad, pad:-pad]


def main():
    t0 = time.time()
    res = {}
    print("=" * 78)
    print("M46 b1 -- TWO-CAPTURE FRC on 112MSDCF / 113MSDCF")
    print("=" * 78)

    # ---------------------------------------------------------- 1. EXIF
    print("\n1. THE EXPOSURE DIFFERENCE, READ NOT ASSUMED")
    ex = {}
    files = {}
    for k, d in STACKS.items():
        fs = sorted(glob.glob(os.path.join(d, "*.ARW")))
        files[k] = fs
        ex[k] = exif_of(fs[0])
        e = ex[k]
        print(f"   {k}: {len(fs)} frames  ISO {e['iso']}  t={e['exposure']}s  "
              f"f/{e['fnum']}  {e['focal']}mm  {e['when']}  {e['model']}")
    t112, t113 = frac(ex["112MSDCF"]["exposure"]), frac(ex["113MSDCF"]["exposure"])
    iso_same = ex["112MSDCF"]["iso"] == ex["113MSDCF"]["iso"]
    stops = np.log2(t113 / t112)
    print(f"   ISO identical: {iso_same}.  exposure ratio t113/t112 = {t113/t112:.4f} "
          f"= {stops:+.4f} stops")
    print("   MECHANISM: the stop is EXPOSURE TIME, not gain." if iso_same else
          "   MECHANISM: the stop involves GAIN.")
    print("   CONSEQUENCE, stated before the scale is measured: gain g and read")
    print("   noise in DN are IDENTICAL, 113 collected 2x the photons, so after")
    print("   photometric rescaling by c=1/2 it is strictly QUIETER than 112 --")
    print("   var -> c^2 var with the model evaluated on unscaled DN.")
    res["exif"] = dict(ex=ex, t112=t112, t113=t113, stops=float(stops),
                       iso_same=bool(iso_same))

    iso = ex["112MSDCF"]["iso"]
    g = iso / 436.8
    rn_e = 1.47 if iso >= 400 else 4.20
    print(f"   calibration: g = {g:.5f} DN/e-, rn_e = {rn_e} (M41's constants)")

    # ---------------------------------------------------------- 2. ROIs
    print("\n2. ROI SELECTION (a1b window-mean procedure, unchanged)")
    det, flat, plane = pick_rois(files["112MSDCF"], g, rn_e)
    print(f"   plane {plane[0]}x{plane[1]}  detail {det}  flat {flat}")
    res["rois"] = dict(detail=det, flat=flat, plane=plane, iso=iso, g=g, rn_e=rn_e)

    # ---------------------------------------- 3. global shift 112 -> 113
    print("\n3. GLOBAL REGISTRATION between the two captures")
    q112 = M.quad_green(files["112MSDCF"][len(files["112MSDCF"]) // 2])
    q113 = M.quad_green(files["113MSDCF"][len(files["113MSDCF"]) // 2])
    sub = 4
    dy, dx = M.phase_shift(q112[::sub, ::sub], q113[::sub, ::sub])
    gdy, gdx = int(round(dy * sub)), int(round(dx * sub))
    print(f"   coarse plane shift (113 -> 112): dy={gdy} px  dx={gdx} px "
          f"(from a {sub}x-decimated plane)")
    if max(abs(gdy), abs(gdx)) > PAD:
        print(f"   *** shift exceeds PAD={PAD}; ROI offset applied so the pad still covers it")
    res["global_shift"] = [gdy, gdx]

    # ------------------------------------------------- 4. depth matching
    n112, n113 = len(files["112MSDCF"]), len(files["113MSDCF"])
    lo, hi = 5.5, 66.6                      # fact 50
    i0, i1 = int(round(lo)), int(round(hi)) + 1
    sel112 = files["112MSDCF"][i0:i1]
    sel113 = files["113MSDCF"]
    print("\n4. DEPTH-RANGE MATCHING (fact 50)")
    print(f"   113 covers 112's frames {lo} -> {hi} of 0 -> {n112 - 1}.")
    print(f"   112 restricted to indices {i0}..{i1-1} ({len(sel112)} frames); "
          f"113 uses all {len(sel113)}.")
    res["depth"] = dict(n112=n112, n113=n113, i0=i0, i1=i1,
                        used112=len(sel112), used113=len(sel113))

    # ------------------------------------------------------- 5. decode
    print("\n5. DECODE + MERGE (m41lib.arm_A, imported frozen)")
    rois112 = [det, flat]
    rois113 = [(det[0] - gdx, det[1] - gdy, B, B), (flat[0] - gdx, flat[1] - gdy, B, B)]
    td = time.time()
    c112 = load_two(sel112, rois112, PAD)
    print(f"   112: {len(sel112)} frames x 2 ROIs in {time.time()-td:.1f}s")
    td = time.time()
    c113 = load_two(sel113, rois113, PAD)
    print(f"   113: {len(sel113)} frames x 2 ROIs in {time.time()-td:.1f}s")

    merges, neff = {}, {}
    for tag, cubes in (("112", c112), ("113", c113)):
        for j, rn in enumerate(["detail", "flat"]):
            m, ne = merge_A(cubes[j], g, rn_e)
            merges[(tag, rn)] = m
            neff[(tag, rn)] = ne
            print(f"   arm A {tag} {rn:6s}: mean n_eff = {ne:.3f}")
    res["n_eff"] = {f"{a}_{b}": v for (a, b), v in neff.items()}

    # ------------------------------------------------ 6. photometric scale
    print("\n6. PHOTOMETRIC SCALE (registered ordering: model on unscaled DN)")
    cs = {}
    for rn in ("detail", "flat"):
        c = M.photometric_scale(core(merges[("112", rn)]), core(merges[("113", rn)]))
        cs[rn] = c
        print(f"   {rn:6s}: median112/median113 = {c:.4f}")
    c_pred = t112 / t113
    c_meas = cs["detail"]
    err = abs(c_meas - c_pred) / c_pred
    print(f"   EXIF prediction c = t112/t113 = {c_pred:.4f}; measured (detail) "
          f"{c_meas:.4f}; disagreement {100*err:.2f}%")
    print("   CHECK: " + ("PASS (<=5%)" if err <= 0.05 else "*** FAIL (>5%) ***"))
    res["scale"] = dict(measured=cs, predicted=c_pred, err=float(err),
                        passed=bool(err <= 0.05))

    lvl112 = float(np.median(core(merges[("112", "flat")])))
    lvl113 = float(np.median(core(merges[("113", "flat")])))
    v112 = float(M.noise_var_dn(lvl112, g, rn_e))
    v113 = float(M.noise_var_dn(lvl113, g, rn_e))
    print(f"   flat ROI level: 112 {lvl112:.1f} DN -> model sd {np.sqrt(v112):.3f} DN")
    print(f"                   113 {lvl113:.1f} DN -> model sd {np.sqrt(v113):.3f} DN")
    print(f"   after scaling 113 by c={c_meas:.4f}: its sd becomes "
          f"{c_meas*np.sqrt(v113):.3f} DN, i.e. {c_meas*np.sqrt(v113)/np.sqrt(v112):.4f}x 112's.")
    print("   That ratio being BELOW 1 is the registered prediction and is what a")
    print("   longer exposure at equal gain must do.  The two halves of this FRC")
    print("   are therefore NOT equal-noise, which FRC tolerates (it is a")
    print("   normalised correlation) but which is stated rather than hidden.")
    res["levels"] = dict(lvl112=lvl112, lvl113=lvl113, sd112=float(np.sqrt(v112)),
                         sd113=float(np.sqrt(v113)),
                         sd113_scaled=float(c_meas * np.sqrt(v113)))

    # --------------------------------------------- 7. align + two-cap FRC
    print("\n7. TWO-CAPTURE FRC")
    out = {}
    for rn in ("detail", "flat"):
        a = merges[("112", rn)]
        b = merges[("113", rn)] * c_meas
        sy, sx = M.phase_shift(core(a), core(b))
        bal = M.fshift(b, sy, sx)
        A, Bc = core(a), core(bal)
        ff, fr = M.frc_curve(A, Bc)
        cr, cen = M.frc_cross_c(A, Bc)
        at = M.frc_at(A, Bc)
        print(f"   {rn:6s}: residual sub-pixel shift dy={sy:+.3f} dx={sx:+.3f} px")
        print(f"           FRC 1/7 crossing = {cr:.4f} cyc/px"
              f"{'  [CENSORED -- a LOWER BOUND, fact 475]' if cen else ''}")
        print(f"           FRC at f_sig={M.F_SIG} = {at:+.4f}")
        print(f"           curve @ 0.10/0.20/0.2762/0.35/0.45: " +
              " ".join(f"{np.interp(f, ff, fr):+.4f}" for f in (.10, .20, .2762, .35, .45)))
        out[rn] = dict(shift=[float(sy), float(sx)], cross=cr, censored=bool(cen),
                       at_fsig=at, ff=ff.tolist(), fr=fr.tolist())
    res["twocap"] = out

    dc, fc = out["detail"], out["flat"]
    print("\n   RULE 9 READING -- the flat ROI next to the detail ROI, same pass:")
    for f in (.10, .20, .2762, .35, .45):
        d = np.interp(f, np.array(dc["ff"]), np.array(dc["fr"]))
        fl = np.interp(f, np.array(fc["ff"]), np.array(fc["fr"]))
        print(f"     f={f:.4f}  detail {d:+.4f}   flat {fl:+.4f}   "
              f"flat/detail {fl/d if abs(d)>1e-6 else float('nan'):+.4f}")

    # ------------------------------------------- 8. split-half comparison
    print("\n8. CONTROL -- SPLIT-HALF WITHIN ONE CAPTURE (M41's split), same ROIs")
    for rn, j in (("detail", 0), ("flat", 1)):
        ev = c112[j][0::2]; od = c112[j][1::2]
        me, _ = merge_A(ev, g, rn_e)
        mo, _ = merge_A(od, g, rn_e)
        cr, cen = M.frc_cross_c(core(me), core(mo))
        at = M.frc_at(core(me), core(mo))
        print(f"   112 {rn:6s}: crossing {cr:.4f}{' [CENSORED]' if cen else ''}   "
              f"at f_sig {at:+.4f}")
        res.setdefault("splithalf", {})[rn] = dict(cross=cr, censored=bool(cen), at_fsig=at)

    # --------------------------------------- 9. misalignment control
    print("\n9. CONTROL -- DELIBERATE MISALIGNMENT (rule 20: this is the input")
    print("   that would make a working metric look powerless)")
    a = core(merges[("112", "detail")])
    b0 = merges[("113", "detail")] * c_meas
    sy, sx = out["detail"]["shift"]
    lad = []
    for extra in (0.0, 0.25, 0.5, 1.0, 2.0, 4.0):
        bb = core(M.fshift(b0, sy + extra, sx))
        cr, cen = M.frc_cross_c(a, bb)
        at = M.frc_at(a, bb)
        lad.append(dict(extra=extra, cross=cr, censored=bool(cen), at_fsig=at))
        print(f"   +{extra:4.2f} px: crossing {cr:.4f}{' [CENS]' if cen else '      '}"
              f"   at f_sig {at:+.4f}")
    res["misalign"] = lad

    np.savez_compressed(os.path.join(M.OUT, "b1_merges.npz"),
                        d112=merges[("112", "detail")], f112=merges[("112", "flat")],
                        d113=merges[("113", "detail")], f113=merges[("113", "flat")],
                        c=c_meas, shift_d=out["detail"]["shift"],
                        shift_f=out["flat"]["shift"])
    with open(os.path.join(M.OUT, "b1_results.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print(f"\nwrote out/b1_results.json and out/b1_merges.npz  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
