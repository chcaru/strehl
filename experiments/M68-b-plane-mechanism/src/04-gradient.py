"""M68 step 04 - POST-HOC. The gradient that D1 found.

03's D1 was a failable check on the assumption that the 0.84 is a uniform
per-plane scale. It FAILED: on a 4x4 block grid the alpha_high ratio
B/G2 ran 0.8845 .. 0.8248, spread 0.0597 against a 0.05 threshold, while
the G2/G1 control was flat at spread 0.0139. The declared consequence was
"report the block map instead of f and withdraw the position claim", and
that is done. This script characterises the gradient instead.

The block map is not scatter. Row-band means ran 0.876, 0.858, 0.844,
0.833 top to bottom - monotone. Column-band means barely moved (left half
0.8559, right half 0.8496). So the anomaly is a VERTICAL gradient in the
B-to-green dark-noise ratio, and the same-parity green control does not
have it.

B and G2 sit on the SAME sensor rows (both odd) and differ only in column
parity. A vertical gradient in a quantity that differs by column parity is
not something either commissioned hypothesis predicts.

--------------------------------------------------- what could fake this

E3 is the one that can kill the finding. Dark frames are not guaranteed
dark: sensor amplifier glow and a dark-current temperature gradient both
put a real photo/thermal signal at one edge of the array, and its shot
noise lands in the temporal variance with a plane-dependent weight. That
would produce exactly a vertical gradient in a plane ratio.

Declared before running, with consequences:

  E1  ROW PROFILE.  alpha_high ratio in 32 row bands, B/G2 and B/G1, with
      G2/G1 and R/G1 as controls. If a control's row profile has a spread
      above half the B profile's spread, the gradient is an instrument
      artefact and is withdrawn.

  E2  COLUMN PROFILE.  Same in 32 column bands. Reported, not a gate.

  E3  CONTAMINATION.  Per-row-band dark mean per plane. If the band-mean
      excess spans more than 0.05 DN across bands AND its Pearson r against
      the band ratio exceeds 0.7 in magnitude, declare the gradient
      contaminated by glow/dark current, re-fit on the cleanest third of
      bands and report that number instead.

  E4  ARM ROBUSTNESS.  Top-half/bottom-half ratio under exclusion arms
      none/r3/r6/r9. If the gradient's sign or rough size changes with the
      arm, it is a defect-exclusion artefact and is withdrawn.

  E5  DOES THE GRADIENT RESCUE EITHER PRE-REGISTERED HYPOTHESIS?  The C3
      verdict was NEITHER on the array average. Recompute the min and max
      band ratios. If EVERY band lies outside both C3 bands (1.000 +/- 0.05
      and 0.705 +/- 0.05), the NEITHER verdict survives the gradient and
      does not depend on the uniformity assumption D1 just refuted. If any
      band falls inside a band, say which and how many.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("m68", HERE / "src" / "01-dark-iso-sweep.py")
m68 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m68)

NBAND = 32
ARMS = {"none": 99, "r3": 3, "r6": 6, "r9": 9}
PRIMARY = "r6"


def bands(n: int, k: int) -> list[slice]:
    e = np.linspace(0, n, k + 1).astype(int)
    return [slice(e[i], e[i + 1]) for i in range(k)]


def main() -> int:
    blob = json.loads((HERE / "data" / "01-dark-iso-sweep.json").read_text())
    cache_of = {int(p.stem.split("-iso")[1]): p
                for p in (HERE / "cache").glob("*MSDCF-iso*.npz")}
    isos = sorted(cache_of)
    if isos != sorted(int(i) for i in blob["isos"]):
        raise RuntimeError("cache/sweep ISO mismatch")
    g = np.maximum(np.array(isos, float), m68.BASE_ISO)
    mode = (np.array(isos) >= 400).astype(int)

    counts = {p: None for p in m68.PLANES}
    bmean = {p: np.zeros(NBAND) for p in m68.PLANES}
    for iso in isos:
        z = np.load(cache_of[iso])
        mean = z["mean"]
        for p in m68.PLANES:
            mp = m68.split_plane(mean, p)
            fl = m68.defect_flags(mp)
            counts[p] = fl.astype(np.int16) if counts[p] is None else counts[p] + fl
        del z, mean

    ny, nx = counts["R"].shape
    rb, cb = bands(ny, NBAND), bands(nx, NBAND)
    interior = m68.interior_mask((ny, nx))
    masks = {arm: {p: (counts[p] >= t) | ~interior for p in m68.PLANES}
             for arm, t in ARMS.items()}
    print(f"plane shape {ny}x{nx}, {NBAND} bands of ~{ny // NBAND} rows / "
          f"~{nx // NBAND} cols")

    rvar = {a: {p: np.zeros((len(isos), NBAND)) for p in m68.PLANES} for a in ARMS}
    cvar = {p: np.zeros((len(isos), NBAND)) for p in m68.PLANES}
    for i, iso in enumerate(isos):
        z = np.load(cache_of[iso])
        var, mean = z["var"], z["mean"]
        for p in m68.PLANES:
            vp = m68.split_plane(var, p).astype(np.float64)
            mp = m68.split_plane(mean, p).astype(np.float64)
            for arm in ARMS:
                keep = ~masks[arm][p]
                for b, sl in enumerate(rb):
                    rvar[arm][p][i, b] = vp[sl][keep[sl]].mean()
            keep = ~masks[PRIMARY][p]
            for b, sl in enumerate(cb):
                cvar[p][i, b] = vp[:, sl][keep[:, sl]].mean()
            if i == 0:
                pass
            for b, sl in enumerate(rb):
                bmean[p][b] += mp[sl][keep[sl]].mean() / len(isos)
        del z, var, mean

    def prof(arm, num, den, axis="row"):
        src = rvar[arm] if axis == "row" else {p: cvar[p] for p in m68.PLANES}
        out = np.zeros(NBAND)
        for b in range(NBAND):
            out[b] = (m68.fit_alpha_delta(g, mode, src[num][:, b])["alpha_high"]
                      / m68.fit_alpha_delta(g, mode, src[den][:, b])["alpha_high"])
        return out

    # -------------------------------------------------------------------- E1
    print(f"\n=== E1 row profile of the alpha_high ratio, {NBAND} bands, arm {PRIMARY} ===")
    pr = {k: prof(PRIMARY, *k.split("/")) for k in ("B/G2", "B/G1", "G2/G1", "R/G1")}
    print(f"{'band':>5s} {'rows':>12s} " + " ".join(f"{k:>8s}" for k in pr))
    for b in range(NBAND):
        print(f"{b:5d} {str(rb[b].start) + '-' + str(rb[b].stop):>12s} "
              + " ".join(f"{pr[k][b]:8.4f}" for k in pr))
    sp = {k: float(v.max() - v.min()) for k, v in pr.items()}
    print("  spreads: " + "  ".join(f"{k} {v:.4f}" for k, v in sp.items()))
    worst_ctl = max(sp["G2/G1"], sp["R/G1"])
    e1_fail = worst_ctl > 0.5 * sp["B/G2"]
    print(f"E1 worst control spread {worst_ctl:.4f} vs half of B/G2 "
          f"{0.5 * sp['B/G2']:.4f} -> {'FAIL - withdraw gradient' if e1_fail else 'PASS'}")
    x = np.arange(NBAND, dtype=float)
    for k, v in pr.items():
        sl, ic = np.polyfit(x, v, 1)
        print(f"    {k:>6s} linear trend {sl * NBAND:+.4f} over the full height, "
              f"r = {np.corrcoef(x, v)[0, 1]:+.3f}")

    # -------------------------------------------------------------------- E2
    print(f"\n=== E2 column profile of the alpha_high ratio, {NBAND} bands ===")
    pc = {k: prof(PRIMARY, *k.split("/"), axis="col") for k in ("B/G2", "G2/G1")}
    for k, v in pc.items():
        sl, _ = np.polyfit(x, v, 1)
        print(f"  {k:>6s} min {v.min():.4f} max {v.max():.4f} spread "
              f"{v.max() - v.min():.4f} trend {sl * NBAND:+.4f} "
              f"r {np.corrcoef(x, v)[0, 1]:+.3f}")

    # -------------------------------------------------------------------- E3
    print("\n=== E3 contamination: per-row-band dark mean (DN above 512) ===")
    print(f"{'band':>5s} " + " ".join(f"{p:>9s}" for p in m68.PLANES) + "   B/G2 ratio")
    for b in range(0, NBAND, 2):
        print(f"{b:5d} " + " ".join(f"{bmean[p][b]:9.5f}" for p in m68.PLANES)
              + f"   {pr['B/G2'][b]:8.4f}")
    span = {p: float(bmean[p].max() - bmean[p].min()) for p in m68.PLANES}
    print("  band-mean span: " + "  ".join(f"{p} {v:.5f} DN" for p, v in span.items()))
    rr = float(np.corrcoef(bmean["G2"], pr["B/G2"])[0, 1])
    rb_ = float(np.corrcoef(bmean["B"], pr["B/G2"])[0, 1])
    print(f"  Pearson r(band mean, B/G2 ratio): G2 {rr:+.3f}  B {rb_:+.3f}")
    e3_fail = max(span.values()) > 0.05 and max(abs(rr), abs(rb_)) > 0.7
    print(f"E3 -> {'CONTAMINATED' if e3_fail else 'clear'} "
          f"(needs span>0.05 DN and |r|>0.7)")
    if e3_fail:
        order = np.argsort(bmean["G2"])[: NBAND // 3]
        v = np.array([rvar[PRIMARY]["B"][:, b] for b in order]).mean(axis=0)
        w = np.array([rvar[PRIMARY]["G2"][:, b] for b in order]).mean(axis=0)
        cl = (m68.fit_alpha_delta(g, mode, v)["alpha_high"]
              / m68.fit_alpha_delta(g, mode, w)["alpha_high"])
        print(f"  cleanest third of bands: alpha_B/alpha_G2 = {cl:.5f}")

    # -------------------------------------------------------------------- E4
    print("\n=== E4 arm robustness of the top/bottom split ===")
    half = NBAND // 2
    for arm in ARMS:
        t = (m68.fit_alpha_delta(g, mode, rvar[arm]["B"][:, :half].mean(1))["alpha_high"]
             / m68.fit_alpha_delta(g, mode, rvar[arm]["G2"][:, :half].mean(1))["alpha_high"])
        bo = (m68.fit_alpha_delta(g, mode, rvar[arm]["B"][:, half:].mean(1))["alpha_high"]
              / m68.fit_alpha_delta(g, mode, rvar[arm]["G2"][:, half:].mean(1))["alpha_high"])
        tc = (m68.fit_alpha_delta(g, mode, rvar[arm]["G2"][:, :half].mean(1))["alpha_high"]
              / m68.fit_alpha_delta(g, mode, rvar[arm]["G1"][:, :half].mean(1))["alpha_high"])
        bc = (m68.fit_alpha_delta(g, mode, rvar[arm]["G2"][:, half:].mean(1))["alpha_high"]
              / m68.fit_alpha_delta(g, mode, rvar[arm]["G1"][:, half:].mean(1))["alpha_high"])
        print(f"  {arm:>5s}  B/G2 top {t:.4f} bottom {bo:.4f} delta {bo - t:+.4f}"
              f"   |  G2/G1 top {tc:.4f} bottom {bc:.4f} delta {bc - tc:+.4f}")

    # -------------------------------------------------------------------- E5
    print("\n=== E5 does the gradient rescue either pre-registered hypothesis? ===")
    v = pr["B/G2"]
    in_p1 = int((np.abs(v - 1.000) <= 0.05).sum())
    in_p2 = int((np.abs(v - 0.705) <= 0.05).sum())
    print(f"  band ratios span {v.min():.4f} .. {v.max():.4f} over {NBAND} bands")
    print(f"  bands inside the {{P1,P5}} band 1.000 +/- 0.05: {in_p1}/{NBAND}")
    print(f"  bands inside the {{P2,P3,P4}} band 0.705 +/- 0.05: {in_p2}/{NBAND}")
    print(f"E5 -> C3's NEITHER verdict "
          f"{'SURVIVES' if in_p1 == 0 and in_p2 == 0 else 'IS QUALIFIED'} the gradient")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
