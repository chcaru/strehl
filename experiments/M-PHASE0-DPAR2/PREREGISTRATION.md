# M-PHASE0-DPAR2 — PRE-REGISTRATION

Written before any DPAR2 plant, dose response, power estimate, or verdict was
computed. I had already read the published M6 result and M103's measured track:
the real S2 values, the linear P1 value (`rho=-0.706`, `p=0.0104`), and the
46.1-plane-px departure of the independent RAW track from its chord are known.
They are prior evidence and commissioning targets, not DPAR2 results.

## 1. Question and fixed primary population

C4c asks whether per-tile alignment residuals contain a depth-conditioned radial
magnification term that one similarity per frame cannot absorb. DPAR2 measures
the minimum physical amplitude at which **M6's existing S2 statistic** detects
that term when its frame dependence follows M103's measured curved breathing
track.

The fixed primary population is M6 `119MSDCF`: M6 pre-identified it as the
strongest real-stack test (33 frames, depth SD 6.83 frames, all 96 labels usable,
S1 identification 0.675). `109MSDCF` and `coffee-bean` are fixed secondary
replications and cannot replace a failed primary after results are seen.

Inputs are read-only:

* `experiments/m6-residual-halo/data/<stack>-{tiles,focus,fits}.csv`;
* `experiments/M103-halfdrift/data/truth-dense.json`;
* M6's unchanged `m6_lib.py`.

No RAW capture is modified and no output is written outside this lane.

## 2. Curved physical plant

Let `ell(k)` be piecewise-linear interpolation of M103's independently measured
`ln(scale)` ladder after mapping target frame `k in [0,n-1]` to
`j=298*k/(n-1)`. It is **not** a polynomial fit or a line through the endpoints.
For pair `p=(ref,mov)`,

```text
q_p = [ell(mov)-ell(ref)] /
      median_k |ell(k+1)-ell(k)|.
```

Thus `q_p` retains M103's measured acceleration while amplitude has a physical
unit independent of stack length. For accepted tile observation `i,p`, radius
`r_i` is measured from M6's fitted scale centre and

```text
wbar_p = sum_i(r_i^2*w_i) / sum_i(r_i^2)
d_rad(i,p) = A * q_p * (w_i-wbar_p) * r_i/1000.
```

`d_rad` is added along the radial unit vector to M6's measured `(ex,ey)`.
The `r^2` centring makes the planted field orthogonal to the one global scale
basis in every pair, so it is explicitly the residual **beyond** a similarity.
`A` is plane px per one depth-index step at radius 1000 plane px for a pair
whose adjacent curved-track increment is the median. At radius 2000 the same
dose is `2A`.

The exact amplitude ladder (px/depth-step at radius 1000) is:

```text
0, 0.010, 0.015, 0.020, 0.0269, 0.035, 0.045, 0.0538,
0.070, 0.090, 0.120, 0.160, 0.220, 0.300, 0.450, 0.600, 0.900
```

It includes the audited M6 P1 regime (0.0269 at radius 1000, 0.0538 at radius
2000) and extends through and beyond C4c's predicted 0.3/0.6 at those radii.

## 3. Statistic, randomisation, and minimum detectable amplitude

The statistic is unchanged M6 S2:

1. project `(ex,ey)` radially about the fitted scale centre;
2. divide by radius to obtain `dg`;
3. demean `dg` within frame pair;
4. average by tile;
5. Spearman-correlate mean `dg` with measured winner index `w`;
6. use M6's 95 non-identity 12x8 torus shifts for the two-sided randomisation
   `p_torus`.

The predicted sign is **negative** under M6's frame/depth convention. A replicate
detects only when `rho(dg,w)<0` and `p_torus<=0.05`.

Power is conditional randomisation power over all 96 spatial phases: identity
plus every non-identity torus shift of `w`. In each replicate the shifted depth
field drives both the plant and the statistic while the complete measured
residual field is untouched. This preserves depth smoothness, residual
autocorrelation, pair structure, censoring, and the real noise distribution.

The **MDA80** is the smallest registered rung with at least 80% detections and
at least 80% at every higher rung. Uncertainty is a paired 10,000-draw bootstrap
of the 96 phases (all doses for a phase resampled together), seed `20260902`;
the 2.5/97.5 percentiles of the discrete crossing are the 95% interval. The
Wilson interval on detection probability at MDA80 is also reported.

## 4. Decision bar fixed before measurement

All controls below must pass.

