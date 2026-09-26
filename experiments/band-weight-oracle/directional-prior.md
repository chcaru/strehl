# Directional and phase-sensitive prior audit

2026-09-26, read-only. **Directional complex fusion has already reached both the
actual original-CFA consumer and a complete photograph here.** The early
`green-match-rgb/directional-route-review.md` absence finding is superseded by
the later experiments below. My initial message stopping at the boundary cost
failure was incomplete; the parallel continuation subsequently completed.
No new run, source/model download or implementation is recommended by this audit.

| Mechanism | Exact existing evidence and conclusion |
|---|---|
| Green-guided separable complex H/V/D fusion | `complex-wavelet-merge/results.md` and `results-review.md`: original u16, identity gather, one level. Neutral-direction and varying-focus colour guards failed at ISO100/400; green direction could not justify differently oriented R/B detail. |
| All-CFA directional energies, two levels | `all-cfa-wavelet/results.md`: original CFA identity and composed variance controls passed; 32-case screen rejected coarse detail. Seven other scene purposes passed. |
| Complete all-CFA complex transform to DC | `complete-cfa-wavelet/results.md`: all 32 periodic cases passed; baseline had fewer actual levels and a larger averaged base, so this did not isolate basis from depth/ramp. |
| Natural boundary plus actual fractional gather | `boundary-cfa-wavelet/results.md`: four original planes, reflected extension, actual GPU rounded MHC/Catmull gather and eight original-noise pairs. Relative RGB/boundary guards passed, but fractional weak-red focused-source retention and required benefit missed the frozen gate. |
| Complete real directional photograph | `parallel-cfa-wavelet/results.md`, `photographic-review.md`: the numerical/parallel repair preserved the old failed gate, then completed all 70 vitamin-C sources in 1253.844s. Exact baseline pixels; both 6920x4612 RGB16 masters retained. Independent whole/native review rejected broader coloured highlight smears, green/magenta intrusion and no compensating detail gain. No second scene or GPU optimization follows from this result. |
| Alleged earlier directional-detail experiment | `docs/research/M189b-directional-detail.md`: an anisotropic sharpening counterexample to a radial-bin quality metric. It is not a fusion experiment or a native source-selection test. |

The full-wavelet command was
`python -I -B -X faulthandler experiments/parallel-cfa-wavelet/full-run.py full
--build experiments/parallel-cfa-wavelet/build-1 --screen
experiments/parallel-cfa-wavelet/controls-1 --cost
experiments/parallel-cfa-wavelet/cost-1 --out
experiments/parallel-cfa-wavelet/full-1`.
The photographic report binds candidate SHA256
`0b3e50438b3215513234713862716a4bd4c50cc6a4ca6c9428f2b17a5edab9d6`.
These are prior measured/reviewed results, not new image judgments by this audit.

## What phase distinction remains

**VERIFIED from the actual fold:** boundary/parallel complex source weights use
smoothed sums of squared complex magnitudes across WB-scaled CFA planes and
their propagated floors. They retain each complex coefficient's phase during
weighted reconstruction, but do not test agreement of phases between sources,
or predict fine phase from coarser phase. They use the commissioned separable
complex transform; calling this a six-orientation dual-tree trial is unsupported.

The scalar phase/trajectory neighbourhood is nevertheless not unexplored:

- `docs/research/M-PHASE0-XSPEC.md` measured real green-quincunx complex
  through-focus spectra. Final verdict **NOT ROBUST**, not permanent KILL, because
  population/alternate-grid floor requirements failed. Nominal inversion was
  not enriched at the independent occlusion mask versus its shifted placebo;
  no phase-sign merge hook was built. This is adverse evidence, not a passed cue.
- `through-focus-events/results.md` and `results-review.md` measured all 70
  sources through actual gather. Signed finest-Laplacian box traces changed sign
  after one-quad translation and missed real ridge continuation. Signed RAW-DN
  association mainly followed common late brightening and did not replicate at
  the facet. A generic signed-L0 ownership rule is closed.
- `raw-affinity-support/results.md` actually consumed signed consecutive
  four-plane changes as spatial affinity: only 3 of 13 cases passed, with two
  unexercised positives retained and a failed no-glint stable-light twin. This is a tested trajectory-driven
  support rule; merely naming signed temporal information is not a new direction.
- `raw-affinity-support/next-motion-audit.md` proposed, but did not execute, local
  complex-band normal motion. It explains the decisive ambiguity: changing
  amplitudes of two stationary components rotates their summed phase without
  geometric motion. Moving ridge sides and residual placement also confound
  ownership. That earlier proposal cannot be presented as a fresh discovery.
- `real-source-contributions/independent-results.md` gives exact signed
  reconstruction accounting, but its fixed five-point profiles did not establish
  stable captured hairs that the merge loses. It does not justify sign rejection
  or a new source interval. `source-gradient-target/results.md` also rejects its
  fixed source-gradient target on contact error; it was not a phase-weight test.

Potts/shared-source fields, harmonic spatial agreement, R/B-own energies and the
new learned guide differ from cross-scale phase prediction: they regulate source
memberships or use intensity/energy/floor features. None makes a valid
inter-source phase or physical ownership claim. Their failures remain separate.

## Literature distinction and next decision

The primary [Hassen, Wang and Salama paper (2009)](https://ece.uwaterloo.ca/~z70wang/publications/iciar09.pdf)
uses local cross-scale phase prediction in a complex steerable pyramid to
distinguish sharpness from contrast. That information is different from squared
band energy and from temporal signed-box correlation. Its fusion rule then
elects a phase donor and boosts magnitude using a separately elected energy
donor. That rule is not suitable to copy into this noise-aware radiance consumer;
its image evidence does not establish deep RAW occlusion safety. Its phase
predictor also cannot be transferred verbatim onto the existing separable
complex transform without commissioning the different phase/scale geometry.
Only the paper was read; no EPFL/GPL implementation source was opened.

**ARGUED priority:** no additional phase experiment now. The root's separately
commissioned free nonnegative band-weight oracle is the inexpensive distinct
diagnostic to do first. It tests whether this held CFA/base/hull/MHC feasible set
can meet the actual seven-case preservation/benefit score at all, independent of
the failed predictor's features. A feasible witness would establish headroom,
not a deployable predictor; an optimizer failure would not prove infeasibility.
Only evidence of achievable headroom would warrant choosing one new information
channel such as cross-scale phase prediction. This audit nominates no parameter
rescue, generic coherence gate, alternate wavelet basis or whole-image rerun.

Mechanical prior searches executed with separate tokens:
`python -B experiments/ORCH-drift-check/prior_art.py complex wavelet phase coherence trajectory`
and `python -B experiments/ORCH-drift-check/prior_art.py signed band phase consistency`,
followed by the exact canonical reports and fold code named above. Archived
source-tree duplicates were not used as authority. Search absence for a
cross-scale phase-weight consumer is bounded to that record, not proof that the
idea is novel or that it will work.
