# M95 arm 7 — colour-difference chroma in the shipped demosaic

**Status:** pre-registration. Written to disk **before any candidate was scored.**
Nothing below was edited after a result was seen; the arm-6 failure F6 was exactly
the opposite of that and it is on the record.

## Why this arm exists

Arm 6 (`docs/research/M95-demosaic.md`, commit `7086ba2`) measured that the
shipped Malvar-He-Cutler demosaic carries **0.1586 dex less true detail** than a
perfect demosaic would, and that the loss is **chromatic**:

| channel | signal (dex) | artifact share |
| --- | --- | --- |
| R | -0.4881 | 0.6430 |
| G | -0.2127 | 0.3127 |
| B | -0.3874 | 0.5586 |

R and B carry roughly twice G's artifact share, which tracks their quarter-density
CFA sampling against G's half-density.

Arm 4 (`experiments/M95-resample/out/x6_summary.txt`) separately measured that the
whole demosaic-algorithm difference between strehl and rawpy-AHD is only -0.0332
dex. So the headroom arm 6 found is **not** headroom against AHD; it is headroom
against perfection, and most of it is available to *any* algorithm including AHD.

## The hypothesis

MHC estimates R at a blue site with the `F_X` stencil: diagonal bilinear on the
R samples, plus `gamma = 3/4` times a Laplacian of **the known channel at that
site**, which is B. Likewise `F_H`/`F_V` correct R at a green site using G. This
is Malvar's cheap first-order approximation to constant-hue interpolation, with a
fixed Wiener-fitted gain and a 5-tap Laplacian.

The classical alternative interpolates the **colour difference** directly:

