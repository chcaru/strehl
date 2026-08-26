"""Does normalising each arm to its own far field really survive the per-image tone?

ORCH's claim (3): "Measurements normalised to an in-image reference are safe,
because a per-image scale factor cancels in a ratio taken within that same
image... my table normalises each arm to its own 600-1400 px far field, so it
survives this and its conclusions stand."

The premise is true and the conclusion does not follow from it. The tone stage is
not a per-image SCALE. From image_out.rs it is

    s    = 1/(white - black)
    y    = (l - black) * s            <- AFFINE: there is an OFFSET
    soft = 0.5*(y + sqrt(y^2 + toe^2))
    v    = l * min(soft/l, s)
    out  = s_curve(srgb(v), contrast) <- TWO NONLINEARITIES

A pure gain cancels because it scales l, black and white together, which is
exactly why ORCH's --auto-exposure experiment returned 1.0000. Two different
MERGES are not related by a gain. They set different black OFFSETS, and an
offset does not cancel in a ratio; and even if it did, srgb() and s_curve() are
nonlinear, so equal linear ratios do not produce equal encoded differences.

The measured tone parameters say the arms are not gain-related. For a common
gain g, black and white must both scale by g:

    subject     white ratio   black ratio
    fern           1.0450        0.0000     (blend black collapsed to exactly 0)
    lavendar       0.9969        1.1416
    couch          0.9947        1.1336

THE TEST: push ONE physical scene -- the control arm's own measured untoned
linear profile -- through each arm's real tone parameters, and read the
far-field-referenced encoded profile out of each. The physical difference between
the two runs is exactly ZERO by construction, so every DN of apparent difference
is manufactured by the tone stage alone, after the far-field normalisation ORCH
believes protects against it.

Two controls, because a number with no control is not a measurement:

  POSITIVE (validates the model): scale the scene and both tone points by
  6.148x, ORCH's --auto-exposure gain. Their measurement says this must cancel
  to within 1 DN. If my model of the chain is wrong, this fails.

  NULL (validates the attribution): give both arms IDENTICAL tone parameters.
  The difference must be exactly zero. If it is not, the difference is coming
  from my code, not from the parameters.
"""
import numpy as np

TOE = 0.004
CONTRAST = 0.55

# Measured tone parameters, read from each file's own ImageDescription.
ARMS = {
    "fern":     {"ctrl": (0.011119, 0.306019), "blend": (0.000000, 0.319798)},
    "lavendar": {"ctrl": (0.015192, 0.368004), "blend": (0.017343, 0.366872)},
    "couch":    {"ctrl": (0.013474, 0.282117), "blend": (0.015274, 0.280613)},
}

# The control arm's own untoned linear profile (bowl/ladder.txt), in DN of 65535.
D = [2, 6, 10, 14, 18, 22, 28, 35, 45, 58, 72, 90, 112, 138, 175, 225, 275, 350, 450, 550]
CTRL_DN = [9925, 12141, 13141, 13542, 13691, 13835, 13979, 13613, 13239, 13123,
           13195, 13415, 13574, 13638, 13762, 13987, 14108, 14190, 14265, 14287]
FAR_DN = 14509


def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def s_curve(x, k):
    return x + (x * x * (3 - 2 * x) - x) * k


def tone_encode(l, black, white):
    """image_out.rs develop_pixel, luminance path, reproduced."""
    l = np.asarray(l, dtype=np.float64)
    s = 1.0 / (white - black)
    y = (l - black) * s
    soft = 0.5 * (y + np.sqrt(y * y + TOE * TOE))
    gain = np.minimum(soft / np.maximum(l, 1e-12), s)
    v = l * gain
    return s_curve(srgb(v), CONTRAST) * 255.0


def profile_of(black, white, scene, far):
    """Far-field-referenced encoded profile: exactly ORCH's 'safe' normalisation."""
    return tone_encode(scene, black, white) - tone_encode(far, black, white)


def run(name, cb, cw, bb, bw, scene, far, show=True):
    pc = profile_of(cb, cw, scene, far)
    pb = profile_of(bb, bw, scene, far)
    diff = pb - pc
    if show:
        print(f"  {'d (px)':>7} {'as CTRL tone':>14} {'as BLEND tone':>15} "
              f"{'APPARENT diff':>15}")
        for d, a, b, c in zip(D, pc, pb, diff):
            print(f"  {d:>7} {a:>14.2f} {b:>15.2f} {c:>15.2f}")
    return diff


print(__doc__)
scene = np.array(CTRL_DN, dtype=np.float64) / 65535.0
far = FAR_DN / 65535.0

