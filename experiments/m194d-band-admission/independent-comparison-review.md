# M194d independent comparison review

**VERIFIED:** the complete fixed experiment is correctly bound and the
independent read agrees with its numerical results. The positive-weight
operator has a useful, limited development result: much lower flat-fixture
noise and smaller extreme-error quantiles, with a small textured-plane error
cost and some newly harmed pixels. This supports continuing the bounded
research program. It is not a default-promotion, physical-calibration,
occlusion-quality or SOTA admission.

No original evidence, product source, threshold, settings, producer input or
scorecard was modified by this independent review. No RAW or sealed capture
was read. All quality observations below come from the already completed
fixed matrix, not an additional render or parameter search.

## What was independently checked

The controller is `experiment-1/controller.json`, SHA-256
`b3e9a71a538d16f6e0f2c399cb530c71a00fa74cd1194362d41417610f5a1e59`.
The interpreted comparison is `experiment-1/comparison-2.json`, SHA-256
`a64df70677d1dc66c81f6e088b0196a23883bc9c480cbe156c6b104e0cadc306`.

`independent-comparison-read.py` reads **120 actual TIFFs**: forty archived
M194c outputs, forty explicit hard-floor outputs and forty positive-weight
outputs. It checks actual input hashes, TIFF file/pixel hashes and all paired
case keys. Every explicit hard-floor output is byte-identical to its archived
M194c counterpart. Plan differences are restricted to the named admission,
formula, schema, environment and build-context fields; the actual crop,
geometry, normalization, input identities and other configuration agree.
Twenty-one mode pairs have identical pixels: all twenty single4 outputs and
the full9 noise-off flat output. Nineteen full9 pairs change.

The independent read uses literal native ROI coordinates, 32-point Gaussian
quadrature for continuous cell integration, numerical pupil-overlap
integration for the observation target, Welford temporal variance, and
repeat-level paired MSE/SEM and leave-one-repeat-out variance uncertainty.
The commissioned independent optical/moment helpers are verified against
their committed M194b/M194c bytes before reuse. This preserves a different
mathematical implementation from the root reader. It does not provide a
second physical camera model. The largest numerical discrepancies are
1.71e-10 DN for RMSE change, 3.12e-9 DN² for paired mean MSE change, and
2.69e-12 DN² for variance jackknife SE. All checks pass on the first run.

`independent-comparison-read-1.json` has SHA-256
`763174a931e3a953189c20ed2404eefd18f5e51f2cb57fc8dd1b043a5afe2b4f`.
The exact command is:

```powershell
python -B experiments/m194d-band-admission/independent-comparison-read.py --controller experiments/m194d-band-admission/experiment-1/controller.json --controller-sha b3e9a71a538d16f6e0f2c399cb530c71a00fa74cd1194362d41417610f5a1e59 --comparison experiments/m194d-band-admission/experiment-1/comparison-2.json --comparison-sha a64df70677d1dc66c81f6e088b0196a23883bc9c480cbe156c6b104e0cadc306 --out experiments/m194d-band-admission/independent-comparison-read-1.json
```

## Measured gains and costs

Across the eight fixed noisy flat repeats, full9 temporal variance ratios
(positive-weight / hard-floor) are RGB **0.457936, 0.312956, 0.464664**.
Paired MSE changes are RGB **-102.681, -129.033, -108.193 DN²**, with
repeat-level SEM **1.917, 2.750, 2.633 DN²**. These are reductions on this
declared flat software model. The same single4 inputs are exactly unchanged;
the gain is not a relabelled single-frame comparator.

The plane needs both target conventions. Against the continuous ideal target,
full9 paired MSE **increases** by RGB **0.688721, 0.739367, 0.689958 DN²**,
with SEM **0.010473, 0.010847, 0.017477 DN²**. Temporal variance nevertheless
falls slightly, to RGB ratios **0.999786, 0.999753, 0.999796**. Against the
in-focus diffraction/aperture observation target, paired MSE changes are
RGB **-0.000409, -0.000074, -0.006284 DN²**, with SEM
**0.001508, 0.001945, 0.002034 DN²**. Lower temporal noise therefore does not
justify saying plane reconstruction improved without naming its target.

The noise-off plane loses up to **0.008668 DN** of fitted wave amplitude.
Its ideal RMSE rises by at most **0.005310 DN**, and its observation RMSE
rises by at most **0.001856 DN**. All its delivered component changes are at
most one TIFF LSB. This is a small, real delivered signal/error cost; it is
not a refutation of the flat-noise benefit. The analytic color and color-null
full9 changes are also at most one TIFF LSB, with no >10 DN paired truth-error
changes. Their narrower color model cannot commission an optical two-layer
claim.

