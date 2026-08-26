"""Does a render RING? A shape test that the sensitivity confound cannot reach.

s37.1 established that the paired overshoot detector's sensitivity depends on
how step-like a render's edges are -- 1.00x on ideal steps, 0.38x on the fork's
render, 0.08x on ours. That is the very property under dispute, so any
comparison of overshoot MAGNITUDES between two stackers is confounded at the
root, and no amount of care in running it removes that.

This asks a different question, one whose answer is qualitative:

    **Does the mean normalised edge profile leave the interval [0, 1]?**

A blurred edge, however heavily blurred, transitions monotonically between its
two plateaus and NEVER exceeds either of them. Blur is a non-negative-kernel
convolution and cannot produce a value outside the local range of its input.
Ringing is exactly the opposite: a kernel with negative lobes -- Lanczos, or a
Wiener restoration pushed too hard -- deposits a local extremum BEYOND the
plateau adjacent to the edge.

So `max(profile) > 1` or `min(profile) < 0` is a statement about the SHAPE of
the transition, not its amplitude. It survives:

  * amplitude scaling      -- each profile is normalised by its own plateaus
  * a monotone tone curve  -- monotone maps preserve "does not exceed the range"
  * DIFFERENT EDGE BLUR    -- which is the whole point; a blurrier edge has a
                              wider transition and still no excursion

and it never divides by a calibration factor, so the 4.75x sensitivity gap
cannot enter the answer.

NO RESAMPLING. The two renders have different rasters (a coverage rescale
differs between them), and registering one onto the other would resample it --
which changes edge blur, which is the measured quantity. Each render is
therefore measured in its OWN geometry at its OWN edges. Nothing is compared
pixel-to-pixel; only the shape statistic is compared, which is what makes that
legitimate.

COMMISSIONING is not optional and is built in. A synthetic BLURRED step must
return an excursion of exactly zero -- it is the null, and a shape test that
reports ringing on a blurred edge is measuring its own plateau estimator. A
synthetic LANCZOS-3 resampled step must return a positive excursion at its known
size. Both must hold before any render is read.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

HALF = 14
N_EDGES = 60000
PLATEAU = 5

# STATED APPLICABILITY RANGE. This instrument cannot answer on edges wider than
# this, and says so rather than returning a number. Derived by `--range`, which
# sweeps blur and reports the widest edge at which a matched lanczos plant is
# still distinguishable from a matched linear null. Both renders in the
# strehl-vs-fork comparison measured 13.52 and 17.86 samples, several times past
# it, so their excursions of exactly 0.000000 were the test refusing -- not an
# absence of ringing. Re-derive with `--range` if HALF or PLATEAU change.
APPLICABLE_MAX_WIDTH = 2.69


def luma(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path)).astype(np.float64)
    if a.ndim == 2:
        return a
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def profiles(y: np.ndarray, label: str, verbose: bool = True):
    """Mean normalised, consistently oriented edge profile for one image."""
    h, w = y.shape
    lo, hi = np.quantile(y[::7, ::7], [0.005, 0.995])
    amp_floor = 0.15 * (hi - lo)
    gx = np.abs(np.diff(y, axis=1))
    peak = (gx[:, 1:-1] >= gx[:, :-2]) & (gx[:, 1:-1] > gx[:, 2:])
    ys, xs = np.nonzero(peak)
    xs = xs + 1
    keep = (xs > HALF + 2) & (xs < w - HALF - 2)
    ys, xs = ys[keep], xs[keep]
    vals = gx[ys, xs]
    take = np.argsort(vals)[-min(N_EDGES, len(vals)):]
    ys, xs = ys[take], xs[take]

    acc = []
    rej_amp = rej_flat = 0
    for r, c in zip(ys, xs):
        p = y[r, c - HALF:c + HALF + 1]
        a, b = p[:PLATEAU], p[-PLATEAU:]
        la, lb = np.median(a), np.median(b)
        amp = abs(lb - la)
        if amp < amp_floor:
            rej_amp += 1
            continue
        # Both ends must actually BE plateaus, or "exceeds the plateau" is
        # meaningless. Rejected edges are counted, never silently dropped.
        if max(a.std(), b.std()) > 0.15 * amp:
            rej_flat += 1
            continue
        # `(p - la) / (lb - la)` already maps the left plateau to 0 and the
        # right to 1 whatever the edge's polarity, so every profile is ALREADY
        # oriented and overshoot always lands past the right end. An earlier
        # version reversed dark-to-bright edges and renormalised by
        # `max(q[-1] - q[0], 1e-12)`; for a reversed profile that denominator is
        # about -1, the `max` clamped it to 1e-12, and the null returned an
        # excursion of 4.3e11. The plant "passed" at the same absurd scale --
        # which is why the null is the check that matters.
        q = (p - la) / (lb - la)
        acc.append(q)
    if not acc:
        print(f"  {label}: VACUOUS -- no edges with clean plateaus")
        return None
    P = np.vstack(acc)
    mean = P.mean(axis=0)
    # The excursion MUST NOT be read at the samples that defined the plateau.
    # A first version measured max/min over the whole profile and reported
    # ~0.011 on both renders -- and the extrema sat at indices 0 and 28, i.e.
    # inside the plateau-estimation windows themselves. That is the statistic
    # reading back its own reference, biased upward by noise (the nulls were
    # noiseless, so the measured floor never covered that regime). Genuine
    # ringing from a negative-lobe kernel lands 1-3 samples from the
    # transition, never 14. So the excursion is read only OUTSIDE the
    # self-referential samples.
    lo, hi = PLATEAU, 2 * HALF + 1 - PLATEAU
    inner = mean[lo:hi]
    over = float(inner.max() - 1.0)
    under = float(0.0 - inner.min())
    if verbose:
        wid = width_10_90(mean)
        answerable = wid <= APPLICABLE_MAX_WIDTH
        print(f"  {label}")
        print(f"    edges used {len(acc)}, rejected {rej_amp} low-amp, "
              f"{rej_flat} no-plateau")
        print(f"    edge width 10-90%               : {wid:.2f} samples "
              f"(applicable range: <= {APPLICABLE_MAX_WIDTH})")
        if answerable:
            print(f"    OVERSHOOT beyond bright plateau : {max(over, 0.0):.6f}")
            print(f"    UNDERSHOOT below dark plateau   : {max(under, 0.0):.6f}")
            print("    VERDICT: RINGING" if max(over, under) > 1e-4
                  else "    VERDICT: NO RINGING")
        else:
            # Structurally refuse rather than print a number a reader could
            # mistake for a verdict. Outside the applicable range this test
            # returns ~0.000000 whether or not ringing is present, so the
            # number is not merely imprecise -- it is uninterpretable.
            print(f"    VERDICT: REFUSED -- edge width {wid:.2f} exceeds the")
            print(f"      applicable range {APPLICABLE_MAX_WIDTH}. Blur absorbs"
                  " the excursion into a")
            print("      transition that is still rising, so this test reads"
                  " ~0 with or")
            print("      without ringing present. Use a method that does not"
                  " compare an")
            print("      amplitude to an external reference (e.g. ISO 12233"
                  " slanted edge).")
            print(f"    (raw, NOT A VERDICT: over {max(over, 0.0):.6f}, "
                  f"under {max(under, 0.0):.6f})")
        print("    profile: " + " ".join(f"{v:.3f}" for v in mean))
    return mean, over, under


def synth(shift: str, noise: float = 0.0, then_blur: float = 0.0) -> np.ndarray:
    """A field of steps, half-pixel shifted by a kernel with NO negative lobes
    ('linear') or WITH them ('lanczos'), then optionally blurred by an
    identical amount in both cases.

    The null and the plant must differ in one property only: the sign of the
    kernel's lobes. An earlier version blurred the null with a 9-tap Gaussian
    and the plant with a 13-tap one, so the two arms were blurred by different
    amounts and the plant series came out non-monotone in blur -- heavier blur
    apparently producing MORE ringing, which is impossible. That was the
    kernels disagreeing, not the images.
    """
    rng = np.random.default_rng(5)
    h, w = 300, 600
    y = np.zeros((h, w))
    for r in range(h):
        x, lvl = 25, rng.uniform(2000, 9000)
        while x < w:
            run = int(rng.integers(45, 70))
            y[r, x:x + run] = lvl
            lvl = rng.uniform(2000, 9000)
            x += run
    if shift == "lanczos":
        t = np.arange(-2.5, 3.5)
        k = np.sinc(t) * np.sinc(t / 3.0)
    elif shift == "linear":
        k = np.array([0.5, 0.5])
    else:
        k = np.array([1.0])
    k = k / k.sum()
    out = np.empty_like(y)
    for r in range(h):
        out[r] = np.convolve(y[r], k, mode="same")
    if then_blur:
        t2 = np.arange(-8, 9)
        k2 = np.exp(-0.5 * (t2 / then_blur) ** 2)
        k2 = k2 / k2.sum()
        for r in range(h):
            out[r] = np.convolve(out[r], k2, mode="same")
    if noise:
        out = out + rng.normal(0.0, noise, out.shape)
    return out


def width_10_90(mean: np.ndarray) -> float:
    """10-90% rise distance of the mean normalised profile, in samples.

    Calibration-free -- the profile is already normalised by its own plateaus,
    so this is one of the few quantities that IS comparable between two renders
    of different geometry. It is also what decides whether the shape test can
    see anything: the matched-pair commissioning shows the excursion is
    absorbed by blur, so a render whose edges are wider than the blindness
    threshold cannot be read at all.
    """
    def cross(level: float) -> float:
        for i in range(len(mean) - 1):
            if mean[i] <= level < mean[i + 1]:
                d = mean[i + 1] - mean[i]
                return i + (level - mean[i]) / d if d > 0 else float(i)
        return float("nan")
    return cross(0.9) - cross(0.1)


def widths() -> int:
    print("EDGE WIDTH (10-90% of the mean normalised profile), in samples.")
    print("The shape test is blind wherever blur absorbs the excursion, so")
    print("these widths decide whether the renders can be read at all.\n")
    for tag, img in [
        ("synthetic step, no blur  -- shape test SEES ringing (0.063624)",
         synth("linear", 0.0, 0.0)),
        ("synthetic step, blur 1.5 -- shape test BLIND (0.000000)",
         synth("linear", 0.0, 1.5)),
        ("synthetic step, blur 2.5 -- shape test BLIND (0.000013)",
         synth("linear", 0.0, 2.5)),
    ]:
        res = profiles(img, tag, verbose=False)
        print(f"  {width_10_90(res[0]):6.2f}   {tag}")
    return 0


def applicable_range() -> int:
    """Derive the applicability range by sweeping blur, rather than quoting it.

    s38.5 reported a blindness threshold of 4.33 samples, but that came from a
    three-point grid (blur 0 / 1.5 / 2.5) and is therefore an upper bound on
    the last WORKING width, not a measurement of where the test fails. This
    sweeps finely and reports the widest edge at which a matched plant is still
    detectable.
    """
    print("APPLICABILITY RANGE -- swept, not quoted.")
    print("Matched pairs at each blur: linear (no negative lobes) against")
    print("lanczos-3 (negative lobes). Detectable = plant > max(20x null, 1e-4).\n")
    print(f"  {'blur':>5}  {'width 10-90':>11}  {'null':>10}  {'plant':>10}  detectable")
    last_ok = None
    for blur in [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5]:
        nres = profiles(synth("linear", 0.0, blur), "n", verbose=False)
        pres = profiles(synth("lanczos", 0.0, blur), "p", verbose=False)
        if nres is None or pres is None:
            print(f"  {blur:5.2f}  VACUOUS")
            continue
        null = max(nres[1], nres[2], 0.0)
        plant = max(pres[1], pres[2], 0.0)
        wid = width_10_90(nres[0])
        det = plant > max(20.0 * null, 1e-4)
        if det:
            last_ok = wid
        print(f"  {blur:5.2f}  {wid:11.2f}  {null:10.6f}  {plant:10.6f}  "
              f"{'yes' if det else 'NO'}")
    print(f"\n  WIDEST EDGE STILL ANSWERABLE: {last_ok:.2f} samples"
          if last_ok is not None else "\n  NEVER ANSWERABLE")
    print(f"  Module constant is APPLICABLE_MAX_WIDTH = {APPLICABLE_MAX_WIDTH}")
    return 0


def commission() -> int:
    print("COMMISSIONING the shape test")
    print("  Matched pairs: identical pipeline, only the sign of the shift")
    print("  kernel's lobes differs. 'linear' has none, 'lanczos' has them.\n")
    ok = True
    for blur, noise in [(0.0, 0.0), (1.5, 0.0), (2.5, 0.0), (2.5, 150.0)]:
        tag = f"blur sigma={blur:.1f} noise={noise:.0f}"
        nres = profiles(synth("linear", noise, blur), tag, verbose=False)
        pres = profiles(synth("lanczos", noise, blur), tag, verbose=False)
        if nres is None or pres is None:
            print(f"  {tag}: VACUOUS")
            return 1
        null = max(nres[1], nres[2], 0.0)
        plant = max(pres[1], pres[2], 0.0)
        good = plant > max(20.0 * null, 1e-4)
        print(f"  {tag}\n    NULL(linear) {null:.6f}   "
              f"PLANT(lanczos) {plant:.6f}   {'PASS' if good else 'FAIL'}")
        ok &= good
    if ok:
        print("\n  COMMISSIONED -- a positive-lobe kernel never leaves [0,1],")
        print("  a negative-lobe one always does, and that holds at every blur")
        print("  level tested. The test is not blinded by edge width, which is")
        print("  the property that differs between the two renders.")
    else:
        print("\n  NOT COMMISSIONED -- do not read results")
    return 0 if ok else 1


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--commission":
        return commission()
    if len(sys.argv) == 2 and sys.argv[1] == "--range":
        return applicable_range()
    if len(sys.argv) == 2 and sys.argv[1] == "--widths":
        return widths()
    print("EDGE SHAPE, each render in its OWN geometry, no resampling\n")
    for a in sys.argv[1:]:
        profiles(luma(Path(a)), Path(a).name)
        print()
    print("A blurred edge cannot leave [0,1]. A positive excursion is ringing,")
    print("and its size is comparable across renders because nothing here is")
    print("divided by a per-image sensitivity.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
