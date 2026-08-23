"""M6 primary measurement: the three real stacks.

Run `m6_selftest.py` and `m6_controls.py` first. Nothing here is interpretable
unless both pass, because this file only computes statistics — the controls are
what establish that those statistics mean what they claim to mean.

    python m6_measure.py            # everything
    python m6_measure.py --halo     # deliverable 2 only (seconds)
    python m6_measure.py --cause    # deliverable 1 only

Output is written to stdout and to `out/measure.txt` by the README's command
line, which is what the report quotes.
"""

from __future__ import annotations

import sys

import numpy as np

import m6_lib as L

STACKS = [
    # (case, csv prefix, index-map TIFF, n frames, aperture, ISO)
    ("109MSDCF", "data/109MSDCF", "out/109MSDCF-index.tiff", 22, "f/11", 160),
    ("119MSDCF", "data/119MSDCF", "out/119MSDCF-index.tiff", 33, "f/5.6", 50),
    ("coffee-bean", "data/coffee-bean", "out/coffee-bean-index.tiff", 105, "f/8", 50),
]
TILE_SIZES = (64, 128, 256)
#: Estimator noise floor on real texture, MEASURED by M3 §0 and reproduced by
#: this crate's `--synthetic` mode.
M3_NOISE_FLOOR_PX = 0.19


def bar(title):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


# ---------------------------------------------------------------------------
# Deliverable 1
# ---------------------------------------------------------------------------


