# M82 — outcome-normalised gate

**VERDICT — MEASURED/ARGUED: NO SHIP; A PORTABLE SHARPNESS PRICE LIST IS
NOT ESTABLISHED, NOT REFUTED.** The requested coordinate is operational: all
six fresh 15-rung ladders are monotone, all three requested model-predicted
sigma gains are bracketed, and all 18 solved points confirm within the frozen
±0.005 bar. The price instrument is not operational at the resulting points.
All 18 M57 `dsig` rows in the original six-stack arm are unreadable under the
rule committed before the measurement: 15 finite central estimates have
maximum absolute magnitude **0.1754 px**, only 51.1% of M82's frozen
**0.343 px** bound taken from M57's measured independent-noise null, and all
three `foam` rows return `N/A`. No unreadable central value is promoted into
a span.

**EASIEST-CASE VERDICT — MEASURED/ARGUED: THE WRAPPED-TEXT SIBLING TEST IS
NOT ESTABLISHED.** At requested gain `S = 0.70`, the two siblings confirm at
0.7005 and 0.7006. Their central sharpness prices are +0.0790 and +0.0845 px,
a nominal 1.069× span, but both are below the frozen 0.343 px null and the
second also misses the corrected-z rule. At `S = 0.50` their central prices
are nearly identical, +0.1754 and +0.1748 px, and still both abstain. These
numbers are compatible with portability; the instrument has no authority to
say that they demonstrate it.

**CAPABILITY VERDICT — MEASURED/DERIVED: OUTCOME NORMALISATION DOES REPAIR
THE KNOB'S NUMERICAL SCALE.** At `S = 0.70`, raw solved gates span
**22.176×** across the six captures, from 1.1327 to 25.1196, while achieved
gain spans only 0.6975–0.7015. The two siblings need gates differing 2.279×
to reach 0.7005 and 0.7006. A per-stack solver can therefore give the request
one model-predicted meaning even though one raw gate cannot. That is a
capability result, not evidence that its sharpness price is portable.

**MECHANISM — MEASURED/ARGUED: A WHOLE-IMAGE MEAN DOES NOT LOCATE THE
DETAIL-BEARING PIXELS ON THE CONTINUUM.** At the matched `S = 0.70` request,
mean local admission in the registered detail ROIs spans 1.026–2.623 and
local singleton exposure spans **25.46%–97.41%**. `coffee-bean` is the
decisive example: whole-image mean `n_eff` is 18.424, yet 97.41% of its detail
ROI remains a selector. This spatial freedom is a measured reason a global
sigma mean need not have one resolution price. It was registered as a
mechanism diagnostic, not as the portability decision, so it does not convert
the unreadable sharpness result into a post-hoc refutation.

**FLOOR VERDICT — MEASURED/ARGUED: NO SINGLE-FRAME NOISE FLOOR IS
ESTABLISHED.** Every solved operating point retains singleton selection
exposure, from **0.96% to 76.84%**. The shipped prediction does not price the
winner's noise coupling at a singleton. M82 therefore makes no actual-noise
claim, ships neither proposed preset, and changes no production code.

**BEE-AMENDMENT VERDICT — MEASURED/ARGUED: THE RENAMED PATH REPRODUCES,
BUT THE THREE-BEE CONTROL CANNOT DECIDE PORTABILITY.** The original `bee-1`
run was complete; a clean rerun from `bee-1-cpl` reproduces every selected
ladder and confirmation value exactly and reproduces the entire sharpness JSON
exactly. M70, contrary to the amendment brief, had already measured all three
bees. The fresh current-path spectral run reproduces M70's tracked aggregate
values exactly, but the group fails M82's frozen physical-comparability rule:
response span is 1.0526× at ±5 and 1.1097× at ±10, above 1.05. All nine new
requests confirm without refinement, but all three primary `dsig` prices are
also unreadable. The conditional bee result is therefore
`PREMISE_NOT_ESTABLISHED`; the numerical price result, even if comparability
were assumed, is `NOT ESTABLISHED`. Neither result changes the original
`NO SHIP / NOT ESTABLISHED` decision.

## M82 §1 — The source question and the corrections carried into it

**MEASURED.** `crates/strehl-core/src/merge.rs` is the authority for the
operator. Pass one elects a winner from the 17×17-regularised focus field.
Pass two admits that winner unconditionally and admits another frame when
`best - focus <= T * sqrt(2) * FOCUS_NOISE_SD`; admitted native RAW samples
enter an arithmetic mean. `DEFAULT_GATE` is 4.0 and
`FOCUS_NOISE_SD` is 0.015214.

**MEASURED.** SYNTHESIS fact 19's source, M2 §3.2.3, measures a plain
unweighted 22-frame mean at 0.534× one-frame spatial noise, naive argmax at
1.253×, and a shifted-winner placebo at 0.981×. The 0.534× value is not a
gated operating point.

**MEASURED.** SYNTHESIS fact 813's source, M57 §9, measures a 0.496–0.740 px
near-selector advantage on 6 of 8 real cells, with one opposite result and one
`NaN`. That experiment used a fractional peak-height gate, not the shipped
absolute-noise gate. M82 reuses its spectral contrast and its limitations,
not its old gate values.

**MEASURED.** SYNTHESIS fact 848 records the owner's decision and its
implication: the gate should expose one noise-versus-sharpness continuum with
named points, rather than hide the trade in two modes. M82 tests whether the
continuum can be labelled by an outcome with a portable price.

**MEASURED.** M69 fact 18's 4.062× number is a controlled texture-form span,
not a per-stack span. M69 facts 17 and 56 report competing per-stack spans of
1.186× and 2.104×. M81's own fact 9 then shows that a per-stack scalar
correction worsens the wrapped-text common-target span from 3.254× to 3.629×,
and M81's own fact 10 reports 49.538× across the five M77 stacks.

**MEASURED.** M77 fact 9 reports `n_eff/N` spanning 31.7× at shipped gate 4.
M77 fact 39 reports sibling target gates differing 3.31×. M70 P34 supplies the
clean control: the siblings' gate-free through-focus responses agree within
4.7% at every rung and their spectral counts within 2.4%.

