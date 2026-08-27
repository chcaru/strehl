"""Is 8-bit sRGB good enough for print?  Measured on the paired 16-bit source.

ORCH: "Measure it: count distinct levels in the smooth regions and determine
whether banding is actually reachable at a plausible print size, rather than
asserting it from theory."

WHY THIS IS A PAIRED MEASUREMENT AND NOT A MODEL

We hold both sides of the quantisation: the 16-bit SHIP-V4 master and the 8-bit
PNG derived from it.  So this does not predict banding, it measures the exact
gradation the 8-bit step destroyed, against the file that still contains it.

THE THREE THINGS A BAND NEEDS, AND WHY LEVEL-COUNTING ALONE IS USELESS

  1. GRADATION TO LOSE.  A flat patch scores one level and is perfect at any
     bit depth.  Only a shallow *ramp* can band.
  2. WIDTH.  A staircase tread wider than the eye resolves reads as a plateau
     with a visible edge.  Measured directly as the run length of a constant
     8-bit code along the local gradient, converted to mm at 300 dpi.
  3. HEIGHT.  The jump between treads, in dL*, because L* is uniform in
     perceived lightness and DN is not.  One code near black is many times the
     perceptual step of one code near white.

STRATIFICATION IS NOT OPTIONAL

Point 3 is why every number here is reported per tone stratum.  This project
learned last night that "a clipping gate that tests one end of the tone scale
has tested half the tone scale"; a banding statistic pooled over the frame
commits the identical error, because it lets acres of safe highlight outvote
the shadows where 8 bits is actually thin.  The first version of this file
reported a single median and it came out of tiles whose mean level was 231 --
i.e. it had measured the safest end and would have certified the file.

DITHER

Quantisation only forms a staircase if the signal is smoother than the step.
Real sensor noise above ~0.5 code is a dither: it randomises which side of the
threshold each pixel falls, and the staircase dissolves.  So noise sigma is
reported in units of the 8-bit code, and it is the variable that decides
whether banding is physically reachable at all.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile

SHIP = Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
PNGS = Path(r"C:\dev\strehl-out\DELIVER-V5\full-resolution")
DPI = 300.0
TILE = 96
STRIDE = TILE * 4

# GATING: tread is the free variable; dL* is a property of the ENCODING.
#
# Measured over the whole 8-bit sRGB scale (dl_range.py): dL* per code spans
# only 0.274 (code ~1-16) to 0.509 (code 24) -- a factor of 1.86 across the
# ENTIRE tone range, and only 5 codes of 254 clear 0.50.  That is the sRGB
# transfer curve working exactly as designed: it exists to make one code step
# perceptually near-uniform.  The consequence is sharp and it is easy to get
# wrong -- dL* cannot discriminate between subjects, regions or tones, because
# every 8-bit sRGB step everywhere is within a factor of 1.86 of the visibility
# threshold by construction.
#
# The first version of this file gated at dL* >= 0.5 and so gated on a condition
# satisfiable by 5 codes in 254.  Commissioning caught it: planted ramps with
# 8 px and 40 px treads -- textbook visible banding -- fired on only 3 of 9
# tiles, because the ramp walked out of that 5-code window.  An absolute
# threshold that nothing can reach certifies everything.
#
# So the gate is on TREAD, which is genuinely free and subject-dependent.  dL*
# is retained as a second condition at 0.30, where it binds on exactly the 11
# deepest codes (1-16, dL* = 0.274) in which one code really is sub-threshold.
# Both are printed beside every verdict so either can be argued with.
MIN_TREAD_MM = 0.5
MIN_DL = 0.30

STRATA = (("shadow", 0, 64), ("mid", 64, 192), ("high", 192, 256))


def srgb_to_L(v8):
    c = np.asarray(v8, dtype=np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return np.where(lin > 0.008856, 116.0 * np.cbrt(lin) - 16.0, 903.3 * lin)


LSTAR = srgb_to_L(np.arange(256))


def noise_codes(t16):
    """Sigma of the high-frequency residual, in units of one 8-bit code (=257).

    Second difference along x is a high-pass that rejects any smooth ramp;
    dividing by sqrt(6) restores the per-pixel sigma of white noise.
    """
    d2 = t16[:, 2:] - 2.0 * t16[:, 1:-1] + t16[:, :-2]
    return float(np.std(d2) / np.sqrt(6.0) / 257.0)


def tile_stats(a16, a8):
    h, w = a16.shape
    out = []
    for y in range(0, h - TILE, STRIDE):
        for x in range(0, w - TILE, STRIDE):
            t16 = a16[y:y + TILE, x:x + TILE].astype(np.float64)
            t8 = a8[y:y + TILE, x:x + TILE]
            n16 = len(np.unique(t16))
            if n16 < 8:
                continue                       # flat: cannot band
            if t16.max() - t16.min() > 40 * 257:
                continue                       # steep: ramp outruns the bits
            gy = np.abs(np.diff(t16, axis=0)).mean()
            gx = np.abs(np.diff(t16, axis=1)).mean()
            line = t8[:, TILE // 2] if gy >= gx else t8[TILE // 2, :]
            chg = np.flatnonzero(np.diff(line.astype(np.int16)))
            tread = float(TILE) if len(chg) < 2 else float(np.median(np.diff(chg)))
            lo, hi = int(t8.min()), int(t8.max())
            # dL* is the step to the ADJACENT code, always -- never 0 just
            # because this tile happens to show one code.
            #
            # The earlier version read `... if hi > lo else 0.0`, and the Q6
            # commissioning arm proved that perverse: quantising R3 harder (to
            # 6 bits) made treads 4x wider yet LOWERED the banded fraction from
            # 100% to 66.7%, because the coarsest tiles collapsed to a single
            # plateau, scored dL* = 0, and were certified clean.  A planted
            # degradation that IMPROVES the score is the failure mode a
            # degradation-only suite cannot see, which is why this ladder plants
            # in both directions.
            #
            # Reaching here already means n16 >= 8: the 16-bit master carries
            # real gradation across this tile.  If the 8-bit derivative shows
            # one code, that is total gradation loss -- the most severe banding
            # available, not the least.
            dL = abs(LSTAR[min(lo + 1, 255)] - LSTAR[lo])
            out.append(dict(n16=n16, n8=len(np.unique(t8)), tread=tread,
                            dL=dL, level=float(t8.mean()),
                            sigma=noise_codes(t16)))
    return out


def summarise(st):
    """Per-stratum rows.  Strata partition by level and the counts are printed,
    so a stratum with no tiles reads as EMPTY and never as a pass."""
    rows = []
    for label, lo, hi in STRATA:
        k = [s for s in st if lo <= s["level"] < hi]
        if not k:
            rows.append((label, 0, None))
            continue
        tread_mm = np.array([s["tread"] for s in k]) / DPI * 25.4
        dL = np.array([s["dL"] for s in k])
        banded = (tread_mm >= MIN_TREAD_MM) & (dL >= MIN_DL)
        rows.append((label, len(k), dict(
            n16=float(np.median([s["n16"] for s in k])),
            n8=float(np.median([s["n8"] for s in k])),
            tread_mm=float(np.median(tread_mm)),
            tread_mm_p95=float(np.percentile(tread_mm, 95)),
            dL=float(np.median(dL)), dLmax=float(dL.max()),
            sigma=float(np.median([s["sigma"] for s in k])),
            banded=100.0 * float(banded.mean()),
            banded_n=int(banded.sum()))))
    return rows


def print_rows(name, rows):
    for label, n, r in rows:
        if n == 0:
            print(f"{name:<30}{label:>8}{'EMPTY -- no tiles, NOT a pass':>62}")
            continue
        print(f"{name:<30}{label:>8}{n:>6}{r['n16']:>8.0f}{r['n8']:>6.0f}"
              f"{r['sigma']:>8.2f}{r['tread_mm']:>9.3f}{r['tread_mm_p95']:>9.3f}"
              f"{r['dL']:>7.2f}{r['dLmax']:>7.2f}{r['banded']:>8.1f}"
              f"{r['banded_n']:>5}")


HEAD = (f"{'subject':<30}{'stratum':>8}{'tiles':>6}{'lv16':>8}{'lv8':>6}"
        f"{'sig/code':>8}{'tread_mm':>9}{'p95_mm':>9}{'dL*':>7}{'dL*max':>7}"
        f"{'band%':>8}{'n':>5}")


def load(name):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    a16 = tifffile.imread(str(SHIP / f"{name}--SHIP-V4.tiff"))
    a8 = np.asarray(Image.open(PNGS / f"{name}.png"))
    return a16, a8


def main():
    names = sys.argv[1:]
    if not names:
        names = sorted(p.name.replace("--SHIP-V4.tiff", "")
                       for p in SHIP.glob("*--SHIP-V4.tiff"))
    print(HEAD)
    print("-" * 111)
    worst = []
    for n in names:
        try:
            a16, a8 = load(n)
        except Exception as ex:
            print(f"{n:<30} LOAD FAILED: {ex}")
            continue
        rows = summarise(tile_stats(a16[:, :, 1], a8[:, :, 1]))
        print_rows(n, rows)
        for label, cnt, r in rows:
            if cnt:
                worst.append((r["banded"], n, label, r))
        del a16, a8
    if worst:
        worst.sort(reverse=True)
        print()
        print("  worst strata by banded fraction:")
        for b, n, label, r in worst[:6]:
            print(f"    {b:>6.1f}%  {n} [{label}]  tread {r['tread_mm']:.3f} mm"
                  f"  dL* {r['dL']:.2f}  sigma {r['sigma']:.2f} code")
        allb = np.array([w[0] for w in worst])
        print(f"  strata measured: {len(allb)}   with ANY banded tile: "
              f"{int((allb > 0).sum())}   max banded fraction: {allb.max():.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
