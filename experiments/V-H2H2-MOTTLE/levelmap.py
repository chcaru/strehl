# Which pyramid level carries a 20-60 px feature, and therefore what exponent
# does the shipped merge apply to the convicted mottle band?
#
# ORCH asserts "~32 px at level 4 and ~64 px at level 5", giving exponents 4 and
# 3. That is an assumption about a level<->scale convention, and this project has
# been burned by exactly that class of unmeasured assumption. If the mapping is
# off by one level the mottle band runs at 5.49 or 7.68 instead of 3.92 -- a
# factor that changes the amplitude of the proposed mechanism substantially.
#
# So measure it. This reimplements the pin's REDUCE/EXPAND in numpy from the
# published kernel (pyramid.rs:79, [1,4,6,4,1]/16, decimate by two) and asks
# which Laplacian level responds most to a sinusoid of known period. No strehl
# code is in the measurement path.
#
# Commissioned on four properties, one of which is an improvement arm:
#   - the pyramid must RECONSTRUCT (a structural check only -- see below)
#   - the peak level must MOVE by one when the period doubles (else the
#     instrument is not reading period at all and every answer is the same answer)
#   - a wrong kernel must break the MAPPING (planted defect)
#   - a sharper input must place energy at a FINER level, not a coarser one
#     (planted improvement -- an instrument that only ever moves one way cannot
#     tell a blur from a resolution gain)
#
# The defect arm was originally "a wrong kernel must break reconstruction" and it
# was INERT: a Laplacian pyramid telescopes exactly for any kernel, because
# `L = x - expand(reduce(x))` and collapse adds back the same `expand(reduce(x))`.
# It reconstructed to 6e-13 with a pure-decimation kernel. Reconstruction is
# therefore necessary but cannot validate the kernel, and the kernel is what the
# mapping depends on. The arm now plants on the mapping, where an identity kernel
# aliases every period into L0 and the defect is unmissable.
#
# The improvement arm originally required the sharp/blurred fine-band ratio to
# exceed a bar of 2.0x. That bar was guessed, it read 1.40x, and the arm failed
# on a true improvement. The energy centroid is directional and needs no bar.

import re
import sys

import numpy as np

KERNEL = np.array([1.0, 4.0, 6.0, 4.0, 1.0], dtype=np.float64) / 16.0
BANDS = 7
# Periods are restricted to exact divisors of the raster and the convolution
# wraps, so the test signal is genuinely periodic. With `edge` padding and a
# period that does not divide the raster, the border discontinuity injects
# broadband energy: a 256 px sinusoid was reported at L0 with a 37% share, and
# 96 px carried a 13% L0 contamination. Both are the boundary, not the signal.
PAD = "wrap"


def conv1(a, k, axis):
    a = np.moveaxis(a, axis, -1)
    r = len(k) // 2
    p = np.pad(a, [(0, 0)] * (a.ndim - 1) + [(r, r)], mode=PAD)
    out = np.zeros_like(a)
    for t, w in enumerate(k):
        out += w * p[..., t:t + a.shape[-1]]
    return np.moveaxis(out, -1, axis)


def blur(a, k=KERNEL):
    return conv1(conv1(a, k, 0), k, 1)


def reduce_(a, k=KERNEL):
    return blur(a, k)[::2, ::2]


def expand(a, shape, k=KERNEL):
    up = np.zeros(shape, dtype=a.dtype)
    up[::2, ::2] = a
    return blur(up, k) * 4.0


def laplacian(img, bands=BANDS, k=KERNEL):
    """Levels 0..bands-2 are Laplacian bands; the last is the Gaussian residual."""
    cur, out = img.astype(np.float64), []
    for _ in range(bands - 1):
        nxt = reduce_(cur, k)
        out.append(cur - expand(nxt, cur.shape, k))
        cur = nxt
    out.append(cur)
    return out


def collapse(lv, k=KERNEL):
    cur = lv[-1]
    for b in reversed(lv[:-1]):
        cur = b + expand(cur, b.shape, k)
    return cur


