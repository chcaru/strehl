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
split, normalized every crop by its own 99.5th percentile rather than by a
frozen paper ROI, and lacked this lane's potency floor, tone gate, or
commissioned geometry check.

This lane **recovers a similar point value but does not confirm** that result.
An adversarial arm with no per-frame anchor gives `theta=0.7410`, 95% CI
`[0.7242, 0.7910]`; it is not an exact reproduction of the predecessor's
per-crop-percentile normalization. Under the preregistered fixed-paper
normalization, the answer becomes `theta=-0.0812`, 95% CI
`[-0.2359, 0.0511]`. The conclusion therefore depends on the exposure/tone
anchor and the commissioned instrument refuses the effect. M63's separate warning
is also respected: two focus-response peaks were never used as proof of two
physical layers.

## Instrument and commissioning

Every numerical product was rendered through
`C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe`, SHA-256
`2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7`,
from source `6af834dac08d6605aee7ea3ad75809fdf6313770`. Outputs are 16-bit
linear-sRGB, seven-band soft pyramid, gate 2, exponent 2, sharpen 1.4. Full
commands, environment, banners, artifact hashes, and raw inventories are in
`experiments/M-PHASE0-VEIL2/out/run-records/`.

The estimator uses the exact Rust `[1,4,6,4,1]/16` REDUCE, replicated borders,
odd/even EXPAND phases, seven-level reconstructed residual, sidecar-derived
60-bisection fit-to-cover scale, and four-tap Catmull-Rom (`a=-1/2`) gather. The
exact cover scales are `0.9320568176176102` (bee) and `0.9597221448500919`
(chia), rather than their four-decimal console banners. A deterministic
20,000-replicate bootstrap (seed 5903002) resamples both frame runs and 16×16
spatial clusters for theta and detail.

Commissioning was **11/11 controls PASS and 11/11 planted defects RED**. The
cancellation-immune external predicates were independent slow-loop REDUCE and
EXPAND implementations (maximum errors `9.5367e-7` and `1.9073e-6`) and
directly observed RAW layer contents. The full-effect blur plant collapsed
detail projection to `3.73e-7`; the gamma plant read affine explained fraction
1.0; and the one-pixel geometry plant read 1.0 px. The 835-DN bowl read
574.97 DN with jackknife lower95 425.17 DN. Three repair-specific plants also
went RED: OpenCV cubic read `-0.09375` against the external Catmull half-pixel
predicate `-0.0625`; four-decimal coverage missed analytic `36/49`; and fixing
frame medians collapsed a known detail-interval width from 2.0000 to
`7.26e-8`. Machine record:
[`out/commission.json`](../../experiments/M-PHASE0-VEIL2/out/commission.json).

## Primary result

All values below are green unless stated otherwise.

| quantity | observed | registered requirement |
|---|---:|---:|
| claw `theta` | **-0.0812**, SE 0.0740, 95% CI **[-0.2359, 0.0511]** | KILL only if all potency gates pass and upper95 <=0.25 |
| layer separation `b_F-b_B` | **0.01757 paper white** | **>=0.15** |
| detail margin `D` | 0.4639, 95% CI **[-0.00302, 0.68143]** | lower95 **>0.30** |
| paper-null median / p95-p05 | 0.001009 / 0.002297 | <=0.02 / <=0.04 |
| affine tone explained fraction | **10.17** | <=0.25 |
| two-window geometry disagreement | **73.63 px** | <=0.75 px |

The normalized base means were background `0.497788`, foreground `0.515358`,
and master `0.496361`. The paper anchor itself drifted from about 17,780 DN in
the claw frames through 18,703–18,775 DN in the hair frames to 19,059 DN in the
master. With no per-frame anchor the three normalized base means are
`0.464292`, `0.507567`, and `0.496361`, producing the strong but merely
predecessor-like answer. Even that arm has only `0.04328` common-master-paper
layer separation, still below the frozen 0.15 potency floor.

The detail point estimate favored the claw frames
(`corr_B=0.7784`, `corr_F=0.3145`), but frame-run-plus-clustered uncertainty did
not clear the gate. One geometry window had response 0.681 and residual
`(dy,dx)=(-1.90,0.21)`; the other had response only 0.0027 and a spurious large
residual. That is a registered failure, not a window to replace after seeing
the answer.

Red, green, and blue all had upper confidence bounds below 0.25, and P6/P8,
ROI ±8 px, frame 180/288 alone, bilinear resampling, and all eight ±1-pixel
perturbations stayed in the same refused/null interval class. An independent
rawpy/LibRaw two-green decode, calibrated only on the three frozen off-target
anchors, read `theta=-0.0210`, 95% CI `[-0.1688, 0.1072]`, with layer separation
0.01694. It agrees that the registered denominator is too small.

## Chia replication and the losing global alternative

The three content-frozen chia sites met the four-contiguous-frame and
15-index-separation predicates, but their normalized foreground-minus-background
denominators were `-0.00070`, `-0.01071`, and `-0.00527`. All three are invalid
by sign and magnitude, so the hierarchical `theta` is audit output only, not
replication evidence. Its nominal median was 1.255, 95% CI
`[-0.998, 1.894]`.

The already-existing global alternative, `WeightedFromCoarsest`, is not a
solution. In the mean-only selected flower quadrant its weighted-minus-mean
plane-detrended wander was **1,493.4 DN** in green (red 1,424.1; blue 1,458.5),
with delete-block jackknife 95% CI **[1,137.9, 1,848.9] DN**, against the
future-treatment ceiling of 100 DN. This confirms the reason A2 proposed a
coherence ramp rather than global weighting; it does not test that unbuilt
proposal.

