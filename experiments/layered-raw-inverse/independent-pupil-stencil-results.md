# Independent pupil-stencil results

**MEASURED by the root-run command; independently reviewed without another execution.** `pupil-stencil-1/output/result.json` explicitly reports `passed=true`, `source_unchanged=true`, `no_fit_performed=true`, and `real_photo_admission=false`. The fixed operator and finite-quadrature commission passed. This does not reclassify any earlier reconstruction-quality rejection.

Root command, retained with its environment and job limits in `control-process/invocation.json`:

```text
python.exe -I -B -X faulthandler experiments/layered-raw-inverse/pupil-stencil-controls.py --out experiments/layered-raw-inverse/pupil-stencil-1/output
```

The 15 fixed64 forward cases cover constants, an impulse, both alpha endpoints and the crossing at three focus positions. Maximum error is 0.00091553 DN against direct CPU same-ray enumeration and 0.00041199 DN against the frozen complete Torch forward, below the 0.1-DN bound. All nine near/far/alpha adjoint comparisons pass; maximum relative L2 error is 1.26787e-6, below 3e-4. Independent finite differences have live derivatives of 0.138854, 0.395575 and -57.7043; all doubled-gradient destroyers reject. These are meaningful sign/routing checks, not evidence that the scene is physically valid.

The incorrect independent-marginal composition differs by 35.9485 DN inside the supported crossing. Thus the test can detect loss of same-ray visibility coupling. The literal boundary witness transmits exactly 500 DN when near coverage lies outside the image; its **first-output-column-only** cotangent produces exactly the required far gradient, with zero near/alpha gradients. The same witness passes on a nondefault stream with in-stream input production. CPU, dtype, strides, nonfinite values, invalid alpha/pupil and double-backward requests all refuse. Inputs remain unchanged. Context-change and graph-capture refusals remain source-reviewed, not exercised results.

For the preselected 16384-site candidate, maximum full-image difference against the unchanged forward using the same sites is 0.0283203 DN. The independently re-chosen density and rotation comparisons both pass at every frozen focus and in both regions:

| Reference | Maximum whole normalized RMS | Maximum crossing normalized RMS |
| --- | ---: | ---: |
| Polar4096, same phase | 0.0121560 (focus8) | 0.0219481 (focus6) |
| Polar16384, rotated phase | 0.00368828 (focus8) | 0.00523470 (focus8) |
| Golden1024, diagnostic | 0.0497379 (focus8) | 0.0925591 (focus6) |
| Polar1024, diagnostic | 0.0256525 (focus4) | 0.0879534 (focus4) |

The required bar was 0.75, with the same injected signal-dependent variance, not a newly fitted error allowance. A whole-region average alone would conceal the old sparse-pupil problem: original64 versus the candidate fails in the crossing at **all five** foci (1.05398–1.66607), and also in the whole region at focus8 (0.875116). The 1024 references agreeing with the denser candidate does not make 1024 physical truth or erase its previous disagreement with64.

The numerical conclusion is limited but useful: at these supplied constant depths, radius/PSF, native96 fields and five foci, the fixed16k operator agrees closely across resolution and angular phase. This removes the earlier sparse quadrature objection for this bounded forward model. It does not calibrate optics, establish continuum error, infer source ownership, repair free-visibility noise/colour failures, or show a successful inverse reconstruction. Adjoint comparisons here use fixed64; the dense cases commission forward evaluation only. Neither a dense inverse fit nor its derivative accuracy is an executed result of this run.

Runtime evidence is an operational receipt for this tiny commission. NVRTC12.8 compiled for compute120 with the declared precise options and an empty compiler log. Root observed 3.594 seconds overall; recorded setup/mechanics/density stages were 0.265/0.282/1.047 seconds. Peak job committed memory was 3,246,379,008 bytes; CUDA allocated and reserved peaks were separately 491,336,192 and 704,643,072 bytes. All limits passed and the job ended with no active processes or cleanup errors. The dense joint tables held 533–1625 entries, without a rays-times-image volume in the new kernel. These facts are neither a comparison benchmark nor evidence of full-RAW-stack speed or memory scaling.

Bindings: result SHA256 `8ae48a156f1a4ccfb175b13c97549503da1ce02de05882fff222bfba91c8e1c3`; kernel source `2be60901ed7a3ee8eb007c8611a4d690fe1ecc859ecaf6e375cb5cd0603e14d6`; independent controls `4393af7a18d875bea4bcc050dbc28b938908707e52e2b289cf0321afd6113e93`. Wrapper completion also verifies all bound source/runtime files unchanged. No parameter or acceptance bar was changed by this review.
