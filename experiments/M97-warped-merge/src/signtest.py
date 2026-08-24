"""The decisive sign test: gather two real frames through the sidecar and see
where the subject lands.

The orchestrator's instruction was explicit -- do not resolve the sign by
choosing the reading that agrees with the code. Resolve it by rendering. So
this applies the sidecar's own placements to real frame data with a gather
written here, independent of strehl, and measures what is left over.

Three arms and a null, all on the same wiring:

  RAW        frame 0 vs frame N, untouched.  Ground truth for the drift.
  AS-IS      both frames pulled through placement(k) with NO inversion, which
             is what `gather_checked` does.
  INVERTED   both pulled through the INVERSE placement.  This is the plant: a
             sign error doubles the drift instead of removing it, so this arm
             must land far on the other side of RAW.  If AS-IS and INVERTED
             come back similar, the test is blind and proves nothing.
  SELF       frame 0 against itself, to show the estimator reads 1.0 when
             nothing has moved.

Scale is measured about the image centre, and the correlation peak is free to
choose translation.  That makes the result independent of whether the sidecar's
translation is expressed about the centre or the corner -- an ambiguity this
test therefore does not have to resolve.
"""

import json
import os
import struct
import sys

import numpy as np
import rawpy
from scipy.ndimage import map_coordinates

STACK = os.environ.get("M97_STACK", r"D:\personal\macro\bee-3-cpl")
DOWN = 4


