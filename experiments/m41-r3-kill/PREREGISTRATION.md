# M41 — pre-registration of the R3 kill experiment

Written and committed **before any arm was run**. Rule 20: the FAIL input is
written down first, and an input that produces it must be shown to exist.

This executes §8 of `docs/research/G-edof-deconvolution.md`, which was itself
pre-registered before any M41 data existed. Deviations from §8 are listed in
§4 below with justification; nothing is silently substituted.

## 1. The claim under test

External review item **R3**: *elevate multi-frame Wiener deconvolution across
the focus axis to the core merge.* Currently marked REFUTED in
`docs/proposals/2026-08-external-review.md` on the strength of M20 alone, which
was a Python proxy that never touched `crates/**` and whose own verification
found its optics gate to be a tautology.

## 2. The kill condition, stated before looking

Primary detail metric: **FRC** (Fourier ring correlation) between two merges
built from disjoint halves of the same stack by the same arm. Primary noise
metric: **flat-ROI spatial sigma ratio** against the single middle frame.
The two axes are reported separately and never combined into one score.

Let `f_D` and `f_A` be the FRC-1/7 crossing frequency (cyc/px, quad plane) of
arm D and arm A. Let `n_D`, `n_A` be their flat-ROI noise ratios.

**R3 STANDS REFUTED if** — on both 109MSDCF and 119MSDCF —

> `f_D <= 1.02 * f_A`, i.e. the deconvolving merge buys **less than 2%**
> in FRC resolution over the shipped noise-gated merge,

**OR** if it buys resolution only by paying noise:

> `f_D > 1.02 * f_A` but `n_D > 1.10 * n_A`.

**R3 MUST BE REOPENED if** — on both stacks —

> `f_D >= 1.05 * f_A` **and** `n_D <= 1.05 * n_A`.

i.e. a >=5% FRC resolution gain at no more than 5% noise cost. This is the
regime M20 never reached: M20's benefit was entirely noise, detail +/-1.5%.

The band between (2%, 5%) is **INDETERMINATE** and is reported as such rather
than being rounded to a verdict.

**The experiment is VOID** (no verdict either way) if the positive control
fails: on a planted synthetic where the true latent image is known, arm D must
beat arm A in PSNR at calibrated sigma. If a Wiener merge cannot win where the
forward model is exactly true by construction, the harness is broken and no
real-data reading from it means anything.

## 3. Rule 20 — do inputs exist that produce each outcome?

| Outcome | An input that produces it | Exists? |
|---|---|---|
| R3 REFUTED via `f_D <= 1.02 f_A` | any scene whose spectrum is empty above `f_sig` — fact 27 says these captures are that scene | yes, by fact 12/27 |
| R3 REFUTED via noise | arm E (unguarded, `sigma^2/S = 0`) is a deconvolution with no noise term; it *must* land here or the noise metric has no power | yes, arm E is built to land there |
| R3 REOPENED | the planted control at low blur and high SNR — same estimator, forward model exactly true | yes, that is the positive control |
| VOID | a harness bug | detectable, not producible on demand |

Arm E is therefore doing double duty: it is an ablation **and** the proof that
the noise axis of the kill condition can fire. Arm C (plain mean) is the proof
that the FRC axis can fire in the other direction: fact 19 says the mean costs
detail relative to selection, so `f_C < f_A` is the expected sign and a null
result there would indicate the FRC metric is insensitive.

## 4. Deviations from §8 as written, with justification

**D1 — §8.6 condition 3 ("D beats A on gradient correlation") is UNRUNNABLE on
real data as specified.** §8.5 requires gradient *correlation* "with the
reference" but never defines a reference for a real stack, where no ground
truth exists. Correlating against any merge of the same data is circular.
*Minimal deviation:* gradient correlation is computed **only on the planted
positive control**, where the latent image is known. On real data the detail
axis is FRC, which is what the orchestrator asked for and is ground-truth-free
by construction. This is a defect in my own pre-registration, not a
convenience.

