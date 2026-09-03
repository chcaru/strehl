# M-PHASE0-VEIL2 — A2 depth-boundary base-band pedestal

**Date:** 2026-09-03  
**Verdict:** **NOT ROBUST**  
**Production consequence:** **No Rust changes. `BaseBand::Mean` remains the
default and no A2 phase-1 arm is licensed.**

## What was actually tested

The dispatch described optical veiling glare, but proposal claim A2 is
different: the pyramid can select detail from one depth while reconstructing it
on the unweighted mean low-frequency base of all depths. This lane therefore
tested a stack-induced depth-boundary pedestal. It did **not** test lens scatter,
diffraction tails, or the `19-razor-edge` / `7-aperture-pairs` captures.

The frozen protocol is
[`experiments/M-PHASE0-VEIL2/PREREGISTRATION.md`](../../experiments/M-PHASE0-VEIL2/PREREGISTRATION.md).
The primary site is the inherited `bee-3-cpl` claw, and the replication sites
are three `chia-seeds-cpl` crevices frozen in
[`roi-manifest.json`](../../experiments/M-PHASE0-VEIL2/roi-manifest.json) before
their bases were evaluated.

## Relationship to the predecessor

`V-VEILCLAW` / `ORCH-veiling` §59.3 reported claw-frame base 0.581,
foreground-hair base 0.892, master base 0.802, and master-detail correlation
+0.852 with the claw frame. Those point values imply a foreground mixing
fraction of about 0.711, but had no uncertainty, used an arbitrary Gaussian
split, and did not have this lane's per-image paper normalization, potency
floor, tone gate, or commissioned geometry check.

This lane **reproduces but does not confirm** that flattering result:
deliberately removing per-image paper normalization gives
`theta=0.7406`, 95% CI `[0.7237, 0.7907]`. Under the preregistered normalization,
the answer becomes `theta=-0.0814`, 95% CI `[-0.2387, 0.0496]`. The conclusion
therefore depends on an exposure/tone convention and the commissioned
instrument refuses the effect. M63's later warning is also respected:
two focus-response peaks were never used as proof of two physical layers.

## Instrument and commissioning

Every numerical product was rendered through
`C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe`, SHA-256
`2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7`,
from source `6af834dac08d6605aee7ea3ad75809fdf6313770`. Outputs are 16-bit
linear-sRGB, seven-band soft pyramid, gate 2, exponent 2, sharpen 1.4. Full
commands, environment, banners, artifact hashes, and raw inventories are in
`experiments/M-PHASE0-VEIL2/out/run-records/`.

The estimator uses the exact Rust `[1,4,6,4,1]/16` REDUCE, replicated borders,
odd/even EXPAND phases, and seven-level reconstructed residual. A deterministic
20,000-replicate bootstrap (seed 5903002) resamples frame runs and 16×16 spatial
clusters.

Commissioning was **8/8 controls PASS and 8/8 planted defects RED**. The
cancellation-immune external predicates were independent slow-loop REDUCE and
EXPAND implementations (maximum errors `9.5367e-7` and `1.9073e-6`) and
directly observed RAW layer contents. The full-effect blur plant collapsed
detail projection to `3.73e-7`; the gamma plant read affine explained fraction
1.0; the one-pixel geometry plant read 1.0 px; and the 835-DN bowl read
574.97 DN. Machine record:
[`out/commission.json`](../../experiments/M-PHASE0-VEIL2/out/commission.json).

## Primary result

All values below are green unless stated otherwise.

| quantity | observed | registered requirement |
|---|---:|---:|
| claw `theta` | **-0.0814**, SE 0.0743, 95% CI **[-0.2387, 0.0496]** | KILL only if all potency gates pass and upper95 <=0.25 |
| layer separation `b_F-b_B` | **0.01757 paper white** | **>=0.15** |
| detail margin `D` | 0.4628, 95% CI **[0.00185, 0.69384]** | lower95 **>0.30** |
| paper-null median / p95-p05 | 0.000984 / 0.002288 | <=0.02 / <=0.04 |
| affine tone explained fraction | **10.06** | <=0.25 |
| two-window geometry disagreement | **20.22 px** | <=0.75 px |

