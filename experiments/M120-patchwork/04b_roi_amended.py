"""M120 step 4b — the registered ROI rule FIRED ITS REFUSAL; this is the
amendment, disclosed rather than substituted.

Registered rule (prereg §4) built "smooth in every frame" from a 9x9 local sd
and refused if no >=128 px square survived. It refused: the largest square is
**64 px**. The reason is an instrument defect in my own registration, not a
property of the scene: a 9x9 local sd of a photon-limited frame is dominated by
photon noise (model sigma 16.6 DN at the ROI's 2400 DN level) plus the card's
own illumination gradient, neither of which is "structure at the artifact's
scale". The registered criterion measured the wrong quantity.

The amendment measures structure at the ARTIFACT'S OWN SCALE and calibrates its
threshold against an INDEPENDENTLY PREDICTED value rather than a percentile of
anything (AGENTS rule 21):

    B(I) = gaussian(I, 3) - gaussian(I, 24)        band-pass, 3..24 px
    floor = the same statistic on synthetic white noise at the project's own
            model sigma, `m87lib.green_luma_sigma(level, ISO=100)`

"Smooth in every frame" is then `max_k RMS_local(B(f_k)) <= 3 x floor`.
Both the registered result and the amended result are reported.
"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\src")))
import m87lib as L  # noqa: E402

M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
HERE = Path(__file__).resolve().parent

TIGHT = (330, 610, 150, 570)
PAD = 40
WIN = (TIGHT[0] - PAD, TIGHT[1] + PAD, TIGHT[2] - PAD, TIGHT[3] + PAD)
S_LO, S_HI = 3.0, 24.0
ISO = 100.0


def bandpass(a):
    a = a.astype(np.float32)
    return ndi.gaussian_filter(a, S_LO) - ndi.gaussian_filter(a, S_HI)


def local_rms(a, k=17):
    return np.sqrt(np.maximum(ndi.uniform_filter(a * a, k), 0.0))


def largest_square(mask):
    h, w = mask.shape
    dp = np.zeros((h, w), np.int32)
    best = (0, 0, 0)
    m = mask.astype(np.int32)
    for y in range(h):
        row = dp[y]
        prev = dp[y - 1] if y else None
        for x in range(w):
            if m[y, x]:
                row[x] = 1 if (y == 0 or x == 0) else 1 + min(prev[x], row[x - 1], prev[x - 1])
                if row[x] > best[0]:
                    best = (row[x], y, x)
    s, y, x = best
    return (y - s + 1, y + 1, x - s + 1, x + 1), s


def main() -> int:
    cube = np.load(M87 / "bee3-leg-luma.npy", mmap_mode="r")
    n = cube.shape[0]
    y0, y1, x0, x1 = WIN
    h, w = y1 - y0, x1 - x0

    # ---- independently predicted band-pass noise floor -------------------
    lvl0 = float(np.array(cube[n // 2, y0:y1, x0:x1]).mean())
    sig = float(L.green_luma_sigma(np.array([[lvl0]]), ISO)[0, 0])
    rng = np.random.default_rng(12345)
    nullmax = np.zeros((h, w), np.float32)
    for _ in range(n):
        synth = rng.normal(0.0, sig, size=(h, w)).astype(np.float32)
        np.maximum(nullmax, local_rms(bandpass(synth)), out=nullmax)
    floor = float(np.median(nullmax))
    print(f"ROI level {lvl0:.0f} DN -> model green-luma sigma {sig:.2f} DN")
    print(f"band-pass({S_LO},{S_HI}) MAX-over-{n} local-RMS on synthetic white "
          f"noise at that sigma: median {floor:.3f} DN, p99 {np.percentile(nullmax, 99):.3f} DN")
    print("  (independent prediction of the SAME statistic, extreme-value "
          "inflation included -- not a percentile of the data)")

    maxbp = np.zeros((h, w), np.float32)
    for k in range(n):
        f = np.array(cube[k, y0:y1, x0:x1], dtype=np.float32)
        np.maximum(maxbp, local_rms(bandpass(f)), out=maxbp)
    np.save(OUT / "maxbp_window.npy", maxbp)
    qs = [1, 5, 10, 20, 30, 50, 90]
    print("maxbp percentiles (DN): " + "  ".join(
        f"p{q}={np.percentile(maxbp, q):.2f}" for q in qs))

    thr = 3.0 * floor
    smooth = maxbp <= thr
    print(f"'smooth in EVERY frame' = max_k local-RMS(B) <= 3 x floor = {thr:.3f} DN")
    print(f"  -> {100 * smooth.mean():.2f}% of the {h}x{w} window, "
          f"{int(smooth.sum())} px")

    er = ndi.binary_erosion(smooth, np.ones((25, 25), bool))
    (by0, by1, bx0, bx1), side = largest_square(er)
    BG_SQ = (y0 + by0, y0 + by1, x0 + bx0, x0 + bx1)
    print(f"largest all-frames-smooth square = {side} px, box-relative {BG_SQ}")

    # textured NC1 control ROI, chosen on the cube alone
    ksz = max(side, 64)
    box = ndi.uniform_filter(maxbp, ksz)
    pad = ksz // 2 + 1
    box[:pad] = 0
    box[-pad:] = 0
    box[:, :pad] = 0
    box[:, -pad:] = 0
    cy, cx = np.unravel_index(int(box.argmax()), box.shape)
    TX = (y0 + cy - ksz // 2, y0 + cy - ksz // 2 + ksz,
          x0 + cx - ksz // 2, x0 + cx - ksz // 2 + ksz)
    print(f"textured NC1 square = {ksz} px, box-relative {TX}")

    meta = json.loads((HERE / "roi.json").read_text(encoding="utf-8")) if (HERE / "roi.json").exists() else {}
    meta.update({
        "amended": True,
        "registered_rule_result": "REFUSED (largest 9x9-sd square = 64 px < 128)",
        "window_box_relative": [int(v) for v in WIN],
        "bandpass": [S_LO, S_HI],
        "model_sigma_dn": sig,
        "bandpass_noise_floor_dn": floor,
        "smooth_threshold_dn": thr,
        "smooth_fraction": float(smooth.mean()),
        "bg_square_box_relative": [int(v) for v in BG_SQ],
        "bg_square_side": int(side),
        "tx_square_box_relative": [int(v) for v in TX],
    })
    (HERE / "roi.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    np.save(OUT / "smooth_mask_window.npy", smooth)
    print(f"\nwrote {HERE / 'roi.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
