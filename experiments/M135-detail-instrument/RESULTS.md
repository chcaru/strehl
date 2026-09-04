# M135 commissioning results

Status: **PASS at estimator level; physical capture path not commissioned**

## D8 adjudication

`python experiments/M135-detail-instrument/d8_audit.py` independently read the
preserved byte-pinned M115 rerun and historical source at commit
`77c8d5e9ac6ed342cdc841e541c98f87e5c743f8`. All source blob hashes and fourteen
audit checks passed. This is a post-brief source adjudication, not a change to
the frozen M135 candidate or its admission bars.

- Blur recovery reproduced at `0.9938215871-0.9973982082`.
- Maximum normalized-SNR movement reproduced at `0.537785%`.
- The naive gradient reading reproduced at `8.2513657x`. Source inspection
  shows this is RMS-gradient gain; the corresponding energy ratio is
  `68.085x`.
- The power identity reproduced at
  `0.999999999987-1.000000000000`.
- The historical null still fails on `MEAN=0.438734` and
  `WIENER_UNG=3.331288` against `0.25`.
- The direct common-mode adversary reads FRC `0.972099`.
- SPLIT2's available repeat pair failed its second geometry gate at
  `0.107703 native px` against `0.10`; the independent estimator reproduced
  the fail at `0.105202`, so no real repeat-pair FRC was retained.
- SPLIT2's evaluation-leakage plant drove high-band FRC to `1.0` and moved an
  externally protected output by `25.002575`; its held-out tuner guard
  correctly went RED.

The values are valid; D8's inference is not. At an ideal Fourier cell, a
common filter multiplies `P_sig` by its power, so `P_sig` is
sharpening-sensitive, while the same factor cancels from normalized split SNR
and FRC, making them blind to post-render blur. Finite Hann/ring aggregation
has implementation-dependent residuals with no structural sign or magnitude
bound, not a blur response. Repeated brackets remove neither that structural
limit nor stable same-sensor pattern without independent calibration. D8 is
rejected as M1 and retained only as an auxiliary diagnostic family.
Machine-readable details are in `d8-audit.json`.

## Freeze history

1. `053ec124` froze the candidate, population, challenges, and numeric bars.
2. The first run was retained as `commission-run1-invalid.json` because C14
   and C15 ran once rather than the frozen 128 populations.
3. `43189f32` froze amendment 1 and the corrected repetition loop.
4. The second run was retained as `commission-run2-superseded.json`.
5. `7606b6ea` froze amendment 2, adding explicit predictable-target and
   shared-flat lineage challenges.
6. The third run was retained as `commission-run3-superseded.json`.
7. `56f7cada` froze amendment 3, making all lineage fields mandatory and
   replacing the weak constant-template periodic fixture with a full-rank
   public cyclic code.
8. `commission-run4-pre-flat-null.json` preserves the first run under that
   contract.
9. `f319c19d` froze amendment 4: a paired flat sentinel became mandatory and a
   high-band noise-amplification plant was added.
10. The first amendment-4 execution stopped before gate evaluation or artifact
    write because its potency record exposed 16 cell gains to a four-frequency
    checker. `a16b3822` froze amendment 5, which de-duplicated that record
    without changing the plant, statistic, or bars.
11. `commission.json` is the first successful run under the mandatory-flat
    contract.
12. `commission-run5-pre-shape-guard.json` preserves that result.
    `6a5b524d` froze amendment 6, which made malformed primary shapes return
    `INVALID_SHAPE` instead of reaching flat-ratio arithmetic. The replacement
    `commission.json` is byte-identical at SHA-256
    `6DC8CC48534387D329010657E76E8574F6AFAFF541511951725BAC79D1B00F14`.

No threshold was relaxed. The amendments only corrected under-execution or
tightened provenance/refusal behavior.

## Final result

`python experiments/M135-detail-instrument/commission.py` returned `PASS` on
all 25 gates.

| Control | Final result |
|---|---:|
| Fresh-noise null | geometric ratio `0.996954`; mean-log 95% CI `[0.992500, 1.001429]` |
| Pre-noise blur | q95 ratio `0.631511` |
| Planted optical improvement | q05 ratio `1.241840` |
| Post-render USM | range `[0.9999999999999993, 1.0000000000000007]` |
| USM at 64/128/256/512 sites | maximum absolute error `3.33e-16`; unchanged `1.01` bar |
| Post-render blur | information ratio unity to `6e-16`; transfer q95 `0.687470` |
| Gamma-3 after 33-step PCHIP | range `[0.999997811, 1.000001928]` |
| Logistic after 33-step PCHIP | range `[0.999958140, 1.000030663]` |
| Added independent noise | q95 ratio `0.468175` |
| High-band noise-only amplification | squared upper-band gain `5.0458`; q95 information ratio `0.549007`; promotions `0` |
| Common A/B artifact absent reference | q95 ratio `0.404241`; q05 residual increase `0.469309`; matched flat `FLAT_NULL_FAILED` 128/128 |
| Deterministic hallucination absent reference | q95 ratio `0.872049` |
| Averaging trap | information q05 `1.808783`, transfer q95 `0.832604`, promotions `0` |
| Edge-angle relabeling | maximum absolute ratio error `4.44e-16` |
| Flat reference | `NO_DETAIL`, 128/128 |
| Mandatory matched flat, uncontaminated arms | worst information ratio `0.002320`; reference-repeat ratio `0.001149`; output-repeat ratio `0.096199` |
| Structured false flat | `FLAT_NULL_FAILED`; all three ratios exactly `1.0` |
| Missing matched flat | `MISSING_FLAT_CONTROL`, 128/128 |
| Predictable target | `PREDICTABLE_TARGET`, 128/128 |
| Permuted reference | `NO_EVIDENCE`, 128/128 |
| Clipping / 8-bit / shared calibration / missing lineage | typed refusal in every case |
| Checker mutations | all three planted wrong decisions rejected |