**D2 — FRC is measured split-half, not on the 112/113 pair.** §8.5 named
112MSDCF/113MSDCF as the independent pair. Those are two *different captures*
(79 and 63 frames, different exposure), so an FRC between them confounds the
merge rule with the capture. Split-half — merge even frames and odd frames
separately with the *same* arm and correlate — is the canonical FRC protocol
and isolates the merge rule, which is the variable under test. 112/113 is
retained as a secondary reading if time allows.

**D3 — the positive control is built inside this experiment, not by calling
`experiments/m25-simulator/`.** §8.4 named m25 as the planted control; the M41
brief forbids touching `experiments/m25-simulator/**` because a live agent owns
it. A self-contained planted control is written here instead.

**D4 — all arms operate on unaligned frames in plane coordinates.** MEASURED:
`crates/strehl-cli/src/merge_cmd.rs` contains no alignment, warp or
registration step. Holding alignment constant at *none* across all six arms is
the correct controlled comparison for a claim about the **merge rule**. It does
mean no arm's absolute FRC number is a statement about the shipped pipeline's
eventual quality.

**D5 — arm A is reproduced in Python and cross-checked against the shipped
binary rather than being read out of it.** The Rust merge writes a
white-balanced, level-scaled RGB TIFF; the Python arms work on the raw green
quad. Rather than invert that transform, arm A is implemented in the harness
and validated against the binary's own printed flat-ROI acceptance invariant on
the same ROI. **If the Python arm A's flat-ROI noise ratio does not agree with
the shipped binary's to within 5%, the harness is declared broken and no
verdict is issued.** That is a control that can fail. Neither
`crates/strehl-core/src/merge.rs` nor `through_focus.rs` is edited (M40 owns
them); the focus and gate rules are re-implemented from their constants
(`WINDOW_RADIUS = 13`, `REGULARISER_RADIUS = 8`, `FINE_WINDOW_RADIUS = 2`) and
that re-implementation is disclosed here.

## 5. Arms (§8.3, unchanged)

| Arm | Rule |
|---|---|
| A | shipped-equivalent: regularised winner field + noise-gated average |
| B | plain per-pixel argmax (fine focus field, no regulariser) |
| C | plain mean of all frames |
| D | guarded focus-axis RIF, `L = sum H_k* Y_k / (sum \|H_k\|^2 + sigma^2/S)`, `H_k` = defocus OTF composed with the measured diffraction OTF |
| D' | ablation: D without the diffraction term in `H_k` |
| E | ablation: D unguarded, `sigma^2/S = 0` |

## 6. Controls (§8.4)

1. **Permutation null** — shuffle the frame order before building the OTFs, so
   each pixel's OTF stack is assigned to the wrong frames. Target: D's
   advantage collapses to <=1.05x. M21's placebo read 1.01x.
2. **Degenerate control** — `coffee-bubbles` (19 frames, constant focus, fact
   49). With no focus variation every `H_k` is equal and D must reduce to C.
3. **Positive control** — planted synthetic, latent known.
4. **Circularity control** — OTF widths self-calibrated from the through-focus
   curve vs. an independent parametric defocus model. If the advantage only
   exists with the self-calibrated widths it is circular.
5. **Band control** — split at `f_sig = 0.2762 cyc/px` (fact 27). Above it the
   scene carries no signal, so all arms must be statistically indistinguishable
   there. If they are not, the metric is reading noise as detail.
6. **Flat-ROI control run FIRST**, not as a closing check (rule 9).

## 7. What is NOT being tested

This does not test whether deconvolution helps *after* a good alignment, and it
does not test an iterative arm (fact 404: a regularised inverse filter lands
within 0.19 dB of Richardson-Lucy at 1/237 the cost, so the iterative arm is
not worth the night). A negative result here is a result about the merge rule
at this rig's optics, not a general claim about deconvolution.