1. reconstruct the G plane everywhere (MHC's `F_G` at R/B sites, known at G sites);
2. form `dR = R - G` at R sites and `dB = B - G` at B sites;
3. interpolate `dR` and `dB` across the full grid;
4. emit `R = G + dR`, `B = G + dB`.

**Why it should win, stated as a mechanism rather than a preference:** the
reference channel becomes G, which is sampled at **twice** the density of R or B
and is therefore reconstructed far better, and the correction gain becomes exactly
1 against a real full-resolution plane instead of 3/4 against a 5-tap Laplacian of
a quarter-density channel.

**Why it is admissible in this codebase:** it is still **linear and shift-invariant
within a CFA phase**. `G` is a fixed linear functional of the mosaic; `dR` masked to
R sites is linear; the interpolation is a convolution; the sum is linear. So it
preserves every property `demosaic.rs`'s module docstring argues for -- computable
noise propagation (property 1) and inability to manufacture detail (property 2).
That is the reason to prefer it over a directional or iterative demosaic, which
would break both.

## Candidates

| arm | what it is | shippable |
| --- | --- | --- |
| `MHC` | the shipped algorithm, unchanged | baseline |
| `CDIFF` | steps 1-4 above, bilinear on the difference lattices | **candidate** |
| `BILINEAR` | arm-6 anchor, retained | no |
| `NEAREST` | arm-6 anchor, retained | no |

## Bars, registered before the run

Scored with the arm-6 instrument: 400 tiles of 64x64 ranked on the **truth's** own
band energy, band 0.30-0.48 cyc/px, luma unless a channel is named. `signal` is
the component of emitted band power correlated with the truth through a
per-frequency-bin `alpha`; `artifact_share` is the remainder over the total.

- **B7 -- SHIP.** `CDIFF` ships if its luma **signal exceeds MHC's by at least
  0.03 dex** *and* its **artifact share is not more than 0.02 above** MHC's.
  The second clause is not decoration: arm 6's whole result is that an arm can be
  louder and worse, so a gain in signal that arrives with a bigger artifact share
  is not a gain.
- **B8 -- DEAD.** If `CDIFF`'s luma signal gain is **below 0.01 dex**, the
  colour-difference hypothesis is dead for this codebase and I report that and
  ship nothing.
- **B9 -- NO CHANNEL REGRESSION.** `CDIFF` must not lose signal against MHC in
  **any** of R, G, B by more than 0.005 dex. A luma win bought by wrecking one
  channel is not a win.
- **Between 0.01 and 0.03 dex:** real but below the ship bar. I report the number
  and do not ship. I am registering this band explicitly so that a marginal result
  cannot be talked upward after the fact.

## What would falsify the fix after it is built

- **F-a.** The Rust implementation must agree with the scored Python to
  below 1e-6 on the arm-6 K6 certification cases. If it does not, the number I
  measured is not the number that ships and I withdraw it.
- **F-b.** The binned default must be **byte-identical** before and after. The
  demosaic is reached only from `image_out.rs::write_demosaiced`, and `main.rs:178`
  states the election statistic is always computed on the binned grid, so the
  prediction is exact identity, not similarity. Any difference at all falsifies my
  claim that this change cannot disturb the byte-frozen path.
- **F-c.** The elected frame per pixel must not change. Arm 1's 100.0000%
  byte-exact election result is a regression test.

## Controls

Reused from arm 6, already validated there: **K1** null (`D = T`), **K2**
determinism, **K3** positive blur dose, **K4** positive uncorrelated-power dose,
**K5** specificity across three truths, **K7** band below truth Nyquist.

New to this arm, and the first two exist specifically because `CDIFF` is a new
algorithm rather than a re-measurement:

- **K8 -- CONSTANT.** A constant mosaic must demosaic to that exact constant in all
  three channels, for every arm. This is the closed-form answer the `demosaic.rs`
  docstring names, and it catches a mis-normalised interpolation kernel, which is
  the most likely way to get `CDIFF` wrong.
- **K9 -- LINEARITY.** `f(a*M1 + b*M2)` must equal `a*f(M1) + b*f(M2)` to float
  tolerance. This is load-bearing: the entire licence-and-noise argument for
  keeping a linear demosaic depends on it, and it is the control that would catch
  me having silently introduced an adaptive step. It must **pass for MHC and
  CDIFF** and I predict it **fails for NEAREST** -- if it passes for everything it
  is not discriminating and I will say so.
- **K10 -- CFA-PHASE SHIFT INVARIANCE.** Shifting the mosaic by (2, 2) must shift
  the output by (2, 2) in the interior. Catches a parity error, which is the other
  most likely way to get `CDIFF` wrong.

**A control that only ever passes is not evidence.** K9 carries a predicted
failure; K8 and K10 are checked against deliberately broken variants of `CDIFF`
(mis-normalised kernel, and parity-swapped masks) which must make them fail.

## Scope limits, stated in advance

- The truth `T` is a 2x box-downsampled AHD decode, not a CFA-free capture, so it
  carries some of AHD's own signature. Arm 6's K5 bounds this -- the ranking held
  under AHD, VNG and LINEAR truths and MHC's signal moved at most 0.0198 dex --
  but does not remove it. The capture that would remove it is still requested and
  unfiled.
- This arm measures the demosaic **only**. Arm 4 measured the interpolation kernel
  in the warp gather at -0.2360 dex, which is larger; that lives in
  `crates/strehl-core/src/align.rs`, which I do not own, and is delivered as a
  patch rather than landed.

---

# ADDENDUM 1 -- written after the CDIFF run, before the CDIFF2 run

**Everything above stands unedited.** `CDIFF` has been scored and its result is
known: luma signal gain **+0.0124 dex**, artifact share **-0.0096**, per channel
**R +0.0435 / G +0.0000 / B +0.0586**. That is the registered *middle band* --
real, but below B7's 0.03 ship bar. **B7 did not fire and I am not moving it.**

Two things must be recorded before anything else is run.

## A1.1 All three registered controls were non-discriminating

I registered predictions that K8 would reject the mis-normalised variant, K10
would reject the parity-swapped variant, and K9 would reject `NEAREST`. **All
three predictions were wrong**, and every arm passed every control:

- **K8 (constant) cannot see the chroma kernel at all.** On a constant mosaic the
  colour difference is identically zero, so scaling the lattice kernel by 1.2
  scales zero and the output is exact regardless. The control tests the green
  path and nothing else.
- **K10 (shift by 2,2) cannot see a Bayer-phase error**, because a parity swap is
  itself invariant to a two-pixel shift. This was foreseeable and I did not
  foresee it.
- **K9 (linearity) does not reject `NEAREST`**, because replication *is* a linear
  operator. My prediction confused "crude" with "non-linear".

**The ladder caught the parity break even though the controls did not:**
`CDIFF_BADPARITY` scores artifact share **0.7470** against `CDIFF`'s 0.3038. The
ladder did **not** catch the normalisation break (`CDIFF_BADNORM` share 0.3071),
because `decompose`'s per-bin `alpha` absorbs a linear gain by construction --
a real and previously unrecorded blind spot in the arm-6 instrument.

## A1.2 K11, added now, and why that is legitimate

**K11 -- KNOWN-SAMPLE PRESERVATION.** At an R site the emitted R must equal the
input mosaic sample exactly; likewise B at B sites and G at G sites. `CDIFF`
guarantees this by construction, since `R = G + (M - G) = M` there.

Measured before this addendum was written, so the numbers are stated rather than
predicted: CDIFF **5.960e-08**, `CDIFF_BADNORM` **1.603e-01**,
`CDIFF_BADPARITY` **6.549e-01**. It rejects both broken variants.

This control is **post-hoc** and I am labelling it as such rather than folding it
into the list above as though it had been there all along. It does not rescue any
result -- `CDIFF`'s verdict was already fixed by B7 before K11 existed.

## A1.3 CDIFF2 -- a new hypothesis, registered before it is scored

`CDIFF` leaves the green plane **exactly** as MHC computes it, which is why its
per-channel green gain is +0.0000 to four decimals. Luma is 71.5% green, so a
chroma-only fix is structurally capped at a small luma number no matter how well
it works. That is a limitation of what `CDIFF` changes, not evidence that green
has no headroom: arm 6 measured green's artifact share at **0.3127**.

**CDIFF2** adds one linear refinement pass over the green plane:

1. run `CDIFF` to get a green plane `g` and full chroma planes `R1`, `B1`;
2. at **G sites**, green is exact and red is interpolated, so form `R1 - M` there;
3. interpolate that difference from the green quincunx onto the R sites;
4. set green at an R site to `M_R - (that difference)`, using the **exact** red
   sample rather than an interpolated one; symmetrically for B sites;
5. redo the chroma of step 1 against the refined green.

Every step is a convolution or a masked subtraction, so **CDIFF2 is still linear
and shift-invariant within a CFA phase** and keeps the same licence and
noise-propagation argument. It is one Jacobi iteration, not an adaptive rule.

**Bars for CDIFF2, registered now, unrun:**

- **B10 -- SHIP.** CDIFF2 ships if luma signal gain over MHC is **at least 0.03
  dex** and artifact share is **no more than 0.02 above** MHC's. Identical to B7;
  I am deliberately not lowering the bar to fit a result I already have.
- **B11 -- NO CHANNEL REGRESSION.** No channel may lose more than 0.005 dex of
  signal against MHC.
- **B12 -- GREEN MUST MOVE.** CDIFF2's green signal gain must be **> 0.005 dex**.
  If green does not move, the refinement did not do the thing it was built to do,
  and any luma gain came from somewhere I have not identified -- in which case I
  report it and ship nothing.
- **K11 applies to CDIFF2 as a hard gate.** Step 4 overwrites green at R and B
  sites, which is precisely where a normalisation or parity error would hide, and
  K11 is now the only control that can see one.

**Falsifier:** if CDIFF2 clears B10 but fails K11, the gain is an artifact of
breaking known-sample preservation and I withdraw it.

If neither `CDIFF` nor `CDIFF2` clears 0.03 dex, **I ship nothing from this arm**
and report that the demosaic is not where the owner's softness lives.