An independent read-only rerun reproduced the first filed record exactly, then
found four flattering instrument/report defects: no C7 confidence bound,
rounded coverage plus OpenCV's wrong cubic kernel, fixed frame medians in the
detail bootstrap, and incorrect wording about the predecessor's normalization.
All four are repaired above. The repaired primary estimate moved only from
`-0.0814` to `-0.0812`, while the detail lower95 moved from `+0.00185` to
`-0.00302`; no failed gate was rescued. A final independent read-only rerun
regenerated all three JSON records value-for-value, independently rederived the
primary pixels, sidecar coverage, and wander interval, and reported no defect
(11/11 commissioning plants and 7/7 checker plants RED).

## Verdict lookup and Rust consequence

The upper claw interval would superficially meet the KILL numerical bar, but
KILL is forbidden unless every potency and provenance gate passes. Four
load-bearing gates failed: layer separation, clustered detail identity, affine
tone locality, and geometry. The required verdict is therefore **NOT ROBUST**.
The dramatic fixed-paper/unanchored flip is an additional reason not to convert
the predecessor point estimate into a product decision.

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

---

## 2026-09-02 re-scope audit: the “already answered” claim fails

**Re-scope verdict:** **STOP_DO_NOT_BUILD. The prior A2 finding did not survive
the ordered audit.** The pro-build bias and seven fail-closed gates were frozen
in
[`RESCOPE-AUDIT-PLAN.md`](../../experiments/M-PHASE0-VEIL2/RESCOPE-AUDIT-PLAN.md)
before formal scoring. Result: **0/7 passed**; the independent checker passed
with **4/4 positive controls and 20/20 self-plants RED**.

### What the earlier work established—and what it did not

`V-VEILCLAW` directly observed foreground hairs and the claw at two focus
positions, and measured the familiar 0.581/0.892/0.802 base split with +0.852
detail correlation. Its repaired focus-curve classifier was reported 7/7 on
known curves with a flat null. The current harness remains 6/6 on its synthetic
curves because the real CSV is absent; independent verification regenerated
the curve from all 299 RAWs and recovered the published f182/f288 peaks exactly.
The classifier is therefore commissioned and reproducible for **curve shape**.
It is not a commissioned test of the causal claim that the pyramid mean base
made the master pedestal.

The originating README explicitly calls that mechanism a “lead, not a finding”
because `meanveil.py` could not confirm it. `BUILD-VEILMAP` explicitly records
that its base/detail cross-reference to the merge was **NOT DONE**. Its own
commission cannot now run because the external SHIP-V1 master is absent; its
potency run lacks the external tensor. None of the 27 tracked predecessor files
is an outcome artifact. The curve can be regenerated from RAW, but the exact
old master/base result cannot. Moreover, its commission tests `DriftFitter`, while the
measurement adds `TrackFitter` and a polynomial solve, and its drift plant
imports the same production `veilgrid.gather` it exercises. No planted
wrong-sign or wrong-component defect ever commissioned the A2 base mechanism.
`potency.py` also prints failed potency without returning nonzero; an
independently planted all-FLAT tensor printed four failures and exited 0.

There is no formal retraction banner on `V-VEILCLAW`, but its explicit
limitation binds. On the earlier broad flower aura, `V-veiling` says “the
finding survives; the mechanism does not”; this is contrary context, not a
claw-specific retraction. Likewise, `BUILD-BLEND`'s broad-aura intervention
measured both base policies removing that aura equally and localized its bowl
one level higher, in selected coarse Laplacian bands. It does not directly
falsify the claw, but it does defeat source inspection as sufficient causal
proof. Finally, the “already answered” triage commit `f7017885` (20:06) is an
ancestor of, and predates, the adverse repaired commissioned result
`e4e3939f` (21:51).

### Tone, defocus, and diffraction

The result is not protected from the exact contrast/tone failure named in the
order. Changing only the per-reference positive scale—slopes
**1.0152–1.0722**, hence strictly increasing affine maps—moves the claw result
from `theta=+0.7410`, 95% CI `[0.7242,0.7910]`, to `theta=-0.0812`, 95% CI
`[-0.2359,0.0511]`. Its sign reverses without changing pixel order. The
fixed-paper tone gate also reads 10.17 against a 0.25 ceiling. Therefore a
contrast/tone change can reproduce or erase the claimed win; the old Gaussian
means and Pearson correlations do not rule it out.

The claw contact sheet proves two contents at that one site, but the classifier
is not generally specific to two depths: M63's single-depth silhouette fires
at **78.9%** versus **78.3%** for the supposed occlusion class, and its physical
single-depth plant produces strong symmetric defocus side-lobes. No comparable
one-depth edge null commissions the predecessor classifier. None of the cited
A2 evidence measures its endpoint across `7-aperture-pairs`; this lane had
explicitly excluded that ladder. Diffraction separation is therefore absent,
not assumed from a shared aperture.

### Binding consequence

The newer direct instrument is reproducible and independently verified:
11/11 controls and plants, checker 7/7 RED, but layer separation is only
0.01757, detail lower95 is -0.00302, tone and geometry fail, and the verdict is
`NOT ROBUST`. The machine audit and evidence are in
[`out/rescope-audit.json`](../../experiments/M-PHASE0-VEIL2/out/rescope-audit.json);
its checker is
[`out/rescope-audit-check.json`](../../experiments/M-PHASE0-VEIL2/out/rescope-audit-check.json).

The re-scope order says to stop if Part 1 fails. Therefore **no Rust was
changed**, no new coherence-ramped A2 pyramid flag was added, no before/after
feature delta was rendered, and the zero-magnitude/wrong-sign feature controls
were not run. Pre-existing estimator-only `STREHL_VEIL` and global
`STREHL_PYRAMID_MEAN_COARSE` controls are not the proposed treatment. Building
it after a 0/7 audit would violate the explicit stop condition, not cure phase
0.
