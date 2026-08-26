"""Is the rim the correct band, or a bright artefact? Compare against truth.

ORCH's synthesis proposes that the bright rim is not something ADDED at the
edge but the one band that is nearly right, standing against a surround that is
wrongly dark -- and therefore that raising the surround dissolves the rim
without ever touching it.

That is a sharp, falsifiable prediction, and the two possibilities need
opposite fixes:

  * If the merge at the rim sits AT the unveiled truth, ORCH is right. Fix the
    surround; the step disappears; never touch the rim band.
  * If the merge at the rim sits ABOVE the unveiled truth, the rim is a real
    bright artefact. Raising the surround would leave a smaller but still
    visible bright band, and the rim needs its own treatment.

The best available estimate of unveiled truth is the per-pixel UPPER ENVELOPE
across frames, because veiling by a dark subject can only darken a bright
backdrop. So the whole question reduces to the sign of (merge - envelope) as a
function of distance from the silhouette.

The trap this script exists to avoid
------------------------------------
This bracket drifts 18.3% in raw DN from f000 to f204 (section 23.1). A
per-pixel max taken over RAW frames is therefore dominated by whichever frame
had the highest exposure, not by whichever frame was least veiled -- it would
measure the drift and call it truth. Every frame is gain-normalised to a common
far-field level BEFORE the envelope is accumulated, and the fitted gains are
printed so the correction is checkable rather than assumed.

A second-highest envelope is carried alongside the maximum. A max over nine
samples is biased bright by roughly the noise, and if the two envelopes
disagree materially the conclusion is resting on noise rather than on veiling.
"""

from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, binary_closing, binary_opening

SRC = Path(r"C:\dev\strehl-out\ORCH-rim")
OUT = Path(r"C:\dev\strehl-out\AURA")

FRAMES = {
    0: "f0-lin.tif", 25: "fb-f025-lin.tif", 51: "fb-f051-lin.tif",
    76: "fb-f076-lin.tif", 102: "frame102-lin.tif", 127: "fb-f127-lin.tif",
    153: "fb-f153-lin.tif", 178: "fb-f178-lin.tif", 204: "f204-lin.tif",
}
MERGE = "merge-lin.tif"

BANDS = [(1, 4), (4, 8), (8, 12), (12, 16), (16, 24), (24, 32), (32, 48),
         (48, 64), (64, 96), (96, 140), (140, 200), (200, 260), (260, 320),
         (320, 400)]
FAR = (500, 900)
RIM_BANDS = [(1, 4), (4, 8), (8, 12), (12, 16)]
SURROUND = [(32, 48), (48, 64), (64, 96), (96, 140), (140, 200), (200, 260)]


