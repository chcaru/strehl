"""V-M116 probe 5: controls that CAN fail, plus mask/parameter dispersion.

C1  self vs self            must be exactly 0.000000
C2  blurred merge vs merge  must be large and NEGATIVE (the instrument must be
                            able to return a negative result)
C3  merge vs itself + noise  a positive dD with no sharpness change at all --
                            shows dD is not a sharpness statistic
C4  mask-source sensitivity  recompute dD with masks from B0, from B1u and from
                            M0u, and with 10/20/30% mask fractions and 3/5/9 px
                            high-pass, to get the dispersion of the headline.
"""
import itertools, json
from pathlib import Path
import numpy as np
import tifffile

M = Path(r"C:\dev\strehl-out\M116\measure")
OUT = Path(r"C:\dev\strehl-out\V-M116")
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]


def load_green(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} loaded as {a.dtype}, NOT uint16"
    return a[:, :, 1].astype(np.float64)


def box(a, k):
    h = k // 2
    pad = np.pad(a, ((h, k - 1 - h), (h, k - 1 - h)), mode="edge")
    c = np.pad(pad.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def structure(g):
    hh, ww = g.shape[0] // 4, g.shape[1] // 4
    small = g[:hh * 4, :ww * 4].reshape(hh, 4, ww, 4).mean(axis=(1, 3))
    m1, m2 = box(small, 33), box(small * small, 33)
    sd = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    up = np.repeat(np.repeat(sd, 4, 0), 4, 1)
    out = np.zeros(g.shape, np.float64)
    out[:up.shape[0], :up.shape[1]] = up[:g.shape[0], :g.shape[1]]
    if up.shape[0] < g.shape[0]: out[up.shape[0]:, :] = out[up.shape[0] - 1, :]
    if up.shape[1] < g.shape[1]: out[:, up.shape[1]:] = out[:, up.shape[1] - 1][:, None]
    return out


def ND(g, mflat, mdet, hpk=5):
    h = g - box(g, hpk)
    return np.log10(h[mflat].std()), np.log10(h[mdet].std())


def gauss_blur(g, sigma):
    r = int(4 * sigma + 0.5)
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-x * x / (2 * sigma * sigma)); k /= k.sum()
    t = np.apply_along_axis(lambda m: np.convolve(m, k, "same"), 0,
                            np.pad(g, ((r, r), (0, 0)), mode="edge"))[r:-r, :]
    t = np.apply_along_axis(lambda m: np.convolve(m, k, "same"), 1,
                            np.pad(t, ((0, 0), (r, r)), mode="edge"))[:, r:-r]
    return t


out = {}
rng = np.random.default_rng(20260824)
for s in SUBJECTS:
    st = structure(load_green(M / f"{s}__M0u.tif"))
    mflat = st <= np.quantile(st, 0.20)
    mdet = st >= np.quantile(st, 0.80)
    g0 = load_green(M / f"{s}__B0.tif")
    g1 = load_green(M / f"{s}__B1u.tif")
    N0, D0 = ND(g0, mflat, mdet)
    N1, D1 = ND(g1, mflat, mdet)
    print(f"\n=== {s} ===")
    print(f"C0 headline  dD(B1u - B0)               = {D1 - D0:+.6f} dex")

    # C1 -- self against self
    Na, Da = ND(g1.copy(), mflat, mdet)
    print(f"C1 self vs self  dD                     = {Da - D1:+.6f} dex  "
          f"(must be exactly 0)")

    # C2 -- a deliberately blurred copy of the merge, against the merge
    for sig in (0.5, 1.0, 2.0):
        Nb, Db = ND(gauss_blur(g1, sig), mflat, mdet)
        print(f"C2 merge blurred sigma={sig:<4} dD        = {Db - D1:+.6f} dex  "
              f"(must be large and NEGATIVE)")

    # C3 -- merge plus white noise: no sharpness change, dD must still rise
    for amp in (10.0, 40.0):
        Nc, Dc = ND(g1 + rng.normal(0, amp, g1.shape), mflat, mdet)
        print(f"C3 merge + N(0,{amp:<5}) dD              = {Dc - D1:+.6f} dex  "
              f"dN {Nc - N1:+.6f}  (noise alone moves D)")

    # C4 -- dispersion of the headline over harness choices
    vals = []
    for src, frac, hpk in itertools.product(["M0u", "B0", "B1u", "A0"],
                                            [0.10, 0.20, 0.30], [3, 5, 9]):
        sx = structure(load_green(M / f"{s}__{src}.tif"))
        mf = sx <= np.quantile(sx, frac)
        md = sx >= np.quantile(sx, 1 - frac)
        n0, d0 = ND(g0, mf, md, hpk)
        n1, d1 = ND(g1, mf, md, hpk)
        vals.append(dict(src=src, frac=frac, hp=hpk, dD=d1 - d0, dN=n1 - n0,
                         dQ=(d1 - n1) - (d0 - n0)))
    dDs = np.array([v["dD"] for v in vals])
    dQs = np.array([v["dQ"] for v in vals])
    print(f"C4 dD over 36 harness variants: min {dDs.min():+.5f}  "
          f"median {np.median(dDs):+.5f}  max {dDs.max():+.5f}  "
          f"sd {dDs.std():.5f}  negative in {int((dDs<0).sum())}/36")
    print(f"C4 dQ over 36 harness variants: min {dQs.min():+.5f}  "
          f"median {np.median(dQs):+.5f}  max {dQs.max():+.5f}  "
          f"sd {dQs.std():.5f}  negative in {int((dQs<0).sum())}/36")
    for v in vals:
        if v["src"] != "M0u" or v["hp"] != 5:
            continue
        print(f"     mask=M0u frac={v['frac']:.2f} hp=5 : dD {v['dD']:+.5f} dQ {v['dQ']:+.5f}")
    for v in vals:
        if v["frac"] != 0.20 or v["hp"] != 5:
            continue
        print(f"     mask={v['src']:4s} frac=0.20 hp=5 : dD {v['dD']:+.5f} dQ {v['dQ']:+.5f}")
    out[s] = dict(headline_dD=D1 - D0, variants=vals)

(OUT / "controls.json").write_text(json.dumps(out, indent=2, default=float))
print(f"\nwrote {OUT/'controls.json'}")
