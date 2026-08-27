#!/usr/bin/env python
"""Measure the DELIVERED exposure gain, not the hash.

WHY THIS EXISTS. `47-exposure-liveness.ps1` rendered five arms, found four
distinct SHA-256s, and concluded "the exposure path is LIVE". That conclusion
does not follow, and this script is the correction. A hash is sensitive to any
change and specific to none: it cannot tell a delivered 64x exposure change
from a few least-significant bits of floating-point rounding. V-NEVERWORSE
regressed delivered gain instead and got 1.00000x for a commanded 38.3x, which
is the opposite verdict from the same binary.

The ladder that reconciles them, and the rung 47 stopped at:

    argv  ->  banner  ->  bytes moved  ->  the commanded quantity was delivered

"The bytes moved" proves NOT INERT. It does not prove IT DID WHAT IT SAID.

THREE INDEPENDENT CHANNELS, because one channel agreeing with a prediction is
weaker than three channels that would have to fail together:

  1. COMMISSIONING. Plant a known gain into the estimator and require it back.
     Both directions: 2.0x proves it can see a gain, 0.5x proves it is not
     bounded below at 1.0 and not direction-blind. An estimator that returns
     1.000 on a planted 2.0x would produce this experiment's expected answer
     for a reason having nothing to do with the tone stage, and every null
     below would be worthless.
  2. PIXELS. LSQ through the origin, all pixels, arm vs arm.
  3. TONE ANCHORS, free, from the arms' own banners. If the tone stage's black
     and white scale by exactly the commanded gain, then the tone stage SAW the
     gain, and combined with a unit pixel slope the cancellation is localised
     to that stage without rendering anything new. This channel is independent
     of the pixel regression: it reads what the program SAID about its own
     internal state, and channel 2 reads what it DID.

Prediction is pre-registered in 48-prediction.md, committed at e736f892 BEFORE
this ran.

Never PIL on this project's TIFFs -- tifffile only.
"""

import math
import re
import sys
from pathlib import Path

import numpy as np
import tifffile

OUT = Path(r"C:\dev\strehl-out\BUILD-DEFECT\47-expo")
ARMS = {
    "A-auto": "--srgb --auto-exposure",
    "B-plain": "--srgb",
    "C-plus3": "--srgb --exposure 3",
    "D-minus3": "--srgb --exposure -3",
}
# Commanded LINEAR gain each arm asks for, relative to no exposure flag.
COMMANDED = {"A-auto": 6.105, "B-plain": 1.0, "C-plus3": 8.0, "D-minus3": 0.125}

ROWS_PER_CHUNK = 256
FULL = 65535


def lsq_through_origin(chunks):
    """slope minimising sum (y - m*x)^2, accumulated in float64.

    Returned alongside its standard error so a null can be stated with a
    width rather than as a bare number. Chunked because the arrays are ~99e6
    samples each and materialising several of them at once is how this box
    starts swapping.
    """
    sxx = sxy = syy = 0.0
    n = 0
    for x, y in chunks:
        x = np.asarray(x, dtype=np.float64).ravel()
        y = np.asarray(y, dtype=np.float64).ravel()
        sxx += float(x @ x)
        sxy += float(x @ y)
        syy += float(y @ y)
        n += x.size
    if sxx <= 0.0:
        raise ValueError("degenerate: sum of x^2 is zero, no slope is defined")
    slope = sxy / sxx
    rss = max(syy - 2.0 * slope * sxy + slope * slope * sxx, 0.0)
    se = math.sqrt((rss / max(n - 1, 1)) / sxx)
    return slope, se, n, rss


def chunk_pair(a, b, mask_saturated=False):
    for r0 in range(0, a.shape[0], ROWS_PER_CHUNK):
        x = a[r0 : r0 + ROWS_PER_CHUNK]
        y = b[r0 : r0 + ROWS_PER_CHUNK]
        if mask_saturated:
            keep = (x < FULL) & (y < FULL)
            yield x[keep], y[keep]
        else:
            yield x, y


def chunk_planted(a, gain):
    """arm vs itself-times-gain. The planted-gain commissioning arm."""
    for r0 in range(0, a.shape[0], ROWS_PER_CHUNK):
        x = np.asarray(a[r0 : r0 + ROWS_PER_CHUNK], dtype=np.float64)
        yield x, x * gain


