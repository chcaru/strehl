# M135 commissioning results

Status: **PASS at estimator level; physical capture path not commissioned**

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
8. `commission.json` is the first run under the final fail-closed contract.

No threshold was relaxed. The amendments only corrected under-execution or
tightened provenance/refusal behavior.

## Final result

`python experiments/M135-detail-instrument/commission.py` returned `PASS` on
all 22 gates.

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
| Common A/B artifact absent reference | q95 ratio `0.404241`; q05 residual increase `0.469309` |
| Deterministic hallucination absent reference | q95 ratio `0.872049` |
| Averaging trap | information q05 `1.808783`, transfer q95 `0.832604`, promotions `0` |
| Edge-angle relabeling | maximum absolute ratio error `4.44e-16` |
| Flat reference | `NO_DETAIL`, 128/128 |
| Predictable target | `PREDICTABLE_TARGET`, 128/128 |
| Permuted reference | `NO_EVIDENCE`, 128/128 |
| Clipping / 8-bit / shared calibration / missing lineage | typed refusal in every case |
| Checker mutations | all three planted wrong decisions rejected |

The two required responsiveness controls therefore both fired: pre-noise blur
fell by roughly 38%, while planted optical improvement rose by roughly 25%.

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