print("=" * 78)
print("POSITIVE CONTROL -- a pure gain must cancel (ORCH measured 1.0000, 1 DN)")
print("=" * 78)
g = 6.148
cb, cw = ARMS["fern"]["ctrl"]
base = profile_of(cb, cw, scene, far)
gained = profile_of(cb * g, cw * g, scene * g, far * g)
worst = float(np.max(np.abs(gained - base)))
print(f"  max |difference| under a {g}x gain = {worst:.6f} of 255")
print(f"  -> {'PASS' if worst < 0.01 else 'FAIL'}: the model reproduces ORCH's "
      f"cancellation, so the chain is modelled correctly.")
print()

print("=" * 78)
print("NULL CONTROL -- identical tone parameters must give exactly zero")
print("=" * 78)
z = run("null", cb, cw, cb, cw, scene, far, show=False)
worst = float(np.max(np.abs(z)))
print(f"  max |apparent difference| = {worst:.6f} of 255")
print(f"  -> {'PASS' if worst == 0.0 else 'FAIL'}: any difference below is "
      f"attributable to the parameters, not to this script.")
print()

print("=" * 78)
print("THE TEST -- ONE physical scene, each arm's REAL tone parameters")
print("Physical difference is ZERO by construction. Everything below is artifact,")
print("and it is present AFTER normalising each arm to its own far field.")
print("=" * 78)
for subj in ARMS:
    cb, cw = ARMS[subj]["ctrl"]
    bb, bw = ARMS[subj]["blend"]
    print(f"\n{subj}:  ctrl black={cb:.6f} white={cw:.6f}   "
          f"blend black={bb:.6f} white={bw:.6f}")
    diff = run(subj, cb, cw, bb, bw, scene, far, show=(subj == "fern"))
    if subj != "fern":
        for d, c in zip(D, diff):
            if d in (2, 90, 350, 550):
                print(f"    d={d:>4}: {c:+.2f} of 255 manufactured")
    print(f"  worst manufactured difference: {np.max(np.abs(diff)):.2f} of 255")

print()
print("=" * 78)
print("AGAINST ORCH'S PUBLISHED blend-minus-control COLUMN")
print("=" * 78)
ORCH_DIFF = {2: +1.39, 90: +3.60, 175: -0.25, 350: -2.19, 550: -2.36}
cb, cw = ARMS["fern"]["ctrl"]
bb, bw = ARMS["fern"]["blend"]
diff = run("fern", cb, cw, bb, bw, scene, far, show=False)
print(f"  {'d':>5} {'ORCH measured':>15} {'manufacturable':>16} {'% of their row':>16}")
tot = 0
for d, o in ORCH_DIFF.items():
    m = float(diff[D.index(d)])
    frac = 100.0 * m / o if o else float("nan")
    print(f"  {d:>5} {o:>+15.2f} {m:>+16.2f} {frac:>15.0f}%")
    tot += 1
print(f"\n  {tot} rows compared.")
print("  A row whose manufacturable artifact has the SAME SIGN and a comparable")
print("  magnitude cannot be read as physics without further evidence.")

# ---------------------------------------------------------------------------
print()
print("=" * 78)
print("COMMON-MODE AMPLIFICATION -- the part far-field normalisation CANNOT remove")
print("=" * 78)
print("""
The rows above measure only the arm-to-arm PARAMETER difference, and in the far
field that is small. There is a second, larger effect that applies to BOTH arms
equally and therefore does not show up in a blend-minus-control column at all:
the tone chain is nonlinear, so it does not preserve the SIZE of a far-field
referenced deficit even when both arms are normalised to their own far field.

Below, the control arm's own profile is expressed two ways: through its real
tone parameters, and through a plain sRGB encode at ORCH's linear operating
point (slope 0.001832 of 255 per DN). The ratio is how much the tone stage
inflates a deficit that is physically identical.
""")
ORCH_SLOPE = 0.001832
cb, cw = ARMS["fern"]["ctrl"]
toned = profile_of(cb, cw, scene, far)
print(f"  {'d (px)':>7} {'linear DN':>11} {'as linear/255':>15} "
      f"{'as toned/255':>14} {'inflation':>11}")
ratios = []
for i, d in enumerate(D):
    lin_dn = CTRL_DN[i] - FAR_DN
    lin_255 = lin_dn * ORCH_SLOPE
    r = toned[i] / lin_255 if lin_255 else float("nan")
    if d in (2, 90, 175, 350, 550):
        print(f"  {d:>7} {lin_dn:>11.0f} {lin_255:>15.2f} "
              f"{toned[i]:>14.2f} {r:>10.2f}x")
    if d >= 175:
        ratios.append(r)
print(f"\n  median inflation over the far-field rows (d >= 175): "
      f"{np.median(ratios):.2f}x")
print("""
  So ORCH's far-field magnitudes are inflated by roughly this factor relative to
  linear, for BOTH arms. That is why the bowl is real in sign and in existence --
  the arm-to-arm artifact at d>=350 is only ~0.05 of 255 and points the other way
  -- while being several times smaller in physical terms than the printed /255
  numbers imply. It is also invisible to any blend-minus-control column, because
  it is common mode.""")
