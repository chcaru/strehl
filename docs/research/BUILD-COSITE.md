# BUILD-COSITE — the chroma co-site, measured on the path it is actually on

Agent BUILD-COSITE. Routed to land BUILD-SHARP §20.5's fold: compose the ±0.25
chroma co-site into the alignment gather for red and blue, delete the serial
`resample_shift` calls, leave green untouched. Predicted gain 1.128× / 1.438× /
2.004× amplitude in R and B at f = 0.25 / 0.35 / 0.50.

Measured HEAD `7cd405cbefd37503a0a0a385ac5cd8336b4e0b1f`; written at
`32369f9253267dac58e9d3194993decad9784082`. Instruments in
`experiments/BUILD-COSITE/`.

**The fold was not landed. Its arithmetic is right, its gain reproduces, and it
is on the wrong path.**

## 1. The headline, first

BUILD-SHARP §20.3 scopes the co-site as follows:

> co-siting runs only inside `write_binned` … So it is on the **viewable**
> render and not on the byte-frozen measurement path … our sharpness instrument
> has been measuring a path the photographer never sees.

The first clause is true. The conclusion is **exactly backwards**, and the
reversal is worth stating plainly because it inverts who is affected:

| render | flags | shape | co-sites? |
| --- | --- | ---: | --- |
| the shipped gallery | `--srgb --auto-exposure` | 7032x4688 | **NO** |
| the byte-frozen measurement file | *(no colour flag)* | 3516x2344 | **NO** |
| the linear measurement render | `--linear-srgb` | 3516x2344 | **YES** |
| binned viewing render | `--srgb --binned` | 3516x2344 | **YES** |

Both callers reach `write_binned` only *after* an `if demosaic { … return }`
branch, and `main.rs` resolves `demosaic: demosaic || (srgb && !binned)`. So
`--srgb` **demosaics** unless `--binned` is also passed. The serial resample is
charged to the file quality is judged on, and not to the file the photographer
looks at.

This is not read off the source. It is read off the shipped artefacts:

    C:\dev\strehl-out\SHIP-V1\bee-3-cpl.tiff      shape=(4688, 7032, 3)
    C:\dev\strehl-out\SHIP-V1\coffee-bean.tiff    shape=(4688, 7032, 3)

and reproduced by running the gallery command verbatim at HEAD:

    wrote : gallery-cmd-before.tif (7032 x 4688, 16-bit RGB, sRGB …,
            Malvar-He-Cutler demosaic)

`write_binned` is never entered. `resample_shift` at `image_out.rs:956-957`
never runs. The 1.438× at f = 0.35 was, for the owner's renders, a prediction
about dead code.

The mechanism BUILD-SHARP bucketed as NOT-ON-THIS-PATH — "demosaic … a quad
collapse never demosaics" — is the one that is actually on it. That bucketing is
correct for a quad collapse and the shipped render is not a quad collapse.

## 2. What *is* right, and it is nearly all of it

BUILD-SHARP's arithmetic is sound and I could not break it.

**2.1 The closed form reproduces to five decimals.** `cosite_mtf.py`
re-derives the co-site column independently from `keys_weights` transcribed out
of the Rust:

| f | my m(f)² | BUILD-SHARP | delta |
| ---: | ---: | ---: | ---: |
| 0.25 | 0.88135 | 0.88135 | −0.00000 |
| 0.35 | 0.68133 | 0.68133 | +0.00000 |
| 0.50 | 0.47266 | 0.47266 | −0.00000 |

**2.2 It reproduces on real pixels too.** Applying `image_out.rs`'s own kernel
to a real merged red plane and taking the amplitude-spectrum ratio:

    chan     f=0.25    f=0.35    f=0.50
       R     0.8815    0.6816    0.4730
       B     0.8814    0.6818    0.4728
    exact    0.8813    0.6813    0.4727

Three to four decimal places. The co-site really does cost what BUILD-SHARP
says it costs, wherever it runs.

## 3. The fold, built and measured

Built behind `STREHL_COSITE_FOLD` so **both arms come from one binary** — no
rebuild between arms, so nothing another agent commits mid-run can contaminate
the A/B. Composed as `Similarity{a: 1, b: δ}.then(t_site)`, i.e. `T'(p) =
T(p + δ)`, matching the pull convention `dst(p) = src(T(p))`; δ = +0.25 for red
and −0.25 for blue, the identical signs `develop_binned` already uses. Reverted
after measurement; the binary is kept at
`C:\dev\strehl-out\BUILD-COSITE\strehl-fold-expt.exe`.

**3.1 The green placebo passes.** Measured on the byte-frozen *camera-native*
pair, because that is the only linear render in which the three planes are still
independent — `--linear-srgb` applies the camera matrix, which mixes all three
camera planes into every output channel, and a per-plane placebo taken through
it reports green moving when green was never touched. (I ran that mistake first;
it read G = 0.960 / 0.938 / 0.959. It is an artefact of the matrix, not of the
fold.)

    R  serial c7a0354fd9516014  fold c9486f8d12bde640   MOVED
    G  serial 50aebee0c023dae6  fold 50aebee0c023dae6   IDENTICAL
    B  serial f2db9863151d61aa  fold 25217b163c94a568   MOVED
    green bit-identical over the whole plane: True

Green's amplitude ratio is 1.0000 / 1.0000 / 1.0000 at all three bands, which is
also the instrument's own null.

**3.2 The sign is right.** A sign error would leave red and blue a full binned
pixel apart on the diagonal. Phase correlation on the binned pair:

    ab-serial.tif   R-to-B separation: 0.270 px
    ab-fold.tif     R-to-B separation: 0.234 px

The folded arm is if anything *better* registered than the serial one.

