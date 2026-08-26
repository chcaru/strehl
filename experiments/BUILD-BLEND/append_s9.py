"""Append section 9 (the tone/far-field answer) to docs/research/BUILD-BLEND.md."""
import io

DOC = "docs/research/BUILD-BLEND.md"
MARK = "Is far-field normalisation actually safe"

NOTE = """
### 9. Provenance of the `ca-*` pair, and: is far-field normalisation actually safe?

ORCH found the per-image normalisation independently, in the tone stage, and
concluded that measurements normalised to an in-image reference are safe because
*"a per-image scale factor cancels in a ratio taken within that same image"*.

**Provenance, asked and answered.** All six `ca-*` files are `--srgb` and
**TONED**, read from their own `ImageDescription`:

| pair | ctrl black / white | blend black / white |
|---|---|---|
| fern | 0.011119 / 0.306019 | **0.000000** / 0.319798 |
| lavendar | 0.015192 / 0.368004 | 0.017343 / 0.366872 |
| couch | 0.013474 / 0.282117 | 0.015274 / 0.280613 |

These arms are **not gain-related**, which is checkable without touching a
pixel: under a common gain `g`, black and white must both scale by `g`. White
ratios are 1.0450 / 0.9969 / 0.9947 while black ratios are 0.0000 / 1.1416 /
1.1336. ORCH's cancellation argument holds for a gain and these are not gains.

**The premise is true; the conclusion does not follow.** The tone stage is not a
scale. It is `y = (l - black)/(white - black)` -- affine, with an **offset** --
followed by a soft toe, `srgb()`, and `s_curve()`: two nonlinearities. A gain
cancels because it scales `l`, `black` and `white` together, which is exactly why
ORCH's `--auto-exposure` test returned 1.0000. An offset does not cancel in a
ratio, and a nonlinearity does not preserve one.

`experiments/BUILD-BLEND/farfieldsafe.py` tests this by pushing **one** physical
scene through each arm's real tone parameters, so the physical difference is
zero by construction and every DN of output is artifact -- measured *after* the
far-field normalisation. Two controls, both passing, because a number with no
control is not a measurement:

- **positive** (validates the model): a 6.148x gain with both tone points scaled
  cancels to **0.000000 of 255**, reproducing ORCH's own measurement.
- **null** (validates the attribution): identical tone parameters give exactly
  **0.000000**, so the differences below come from the parameters, not the code.

**The answer is row-dependent, and it is not uniformly bad news:**

| d | ORCH's blend-control | manufacturable by tone alone | share |
|---:|---:|---:|---:|
| 2 | +1.39 | **+2.01** | **144%** |
| 90 | +3.60 | +0.27 | **7%** |
| 175 | -0.25 | +0.17 | -68% |
| 350 | -2.19 | +0.07 | -3% |
| 550 | -2.36 | +0.05 | -2% |

- **d=2 is not physics.** The artifact is *larger* than the measured value and
  has the same sign. ORCH's reading that the blend is better at the silhouette
  is not supported by that row. This also explains why their instrument and mine
  disagree about the sign of criterion (c).
- **d=90, the mid-field win, is 93% real.** Independently corroborated: my
  untoned re-render measures +876 DN there.
- **The bowl is not manufactured by the arm-to-arm difference.** At d>=350 the
  artifact is ~0.05 of 255 and points the *other way*.

**But there is a second effect, and it is the larger one.** It applies to both
arms equally, so it is invisible to any blend-minus-control column and survives
far-field normalisation untouched, because it is nonlinear rather than
multiplicative. Expressing the control's own profile both ways:

| d | linear DN | as linear /255 | as toned /255 | inflation |
|---:|---:|---:|---:|---:|
| 90 | -1094 | -2.00 | -6.97 | 3.48x |
| 350 | -319 | -0.58 | -1.94 | 3.32x |
| 550 | -222 | -0.41 | -1.34 | 3.30x |

Median **3.33x** over d>=175. So the bowl is real in sign and in existence, and
roughly three times smaller in physical terms than the printed `of 255` numbers
imply. De-inflating ORCH's own -2.36 gives about -0.71 of 255 -- **still inside
their own 1.00 bar**, which is an independent route to the same conclusion
section 6 reached from my untoned renders (+0.35 of 255).

**Revised rule, narrower than ORCH's.** Normalising to an in-image reference
removes a per-image *gain*. It does not remove a per-image *offset*, and it does
not undo a nonlinearity. On a toned render it is safe only where the tone curve
is locally linear -- which the bright far field roughly is, and the deep
silhouette emphatically is not, at 4.28x inflation and a sign-flipping artifact.
Measuring on untoned linear output remains the only thing that needs no caveat.
"""

src = io.open(DOC, encoding="utf-8").read()
if MARK in src:
    raise SystemExit("section already present -- refusing to duplicate")
io.open(DOC, "w", encoding="utf-8", newline="").write(src.rstrip("\n") + "\n" + NOTE)
print("appended section 9;", len(io.open(DOC, encoding="utf-8").read().splitlines()), "lines")