def luma(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    if a.ndim == 3:
        out = (0.2126 * a[..., 0].astype(np.float32)
               + 0.7152 * a[..., 1].astype(np.float32)
               + 0.0722 * a[..., 2].astype(np.float32))
    else:
        out = a.astype(np.float32)
    del a
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    print("silhouette from frame 102 (subject sharpest, no election in it) ...",
          flush=True)
    f102 = luma(SRC / FRAMES[102])
    backdrop = float(np.median(f102))
    subject = f102 < 0.5 * backdrop
    subject = binary_closing(subject, np.ones((9, 9)))
    subject = binary_opening(subject, np.ones((9, 9)))
    print(f"  backdrop {backdrop:.1f} DN, subject {100 * subject.mean():.2f}% of frame")
    del f102

    print("distance transform ...", flush=True)
    dist = distance_transform_edt(~subject)

    # Flat index lists per band: far cheaper in memory than 14 bool planes,
    # and frozen once so every arm is scored on identical pixels.
    band_idx = []
    for lo, hi in BANDS:
        m = (dist >= lo) & (dist < hi) & ~subject
        band_idx.append(np.flatnonzero(m.ravel()).astype(np.int64))
        del m
    fm = (dist >= FAR[0]) & (dist < FAR[1]) & ~subject
    far_idx = np.flatnonzero(fm.ravel()).astype(np.int64)
    del fm, dist, subject
    print(f"  far field {FAR}: {far_idx.size:,} px")
    for (lo, hi), ix in zip(BANDS, band_idx):
        print(f"    d {lo:4d}-{hi:4d}: {ix.size:9,} px")

    # ---- accumulate the gain-normalised per-pixel envelope ---------------
    merge = luma(SRC / MERGE)
    target = float(np.median(merge.ravel()[far_idx]))
    print(f"\nmerge far-field level {target:.1f} DN -- every frame is scaled "
          f"to this before the envelope")
    print("\n=== per-frame gain fitted on the far field (checkable, not assumed) ===")

    env = None
    env2 = None
    for k in sorted(FRAMES):
        img = luma(SRC / FRAMES[k])
        far_k = float(np.median(img.ravel()[far_idx]))
        g = target / far_k
        print(f"  f{k:03d}  far {far_k:9.1f} DN   gain x{g:6.4f}")
        img *= g
        if env is None:
            env = img.copy()
            env2 = img
        else:
            tmp = np.minimum(img, env)
            np.maximum(env2, tmp, out=env2)
            del tmp
            np.maximum(env, img, out=env)
            del img
    gains = []
    print()

    def prof(a):
        return np.array([float(np.median(a.ravel()[ix])) for ix in band_idx])

    p_merge = prof(merge)
    p_env = prof(env)
    p_env2 = prof(env2)
    f_mid = luma(SRC / FRAMES[102])
    g_mid = target / float(np.median(f_mid.ravel()[far_idx]))
    f_mid *= g_mid
    p_mid = prof(f_mid)

    far_env = float(np.median(env.ravel()[far_idx]))

    # Excess is measured against the ENVELOPE's own far field for every arm,
    # so a single common reference is used and no arm gets its own divisor.
    print("=== profiles, all referenced to the SAME far field "
          f"({far_env:.1f} DN) ===")
    print("  d(px)        merge     env(max)    env(2nd)     f102      "
          "merge-env   %px merge>env")
    frac_above = []
    for i, (lo, hi) in enumerate(BANDS):
        ix = band_idx[i]
        fa = 100.0 * float(np.mean(merge.ravel()[ix] > env.ravel()[ix]))
        frac_above.append(fa)
        print(f"  {lo:4d}-{hi:4d} {p_merge[i] - far_env:11.1f} "
              f"{p_env[i] - far_env:11.1f} {p_env2[i] - far_env:11.1f} "
              f"{p_mid[i] - far_env:10.1f} {p_merge[i] - p_env[i]:11.1f} "
              f"{fa:11.1f}%")
    print()

    def agg(sel):
        ii = [i for i, b in enumerate(BANDS) if b in sel]
        w = np.array([band_idx[i].size for i in ii], dtype=np.float64)
        d = np.array([p_merge[i] - p_env[i] for i in ii])
        return float((d * w).sum() / w.sum()), float(np.mean([frac_above[i] for i in ii]))

    rim_d, rim_f = agg(RIM_BANDS)
    sur_d, sur_f = agg(SURROUND)
    print("=== THE VERDICT ===")
    print(f"  RIM      d=1-16 px : merge - envelope = {rim_d:9.1f} DN "
          f"({rim_f:.1f}% of px above the envelope)")
    print(f"  SURROUND d=32-260px: merge - envelope = {sur_d:9.1f} DN "
          f"({sur_f:.1f}% of px above the envelope)")
    print()
    if rim_d > 200:
        print("  -> the merge sits ABOVE unveiled truth at the rim.")
        print("     The rim is a real bright artefact. Raising the surround")
        print("     alone would leave a smaller but still visible bright band.")
    elif rim_d > -300:
        print("  -> the merge sits AT unveiled truth at the rim, within "
              f"{abs(rim_d):.0f} DN.")
        print("     ORCH is right: the rim is the correct band and the step is")
        print("     made by the surround. Fix the surround, never the rim.")
    else:
        print("  -> the merge is BELOW unveiled truth at the rim too; the rim")
        print("     is not a bright overshoot at all.")
    print(f"\n  headroom available in the surround: {-sur_d:.1f} DN "
          f"({100.0 * -sur_d / far_env:.1f}% of backdrop)")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cx = np.array([0.5 * (lo + hi) for lo, hi in BANDS])
    fig, ax = plt.subplots(2, 1, figsize=(11, 8), dpi=130, sharex=True)
    ax[0].plot(cx, p_env - far_env, "o-", color="seagreen", lw=2,
               label="upper envelope (unveiled truth)")
    ax[0].plot(cx, p_env2 - far_env, "^--", color="darkseagreen", lw=1,
               label="2nd-highest (noise control)")
    ax[0].plot(cx, p_mid - far_env, "s-", color="steelblue", lw=1.4,
               label="frame 102 (middle)")
    ax[0].plot(cx, p_merge - far_env, "o-", color="crimson", lw=2.4,
               label="MERGE")
    ax[0].axhline(0, color="k", lw=0.7, ls=":")
    ax[0].set_xscale("log")
    ax[0].set_ylabel("DN excess over common far field")
    ax[0].legend(fontsize=9)
    ax[0].grid(alpha=0.3)
    ax[0].set_title("flower-bud-alone-cpl: is the rim correct, or bright?")
    ax[1].plot(cx, p_merge - p_env, "o-", color="crimson", lw=2.4)
    ax[1].axhline(0, color="k", lw=0.9)
    ax[1].axvspan(1, 16, color="orange", alpha=0.18, label="rim band")
    ax[1].axvspan(32, 260, color="steelblue", alpha=0.14, label="surround")
    ax[1].set_xscale("log")
    ax[1].set_xlabel("distance from silhouette (px)")
    ax[1].set_ylabel("merge - envelope (DN)")
    ax[1].legend(fontsize=9)
    ax[1].grid(alpha=0.3)
    fig.tight_layout()
    p = OUT / "AURA-envelope.png"
    fig.savefig(p)
    assert p.read_bytes()[:4] == b"\x89PNG"
    print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
