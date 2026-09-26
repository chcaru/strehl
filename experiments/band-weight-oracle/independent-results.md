# Constructive headroom on near/far detail; no complete qualification

MEASURED, independent scientific read of `check-1/output/screen.json` and
`solve-1/output/fit.json` only. Root executed the bounded `run.py` solve/check
jobs; their invocation/process records remain with those jobs. No rerun, new
window, revised bar or photographic output was used for this review.

The exact final1024-step truth-assisted fit constructs a useful witness for the
near-fine/far-coarse case while retaining the original four-CFA coefficients,
Mean terminal, hull and MHC. Its positive-window RGB RMSE is
.00518630 -> .00407554, **.785829x canonical** (.236874x uniform), and every fixed
error/component guard for that case passes. Green near/far coefficients are
1.01957/.97708, against canonical1.00855/.93711 and uniform.37376/.90608.
The interior also improves (.733279x canonical RGB error). This is constructive
headroom within this exact consumer without sacrificing the other depth.

The full seven-case conjunction still fails. The failures are **chroma error
against uniform**, not failed eligible component retention:

| Case/window | Chroma canonical | Chroma uniform | Chroma oracle | Failed ratio |
|---|---:|---:|---:|---:|
| Curved/interior | .00344986 | .00155945 | .00358076 | 2.29618x uniform |
| Curved/positive | .00486400 | .00206098 | .00530844 | 2.57569x uniform |
| Unclipped glint/core | .00372014 | .00120546 | .00361570 | 2.99944x uniform |

All exceed the frozen1.10 limit. Curved positive RGB improves to .677002x
canonical, but its chroma rises to1.09137x canonical and fails the cleaner-colour
uniform reference. Its far coefficients improve from approximately.19-.31 to
.63-.84; those weak canonical/uniform far references were unqualified retention,
so this is not newly measured detail destruction. Eligible near retention passes.

The genuine glint core improves RGB to .754654x canonical, green to .793712x,
and chroma to .971927x; green glint recovery rises .98102 -> .99221. Adjacent
detail and outside spread pass (outside RGB .493714x canonical). Thus calling
this a lost-highlight failure would misread the result. It preserves/improves
the current core while remaining well above uniform's lower chroma error.
The two-reference guard is retained exactly; that tradeoff is not waived.

Weak colour passes: local RGB/chroma are .693298/.761052x canonical. Near red
and blue recovery improve .85783/.85430 -> .91402/.93520; green near falls
.72379 -> .68103 but retains94.1%, above the90% bar. The clipped case passes
only its registered adjacent/spread windows; its clipped core is unqualified.
Both flat cases pass, but direct access to the exact truth lets these free
weights fit away particular noise draws. This is oracle privilege, not a
deployable denoising or noise-calibration gain.

The receipt reports exact complete CFA/RGB replay from saved fitted weights,
including boundaries. Native reference-score parity and all scorer destroyers
pass. This replay reuses the previously commissioned frozen consumer port;
there was no new native RAW/full-image execution. The fixed learned737-parameter
predictor remains rejected; these325080 per-case truth-fitted logits are not it.

Next implication: retain Mean while examining how to recover the demonstrated
near/far weight choice without truth. The failed learner did not establish that
this reconstruction cannot represent an improvement. Conversely, neither the
two chroma failures nor the finite fit establish an optimization ceiling or a
mean-base defect. Scope is three AC levels on80x72quad generated crops, not the
seven-level photographic consumer. No retraining, photograph, default change,
generalization or SOTA claim is authorized by this result.

Screen SHA256: `c60e4d2399157a16f392a002589e041b6f6fd80ff9d0ca4cb07ff41e48ab0fe5`.
Fit SHA256: `b765534f7656624a77e343a3527c326c8afa6f83ec1824baec0629809ec35ffa`.