**ARGUED.** Those results reject the search for one raw threshold but do not
reject an exposed continuum. M82's hypothesis is narrower: if a user requests
one model-predicted merged sigma relative to one frame, the sharpness price of
that request is portable across stacks.

## M82 §2 — Frozen design, stacks and provenance

**MEASURED.** `experiments/M82-normalised-gate/PREREGISTRATION.md` was
committed as `528a85d` before any M82 ladder, confirmation, sharpness merge,
flat rescan, or portability score. The primary coordinate is

```text
S(T) = mean_pixels(predicted merged sigma / predicted single-frame sigma).
```

**ARGUED.** This is the shipped mean of per-pixel predicted-sigma ratios, not
`1/sqrt(mean n_eff)`. The latter discards the admission distribution and is
Jensen-wrong. The requested rungs are 0.90, 0.70, and 0.50; 0.70 is the sole
primary decision point.

**ARGUED.** `S` remains a **model-predicted sigma gain**. The shipped
`selection_inflation` is 1.0, so M82 never shortens that phrase to measured
noise and never infers an actual-noise floor.

**MEASURED.** All RAW inputs were read from filename-sorted directories under
`D:\personal\macro`. The stack identities and original 256² ROIs come from
M77's committed ROI records. The 512² cells are the frozen M82 expansion used
by M57 `dsig`; every flat cell ran before its detail cell.

| Class | stack / subject | N | original flat ROI | original detail ROI | M82 sharpness flat / detail |
| --- | --- | ---: | --- | --- | --- |
| MEASURED | `wrapped-text-1` / label text | 130 | `32,1312,256,256` | `2208,672,256,256` | `32,1184,512,512` / `2080,544,512,512` |
| MEASURED | `wrapped-text-2` / label text | 120 | `32,672,256,256` | `3104,160,256,256` | `32,544,512,512` / `2970,32,512,512` |
| MEASURED | `109MSDCF` / acrylic paint | 22 | `1440,416,256,256` | `1952,1056,256,256` | `1312,288,512,512` / `1824,928,512,512` |
| MEASURED | `coffee-bean` / coffee bean | 105 | `32,416,256,256` | `1312,416,256,256` | `32,288,512,512` / `1184,288,512,512` |
| MEASURED | `foam` / coffee foam | 100 | `1312,288,256,256` | `160,1952,256,256` | `1184,160,512,512` / `32,1800,512,512` |
| MEASURED | `bee-1` / bee anatomy | 299 | `2720,1568,256,256` | `1952,672,256,256` | `2592,1440,512,512` / `1824,544,512,512` |

**MEASURED.** The original `bee-1` row was read from the then-existing
`D:\personal\macro\bee-1`. That path is now absent and its current physical
directory is `D:\personal\macro\bee-1-cpl`. M82's amendment preserves the
logical ID, maps it to the renamed directory, and reruns the row rather than
rewriting the original evidence (§§10–13).

**ARGUED.** The primary sharpness price is M57 `dsig` between independently
merged even/odd pairs at gate 0 and at the solved absolute gate. Positive
means the requested point is blurrier than the selector. A price is readable
only when it is finite, has no RAW container pin, passes the local
Python-versus-Rust check, has absolute magnitude above 0.343 px, and satisfies
`abs(C)/(3.09 * jackknife_se) >= 2`.

**ARGUED.** The sibling bar is a positive readable-price span no larger than
1.50×. The five-M77-stack bar is no larger than 2.00×. An unreadable member
returns `NO SHIP / NOT ESTABLISHED`; a readable excess or sign reversal would
return `NO SHIP / REFUTED`. Neither threshold changes after seeing the data.

**MEASURED.** The private release binary was built from
`79468b971bbf3e7657c86def2ea1b0ddbef78c99` with Rust and Cargo 1.98.0 MSVC,
`--locked`, `RUSTFLAGS=--cfg m82_private_build`, and private
`CARGO_TARGET_DIR=experiments/M82-normalised-gate/target-m82`. It is
8,278,016 bytes with SHA-256
`2f1ea8904240acca98937f4755354302b53a061c8791d677b721137e45c58a74`.
The runtime crate trees and `Cargo.lock` are unchanged between that revision
and both original evidence commit `543534e` and bee evidence commit
`4ea2f1b`.

## M82 §3 — The outcome axis exists and the solver reaches it

**MEASURED.** Every fresh ladder uses gates
`0, 0.25, 0.5, 1, 2, 4, 8, 16, 24, 32, 40, 48, 64, 96, 128`. All six
predicted-sigma ladders are non-increasing. Every request is bracketed without
extrapolation. The analytic power-law control and interpolation
reconstruction tests both pass.

**MEASURED.** Sixteen of 18 initial confirmations met the ±0.005 rule.
`wrapped-text-2` at 0.70 first read 0.7070 and `109MSDCF` at 0.70 first read
0.7079. The frozen interpolation update was applied once to each; they then
read 0.7006 and 0.7005. No result needed the second permitted update.

**MEASURED.** The complete set of solved operating points follows. `n/N` is
whole-plane mean `n_eff` divided by frame count; singleton and boundary are
whole-plane pixel percentages.

