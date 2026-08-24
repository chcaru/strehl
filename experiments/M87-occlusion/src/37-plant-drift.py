"""M87 addendum 4 / R2 + R3 -- can drift, or the focus measure itself,
manufacture a halo with NO occlusion anywhere?

Registered in PREREG-ADDENDUM-4-registration.md sections A4.4 and A4.5,
commit a66ca28, BEFORE this ran.

R1 (step 35/36) measured that correcting registration removes only ~7% of the
halo. That is a NECESSITY test: the halo does not need misregistration. It does
not answer the SUFFICIENCY question the orchestrator's hypothesis actually
asks -- can misregistration manufacture a rim at all? And it does not separate
either from M63's rival explanation.

The plant is SINGLE-DEPTH with a PAINTED step edge. There is no occluder, no
second layer, no alpha, and nothing to veil. Every pixel focuses at the same
frame k_F. Three arms differ in one factor:

    R3  drift = 0 px     -- if a halo appears here it is the FOCUS MEASURE's own
                            side lobe (M63 s9.1: the boxed gradient response at
                            offset x peaks at sigma = |x|, so a pixel d px from
                            an edge is maximised by a DEFOCUSED frame), and it
                            needs neither occlusion nor misregistration
    R2  drift = 30 px pp -- adds monotone translation matched to the 63 px p-p
                            excursion step 35 measured inside ROI_LEG, scaled
                            to this frame's width
    R2b drift = 60 px pp -- double, to show the response is monotone in drift
                            and not a threshold artifact

WHY THIS PLANT CAN EXPRESS THE FAILURE (the trap this project keeps hitting: a
synthetic that cannot exhibit the effect it is supposed to test).
  - It has a high-contrast edge. The dark/bright step is 0.08 vs 0.75, the same
    levels the step-24 polarity plant used, chosen there to match the real
    leg-against-background contrast.
  - Drift moves that edge across WHOLE pixels. 30 px p-p over 121 frames is
    0.25 px/frame and 30 px total, so the edge traverses many pixel centres.
    The script asserts this rather than assuming it.
  - Defocus spans the range that matters. sigma_k = |k - k_F| * 0.28 reaches
    16.8 px, larger than the D_ISO window the metric reads (3..40 px).
  - Selection is per-pixel argmax over frames, which is the exact mechanism the
    orchestrator's hypothesis invokes.
  - It is scored by the SAME metric, from the KNOWN silhouette, so a null here
    cannot be blamed on Otsu.

Shifts are INTEGER (np.roll), so no interpolation touches the plant and no
result here can be a resampler artifact.
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))
import m87lib as L          # noqa: E402
import m87metric2 as M2     # noqa: E402

DATA = HERE / "data"
OUT = HERE / "out"
DEST = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")

H, W = 384, 512
N = 121
KF = 60
SCALE = 0.28
LEVEL = 3000.0
READ_SD = 6.0
LO, HI = 0.08, 0.75
D_ISO = (3, 40)


def build(drift_px, seed=87):
    """Single depth, painted edge, monotone integer translation drift."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]

    stripe = ((xx > 150) & (xx < 260)) & (yy > 20) & (yy < H - 20)
    tex = 0.0467 * np.sin(xx / 1.6) * np.cos(yy / 1.9)
    tex = tex + 0.016 * ndi.gaussian_filter(rng.standard_normal((H, W)), 0.8)
    scene = np.where(stripe, LO, HI) * (1.0 + tex)
    scene = np.clip(scene, 0.01, 1.2).astype(np.float32)

    dx = np.rint(drift_px * (2.0 * np.arange(N) / (N - 1) - 1.0)).astype(int)
    frames = np.empty((N, H, W), np.float32)
    for k in range(N):
        s = np.roll(scene, dx[k], axis=1)
        sig = abs(k - KF) * SCALE
        img = ndi.gaussian_filter(s, sig) if sig > 0.3 else s.copy()
        v = img * LEVEL
        frames[k] = v + rng.normal(0, np.sqrt(np.maximum(v, 1.0)) + READ_SD,
                                   (H, W))
    truth = (np.roll(scene, dx[KF], axis=1) * LEVEL).astype(np.float32)
    ref = np.roll(stripe, dx[KF], axis=1)
    return frames, truth, ref, dx, float(abs(k - KF) * SCALE)


def merge_argmax(frames):
    best = np.full(frames.shape[1:], -np.inf, np.float32)
    arg = np.zeros(frames.shape[1:], np.int32)
    for k in range(len(frames)):
        fl = L.regularised_field(frames[k].astype(np.float64), 100.0)
        b = fl > best
        best[b] = fl[b]
        arg[b] = k
    return np.take_along_axis(frames, arg[None], 0)[0], arg


