# M82 — outcome-normalised gate

**VERDICT — MEASURED/ARGUED: NO SHIP; A PORTABLE SHARPNESS PRICE LIST IS
NOT ESTABLISHED, NOT REFUTED.** The requested coordinate is operational: all
six fresh 15-rung ladders are monotone, all three requested model-predicted
sigma gains are bracketed, and all 18 solved points confirm within the frozen
±0.005 bar. The price instrument is not operational at the resulting points.
All 18 M57 `dsig` rows are unreadable under the rule committed before the
measurement: 15 finite central estimates have maximum absolute magnitude
**0.1754 px**, only 51.1% of M82's frozen **0.343 px** bound taken from
M57's measured independent-noise null, and all three `foam` rows return
`N/A`. No unreadable central value is promoted into a span.

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
and evidence commit `543534e`.

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

## M82 §10 — Candidate facts

| M82 namespace | Claim | Label | Evidence |
| --- | --- | --- | --- |
| **M82 P1** | A per-stack solver can reach requested shipped mean model-predicted sigma gains: all six 15-rung ladders are monotone and bracket 0.90, 0.70, and 0.50; all 18 confirmations finish within ±0.005 after two points each require one registered update. | MEASURED | `ladder-results.json`; `confirm-results.json`; refinement logs |
| **M82 P2** | At request 0.70, raw gates span 22.176× across six stacks while achieved gain spans 0.6975–0.7015. The coordinate repairs the numerical scale of the knob, not its demonstrated price. | MEASURED/DERIVED | `confirm-results.json` |
| **M82 P3** | The wrapped-text primary central prices are +0.0790 and +0.0845 px, nominally 1.069× apart, but both are below M82's frozen 0.343 px bound from M57's measured null; sibling portability is NOT ESTABLISHED. | MEASURED/ARGUED | `sharpness-wrapped-text-*.json`; `results.json` |
| **M82 P4** | All 18 price rows abstain: 15 finite centres have maximum absolute magnitude 0.1754 px and three `foam` rows are `N/A`; no five-stack price span exists under the frozen decision. | MEASURED/ARGUED | `sharpness-*.json`; `results.json` |
| **M82 P5** | At globally matched request 0.70, local detail mean `n_eff` spans 1.026–2.623 and local singleton exposure spans 25.46%–97.41%; `coffee-bean` has whole-image mean `n_eff` 18.424 while 97.41% of its detail cell remains singleton. | MEASURED | `sharpness-*.json`; `results.json` |
| **M82 P6** | Every solved point retains whole-plane singleton exposure, 0.96%–76.84%; the actual single-frame noise floor remains unestablished. | MEASURED/ARGUED | `confirm-results.json`; `results.json` |
| **M82 P7** | M77's all-frame flat precondition fails on three of five required stacks and on the extra sibling; only `coffee-bean` and `bee-1` expose readable M80 companion rows. | MEASURED | `sharpness-*.json`; `results.json` |
| **M82 P8** | A fresh independent full-plane implementation matches Rust mean `n_eff` to 0.00380%; 16 of 18 target raw-RMS checks pass within 1%, and the two failures are pinned `foam` rows made unreadable by registration. | MEASURED | `validation.json`; `results.json` |
| **M82 P9** | Reversing the core admission comparison is detected by read-back and makes the announced self-test exit nonzero; exact byte restoration succeeds. | MEASURED | `mutation-control.log` |
| **M82 P10** | The portable-price-list hypothesis is neither passed nor refuted by M82. The executable product decision is NO SHIP / NOT ESTABLISHED, with no production solver or presets. | ARGUED from MEASURED | `PREREGISTRATION.md`; `results.json`; M82 §§4–9 |

## M82 §11 — Reproduction, hashes and disposition

**MEASURED.** Durable evidence is committed under
`experiments/M82-normalised-gate/`:

- frozen design: `PREREGISTRATION.md`;
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

**MEASURED.** Toolchain and library versions are Rust
`1.98.0 (88d9e12ae 2026-08-18)`, Cargo
`1.98.0 (797e8a9bc 2026-08-05)`, Python 3.12.10, NumPy 2.4.4, and SciPy
1.17.1.

**MEASURED.** Core hashes are:

| Class | artifact | SHA-256 |
| --- | --- | --- |
| MEASURED | private `strehl.exe` | `2f1ea8904240acca98937f4755354302b53a061c8791d677b721137e45c58a74` |
| MEASURED | `m82lib.py` | `8b5ca517e5bdff03ad633b63d92bbb3c0feac59c3cf11f1c4359c7804ee3525c` |
| MEASURED | M57 `m57lib.py` | `1fc473069d854775e5abe427cf9e43e9e3abe4be704308163bf25f61025c744a` |
| MEASURED | `ladder-results.json` | `4d95f93dbdc4419c58373644dae30e7822a958bbeec99872574ece7195bd1c86` |
| MEASURED | `confirm-results.json` | `1092967d751459c2ff7874b43bb1c4812d11714f365685d390c9c86a8371e9b1` |
| MEASURED | `validation.json` | `aa28be46e593dd1867fab2e615aa7533dc0db514351ea950cfaa3a950caf95c5` |
| MEASURED | `results.json` | `3e95ff567b09b5b98ecac7d08e280c34a638e73e0e346ade6e907796af0e6b90` |
| MEASURED | M77 five-stack ROI source | `0eae7a12aa959f9617fd4a1a09c85d17e58ed4a966fe7ab2af8a400132fc4290` |
| MEASURED | M77 sibling ROI source | `80b0bf0b07eb1d52ce3eb9efa57ec4d38b0e0db3c44e50a0a9f772da9661c748` |

**MEASURED.** The release build log contains fresh `Compiling strehl-core` and
`Compiling strehl-cli` lines and exits 0. The unmutated source tests pass 4/4,
the decision tests pass 4/4, all nine M82 Python programs compile in memory,
all 12 JSON artifacts parse, and the executable re-hashes to its recorded
value. Final corpus lint checks 109 Markdown files and 30 Rust files and
reports `OK — no violations`.

**MEASURED.** Evidence commit `543534e` contains exactly the 33 M82 result
artifacts. No file under `crates/`, `docs/research/SYNTHESIS.md`, `AGENTS.md`,
or the M83 literature audit was modified. The private target directory remains
untracked, no generated binary is committed, and nothing was pushed.