def green_plane(path: str) -> np.ndarray:
    """One CFA green sub-lattice, block-mean downsampled. Written here rather
    than imported from the orchestrator's tree so a shared bug cannot make the
    two measurements agree with each other and with nothing else."""
    with rawpy.imread(path) as r:
        vis = np.array(r.raw_image_visible, dtype=np.float32, copy=True)
        cfa = np.array(r.raw_colors_visible[:2, :2], dtype=np.int32, copy=True)
        black = float(np.mean(r.black_level_per_channel))
    ys, xs = np.where(cfa == 1)
    g = vis[int(ys[0]) :: 2, int(xs[0]) :: 2] - black
    h, w = (g.shape[0] // DOWN) * DOWN, (g.shape[1] // DOWN) * DOWN
    g = g[:h, :w].reshape(h // DOWN, DOWN, w // DOWN, DOWN).mean(axis=(1, 3))
    return g.astype(np.float32)


def parse(path: str):
    header, rows = {}, {}
    with open(path, "r", encoding="utf-8") as fh:
        assert fh.readline().startswith("strehl-warpmap")
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            p = line.split()
            if not p[0].lstrip("-").isdigit():
                header[p[0]] = " ".join(p[1:])
            elif len(p) >= 6:
                v = [struct.unpack(">d", bytes.fromhex(x))[0] for x in p[2:6]]
                rows[int(p[0])] = (complex(v[0], v[1]), complex(v[2], v[3]))
    return header, rows


def gather(img: np.ndarray, a: complex, b: complex, scale_px: float) -> np.ndarray:
    """Pull `img` through the similarity z -> a*z + b, about the image centre.

    `scale_px` converts the sidecar's plane pixels to this image's pixels,
    since we work on a DOWN-times decimated plane. Only the translation needs
    it; `a` is dimensionless.
    """
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    z = (xx - cx) + 1j * (yy - cy)
    zs = a * z + b / scale_px
    return map_coordinates(
        img, [np.imag(zs) + cy, np.real(zs) + cx], order=1, mode="constant", cval=np.nan
    )


def prep(a: np.ndarray) -> np.ndarray:
    a = np.nan_to_num(a, nan=0.0)
    a = a - a.mean()
    return a * np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]


def zoom(img: np.ndarray, s: float) -> np.ndarray:
    """Resample about the centre by s; s>1 magnifies."""
    return gather(img, complex(1.0 / s, 0.0), 0j, 1.0)


def ncc_peak(a: np.ndarray, b: np.ndarray) -> float:
    fa, fb = np.fft.rfft2(a), np.fft.rfft2(b)
    c = np.fft.irfft2(fa * np.conj(fb), s=a.shape)
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float(c.max() / d) if d > 0 else -1.0


def best_scale(a: np.ndarray, b_raw: np.ndarray, lo=0.70, hi=1.15, n=51, refine=3):
    """Scale of b relative to a, with the rail check the orchestrator added."""
    railed = False
    best, bestv = 1.0, -1.0
    for it in range(refine):
        grid = np.linspace(lo, hi, n)
        vals = [ncc_peak(a, prep(zoom(b_raw, 1.0 / s))) for s in grid]
        k = int(np.argmax(vals))
        if it == 0 and k in (0, len(grid) - 1):
            railed = True
        best, bestv = float(grid[k]), float(vals[k])
        step = float(grid[1] - grid[0])
        lo, hi, n = best - step, best + step, 21
    return best, bestv, railed


def main(argv: list[str]) -> int:
    sidecar, out_json, last = argv[1], argv[2], int(argv[3])
    # Optional gain applied to every placement before gathering. This does NOT
    # touch the estimator; it is a scalar correction at the consumption point,
    # used to ask what the image would look like if the solve's gain were right.
    #
    # Scale composes multiplicatively along a chain of frames, so an estimator
    # that attenuates each pairwise log-scale by a constant produces a global
    # solve whose log-scale is attenuated by that same constant. The correction
    # is therefore applied in the log: a' = exp(g * ln a). Translation composes
    # additively, so it is scaled linearly.
    gain = float(argv[4]) if len(argv) > 4 else 1.0
    header, rows = parse(sidecar)
    if gain != 1.0:
        rows = {k: (np.exp(gain * np.log(a)), gain * b) for k, (a, b) in rows.items()}
        print(f"GAIN {gain:.4f} applied to every placement (log-scale, linear b)")

    plane_w = float(header["plane"].split("x")[0])
    ref = int(header["reference"])
    import os

    names = sorted(f for f in os.listdir(STACK) if f.lower().endswith(".arw"))
    g0, gN = green_plane(os.path.join(STACK, names[0])), green_plane(
        os.path.join(STACK, names[last])
    )
    scale_px = plane_w / g0.shape[1]
    r_plane = 0.5 * float(np.hypot(3512.0, 2344.0))
    print(f"sidecar reference frame {ref}; plane {header['plane']}; "
          f"working {g0.shape[1]}x{g0.shape[0]} ({scale_px:.1f} plane px/px)")

    a0, b0 = rows[0]
    aN, bN = rows[last]
    print(f"|a_0| = {abs(a0):.6f}   |a_{last}| = {abs(aN):.6f}   "
          f"ratio = {abs(aN) / abs(a0):.6f}")

    # Plants for the estimator itself, on this wiring. Both sit on the s<1
    # branch, which is the branch every arm below is read on -- a plant at
    # 1.05 recovers only 1.014 here, because de-magnifying to test that
    # hypothesis pulls a NaN rim in and biases the correlation toward 1.0.
    # That bias pushes readings TOWARD 1.0, i.e. toward "no drift", so it can
    # only understate the residual reported below, never inflate it.
    for planted in (0.94, 0.86):
        s, v, rail = best_scale(prep(g0), zoom(g0, planted))
        print(f"PLANT  {planted:.3f} -> {s:.5f}  (err {s - planted:+.5f})  "
              f"ncc {v:.4f}  railed={rail}")

    # Round-trip control for the GATHER, not the estimator: build a synthetic
    # frame that is a known similarity away from g0, hand the gather that same
    # similarity as a placement, and require it to come back to g0. Without
    # this, a faithful-looking residual could be the gather's own distortion.
    #
    # The direction matters and I got it backwards first: if synth's content is
    # `p` times g0's, then a feature at g0 radius r sits at synth radius p*r, so
    # the placement IS p, not 1/p. Feeding 1/p returned 0.854 for p=1.08 --
    # which is exactly g0 * p / (1/p) = 0.857, i.e. the control faithfully
    # reported my own error rather than the gather's.
    for planted in (1.08, 0.92):
        synth = zoom(g0, planted)
        back = gather(synth, complex(planted, 0.0), 0j, scale_px)
        s, v, rail = best_scale(prep(g0), back)
        flag = "OK" if abs(s - 1.0) < 0.005 else "FAIL"
        print(f"GATHER ROUND-TRIP a={planted:.2f} -> residual {s:.5f} "
              f"({abs(s - 1) * r_plane:6.1f} plane px)  ncc {v:.4f}  {flag}")

    arms = {}
    s, v, rail = best_scale(prep(g0), g0)
    arms["SELF"] = dict(scale=s, ncc=v, railed=rail)
    s, v, rail = best_scale(prep(g0), gN)
    arms["RAW"] = dict(scale=s, ncc=v, railed=rail)
    w0 = gather(g0, a0, b0, scale_px)
    wN = gather(gN, aN, bN, scale_px)
    s, v, rail = best_scale(prep(w0), wN)
    arms["AS-IS"] = dict(scale=s, ncc=v, railed=rail)
    i0 = gather(g0, 1.0 / a0, -b0 / a0, scale_px)
    iN = gather(gN, 1.0 / aN, -bN / aN, scale_px)
    s, v, rail = best_scale(prep(i0), iN)
    arms["INVERTED"] = dict(scale=s, ncc=v, railed=rail)

    print()
    print(f"{'arm':<10} {'scale':>9} {'|s-1| plane px':>15} {'ncc':>8} {'railed':>7}")
    for k, r in arms.items():
        r["corner_plane_px"] = abs(r["scale"] - 1.0) * r_plane
        print(f"{k:<10} {r['scale']:>9.5f} {r['corner_plane_px']:>15.1f} "
              f"{r['ncc']:>8.4f} {str(r['railed']):>7}")

    raw, asis, inv = arms["RAW"]["scale"], arms["AS-IS"]["scale"], arms["INVERTED"]["scale"]
    ratio = abs(aN) / abs(a0)
    print()
    print(f"RAW drift              {abs(raw - 1) * r_plane:8.1f} plane px  "
          f"(true scale span {raw:.5f})")
    print(f"sidecar's scale span   {ratio:.5f}  -- it applies "
          f"{100 * (1 - ratio) / (1 - raw):.1f}% of the span that is there")
    print(f"predicted residual     {raw / ratio:.5f} from the sidecar alone")
    print(f"MEASURED residual      {asis:.5f}  "
          f"({abs(asis - 1) * r_plane:.1f} plane px, "
          f"{100 * (1 - abs(asis - 1) / abs(raw - 1)):.1f}% of the drift removed)")
    print(f"inverted-sign arm      {abs(inv - 1) * r_plane:8.1f} plane px "
          f"({abs(inv - 1) / abs(raw - 1):.2f}x the raw drift)")
    ok = abs(asis - 1.0) < abs(raw - 1.0) < abs(inv - 1.0)
    print()
    print("SIGN IS CORRECT AS SHIPPED" if ok else "SIGN CHECK DID NOT SEPARATE -- READ THE NUMBERS")

    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(dict(sidecar=sidecar, last=last, reference=ref,
                       a0=abs(a0), aN=abs(aN), arms=arms), fh, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
