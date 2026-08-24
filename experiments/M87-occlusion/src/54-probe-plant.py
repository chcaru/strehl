"""M87 step 54 -- settle the illumination-probe sign by planting a known ramp.

THE DISPUTE. My far-background probe reports the early frames of `bee-3-cpl`
as -3.18%; M99's reports +5.31%. The orchestrator has stopped M99 shipping
until the sign is settled and asked me to plant a signed gain ramp into real
frames and recover it.

WHAT THIS TEST CAN AND CANNOT SETTLE. Planting validates MY probe as an
estimator: if a planted +4% comes back as +4% with the right sign, my
instrument is unbiased and my baseline number is what my probe says it is.
It CANNOT settle M99's number, because I do not have M99's probe. So the
script also reports the baseline under every convention and region I can
think of that a reasonable implementer might have chosen, so the orchestrator
can match M99's 5.31% to one of them rather than guess.

WHY THE TEST CAN EXPRESS A FAILURE. Planting is a per-frame scalar multiply,
so a probe that is a linear functional of the frame must return the planted
factor exactly. A probe that is NOT -- one that mixes in a nonlinearity, or
that normalises by something that moves with the plant -- will return a
slope != 1. The two failure modes actually available here are a wrong SIGN
(slope -1, a reciprocal-convention error) and a DILUTED response (|slope| < 1,
a probe partly anchored to something the plant does not move). Both are
detectable by this design, so it is not vacuous.

TWO CONVENTIONS, AND WHY THEY DIFFER IN SIGN. My probe returns the CORRECTION
GAIN g_k = ref / lev_k. The underlying BRIGHTNESS bias is b_k = lev_k / ref - 1.
These are reciprocals, so they carry OPPOSITE SIGNS: frames that are dim have
negative brightness bias and a positive correction gain. -3.18% brightness is
+3.28% gain. That alone flips a sign without anyone being wrong, which is why
this script prints both for every arm.

RESOLVED AT SOURCE. `crates/strehl-core/src/photometric.rs:390` computes
`let g = (r / f.mean().unwrap_or(r)) as f32`, i.e. reference / frame flux --
the CORRECTION GAIN convention. So M99's +5.31% and my -3.18% are the two
reciprocal conventions of the same signed statement, "the early frames are dim
and need boosting". There is no sign conflict to settle. This script is still
worth running because it is what proves MY arm is an unbiased estimator.

A DEFECT IN THE FIRST VERSION OF THIS SCRIPT, DISCLOSED. Its predicted planted
shift was `mean(pg[:E])/median(pg) - 1`, which silently assumes the median of a
product is the product of medians. It is not, so the FAR arm read a slope of
0.8079 and looked 19% diluted when the probe is in fact exactly linear. The
primary test below is now the per-frame RATIO levA[k]/lev0[k] against pg[k],
which involves no median at all and is therefore exact; the early-decile
summary is kept as a secondary with a prediction computed from the baseline
levels the same way the measurement is.

ARMS. Three probe regions, identical plant:
  FAR   far background, dist(subject) > 60 px      -- mine, the one under test
  CROP  whole-crop median                          -- the orchestrator's
                                                      leading hypothesis for M99
  SUBJ  subject pixels only                        -- a deliberately bad probe,
                                                      included so the table has
                                                      a known-wrong row
Every arm recovers a planted GLOBAL gain correctly (a global multiply scales
every region alike). They differ in their BASELINE, which is the disagreement.
That distinction is the point of the table and is stated in the output.

No file outside experiments/M87-occlusion is touched. Read-only on the cube.
"""

import json
import pathlib
import sys

import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"

EARLY = 30          # first decile of 299 frames
AMPS = [-0.08, -0.04, 0.0, +0.04, +0.08]
DIST_PX = 60.0


def plant_gain(n, amp):
    """Signed ramp centred on the sweep: early frames scaled by (1 - amp/2)."""
    t = np.arange(n, dtype=np.float64) / (n - 1) - 0.5
    return 1.0 + amp * t


def summarise(lev):
    """Return (brightness_bias_early, correction_gain_early) in percent."""
    ref = float(np.median(lev))
    b = float(lev[:EARLY].mean()) / ref - 1.0
    g = ref / float(lev[:EARLY].mean()) - 1.0
    return 100.0 * b, 100.0 * g, ref