* **SURVIVE:** unplanted primary M6 S2 itself has the predicted negative sign
  and `p_torus<=0.05`.
* **KILL:** otherwise, the upper endpoint of the primary MDA80 95% interval is
  `<=0.300 px/depth-step at r=1000` (equivalently `<=0.600` at `r=2000`).
  This demonstrates power at the proposal's weakest predicted amplitude.
* **NOT ROBUST / UNDERPOWERED:** neither condition holds, any commissioning
  control fails, or the analytic and estimator-read transfer checks disagree
  across the 0.300 bar. State the capture/design needed to settle it.

Whether MDA80 reaches the much smaller audited P1 regime is reported separately;
failure there does not turn a demonstrated exclusion of C4c's stated prediction
into underpowering.

## 5. Commissioning and fixed external predicate

Commissioning runs and is saved before the power ladder is accepted.

1. **C1 — cancellation-immune curved-track predicate.** Independently parse
   M103 `truth-dense.json` and compare it to fixed published facts that this
   lane cannot rewrite: deviation from its endpoint chord must be 45.5–46.7
   plane px with the maximum at `j=200`; absolute mean `ln(scale)` rates over
   0–96, 96–192, 192–298 must fall respectively in
   `[0.00028,0.00032]`, `[0.00049,0.00053]`, `[0.00069,0.00075]` per frame and
   be strictly increasing. A straight chord must fail these predicates. This
   control's expected values come from `docs/research/M103-halfdrift.md`, not
   from the plant generator or S2.
2. **C2 — what the estimator reads at full presence.** Re-run unchanged M6 S2
   on existing image-generated controls. `P1-both/measured-w` must reproduce
   the estimator's achieved `rho=-0.706 +/- 0.005`, `p=0.0104`; it is not scored
   against the unattainable ideal `rho=-1`. `P2-blur-only/measured-w` must
   reproduce `rho=-0.099 +/- 0.005` and remain non-significant.
3. **C3 — external scalar fixture.** A separate truth factory that does not
   import S2 supplies literal curved pair factors `[-0.5,-1,-2]`, depths
   `[-1,+1]`, and radii `[1000,2000]` at `A=0.300`. The plant applicator must
   return the precomputed radial values
   `[+0.150,-0.300,+0.300,-0.600,+0.600,-1.200]` px in that order. Mutating the
   applicator to a straight unit factor must make the check fail.
4. **C4 — similarity and channel wiring.** For every primary pair at maximum
   dose, `|sum(r_i*d_rad_i)| / sum(|r_i*d_rad_i|) <= 1e-10`; tangential
   displacement changes by at most `1e-10` px. At dose zero `(ex,ey)` is
   bit-identical.
5. **C5 — null and expressiveness.** Zero-dose false detection over the 96
   phases must be <=10%. The mapped primary curved track must have nonzero
   adjacent-increment CV and differ from its endpoint chord; the chord mutation
   must make adjacent-increment CV `<1e-12`.

## 6. Bias directions declared before measurement (rule 18)

I prefer **KILL** because a similarity-only pipeline is cheaper. The dangerous
error is therefore an optimistic power claim.

| source | direction | handling |
|---|---|---|
| smooth radial scene structure can correlate with smooth depth | favours KILL through a false detection | all 96 torus phases and zero-dose false-positive bar |
| injecting after tile correlation bypasses dose-dependent rejection/peak loss | favours KILL by understating MDA | preserve M6's actual accepted rows; require C2 estimator-read transfer and label the resulting MDA conditional on M6's residual reader |
| rank correlation saturates below the physical truth | favours UNDERPOWERED/KILL depending on where an ideal ceiling is assumed | score C2 against the observed `-0.706`, never against `-1`; use detection probability, not recovered rho as amplitude |
| pairwise curvature can change temporal weighting relative to a linear plant | either direction | measured M103 ladder enters every planted pair; chord is a deliberate failing mutation |
| 119MSDCF was selected as M6's best stack | favours KILL relative to an arbitrary future stack | fixed from M6 before DPAR2; both weaker stacks are disclosed, not substituted |
| conditioning on one observed residual field omits capture-to-capture variance | favours KILL | verdict is scoped to M6; new reversed-rack, deep planar/depth-target repeats are required if the 0.300 bar is not cleared |

The residual-level injection measures the sensitivity of the exact statistic
that produced M6's null. It does not claim to commission a future image warp or
to measure capture-to-capture prevalence.