def measure_cause():
    bar("DELIVERABLE 1 - SYNTHESIS q6: what IS the 0.6-1.3 px residual?")
    res = {}
    for case, prefix, index_tiff, nfr, ap, iso in STACKS:
        t = L.load_tiles(prefix, case)
        focus = L.load_focus(prefix, case)
        fits = L.load_fits(prefix, case, grid="m6")
        direct = fits.select(fits.ref == 0)
        w, pk, prof = L.winner_index(focus)
        ox, oy = L.scale_centre(direct)
        res[case] = dict(
            t=t, w=w, pk=pk, fits=fits, direct=direct, ox=ox, oy=oy,
            nfr=nfr, ap=ap, iso=iso, index_tiff=index_tiff, prefix=prefix,
        )

    # -- 0. the depth label ------------------------------------------------
    print("\n0. THE DEPTH LABEL  (registered per-tile focus profile, ring measure)")
    print(f"  {'stack':<14}{'n frames':>9}{'pk median':>11}{'frac>gate':>11}"
          f"{'w sd':>8}{'w range':>14}{'ident(S1)':>11}")
    for case, r in res.items():
        w, pk = r["w"], r["pk"]
        g = np.isfinite(w)
        r["ident_pre"] = None
        print(
            f"  {case:<14}{r['nfr']:>9}{np.nanmedian(pk):>11.3f}"
            f"{float(np.nanmean(pk > L.PEAKINESS_MIN)):>11.3f}{np.nanstd(w[g]):>8.2f}"
            f"{f'{np.nanmin(w[g]):.1f}-{np.nanmax(w[g]):.1f}':>14}{'':>11}"
        )

    # -- 0b. cross-check the label against the CLI winner-index map ---------
    print("\n0b. CROSS-CHECK: registered focus argmax vs the CLI's own winner-index map")
    print("    The CLI map is built from an UNALIGNED stack, so drift smears it radially")
    print("    by tens of plane px at the corner. Agreement is a sanity check, not a")
    print("    calibration.")
    print(f"  {'stack':<14}{'n tiles':>9}{'Spearman':>10}{'median |diff|':>15}")
    for case, r in res.items():
        try:
            focus = L.load_focus(r["prefix"], case)
            # tile anchor in frame 0 is where the canonical grid lives
            m0 = focus["frame"] == 0
            ids = focus["tile_id"][m0]
            tx, ty = focus["tx"][m0], focus["ty"][m0]
            order = np.argsort(ids)
            wmap = L.winner_from_index_map(r["index_tiff"], tx[order], ty[order])
            wi = r["w"][ids[order]]
            good = np.isfinite(wmap) & np.isfinite(wi)
            r["w_map"] = wmap
            print(
                f"  {case:<14}{int(good.sum()):>9}{L._spearman(wmap[good], wi[good]):>10.3f}"
                f"{float(np.median(np.abs(wmap[good] - wi[good]))):>15.2f}"
            )
        except Exception as e:  # noqa: BLE001
            print(f"  {case:<14}  index-map cross-check unavailable: {e}")

    # -- 1. S1 -------------------------------------------------------------
    print("\n1. S1 - the pre-stated discriminating statistic")
    print("   res[i,j] = alpha[i] + beta[j] + gamma*|c[j] - w[i]| + eps")
    print("   gamma > 0 => cause (b) blur-induced correlation bias")
    print("   gamma ~ 0 => not (b); consistent with cause (a) depth-dependent magnification")
    print("   floor from the N0-integer real-data null: gamma = +0.000003 +/- 0.000032 px/frame")
    print(f"\n  {'stack':<14}{'variant':<22}{'gamma':>11}{'+/-SE':>9}{'ident':>8}"
          f"{'p_perm':>9}{'p_torus':>9}{'n':>8}  verdict")
    for case, r in res.items():
        for label, ctl in (
            ("plain", ()),
            ("+contrast,peak", ("logcontrast", "peak")),
            ("+contrast,peak,radius", ("logcontrast", "peak", "radius")),
        ):
            g = L.s1_gamma(r["t"], r["w"], controls=ctl)
            if label == "plain":
                r["s1"] = g
            v = "FIRES" if g.fires else ("unidentified" if not g.identified else "quiet")
            print(
                f"  {case:<14}{label:<22}{g.gamma:>+11.5f}{g.se_cluster:>9.5f}{g.ident:>8.4f}"
                f"{g.p_perm:>9.4f}{g.p_torus:>9.4f}{g.n:>8d}  {v}"
            )

    print("\n1b. S1 by baseline: does the coupling strengthen with frame separation?")
    print(f"  {'stack':<14}{'delta':>7}{'gamma':>11}{'+/-SE':>9}{'ident':>8}{'p_torus':>9}{'n':>8}")
    for case, r in res.items():
        for dl in np.unique(r["t"].delta):
            sub = r["t"].select(r["t"].delta == dl)
            if sub.ok.sum() < 200:
                continue
            g = L.s1_gamma(sub, r["w"], n_perm=199)
            print(
                f"  {case:<14}{int(dl):>7}{g.gamma:>+11.5f}{g.se_cluster:>9.5f}"
                f"{g.ident:>8.4f}{g.p_torus:>9.4f}{g.n:>8d}"
            )

    # -- 2. S5, the direct form of the same question ----------------------
    print("\n2. S5 - the brief's own prediction, computed directly")
    print("   Within each baseline, mean residual of tiles IN FOCUS in both frames")
    print(f"   (|c-w| <= 2) against tiles far from focus (|c-w| >= 8).")
    print("   Under (b) the in-focus residual should fall to the 0.19 px estimator floor.")
    print("   Under (a) it should not care.")
    for case, r in res.items():
        s5 = L.s5_infocus_residual(r["t"], r["w"])
        r["s5"] = s5
        print(f"\n  {case}:")
        print(f"    {'delta':>6}{'n in-focus':>12}{'res in':>9}{'n far':>9}{'res far':>10}{'gap':>9}")
        for dl, na, ra, nb, rb, gap in s5["rows"]:
            print(f"    {dl:>6}{na:>12}{ra:>9.3f}{nb:>9}{rb:>10.3f}{gap:>+9.3f}")
        print(
            f"    weighted gap = {s5['gap_px']:+.4f} px   torus null p = {s5['p_torus']:.4f}"
            f"   (torus sd {s5['torus_sd']:.4f})"
        )
        print(
            f"    within-PAIR gap  = {s5['gap_within_pair']:+.4f} px  "
            f"p = {s5['p_torus_pair']:.4f}  ({s5['n_pair_groups']} pair groups)"
            f"   [removes 'this pair aligns badly']"
        )
        print(
            f"    within-TILE gap  = {s5['gap_within_tile']:+.4f} px  "
            f"p = {s5['p_torus_tile']:.4f}  ({s5['n_tile_groups']} tile groups)"
            f"   [removes texture, contrast, field position exactly]"
        )
        infoc = [row[2] for row in s5["rows"]]
        if infoc:
            print(
                f"    mean in-focus residual over baselines = {np.mean(infoc):.3f} px"
                f"  vs estimator floor {M3_NOISE_FLOOR_PX:.2f} px"
                f"  -> {np.mean(infoc) / M3_NOISE_FLOOR_PX:.2f}x the floor"
            )

    # -- 3. S2 -------------------------------------------------------------
    print("\n3. S2 - cause (a)'s own signature: a depth-organised RADIAL scale anomaly")
    print("   dg[i] = e_rad / |u - o| is how much tile i's depth scales differently from")
    print("   the global fit. Magnification is monotone in object distance, so under (a)")
    print("   dg must be monotone in depth. Torus null on the same statistic.")
    print(f"  {'stack':<14}{'rho(dg,w)':>11}{'p_tor':>8}{'rho(res,|w-mid|)':>18}{'p_tor':>8}"
          f"{'sd_rad':>9}{'sd_tan':>9}{'aniso':>8}")
    for case, r in res.items():
        s2 = L.s2_scale_anomaly(r["t"], r["w"], r["ox"], r["oy"])
        r["s2"] = s2
        print(
            f"  {case:<14}{s2['rho_dg_w']:>+11.3f}{s2['p_torus_dg']:>8.4f}"
            f"{s2['rho_res_absw']:>+18.3f}{s2['p_torus_v']:>8.4f}"
            f"{s2['sd_rad']:>9.3f}{s2['sd_tan']:>9.3f}{s2['aniso']:>8.3f}"
        )
    print("   N0-integer null anisotropy for reference: see out/controls.txt section 3.")

    # -- 4. S4 -------------------------------------------------------------
    print("\n4. S4 - the censoring channel: does the aligner DROP tiles by defocus?")
    print("   A tile that fails the correlation gate contributes no residual, so a")
    print("   defocus-driven rejection rate censors exactly the tiles (b) predicts.")
    for case, r in res.items():
        s4 = L.s4_rejection(r["t"], r["w"])
        r["s4"] = s4
        print(
            f"  {case:<14} reject rate {s4['overall']:.3f}   "
            f"slope {s4['slope_per_frame']:+.5f} +/- {s4['se']:.5f} per frame of mismatch"
        )
        print("      " + "  ".join(f"|c-w| {int(lo)}-{'inf' if hi > 1e8 else int(hi)}: "
                                   f"{rate:.3f} (n={n})" for lo, hi, n, rate in s4["bins"]))

    # -- 5. S6: is it a BIAS or just VARIANCE? -----------------------------
    print("\n5. S6 - the architecture question: peak BIAS or peak VARIANCE?")
    print("   A symmetric defocus PSF does not move a correlation peak, it only flattens")
    print("   it -> larger random error, no preferred direction. A peak that is actually")
    print("   DISPLACED needs an asymmetric, field-dependent PSF. Only the second would")
    print("   make a lens plugin genuine computation (SYNTHESIS section 3.4.2).")
    print("   Signed blur asymmetry a[i,j] = |mov-w| - |ref-w| (>0: moving frame blurrier).")
    print("   Regressed on the RADIAL residual, with TANGENTIAL as the placebo channel.")
    print(f"  {'stack':<14}{'b_rad':>10}{'+/-SE':>9}{'p_tor':>8}{'b_tan':>10}{'+/-SE':>9}"
          f"{'b_x':>10}{'b_y':>10}{'n':>8}")
    for case, r in res.items():
        s6 = L.s6_signed_bias(r["t"], r["w"], r["ox"], r["oy"])
        r["s6"] = s6
        print(
            f"  {case:<14}{s6['b_rad']:>+10.5f}{s6['se_rad']:>9.5f}{s6['p_torus_rad']:>8.4f}"
            f"{s6['b_tan']:>+10.5f}{s6['se_tan']:>9.5f}"
            f"{s6['b_x']:>+10.5f}{s6['b_y']:>+10.5f}{s6['n']:>8}"
        )
    print("\n   S7 - variance decomposition inside each tile and defocus bin.")
    print("   |mean vector|^2 is de-biased by scatter^2/n before it is called a bias.")
    print("   Both terms average over the SAME set of pairs: no spatial-sd vs temporal-sigma.")
    for case, r in res.items():
        print(f"  {case}:")
        print(f"      {'|c-w| bin':<12}{'tiles':>7}{'bias px':>10}{'scatter px':>12}{'bias/scatter':>14}")
        for lo, hi, cnt, b, s, ratio in L.s7_bias_variance(r["t"], r["w"]):
            lbl = f"{int(lo)}-{'inf' if hi > 1e8 else int(hi)}"
            print(f"      {lbl:<12}{cnt:>7}{b:>10.3f}{s:>12.3f}{ratio:>14.3f}")

    # -- 6. how much of the residual does it explain? ----------------------
    print("\n6. EFFECT SIZE - how much of the measured residual does the defocus term carry?")
    print(f"  {'stack':<14}{'mean res':>10}{'sd within':>11}{'gamma':>10}"
          f"{'typ |c-w|':>11}{'gamma*|c-w|':>13}{'as % of res':>13}{'partial R2':>12}")
    for case, r in res.items():
        g = r["s1"]
        typ = float(np.mean(g.extra["d_range"]))
        pred = g.gamma * typ
        print(
            f"  {case:<14}{g.extra['mean_res']:>10.3f}{g.extra['sd_within']:>11.3f}"
            f"{g.gamma:>+10.5f}{typ:>11.1f}{pred:>+13.3f}"
            f"{100 * pred / g.extra['mean_res']:>12.1f}%{g.r2:>12.4f}"
        )

    return res


