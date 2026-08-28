"""V-DILUTE analysis. Usage: python analyze.py {A|B|C}

Every row pairs detail with noise on the same pixels (rule 3), and every band
edge is corrected by that arm's own alignment FOV scale so arms built from
different frame sets are compared at matched SENSOR bandwidth.
"""
import os
import sys
import json
import numpy as np

HERE = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-DILUTE"
sys.path.insert(0, HERE)
import vd_metrics as vd

R = r"D:\strehl-out\V-DILUTE\runs"

# FOV scale is set by the frame set, not the merge flags. The N=22 arms were
# rendered before the queue existed and have no log; 0.9021 was read directly
# off two separate beeN22 runs (X_n22_default_rep, X_n22_e4).
FALLBACK_SCALE = {"A_n22_default": 0.9021, "A_n22_hardmax": 0.9021, "A_n22_meanarm": 0.9021}


def scale_of(tag):
    return vd.fov_scale(rf"{R}\{tag}.log", FALLBACK_SCALE.get(tag))


def have(tag, conf=False):
    p = rf"{R}\{tag}_conf.tif" if conf else rf"{R}\{tag}.tif"
    return os.path.exists(p)


def _tiles():
    """Tile sets chosen ONCE from a single fixed reference and reused for every
    arm, so tile selection cannot respond to the arm under test."""
    ref_tag = "A_n299_default" if have("A_n299_default") else "A_n22_default"
    ref = vd.green(rf"{R}\{ref_tag}.tif")
    tex, flat = vd.select_tiles(ref)
    return ref_tag, tex, flat


# ------------------------------------------------------------------ A

def expA():
    print("EXPERIMENT A -- confidence vs N, bee-3-cpl, full focus range, stride varied")
    print("statistic: 1 - 2|below/seen - 0.5| in milli-units. LOW = committed, HIGH = averaged.\n")
    Ns = [22, 33, 63, 105, 299]
    rows = []
    for n in Ns:
        for arm in ("default", "hardmax", "meanarm"):
            tag = f"A_n{n}_{arm}"
            if not have(tag, conf=True):
                continue
            s = vd.confidence_stats(rf"{R}\{tag}_conf.tif")
            s.update(N=n, arm=arm, tag=tag)
            rows.append(s)
    print(f"{'N':>4} {'arm':>8} {'mean':>7} {'p10':>6} {'p50':>6} {'p90':>6} {'>=800':>7} {'>=900':>7}")
    for r in rows:
        print(f"{r['N']:>4} {r['arm']:>8} {r['mean']:>7.1f} {r['p10']:>6.0f} {r['p50']:>6.0f} "
              f"{r['p90']:>6.0f} {r['frac_ge_800']*100:>6.1f}% {r['frac_ge_900']*100:>6.1f}%")

    # A second, independent instrument that the rank-sampling bias cannot touch.
    #
    # Because every stack here spans the SAME focus range (frames 1..299) and only
    # the stride changes, N is proportional to the number of frames simultaneously
    # near focus at a pixel. So this table is a COMPETITOR-DENSITY sweep at fixed
    # range -- the axis the model actually names -- and not merely a frame count.
    #
    # hard-max inherits ONE frame's noise in the fine bands; the default averages
    # whatever frames clear the gate. Measured at 0.40-0.50 cyc/px -- high
    # frequency, so it lives in the selecting bands and not in the base band,
    # which is an unweighted mean under BOTH arms and would otherwise confound it.
    print("\nDETAIL AND NOISE vs N, bee-3-cpl, FIXED focus range, stride varied")
    print("detail 0.30-0.35 and noise 0.40-0.50 cyc/px on the SAME textured tiles (rule 3).")
    print("'raw' repeats the detail with the magnification correction OFF, so the")
    print("correction cannot quietly carry a trend.\n")
    ref_tag, tex, flat = _tiles()
    print(f"{'N':>4} {'fov s':>7} {'detail(corr)':>13} {'detail(raw)':>12} {'noiseHF':>10} "
          f"{'det/noise':>10} {'n_eff':>7}")
    for n in Ns:
        td, th = f"A_n{n}_default", f"A_n{n}_hardmax"
        if not have(td):
            continue
        s = scale_of(td)
        img = vd.green(rf"{R}\{td}.tif")
        md = vd.measure(img, tex, flat, s)
        raw = vd.band_power(img, tex, 0.30, 0.35)
        neff = ""
        if have(th):
            mh = vd.measure(vd.green(rf"{R}\{th}.tif"), tex, flat, scale_of(th))
            neff = f"{mh['noise_hf_tex'] / md['noise_hf_tex']:7.2f}"
        print(f"{n:>4} {s:>7.4f} {md['detail_30_35']:>13.1f} {raw:>12.1f} "
              f"{md['noise_hf_tex']:>10.1f} {md['detail_30_35']/md['noise_hf_tex']:>10.3f} {neff:>7}")

    print("\nNORMALISED COMMITMENT INDEX  CI = (default - hardmax)/(meanarm - hardmax)")
    print("dimensionless; absorbs the rank-sampling bias because floor and ceiling carry it too.")
    print("0 = as committed as hard-max argmax, 1 = as averaged as an unweighted gated mean.\n")
    print(f"{'N':>4} {'hardmax':>8} {'default':>8} {'meanarm':>8} {'CI':>7} {'analytic null':>14}")
    by = {(r["N"], r["arm"]): r["mean"] for r in rows}
    for n in Ns:
        if (n, "default") in by and (n, "hardmax") in by and (n, "meanarm") in by:
            h, d, m = by[(n, "hardmax")], by[(n, "default")], by[(n, "meanarm")]
            ci = (d - h) / (m - h)
            print(f"{n:>4} {h:>8.1f} {d:>8.1f} {m:>8.1f} {ci:>7.3f} {vd.null_confidence(n):>14.1f}")
        elif (n, "default") in by:
            print(f"{n:>4} {'-':>8} {by[(n,'default')]:>8.1f} {'-':>8} {'-':>7} {vd.null_confidence(n):>14.1f}")


