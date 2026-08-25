"""M120 step 12 — coincidence and the photometric decomposition ACROSS the
gate ladder, so item 1 and R4 are answered for the SHIPPED default and not
only for the gate-0 image ORCH happened to be shown.
"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy import stats

M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
HERE = Path(__file__).resolve().parent

CY0, CY1, CX0, CX1 = 476, 604, 442, 570
BANDS = [(1.0, 4.0), (2.0, 8.0), (4.0, 16.0), (8.0, 32.0)]
B28 = (2.0, 8.0)
UNIT = float(np.sqrt(2.0)) * 0.015214
SHIFT = 64


def bp(a, s):
    a = np.asarray(a, np.float32)
    return ndi.gaussian_filter(a, s[0]) - ndi.gaussian_filter(a, s[1])


def C(a, b):
    a = np.asarray(a, np.float32)
    return float(np.sqrt((bp(a, b) ** 2).mean()) / a.mean())


def gm(a):
    return np.hypot(*np.gradient(ndi.gaussian_filter(np.asarray(a, np.float32), 1.0)))


def main() -> int:
    cube = np.load(M87 / "bee3-leg-luma.npy", mmap_mode="r")
    fld = np.load(M87 / "bee3-leg-field.npy", mmap_mode="r")
    n = cube.shape[0]
    L = np.stack([np.array(cube[k, CY0:CY1, CX0:CX1], np.float32) for k in range(n)])
    F = np.stack([np.array(fld[k, CY0:CY1, CX0:CX1], np.float32) for k in range(n)])
    Cf = {b: max(C(f, b) for f in L) for b in BANDS}
    lev = L.reshape(n, -1).mean(1)
    gl = float(lev.mean())
    bound = float(lev.max() / lev.min())
    best = F.max(0)
    arg = F.argmax(0).astype(np.int32)
    ga = gm(arg).ravel()
    Lnorm = L * (gl / lev)[:, None, None]        # per-frame photometric normalisation

    print(f"ROI 128x128; Q bound for constant weights = {bound:.3f}; "
          f"denominator max_k C = {1e4*Cf[B28]:.3f} x1e-4")
    print(f"\n{'gate':>5}{'n_eff':>8}{'Q(2-8)':>9}{'Q after per-frame':>19}{'residual':>10}"
          f"{'  rho(|grad idx|,|grad out|)':>30}{'null rho':>10}")
    print(f"{'':>5}{'':>8}{'':>9}{'level normalisation':>19}{'share':>10}")
    rows = {}
    for th in (0.0, 1.0, 2.0, 4.0, 8.0, 16.0):
        adm = F >= (best - th * UNIT)
        cnt = adm.sum(0)
        out = (L * adm).sum(0) / cnt
        outn = (Lnorm * adm).sum(0) / cnt
        q = C(out, B28) / Cf[B28]
        qn = C(outn, B28) / Cf[B28]
        share = qn / q
        r = stats.spearmanr(ga, gm(out).ravel()).statistic
        r0 = stats.spearmanr(ga, gm(np.roll(np.roll(out, SHIFT, 0), SHIFT, 1)).ravel()).statistic
        rows[th] = {"mean_neff": float(cnt.mean()), "Q": round(q, 4), "Q_levelnorm": round(qn, 4),
                    "residual_share": round(share, 4), "rho": round(float(r), 4),
                    "rho_null": round(float(r0), 4)}
        print(f"{th:5.0f}{cnt.mean():8.1f}{q:9.3f}{qn:19.3f}{share:10.1%}"
              f"{r:+30.4f}{r0:+10.4f}")

    print("\ninterpretation of the two right-hand columns:")
    print("  'Q after per-frame level normalisation' removes ALL frame-to-frame")
    print("  photometric drift and re-merges with the SAME admitted sets. What")
    print("  survives is geometric -- the frames' defocused backgrounds differ in")
    print("  SHAPE, not only in level. 'residual share' is how much of the")
    print("  patchwork photometric normalisation alone cannot remove.")

    # decisive placebo: identical admitted sets, zero inter-frame difference
    ref = L[n // 2]
    flat = np.repeat(ref[None], n, 0)
    adm = F >= (best - 4.0 * UNIT)
    plc = (flat * adm).sum(0) / adm.sum(0)
    print(f"\nPLACEBO (rule 11): gate-4 admitted sets UNCHANGED, every frame replaced")
    print(f"  by one real frame -> Q(2-8) = {C(plc, B28)/Cf[B28]:.4f}  "
          f"(must be <= {bound:.3f}; the election alone manufactures nothing)")

    (HERE / "ladder.json").write_text(json.dumps(
        {"bound": bound, "ladder": {str(k): v for k, v in rows.items()},
         "placebo_Q": round(C(plc, B28) / Cf[B28], 4)}, indent=2), encoding="utf-8")
    print(f"\nwrote {HERE / 'ladder.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