The normalized base means were background `0.497791`, foreground `0.515365`,
and master `0.496361`. The paper anchor itself drifted from about 17,780 DN in
the claw frames through 18,703–18,775 DN in the hair frames to 19,059 DN in the
master. Without per-image normalization the three base means are 8,849, 9,674,
and 9,460 DN, producing the strong predecessor-like answer. Even that arm has
only `825/19059 = 0.0433` paper-white layer separation, still below the frozen
0.15 potency floor.

The detail point estimate favored the claw frames
(`corr_B=0.7780`, `corr_F=0.3152`), but clustered uncertainty did not clear the
gate. One geometry window had response 0.756 and residual `(dy,dx)=(-1.56,0.26)`;
the other had response only 0.0156 and a spurious large residual. That is a
registered failure, not a window to replace after seeing the answer.

Red, green, and blue all had upper confidence bounds below 0.25, and P6/P8,
ROI ±8 px, frame 180/288 alone, bilinear resampling, and all eight ±1-pixel
perturbations stayed in the same refused/null interval class. An independent
rawpy/LibRaw two-green decode, calibrated only on the three frozen off-target
anchors, read `theta=-0.0221`, 95% CI `[-0.1701, 0.1063]`, with layer separation
0.01695. It agrees that the registered denominator is too small.

## Chia replication and the losing global alternative

The three content-frozen chia sites met the four-contiguous-frame and
15-index-separation predicates, but their normalized foreground-minus-background
denominators were `-0.00099`, `-0.01076`, and `-0.00541`. All three are invalid
by sign and magnitude, so the hierarchical `theta` is audit output only, not
replication evidence. Its nominal median was 1.261, 95% CI
`[-0.854, 2.245]`.

The already-existing global alternative, `WeightedFromCoarsest`, is not a
solution. In the mean-only selected flower quadrant its weighted-minus-mean
plane-detrended wander was **1,493.4 DN** in green (red 1,424.1; blue 1,458.5),
against the future-treatment ceiling of 100 DN. This confirms the reason A2
proposed a coherence ramp rather than global weighting; it does not test that
unbuilt proposal.

## Verdict lookup and Rust consequence

The upper claw interval would superficially meet the KILL numerical bar, but
KILL is forbidden unless every potency and provenance gate passes. Four
load-bearing gates failed: layer separation, clustered detail identity, affine
tone locality, and geometry. The required verdict is therefore **NOT ROBUST**.
The dramatic normalized/unnormalized flip is an additional reason not to
convert the predecessor point estimate into a product decision.

**Nothing changes in Rust.** Specifically, do not add the proposed base policy
to `crates/strehl-core/src/pyramid.rs`, do not add its coherence ramp to
`crates/strehl-core/src/election_coherence.rs`, and do not add plumbing or CLI
surface in `crates/strehl-cli/src/merge_cmd.rs` or
`crates/strehl-cli/src/main.rs`. `BaseBand::Mean` stays. The claim's present
value is negative but actionable: it blocks spending a phase-1 implementation
on an effect whose sign changes under the registered tone control and whose
reference layers are not separated enough for this estimator.

## Limits and reproduction

This lane could not verify optical veiling glare, a future coherence-ramped A2
treatment, or generality beyond one inherited bee site and three refused chia
sites. Bee alignment's product-reported held-out error was 13.353 px. Default
gear-matched lateral-CA correction was active and common to every product arm;
no CA override was used. The flower weighted arm is a diagnostic bound, not the
unimplemented proposal.

From the repository root:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = (Get-Location).Path
python experiments\M-PHASE0-VEIL2\src\commission.py
python experiments\M-PHASE0-VEIL2\src\render.py --plan experiments\M-PHASE0-VEIL2\render-plan.json
python experiments\M-PHASE0-VEIL2\src\measure.py
python experiments\M-PHASE0-VEIL2\src\check.py
```

The complete numerical record is
[`out/measurement.json`](../../experiments/M-PHASE0-VEIL2/out/measurement.json).
