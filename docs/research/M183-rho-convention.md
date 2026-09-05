**Answer: C1 still flips after rho's grid and boundary convention are pinned.**
**Pinned result: rho = 0.00551650, scene-bootstrap 95% interval 0.00184706--0.01077932; KILL at the median, but NARROWED at field centre at the upper endpoint.**
**Disposition: C1 remains NOT ROBUST; the next preregistered decision is the target scene population and product risk functional, which the corpus does not contain.**

# M183-rho-convention: pinning the operational PHASE scalar

**Lane:** `experiments/M183-rho-convention/`
**Preregistration commit:** `014063e498a2f0a1faf627b7bb7534e3163e76cd`
**Status:** convention pinned; C1 remains blocked, for a narrower reason than
Amendment 8 states.

## 1. Deciding answer

**VERIFIED — the verdict still flips.** Under the preregistered convention, the
interval endpoints and point estimate read:

| rho read | field centre | inner annulus | corner |
|---|---:|---:|---:|
| 0.00184706, interval low | 5.00% KILL | 1.5625% KILL | 0% KILL |
| 0.00551650, median | 22.1875% KILL | 7.50% KILL | 1.25% KILL |
| 0.01077932, interval high | 37.1875% NARROWED | 16.875% KILL | 2.8125% KILL |

All values are produced by
`experiments/M183-rho-convention/src/analyze.py:366-422` and recorded at
`experiments/M183-rho-convention/out/result.json:81-177`. The field-centre
KILL/NARROWED transition is `rho = 0.00633340`
(`out/result.json:163-177`), inside the pinned interval. The other two radii do
not change class.

The additional **preregistered decision** needed for one product-level verdict
is: define the target scene population and its risk functional — for example,
whether C1 must pass the median scene, a stated upper quantile, or every scene
in a stated application class. That decision is **genuinely absent** from the
corpus. The six stored scene clusters can be recomputed under any declared rule,
but they do not license a general population weighting. The per-site joint
scene/frequency/conditioning census is computationally derivable but still
unrun (`experiments/M-PHASE0-PHASE/PREREGISTRATION.md:1408-1414`).

## 2. What rho is and where the old estimate came from

PHASE defines

```text
rho = E |x_k|^2 / E |x_0|^2,  k >= 1,
```

the expected power of **one alias component** relative to the base component
at the same output frequency
(`experiments/M-PHASE0-PHASE/PREREGISTRATION.md:489-497`). It is an input to
the alias-unfolding displacement-error simulator: lower rho means less alias
energy to recover and therefore a tighter registration bar; PHASE explicitly
models `bar(kappa,rho)` (`ibid.:495-503`).

M-PHASE0-RHO preserved the green quincunx, estimated a two-dimensional Welch
PSD, subtracted measured photon-plus-read noise, and fitted a power law with
even angular terms (`docs/research/M-PHASE0-RHO.md:45-53`). Its scalar is the
sum of designated alias powers divided by mean per-alias base power
(`ibid.:61-64`). Most accepted estimates remain model continuations: only
`9/46` passing records directly detect the high band above scene-to-noise three
(`ibid.:126-134`).

The old `0.0055165` point is the median of six f/5.6 scene-cluster values. The
`0.0018471--0.0107793` interval resamples those six clusters 10,000 times and
takes bootstrap percentiles 2.5 and 97.5
(`experiments/M-PHASE0-RHO/src/aggregate.py:46-84`;
`docs/research/M-PHASE0-RHO.md:16-18`). M183 repeats the same hierarchy, seed,
and draw count after changing only the boundary reduction
(`experiments/M183-rho-convention/src/analyze.py:234-278`;
`out/result.json:79-105`).

## 3. The 30.49x crux

**VERIFIED — one degree of freedom caused it: the resolution of the
cell-centred scalar quadrature, not Welch resolution, frequency units, or
spatial padding.**

The two endpoint conventions are:

* 8 by 8 cell centres over `[-0.5,0.5)^2`, 32 deduplicated green pairs:
  scene median `0.0055164975`;
* 32 by 32 cell centres over the same square, 512 deduplicated pairs:
  scene median `0.00018093468`.