# ------------------------------------------------------------------ B

def expB():
    arms = [("B_step2_n150", "x2 step, FULL range, N=150"),
            ("B_first150_n150", "x1 step, HALF range, N=150"),
            ("B_dup300_n300", "x1 step, HALF range, each frame TWICE, N=300")]
    arms = [(t, d) for t, d in arms if have(t)]
    if not arms:
        print("no B arms yet")
        return
    ref_tag, tex, flat = _tiles()
    print(f"EXPERIMENT B -- equal-N decimation, bee-3-cpl. tiles from {ref_tag}\n")
    res = {}
    for tag, desc in arms:
        s = scale_of(tag)
        img = vd.green(rf"{R}\{tag}.tif")
        m = vd.measure(img, tex, flat, s)
        if have(tag, conf=True):
            m["conf"] = vd.confidence_stats(rf"{R}\{tag}_conf.tif")["mean"]
        res[tag] = m
        print(f"{desc}")
        print(f"  fov_scale {s:.4f} | detail(0.30-0.35) {m['detail_30_35']:.1f} | "
              f"detail(0.20-0.25) {m['detail_20_25']:.1f} | noise(0.40-0.50) {m['noise_40_50']:.1f}"
              + (f" | confidence {m['conf']:.1f}" if 'conf' in m else ""))
    # global ratio
    if "B_step2_n150" in res and "B_first150_n150" in res:
        a, b = res["B_step2_n150"], res["B_first150_n150"]
        print(f"\nGLOBAL x2/x1 detail ratio 0.30-0.35: {a['detail_30_35']/b['detail_30_35']:.4f}"
              f"  noise ratio: {a['noise_40_50']/b['noise_40_50']:.4f}")
        print("  CONFOUNDED -- the x1 arm has no in-focus data for the far half of the subject.")
    # duplication null
    if "B_dup300_n300" in res and "B_first150_n150" in res:
        x = vd.read_rgb(rf"{R}\B_dup300_n300.tif").astype(np.int64)
        y = vd.read_rgb(rf"{R}\B_first150_n150.tif").astype(np.int64)
        d = np.abs(x - y)
        print(f"\nB2 DUPLICATION NULL  first150 (N=150) vs same frames each twice (N=300)")
        print(f"  array_equal      : {np.array_equal(x, y)}")
        print(f"  samples differing: {int((d>0).sum())} of {d.size} = {100.0*(d>0).mean():.4f}%")
        print(f"  max |delta| DN   : {int(d.max())}   mean |delta| DN: {d.mean():.4f}")
        p, q = res['B_dup300_n300'], res['B_first150_n150']
        print(f"  detail 0.30-0.35 : N=300 {p['detail_30_35']:.1f} vs N=150 {q['detail_30_35']:.1f} "
              f"-> ratio {p['detail_30_35']/q['detail_30_35']:.5f}")
        print(f"  noise  0.40-0.50 : N=300 {p['noise_40_50']:.1f} vs N=150 {q['noise_40_50']:.1f} "
              f"-> ratio {p['noise_40_50']/q['noise_40_50']:.5f}")
    json.dump({k: v for k, v in res.items()}, open(rf"{R}\B_results.json", "w"), indent=1)


