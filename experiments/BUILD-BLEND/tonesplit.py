"""Separate the tone difference from the image difference in a toned A/B pair.

ORCH profiled ca-ctrl / ca-blend-flower-bud-with-background-fern-cpl.tiff as
"linear, no tone curve". The descriptions those renders wrote into themselves
say otherwise (see tonecheck.py):

    both : "sRGB (IEC 61966-2-1) ... sRGB transfer curve. For viewing."
    ctrl : Tone rendering: black 0.011119, white 0.306019
    blend: Tone rendering: black 0.000000, white 0.319798

The tone black and white are percentiles of EACH IMAGE'S OWN luminance
(TONE_BLACK_PCT 0.1, TONE_WHITE_PCT 99.9), so the two arms went through two
DIFFERENT affine placements before a shared sRGB encode and s-curve. A
cross-arm DN difference therefore mixes a global tone difference into every
row, and the mixture is not a constant offset: the chain is nonlinear, so the
same tone difference is worth different DN at different levels.

This quantifies it. For each row, given the CONTROL DN:

  1. invert the control's full chain to recover the true linear value v;
  2. push that SAME v through the BLEND arm's chain;
  3. the result is what the blend row would read if the underlying image were
     byte-identical to the control's -- i.e. the pure tone artifact;
  4. whatever is left over against the blend's ACTUAL DN is the real image
     difference.

Chain reproduced from crates/strehl-cli/src/image_out.rs:

    Tone::gain   s = 1/(white-black); y = (l-black)*s
                 soft = 0.5*(y + sqrt(y^2 + toe^2)); gain = min(soft/l, s)
    develop_pixel  v *= gain -> gamut_map -> srgb_encode -> s_curve(contrast)
                   -> *65535
    s_curve      s = x*x*(3-2x); return x + (s-x)*strength
    srgb_encode  v<=0.0031308 ? 12.92v : 1.055*v^(1/2.4) - 0.055

Neutral grey is assumed (R=G=B), so luma709(v,v,v) = v and gamut_map is
identity. The backdrop this is applied to is a near-neutral grey/white field,
which is the case the assumption is good for; it is stated because it is an
assumption.
"""

import sys

TONE_TOE = 0.004
TONE_CONTRAST = 0.55
MAXV = 65535.0

# Read off the two files' own ImageDescription tags by tonecheck.py.
CTRL = {"black": 0.011119, "white": 0.306019, "contrast": 0.550}
BLEND = {"black": 0.000000, "white": 0.319798, "contrast": 0.550}

# ORCH's table: (label, control DN, blend DN)
ROWS = [
    ("0-4", 39402, 40488),
    ("8-12", 45688, 46262),
    ("16-20", 49789, 50024),
    ("25-30", 54199, 55456),
    ("30-40", 54725, 56935),
    ("50-65", 54871, 57708),
    ("65-80", 55110, 57907),
    ("80-100", 55516, 58038),
    ("100-125", 56150, 58133),
    ("125-150", 56706, 58268),
    ("150-200", 57912, 58398),
    ("200-250", 59075, 58540),
    ("250-300", 59604, 58737),
    ("300-400", 59358, 58792),
    ("400-500", 59282, 58638),
    ("500-600", 59201, 58544),
    ("far 600-1400", 59630, 60260),
]


def gain(lum, t):
    l = max(lum, 0.0)
    if l <= 0.0:
        return 0.0
    s = 1.0 / (t["white"] - t["black"])
    y = (l - t["black"]) * s
    soft = 0.5 * (y + (y * y + TONE_TOE * TONE_TOE) ** 0.5)
    return min(soft / l, s)


def srgb_encode(v):
    if v <= 0.0031308:
        return 12.92 * v
    return 1.055 * (v ** (1.0 / 2.4)) - 0.055


def s_curve(x, strength):
    s = x * x * (3.0 - 2.0 * x)
    return x + (s - x) * strength


def forward(v, t):
    """Linear neutral value -> output DN, through the whole viewing chain."""
    g = gain(v, t)
    x = min(max(v * g, 0.0), 1.0)
    x = srgb_encode(x)
    x = s_curve(x, t["contrast"])
    return x * MAXV