Their ratio is `30.488889x`
(`experiments/M183-rho-convention/out/result.json:13-33`), reproducing the
original `0.0055165 / 0.0001809 = 30.49x`
(`docs/research/M-PHASE0-RHO.md:28-30`). The 16-grid midpoint is
`0.00096590448` (`out/result.json:21-27`).

Why it moves: refinement halves the nearest sampled base radius from
`0.08838835` to `0.04419417` to `0.02209709` sensor cycles/pixel
(`out/result.json:15-31`). The fitted scene model has median exponent
`beta = 4.433` (`docs/research/M-PHASE0-RHO.md:67-69`), so each refinement adds
much larger near-DC base power to the denominator. The old "refinement" was
therefore changing the scalar's output-frequency population while PHASE's
consumer stayed at `NU_GRID=8`
(`experiments/M-PHASE0-PHASE/src/p1_bar.py:40-44`). It was not a rounding
effect or a change in the measured PSD.

## 4. Candidate conventions found

The complete derived inventory and rejection reasons were committed before the
M183 computation (`experiments/M183-rho-convention/PREREGISTRATION.md:49-164`):

| axis | conventions present in the corpus |
|---|---|
| physical units | cycles/full-resolution sensor pixel; GQ-native `(fu,fv)` mapped by `/2`; cycles/photosite pitch; cycles/mm conversion |
| scalar grid | PHASE/RHO 8-cell-centred; RHO 16/32 cell-centred sensitivities; distinct 128/256/512 Welch DFT grids; exploratory radial bins; XSPEC 64/48/32 grids |
| endpoints | scalar cell centres omit DC and Nyquist edges; Welch `fftfreq` includes DC and negative Nyquist, while the fit excludes radius below 0.04 |
| green boundary | primary lower-radius/lexicographic label; swap; reciprocal average; exclude |
| spatial boundary | RHO periodic Hann primary; Kaiser-8 and 128/512 tile sensitivities; rectangular controls; XSPEC symmetric Hann; exploratory single Hann window |
| extent | fixed in-bounds square GQ crops, no padding/resampling; XSPEC's non-power-of-two 48 grid leaves unused samples |

No real-RHO zero-pad, reflected-pad, edge-sampled scalar quadrature, continuum
integral, or DC/Nyquist half-weight rule exists in the corpus. Reflection occurs
only in an XSPEC synthetic generator. Inventing one would also require an
unregistered low-frequency loss/cutoff, because the RHO fit excludes radius
below `0.04` while refined scalar grids approach DC
(`PREREGISTRATION.md:91-109`).

## 5. Preregistered convention and justification

Before computation, M183 committed:

1. **frequency:** cycles/full-resolution sensor pixel on PHASE's exact 8 by 8
   cell-centred grid, half-open Nyquist square, reciprocal pairs deduplicated;
2. **alias boundary:** average both reciprocal assignments on exact green
   diamond ties;
3. **spatial boundary:** retain the commissioned in-bounds, square,
   256-square, 50%-overlap periodic-Hann Welch fit with no padding or
   resampling.

The choice and verdict-independent rationale are at
`experiments/M183-rho-convention/PREREGISTRATION.md:166-202`. The 8 grid is the
consumer's actual population, not the answer-favouring grid. Reciprocal
averaging removes an arbitrary coordinate label on a shared Brillouin boundary.
Hann-without-padding suppresses the periodisation seam without inventing
samples.

The boundary result is informative: primary, swap, and average agree to
floating precision at `0.00551650`; excluding all eight boundary groups instead
gives `0.00278320` with interval `0.00081994--0.00595654`
(`experiments/M183-rho-convention/out/result.json:35-76`). Thus the
coordinate-label choice was harmless on this complete symmetric grid, but
discarding 25% of its groups was not.

## 6. Computation and C1 mapping

`src/analyze.py` independently re-evaluates each stored accepted fit's `beta`
and angular terms on the pinned grid (`:83-200`), takes record medians within
the five ordinary scenes and independent bee repeat (`:210-257`), and applies
the original 10,000-draw scene bootstrap (`:259-278`). It reproduced all 19
stored primary and boundary-average record values with maximum relative errors
`5.86e-16` and `7.03e-16`
(`experiments/M183-rho-convention/out/result.json:180-185`).