The two required responsiveness controls therefore both fired: pre-noise blur
fell by roughly 38%, while planted optical improvement rose by roughly 25%.

Every pre-amendment summary and C0-C21 gate reproduced exactly against
`commission-run4-pre-flat-null.json`. The new flat control is not a post-hoc
plot: `evaluate` requires it, emits all three ratios, and suppresses the
claim-bearing score when the flat is structured or repeatably contaminated.
The worst output-repeatability ratio, `0.09619849966263185`, is only
`3.80150033736815%` below its `0.10` bar. That is a real warning about
physical false-refusal margin, not grounds to relax the frozen threshold.

## M137 flat-null input

**VERIFIED.** M137's independent kernel experiment selected a low-structure arm at
`13.314850036584688%` of the detailed arm's coarse structure. Its
Catmull-Rom-over-bilinear gap nevertheless rose from
`0.3403664343410666 dex` to `0.3488548829813006 dex`, ratio
`1.0249391472947889`; its registered `0.10` flat-gap bar failed and the lane
withdrew the resolved-detail claim. M135's paired-flat requirement and
spectrally shaped noise-only plant were frozen in response before their first
successful outcomes
(`experiments/M134-kernel-frontier/M137-clamped-detail.md:207-289`).

## M138 consumer contract

**VERIFIED.** Commit `6e581c05` froze the contract and checker before the
first self-test. The first self-test passed. A later input audit found that
Python/NumPy would coerce JSON Booleans and numeric strings; commit
`11879ddc` froze consumer amendment 1 before replacement execution. It changed
no bar or valid numeric decision and added malformed-input plants.

**VERIFIED.** `m135-detail-pass-v1` is now a deterministic, per-capture
comparison rule. The checker emits `DETAIL_PASS`, `DETAIL_FAIL`,
`NOT_APPLICABLE`, `INSTRUMENT_UNBOUND`, or `INSTRUMENT_INVALID`; its
`detail_pass` field is Boolean only for the first two states and `null`
otherwise.

**VERIFIED.** A valid applicable candidate passes only when its `10,000`
paired-site bootstrap draws at seed `20260902` satisfy all three
non-compensating bars: information-ratio lower 95% `>=0.98`, every cell's
transfer-ratio lower 95% `>=0.98`, and unexplained-fraction-difference upper
95% `<=0.02`. Candidate and legacy must also each pass the mandatory
flat-control bars.

**VERIFIED.** The frozen self-test passed `14 / 14` controls, including exact
boundary and one-step-beyond-boundary tests, defect and improvement arms,
malformed payloads, failed flats, unbound state, and per-capture
`NOT_APPLICABLE`.

**VERIFIED.** The canonical contract SHA-256 is
`247abd2024307aa43e7ab62edd7da23b8042ca98dedf6ca1a8eaac2d1510c249`;
the checker SHA-256 is
`a8f92dbfc436e7a0ffab0fd0cc8bbc9d6708cc829f0435a5bdda510e2a30af5b`.
The checked-in binding remains `UNBOUND`, so no current result is a
claim-bearing `detail_pass`.

**VERIFIED.** M138 requires an amendment before binding: its current input and
output lists omit the flat certificate, its adjudicator accepts supplied
Booleans instead of invoking M135, and its pinned M135 source hash predates the
mandatory-flat API. That amendment must route unbound or invalid M135 states
to instrument blockage, not Phase-1 refutation.

## Load-bearing negative diagnostics

The complete certificate includes capture lineage because the score alone
cannot infer it.

- A physically flat shared-pattern plant with the calibration witness enabled
  returns `SHARED_REFERENCE`.
- The identical plant with that witness deliberately disabled returns
  `OK`, `J_TR = 1.830436 bits/site`.
- A full-rank public cyclic target with forged nonperiodic lineage returns
  `OK`, `J_TR = 1.799726 bits/site`.

Those are not failed gates. They demonstrate the exact boundary: independent
sensor/calibration lineage and unpredictable target provenance are
constitutive parts of the instrument. If either is unavailable, M1 must be
`UNMEASURED`; the pixels cannot repair the missing provenance.

## Scope

The final run commissions:

- the per-cell coherence/information arithmetic;
- the exact LSI postfilter invariance;
- the non-compensating transfer veto;
- the common-mode residual response;
- a mandatory per-run flat/detail certificate;
- a high-band noise-amplification rejection;
- the typed refusal paths;
- null, defect, improvement, and checker power.

It does not commission:

- image-to-carrier extraction on a physical random-code target;
- physical reference MTF, magnification, registration, or calibration
  independence;
- site-level power on a real capture;
- a scored M1 value.

The current result is therefore a conditional GO to physical commissioning,
not scorecard admission.
