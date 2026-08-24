# M107 addendum — amendment: bar K7, registered before K7 is run

Prior: `bf975e0` registered K1–K6. K1–K6 have now been **run and read** on two
ROIs. This amendment adds one bar, K7, and is committed **before** the K7 code
is executed. It is labelled **POST-HOC relative to K1–K6** everywhere it is
reported, because the idea for it came from looking at K1–K6 output. It is
**pre-registered relative to its own data**, which is the most that can honestly
be claimed for it.

## Why K7 exists

K3 asks whether `rho = rms(HP(chroma)) / rms(HP(luma))` is invariant between
arms, on the theory that a channel-independent filter scales numerator and
denominator alike. Its control K3-CTRL blurs the Catmull-Rom arm by a synthetic
channel-independent Gaussian and requires `rho` to hold.

**K3-CTRL partially failed and that failure is informative.** On the near-centre
ROI it returned `rho_cr` ratios of 0.859 at sigma = 1.0 px and **0.694 at
sigma = 2.0 px** — the latter far outside the `[0.85, 1.18]` band K3 uses. So
`rho` is *not* invariant under strong blur; the first-order displacement
argument decays as the blur becomes comparable to the edge width.

That does **not** invalidate K3, because the two arms differ by far less blur
than sigma = 1.0 px (their luma high-pass rms differ by only 4.4%, and a
sigma = 1.0 blur changes luma rms by much more). But it does mean K3's band was
never calibrated against the actual size of the effect, and an uncalibrated
invariance band is an argument, not a measurement.

## K7 — the direct form of the question

Rather than test a ratio's invariance, do the substitution the orchestrator's
reading literally asserts. Their claim is: *`nearest` shows more fringe only
because Catmull-Rom lowpasses it away.* If that is true, then applying an
equivalent **channel-independent** lowpass to `nearest` must reproduce
Catmull-Rom's chroma.

Procedure:
1. Find `sigma*` by 1-D root-find such that a channel-independent Gaussian blur
   of the `nearest` arm matches `rms(HP(L_catmull))` on the shared edge mask.
   `sigma*` is a useful number in its own right: it is how much lowpass
   Catmull-Rom costs relative to a zero-order hold, in pixels.
2. Compute `rho7 = rms(HP(chroma_nearest_blurred)) / rms(HP(chroma_catmull))`.

**BARS:**

- **Pre-existing fringe, merely blurred (orchestrator's reading): `rho7` in `[0.90, 1.10]`.**
- **`nearest` synthesised chroma (aliasing): `rho7 > 1.20`.**
- **`rho7 < 0.90`** would mean that once luma is matched, `nearest` carries
  *less* chroma than Catmull-Rom — i.e. Catmull-Rom's own kernel adds chroma.
  That would implicate candidate (d) in the opposite direction to everything
  measured so far, and I register it explicitly so that it is a possible
  outcome rather than an unthinkable one.
- Between 1.10 and 1.20: **INDETERMINATE**, reported as such.

**NULL (not optional).** Run the identical procedure on the `bilinear` arm:
blur `catmull-rom` to match `rms(HP(L_bilinear))`, then compare chroma. Both
are interpolating lowpass kernels with no aliasing story, so this pair *must*
land in `[0.90, 1.10]`. If the null fails, the matching procedure itself is
biased and K7's headline number means nothing.

**Reported alongside, not as a bar:** `sigma*`, and the luma rms of each
K3-CTRL point, so the control is calibrated against the real arm separation
instead of being quoted at an arbitrary blur.

## Reach

Unchanged from `bf975e0`. K7 can tighten or overturn the reading of the kernel
arms. It cannot touch hypotheses (a) or (b), which were measured on raw CFA
planes that never entered strehl's gather.