def invert(dn, t):
    """Output DN -> linear neutral value, by bisection (forward is monotone)."""
    lo, hi = 0.0, 4.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if forward(mid, t) < dn:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main():
    print("=" * 78)
    print("DECOMPOSING ORCH'S TABLE: how much of each row is TONE, not image?")
    print("=" * 78)
    print()
    print(f"  ctrl  tone: black {CTRL['black']:.6f}  white {CTRL['white']:.6f}"
          f"  span {CTRL['white'] - CTRL['black']:.6f}")
    print(f"  blend tone: black {BLEND['black']:.6f}  white {BLEND['white']:.6f}"
          f"  span {BLEND['white'] - BLEND['black']:.6f}")
    span_ratio = (BLEND["white"] - BLEND["black"]) / (CTRL["white"] - CTRL["black"])
    print(f"  span ratio blend/ctrl: {span_ratio:.5f}  "
          f"({(span_ratio - 1) * 100:+.2f}% -- blend compresses harder)")
    print()

    # Sanity: a pure null. Same linear in, both tones out.
    print("-" * 78)
    print("PURE NULL -- identical linear input through both tones")
    print("-" * 78)
    print(f"{'linear':>10} {'ctrl DN':>10} {'blend DN':>10} {'tone-only':>11}")
    for v in (0.05, 0.10, 0.15, 0.20, 0.25, 0.28, 0.30, 0.32):
        a, b = forward(v, CTRL), forward(v, BLEND)
        print(f"{v:10.3f} {a:10.0f} {b:10.0f} {b - a:+11.0f}")
    print()
    print("  Every number in that last column is produced with ZERO difference")
    print("  in the underlying image. It is the tone alone.")
    print()

    print("-" * 78)
    print("ORCH'S ROWS, DECOMPOSED")
    print("-" * 78)
    print(f"{'d (px)':>13} {'ctrl':>8} {'blend':>8} {'reported':>9} "
          f"{'tone-only':>10} {'REAL':>8}")
    tot_rep = tot_tone = 0.0
    for label, dc, db in ROWS:
        v = invert(dc, CTRL)
        pred = forward(v, BLEND)
        reported = db - dc
        tone_only = pred - dc
        real = db - pred
        tot_rep += abs(reported)
        tot_tone += abs(tone_only)
        print(f"{label:>13} {dc:8d} {db:8d} {reported:+9.0f} "
              f"{tone_only:+10.0f} {real:+8.0f}")

    print()
    print("  'tone-only' is what the row would read if the two images were")
    print("  IDENTICAL. 'REAL' is what survives once that is removed.")
    print()
    print(f"  sum |reported| = {tot_rep:,.0f} DN")
    print(f"  sum |tone-only| = {tot_tone:,.0f} DN "
          f"({100 * tot_tone / tot_rep:.0f}% of the reported total)")

    # ---------------------------------------------------------------
    # Error bar. The chain is strongly compressive near saturation, so
    # inverting DN -> linear amplifies error there, and the far-field rows sit
    # at ~0.91 of full scale. Without this, the high rows would be quoted with
    # the same confidence as the mid rows, which they do not deserve.
    # ---------------------------------------------------------------
    print()
    print("-" * 78)
    print("SENSITIVITY -- how much does REAL move per 1 DN of error in ctrl?")
    print("-" * 78)
    print(f"{'d (px)':>13} {'ctrl DN':>8} {'lin':>8} {'REAL':>8} "
          f"{'d(REAL)/dDN':>12} {'REAL +/- 50DN':>16}")
    for label, dc, db in ROWS:
        v = invert(dc, CTRL)
        real = db - forward(v, CTRL if False else BLEND)
        hi = db - forward(invert(dc + 50, CTRL), BLEND)
        lo = db - forward(invert(dc - 50, CTRL), BLEND)
        slope = (hi - lo) / 100.0
        print(f"{label:>13} {dc:8d} {v:8.4f} {real:+8.0f} {slope:+12.3f} "
              f"{min(lo, hi):+8.0f}..{max(lo, hi):+.0f}")
    print()
    print("  A slope near -1 means the row is well conditioned: an error in the")
    print("  control DN passes through roughly one-for-one. A slope far from -1")
    print("  means the two arms' tones have very different local gain there and")
    print("  the row is amplified. Read the top rows with that in mind.")


if __name__ == "__main__":
    sys.exit(main())