| Class | stack | request | solved gate | confirmed S | mean `n_eff` | `n/N` | singleton | boundary |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MEASURED | `wrapped-text-1` | 0.90 | 6.736142 | 0.9039 | 1.395 | 0.01073 | 68.86% | 0.16% |
| MEASURED | `wrapped-text-1` | 0.70 | 25.119558 | 0.7005 | 2.613 | 0.02010 | 15.49% | 0.16% |
| MEASURED | `wrapped-text-1` | 0.50 | 62.056392 | 0.5004 | 11.261 | 0.08662 | 0.96% | 0.16% |
| MEASURED | `wrapped-text-2` | 0.90 | 2.501842 | 0.9041 | 1.487 | 0.01239 | 71.26% | 0.02% |
| MEASURED | `wrapped-text-2` | 0.70 | 11.022407 | 0.7006 | 3.302 | 0.02752 | 21.11% | 0.02% |
| MEASURED | `wrapped-text-2` | 0.50 | 28.148201 | 0.5004 | 15.419 | 0.12849 | 2.89% | 0.02% |
| MEASURED | `109MSDCF` | 0.90 | 0.450363 | 0.9025 | 1.370 | 0.06227 | 69.40% | 2.22% |
| MEASURED | `109MSDCF` | 0.70 | 1.574757 | 0.7005 | 2.459 | 0.11177 | 23.43% | 2.22% |
| MEASURED | `109MSDCF` | 0.50 | 3.830908 | 0.5003 | 4.802 | 0.21827 | 4.92% | 2.22% |
| MEASURED | `coffee-bean` | 0.90 | 0.370100 | 0.9042 | 1.551 | 0.01477 | 76.84% | 7.60% |
| MEASURED | `coffee-bean` | 0.70 | 2.303041 | 0.6975 | 18.424 | 0.17547 | 59.59% | 7.60% |
| MEASURED | `coffee-bean` | 0.50 | 36.237022 | 0.5000 | 38.402 | 0.36573 | 17.87% | 7.60% |
| MEASURED | `foam` | 0.90 | 4.295399 | 0.9018 | 1.386 | 0.01386 | 69.32% | 0.00% |
| MEASURED | `foam` | 0.70 | 18.513285 | 0.7015 | 2.677 | 0.02677 | 22.75% | 0.00% |
| MEASURED | `foam` | 0.50 | 55.035844 | 0.5006 | 6.324 | 0.06324 | 1.84% | 0.00% |
| MEASURED | `bee-1` | 0.90 | 0.263891 | 0.9015 | 1.502 | 0.00502 | 74.26% | 1.74% |
| MEASURED | `bee-1` | 0.70 | 1.132716 | 0.6992 | 7.427 | 0.02484 | 49.24% | 1.74% |
| MEASURED | `bee-1` | 0.50 | 6.048060 | 0.5023 | 80.140 | 0.26803 | 23.52% | 1.74% |

**MEASURED/DERIVED.** Across all six captures, solved-gate spans are 25.526×,
22.176×, and 16.199× at requests 0.90, 0.70, and 0.50. The sibling gate ratios
are 2.692×, 2.279×, and 2.205×. The achieved request, not the raw threshold,
is the portable part of this result.

## M82 §4 — The sibling price, reported separately

**MEASURED.** The table reports central `dsig`, the frozen 3.09×-corrected
sector-jackknife standard error, and their ratio. `READABLE = no` is a
registered abstention, not a zero price.

| Class | stack | request | price px | corrected SE px | corrected z | null-bound limb | readable |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| MEASURED | `wrapped-text-1` | 0.90 | -0.03497 | 0.02833 | 1.23 | fail | no |
| MEASURED | `wrapped-text-2` | 0.90 | +0.06775 | 0.03987 | 1.70 | fail | no |
| MEASURED | `wrapped-text-1` | 0.70 | +0.07901 | 0.01971 | 4.01 | fail | no |
| MEASURED | `wrapped-text-2` | 0.70 | +0.08450 | 0.07131 | 1.18 | fail | no |
| MEASURED | `wrapped-text-1` | 0.50 | +0.17539 | 0.00886 | 19.79 | fail | no |
| MEASURED | `wrapped-text-2` | 0.50 | +0.17481 | 0.03268 | 5.35 | fail | no |

**MEASURED/ARGUED.** The primary central values differ by 6.72% relative to
their mean and have a nominal 1.069× ratio, inside the 1.50× product bar. The
ratio is not the result because its two inputs are not readable. The same
restriction applies to the striking 0.3% central agreement at request 0.50.

**ARGUED.** The sibling test therefore neither fails nor passes. Outcome
normalisation co-locates the two captures in its own model and also makes their
local detail admissions similar (§6), but M57's independently measured null is
wider than the price being compared. The frozen consequence is
`NO SHIP / NOT ESTABLISHED`.

## M82 §5 — The five-stack price and the full curve

**MEASURED.** At the primary request, no required price is readable.
`coffee-bean` has one pinned sample in the 512² detail cell and a small
negative central estimate. `foam` has 22,623 pinned detail samples and returns
`N/A`. The other finite values all remain under the 0.343 px null.

| Class | stack | primary price px | corrected SE px | corrected z | detail pins | readable | registered disposition |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| MEASURED | `wrapped-text-1` | +0.07901 | 0.01971 | 4.01 | 0 | no | below null bound |
| MEASURED | `wrapped-text-2` | +0.08450 | 0.07131 | 1.18 | 0 | no | below null and z |
| MEASURED | `109MSDCF` | +0.05832 | 0.05392 | 1.08 | 0 | no | below null and z |
| MEASURED | `coffee-bean` | -0.01500 | 0.04285 | 0.35 | 1 | no | pin, below null and z |
| MEASURED | `foam` | `N/A` | `N/A` | `N/A` | 22,623 | no | pin and non-finite |
| MEASURED | `bee-1` | +0.02073 | 0.01834 | 1.13 | 0 | no | below null and z |

**MEASURED.** The complete central curve is shown to disclose its numerical
shape without promoting it. Each cell is `price ± corrected SE` in pixels.

| Class | stack | request 0.90 | request 0.70 | request 0.50 | curve control |
| --- | --- | --- | --- | --- | --- |
| MEASURED | `wrapped-text-1` | -0.03497 ± 0.02833 | +0.07901 ± 0.01971 | +0.17539 ± 0.00886 | pass |
| MEASURED | `wrapped-text-2` | +0.06775 ± 0.03987 | +0.08450 ± 0.07131 | +0.17481 ± 0.03268 | pass |
| MEASURED | `109MSDCF` | -0.01352 ± 0.06166 | +0.05832 ± 0.05392 | +0.07826 ± 0.03971 | pass |
| MEASURED | `coffee-bean` | -0.01208 ± 0.00836 | -0.01500 ± 0.04285 | +0.04144 ± 0.04583 | not established: pin |
| MEASURED | `foam` | `N/A` | `N/A` | `N/A` | not established: pins |
| MEASURED | `bee-1` | +0.01116 ± 0.02632 | +0.02073 ± 0.01834 | +0.03318 ± 0.02654 | pass |