def score(img, mask, tag):
    roi = (30, H - 30, 40, W - 40)
    pts, nrm = M2.boundary_normals(mask, roi=roi)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    if val.sum() < M2.MIN_PROFILES:
        print(f"  {tag:30s} only {val.sum()} valid profiles")
        return None
    r = M2.score_iso(img, pts[val], nrm[val])
    print(f"  {tag:30s} ISO={r['ISO']:.5f} "
          f"CI[{r['ISO_ci'][0]:.5f},{r['ISO_ci'][1]:.5f}] n={r['n']} "
          f"d*={r['d_star']:.0f}")
    return {"ISO": r["ISO"], "ISO_ci": r["ISO_ci"], "n": r["n"],
            "d_star": r["d_star"]}


def png(a, path, lo, hi, gamma=2.2):
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** (1.0 / gamma)
    Image.fromarray((v * 255).astype(np.uint8)).save(path)


def main():
    out = {}
    arms = [("R3-drift0", 0.0), ("R2-drift30pp", 15.0), ("R2b-drift60pp", 30.0)]

    print("=== plant sufficiency checks (rule: show it CAN express the effect) ===")
    _, _, _, dx0, sig_max = build(15.0)
    print(f"  sigma_k max          = {sig_max:.2f} px  (D_ISO reads {D_ISO})")
    print(f"  drift dx range       = {dx0.min()} .. {dx0.max()} px, "
          f"{len(np.unique(dx0))} distinct integer positions")
    assert len(np.unique(dx0)) >= 10, "drift does not move the edge across pixels"
    assert sig_max > D_ISO[1] * 0.4, "defocus too small to reach the metric window"
    out["sigma_max"] = sig_max
    out["drift_positions"] = int(len(np.unique(dx0)))

    print("\n=== arms ===")
    keep = {}
    for tag, d in arms:
        frames, truth, ref, dx, _ = build(d)
        sel, arg = merge_argmax(frames)
        r = score(sel, ref, tag)
        rt = score(truth, ref, tag + " TRUTH")
        out[tag] = {"merge": r, "truth": rt, "drift_pp": 2 * d}
        keep[tag] = (sel, truth, ref, arg)
        if r and rt:
            print(f"    {'':30s} excess over truth = "
                  f"{r['ISO'] - rt['ISO']:+.5f}")

    r3 = out["R3-drift0"]["merge"]
    r2 = out["R2-drift30pp"]["merge"]
    r2b = out["R2b-drift60pp"]["merge"]
    t3 = out["R3-drift0"]["truth"]
    if r3 and r2 and t3:
        print(f"\n  R3 zero-drift halo   : {r3['ISO']:.5f} "
              f"(truth floor {t3['ISO']:.5f})")
        print(f"  R2 30 px p-p         : {r2['ISO']:.5f}  "
              f"({100*(r2['ISO']/r3['ISO']-1):+.1f}% vs R3)")
        print(f"  R2b 60 px p-p        : {r2b['ISO']:.5f}  "
              f"({100*(r2b['ISO']/r3['ISO']-1):+.1f}% vs R3)")
        real = 0.06805
        print(f"  real bee-3 leg halo  : {real:.5f}")
        print(f"  zero-drift plant reaches "
              f"{100*r3['ISO']/real:.0f}% of the real halo with NO occlusion "
              f"and NO misregistration")
        out["summary"] = {
            "R3": r3["ISO"], "R2": r2["ISO"], "R2b": r2b["ISO"],
            "truth_floor": t3["ISO"], "real_bee3": real,
            "R3_frac_of_real": r3["ISO"] / real,
            "drift_gain_pct": 100 * (r2["ISO"] / r3["ISO"] - 1),
            "drift_gain_pct_double": 100 * (r2b["ISO"] / r3["ISO"] - 1)}

    DEST.mkdir(parents=True, exist_ok=True)
    for tag in ("R3-drift0", "R2-drift30pp"):
        sel, truth, ref, arg = keep[tag]
        lo, hi = float(np.percentile(truth, 0.5)), float(np.percentile(truth, 99.5))
        png(sel, DEST / f"23-PLANT-{tag}-merge.png", lo, hi)
    sel3 = keep["R3-drift0"][0]
    tr3 = keep["R3-drift0"][1]
    lo, hi = float(np.percentile(tr3, 0.5)), float(np.percentile(tr3, 99.5))
    gap = np.full((H, 16), hi, np.float32)
    png(np.hstack([tr3, gap, sel3]), DEST / "24-PLANT-truth-vs-merge.png", lo, hi)
    print(f"\n  wrote plant crops to {DEST}")

    (DATA / "37-plant-drift.json").write_text(json.dumps(out, indent=2),
                                              encoding="utf-8")
    print("wrote data/37-plant-drift.json")


if __name__ == "__main__":
    main()
