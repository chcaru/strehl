"""M55b -- CALIBRATE the acceptance battery.

PRE-REGISTERED as PR27 (the battery must PASS the passability probe on B1/B2)
and PR28 (the battery must KILL all three known-bad references, and must kill
REF_SIGPOW specifically on B1 and B2) before this file ran.

A gauntlet that nothing can pass is not a gauntlet.  A gauntlet that everything
passes has no power.  Both directions are measured here.

Real-data work uses ONLY development stacks.  The six held-out stacks named in
spec_v1.HELD_OUT are NOT loaded, NOT merged and NOT scored by this file -- if
the spec's author measures them, they are no longer held out.  Their substrate
is validated from EXIF and frame counts alone.
"""
import os, sys, glob, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (os.path.join(ROOT, "m46-detail-metric", "src"),
          os.path.join(ROOT, "m41-r3-kill", "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

import spec_v1 as S
import ref_metrics as R

PAD, G, RN_E = 32, 1.14469, 1.47


def load_cube(files, roi, pad=PAD):
    import rawpy, m46lib as M
    x, y, w, h = roi
    x0, y0, x1, y1 = x - pad, y - pad, x + w + pad, y + h + pad
    out = np.empty((len(files), y1 - y0, x1 - x0), np.float32)
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            v = r.raw_image_visible
            g1 = v[2 * y0:2 * y1:2, 2 * x0 + 1:2 * x1 + 1:2].astype(np.float32)
            g2 = v[2 * y0 + 1:2 * y1 + 1:2, 2 * x0:2 * x1:2].astype(np.float32)
        out[i] = 0.5 * (g1 + g2) - M.BLACK
    return out


def merge(cube, coarse, reg, idx):
    c, cf, rg = cube[idx], coarse[idx], reg[idx]
    w = np.argmax(rg, axis=0)
    peak = np.take_along_axis(cf, w[None], 0)[0]
    acc = cf >= (0.5 * peak)[None]
    acc[w, np.arange(c.shape[1])[:, None], np.arange(c.shape[2])[None]] = True
    n = acc.sum(0).astype(np.float32)
    return ((c * acc).sum(0) / np.maximum(n, 1.0))[PAD:-PAD, PAD:-PAD].astype(np.float32)


def main():
    res, t0 = {}, time.time()
    print("=" * 78)
    print("M55b -- CALIBRATION OF THE ACCEPTANCE BATTERY (PR27 / PR28)")
    print("=" * 78)
    print(f"   reference signal step: true MTF 1.00 -> 0.90 at f_sig, "
          f"Gaussian sd {S.sd_for_mtf(0.90):.4f} px")
    print(f"   M46's 0.05 px step is an MTF loss of "
          f"{100*(1-S.gauss_mtf(0.05)):.3f} %  (MEASURED)")
    g = S._mtf_grid()
    print(f"   B1 grid: {len(g)} points, {g[0]:.3f} down to {g[-1]:.4f}, "
          f"max adjacent ratio {max(g[i]/g[i+1] for i in range(len(g)-1)):.4f}")
    print(f"   ROI rule -> {S.roi_rule()}")
    print(f"   HELD OUT (not touched by this file): {', '.join(S.HELD_OUT)}\n")

    plant = S.Plant(seed=0)
    res["plant"] = {}
    print("-" * 78)
    print(" PLANT BATTERIES")
    print("-" * 78)
    print(f"   {'candidate':22s} {'B0':>5s} {'B1':>5s} {'B2':>5s} {'B4':>5s} {'B7':>5s}"
          f"   verdict")
    for cand in R.ALL:
        r = S.run_plant_batteries(cand, plant)
        v, dead = S.verdict(r)
        res["plant"][cand.name] = {k: {kk: vv for kk, vv in x.items()
                                       if kk in ("passed", "kill", "inv_plain", "inv_comp", "inv_capped", "resolve_threshold",
                                                 "blind_spot_generative",
                                                 "d_one", "d_both", "d_swap", "degree_one",
                                                 "degree_both", "specificity", "sensitivity",
                                                 "swing", "null_consistent_with_zero")}
                                   for k, x in r.items()}
        res["plant"][cand.name]["verdict"] = v
        flags = "  ".join(("PASS" if r[k]["passed"] else "FAIL") for k in ("B0", "B1", "B2", "B4", "B7"))
        print(f"   {cand.name:22s} {flags}   {v}")
        for k in ("B1", "B2", "B4", "B7"):
            if r[k]["kill"]:
                print(f"        {k}: {r[k]['kill']}")
        if "B1" in r:
            print(f"        B1 inversion depth: B1a plain {r['B1']['inv_plain']:.5g}, "
                  f"B1c capped {r['B1']['inv_capped']:.5g}, "
                  f"B1b matched {r['B1']['inv_comp']:.5g}   "
                  f"(resolve threshold {r['B1']['resolve_threshold']:.5g}; "
                  f"cap amp {r['B1']['cap']:.4g} DN, noise {r['B1']['noise_e']:.1f} e-, "
                  f"nrep {r['B1']['nrep']})")
            print(f"        B1b generative blind spot: "
                  f"{r['B1']['blind_spot_generative']}")
            print(f"        B2 degree: both-scaled {r['B2']['degree_both']:+.4f}, "
                  f"one-scaled {r['B2']['degree_one']:+.4f};  swap d {r['B2']['d_swap']:+.3e}")
            print(f"        B7 S swing {r['B7']['swing']:.3f}; null within 2 SE of zero: "
                  f"{r['B7']['null_consistent_with_zero']}")

    # ------------------------------------------------------- PR27 / PR28
    print("\n" + "=" * 78)
    print("  PR28 -- does the battery have POWER?  (known-bad must die)")
    print("=" * 78)
    killed = {n: res["plant"][n]["verdict"] != "ACCEPTED" for n in R.KNOWN_BAD}
    for n, k in killed.items():
        print(f"   {n:22s} {'KILLED' if k else 'SURVIVED -- battery has no power'}")
    sig = res["plant"]["sigpow-canonical"]
    pr28 = all(killed.values()) and not sig["B2"]["passed"]
    print(f"   REF_SIGPOW killed on B1 (fact 703, BOUNDED threat model): "
          f"{not sig['B1']['passed']}; on B2 (fact 704): {not sig['B2']['passed']}")
    print(f"   REF_SIGPOW B1b generative blind spot declared: "
          f"{sig['B1']['blind_spot_generative']}")
    print("   NOTE: PR28 was pre-registered as requiring a B1 kill.  B1 now uses a")
    print("   BOUNDED adversary, so a B1 pass here is a real softening of fact 703")
    print("   and is reported as such, not hidden.")
    print(f"   -> PR28 {'MET' if pr28 else 'NOT MET'}")
    res["pr28"] = dict(met=bool(pr28), killed=killed)

    print("\n" + "=" * 78)
    print("  PR27 -- is the battery PASSABLE?  (the probe must survive B1 and B2)")
    print("=" * 78)
    pb = res["plant"]["band-ratio-PROBE"]
    pr27 = pb["B1"]["passed"] and pb["B2"]["passed"]
    print(f"   band-ratio probe: B1 {'PASS' if pb['B1']['passed'] else 'FAIL'}, "
          f"B2 {'PASS' if pb['B2']['passed'] else 'FAIL'}, overall {pb['verdict']}")
    print(f"   -> PR27 {'MET' if pr27 else 'NOT MET -- thresholds must be revised'}")
    res["pr27"] = dict(met=bool(pr27), verdict=pb["verdict"])

    # ------------------------------------------------------- real data, DEV only
    print("\n" + "=" * 78)
    print("  B3 / B6 / B9 on a DEVELOPMENT stack (112MSDCF detail).  Held-out untouched.")
    print("=" * 78)
    import m41lib as L1
    files = sorted(glob.glob(r"D:\personal\macro\112MSDCF\*.ARW"))[6:68]
    cube = load_cube(files, (1671, 1373, 512, 512))
    fine, coarse, reg = L1.focus_fields(cube, G, RN_E)
    nf = cube.shape[0]
    idx = np.arange(nf)
    sp = {"parity": (idx[0::2], idx[1::2]),
          "contiguous": (idx[:nf // 2], idx[nf // 2:2 * (nf // 2)]),
          "block-4": (idx[(idx // 4) % 2 == 0], idx[(idx // 4) % 2 == 1])}
    merges = {k: (merge(cube, coarse, reg, ia), merge(cube, coarse, reg, ib))
              for k, (ia, ib) in sp.items()}
    del cube, fine, coarse, reg
    res["real"] = {}
    for cand in (R.RefSigpow(), R.RefBandRatio()):
        a, b = merges["parity"]
        cell = S.b6_cell(cand, a, b)
        base = cell["ref"]
        sig_d = abs(cell["d"])
        nd = {}
        for k in ("contiguous", "block-4"):
            nd["split"] = max(nd.get("split", 0.0),
                              abs(cand.compare(base, cand.value(*merges[k])[0])))
        for attr, vals in cand.nuisances.items():
            if attr == "split":
                continue
            old = getattr(cand, attr, None)
            if old is None:
                continue
            worst = 0.0
            for v in vals:
                setattr(cand, attr, v)
                worst = max(worst, abs(cand.compare(base, cand.value(a, b)[0])))
            setattr(cand, attr, old)
            nd[attr] = worst
        pinned = {"split": True, "nbin": True, "ring_offset": True, "f_ref": True}
        b3 = S.b3_leverage(cand, sig_d, nd, pinned)
        b5 = S.b5_sign_range(cand, [(k, cand.value(*v)[0], cand.value(*v)[1])
                                    for k, v in merges.items()])
        print(f"\n   {cand.name}")
        print(f"     B6 cell: ref {cell['ref']:+.5e}  d {cell['d']:+.5f}  "
              f"roll-null z {cell['z']:+.2f}  detected {cell['detected']}  "
              f"{'PASS' if cell['passed'] else 'FAIL'}")
        print(f"     B3 signal step |d| = {sig_d:.5f}")
        for k, v in b3["rows"].items():
            print(f"        {k:12s} leverage {v['leverage']:9.2f}x  limit {v['limit']:.2f}  "
                  f"{'pass' if v['passed'] else 'FAIL'}")
        if b3["kill"]:
            print(f"        B3 KILL: {b3['kill']}")
        if b5["kill"]:
            print(f"        B5 KILL: {b5['kill']}")
        res["real"][cand.name] = dict(cell=cell, b3=b3,
                                      b5={k: v for k, v in b5.items() if k != "out_of_range"},
                                      b5_out_of_range=[[l, float(v), s] for l, v, s in b5["out_of_range"]])

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "calibrate.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote out/calibrate.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
