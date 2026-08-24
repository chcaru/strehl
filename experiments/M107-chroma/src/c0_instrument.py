"""C0 — validate Instrument A on a plant whose answer is known by construction.

Rule 20: each control names the input that would make it fail, and C5 plants that
input to prove the instrument can detect it.

The plant is a continuous scene sampled on the sensel lattice, so there is no
interpolator anywhere in the truth. Per-channel lateral shift and per-channel blur
are planted analytically into the erf, not by resampling.
"""

import sys, os
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import esf_all_planes, summarise, dump, TRUE_OFFSET
import common
from scipy.special import erf

RNG = np.random.default_rng(107)


def plant(nx=192, ny=192, angle_deg=11.0, shift=None, blur=None, noise=0.0,
          swap_rb=False, amp=8000.0, base=1000.0):
    """Continuous edge at `angle_deg`, sampled at the true sensel positions.

    shift[c] displaces channel c ALONG THE EDGE NORMAL, in sensel.
    blur[c]  is that channel's edge sigma, in sensel.
    """
    shift = shift or {}
    blur = blur or {}
    a = np.deg2rad(angle_deg)
    n = np.array([np.cos(a), np.sin(a)])
    cx, cy = nx / 2.0, ny / 2.0
    out = np.zeros((ny, nx), dtype=np.float32)
    name_at = {}
    for pname, (dx, dy) in TRUE_OFFSET.items():
        name_at[pname] = (int(dy), int(dx))
    if swap_rb:
        name_at["R"], name_at["B"] = name_at["B"], name_at["R"]
    for pname, (oy, ox) in name_at.items():
        xs = np.arange(ox, nx, 2, dtype=np.float64)
        ys = np.arange(oy, ny, 2, dtype=np.float64)
        X, Y = np.meshgrid(xs, ys)
        d = (X - cx) * n[0] + (Y - cy) * n[1] - shift.get(pname, 0.0)
        w = blur.get(pname, 1.6)
        v = base + 0.5 * amp * (1.0 + erf(d / (np.sqrt(2.0) * w)))
        if noise:
            v = v + RNG.normal(0.0, noise, v.shape)
        out[oy::2, ox::2] = v
    return out, n


