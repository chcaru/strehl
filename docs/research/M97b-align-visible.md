# M97b — building the instrument that can see the alignment

**Status: DONE.** The question is answered, the answer is not the one either
M86 or I expected, and it is reproducible.

> **Headline (MEASURED).** Alignment *does* improve the photograph — by
> **19–32%** in matched-content sharpness. But **only when the solve's gain is
> corrected.** The alignment as shipped measures **1.033 / 0.979 / 1.000**, a
> null, because it applies only **23.9%** of the drift that is present. Every
> previous null in this project is a measurement of an under-correction, not a
> measurement of alignment.

---

## 1. Why the old instruments could not see it, and it is not what we thought

M86 measured whole-frame Tenengrad at **0.9859x** against a matched zoom-only
null and declined to claim a win. M85 independently measured **0.985x**. The
standing ARGUED explanation was that misregistration *displaces* detail rather
than blurring it, so gradient energy is structurally blind.

**That explanation is incomplete, and the missing piece invalidates most
image-space comparisons anyone would naturally write.** MEASURED:

**Registration changes the rendered field of view.** An aligned render sits in
the reference frame's field of view. An unregistered render blends the fields
of view of frames spanning 23.9% of magnification. So **comparing two arms at
the same pixel coordinate compares different scene content.**

I proved this on myself. My first radial metric (`src/radial4.py`) reported the
gain-corrected render at **24.5x** the null in the outermost radius band. A 24x
sharpness gain is not physical. I built a contact sheet and looked
(`src/sheet.py`, `C:\dev\strehl-out\M97b\SHEET.png`): at that radius the
corrected render holds marker bristles and the null holds smooth white barrel.
**The 24.5x is a content shift wearing a sharpness ratio's clothes** — the same
class of error as M86's fake 1.4565x boundary reading. `radial4.py`'s treatment
numbers are **inadmissible and I do not report them.**

**DERIVED: any fixed-coordinate image comparison between registration arms is
invalid, because the field of view is exactly what registration changes.** This
is a stronger constraint than "gradient energy is blind" and it is the reason
this question has resisted three milestones.

---

## 2. The instrument

`src/matched.py`. Recover the similarity between two renders with the same
FFT/NCC scale ladder used for ground truth, then bring **both** arms onto a
common intermediate grid — A magnified by `sqrt(s)`, B by `1/sqrt(s)` — so each
pays exactly one resampling of equal magnitude. Comparing a resampled arm
against an untouched one hands the untouched one a free sharpness win; the
symmetric split is what makes the ratio mean anything. Sharpness is gradient
energy over the common valid region, eroded 49 px, radially resolved.

**Controls, run before the treatment:**

| control | centre | mid | outer | verdict |
|---|---:|---:|---:|---|
| placebo: ZOOMNULL vs itself | 1.0004 | 0.9999 | 0.9996 | the symmetric resampling is fair |
| plant: vs itself blurred σ=1.0 | **2.8993** | **1.8618** | 1.0177 | the functional can see softness |

The outer-band plant response (1.0177) is weak, so outer-band numbers are the
least sensitive and I weight them least.

---

## 3. The subject, and why the project was testing on the worst possible one

`src/scout.py` scored eight stacks on the two properties this test needs:
drift magnitude, and whether the subject has detail at large radius (where a
scale error is largest — it is exactly zero at the optical centre).

| stack | drift (magnification) | edge/centre detail |
|---|---:|---:|
| **dry-erase-marker-head-cpl** | **1.2389** | **72.2** |
| bee-3-cpl | 1.1802 | 1.95 |
| couch-fibers-cpl | 1.2034 | 1.40 |
| flat-on-ruler-cpl | 1.0506 | 1.60 |
| lavendar-cpl | 1.2188 | 0.011 |

**MEASURED: `bee-3-cpl` is a poor test bed** — the bee is central, so the region
where alignment can help contains almost no subject. `dry-erase-marker-head-cpl`
has the corpus's largest drift and detail concentrated exactly where the error
lives.

**The scout lied to me once first.** Its initial ladder let the refinement
bracket walk outside its own bounds and returned `scale=1.1722` for **four
unrelated subjects** — identical values across different scenes, which is a
search hitting a stop, not a measurement. Bounds are now hard and rails are
reported. Its `edge/centre` was also wrong (bee-3 scored 1.621 where the
rendered frame measures ~0.005) because gradient of a *raw* frame is dominated
by shot noise, which is spatially uniform and therefore reports empty
background as detailed. Low-passed first, both are fixed.

---

## 4. Ground truth on the marker head

`signtest.py` (M97's validated instrument; plants recover 0.940→0.93841 and
0.860→0.85939). All MEASURED:

| quantity | value |
|---|---:|
| true drift, frame 0 → 298 | **422.3 plane px** (scale span 0.79999) |
| sidecar's scale span | 0.95214 — **applies 23.9%** |
| residual after the shipped sidecar | **281.8 plane px**, 33.3% removed |
| residual after gain 4.5498 | **44.2 plane px**, 89.5% removed |
| inverted-sign control | 579.0 px, 1.37x raw — **sign correct as shipped** |

**P1 (MEASURED). The solve's under-correction reproduces on a second,
independent stack, and it scales with the drift.** bee-3: 54.3% of the span
applied, 150 px residual. Marker head: **23.9% applied, 282 px residual** —
70x M86's own `T_usable` of 4.0 px. It is not a fixed offset; it degrades as
drift grows.

Rewriter control: gain 1.0 reproduces the as-shipped residual **0.86650
exactly**; gain 4.5498 reaches **100.0%** of the span.

---

## 5. The answer

Arms on `dry-erase-marker-head-cpl`, `--gate 2`, default binned linear output
(M85 forbids measuring `--srgb`/`--demosaic`). ZOOMNULL is the denominator: same
resampler, same field of view, relative registration discarded.

| A vs ZOOMNULL | drift removed | centre | mid | outer |
|---|---:|---:|---:|---:|
| **GAINED** | **89.5%** | **1.1866** | **1.3161** | **1.1492** |
| **ALIGNED (as shipped)** | 33.3% | 1.0330 | 0.9789 | 1.0003 |
| UNALIGNED | 0% | 1.0742 | 1.0403 | 1.0025 |

**P2 (MEASURED). The alignment as shipped is a null.** 1.033 / 0.979 / 1.000.
This independently reproduces M86's 0.9859x and M85's 0.985x — different stack,
different instrument, same answer.

**P3 (MEASURED). The gain-corrected alignment is a 19–32% sharpness win.**

**P4 (DERIVED). The nulls were never a property of alignment. They are a
property of a solve that applies a quarter of the drift.** Correct the gain and
the same instrument that reads null reads a large win.

**P5 (MEASURED). UNALIGNED reads 1.074 against the zoom null, which prices the
resampling cost at ~7%.** GAINED pays that same cost and still wins by 19–32%,
so the win is net of resampling.

### The confound, and which way it runs

**P6 (MEASURED). Gradient energy is fooled by seams, and the plant proves it.**
GAINED vs JITTER reads **0.674 / 0.665 / 0.851** — the deliberately jittered
render measures *sharper*. This corroborates M86's ARGUED seam explanation and
my own M97 §6 finding that misregistration raises a band-limited detail metric
by 5.6%.

**It does not undermine the result, because it runs against it.** Better
registration produces *fewer* seams and therefore *less* seam energy. GAINED is
the best-registered arm and still measures the *most* energy, so the surplus
cannot be seams. **The 19–32% is a lower bound.**

---

## 6. An instrument that failed its plant, and is therefore withdrawn

Mean `n_eff` looked like the answer. It is printed by the binary already, it is
distributional rather than positional so it is immune to the field-of-view
problem in §1, and it moves beautifully:

| arm | drift removed | mean n_eff |
|---|---:|---:|
| ZOOMNULL | 0% | 38.254 |
| UNALIGNED | 0% | 35.985 |
| ALIGNED | 33.3% | 28.204 |
| GAINED | 89.5% | **13.117** |
| **JITTER (plant)** | 89.5% + 8.855 px | **11.216** |

Monotone across a 65.7% range, and opposite in sign to the resampling confound
(resampling alone *raises* it, 35.985 → 38.254). It looked like the instrument
the project already owned and had been misreading.

**The plant killed it.** JITTER reads **11.216 — lower than GAINED**, so the
planted defect moves `n_eff` in the *same direction as the treatment*. DERIVED:
`n_eff` measures how much frames disagree at a pixel, and **both** correct
registration (a sharply peaked through-focus response) and random jitter
(scrambled content) increase disagreement. It is responsive but **not
diagnostic of quality**, and it fails the Q5 bar I pre-registered. **Withdrawn.**

Had I not planted, I would have shipped this as the headline. It is the third
time tonight a plant has caught something a null would have concealed.

---

## 7. Coverage: the anomaly I nearly reported as a bug

Three sidecars with very different scale spans — bee-3 0.922, marker 0.952,
marker-gained 0.800 — all report cover scale **exactly 0.9974**. I held the
result until I could explain it rather than waving it through.

**MEASURED + DERIVED.** `fit_to_cover(&map, 3.0)` (align_cmd.rs:972) bisects
against real placements, but when the reference is an endpoint frame every
placement has `|a| ≤ 1`, so the pull gather samples strictly *inward* and no
destination pixel is ever uncovered. The binding constraint is then the
reference frame's own identity placement against the 3.0 px resampler margin on
the short axis:

```
k = 1 - margin/(plane_height/2) = 1 - 3/1172 = 0.997440
```

which matches the reported 0.9974 **to four decimals on all three stacks**.

**Consequence: the "coverage" line is uninformative about drift**, and the
orchestrator's "coverage is a quarter of the image" concern does not arise for
endpoint-referenced sidecars. Choosing an endpoint reference costs nothing in
field of view. It also means my arms are a matched set, differing in
registration alone.

---

## 8. What the owner will actually see, having opened it

The metric in §5 is matched-content, band-limited and masked. That is what makes
it trustworthy and it is also what makes it abstract. So I rendered the two arms
the owner would care about at full resolution through the real binary — `strehl
stack 'D:\personal\macro\dry-erase-marker-head-cpl' --gate 2 --srgb --demosaic`
— as `marker-TODAY-shipped.tif` (alignment exactly as it ships) and
`marker-POSSIBLE-gaincorrected.tif`, and I opened them.

### The viewer had to be built carefully, and it lied twice first

A fixed-coordinate crop is invalid here for the reason in §1: these two renders
differ in field of view. **MEASURED: `marker-POSSIBLE`'s subject is 1.1278x the
size of `marker-TODAY`'s** (NCC 0.9419, 8x block-mean scale ladder), so the same
pixel coordinates are different parts of the marker. `src/owner_sbs.py`
therefore takes a 474 px crop from the corrected render for every 420 px crop
from the shipped one and Lanczos-downsamples it to match. **That resampling is
deliberately a handicap applied to the corrected side** — it can only make the
render I expect to win look softer than it is.

Two defects in this viewer, caught before its output was believed:

1. **The scale was applied inverted.** The ladder returns *the magnification to
   apply to B*; I read it as *B's magnification*. The first run took a
   **smaller** crop from the corrected render and **upscaled** it — blurring the
   treatment arm and handicapping the wrong side. Caught by noticing 0.8867
   meant the opposite of what I had printed.
2. **The first content lock lost the lock.** A single full-resolution NCC search
   scored 0.9244 on the self-control (should be 1.0000) and 0.22–0.49 on the
   treatment, and it walked *away* from a centre crop that had visibly matched.
   On macro texture the full-resolution signal is dominated by the fine detail
   that genuinely differs between arms. Replaced with a coarse 4x block-mean
   structural pass plus a fine full-resolution pass, integer shifts only.

**Controls on the final viewer (MEASURED):**

| control | result |
| --- | --- |
| self vs self, scale | 0.9995 (truth 1.0) |
| self vs self, lock | 1.0000 / 1.0000 / 1.0000, exact coordinates recovered |
| **plant: starting guess displaced (+90, −110) px** | **still recovers the exact truth, 1.0000 on all three panels** |

The plant matters: a self-control that starts 1 px from the answer does not
demonstrate a ±158 px search range. The planted one does.

### What I saw

`C:\dev\strehl-out\M97-before-after\SBS-marker-TODAY-vs-POSSIBLE.png`, three
1:1 panels, shipped on the left, gain-corrected on the right.

- **Centre.** Well locked — the same distinctive hooked fibre appears in both.
  The two are very close. The corrected render is *marginally* crisper in fibre
  separation; the shipped render is very slightly mushier. **This is a marginal
  call at 1:1, and it is exactly where §5 predicts the smallest difference,
  because the scale error is zero at the centre of rotation.**
- **Lower-right.** Well locked, and here the difference is visible without
  hunting for it: the corrected render separates individual fibres over the
  bright marker body where the shipped render renders them as a flatter, softer
  mass. **But the corrected render also shows waxy, smeared blobs in the bright
  low-texture region at the bottom** that the shipped render does not. I do not
  know their cause; they are a real artefact and I am not going to omit them
  because they are inconvenient.
- **Upper-left.** Lock NCC 0.2253 and the panels still show different scene
  content — a bright fibre highlight appears in one and not the other.
  **This panel is not a valid comparison and I am not drawing a conclusion from
  it.**

### The honest verdict

**MEASURED/ARGUED: the improvement is real and it is visible, but at 1:1 it is
modest, not transformative, and it is accompanied by at least one new
artefact.** The 19–32% of §5 is a matched-content, band-limited number; the
eye's impression of a full-resolution photograph is not the same quantity and I
will not claim the metric's magnitude as a visual claim.

Two caveats that bound this section, stated rather than buried:

- The treatment lock NCCs are 0.23–0.49 against 1.0000 on the self-control.
  **The two renders genuinely disagree in fine detail**, which is the expected
  consequence of their electing different frames — but it also means these
  panels are approximately, not exactly, the same scene. §5's metric, which
  registers before comparing, remains the decisive measurement; this section is
  corroboration by eye, not a replacement for it.