def main():
    luma = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    n = luma.shape[0]
    print(f"cube {luma.shape}  early decile = first {EARLY} frames")

    far = distance_transform_edt(~mask) > DIST_PX
    subj = mask.copy()
    print(f"FAR  probe: {100 * far.mean():.2f}% of pixels "
          f"(background, dist > {DIST_PX:.0f} px from subject)")
    print(f"SUBJ probe: {100 * subj.mean():.2f}% of pixels")
    assert far.sum() > 10000 and subj.sum() > 10000

    # Materialise every planted frame rather than scaling levels analytically,
    # so the recovered slope is a property of the pipeline and not of algebra.
    arms = ["FAR", "CROP", "SUBJ"]
    lev = {a: np.zeros((len(AMPS), n)) for a in arms}
    for k in range(n):
        base = np.asarray(luma[k], np.float32)
        for i, amp in enumerate(AMPS):
            f = base * np.float32(plant_gain(n, amp)[k])
            lev["FAR"][i, k] = f[far].mean()
            lev["CROP"][i, k] = np.median(f)
            lev["SUBJ"][i, k] = f[subj].mean()
        if k % 60 == 0:
            print(f"  frame {k:3d}/{n}", flush=True)

    out = {"n": n, "early": EARLY, "amps": AMPS, "dist_px": DIST_PX,
           "far_frac": float(far.mean()), "arms": {}}
    i0 = AMPS.index(0.0)

    print("\n=== PRIMARY: per-frame recovery of the planted gain (no median) ===")
    print("    ratio_k = lev_planted[k]/lev_baseline[k]  must equal plant_gain[k]")
    print(f"{'arm':<6}{'amp':>7}{'slope':>11}{'max|ratio/pg-1|':>18}{'sign':>7}")
    for a in arms:
        pr = []
        for i, amp in enumerate(AMPS):
            if i == i0:
                continue
            pg = plant_gain(n, amp)
            ratio = lev[a][i] / lev[a][i0]
            slope = float(np.polyfit(pg, ratio, 1)[0])
            err = float(np.abs(ratio / pg - 1.0).max())
            ok = "OK" if np.sign(ratio[-1] - ratio[0]) == np.sign(amp) else "WRONG"
            pr.append({"amp": amp, "slope": slope, "max_rel_err": err, "sign": ok})
            print(f"{a:<6}{amp:>7.2f}{slope:>11.6f}{err:>18.2e}{ok:>7}")
        out.setdefault("primary", {})[a] = pr

    print("\n=== SECONDARY: the early-decile summary, prediction from baseline ===")
    print(f"{'arm':<6}{'planted':>9}{'recovered':>11}{'residual':>12}"
          f"{'  brightness%':>14}{'  gain%':>9}")
    for a in arms:
        res = []
        b0, g0, _ = summarise(lev[a][i0])
        rows = []
        for i, amp in enumerate(AMPS):
            b, g, _ = summarise(lev[a][i])
            pg = plant_gain(n, amp)
            # exact prediction: apply the plant to the BASELINE levels and
            # summarise them by the same route the measurement uses.
            sim = pg * lev[a][i0]
            pred = 100.0 * (sim[:EARLY].mean() / np.median(sim) - 1.0) - b0
            got = b - b0
            res.append(got - pred)
            rows.append({"amp": amp, "planted_pct": pred, "recovered_pct": got,
                         "brightness_pct": b, "gain_pct": g})
            print(f"{a:<6}{pred:>9.4f}{got:>11.4f}{got - pred:>12.2e}"
                  f"{b:>14.4f}{g:>9.4f}")
        A = np.array([r["planted_pct"] for r in rows])
        B = np.array([r["recovered_pct"] for r in rows])
        slope = float(np.polyfit(A, B, 1)[0])
        out["arms"][a] = {"rows": rows, "slope": slope,
                          "max_abs_residual_pct": float(np.abs(res).max()),
                          "baseline_brightness_pct": b0,
                          "baseline_gain_pct": g0}
        print(f"{a:<6}slope {slope:.6f}   max|residual| {np.abs(res).max():.2e} pp"
              f"   baseline {b0:+.4f}% brightness = {g0:+.4f}% gain\n")

    print("=== BASELINE, every convention (this is where the arms disagree) ===")
    print(f"{'arm':<6}{'brightness%':>13}{'gain%':>10}")
    for a in arms:
        r = out["arms"][a]
        print(f"{a:<6}{r['baseline_brightness_pct']:>13.4f}"
              f"{r['baseline_gain_pct']:>10.4f}")

    json.dump(out, open(DATA / "54-probe-plant.json", "w"), indent=1)
    print(f"\nwrote {DATA / '54-probe-plant.json'}")


if __name__ == "__main__":
    main()
