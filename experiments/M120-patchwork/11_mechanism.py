"""M120 step 11 — mechanism (R1a), the gate dose-response, and a falsifiable
PREDICTION for the soft gate that M116's render can check.

Soft-gate kernels are taken from the shipped source, not guessed:
  merge.rs:346  Gaussian     w = exp(-0.5 (gap/T)^2), support 4.71 T
  merge.rs:355  Exponential  w = exp(-gap/T),         support 11.09 T
  merge.rs:1424 SoftGate::new(threshold) shares Gate::tolerance bit-for-bit,
                T = threshold * sqrt(2) * FOCUS_NOISE_SD = threshold * 0.021516

M120 does NOT render the soft-gate A/B; M116 owns that. What follows is a
prediction computed from the cached focus field, stated before M116 reports,
so that M116's render is a falsification test of it and not a confirmation.
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage as ndi

M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
M93 = Path(r"C:\dev\strehl-out\M93-out")
SO = Path(r"C:\dev\strehl-out")
OUT = Path(r"C:\dev\strehl-out\M120")
HERE = Path(__file__).resolve().parent

BOX = (1178, 1922, 278, 1422)
CY0, CY1, CX0, CX1 = 476, 604, 442, 570
AY0, AY1, AX0, AX1 = BOX[0] + CY0, BOX[0] + CY1, BOX[2] + CX0, BOX[2] + CX1
BANDS = [(1.0, 4.0), (2.0, 8.0), (4.0, 16.0), (8.0, 32.0)]
FOCUS_NOISE_SD = 0.015214
UNIT = float(np.sqrt(2.0)) * FOCUS_NOISE_SD
G_SUPPORT, E_SUPPORT = 4.71, 11.0904


def bp(a, s):
    a = np.asarray(a, np.float32)
    return ndi.gaussian_filter(a, s[0]) - ndi.gaussian_filter(a, s[1])


def C(a, b):
    a = np.asarray(a, np.float32)
    return float(np.sqrt((bp(a, b) ** 2).mean()) / a.mean())


def main() -> int:
    cube = np.load(M87 / "bee3-leg-luma.npy", mmap_mode="r")
    fld = np.load(M87 / "bee3-leg-field.npy", mmap_mode="r")
    n = cube.shape[0]
    L = np.stack([np.array(cube[k, CY0:CY1, CX0:CX1], np.float32) for k in range(n)])
    F = np.stack([np.array(fld[k, CY0:CY1, CX0:CX1], np.float32) for k in range(n)])
    Cf = {b: np.array([C(f, b) for f in L]) for b in BANDS}
    lev = L.reshape(n, -1).mean(1)
    bound = float(lev.max() / lev.min())
    B28 = BANDS[1]

    # ---- geometry of the outlier arm ------------------------------------
    p = SO / "ORCH-morning" / "bee-3-strehl.tif"
    if p.exists():
        o = tifffile.imread(p)
        g0 = tifffile.imread(M93 / "armM-gate0-binlin.tif")[:, :, 1].astype(np.float32)
        print(f"ORCH-morning/bee-3-strehl.tif {o.shape} {o.dtype}")
        a = o[AY0:AY1, AX0:AX1, 1].astype(np.float32)
        bb = g0[AY0:AY1, AX0:AX1]
        r = float(((a - a.mean()) / a.std() * (bb - bb.mean()) / bb.std()).mean())
        print(f"  NCC vs armM-gate0-binlin over the ROI = {r:+.4f}  "
              f"({'same geometry' if r > 0.7 else 'DIFFERENT GEOMETRY -- its Q is NOT comparable'})")
        del o, g0

    # ---- R1a: is the through-focus response noise-dominated here? -------
    best = F.max(0)
    srt = np.sort(F, 0)
    ceiling = 2.928 * FOCUS_NOISE_SD          # E[max of 299 iid N(0, sd)]
    print(f"\n=== R1a: through-focus response in the background ROI ===")
    print(f"  winner response: median {np.median(best):.4f}  p10 {np.percentile(best,10):.4f} "
          f"p90 {np.percentile(best,90):.4f}")
    print(f"  pure-noise ceiling E[max of {n} iid N(0,{FOCUS_NOISE_SD})] = {ceiling:.4f}")
    print(f"  -> winner / ceiling = {np.median(best)/ceiling:.2f}x   "
          f"({100*np.mean(best <= ceiling):.1f}% of ROI px at or below the ceiling)")
    gap = best - srt[-2]
    print(f"  winner-to-runner-up gap: median {np.median(gap):.5f} = "
          f"{np.median(gap)/UNIT:.3f} gate units (1 unit = {UNIT:.6f})")
    print(f"  response range over frames: median (max-min) = {np.median(best - F.min(0)):.4f}, "
          f"i.e. {np.median(best - F.min(0))/FOCUS_NOISE_SD:.1f} noise SD -- "
          f"{'FLAT' if np.median(best - F.min(0)) < 3*FOCUS_NOISE_SD else 'NOT flat'}")

    # ---- gate dose-response, plus n_eff / confusion radius --------------
    print(f"\n=== hard-gate dose-response (violation iff Q > {bound:.3f}) ===")
    print(f"{'gate':>6}{'tol':>10}{'mean n_eff':>12}{'n_eff=1 %':>11}"
          + "".join(f"{b[0]:g}-{b[1]:g}".rjust(10) for b in BANDS))
    dose = {}
    for th in (0.0, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0):
        tol = th * UNIT
        adm = F >= (best - tol)
        neff = adm.sum(0)
        out = (L * adm).sum(0) / neff
        q = [C(out, b) / Cf[b].max() for b in BANDS]
        dose[th] = {"mean_neff": float(neff.mean()), "neff1_pct": float(100 * np.mean(neff == 1)),
                    "Q": {f"{b[0]:g}-{b[1]:g}": round(v, 4) for b, v in zip(BANDS, q)}}
        print(f"{th:6.0f}{tol:10.5f}{neff.mean():12.2f}{100*np.mean(neff==1):11.1f}"
              + "".join(f"{v:10.3f}" for v in q))
    g2c = np.load(M87 / "bee3-leg-g2.npy")[CY0:CY1, CX0:CX1].astype(np.float32)
    tol = 2.0 * UNIT
    adm = F >= (best - tol)
    mine = (L * adm).sum(0) / adm.sum(0)
    print(f"  check: my gate-2 reconstruction vs M87's cached bee3-leg-g2.npy: "
          f"max abs diff {np.abs(mine - g2c).max():.3e} DN")

    # ---- the PREDICTION for M116 ----------------------------------------
    print(f"\n=== PREDICTION for the soft gate at the shipped threshold 4 ===")
    pred = {}
    for name, sup, fn in (("gaussian", G_SUPPORT, lambda z: np.exp(-0.5 * z * z)),
                          ("exponential", E_SUPPORT, lambda z: np.exp(-z))):
        for th in (4.0,):
            T = th * UNIT
            z = (best - F) / T
            w = np.where(z <= sup, fn(z), 0.0).astype(np.float32)
            neff = (w.sum(0) ** 2) / (w ** 2).sum(0)
            out = (L * w).sum(0) / w.sum(0)
            q = {f"{b[0]:g}-{b[1]:g}": round(C(out, b) / Cf[b].max(), 4) for b in BANDS}
            pred[f"{name}@{th:g}"] = {"mean_neff": float(neff.mean()), "Q": q}
            print(f"  {name:12s} T={T:.5f}  mean n_eff {neff.mean():7.2f}  "
                  + "  ".join(f"Q({k})={v:.3f}" for k, v in q.items()))
    hard4 = dose[4.0]["Q"][f"{B28[0]:g}-{B28[1]:g}"]
    for k, v in pred.items():
        dq = v["Q"][f"{B28[0]:g}-{B28[1]:g}"]
        print(f"  -> {k}: Q(2-8) {hard4:.3f} -> {dq:.3f} "
              f"({100*(dq/hard4-1):+.1f}%), still {'ABOVE' if dq > bound else 'below'} the "
              f"{bound:.3f} bound")

    # fraction of frame the soft gate would touch
    fldfull = np.load(M87 / "bee3-leg-field.npy", mmap_mode="r")
    step = 4
    sub = np.array(fldfull[:, ::step, ::step], np.float32)
    b2 = sub.max(0)
    T = 4.0 * UNIT
    hard = (sub >= b2 - T).sum(0)
    zz = (b2 - sub) / T
    soft = np.where(zz <= G_SUPPORT, np.exp(-0.5 * zz * zz), 0.0)
    neff_s = (soft.sum(0) ** 2) / (soft ** 2).sum(0)
    changed = np.mean(neff_s > 1.05 * hard)
    print(f"\n  over the WHOLE {sub.shape[1]}x{sub.shape[2]} (4x-decimated) M87 box:")
    print(f"    hard gate 4 mean n_eff {hard.mean():.2f}; n_eff==1 on "
          f"{100*np.mean(hard == 1):.1f}% of the box")
    print(f"    gaussian soft gate 4 mean n_eff {neff_s.mean():.2f}")
    print(f"    fraction of the frame where soft n_eff exceeds hard by >5%: {100*changed:.1f}%")

    (HERE / "mechanism.json").write_text(json.dumps({
        "roi_shipped_abs": [AY0, AY1, AX0, AX1], "Q_bound": bound,
        "winner_response_median": float(np.median(best)), "noise_ceiling": float(ceiling),
        "response_range_median": float(np.median(best - F.min(0))),
        "gate_dose_response": {str(k): v for k, v in dose.items()},
        "soft_gate_prediction": pred,
        "soft_gate_frame_fraction_changed": float(changed),
        "hard4_mean_neff_whole_box": float(hard.mean()),
        "hard4_neff1_pct_whole_box": float(100 * np.mean(hard == 1)),
    }, indent=2), encoding="utf-8")
    print(f"\nwrote {HERE / 'mechanism.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