**MEASURED.** None of the four unpinned curves has a significant reversal
under the frozen conservative intervals. That control passes where it can
answer. It cannot rescue a price whose absolute magnitude sits below the
separate empirical null bound.

**ARGUED.** The registered five-stack span is undefined because all five
required inputs abstain. The small negative `coffee-bean` centre cannot
trigger the sign-reversal rule because it is unreadable. The five-stack result
is `NO SHIP / NOT ESTABLISHED`, not a refutation manufactured from central
signs.

## M82 §6 — Why the whole-image coordinate does not determine local price

**MEASURED.** The registered diagnostics below use the full-stack merge in
each 512² detail cell at the primary solved gate. The whole-plane request is
matched to roughly 0.70 on every row, but local admission remains very
different.

| Class | stack | confirmed S | whole mean `n_eff` | whole singleton | local mean `n_eff` | local singleton | local `n_eff` p10 / p50 / p90 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| MEASURED | `wrapped-text-1` | 0.7005 | 2.613 | 15.49% | 1.567 | 43.30% | 1 / 2 / 2 |
| MEASURED | `wrapped-text-2` | 0.7006 | 3.302 | 21.11% | 1.625 | 38.32% | 1 / 2 / 2 |
| MEASURED | `109MSDCF` | 0.7005 | 2.459 | 23.43% | 2.182 | 35.62% | 1 / 2 / 4 |
| MEASURED | `coffee-bean` | 0.6975 | 18.424 | 59.59% | 1.026 | 97.41% | 1 / 1 / 1 |
| MEASURED | `foam` | 0.7015 | 2.677 | 22.75% | 2.623 | 25.46% | 1 / 2 / 5 |
| MEASURED | `bee-1` | 0.6992 | 7.427 | 49.24% | 1.090 | 91.28% | 1 / 1 / 1 |

**MEASURED/DERIVED.** At fixed whole-image `S`, whole-image mean `n_eff`
spans 7.49× and local detail mean `n_eff` spans 2.56×. The more informative
quantity is the distribution: the detail-cell singleton fraction spans 71.95
percentage points. A scalar mean sigma can be identical while the pixels that
carry the sharpness measurement occupy different ends of the gate continuum.

**ARGUED.** This explains why replacing raw gate with a whole-image mean is
not sufficient by construction. It does not prove that no global coordinate
can work, and it does not overrule the registered `dsig` decision. It identifies
what a successful coordinate would additionally have to constrain: the
spatial admission distribution in regions containing resolved detail.

## M82 §7 — Flat control, M80 companion, pins and the floor

**MEASURED.** M77's all-frame flat-contamination precondition fails on
`wrapped-text-1`, `109MSDCF`, and `foam`, exactly three of the five mandatory
M77 stacks. The fresh all-frame sibling scan also fails on
`wrapped-text-2`. Only `coffee-bean` and `bee-1` may expose M80's numerical
retention as readable.

| Class | stack | max flat contamination | precondition | M80 retention 0.90 / 0.70 / 0.50 | M80 status |
| --- | --- | ---: | --- | --- | --- |
| MEASURED | `wrapped-text-1` | 2.633887 | fail | 0.989 / 0.963 / 0.866 | UNREADABLE |
| MEASURED | `wrapped-text-2` | 1.772517 | fail | 0.980 / 0.931 / 0.798 | UNREADABLE |
| MEASURED | `109MSDCF` | 1.139894 | fail | 0.997 / 0.992 / 0.987 | UNREADABLE |
| MEASURED | `coffee-bean` | 1.096836 | pass | 1.003 / 0.998 / 0.979 | READABLE |
| MEASURED | `foam` | 15.876902 | fail | 0.962 / 0.896 / 0.843 | UNREADABLE |
| MEASURED | `bee-1` | 1.066618 | pass | 1.000 / 0.999 / 0.990 | READABLE |

**ARGUED.** M80 is one-sided against resolved-detail collapse. The two
readable rows show no material collapse at the primary point; they cannot
establish positive sharpness or repair M57's abstention. Numerical signs on
the four failed flat controls do not enter any verdict.

**MEASURED.** The independent Python implementation matches Rust whole-plane
mean `n_eff` on `109MSDCF`, gate 2, at 2.8911099 versus 2.891, relative error
**0.00380%** against a 1% bar. At the 18 target/ROI checks, 16 raw-gradient RMS
values agree within 0.424%; `foam` at 0.70 and 0.50 differ by 1.92% and 6.14%.
Those two rows contain container pins and were made unreadable exactly as
pre-registered rather than silently treated as `fold_censored`.

**MEASURED.** Every whole-plane target in §3 has non-zero singleton exposure.
At requests 0.90, 0.70, and 0.50 the ranges are respectively 68.86%–76.84%,
15.49%–59.59%, and 0.96%–23.52%. M82 does not claim that model-predicted
sigma bounds actual output noise on those pixels.

## M82 §8 — The control that failed on demand

**MEASURED.** `mutation_control.py` found exactly one source byte sequence,
changed the core Python admission comparison from `gap <= tolerance` to
`gap >= tolerance`, and verified the planted bytes by read-back. The announced
four-test invocation exited 1 on its first assertion.

**MEASURED.** The `finally` path restored `m82lib.py` byte-for-byte.
`mutation-control.log` records `PLANTED_READBACK=PASS`, `EXIT=1`, and
`RESTORED=True`; its SHA-256 is
`30dad39e4a8db547cc0260e263166f39e0e2c590b5fac5b2a0219058e4116465`.
The unmutated suite subsequently passes 4/4.

**ARGUED.** This control demonstrates sensitivity to the direction of the
admission comparison. It does not validate M57's sharpness power; M57's
independent-noise null is the control that governs that choice, and it is the
one that forces abstention here.

## M82 §9 — Product decision and what would have to be true instead

**ARGUED.** Do not ship an automatic gate solver from this milestone. The
solver reaches its requested model outcome, but the only registered instrument
for the promised price list cannot resolve the price. Calling the sibling
central values a pass would relax a bar after seeing the result; calling the
five-stack central signs a refutation would do the same in the other direction.