For C1, the script reads the 320 G-1x, zero-mean, noiseless PHASE curves,
requires each to be monotone, interpolates `log(bar)` in `log(rho)`, and applies
the filed `<25% / 25--<60% / >=60%` KILL/NARROWED/SURVIVE thresholds
(`src/analyze.py:320-422`;
`experiments/M-PHASE0-PHASE/src/p8_verdict.py:108-141`). No aligner number was
changed.

## 7. Instrument commissioning

**VERIFIED — PASS 10 / FAIL 0 known-answer controls; CAUGHT 4 / MISSED 0
deliberate mutations**
(`experiments/M183-rho-convention/out/commission.txt:1-2`).

* Null white spectrum read exactly `1.0`; the known `0.04` plant read
  `0.040000000000000015`.
* The raise arm read `0.08` (`2.0x`) and the lower arm `0.02` (`0.5x`).
* The inert common-power `7x` arm did **not** move rho.
* Exchanging every ambiguous pair did **not** move the averaged boundary read.
* An independent rational enumerator agreed on 32 pairs / 8 ambiguous.
  (`out/commission.json:12-58`.)
* Unique full-line mutations of grid `8 -> 16`, frequency scale `1 -> 2`,
  average boundary to primary, and ratio inversion were all caught by their
  intended controls, without exception-based catches
  (`out/commission.json:89-125`;
  `src/commission.py:222-282,323-356`).

The separate checker re-aggregated stored per-fit values and PHASE endpoint
fractions without importing the estimator, verified that the preregistration
commit contains only its one file, and reports **PASS 6 / FAIL 0**
(`experiments/M183-rho-convention/out/verify.txt:1`;
`src/verify.py:202-274`).

These controls support the arithmetic, grid, directionality, and mutation
sensitivity. They do **not** make six selected scenes a representative product
population or validate the power-law continuation beyond directly separable
support.

## 8. Contradictions to Amendment 8 section 18.5

The disposition "C1 remains blocked" is upheld, but two statements in section
18.5 are wrong or too strong:

1. It says the measured interval contains **SURVIVE**
   (`docs/proposals/2026-08-sota-path.md:3003-3008`). It does not. The source
   says the measured interval reaches NARROWED at `rho=0.01`; SURVIVE occurs at
   `rho=0.06`, the top of the wider design census
   (`experiments/M-PHASE0-PHASE/PREREGISTRATION.md:1385-1398`).
2. It says the decidable quantity is grid/boundary and not the aligner. M183
   pins grid/boundary and the measured scene interval **still crosses** the
   field-centre class boundary. Grid/boundary was a blocker, but not the sole
   blocker. The absent scene-population risk rule and the already-owed per-site
   joint census remain.

## 9. What would make me wrong

* **Wrong consumer:** if C1 will not consume the 8-grid population represented
  by `p1_bar.py`, this pins an audit instrument, not the future product. A
  continuum consumer needs its own preregistered loss weighting and matched
  PHASE rerun.
* **Wrong boundary physics:** a physical base-member role independent of
  reciprocal coordinates would invalidate boundary averaging. None is defined
  in A2.2.
* **Wrong spectrum model:** only `9/46` records directly detect the high band;
  optical-cutoff or model-form error is outside this bootstrap.
* **Wrong population:** the interval covers sampling among six selected scene
  clusters, not sensors or all macro subjects. More representative scenes may
  move or narrow it.
* **Wrong C1 substrate:** PHASE itself records that the preregistered per-site
  joint census remains unrun; that future result can supersede the marginal
  winnable fractions used here.

## 10. Reproduction

From the repository root:

```text
python experiments/M183-rho-convention/src/commission.py
python experiments/M183-rho-convention/src/analyze.py
python experiments/M183-rho-convention/src/verify.py
```

The analysis refuses changed input or instrument hashes after commissioning
(`experiments/M183-rho-convention/src/analyze.py:425-448`).
