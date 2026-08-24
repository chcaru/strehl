"""E6 -- what the shipped single-election actually costs the off-channels,
plus two robustness arms and the no-CPL control.

E3 establishes that R and B reach best focus at a different frame from G.  That
is only worth acting on if electing them at G's frame costs something MEASURABLE.
This prices it three ways:

  1. FOCUS-ENERGY LOSS.  loss_c = 1 - F_c(k_G) / F_c(k_c), the fraction of
     gradient energy channel c forfeits by being elected at green's frame
     instead of its own.  F is evaluated at fractional k by the same parabola
     used for the argmax, so the loss is not quantised to whole frames.

  2. IN DEPTH-OF-FIELD UNITS.  The through-focus response has a width; a 1-frame
     offset means nothing until it is compared to it.  W is the half-width of
     F_G at half its prominence above the local floor, in frames.  delta/W is
     the offset as a fraction of one depth of field.

  3. THE NULL FLOOR.  loss_G1 = 1 - F_G1(k_G2)/F_G1(k_G1) is the same
     quantity computed between the two greens, i.e. the loss you would book by
     electing a channel at a same-wavelength neighbour's index.  Any real cost
     must beat it.

Arms, to show the E3 number is not a property of one operator or one warp:
  --warp-off   gather with the identity instead of the render's own sidecar
  --laplace    replace Sobel gradient energy with Laplacian energy
  --win 15/41  change the box support from the shipped 27
"""
import sys, os, json, time
import numpy as np
from scipy.ndimage import uniform_filter, sobel, laplace

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, dump, frames
import e3_argmax as E
from e3_argmax import (PLANES, read_warpmap, gather_planes, subframe_argmax)

import rawpy


def focus_op(plane, kind, win):
    if kind == "sobel":
        gx = sobel(plane, axis=1, mode="nearest")   # 2-D plane only -- rule 23
        gy = sobel(plane, axis=0, mode="nearest")
        e = gx * gx + gy * gy
    elif kind == "laplace":
        l = laplace(plane, mode="nearest")
        e = l * l
    else:
        raise ValueError(kind)
    return uniform_filter(e, win, mode="nearest")


def sample_at(F, k):
    """F is (nk,ny,nx); k is a float map. Parabolic interpolation through the
    three samples bracketing k -- the same model the sub-frame argmax uses, so
    the loss and the argmax cannot disagree by construction."""
    nk = F.shape[0]
    k0 = np.clip(np.round(k).astype(int), 1, nk - 2)
    I, J = np.ogrid[: F.shape[1], : F.shape[2]]
    y0, y1, y2 = F[k0 - 1, I, J], F[k0, I, J], F[k0 + 1, I, J]
    t = k - k0
    a = 0.5 * (y0 - 2 * y1 + y2)
    b = 0.5 * (y2 - y0)
    return a * t * t + b * t + y1


def halfwidth(F, k, conf):
    """Half-width of the through-focus peak, in frames, at half prominence."""
    nk = F.shape[0]
    peak = sample_at(F, k)
    floor = np.min(F, axis=0)
    half = floor + 0.5 * (peak - floor)
    above = F > half[None, :, :]
    return above.sum(axis=0).astype(np.float32)  # frames above half height