**ARGUED.** Do not ship the preregistered names **detail** (`S = 0.90`) and
**quiet** (`S = 0.50`). A preset name is a promise about the trade, not merely
about a model field printed by the CLI. M82 has validated only the latter.

**ARGUED.** A decisive follow-up needs at least one of these changes, frozen
before another price measurement:

1. a truth-linked or multi-ROI sharpness instrument whose independent-noise
   null is measured below the effect it compares, with a valid standard error
   and an explicit pin policy; simply lowering M57's 0.343 px bar is not
   admissible;
2. an outcome coordinate that constrains the spatial distribution of
   admission in detail-bearing regions, such as a predeclared predicted-sigma
   quantile or region-aware request, rather than only its whole-image mean; or
3. a capture with truth-linked resolution and repeated-noise information,
   allowing the sharpness and actual-noise prices to be measured together.

**ARGUED.** M57 §11 already proposes testing whether independent 512² ROIs
average its scatter down, but labels that premise unmeasured. M82's largest
finite central price is 0.175 px, so a useful follow-up instrument would need
substantially more resolving power than the present 0.343 px null if these
centres are representative. That observation sizes a future experiment; it is
not a replacement acceptance threshold.

**ARGUED.** The owner's continuum reframe survives as an open hypothesis. The
specific whole-image-mean presentation is not ready for a user because it has
neither a measured portable price nor a measured noise floor.

## M82 §10 — Renamed-path audit and the prior bee evidence

**MEASURED.** The amendment began with a fresh metadata-only path audit. The
four unchanged M77 directories and the extra `wrapped-text-2` directory exist
at the registered frame counts. The old bee path does not exist; all three
current bee directories contain 299 filename-sorted ARWs.

| Class | logical stack | physical directory | current ARWs |
| --- | --- | --- | ---: |
| MEASURED | `wrapped-text-1` | `wrapped-text-1` | 130 |
| MEASURED | `wrapped-text-2` | `wrapped-text-2` | 120 |
| MEASURED | `109MSDCF` | `109MSDCF` | 22 |
| MEASURED | `coffee-bean` | `coffee-bean` | 105 |
| MEASURED | `foam` | `foam` | 100 |
| MEASURED | `bee-1` | `bee-1` | absent |
| MEASURED | `bee-1` | `bee-1-cpl` | 299 |
| MEASURED | `bee-2` | `bee-2-cpl` | 299 |
| MEASURED | `bee-3` | `bee-3-cpl` | 299 |

**MEASURED.** The original result was not partial. `ladder-bee-1.log`,
`confirm-bee-1.log`, and `sharpness-bee-1.log` each record 299 frames and
exit 0. Their run interval is 2026-08-24T05:40:07Z through
2026-08-24T05:59:12Z. The original ladder and confirmation aggregates,
per-stack sharpness JSON, and final results JSON all include `bee-1`.

**MEASURED.** The urgent brief's statement that nobody had measured the bee
group is false at source. M70 commit `d882b0c` includes `bee-1`, `bee-2`, and
`bee-3`; its tracked `s10_architecture.json` and log contain their
equal-average through-focus ladders. M70 records 299 frames at marked f/5.6
for each and ISO 100, 400, and 100.

**MEASURED CORRECTION TO M82'S OWN AMENDMENT.**
`PREREGISTRATION-BEE.md` calls M70's `tfs-bee-*.npz` files “committed.”
`git ls-files --error-unmatch` shows that they are not tracked; `*.npz` is
ignored. The pre-measurement filename comparison used those existing local
intermediates, not durable repository evidence. The full-precision comparison
targets used by the frozen identity test do come from M70's tracked
`s10_architecture.json` and log. M82's fresh aggregate outputs and run logs are
tracked; its regenerated NPZ intermediates remain ignored.

**MEASURED.** The bee amendment was committed as `1c2caee` before M82 decoded
any current `*-cpl` RAW. It preserves the original wrapped-text and five-stack
bars independently, freezes current-path identity within 0.1%, and allows the
bee price result to decide portability only if a separate physical rule
passes.

## M82 §11 — The bee triple is not a sibling control under the frozen rule

**MEASURED.** M82 reran M70's unchanged `s04`, `s05`, `s10`, and `m70lib`
methods from `d882b0c` on all three current directories. The current shipped
profile is also unchanged from that commit. Each run used M70's 24 fixed
green-quincunx centres, 256-sample patches, 128-sample Hann Welch tiles, its
six bands, shipped photon-transfer subtraction, and its low-band texture gate.
The three filename manifests each contain `DSC00001.ARW` through
`DSC00299.ARW`.

**MEASURED.** Every current-path response below equals M70's tracked
full-precision aggregate value exactly; maximum relative identity error is
0.0 on every stack, inside the frozen 0.1% line.

**ARGUED.** This establishes the amendment's numerical current-path identity
control. It does not retroactively establish RAW byte identity with M70's old
inputs, because M70 recorded no tracked RAW hashes.

| Class | stack | textured patches | ±1 | ±2 | ±3 | ±5 | ±10 | ±20 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MEASURED | `bee-1` | 16 | 1.000000 | 1.182340 | 1.290873 | 1.371983 | 1.505788 | 1.381273 |
| MEASURED | `bee-2` | 18 | 1.000000 | 1.181535 | 1.302446 | 1.444175 | 1.670943 | 1.757968 |
| MEASURED | `bee-3` | 19 | 1.000000 | 1.207006 | 1.338482 | 1.435487 | 1.564759 | 1.636857 |

**MEASURED/DERIVED.** All stacks meet the minimum of 16 textured patches and
all select ±10 as the maximum registered stable rung. The cross-stack spans
at ±1, ±2, ±3, ±5, and ±10 are respectively 1.0000×, 1.0216×, 1.0369×,
**1.0526×**, and **1.1097×**. The last two exceed the frozen 1.05 line. The
reported but non-deciding ±20 span is 1.2727×.

**ARGUED.** Physical comparability is therefore
`PREMISE_NOT_ESTABLISHED`. The three captures may be the same subject class,
but they do not earn M70 P34-equivalent sibling status. Under the committed
amendment, neither agreement nor disagreement in their price values may pass
or refute portability.