def load(name):
    p = OUT / f"{name}.tif"
    if not p.exists():
        sys.exit(f"MISSING {p} -- rerun 47-exposure-liveness.ps1")
    return tifffile.memmap(str(p), mode="r")


def parse_tone(name):
    """Pull `tone : black B, white W (linear), contrast C` from the arm's log."""
    txt = (OUT / f"{name}.log").read_text(errors="replace")
    m = re.search(
        r"tone\s*:\s*black\s+([0-9.eE+-]+),\s*white\s+([0-9.eE+-]+)", txt
    )
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def main():
    print("=" * 74)
    print("DELIVERED exposure gain -- regression, not hash")
    print("=" * 74)

    imgs = {k: load(k) for k in ARMS}
    ref = imgs["B-plain"]
    print(f"\nshape {ref.shape}  dtype {ref.dtype}  samples/arm {ref.size:,}")
    for k in ARMS:
        if imgs[k].shape != ref.shape or imgs[k].dtype != ref.dtype:
            sys.exit(f"REFUSING: {k} has a different geometry from B-plain")

    # ---- CHANNEL 1: COMMISSIONING ------------------------------------------
    print("\n" + "-" * 74)
    print("CHANNEL 1 -- COMMISSIONING the estimator (must pass before any null")
    print("             below is worth reading)")
    print("-" * 74)
    print(f"{'planted':>10} {'recovered':>14} {'abs err':>12}   verdict")
    commission_ok = True
    for planted in (2.0, 0.5, 1.0):
        got, se, n, _ = lsq_through_origin(chunk_planted(ref, planted))
        err = abs(got - planted)
        ok = err < 1e-9
        commission_ok &= ok
        print(
            f"{planted:>10.4f} {got:>14.9f} {err:>12.2e}   "
            f"{'PASS' if ok else 'FAIL'}"
        )
    print(
        "\n  0.5x is the perverse-metric arm: an estimator bounded below at 1.0,"
        "\n  or blind to direction, passes the 2.0x arm and fails this one."
    )
    if not commission_ok:
        sys.exit("\nREFUSING to report any real slope: the estimator is not commissioned.")
    print("\n  COMMISSIONED: the estimator returns planted gains in both directions.")

    # ---- CHANNEL 2: PIXELS -------------------------------------------------
    print("\n" + "-" * 74)
    print("CHANNEL 2 -- DELIVERED gain at the pixels, LSQ through origin")
    print("-" * 74)
    pairs = [
        ("D-minus3", "C-plus3", COMMANDED["C-plus3"] / COMMANDED["D-minus3"]),
        ("A-auto", "B-plain", COMMANDED["B-plain"] / COMMANDED["A-auto"]),
    ]
    results = {}
    print(
        f"{'y  vs  x':>22} {'commanded':>11} {'delivered':>13} "
        f"{'95% CI half':>12} {'n':>14}"
    )
    for ynm, xnm, commanded in pairs:
        for masked in (False, True):
            slope, se, n, _ = lsq_through_origin(
                chunk_pair(imgs[xnm], imgs[ynm], mask_saturated=masked)
            )
            tag = f"{ynm} vs {xnm}" + (" (unsat)" if masked else "")
            print(
                f"{tag:>22} {commanded:>11.5f} {slope:>13.7f} "
                f"{1.96 * se:>12.2e} {n:>14,}"
            )
            if not masked:
                results[(ynm, xnm)] = (slope, se, commanded)

    # ---- residual character -------------------------------------------------
    print("\n" + "-" * 74)
    print("CHANNEL 2b -- residual CHARACTER (is the difference a gain, or noise?)")
    print("-" * 74)
    for ynm, xnm, _ in pairs:
        a = imgs[xnm]
        b = imgs[ynm]
        ndiff = 0
        maxabs = 0
        tot = 0
        for r0 in range(0, a.shape[0], ROWS_PER_CHUNK):
            x = np.asarray(a[r0 : r0 + ROWS_PER_CHUNK], dtype=np.int32)
            y = np.asarray(b[r0 : r0 + ROWS_PER_CHUNK], dtype=np.int32)
            d = np.abs(y - x)
            ndiff += int(np.count_nonzero(d))
            m = int(d.max()) if d.size else 0
            maxabs = max(maxabs, m)
            tot += d.size
        print(
            f"  {ynm} vs {xnm}: samples differing {ndiff:,}/{tot:,} "
            f"({100.0*ndiff/tot:.4f}%), max |delta| {maxabs} counts of {FULL}"
        )

    # ---- CHANNEL 3: TONE ANCHORS -------------------------------------------
    print("\n" + "-" * 74)
    print("CHANNEL 3 -- did the TONE STAGE see the gain? (from the arms' own")
    print("             banners; independent of the pixel regression)")
    print("-" * 74)
    tones = {k: parse_tone(k) for k in ARMS}
    base = tones.get("B-plain")
    tone_ok = None
    if base is None or any(v is None for v in tones.values()):
        print("  NOT AVAILABLE: at least one arm's log has no tone line.")
        print("  This channel is SKIPPED, not passed.")
    else:
        bb, bw = base
        print(
            f"{'arm':>10} {'black':>12} {'white':>12} "
            f"{'blk ratio':>11} {'wht ratio':>11} {'commanded':>11}"
        )
        tone_ok = True
        for k in ("B-plain", "C-plus3", "D-minus3", "A-auto"):
            kb, kw = tones[k]
            rb = kb / bb if bb else float("nan")
            rw = kw / bw if bw else float("nan")
            cmd = COMMANDED[k]
            print(
                f"{k:>10} {kb:>12.5f} {kw:>12.5f} {rb:>11.4f} "
                f"{rw:>11.4f} {cmd:>11.4f}"
            )
            # 5 printed decimals is the resolution limit here, so the tolerance
            # is generous by necessity and stated rather than hidden.
            if not (abs(rw - cmd) <= 0.02 * cmd):
                tone_ok = False
        print(
            "\n  If the ratios track 'commanded', the tone stage RECEIVED the gain"
            "\n  and moved its own anchors by it. Combined with a unit pixel slope"
            "\n  that is cancellation, not an ignored flag."
        )

    # ---- VERDICTS, each one gated ------------------------------------------
    print("\n" + "=" * 74)
    print("VERDICTS  (every number printed above that matters is tested here)")
    print("=" * 74)

    dc_slope, dc_se, dc_cmd = results[("D-minus3", "C-plus3")]
    ab_slope, ab_se, ab_cmd = results[("A-auto", "B-plain")]

    def classify(slope, commanded, se):
        hi = 1.96 * se
        if abs(slope - commanded) <= max(0.01 * commanded, 3 * hi):
            return "DELIVERED"
        if abs(slope - 1.0) <= max(1e-3, 3 * hi):
            return "CANCELLED"
        return "PARTIAL"

    v_dc = classify(dc_slope, dc_cmd, dc_se)
    v_ab = classify(ab_slope, ab_cmd, ab_se)
    print(f"  D vs C  commanded {dc_cmd:9.5f}  delivered {dc_slope:.7f}  -> {v_dc}")
    print(f"  A vs B  commanded {ab_cmd:9.5f}  delivered {ab_slope:.7f}  -> {v_ab}")

    if v_dc == "CANCELLED" and v_ab == "CANCELLED":
        print("\n  OVERALL: the commanded exposure is CANCELLED before it reaches")
        print("           the file. The flag is not inert -- it is undone.")
        if tone_ok is True:
            print("           LOCALISED to the tone stage: its anchors moved by the")
            print("           commanded gain (channel 3), while the pixels did not.")
        elif tone_ok is False:
            print("           NOT localised: tone anchors did NOT track the command,")
            print("           so the cancellation is somewhere else. Investigate.")
        else:
            print("           Localisation SKIPPED (no tone line); not established.")
        print("\n  Therefore 47-exposure-liveness's verdict 'the path is LIVE' is")
        print("  WITHDRAWN. It measured f32 rounding and reported it as liveness.")
        rc = 2
    elif v_dc == "DELIVERED" and v_ab == "DELIVERED":
        print("\n  OVERALL: the commanded exposure IS delivered. The cancellation")
        print("           hypothesis is refuted and V-NEVERWORSE needs another")
        print("           explanation.")
        rc = 0
    else:
        print("\n  OVERALL: MIXED/PARTIAL -- neither clean delivery nor clean")
        print("           cancellation. Do not summarise this as either.")
        rc = 3
    print(f"\nexit {rc}  (0=delivered, 2=cancelled, 3=mixed)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
