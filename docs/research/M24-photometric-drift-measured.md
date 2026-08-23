# M24 — Does this corpus have per-frame photometric drift?

> **NOT INDEPENDENTLY VERIFIED.** Same author as the measurements. Rule 12.
> This is a **probe**, not a full milestone: three scripts, no plants, no sweep.
> It was run to decide whether review item R9 is speculative or load-bearing.

Review item **R9** asserts the merge's forward model needs a per-frame gain and
offset, "or the Wiener gate misreads exposure drift as signal". The project had
no measurement either way. This probe asks the prior question: **is there any
drift to model?**

## 1. MEASURED — yes, and it is not small

Mean level of the CFA green plane per frame, normalised to the stack mean:

| stack | n | ISO | exposure | peak-to-peak | linear trend | frame-to-frame jitter |
|---|---:|---:|---:|---:|---:|---:|
| `109MSDCF` | 22 | 160 | 13/10 | 0.91% | +0.19% | 0.332% |
| `119MSDCF` | 33 | 50 | 1/8 | 2.88% | +1.82% | 0.345% |
| `coffee-bean` | 35 of 105 | 50 | 4/5 | **11.70%** | −4.51% | 1.941% |
| `112MSDCF` | 40 of 79 | 500 | 1/60 | 6.84% | −0.45% | 1.025% |
| `coffee-bubbles` | 19 | 1000 | 5/2 | 8.93% | +2.21% | 1.723% |

`109MSDCF` — the stack most of this project's measurements were made on — is
the *quietest* in the corpus at 0.91%. That is worth noting explicitly: the
stack that shaped the project's intuitions is not representative here.

## 2. The confound, and how it was addressed

Focus breathing changes magnification, so the frame samples different scene
content, which moves the mean **without any exposure change**. Binning "drift"
without addressing this is exactly the failure rule 17 names.

Two tests:

**A. Does EXIF actually vary?** MEASURED:

| stack | distinct (exposure, ISO, FNumber) across the stack |
|---|---|
| `coffee-bean` | **2** — `(4/5, 50, f/8)` and `(5/8, 50, f/8)` |
| `coffee-bubbles` | 1 |
| `112MSDCF` | 1 |

**`coffee-bean` changes exposure mid-capture.** That is incontrovertible and
settles the question of whether photometric state can vary within one of this
owner's real stacks: it can, and it did.

**B. Does a small central ROI track the full frame?** A true global gain moves
both together; a framing change moves the full frame more.

| stack | full-frame p-p | central 600 px p-p | ratio | correlation |
|---|---:|---:|---:|---:|
| `coffee-bean` | 11.70% | 17.58% | 1.50 | +0.911 |
| `coffee-bubbles` | 8.93% | 18.32% | 2.05 | +0.971 |
| `112MSDCF` | 6.84% | 6.27% | 0.92 | +0.848 |

The centre moves *at least* as much as the full frame in every case, correlating
+0.85 to +0.97. So the variation is not a framing artifact — the framing
hypothesis predicts the opposite ordering.

**Honest limit:** the central ROI is not a clean probe either. A centred subject
blurring in and out moves light across the ROI boundary, so this test bounds the
framing explanation rather than eliminating it.

## 3. MEASURED — and the simple explanation FAILS, which is the useful part

If the drift were just the EXIF exposure change, the level ratio between
`coffee-bean`'s two exposure groups should equal the exposure ratio:

| quantity | value |
|---|---:|
| EXIF exposure ratio `4/5` ÷ `5/8` | **1.2800** (0.356 EV) |
| measured level ratio between the groups | **1.0443** |

**The level moved 4.4% for a 28% exposure change.** The simple model is refuted.

ARGUED, the most likely reading: the body was compensating. A shortened exposure
alongside a nearly unchanged level is the signature of **auto-exposure tracking a
real change in scene illumination** — the camera removed most of an illumination
drift, leaving a residual. The alternative (that scene content differs between
the two groups because they are different focus ranges) is a genuine confound
and is not separable here.

Either reading gives the same design consequence, which is why this probe is
worth recording despite not resolving between them.

## 4. The design consequence — sharper than R9 as stated

**R9 is justified, and the reason is stronger than the review's.** The review
argued drift exists and must be modelled. The measurement says something more
specific:

1. **Photometric state varies frame to frame across most of this corpus** —
   2.9% to 11.7% peak-to-peak on four of five stacks.
2. **EXIF does not predict it.** Two stacks vary 6.8–8.9% with *identical* EXIF,
   and on the one stack where EXIF does change, the level moves by **16% of what
   EXIF predicts**.
3. Therefore **the per-frame gain must be FITTED from the data, not read from
   metadata.** A forward model that trusts `ExposureTime` × `ISO` would be wrong
   in both directions: blind to variation on three stacks, and overcorrecting by
   ~6× on `coffee-bean`.
4. DERIVED: `112MSDCF` at **1/60 s** is precisely the shutter speed at which
   mains-frequency flicker in continuous lighting beats against the exposure.
   That is a checkable mechanism for its 6.84% with constant EXIF, and it is
   untested.

## 5. What was NOT measured

- **No gain/offset was fitted.** Only the mean level was tracked. Whether a
  single global gain per frame suffices, or an offset term is also needed, is
  unmeasured — as is whether the variation is spatially uniform.
- **No effect on merge output was measured.** The claim that the gate "misreads
  drift as signal" remains ARGUED. This probe establishes the input exists.
- Stacks were subsampled (every 2nd or 3rd frame) to keep decode cost down, so
  the jitter figures are lower bounds on the true frame-to-frame variation.
- `coffee-bubbles`'s scene genuinely evolves (bubbles move), so its number
  carries a content component that cannot be separated here.
- `foam` was excluded; `113MSDCF` was not run.

## 6. Questions for the owner

- Was `coffee-bean` shot in an auto-exposure mode? The EXIF change from 4/5 s to
  5/8 s mid-stack, with the level nearly unchanged, is consistent with the camera
  compensating a light that was drifting. Knowing the mode would resolve §3
  immediately, and it changes whether in-camera bracketing can be trusted to hold
  exposure fixed.
- Was continuous (mains-powered) lighting used, or flash? `112MSDCF` at 1/60 s
  is the classic flicker-beat case.

## 7. Reproducing

```
experiments/m24-photometric-drift/src/
  01-levels.py            per-frame level, trend and jitter across five stacks
  02-exif-vs-framing.py    test A (EXIF variation) and test B (centre vs full frame)
  03-exposure-ratio.py     the check that refuted the simple exposure explanation
```