def expB_roi():
    """The decisive, de-confounded arm: restrict to pixels whose best-focus frame
    lies in the first half of the stack, where BOTH arms own the in-focus frame.

    Geometry. Alignment shrinks the field of view by an arm-specific factor s and
    upsamples back to fixed dimensions, so one output pixel spans s sensor pixels
    and the three products here (index map s=0.9208, x2 arm s=0.9228, x1 arm
    s=0.9595) are NOT pixel-aligned -- up to ~4.2% differential magnification,
    which is ~74 px at the far corner. Images are therefore never resampled
    (resampling blurs, and would blur the two arms by different amounts, biasing
    the very quantity under test). Instead every sample is addressed in a common
    SENSOR frame: a sensor offset x maps to output offset x/s in each product.
    """
    import tifffile
    idx_path = rf"{R}\ROI_index_n63.tif"
    if not (os.path.exists(idx_path) and have("B_step2_n150") and have("B_first150_n150")):
        print("B-ROI: missing inputs")
        return
    idx = tifffile.imread(idx_path)
    s_i = vd.fov_scale(rf"{R}\ROI_index_n63.log")
    n_sub = 63
    # subsampled index -> original frame index; < 150 == inside the x1 arm's range
    near_i = (idx.astype(np.float64) * (298.0 / (n_sub - 1))) < 150.0
    H, W = idx.shape
    cy, cx = H / 2.0, W / 2.0
    print("EXPERIMENT B (ROI) -- the de-confounded, equal-N comparison")
    print(f"index map s={s_i:.4f}, {100.0*near_i.mean():.1f}% of pixels have best focus in frames 0-149\n")

    arms = [("B_step2_n150", "x2 step, FULL range, N=150"),
            ("B_first150_n150", "x1 step, HALF range, N=150")]
    imgs, scales, confs = {}, {}, {}
    for tag, _ in arms:
        imgs[tag] = vd.green(rf"{R}\{tag}.tif")
        scales[tag] = scale_of(tag)
        confs[tag] = tifffile.imread(rf"{R}\{tag}_conf.tif") if have(tag, conf=True) else None

    tile = vd.TILE
    half = tile // 2
    # Grid of candidate tile centres in the SENSOR frame.
    step_sensor = tile
    cands = []
    lim_y = (H / 2.0 - half - 2) * min(scales.values())
    lim_x = (W / 2.0 - half - 2) * min(scales.values())
    yy = np.arange(-lim_y, lim_y, step_sensor)
    xx = np.arange(-lim_x, lim_x, step_sensor)
    for u in yy:
        for v in xx:
            # inside the near-focus region, in the index map's own geometry
            iy, ix = int(round(cy + u / s_i)), int(round(cx + v / s_i))
            if not (half <= iy < H - half and half <= ix < W - half):
                continue
            if near_i[iy - half:iy + half, ix - half:ix + half].mean() < 0.90:
                continue
            cands.append((u, v))
    print(f"candidate tiles fully inside the common-focus region: {len(cands)}")
    if len(cands) < 10:
        print("  too few tiles for a stable ROI number")
        return

    def coords_for(tag):
        s = scales[tag]
        out = []
        for (u, v) in cands:
            y, x = int(round(cy + u / s)) - half, int(round(cx + v / s)) - half
            out.append((y, x))
        return out

    # Texture ranking is SYMMETRIC between the arms -- the mean of both arms'
    # gradient energy at matched sensor locations -- so tile selection cannot
    # favour the arm under test.
    energy = np.zeros(len(cands))
    for tag, _ in arms:
        g = imgs[tag]
        gy, gx = np.gradient(g)
        e = gy * gy + gx * gx
        for k, (y, x) in enumerate(coords_for(tag)):
            energy[k] += e[y:y + tile, x:x + tile].mean() / len(arms)
    order = np.argsort(energy)
    n_each = max(10, len(cands) // 4)
    sel_tex = [cands[i] for i in order[-n_each:]]
    sel_flat = [cands[i] for i in order[:n_each]]
    print(f"textured tiles {len(sel_tex)}, flat tiles {len(sel_flat)} "
          f"(ranked symmetrically across both arms)\n")

    print(f"{'arm':>28} {'detail30-35':>12} {'detail20-25':>12} {'noiseHF(tex)':>13} {'conf':>7}")
    out = {}
    for tag, desc in arms:
        s = scales[tag]
        img = imgs[tag]
        tex = [(int(round(cy + u / s)) - half, int(round(cx + v / s)) - half) for (u, v) in sel_tex]
        flt = [(int(round(cy + u / s)) - half, int(round(cx + v / s)) - half) for (u, v) in sel_flat]
        m = vd.measure(img, tex, flt, s)
        cs = ""
        if confs[tag] is not None:
            cm = confs[tag]
            mask = np.zeros(cm.shape, bool)
            for (y, x) in tex:
                mask[y:y + tile, x:x + tile] = True
            v_ = cm[mask & (cm != vd.UNREACHED)]
            m["conf"] = float(v_.mean())
            cs = f"{m['conf']:7.1f}"
        out[tag] = m
        print(f"{desc:>28} {m['detail_30_35']:>12.1f} {m['detail_20_25']:>12.1f} "
              f"{m['noise_hf_tex']:>13.1f} {cs:>7}")

    a, b = out["B_step2_n150"], out["B_first150_n150"]
    print(f"\n  ROI x2/x1 detail 0.30-0.35 : {a['detail_30_35']/b['detail_30_35']:.4f}")
    print(f"  ROI x2/x1 detail 0.20-0.25 : {a['detail_20_25']/b['detail_20_25']:.4f}")
    print(f"  ROI x2/x1 noise HF (same tiles): {a['noise_hf_tex']/b['noise_hf_tex']:.4f}")
    if "conf" in a and "conf" in b:
        print(f"  ROI confidence  x2 {a['conf']:.1f} vs x1 {b['conf']:.1f}  (LOW = more committed)")
    print("\n  MODEL PREDICTION: the x2 arm (half the near-focus competitors at equal N)")
    print("  should be SHARPER and MORE COMMITTED. Ratio > 1 and lower x2 confidence support it.")


# ------------------------------------------------------------------ C

def expC():
    arms = [("A_n299_default", "2.0 / 1.4  SHIPPED DEFAULT"),
            ("C_e0p5_s1p4", "0.5 / 1.4"),
            ("C_e1_s1p4", "1.0 / 1.4"),
            ("C_e4_s1p4", "4.0 / 1.4"),
            ("C_e8_s1p0", "8.0 / 1.0  uniform cap")]
    arms = [(t, d) for t, d in arms if have(t)]
    if not arms:
        print("no C arms yet")
        return
    ref_tag, tex, flat = _tiles()
    print(f"EXPERIMENT C -- exponent sweep, bee-3-cpl N=299. tiles from {ref_tag}")
    print("every row pairs detail with noise on the same pixels (rule 3)\n")
    print(f"{'exponent/sharpen':>26} {'detail30-35':>12} {'detail20-25':>12} {'noise40-50':>11} "
          f"{'det/def':>8} {'noi/def':>8}")
    base = None
    for tag, desc in arms:
        s = scale_of(tag)
        img = vd.green(rf"{R}\{tag}.tif")
        m = vd.measure(img, tex, flat, s)
        if base is None:
            base = m
        print(f"{desc:>26} {m['detail_30_35']:>12.1f} {m['detail_20_25']:>12.1f} "
              f"{m['noise_40_50']:>11.1f} {m['detail_30_35']/base['detail_30_35']:>8.3f} "
              f"{m['noise_40_50']/base['noise_40_50']:>8.3f}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "A"
    {"A": expA, "B": expB, "BROI": expB_roi, "C": expC}[which]()