**3.3 The predicted gain reproduces.** Measured in camera space, composing the
fold's own cost against the co-site's measured cost:

| f | R measured | B measured | mean | BUILD-SHARP predicted |
| ---: | ---: | ---: | ---: | ---: |
| 0.25 | 1.1294× | 1.1118× | 1.121× | 1.128× |
| 0.35 | **1.4325×** | **1.3925×** | **1.413×** | **1.438×** |
| 0.50 | 2.0806× | 1.8001× | 1.940× | 2.004× |

Within 1.8% at f = 0.35. The spread between R and B at f = 0.50 (2.08 vs 1.80)
is real and comes from the fold's own cost, where blue pays 0.851 against red's
0.984 — BUILD-SHARP's ensemble control of 0.947 is a fair average of the two but
does not resolve the per-channel difference.

**3.4 It is visible.** `crops-binned/crop-pair.png`, 1:1, tile chosen by the
data (highest high-frequency energy in R−G) and chosen from the *before* image
so the choice cannot flatter the after.

## 4. Why it was not landed

Two blockers, both measured rather than argued.

**4.1 It moves the byte-frozen measurement file.** The gather feeds *every*
output path, not just the co-sited one. `cam-serial.tif` and `cam-fold.tif` are
byte-frozen-path renders and their R and B planes have different SHA-256 (§3.1).
`crates/strehl-cli/tests/byte-freezes.tsv` carries
`coffee-bean-20-gate2-sidecar`, a **registered** row on exactly that path, so
its hash moves. That is a re-baseline of the corpus, not a free win.

**4.2 It damages the shipped render.** Folding puts red and blue on green's
lattice *before* the mosaic is re-interleaved, and Malvar-He-Cutler then treats
those samples as though they still sat at their CFA corners. Measured on the
demosaiced pair, central 2048², linear light:

| statistic | serial | folded | ratio |
| --- | ---: | ---: | ---: |
| sd(R−G) | 1512.5 | 1867.4 | **1.235** |
| sd(B−G) | 1516.0 | 1864.8 | **1.230** |
| HF(R−G), \|f\| > 0.2 | 212658 | 279107 | **1.313** |
| HF(B−G), \|f\| > 0.2 | 206738 | 272225 | **1.317** |

+23% chroma error, +31% of it at high frequency. That is the colour fringe on
every luminance edge that co-siting exists to remove, re-introduced on the one
render the owner actually looks at.

Note what this is *not*: it is not a rigid displacement. `chroma_shift.py`
measures the output red plane moving by 0.02 px, not the 0.5 px the sample
sites moved. The estimator is potent at that magnitude — a planted 0.5 px shift
is recovered at 0.531 / 0.514, ratio 1.06, and a planted 1.0 px at exactly
1.000 — so the null is a real property of Malvar, which rebuilds red at three of
every four sites out of the green gradient. Mis-siting the sparse red samples
injects error into the plane instead of translating it.

BUILD-SHARP's "composing is exact … the sample count, the kernel and the cost
are unchanged — only the coordinate differs" is true of the gather in isolation.
It is not true of the gather's *consumers*, of which there are three and only
one wants the co-site.

## 5. What I changed

One thing, in my own lane: the module header of
`crates/strehl-cli/src/image_out.rs` asserted that `write_binned` "is the 'for
looking at' render". That sentence is what BUILD-SHARP read, and it is false. It
now states the reachability rule, both invocations that reach it, and the
measured cost. Documentation-only — the byte-freeze test passes unchanged,
which is the proof that no byte moved.

## 6. What this reroutes

1. **The softness effort should move to the demosaic.** On the shipped path the
   chain is: alignment gather at near-uniform phase → lateral-CA (composed, free)
   → Malvar-He-Cutler. Red and blue are softer than green there, and the cause is
   Malvar, which infers R at three of every four sites. BUILD-SHARP's §20 table
   does not price it. It is the largest unpriced term on the viewable render.
2. **The merge already has what a demosaic has to guess.** Every CFA site of
   every quad is estimated independently; the demosaic branch throws that
   structure away by re-interleaving into a Bayer mosaic and reconstructing it.
   Whether a direct 2× upsample of four known planes beats Malvar on four known
   planes is an open question and a promising one.
3. **The sharpness instrument's target is wrong in the other direction.** ESF on
   `--linear-srgb` measures a render carrying an extra Keys-0.25 resample in R
   and B that the shipped render does not have. Sharpness numbers taken there
   understate red and blue by the §2.2 factors.
4. **A test should pin the flag resolution.** `demosaic || (srgb && !binned)`
   lives in `main.rs`, which another agent holds open; nothing asserts which
   writer `--srgb` reaches. A comment can drift again — this one did.

## 7. What I did not establish

- I measured one subject, `coffee-bean` (105 placed frames, sidecar alignment,
  CA correcting). The amplitude ratios are properties of the kernel and should
  not be scene-dependent, and the closed-form agreement in §2.2 supports that,
  but I have not shown it on a second subject.
- The +23% chroma-error figure in §4.2 is measured through the colour matrix
  (`--linear-srgb --demosaic`, which is what `finalpass.ps1` renders). The
  matrix mixes channels, so the true camera-space chroma damage is not exactly
  this number. The sign and the order of magnitude are not in doubt; the third
  digit is.
- I did not price Malvar's R/B cost, which §6 argues is now the leading term.
  That is the next measurement and it is not mine.
- The fold binary is kept but the fold is **not** in the tree. Anyone re-running
  §3 must rebuild it; there is no `STREHL_COSITE_FOLD` at HEAD, and it was
  deliberately never added to `RENDER_ENV` because it was never meant to ship.
