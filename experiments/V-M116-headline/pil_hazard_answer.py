"""V-M116: exposed / not-exposed, commissioned rather than asserted.

Two jobs.

(1) INDEPENDENTLY COMMISSION ORCH'S FALSE-POSITIVE CORRECTION.
    ORCH now says experiments/ORCH-drift-check/ca_radial.py is NOT affected:
    Image.open is used for the TAGS, pixels come from np.memmap, and strip
    contiguity is validated. That is itself a claim. This imports the real
    function and compares it byte-for-byte against tifffile.imread on six M116
    arm files, including files ORCH did not test.

(2) PLANT THE DEFECT ON MY OWN HEADLINE VERIFICATION.
    A verifier that has never been shown to fail is not a verifier. This narrows
    the M85 arm pair exactly the way the hazard does -- np.asarray(Image.open(p))
    -- and reports what that would have done to dD, to dQ, and to the
    small-over-large ratio ORCH warns compresses toward 1.
"""
import sys
from pathlib import Path
import numpy as np
import tifffile
from PIL import Image

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
from ca_radial import load_tiff_u16          # noqa: E402  -- the reader under test

M = Path(r"C:\dev\strehl-out\M116\measure")
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]


def box(a, k):
    h = k // 2
    pad = np.pad(a, ((h, k - 1 - h), (h, k - 1 - h)), mode="edge")
    c = np.pad(pad.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def structure(g):
    hh, ww = g.shape[0] // 4, g.shape[1] // 4
    s = g[:hh * 4, :ww * 4].reshape(hh, 4, ww, 4).mean(axis=(1, 3))
    sd = np.sqrt(np.maximum(box(s * s, 33) - box(s, 33) ** 2, 0))
    up = np.repeat(np.repeat(sd, 4, 0), 4, 1)
    o = np.zeros(g.shape)
    o[:up.shape[0], :up.shape[1]] = up[:g.shape[0], :g.shape[1]]
    if up.shape[0] < g.shape[0]: o[up.shape[0]:, :] = o[up.shape[0] - 1, :]
    if up.shape[1] < g.shape[1]: o[:, up.shape[1]:] = o[:, up.shape[1] - 1][:, None]
    return o


print("=" * 78)
print("(1) COMMISSIONING ORCH's FALSE-POSITIVE CALL ON ca_radial.load_tiff_u16")
print("=" * 78)
files = [M / f"{s}__{a}.tif" for s in SUBJECTS for a in ("B0", "B1u")]
allok = True
for f in files:
    ref = tifffile.imread(f)
    assert ref.dtype == np.uint16, f"{f} loaded as {ref.dtype}, NOT uint16"
    got, w, h = load_tiff_u16(str(f))
    got = np.asarray(got)
    same = got.shape == ref.shape and got.dtype == ref.dtype and np.array_equal(got, ref)
    allok &= same
    print(f"    -> shape {got.shape} dtype {got.dtype}  levels(G) "
          f"{len(np.unique(got[:, :, 1])):6d}   byte-identical to tifffile: {same}")
print(f"\n  VERDICT: ca_radial.load_tiff_u16 == tifffile.imread on {len(files)}/"
      f"{len(files)} files: {allok}")

print()
print("=" * 78)
print("(2) PLANTING THE HAZARD ON MY OWN HEADLINE -- the control that must fail")
print("=" * 78)
for s in SUBJECTS:
    truth = {a: tifffile.imread(M / f"{s}__{a}.tif") for a in ("B0", "B1u", "M0u")}
    for a, v in truth.items():
        assert v.dtype == np.uint16, f"{s}/{a} loaded as {v.dtype}, NOT uint16"
    # the hazard, verbatim: pixels through PIL
    hazard = {a: np.asarray(Image.open(M / f"{s}__{a}.tif")) for a in truth}

    print(f"\n=== {s} ===")
    for a in ("B0", "B1u"):
        t, z = truth[a], hazard[a]
        print(f"  {a:4s} truth: dtype {str(t.dtype):7s} levels(G) {len(np.unique(t[:,:,1])):6d}"
              f"   |  PIL: mode-derived dtype {str(z.dtype):7s} levels(G) "
              f"{len(np.unique(z[:,:,1])):6d}")

    out = {}
    for tag, src in (("TRUTH ", truth), ("HAZARD", hazard)):
        st = structure(src["M0u"][:, :, 1].astype(np.float64))
        mf, md = st <= np.quantile(st, .20), st >= np.quantile(st, .80)
        r = {}
        for a in ("B0", "B1u"):
            g = src[a][:, :, 1].astype(np.float64)
            hp = g - box(g, 5)
            sf, sd_ = hp[mf].std(), hp[md].std()
            r[a] = (np.log10(sf), np.log10(sd_), sf, sd_)
        dD = r["B1u"][1] - r["B0"][1]
        dN = r["B1u"][0] - r["B0"][0]
        # ORCH's "small over large, compresses toward 1" case:
        share = (r["B0"][2] / r["B0"][3]) ** 2
        out[tag] = (dD, dN, dD - dN, share)
        print(f"  {tag}  dD {dD:+.5f}   dN {dN:+.5f}   dQ {dD-dN:+.5f}   "
              f"noise_share(B0) {100*share:7.3f}%")
    (dDt, dNt, dQt, sht), (dDh, dNh, dQh, shh) = out["TRUTH "], out["HAZARD"]
    print(f"  MOVED BY THE HAZARD:  dD {dDh-dDt:+.5f} ({100*(dDh-dDt)/abs(dDt):+.1f}%)"
          f"   dQ {dQh-dQt:+.5f}"
          f"   noise_share {100*sht:.3f}% -> {100*shh:.3f}%  (ratio {shh/sht:.3f}x)")