def band_energy(lv):
    """Energy per level, referred to the ORIGINAL raster.

    A level on a 2^k grid holds 4^-k as many coefficients, so summed squared
    coefficients understate coarse levels. Sum, don't average: total energy is
    the quantity that is conserved, and the question is where a feature's energy
    lands, not its density.
    """
    return np.array([float(np.sum(b.astype(np.float64) ** 2)) for b in lv])


def sinusoid(n, period, angle=0.0):
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    u = x * np.cos(angle) + y * np.sin(angle)
    return np.sin(2.0 * np.pi * u / period)


def peak_level(period, n=1024, bands=BANDS):
    e = band_energy(laplacian(sinusoid(n, period), bands))
    return int(np.argmax(e)), e


def commission():
    fails = []

    def arm(name, ok, detail):
        print("  %-4s %-46s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            fails.append(name)

    rng = np.random.default_rng(7)
    img = rng.normal(size=(256, 256))
    err = float(np.max(np.abs(collapse(laplacian(img)) - img)))
    arm("pyramid reconstructs (structural only)", err < 1e-9, "max abs err %.3e" % err)

    ps = [int(np.argmax(band_energy(laplacian(sinusoid(1024, float(p))))))
          for p in (8, 16, 32, 64, 128, 256)]
    arm("peak moves one level per octave", ps == list(range(6)),
        "8/16/32/64/128/256px -> L%s" % ps)

    # planted DEFECT, on the mapping rather than on reconstruction: pure
    # decimation with no anti-aliasing must destroy the period->level relation.
    bad = np.array([0.0, 0.0, 1.0, 0.0, 0.0])
    bl = [int(np.argmax(band_energy(laplacian(sinusoid(512, p), BANDS, bad))))
          for p in (8.0, 16.0, 32.0)]
    arm("a wrong kernel breaks the mapping", len(set(bl)) == 1,
        "identity kernel: 8/16/32px all -> L%s (aliased)" % bl)

    # planted IMPROVEMENT: a sharper edge must place its energy at a finer
    # level than a blurred copy. Stated as a centroid so there is no bar to tune.
    edge = np.zeros((256, 256))
    edge[:, 128:] = 1.0
    soft = blur(blur(blur(edge)))
    cen = lambda v: float((np.arange(len(v)) * v).sum() / v.sum())
    ce, cs = cen(band_energy(laplacian(edge))), cen(band_energy(laplacian(soft)))
    arm("a sharper input lands finer", ce < cs,
        "centroid level sharp %.4f < blurred %.4f" % (ce, cs))

    # the boundary artifact that this instrument was originally wrong about.
    # A non-divisor period under edge padding must be visibly contaminated;
    # this arm exists so the regression cannot come back silently.
    global PAD
    PAD, dirty = "edge", None
    try:
        dirty = int(np.argmax(band_energy(laplacian(sinusoid(1024, 256.0)))))
    finally:
        PAD = "wrap"
    clean = int(np.argmax(band_energy(laplacian(sinusoid(1024, 256.0)))))
    arm("edge padding is what broke long periods", dirty == 0 and clean == 5,
        "256px: edge-pad -> L%d (wrong), wrap-pad -> L%d" % (dirty, clean))

    # Cross-lane check. V-NEVERWORSE derived the exponent ladder independently,
    # from its own reimplementation, and published it in a table. If the two
    # disagree, one of us is wrong and neither result should be quoted. This
    # FAILS if the file is missing: an unverifiable claim of independent
    # confirmation must not read as a pass.
    import os
    p = os.path.join("experiments", "V-NEVERWORSE", "RESULT.md")
    rows, txt = [], None
    if os.path.exists(p):
        txt = open(p, encoding="utf-8").read()
        for k in range(BANDS):
            m = re.search(r"\|\s*L%d\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|" % k, txt)
            if m:
                rows.append((int(m.group(1)), float(m.group(2))))
    ok = (len(rows) == BANDS
          and [c for c, _ in rows] == [2 ** k for k in range(BANDS)]
          and all(abs(e - round(LADDER[k], 2)) < 5e-3 for k, (_, e) in enumerate(rows)))
    arm("V-NEVERWORSE's independent ladder agrees", ok,
        "their table: cells %s exponents %s"
        % ([c for c, _ in rows], [e for _, e in rows]) if rows else "TABLE NOT FOUND")
    return fails


LADDER = [8.0000, 8.0000, 7.6832, 5.4880, 3.9200, 2.8000, 2.0000]


def main():
    print("commissioning")
    if commission():
        print("\nRED")
        return 1
    print("  GREEN\n")

    print("which Laplacian level carries a feature of period P, bands = %d" % BANDS)
    print("  (periods are exact divisors of the 1024 px raster; see PAD note)")
    print("  %-10s %-8s %-10s %s" % ("period px", "level", "exponent", "share"))
    for p in (8, 16, 32, 64, 128, 256, 512):
        k, e = peak_level(float(p))
        print("  %-10d L%-7d %-10.4f %.1f%%"
              % (p, k, LADDER[k], 100.0 * e[k] / e.sum()))

    print("\n  cross-check against the pin's own arithmetic (pyramid.rs:655-657):")
    print("  \"on a 7040 px frame with 7 bands, level 6 sits on a 110 px grid\"")
    print("  7040 / 110 = %.1f = 2^6, so level k has coefficient spacing 2^k --" % (7040 / 110))
    print("  the same indexing this reimplementation uses. The mapping is")
    print("  period ~ 8 * 2^k output px, i.e. level k peaks at 2^(k+3).")

    print("\nthe convicted mottle band, 20-60 px:")
    ks = sorted({peak_level(float(p))[0] for p in (20, 24, 32, 40, 48, 60)})
    print("  by PASSBAND: levels %s -> exponents %s"
          % (ks, ["%.4f" % LADDER[k] for k in ks]))
    print("\n  what a random 1.5x band-energy fluctuation buys in weight:")
    for k in ks + [4, 5]:
        print("    L%d  p = %-7.4f  1.5^p = %6.2fx" % (k, LADDER[k], 1.5 ** LADDER[k]))

    print("\n" + "=" * 72)
    print("TWO SCALES PER LEVEL. They are different and both are real.")
    print("=" * 72)
    print("""
This distinction has now been got wrong in three independent places, so it is
stated here once, measured, as the thing to cite.

  CELL SPACING, 2^k px
      The sampling grid of level k. Bounds the finest structure the WEIGHT
      FIELD at that level can have. A connected plateau of D cells in the
      weight field is a real image structure of D * 2^k native px, whatever
      the band's passband is. This is the right scale for plateau geometry
      and it is what V-NEVERWORSE's vn_plateau.py:253 uses (`2 ** k`).
      Cross-checked against the pin: pyramid.rs:656 says level 6 spans 64
      output px, and 2^6 = 64.

  PASSBAND PERIOD, ~2^(k+3) px
      The spatial period the Laplacian band at level k is most responsive to.
      Measured above. This is the right scale for asking which level carries a
      20-60 px FEATURE, i.e. band content.

So, for the 20-60 px mottle band, both of these are true and they are not in
conflict:

  a 20-60 px PLATEAU in the weight field  lives at L3 (8 px cells) and L4
  a 20-60 px IMAGE FEATURE                lives at L2 (7.68) and L3 (5.49)

The error to avoid is the third mapping, `2^(k+1)`, asserted in a comment at
vn_split.py:89-90 and used there to choose which levels to examine. It is two
octaves fine and it is not measured. My own earlier report to ORCH cited only
the passband scale and should not be read as refuting the plateau result --
that result rests on cell spacing, which is correct.
""")
    print("  %-7s %-12s %-16s %-10s" % ("level", "cell px", "passband px", "exponent"))
    for k in range(BANDS):
        pb = 2 ** (k + 3)
        print("  L%-6d %-12d %-16s %-10.4f"
              % (k, 2 ** k, ("~%d" % pb) if k < 6 else ">=%d (residual)" % pb, LADDER[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