def run():
    res = {}
    print("=== C0: instrument A controls (truth by construction) ===")

    # C1 -- no planted shift, no planted blur difference. R and B must read ZERO.
    #       If the RGGB phase convention were wrong they would read +-1 sensel.
    s = summarise(esf_all_planes(plant()[0]))
    res["C1"] = s
    print(f"C1 null          dR={s['dR']:+.5f} dB={s['dB']:+.5f} "
          f"nullG={s['null_dG']:+.5f}  wR={s['wR']:+.5f} wB={s['wB']:+.5f}")

    # C2 -- planted lateral shift along the normal.
    for pr, pb in [(0.40, -0.40), (0.15, -0.15), (1.00, 1.00), (0.0, 0.60)]:
        s = summarise(esf_all_planes(plant(shift={"R": pr, "B": pb})[0]))
        key = f"C2_{pr}_{pb}"
        res[key] = {"planted_R": pr, "planted_B": pb, **s}
        print(f"C2 plant R{pr:+.2f} B{pb:+.2f} -> dR={s['dR']:+.5f} "
              f"dB={s['dB']:+.5f}  err=({s['dR']-pr:+.2e},{s['dB']-pb:+.2e})")

    # C3 -- planted per-channel blur (axial CA within one frame).
    s = summarise(esf_all_planes(plant(blur={"R": 2.6, "G1": 1.6, "G2": 1.6, "B": 2.1})[0]))
    res["C3"] = s
    print(f"C3 blur planted R=2.6 G=1.6 B=2.1 -> fitted "
          f"R={s['w_abs']['R']:.4f} G1={s['w_abs']['G1']:.4f} "
          f"G2={s['w_abs']['G2']:.4f} B={s['w_abs']['B']:.4f}")
    print(f"   wR={s['wR']:+.5f} (planted +1.000) wB={s['wB']:+.5f} "
          f"(planted +0.500) nullW={s['null_wG']:+.5f}")

    # C3b -- WIDTH CALIBRATION. The fit reads w high because the plane lattice
    #        samples on a 2-sensel pitch. Measure the additive-in-quadrature
    #        term q so that per-channel width DIFFERENCES can be de-biased.
    ws = [1.0, 1.4, 1.8, 2.2, 2.8, 3.6]
    fitted = []
    for wt in ws:
        s = summarise(esf_all_planes(plant(blur={k: wt for k in TRUE_OFFSET})[0]))
        fitted.append(0.5 * (s["w_abs"]["G1"] + s["w_abs"]["G2"]))
    A = np.array(ws) ** 2
    F = np.array(fitted) ** 2
    q2 = float(np.mean(F - A))
    res["C3b"] = {"planted": ws, "fitted": fitted, "q_sensel": float(np.sqrt(max(q2, 0.0))),
                  "resid": [float(x) for x in (F - A - q2)]}
    print(f"C3b width calibration: fitted^2 - planted^2 = {q2:.5f} "
          f"=> q = {np.sqrt(max(q2,0.0)):.5f} sensel, "
          f"scatter {np.std(F - A):.5f}")
    for wt, wf in zip(ws, fitted):
        print(f"    planted {wt:.2f} -> fitted {wf:.4f} -> "
              f"corrected {np.sqrt(max(wf**2-q2,0)):.4f}")

    # C4 -- with noise, at a realistic shot-noise level for a 8000 DN edge.
    errs = []
    for seed in range(5):
        global RNG
        RNG = np.random.default_rng(1000 + seed)
        s = summarise(esf_all_planes(plant(shift={"R": 0.25, "B": -0.25}, noise=90.0)[0]))
        errs.append((s["dR"] - 0.25, s["dB"] + 0.25, s["null_dG"]))
    errs = np.array(errs)
    res["C4"] = {"worst_dR_err": float(np.abs(errs[:, 0]).max()),
                 "worst_dB_err": float(np.abs(errs[:, 1]).max()),
                 "worst_null": float(np.abs(errs[:, 2]).max())}
    print(f"C4 noise sd=90DN, 5 seeds -> worst dR err {np.abs(errs[:,0]).max():.5f}, "
          f"worst dB err {np.abs(errs[:,1]).max():.5f}, worst G1-G2 null "
          f"{np.abs(errs[:,2]).max():.5f}")

    # C5 -- POWER CONTROL. Plant a scene where R and B genuinely DIFFER (R is
    #       blurrier), then write them to each other's lattice sites. The
    #       instrument must report the exchange. If it cannot, C1 proves nothing.
    base = plant(blur={"R": 3.2, "G1": 1.6, "G2": 1.6, "B": 1.6})[0]
    sw = base.copy()
    sw[0::2, 0::2] = base[1::2, 1::2]   # R site <- B data
    sw[1::2, 1::2] = base[0::2, 0::2]   # B site <- R data
    s_ok = summarise(esf_all_planes(base))
    s_sw = summarise(esf_all_planes(sw))
    res["C5"] = {"correct": s_ok, "swapped": s_sw}
    print(f"C5 correct  wR={s_ok['wR']:+.4f} wB={s_ok['wB']:+.4f}")
    print(f"C5 R/B SITES SWAPPED wR={s_sw['wR']:+.4f} wB={s_sw['wB']:+.4f} "
          f"(must exchange)")

    # C6 -- a second power control: read the SAME plant with the plane offsets
    #       forced to (0,0), i.e. pretending the CFA is co-sited. What appears
    #       is exactly the co-siting displacement the convention removes.
    roi = plant()[0]
    saved = dict(common.PLANE_OFFSET)
    common.PLANE_OFFSET.update({k: (0.0, 0.0) for k in saved})
    s = summarise(esf_all_planes(roi))
    common.PLANE_OFFSET.update(saved)
    res["C6"] = s
    print(f"C6 offsets forced to (0,0) -> dR={s['dR']:+.5f} dB={s['dB']:+.5f} "
          f"nullG={s['null_dG']:+.5f}  (= the raw CO-SITING offset)")

    dump("c0_instrument", res)


if __name__ == "__main__":
    run()