- **The 1.1278x field-of-view ratio measured here disagrees with the 1.1949x
  implied by §5's ratios** (1.25852 / 1.05329). I have not resolved it. The two
  are measured on different products — full-resolution demosaiced sRGB here,
  binned linear there — so they are not required to agree, but the gap is 6% and
  I flag it rather than assume it away.

---

## 9. Status / Changes / Verified / Not verified / Notes

### Status
**DONE.** The instrument exists, is plant-validated, and answers the question.

### Changes
- `experiments/M97b-align-visible/**` — `PREREG.md`, `src/scout.py`,
  `src/matched.py`, `src/radial4.py` (reported but inadmissible),
  `src/sheet.py`, `src/owner_sbs.py`, `src/render.ps1`, logs and JSON.
- `experiments/M97-warped-merge/src/signtest.py` — one line: `STACK` now reads
  `M97_STACK` from the environment, defaulting to the previous hard-coded
  bee-3 path, so prior results reproduce byte-identically.
- **No changes** to `merge_cmd.rs`, `merge.rs`, `align_cmd.rs`, `warpmap.rs`,
  `lib.rs`, `main.rs`, or any other milestone's tree.

### Verified
- Placebo 1.0004/0.9999/0.9996; blur plant 2.8993/1.8618.
- Ground truth 422.3 plane px with plants at err −0.0016 and −0.0006; sign
  correct; gain-1.0 rewriter control reproduces 0.86650 exactly.
- The zoom-only null banner fired in the ZOOMNULL render; the three arms are
  distinct files by MD5.
- PREREG named risk cleared: mean `n_eff` 13–38 of 299 frames, so the subject
  is not too flat for the test to bite.
- Q4 boundary plant: 186624 blackened rim px move the masked metric 0.0000%.
- `k = 1 − 3/1172 = 0.997440` against three reported 0.9974.
- `cargo clippy --release -p strehl-cli --bins` rc=0.
- Owner side-by-side viewer: self-control 0.9995 scale / 1.0000 lock with exact
  coordinates, and a **planted (+90, −110) px displacement of the starting guess
  still recovers the exact truth at 1.0000 on all three panels**.
- **I opened the renders.** §8 describes what is in them, including an artefact
  that runs against my own conclusion.

### Not verified
- **The 19–32% win is measured on one stack.** It should be repeated on
  `couch-fibers-cpl` (drift 1.2034, edge/centre 1.40) before it is a general
  claim.
- Gain 4.5498 is `ln(0.79999)/ln(0.95214)`, **per-stack and empirical**. It is a
  probe that proves the solve is short, **not a fix**. The fix belongs in M86's
  estimator.
- Whether the win is *visible* at normal viewing size, as opposed to at 1:1.
  §8 is a 1:1 judgement; I did not assess a fit-to-screen view.
- The cause of the waxy smearing §8 found in the corrected render's bright
  low-texture region. It is real; I did not diagnose it.
- Why the field-of-view ratio reads 1.1278 in §8 and 1.1949 in §5.
- `cargo clippy --bins --tests` fails: 3 errors in
  `crates/strehl-cli/src/merge_cmd/halo.rs` (M87, `52c6a52`). Test code only;
  not mine and not touched.
- Whether `WarpMap::load` rejects the torn sidecar I observed in M97.

### Notes
**Corpus pollution has grown from 8 to 11 stray `warpmap.txt` files** under
`D:\personal\macro`, and `bee-3-cpl\warpmap.txt` was rewritten at 06:03 during
this session. `dry-erase-marker-head-cpl` was kept clean by solving with
`strehl align --out` outside the corpus and consuming via `STREHL_WARPMAP`.
The verbatim `align_cmd.rs` patch is in `docs/research/M97-warped-merge.md` §11.

**For M86, one item, and it is the whole story:** the solve applies 23.9% of the
drift on the marker head and 54.3% on bee-3. `E*` is structurally blind to a
common multiplicative gain error — every edge agrees with every other while the
accumulated absolute scale is short — which is how a held-out error of 23.5 px
coexists with a 282 px end-to-end residual. **Fixing the gain converts a
measured null into a measured 19–32% win.** `signtest.py` is a four-minute
end-to-end test for it.

**Correction to my own earlier reporting:** in `docs/research/M97-warped-merge.md`
§11a I wrote that correcting the gain produces "a real but subtle improvement"
and does "not transform this photograph". That conclusion was drawn on bee-3,
which §3 above now shows is the worst subject in the corpus for this question.
On a subject with detail where the error lives, the same correction measures
19–32%. **I was measuring the subject, not the treatment.**