## M82 §12 — The three-bee outcome and price measurements

**MEASURED.** All three fresh 15-rung ladders are non-increasing, bracket all
three requests, and report the required CLI ISO values. All nine first
solutions confirm within ±0.005; `bee-refine-plan.json` contains zero updates.
The table reports whole-plane admission and the separately measured 512²
detail-cell singleton exposure.

| Class | stack | request | solved gate | confirmed S | mean `n_eff` | `n/N` | whole singleton | local singleton |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MEASURED | `bee-1` | 0.90 | 0.263891 | 0.9015 | 1.502 | 0.00502 | 74.26% | 97.96% |
| MEASURED | `bee-1` | 0.70 | 1.132716 | 0.6992 | 7.427 | 0.02484 | 49.24% | 91.28% |
| MEASURED | `bee-1` | 0.50 | 6.048060 | 0.5023 | 80.140 | 0.26803 | 23.52% | 58.18% |
| MEASURED | `bee-2` | 0.90 | 0.268920 | 0.9021 | 1.508 | 0.00504 | 74.49% | 95.38% |
| MEASURED | `bee-2` | 0.70 | 1.124448 | 0.6997 | 7.917 | 0.02648 | 47.74% | 81.64% |
| MEASURED | `bee-2` | 0.50 | 4.855507 | 0.5022 | 78.141 | 0.26134 | 20.00% | 39.63% |
| MEASURED | `bee-3` | 0.90 | 0.300538 | 0.9037 | 1.519 | 0.00508 | 75.55% | 96.94% |
| MEASURED | `bee-3` | 0.70 | 1.514691 | 0.6987 | 12.265 | 0.04102 | 50.73% | 85.30% |
| MEASURED | `bee-3` | 0.50 | 9.279772 | 0.5019 | 74.635 | 0.24962 | 18.96% | 35.83% |

**MEASURED/DERIVED.** Raw gate spans are 1.139×, 1.347×, and 1.911× at
requests 0.90, 0.70, and 0.50. Confirmation spans are only 0.9015–0.9037,
0.6987–0.6997, and 0.5019–0.5023. Outcome normalisation is operational on
the new captures; that does not supply the missing sharpness price.

**MEASURED.** Every `dsig` centre is finite and every 512² cell has zero
container pins. All nine independent Python raw-RMS checks agree with the CLI
within 0.424%. Nevertheless every price is unreadable because its absolute
magnitude is below 0.343 px. A high corrected z on a below-null centre does
not override the separate null limb.

| Class | stack | request 0.90 px ± corrected SE | request 0.70 px ± corrected SE | request 0.50 px ± corrected SE | curve control |
| --- | --- | --- | --- | --- | --- |
| MEASURED | `bee-1` | +0.01116 ± 0.02632 | +0.02073 ± 0.01834 | +0.03318 ± 0.02654 | pass |
| MEASURED | `bee-2` | -0.02994 ± 0.00917 | -0.02862 ± 0.03285 | +0.08198 ± 0.01900 | pass |
| MEASURED | `bee-3` | +0.01992 ± 0.02075 | -0.01658 ± 0.04954 | -0.03523 ± 0.03369 | pass |

**MEASURED.** Primary corrected z values are 1.13, 0.87, and 0.33, all below
2. `bee-2` exceeds corrected z 2 at requests 0.90 and 0.50, but those centres
are still only 0.030 and 0.082 px in magnitude and fail the independent null
limb.

**MEASURED.** The transferred all-frame flat precondition passes only on
`bee-1`. It fails on `bee-2` and `bee-3`, whose transferred M80 cells both
return `N/A / NO TARGET`. Those M80 rows are UNREADABLE; their numerical
contents do not enter a claim.

| Class | stack | max flat contamination | flat precondition | M80 0.90 / 0.70 / 0.50 | M80 status |
| --- | --- | ---: | --- | --- | --- |
| MEASURED | `bee-1` | 1.066618 | pass | 1.000 / 0.999 / 0.990 | READABLE |
| MEASURED | `bee-2` | 3.117344 | fail | `N/A / N/A / N/A` | UNREADABLE |
| MEASURED | `bee-3` | 4.796492 | fail | `N/A / N/A / N/A` | UNREADABLE |

**MEASURED/ARGUED.** All nine whole-plane and local singleton percentages are
non-zero. Across the extension they span 18.96%–75.55% and
35.83%–97.96%, respectively. M82 makes no actual-noise floor claim.

## M82 §13 — Bee disposition and what it changes

**MEASURED/ARGUED.** The conditional bee-triple result is
`PREMISE_NOT_ESTABLISHED` because §11 fails before price is considered. If
physical comparability were assumed contrary to the registration, the
numerical result would still be `NOT ESTABLISHED`: all three primary prices
abstain. Their central signs are descriptive and do not constitute a readable
sign reversal.

**MEASURED.** The clean `bee-1-cpl` rerun has zero selected numerical
difference from the original ladder and confirmation aggregates. Its
sharpness JSON is byte-identical to the original; both have SHA-256
`086f6810c86ad3c2064a0a1c23051a1f5097f957bf259749b2a32b126abc5e7a`.
The rename therefore did not invalidate or change M82's original `bee-1` row.

**MEASURED/ARGUED.** The new captures expose two distinct limitations rather
than resolving either. Their through-focus breadth diverges enough that they
are not a controlled sibling triple, while their matched whole-plane requests
still leave 81.64%–91.28% local singleton exposure at the primary point. This
is consistent with M82's original spatial-admission mechanism, but the
unreadable price instrument forbids promoting it into a refutation.

**MEASURED.** The extension reran the required byte mutation after changing
the shared admission helper. `mutation-control-bee.log` records planted
read-back, exit 1 on the first admission assertion, and exact restoration.
The restored source and decision suites then pass.

**ARGUED.** The project decision remains: ship no automatic solver and no
named presets. The owner can treat the renamed directory as the same measured
`bee-1` capture, but cannot treat `bee-1`/`bee-2`/`bee-3` as an established
physical sibling control. A future three-capture control must first meet a
frozen comparability rule, then use a sharpness instrument with resolving
power below the effect it prices.

