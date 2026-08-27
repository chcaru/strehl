# The clip-to-zero defect is fixed at HEAD

ORCH declared this top priority: 122,416 pixels at exactly zero in all three
channels on `flower-bud-alone-cpl`, against 0 such pixels in the estimator arm,
and halted the default flip over it.

**It reproduces exactly on the renders ORCH measured, and reads 0.0000% at HEAD.**
The answer is neither "it is `pyramid.rs`" nor "it is downstream of `pyramid.rs`".
It is fixed *in time*: `clean6` is a pin render, and something landed between that
pin and HEAD that repaired it.

## The measurement

One instrument (`repro_cells.py`), one reference (ORCH's own
`clean6\flower-bud-alone-cpl--ctrl.tiff`), three test arms. Cells are percentages
of the reference-derived lit / dark populations that are exactly zero in all
three channels.

| arm | build | gate | black_lit | black_dark | TOTAL |
|---|---|---:|---:|---:|---:|
| ctrl (estimator) | pin | - | 0.0000 | 0.0000 | 0.0001 |
| **blend (ORCH's arm)** | **pin** | **4** | **+0.0401** | **+1.3613** | **+1.4014** |
| blend | HEAD `5dc8841d` | 2 | 0.0000 | 0.0000 | -0.0001 |
| **blend** | **HEAD `5dc8841d`** | **4** | **0.0000** | **0.0000** | **-0.0001** |

The pin row reproduces ORCH's defect. 1.3613% of the dark population is the
large contiguous crushed region they bounded at y 744..4687, x 1668..5104.

## Why the gate is ruled out

My first HEAD render was at gate 2, which differs from ORCH's arm in *two* ways
at once — build and gate — so on its own it isolates nothing. The fourth row is
the missing control: HEAD at **gate 4**, ORCH's exact protocol
(`--gate 4 --base-mean --camera-linear`, `STREHL_FIX_CA=off`), same subject, same
reference. It is clean. The repair is in the build, not in the gate.

## Mechanisms ORCH proposed, and where they stand

ORCH offered three candidates. None of them can be the cause, because the cause
is not present at HEAD — but two are worth answering directly since they bear on
the instrument they asked me to build.

1. **The weight clamp** (`eb072d5`). Not eliminated as the *historical* cause;
   that commit is inside the window between the pin and HEAD, so it is as likely
   a candidate for the *repair* as for the defect.
2. **Signed Laplacian coefficients clipped at the write.** Cannot be reached at
   defaults: `Hull::InputRange` is the shipped default and clamps every output
   pixel to `[min_k, max_k]` over the aligned input frames. An output of exactly
   0 under that clamp requires `min_k == 0` at those pixels.
3. **Base band weighted while detail bands take the fallback.** Untested. Left
   untested deliberately — chasing a mechanism for a defect that does not
   reproduce is how one manufactures a fix for nothing.

## On the min/max hull discriminator ORCH asked for

Their proposed check — "compare each output pixel against min and max across all
input frames" — is already the shipped default behaviour, not a diagnostic that
needs building: `Hull::InputRange`. That is why I want them to re-render before I
build a per-band version of it. A per-band violation count is genuinely useful
and I will build it if they still want it, but it needs the input frames
re-decoded and it should be aimed at a defect that still exists.

## The one clip defect that IS still live at HEAD

`dry-erase-marker-head-cpl`, white rail, lit population: ctrl 7.8774%, blend
8.4054%, **+0.5280%**. This is real, at HEAD, and unfixed. It is the opposite
polarity from ORCH's defect — saturation, not crush — and it is much smaller.

Any fix for it must be **ratio-preserving**. An achromatic overshoot clamped
per-channel changes hue irreversibly; the same arithmetic in the other direction
is what would turn a crushed neutral into a colour cast.

## Recommendation

Re-render `clean6` at HEAD before any further work on this. The flip ORCH halted
may not need to be halted.