# ---------------------------------------------------------------------------
# Deliverable 2
# ---------------------------------------------------------------------------


def measure_halo():
    bar("DELIVERABLE 2 - SYNTHESIS q10: how big is the halo actually?")
    print("\nPure arithmetic on M3's fitted per-frame similarities. For every output tile,")
    print("the bounding box of S_k^-1(tile) over all frames k, expressed as the symmetric")
    print("halo the tile needs in the source frame. Plane px; sensor px = 2x plane px.")

    out = {}
    for case, prefix, _idx, nfr, ap, iso in STACKS:
        fits = L.load_fits(prefix, case, grid="m6")
        direct = fits.select(fits.ref == 0)
        anchor = L.load_fits(prefix, case, grid="anchor")
        anchor = anchor.select(anchor.mov > 0)
        ox, oy = L.scale_centre(direct)
        out[case] = dict(direct=direct, anchor=anchor, ox=ox, oy=oy, nfr=nfr, ap=ap, iso=iso)

    print("\n1. THE FITS THE ARITHMETIC RESTS ON")
    print(f"  {'stack':<14}{'ap':>6}{'frames':>8}{'fits':>6}{'g at k=max':>12}"
          f"{'total drift':>13}{'scale centre (plane px)':>26}")
    for case, r in out.items():
        d = r["direct"]
        kmax = int(d.mov.max())
        gmax = float(d.g[np.argmax(np.abs(d.g))])
        print(
            f"  {case:<14}{r['ap']:>6}{r['nfr']:>8}{len(d.g):>6}{gmax:>12.6f}"
            f"{100 * gmax:>12.4f}%{f'({r[chr(111) + chr(120)]:+.1f}, {r[chr(111) + chr(121)]:+.1f})':>26}"
        )

    print("\n2. FIT QUALITY - the caveat that has to travel with the coffee-bean numbers")
    print(f"  {'stack':<14}{'fits':>6}{'median used':>13}{'min used':>10}{'median rms':>12}{'max rms':>10}")
    for case, r in out.items():
        d = r["direct"]
        print(
            f"  {case:<14}{len(d.g):>6}{float(np.median(d.used)):>13.0f}{int(d.used.min()):>10}"
            f"{float(np.median(d.rms)):>12.3f}{float(d.rms.max()):>10.3f}"
        )

    print("\n3. HEADLINE - halo required at the exact plane corner (comparable to B1's '39 px')")
    print("   B1's figure is a *displacement*; a halo is a rectangle expansion, so the")
    print("   directly comparable quantity is max(|dx|,|dy|), not the Euclidean norm.")
    print(f"  {'stack':<14}{'halo, raw fits':>16}{'halo, smoothed':>16}"
          f"{'Euclidean disp':>16}{'halo in sensor px':>19}")
    for case, r in out.items():
        cp = L.corner_halo_point(r["direct"])
        cs = L.corner_halo_point(r["anchor"])
        eu = L.max_drift_corner(r["direct"])
        r["corner_pt"] = cp
        print(f"  {case:<14}{cp:>16.2f}{cs:>16.2f}{eu:>16.2f}{cp * L.SENSOR_SCALE:>19.1f}")

    print("\n3b. IS THE HALO A PROPERTY OF THE LENS OR OF THE STACK?")
    print("    Corner halo when only the first N frames of the stack are used. A scalar")
    print("    halo() on a lens plugin is a compile-time constant and cannot see N.")
    print(f"  {'stack':<14}" + "".join(f"{f'N={n}':>10}" for n in (5, 10, 20, 30, 50, 100)))
    for case, r in out.items():
        d = r["direct"]
        row = ""
        for n in (5, 10, 20, 30, 50, 100):
            m = d.mov <= n
            row += f"{L.corner_halo_point(d.select(m)):>10.2f}" if m.sum() else f"{'-':>10}"
        print(f"  {case:<14}{row}")

    print("\n4. PER-TILE HALO BY TILE SIZE")
    for case, r in out.items():
        print(f"\n  {case}  ({r['ap']}, {r['nfr']} frames)")
        print(f"    {'tile':>6}{'n':>6}{'min':>8}{'median':>9}{'mean':>8}{'max':>8}"
              f"{'centre':>8}{'corner':>8}{'max/med':>9}{'area waste':>12}")
        for tile in TILE_SIZES:
            h = L.halo_table(r["direct"], tile, r["ox"], r["oy"])
            print(
                f"    {tile:>6}{h['n_tiles']:>6}{h['min_halo']:>8.2f}{h['median_halo']:>9.2f}"
                f"{h['mean_halo']:>8.2f}{h['max_halo']:>8.2f}{h['centre_halo']:>8.2f}"
                f"{h['corner_halo']:>8.2f}{h['ratio_max_median']:>9.2f}{h['area_waste']:>11.2f}x"
            )
        h = L.halo_table(r["direct"], 128, r["ox"], r["oy"])
        r["h128"] = h
        print(f"    128 px halo vs radius from the scale centre:")
        print(f"      {'radius (plane px)':>19}{'mean halo':>11}{'max halo':>10}{'n':>5}")
        for rad, hm, hx, n in h["profile"]:
            print(f"      {rad:>19.0f}{hm:>11.2f}{hx:>10.2f}{n:>5}")
        print(f"      linear fit: halo = {h['slope_px_per_px']:.6f} * radius "
              f"{h['intercept_px']:+.3f} px  (Spearman rho "
              f"{L._spearman(h['radius'], h['halo']):.3f})")

    print("\n5. DOES A SCALAR halo() SURVIVE?")
    print("   A scalar halo() must be set to the maximum over the frame. Everything")
    print("   nearer the scale centre then pays for a margin it does not use.")
    print(f"  {'stack':<14}{'tile':>6}{'scalar halo':>13}{'mean needed':>13}"
          f"{'median needed':>15}{'tiles needing <10%':>20}{'gather area waste':>19}")
    for case, r in out.items():
        for tile in TILE_SIZES:
            h = L.halo_table(r["direct"], tile, r["ox"], r["oy"])
            frac_small = float(np.mean(h["halo"] < 0.1 * h["max_halo"]))
            print(
                f"  {case:<14}{tile:>6}{h['scalar_halo_px']:>13.2f}{h['mean_halo']:>13.2f}"
                f"{h['median_halo']:>15.2f}{100 * frac_small:>19.1f}%{h['area_waste']:>18.2f}x"
            )

    print("\n6. STACK DEPENDENCE")
    ratios = []
    for case, r in out.items():
        h = r["h128"]
        ratios.append(h["ratio_max_median"])
        print(
            f"  {case:<14} total drift {100 * float(r['direct'].g[np.argmax(np.abs(r['direct'].g))]):+.3f}%"
            f"   corner halo {L.corner_halo_point(r['direct']):.2f} px"
            f"   max/median at 128 px {h['ratio_max_median']:.2f}"
            f"   area waste {h['area_waste']:.2f}x"
        )
    print(f"\n  The absolute halo scales with total drift and is therefore stack-dependent.")
    print(f"  The max/median SHAPE ratio at 128 px spans {min(ratios):.2f}-{max(ratios):.2f}"
          f" across the three stacks.")

    print("\n7. THE COST OF A SCALAR halo() THAT MUST SERVE ALL THREE STACKS")
    print("   A `halo() -> usize` on a lens plugin is answered once, without seeing the")
    print("   stack. It must therefore be sized for the worst stack the lens will ever")
    print("   shoot. This is what every other stack then pays.")
    worst = max(L.corner_halo_point(r["direct"]) for r in out.values())
    print(f"   worst-case scalar over these three stacks = {worst:.2f} plane px "
          f"({worst * L.SENSOR_SCALE:.1f} sensor px)")
    print(f"  {'stack':<14}{'tile':>6}{'needed (mean)':>15}{'scalar':>9}"
          f"{'gather area waste':>19}{'vs per-stack scalar':>21}")
    for case, r in out.items():
        for tile in TILE_SIZES:
            h = L.halo_table(r["direct"], tile, r["ox"], r["oy"])
            need = np.mean((tile + 2 * h["halo"]) ** 2)
            cross = (tile + 2 * worst) ** 2 / need
            print(
                f"  {case:<14}{tile:>6}{h['mean_halo']:>15.2f}{worst:>9.2f}"
                f"{cross:>18.2f}x{h['area_waste']:>20.2f}x"
            )
    return out


def main():
    args = set(sys.argv[1:])
    do_cause = not args or "--cause" in args
    do_halo = not args or "--halo" in args
    print(f"M6 primary measurement.  constants: TILE_PX={L.TILE_PX} grid={L.GRID_NX}x{L.GRID_NY} "
          f"N_PERM={L.N_PERM} SEED={L.SEED} PEAKINESS_MIN={L.PEAKINESS_MIN}")
    if do_cause:
        measure_cause()
    if do_halo:
        measure_halo()


if __name__ == "__main__":
    main()