## M82 §14 — Candidate facts

| M82 namespace | Claim | Label | Evidence |
| --- | --- | --- | --- |
| **M82 P1** | A per-stack solver can reach requested shipped mean model-predicted sigma gains: all six 15-rung ladders are monotone and bracket 0.90, 0.70, and 0.50; all 18 confirmations finish within ±0.005, with one registered update on each of two points. | MEASURED | `ladder-results.json`; `confirm-results.json`; refinement logs |
| **M82 P2** | At request 0.70, raw gates span 22.176× across six stacks while achieved gain spans 0.6975–0.7015. The coordinate repairs the numerical scale of the knob, not its demonstrated price. | MEASURED/DERIVED | `confirm-results.json` |
| **M82 P3** | The wrapped-text primary central prices are +0.0790 and +0.0845 px, nominally 1.069× apart, but both are below M82's frozen 0.343 px bound from M57's measured null; sibling portability is NOT ESTABLISHED. | MEASURED/ARGUED | `sharpness-wrapped-text-*.json`; `results.json` |
| **M82 P4** | All 18 price rows abstain: 15 finite centres have maximum absolute magnitude 0.1754 px and three `foam` rows are `N/A`; no five-stack price span exists under the frozen decision. | MEASURED/ARGUED | `sharpness-*.json`; `results.json` |
| **M82 P5** | At globally matched request 0.70, local detail mean `n_eff` spans 1.026–2.623 and local singleton exposure spans 25.46%–97.41%; `coffee-bean` has whole-image mean `n_eff` 18.424 while 97.41% of its detail cell remains singleton. | MEASURED | `sharpness-*.json`; `results.json` |
| **M82 P6** | Every solved point retains whole-plane singleton exposure, 0.96%–76.84%; the actual single-frame noise floor remains unestablished. | MEASURED/ARGUED | `confirm-results.json`; `results.json` |
| **M82 P7** | M77's all-frame flat precondition fails on three of five required stacks and on the extra sibling; only `coffee-bean` and `bee-1` expose readable M80 companion rows. | MEASURED | `sharpness-*.json`; `results.json` |
| **M82 P8** | A fresh independent full-plane implementation matches Rust mean `n_eff` to 0.00380%; 16 of 18 target raw-RMS checks pass within 1%, and the two failures are pinned `foam` rows made unreadable by registration. | MEASURED | `validation.json`; `results.json` |
| **M82 P9** | Reversing the core admission comparison is detected by read-back and makes the announced self-test exit nonzero; exact byte restoration succeeds. | MEASURED | `mutation-control.log` |
| **M82 P10** | The portable-price-list hypothesis is neither passed nor refuted by M82. The executable product decision is NO SHIP / NOT ESTABLISHED, with no production solver or presets. | ARGUED from MEASURED | `PREREGISTRATION.md`; `results.json`; M82 §§4–9 |
| **M82 P11** | The original `bee-1` run was complete. Current `bee-1-cpl` reproduces selected ladder and confirmation values with zero numerical difference and reproduces the full sharpness JSON exactly. | MEASURED | original and `bee-*bee-1*` logs/JSON; `bee-results.json` |
| **M82 P12** | M70 had already measured all three bees. Fresh current-path responses reproduce its tracked full-precision aggregates exactly, but cross-bee spans of 1.0526× at ±5 and 1.1097× at ±10 exceed M82's frozen 1.05 physical line; bee sibling comparability is NOT ESTABLISHED. | MEASURED/ARGUED | M70 `s10_architecture.json`; `bee-physics.json` |
| **M82 P13** | All nine bee-extension requests confirm without refinement. At request 0.70, raw gates span 1.347× while gains span 0.6987–0.6997. | MEASURED/DERIVED | `bee-ladder-results.json`; `bee-confirm-results.json` |
| **M82 P14** | The three bee primary centres are +0.02073, -0.02862, and -0.01658 px; all are below the frozen 0.343 px null and unreadable. Even assuming comparability, bee price portability is NOT ESTABLISHED. | MEASURED/ARGUED | `bee-sharpness-*.json`; `bee-results.json` |
| **M82 P15** | At the bee primary points, whole-plane singleton exposure is 47.74%–50.73% and local detail singleton exposure is 81.64%–91.28%; no actual single-frame floor is established. | MEASURED/ARGUED | `bee-confirm-results.json`; `bee-results.json` |
| **M82 P16** | M82's amendment incorrectly called local ignored M70 NPZ intermediates committed. The durable prior targets are M70's tracked `s10_architecture.json` and log; M82's tracked current-path aggregates reproduce them exactly. | MEASURED | `git ls-files`; `.gitignore`; M70 `s10_architecture.*`; M82 §10 |

## M82 §15 — Reproduction, hashes and disposition

**MEASURED.** Original durable evidence is committed under
`experiments/M82-normalised-gate/`:

- frozen design: `PREREGISTRATION.md` and its separately committed
  `PREREGISTRATION-BEE.md` amendment;
- source-level reproduction and decision code: `m82lib.py`,
  `analyse_ladders.py`, `analyse_confirm.py`, `refine_confirm.py`,
  `apply_refinement.py`, `sharpness.py`, `validate_whole.py`, and `decide.py`;
- build and executable provenance: `build.log` and `binary.json`;
- six ladder logs and `ladder-results.json`;
- six initial confirmation logs, two refinement logs,
  `refinement-plan.json`, and `confirm-results.json`;
- six sharpness logs, six sharpness JSON files, `validation.json`, and
  `results.json`; and
- the byte-level negative control: `mutation_control.py` and
  `mutation-control.log`.

**MEASURED.** The amendment adds path-aware source and runners,
`bee_physics_measure.py`, `analyse_bee_physics.py`, the `analyse_bee_*`,
`refine_bee_*`, `apply_bee_refinement.py`, and `decide_bee.py` programs;
three physical logs and `bee-physics.json`; three ladder logs and their
aggregate; three confirmation logs, the zero-entry refinement plan, and their
aggregate; three sharpness logs and JSON files; `bee-results.json`; and
`mutation-control-bee.log`. The regenerated `bee-physics-bee-*.npz` files are
ignored local intermediates, matching M70's repository convention, and are
not durable evidence.

