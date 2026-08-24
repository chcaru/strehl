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

## 8. Status / Changes / Verified / Not verified / Notes

### Status
**DONE.** The instrument exists, is plant-validated, and answers the question.

### Changes
- `experiments/M97b-align-visible/**` — `PREREG.md`, `src/scout.py`,
  `src/matched.py`, `src/radial4.py` (reported but inadmissible),
  `src/sheet.py`, `src/render.ps1`, logs and JSON.
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

### Not verified
- **The 19–32% win is measured on one stack.** It should be repeated on
  `couch-fibers-cpl` (drift 1.2034, edge/centre 1.40) before it is a general
  claim.
- Gain 4.5498 is `ln(0.79999)/ln(0.95214)`, **per-stack and empirical**. It is a
  probe that proves the solve is short, **not a fix**. The fix belongs in M86's
  estimator.
- Whether the win is *visible* to the owner at normal viewing size, as opposed
  to measurable. Renders are at `C:\dev\strehl-out\M97-before-after\`.
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
