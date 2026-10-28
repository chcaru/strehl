# Saved-stage audit: CFA fusion and final RGB completion

**VERIFIED:** the saved audit completed all ten fixed cases, twenty original
sources and twenty delivered arms. Its process exited 0 in 0.516 s, with
62,373,888 bytes peak owned-job commit, no active children, termination or
cleanup errors. This review freshly checked all 82 input bindings
(18,018,146 bytes) and the completion's report hash. All matched. No RAW,
producer, GPU, FFT, reconstruction or renderer was run by this review.

The command actually executed by root was:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/native-spectral-fusion/pilot/analysis/stage-audit.py --out outputs/raw-quality-2026-10-27/native-spectral-stage-audit-1/output
```

The [receipt](../../../../../outputs/raw-quality-2026-10-27/native-spectral-stage-audit-1/output/receipt.json)
has SHA256 `ed88059409db6108f53b7b325619d276f48c19fca5069135ca8f1f677c491da6`.
It binds controls5 receipt `c747fc882838b755a65683681ea4f9b17b338bdb7b56e39d27ee67a891677010`,
audit source `65bf56bde722eb37f0c41a85fc9a648ff635e0e506284ce835d6c7fbddd007f2`
and the actual saved CFA/camera arrays. `inputs_unchanged:true`,
`quality_claim:false` and `photographic_admission:false` remain explicit.
The [protocol](stage-audit-protocol.md) fixes physical sites, units, basis and
rank handling. Complete-camera component scores reproduce the original
headline scorer within its fixed 1e-7 DN tolerance.

## What the saved stages establish

**MEASURED:** all twenty CFA fields have zero negative samples. The largest
known-color-site difference between the delivered camera field, converted back
to DN with its recorded WB/range, and the incoming CFA is 0.00033004 DN. Thus
the following large changes occur in the RGB values newly inferred at missing
color sites; neither the writer's max-zero step nor a changed known sample
explains them.

All amplitudes below are DN in the predeclared continuous component basis.
Combined green uses both physical green sites, not a square-grid substitution.

| Fixed case | Fused CFA component | Final camera at inferred sites |
| --- | --- | --- |
| Independent colors | R 153.376/160; weak G 7.309/8; B 127.165/130. Off-channel components are small. | Intended R/G/B become 87.588/4.946/70.311. Inferred G gains false R 52.793 and false B 84.623. |
| Green diamond | G 140.282/140; R 0.252 and B -1.698 against zero. | G becomes 46.375; false R/B are 44.221/26.309. |
| Near fine / far coarse | G 158.713/160 and 146.317/160, versus uniform 84.872 and 139.097. | G becomes 106.652 and 140.766; false fine R is 27.417. |
| Crossed components / glints | The two intended RGB components remain close to their planted CFA amplitudes; the second G is 49.628/50. | The second inferred G is 149.509. The complete-camera G amplitude is 99.556/50; the old lower-only recovery guard does not penalize this overshoot. |

The sharp original samples also carry the independent-color and green-diamond
components. The audit evaluates those originals in their own physical source
coordinates with their known plant; it does not interpolate them or call their
fixed source window the same target footprint.

**ARGUED:** these results localize much of the selected color/detail failure to
the final missing-color completion. They contradict an explanation in which
every poor final RGB component was already absent from the fused CFA. They do
not establish that MHC is a defective implementation, that the four fused phase
fields constitute a physically consistent arbitrary RGB scene, or that an
alternative demosaic will recover real insect detail. A full-rank regression
within the declared basis is not a general sampling-identification proof.

## Problems already present before MHC

- Both flat-noise candidates have larger CFA error than uniform. For flat A,
  R/G/B RMS is 13.654/17.129/19.066 DN versus 12.043/15.447/16.879 DN. The
  inherited permissive flat guard remains a pass, not evidence of denoising.
- Shared-bin conflict is already substantial: intended R and combined G are
  85.392/150 and 89.200/150 in CFA. Final RGB completion adds further errors,
  but cannot explain the original source-selection conflict away.
- Red cancellation has rank 2 for a three-column basis on each individual CFA
  phase. No separate red 0.20/0.30 component estimates are reported there.
  Candidate R truth-wave RMS is 207.707 DN versus uniform 78.991 DN, so a large
  error precedes demosaic. Dense-camera regression does not make those aliased
  original components identifiable.

All six inherited quality failures remain failures. No saved array is changed,
no new threshold is introduced, and no photographic admission follows. The
ongoing complete-299 candidate/uniform photograph remains the decisive trial.
This stage accounting supplies a concrete completion-stage hypothesis if its
actual appearance warrants follow-up, while retaining the independent noise,
alias and shared-weight failures that such a follow-up would not cure.