**MEASURED.** From the repository root, with Python encoding set before every
Python process, the measurement order is:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
& .\experiments\M82-normalised-gate\build.ps1
& .\experiments\M82-normalised-gate\run_ladders.ps1
python .\experiments\M82-normalised-gate\analyse_ladders.py
& .\experiments\M82-normalised-gate\run_confirm.ps1
python .\experiments\M82-normalised-gate\analyse_confirm.py
python .\experiments\M82-normalised-gate\refine_confirm.py
& .\experiments\M82-normalised-gate\run_refine.ps1
python .\experiments\M82-normalised-gate\apply_refinement.py
python .\experiments\M82-normalised-gate\validate_whole.py
& .\experiments\M82-normalised-gate\run_sharpness.ps1
python .\experiments\M82-normalised-gate\decide.py
```

**MEASURED.** With the preregistration amendment already committed, the bee
extension ran in this order:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python .\experiments\M82-normalised-gate\mutation_control.py `
  --log mutation-control-bee.log
& .\experiments\M82-normalised-gate\run_bee_physics.ps1
python .\experiments\M82-normalised-gate\analyse_bee_physics.py
& .\experiments\M82-normalised-gate\run_bee_ladders.ps1
python .\experiments\M82-normalised-gate\analyse_bee_ladders.py
& .\experiments\M82-normalised-gate\run_bee_confirm.ps1
python .\experiments\M82-normalised-gate\analyse_bee_confirm.py
python .\experiments\M82-normalised-gate\refine_bee_confirm.py
# run_bee_refine.ps1 plus apply_bee_refinement.py only if the plan has entries
& .\experiments\M82-normalised-gate\run_bee_sharpness.ps1
python .\experiments\M82-normalised-gate\decide_bee.py
```

**MEASURED.** Toolchain and library versions are Rust
`1.98.0 (88d9e12ae 2026-08-18)`, Cargo
`1.98.0 (797e8a9bc 2026-08-05)`, Python 3.12.10, NumPy 2.4.4, and SciPy
1.17.1.

**MEASURED.** Core hashes below are of worktree bytes in the recorded Windows
checkout:

| Class | artifact | SHA-256 |
| --- | --- | --- |
| MEASURED | private `strehl.exe` | `2f1ea8904240acca98937f4755354302b53a061c8791d677b721137e45c58a74` |
| MEASURED | `m82lib.py` at original evidence commit `543534e` | `8b5ca517e5bdff03ad633b63d92bbb3c0feac59c3cf11f1c4359c7804ee3525c` |
| MEASURED | current path-aware `m82lib.py` | `748fa208ca820b1f43799b55778399eea4191784d087c5d2ef1b734f2aa439be` |
| MEASURED | M57 `m57lib.py` | `1fc473069d854775e5abe427cf9e43e9e3abe4be704308163bf25f61025c744a` |
| MEASURED | `ladder-results.json` | `4d95f93dbdc4419c58373644dae30e7822a958bbeec99872574ece7195bd1c86` |
| MEASURED | `confirm-results.json` | `1092967d751459c2ff7874b43bb1c4812d11714f365685d390c9c86a8371e9b1` |
| MEASURED | `validation.json` | `aa28be46e593dd1867fab2e615aa7533dc0db514351ea950cfaa3a950caf95c5` |
| MEASURED | `results.json` | `3e95ff567b09b5b98ecac7d08e280c34a638e73e0e346ade6e907796af0e6b90` |
| MEASURED | `PREREGISTRATION-BEE.md` | `6575fb58ea30782cc03dfcca18c058bd64761f8205007ad063a07de751965699` |
| MEASURED | `bee-physics.json` | `70909409d92005f5d0b02e2a67786a5dd00e75e9d95af39a0993c9c2144606f2` |
| MEASURED | `bee-ladder-results.json` | `3201d54cd285b8cef2872a55a32e0195337b8d47f61f09aa24da409848f15c38` |
| MEASURED | `bee-confirm-results.json` | `66eaf253a569d43252aed928455a6b79b6a53731cec5feebf47f9bec4260471b` |
| MEASURED | `bee-results.json` | `8ceac2cb476c276b0d94d1a25a0f4946e55d190af6d52c0848807ebe3c69e067` |
| MEASURED | `mutation-control-bee.log` | `fdc2c971ec8d38f6fc8ce5cd458265269122087039b0236020e59ba229509a4a` |
| MEASURED | M70 tracked `s10_architecture.json` | `d091945bda60ae672dcb53056a7459306a55dda424e30d3c2c211ee406b9bf9c` |
| MEASURED | M70 tracked `s10_architecture.log` | `f82fadacdc20432d6785ebed9aee666b887143c21a7f7d72c1acfc4fd5b10152` |
| MEASURED | M77 five-stack ROI source | `0eae7a12aa959f9617fd4a1a09c85d17e58ed4a966fe7ab2af8a400132fc4290` |
| MEASURED | M77 sibling ROI source | `80b0bf0b07eb1d52ce3eb9efa57ec4d38b0e0db3c44e50a0a9f772da9661c748` |

**MEASURED.** The release build log contains fresh `Compiling strehl-core` and
`Compiling strehl-cli` lines and exits 0. The unmutated source tests pass 4/4,
the original and extension decision tests pass 4/4, the physical helper tests
pass 18/18, all 16 M82 Python programs parse in memory, all 20 JSON artifacts
parse, and the executable re-hashes to its recorded value. Original
evidence-time corpus lint checked 109 Markdown files and 30 Rust files; the
final amendment rerun also reports `OK — no violations`.

**MEASURED.** Evidence commit `543534e` contains exactly the 33 M82 result
artifacts. Amendment commit `1c2caee`, harness commit `0601788`, and bee
evidence commit `4ea2f1b` were each audited with `git show --name-only`;
the latter two contain exactly 23 and 22 M82 paths. No file under `crates/`,
`docs/research/SYNTHESIS.md`, `AGENTS.md`, or the M83 literature audit was
modified. The private target directory and NPZ intermediates remain
untracked, no generated executable is committed, and nothing was pushed.