def run(stack, sidecar, x0, y0, w, h, warp=True, kind="sobel", win=27, tag=""):
    E.WIN = win
    fs = frames(stack)
    meta, warps = read_warpmap(sidecar)
    assert int(meta["frames"]) == len(fs)
    F = {c: np.empty((len(fs), h, w), dtype=np.float32) for c in PLANES}
    t0 = time.time()
    for k, path in enumerate(fs):
        with rawpy.imread(path) as r:
            cfa = r.raw_image_visible.astype(np.float32)
            black = float(np.mean(r.black_level_per_channel))
        cfa -= black
        pls = gather_planes(cfa, warps[k] if warp else None, x0, y0, w, h, 3)
        for c in PLANES:
            F[c][k] = focus_op(pls[c].astype(np.float32), kind, win)
        if k % 100 == 0:
            print(f"    frame {k}/{len(fs)} ({time.time()-t0:.0f}s)", flush=True)

    res = {}
    for c in PLANES:
        kk, prom, interior, uni = subframe_argmax(F[c])
        res[c] = {"k": kk, "prom": prom, "interior": interior, "uni": uni}
    conf = np.ones((h, w), bool)
    for c in PLANES:
        conf &= res[c]["interior"] & res[c]["uni"] & (res[c]["prom"] >= 3.0)
    m = win
    e = np.zeros((h, w), bool); e[m:-m, m:-m] = True
    conf &= e

    kG = 0.5 * (res["G1"]["k"] + res["G2"]["k"])
    dR = res["R"]["k"] - kG
    dB = res["B"]["k"] - kG
    null = res["G1"]["k"] - res["G2"]["k"]

    def loss(c, at):
        own = sample_at(F[c], res[c]["k"])
        got = sample_at(F[c], at)
        return 1.0 - got / np.maximum(own, 1e-9)

    lR = loss("R", kG)
    lB = loss("B", kG)
    lnull = loss("G1", res["G2"]["k"])          # the floor
    W = halfwidth(F["G1"], res["G1"]["k"], conf)

    def med(a):
        return float(np.median(a[conf]))

    out = {
        "stack": stack, "tag": tag, "arm": f"warp={'on' if warp else 'OFF'},"
                                           f"op={kind},win={win}",
        "nframes": len(fs), "n_conf": int(conf.sum()),
        "median_dR": med(dR), "median_dB": med(dB), "median_null": med(null),
        "median_loss_R": med(lR), "median_loss_B": med(lB),
        "median_loss_NULL": med(lnull),
        "median_halfwidth_frames": med(W),
        "dR_in_DoF": med(dR) / max(med(W), 1e-9),
        "dB_in_DoF": med(dB) / max(med(W), 1e-9),
    }
    print(f"  [{out['arm']}] {stack} n={out['n_conf']}")
    print(f"    dR {out['median_dR']:+.4f}  dB {out['median_dB']:+.4f}  "
          f"NULL {out['median_null']:+.4f} frames")
    print(f"    focus-energy forfeited by electing at green's frame: "
          f"R {out['median_loss_R']*100:+.2f}%  B {out['median_loss_B']*100:+.2f}%"
          f"   NULL floor {out['median_loss_NULL']*100:+.2f}%")
    print(f"    through-focus half-width {out['median_halfwidth_frames']:.2f} frames"
          f"  ->  R sits {out['dR_in_DoF']:+.3f} DoF, B {out['dB_in_DoF']:+.3f} DoF"
          f" from its own best focus", flush=True)
    return out


if __name__ == "__main__":
    R = r"C:\dev\strehl-out\M107-chroma\renders"
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    o = []
    T = ("tweezers-cpl", f"{R}\\tweezers-cpl-warpmap.txt", 1200, 900, 512, 512)
    if which in ("all", "payoff"):
        print("== payoff, shipped operator ==", flush=True)
        o.append(run(*T, warp=True, kind="sobel", win=27, tag="payoff"))
    if which in ("all", "robust"):
        print("== robustness arms ==", flush=True)
        o.append(run(*T, warp=False, kind="sobel", win=27, tag="warp-off"))
        o.append(run(*T, warp=True, kind="laplace", win=27, tag="laplace"))
        o.append(run(*T, warp=True, kind="sobel", win=15, tag="win15"))
        o.append(run(*T, warp=True, kind="sobel", win=41, tag="win41"))
    if which in ("all", "nocpl"):
        print("== B5: no-CPL achromatic control ==", flush=True)
        o.append(run("wrapped-text-1", f"{R}\\wrapped-text-1-warpmap.txt",
                     1200, 900, 512, 512, warp=True, kind="sobel", win=27,
                     tag="no-CPL"))
        o.append(run("coffee-bean", f"{R}\\coffee-bean-warpmap.txt",
                     1200, 900, 512, 512, warp=True, kind="sobel", win=27,
                     tag="no-CPL"))
    dump(f"e6_{which}", o)
