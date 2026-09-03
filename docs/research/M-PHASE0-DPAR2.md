# M-PHASE0-DPAR2 — curved-track power of the DPAR null

**Status: MEASURED. Verdict: KILL C4c's stated 0.3–0.6 px/depth-step
prediction.** This does not alter M6's blur result; it repairs only the
sensitivity argument that an audit rejected.

The design and exact ladder were committed before measurement at
`e27e3dd84bc62b40af17daca8c21a93f912b8a2e`. Executable records are
`experiments/M-PHASE0-DPAR2/out/commission.json` and `measurement.json`.

## Headline

On preregistered primary `119MSDCF`, the registered-grid **MDA80 is at most
0.010 plane px per depth-index step at radius 1000 plane px** (0.020 at radius
2000). The first nonzero rung already detected in **96/96** preserved-noise
torus phases (Wilson 95% interval **[0.9615, 1.0000]**), so the ladder gives an
upper bound rather than a lower-bracketed continuous threshold. The paired
10,000-draw phase bootstrap puts the discrete crossing at
**0.010 [0.010, 0.010]** px/step.

That clears both relevant regimes:

| physical amplitude | primary detections | identity S2 | reading |
|---|---:|---:|---|
| zero | 3/96 (3.125%) | `rho=+0.1352`, `p=0.4896` | null |
| 0.010 / 0.020 px at r=1000/2000 | 96/96 | `rho=-0.8386`, `p=0.0104` | MDA80 rung |
| **0.0269 / 0.0538** (audited M6 P1 regime) | **96/96** | `rho=-0.9630`, `p=0.0104` | reached |
| **0.300 / 0.600** (C4c prediction) | **96/96** | `rho=-0.9959`, `p=0.0104` | cleared by 30x |

Secondary MDA80s were `0.015 [0.015,0.020]` on `109MSDCF` and
`0.010 [0.010,0.010]` on `coffee-bean`; neither was allowed to replace the
primary.

## What was repaired

M6's image plant used `g_k=gstep*k`. M103 later measured that the independent
RAW breathing track departs its chord by 46.1 plane px and accelerates
0.00030 -> 0.00051 -> 0.00072 `ln(scale)` per frame. Rule 6 therefore makes the
linear plant non-transferable.

DPAR2 instead maps M103's 39 measured `ln(scale)` rungs onto each stack's
normalised focus axis by piecewise-linear interpolation. For pair `p`,

```text
q_p = [ell(mov)-ell(ref)] / median |Delta ell adjacent|
d_rad(i,p) = A*q_p*(w_i-wbar_p)*r_i/1000,
wbar_p = sum(r_i^2*w_i)/sum(r_i^2).
```

The primary adjacent-increment CV is **0.4249**, versus
`1.25e-15` for the deliberately failing straight chord. The `r^2` centring
makes the plant orthogonal to a global scale fit in every pair; it is the
depth-conditioned residual that one similarity cannot absorb, not another
global scale.

The statistic is unchanged M6 S2: radial residual divided by radius, pair
demean, tile mean, Spearman correlation with measured focus winner, and the
95-shift spatial torus null. Detection required the predicted negative sign and
M6's two-sided `p_torus<=0.05`. Power enumerates all 96 relative spatial phases
of the intact measured residual field and depth field. This preserves the real
noise, spatial autocorrelation, pair structure, and M6 censoring.

## Commissioning

All six controls passed before the nonzero ladder was accepted:

| control | measured unmodified path | failing input |
|---|---|---|
| **C1 fixed external M103 predicate** | chord departure **46.0921 px at j=200**; rates `0.00030199/0.00050876/0.00072002` | a straight chord read 0 px and equal `0.00051730` rates, RED |
| **C2 estimator-read ceiling** | existing image-generated P1 read `rho=-0.705963`, `p=0.0104`; P2 read `-0.099492`, `p=0.2813` | symmetric-blur P2 remained quiet |
| **C3 literal scalar oracle** | `[+0.15,-0.30,+0.30,-0.60,+0.60,-1.20]` px, exact | replacing curved factors by `-1` disagreed, RED |
| C4 beyond-similarity/radial wiring | worst scale-basis inner-product ratio `5.75e-15`; tangential change `9.29e-14` px; zero bit-identical | maximum dose moved vectors by 887.97 px, so no-op cannot pass |
| C5 null/expressiveness | zero false detection 3/96; curved CV 0.4249 | chord CV `1.25e-15` |
| C6 accelerated evaluator | three fixed cases matched unchanged M6 S2 to `2.22e-16` in rho and exactly in p | independent unchanged function was the comparator |

C1 is cancellation-immune: its answer was published by M103 and comes from a
RAW truth ladder this lane neither generated nor modifies. C2 deliberately
checks what M6's estimator **actually read** at full presence (`-0.706`), not
the ideal rank ceiling of `-1`.

## Interpretation and scope

The unplanted primary remains quiet and has the wrong sign
(`rho=+0.1352`, `p=0.4896`). Its curved-track MDA80 upper bound is 30 times below
the proposal's weakest stated amplitude, and it also reaches the audit's much
smaller 0.0269/0.0538 regime. Under the preregistered rule this is **KILL**:
M6's null excludes C4c's stated depth-conditioned residual on these data.

No Rust file changes. A depth-conditioned warp would add complexity for an
effect the commissioned residual reader would have detected and did not.

**Limits / not verified.** The result is conditional sensitivity of M6's
post-correlation residual statistic on three existing stacks. The plant is
inserted after tile correlation, so it does not measure dose-dependent upstream
tile rejection or capture-to-capture prevalence; that choice biases the MDA
downward and was declared before measurement. C2 supplies an image-generated
estimator-read check, but its historical plant is linear. DPAR2 therefore
licenses the stated M6 residual null, not a claim that every lens/capture lacks
all smaller or differently shaped depth-dependent terms. The continuous MDA
below 0.010 is unresolved because the preregistered ladder has no rung between
zero and 0.010.

An independent ultra verifier reran both commands, recomputed the M103
curvature, all 17 powers and Wilson intervals, the MDA crossing and 10,000-draw
bootstrap, and the per-pair scale orthogonality without trusting this note. It
reported VERIFIED with no defects.

## Reproduction

```powershell
cd C:\dev\blog\death-of-software\projects\strehl
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH=(Get-Location).Path
python -B experiments\M-PHASE0-DPAR2\src\commission.py
python -B experiments\M-PHASE0-DPAR2\src\measure.py
```

Both commands exit nonzero on a failed commission/refusal. Inputs are
content-hashed in `commission.json` and per-stack in `measurement.json`.
