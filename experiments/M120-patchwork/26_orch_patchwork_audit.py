"""M120 step 26 -- damage assessment on ORCH's two patchwork* scripts.

ORCH: "M120: these two patchwork* scripts are in your lane -- this is the one to
act on first." Re-run rather than reason: compute the SAME statistic
`patchwork_16bit.py` computes, on the SAME file, through both readers.

The point of that script (its own docstring) is:
    "Rival to kill: quantisation contouring. If the polygons only exist after an
     8-bit export, they are a display artifact and not a stacker defect."

It reads its pixels with np.asarray(Image.open(src)). So it is worth checking
whether the script could ever have answered its own question.

Reads only. Writes nothing outside experiments/M120-patchwork.
"""
import os
import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
CANDIDATES = [r"C:\dev\strehl-out\bee3-full.tif",
              r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif"]
S = 256


def excess_kurtosis(win):
    """Verbatim from patchwork_16bit.py (dead `ravea` branch removed)."""
    lap = (-4 * win[1:-1, 1:-1] + win[:-2, 1:-1] + win[2:, 1:-1]
           + win[1:-1, :-2] + win[1:-1, 2:])
    f = lap.ravel()
    mu = f.mean()
    v = ((f - mu) ** 2).mean()
    if v <= 0:
        return float("nan"), 0.0
    return ((f - mu) ** 4).mean() / v ** 2 - 3.0, float(np.sqrt(v))


def pick_windows(lum, full):
    """Verbatim selection logic from patchwork_16bit.py."""
    H, W = lum.shape
    best = []
    for y in range(0, H - S, S):
        for x in range(0, W - S, S):
            w = lum[y:y + S, x:x + S]
            m = w.mean()
            if m < 0.55 * full:
                continue
            best.append((w[::16, ::16].std(), m, x, y))
    best.sort()
    return best


def main():
    src = next((p for p in CANDIDATES if os.path.exists(p)), None)
    print(f"src {src}\n")

    tf = tifffile.imread(src)
    assert tf.dtype == np.uint16, tf.dtype
    pil = np.asarray(Image.open(src))
    print(f"  tifffile : {tf.shape} {tf.dtype}  min {tf.min()} max {tf.max()}")
    print(f"  PIL      : {pil.shape} {pil.dtype}  min {pil.min()} max {pil.max()}"
          f"   mode {Image.open(src).mode}")
    print(f"  full scale the script would assume:"
          f"  tifffile {np.iinfo(tf.dtype).max}   PIL {np.iinfo(pil.dtype).max}"
          f"   -> {np.iinfo(tf.dtype).max / np.iinfo(pil.dtype).max:.0f}x error\n")

    res = {}
    for tag, a in (("tifffile (truth)", tf), ("PIL (as shipped)", pil)):
        lum = a[..., :3].astype(np.float64).mean(axis=2)
        full = float(np.iinfo(a.dtype).max)
        best = pick_windows(lum, full)
        picks = best[:6]
        ks = []
        for rough, m, x, y in picks:
            k, lsd = excess_kurtosis(lum[y:y + S, x:x + S])
            ks.append((x, y, 100 * m / full, lsd, k))
        res[tag] = ks
        print(f"  {tag}: {len(best)} candidate windows")
        print(f"    {'x':>6}{'y':>7}{'mean%':>8}{'lapSD':>10}{'excessKurt':>13}")
        for x, y, mp, lsd, k in ks:
            print(f"    {x:>6}{y:>7}{mp:>7.1f}%{lsd:>10.3f}{k:>13.2f}")
        print()

    a_t = np.array([r[4] for r in res["tifffile (truth)"]])
    a_p = np.array([r[4] for r in res["PIL (as shipped)"]])
    same_win = [(r[0], r[1]) for r in res["tifffile (truth)"]] == \
               [(r[0], r[1]) for r in res["PIL (as shipped)"]]
    print("=" * 72)
    print(f"  kurtosis median : truth {np.median(a_t):8.2f}   PIL {np.median(a_p):8.2f}"
          f"   ratio {np.median(a_p)/np.median(a_t):.3f}x")
    print(f"  kurtosis worst  : truth {a_t.max():8.2f}   PIL {a_p.max():8.2f}")
    print(f"  same windows selected by both readers: {same_win}")

    # The question the script was built to answer.
    lum_t = tf[..., :3].astype(np.float64).mean(axis=2)
    x, y = res["tifffile (truth)"][0][0], res["tifffile (truth)"][0][1]
    w = lum_t[y:y + S, x:x + S]
    print(f"\n  CAN THE SCRIPT ANSWER ITS OWN QUESTION?")
    print(f"    Its stated rival is 'the polygons only exist after an 8-bit export'.")
    print(f"    Its reader performs an 8-bit conversion before its first arithmetic.")
    print(f"    distinct luma levels in its best window: "
          f"truth {len(np.unique(w)):,}   via PIL "
          f"{len(np.unique(np.asarray(Image.open(src))[y:y+S, x:x+S, :3].astype(np.float64).mean(axis=2))):,}")
    print(f"    -> the treatment arm and the control arm are the SAME arm.")

    print(f"\n  TRIAGE (ORCH's two questions applied to this statistic):")
    print(f"    absolute, not a ratio?           YES -- excess kurtosis is absolute.")
    print(f"    small-over-large ratio?          no.")
    print(f"    -> destroyed, not protected by cancellation.")

    # is the instrument's own control matched to its data?
    rng = np.random.default_rng(20260825)
    noise = rng.normal(w.mean(), w.std(), w.shape)
    kn_cont, _ = excess_kurtosis(noise)
    kn_q8, _ = excess_kurtosis(np.round(noise / 257.0))
    print(f"\n  SEPARATE FLAW, independent of the reader:")
    print(f"    the null/plant are synthesised at CONTINUOUS precision and compared")
    print(f"    against data the reader had already quantised.")
    print(f"    iid null, continuous : excess kurtosis {kn_cont:+.3f}")
    print(f"    iid null, 8-bit      : excess kurtosis {kn_q8:+.3f}")
    print(f"    -> control and data were not on the same footing. Fixing the reader")
    print(f"       fixes this too, because uint16 -> float64 is effectively continuous.")


if __name__ == "__main__":
    main()