None of the prospectively fixed engineering alarms fires. The independent
reconstruction agrees with that fact. Those alarms are intentionally coarse
review triggers, not a test of zero harm: the positive plane ideal-MSE cost
and the adverse sparse pixels below remain measured facts.

## Sparse changes and their interpretation

The independent nearest-rank p99.9 description is explicitly different from
the root's commissioned linear interpolation. Every one of the 24 noisy
flat channel/repeat nearest-rank quantiles improves. The worst after/before
ratio across repeats is RGB **0.43358, 0.33396, 0.43230**.

Across eight flat/full9 repetitions, each channel has 172,032 scored
pixel-repetition sites. Absolute truth error increases by >10 DN at RGB
**858, 312, 988** sites and decreases by >10 DN at RGB
**13,651, 14,693, 14,006** sites. These descriptive counts use the preregistered
10 DN cutoff; they are not independent trials, a new bar or an occlusion map.

The worst scored adverse change is **+33.451259 DN** at seed 743, red,
native **(203,146)**: the output moves from **2999.506706** to **3033.944732 DN**
against truth **3000.000089 DN**. A smaller aggregate error distribution does
not mean every site improves. The largest whole-image movement is
**556 TIFF LSB = 125.970672 DN**, at seed 733, blue, native **(155,51)**,
outside the fixed ROI. Movement alone does not say whether truth error
improved; it must not be presented as an adverse-error maximum.

The separately preregistered historical red site **(142,170)** improves by
**97.116293 DN** in absolute truth error at seed 709. Its trace across all
eight repetitions is retained: four other repetitions worsen there, three
improve including 709, and one is unchanged. Selecting only seed 709 would
overstate what this site demonstrates. The component/operator evidence,
owned by the other independent verifier, is needed to discuss mechanism;
this complete image comparison cannot attribute every benefit solely to
removing the hard cutoff because the proposed formula also reshapes weights
above the floor.

## Instrument and evidence commissioning

The sparse component passes **26/26** controls. Ten ordinary-domain
numerical/null/power checks passed from the start. Initial malformed-domain
controls exposed complex-value conversion, coordinate-range and arithmetic
overflow holes; both failed runs and the exact original helper are preserved.
Root added refusals before scored output. All sixteen malformed cases then
refuse. These cases are outside the bounded u16 image domain and did not
invalidate a measured image result. See
`independent-comparison-review-notes.md` for their commands and exact hashes.

Before the complete matrix, the pinned consumer passed **46/46** runtime
checks, including three actual TIFFs and 22 mode/environment/rehashed-plan/
source/old-binary refusals. Valid direct-child and ambient-override companions
passed. The record is `independent-mode-run-1/result.json`, SHA-256
`fa91ecc03f506bd25eaf2c0d113e00bc17331c5f4dd6e7c6744b26f5dc5418b4`.
No test correction or product edit followed this first runtime execution.

The original complete comparison reader failed before writing a result:
it passed a JSON string to the unchanged Path-only hash API. The original
reader, render evidence and failure remain intact. I programmatically verify
that `compare-experiment-v2.py` differs only by wrapping that log path as
`Path(...)` and adding explicit reader identity metadata to the output.
Its SHA-256 is
`9cc3fd5652a4e17d9036e6b69300b4e0bef50089893c3ba0fa40424e15b00fb1`.
No renderer or scoring equation changed; no rerender was needed.

Against v2 and the complete package, **18/18** new evidence controls pass:
the unchanged controller and a complete index with absolute references are
valid, and sixteen rehashed contradictions refuse. They cover missing or
duplicated modes, omitted included source, changed reader binding, false
product-source delta, failed terminal command, unknown indexed admission,
legacy/mismatched plan and receipt schemas or mode/formula/environment,
missing or duplicated paired outputs, and changed actual child mode.
Original evidence and source bytes remain unchanged after a final replay.
The checks validate recorded consistency; they do not authenticate a wholly
fabricated execution history.

`independent-comparison-bindings-run-1/result.json` has SHA-256
`04f96184beb98440d5ac05c86197110e892a609a1a03fb2635346479ffdb470c`.
Command:

```powershell
python -B experiments/m194d-band-admission/independent-comparison-bindings.py --controller experiments/m194d-band-admission/experiment-1/controller.json --controller-sha b3e9a71a538d16f6e0f2c399cb530c71a00fa74cd1194362d41417610f5a1e59 --out experiments/m194d-band-admission/independent-comparison-bindings-run-1
```

The fixed synthetic/model and repeat uncertainty scope remains binding.
The observations warrant a next bounded test that can express competing
depths and detail dilution. They do not resolve the older M138/M143
Phase-1 admission requirements, grant a calibration claim, or justify
changing the shipping default.
