"""Commissioning for `flatexp.py`. Five arms, all required to pass.

AGENTS.md is explicit that a metric earns trust only by reading a planted defect
as RED and a known-clean input as GREEN -- and that a suite planting only
degradations cannot separate a metric that is BLIND to a defect from one that is
PERVERSE on it. This project has shipped exactly that bug: a statistic bounded
below by zero, which could never charge for the artifact it was built to catch,
passed every commissioning it was ever given because every plant made the image
worse and every check asked only whether the number went down.

So arm C plants an IMPROVEMENT and requires the scorer to say so.

  A  null            candidate IS the base file. Must read ~1.000 on every
                     ratio and NEUTRAL. An instrument that cannot be quiet
                     cannot be trusted when it is loud.
  B  planted blur    candidate is the base, Gaussian-blurred. Must be scored
                     TRADE: quieter AND materially softer. This is the failure
                     mode the whole comparison exists to catch, because a lower
                     exponent blends more frames and the degenerate limit of
                     this arm is the plain mean.
  C  planted improve candidate is the base with HALF THE NOISE and structure
                     untouched by construction. Must be scored FLAT WINS.
                     If B and C are not separated, the scorer is measuring
                     "did the number fall" and is worthless here.
  D  planted noise   candidate is the base plus noise. Must be scored
                     FLAT LOSES. Tests the other side of the tone of the
                     statistic; a one-sided gate has tested half of it.
  E  registration    candidate is the base shifted by 2 px. Must be REFUSED as
                     UNREGISTERED, not silently measured. A per-pixel comparison
                     between images on different grids is not a measurement.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import flatexp as FE  # noqa: E402
import recertlib as R  # noqa: E402

SIZE = 2600
RNG = np.random.default_rng(20260824)


def synth():
    """A base image built so that EACH BAND IS DOMINATED BY WHAT IT MEASURES.

    This matters more than realism, and two earlier versions got it wrong in ways
    worth recording, because both failures were the plant's and not the
    instrument's.

    First version carried 65-px checker blocks and `sin(r/7)` rings, whose period
    is ~44 px -- squarely inside the `mottle` (21-61 px) passband. The mottle
    floor was therefore STRUCTURE-dominated, so halving the noise moved it from
    1.0000 to 1.0002 and the planted improvement was invisible.

    Second version used DENSE 7-px and 11-px checkerboards for the `struct` band.
    Measured, that gave `struct` floor=4.587, peak=10.559, and therefore
    structure=0.000: a dense periodic texture raises the MAD floor exactly as
    much as it raises the p99.5 peak, so `band_stats` correctly reported no
    structure above the noise and refused every sharpness claim. It also beat at
    the 77-px LCM of 7 and 11, re-contaminating the mottle band (floor 0.191
    against a pure-noise prediction of 0.078).

    The lesson is a property of the instrument that is worth stating: `structure`
    is p99.5 over MAD, so it detects SPARSE features and is deliberately blind to
    dense texture. Real detail -- edges, specular points, hairs -- is sparse.
    So the plant is sparse:

      grain  (<=3 px)   white noise, nothing else there
      struct (5-13 px)  ~2000 discs of radius 4 on ~1.5% of the area, well above
                        the noise and sparse enough to live in p99.5
      mottle (21-61 px) no deliberate structure -- a smooth linear gradient only,
                        so its floor is noise and a denoise plant moves it by the
                        factor it was planted with.
    """
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    s = 12000.0 + 2.0 * x + 1.5 * y          # smooth; carries no mottle-band energy

    rng = np.random.default_rng(4242)
    n = 2000
    r = 4
    cy = rng.integers(r, SIZE - r, n)
    cx = rng.integers(r, SIZE - r, n)
    dy, dx = np.mgrid[-r:r + 1, -r:r + 1]
    stamp = (dy * dy + dx * dx <= r * r).astype(np.float32) * 9000.0
    for j in range(n):
        s[cy[j] - r:cy[j] + r + 1, cx[j] - r:cx[j] + r + 1] += stamp
    return s


STRUCT = synth()


def noise_field(rng):
    """White grain PLUS band-limited mottle, because the artifact is mottle.

    A first version planted white noise only. Measured, that moved the `mottle`
    (21-61 px) floor from 1.0000 to 0.9947 when halved -- a 0.53% move, under the
    2% tolerance, so the planted IMPROVEMENT read as NEUTRAL and the arm failed.
    The reason is that white noise is suppressed ~20x by a 21-61 px passband,
    while the sparse discs leak into it through their own random clustering; the
    floor there was structure-driven, not noise-driven, so halving the noise
    barely touched it.

    Planting mottle-band noise is not a convenience, it is the correct plant:
    the defect this whole comparison exists to price is MID-SCALE MOTTLE, and a
    commissioning that never puts energy in the mottle band has never asked the
    statistic the question it will be asked in production.
    """
    white = rng.normal(0, 400.0, (SIZE, SIZE)).astype(np.float32)
    coarse = R.boxblur(rng.normal(0, 1.0, (SIZE, SIZE)).astype(np.float64), 15)
    coarse = (coarse / float(coarse.std()) * 600.0).astype(np.float32)
    return white + coarse


def make(kind):
    rng = np.random.default_rng(11071)
    base_noise = noise_field(rng)
    base = STRUCT + base_noise
    if kind == "null":
        cand = base.copy()
    elif kind == "blur":
        cand = R.boxblur(base.astype(np.float64), 3).astype(np.float32)
    elif kind == "improve":
        # Structure IDENTICAL by construction; only the noise term is halved.
        cand = STRUCT + base_noise * 0.5
    elif kind == "noise":
        cand = base + noise_field(np.random.default_rng(99))
    elif kind == "softonly":
        # Detail spent, nothing bought: the structure is blurred while the noise
        # term is left BIT-IDENTICAL, so the mottle floor cannot move. This is
        # the case the first verdict rule got wrong on real data -- it read
        # "NEUTRAL" on coffee-bubbles at blotch 1.0065 while sharpness had fallen
        # to 0.8587. A sharpness loss that buys nothing must convict on its own.
        cand = R.boxblur(STRUCT.astype(np.float64), 2).astype(np.float32) + base_noise
    elif kind == "shift":
        cand = np.roll(base, 2, axis=0)
    else:
        raise ValueError(kind)

    def to16(a):
        return np.repeat(np.clip(a, 0, 65535).astype(np.uint16)[:, :, None], 3, axis=2)
    return to16(base), to16(cand)


EXPECT = {
    "null": "NEUTRAL",
    "blur": "TRADE",
    "improve": "FLAT WINS",
    "noise": "FLAT LOSES",
    "softonly": "FLAT LOSES",
    "shift": "UNREGISTERED",
}


def run_arm(kind, tmp):
    d, f = tmp / "def", tmp / "flat"
    for p in (d, f):
        shutil.rmtree(p, ignore_errors=True)
        p.mkdir(parents=True)
    base, cand = make(kind)
    tifffile.imwrite(d / "SYNTH--DEF-2f858c62.tiff", base)
    tifffile.imwrite(f / "SYNTH--FLAT1-2f858c62.tiff", cand)
    FE.DEF_DIR, FE.FLAT_DIR = d, f

    r = FE.score_subject("SYNTH")
    if r["state"] != "SCORED":
        return r["state"], None, None, r

    cells = r["cells"]
    blotch, _ = FE.ratios(cells, "mottle", "floor")
    sharp, _ = FE.ratios(cells, "struct", "struct")

    def fin(v):
        return v is not None and np.isfinite(v)

    if not (fin(blotch) and fin(sharp)):
        v = "REFUSED"
    else:
        quieter, noisier = blotch < 0.98, blotch > 1.02
        softer, sharper = sharp < 0.98, sharp > 1.02
        if quieter and not softer:
            v = "FLAT WINS"
        elif quieter and softer:
            v = "TRADE"
        elif softer:
            v = "FLAT LOSES"
        elif noisier:
            v = "FLAT LOSES"
        elif sharper:
            v = "FLAT WINS"
        else:
            v = "NEUTRAL"
    return v, blotch, sharp, r


def main():
    tmp = Path(tempfile.mkdtemp(prefix="flatexp-comm-"))
    saved = (FE.DEF_DIR, FE.FLAT_DIR)
    print(f"{'arm':<10} {'expected':<14} {'got':<14} {'blotch':>9} {'sharp':>9}  result")
    print("-" * 74)
    npass = nfail = 0
    try:
        for kind, want in EXPECT.items():
            got, blotch, sharp, _ = run_arm(kind, tmp)
            ok = got == want
            npass, nfail = npass + int(ok), nfail + int(not ok)

            def f(v):
                return f"{v:>9.4f}" if (v is not None and np.isfinite(v)) else f"{'--':>9}"
            print(f"{kind:<10} {want:<14} {got:<14} {f(blotch)} {f(sharp)}  "
                  f"{'PASS' if ok else 'FAIL'}")
    finally:
        FE.DEF_DIR, FE.FLAT_DIR = saved
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{npass} PASS / {nfail} FAIL out of {len(EXPECT)} arms")
    if nfail:
        print("COMMISSIONING FAILED -- do not interpret any flatexp.py output")
        return 1
    print("COMMISSIONING PASSED -- the scorer separates a blur from a denoise,")
    print("is quiet on a null, charges for added noise, and refuses an")
    print("unregistered pair rather than measuring it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
