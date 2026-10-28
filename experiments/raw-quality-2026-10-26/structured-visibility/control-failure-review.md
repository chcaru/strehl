# Saved-alpha diagnostic stopped at its positive control

2026-10-26. **VERIFIED from source and completed failure receipts; no numerical replay by this reviewer.** The failed diagnostic establishes that this execution did not satisfy its prescribed constant-coverage response tolerance. It does not measure the effect of smoothing saved alpha, identify an unobserved coverage mode, validate a revised visibility representation, or change the earlier photographic rejection. No saved-field intervention was reached.

## What actually ran and stopped

Root invoked Python3.12 with `-I -B -X faulthandler` on `diagnose.py`, output `outputs/raw-quality-2026-10-26/structured-visibility-1`, through its bounded process controller. The child exited1 at `assert positive_error < .02, "known 500DN coverage response failed"`. Outer wall time was7.079seconds; the script timer reported6.469seconds. Peak job commitment was2,360,827,904bytes under4GiB, with no terminated or remaining owned processes. Torch reported CUDA12.8, Torch2.11.0+cu128 and RTX5090; allocator peaks were7,285,248allocated/25,165,824reserved bytes, excluding driver/compiler allocations. These are execution observations, not performance claims.

The output directory contains only `result.json` and `bindings.json`. It records `status=FAILED`, no RAW reads, no fit steps, no complete-stack output and unchanged bound inputs. It does not contain `changed-fields.npz`, controls success, prediction comparisons or reconstructed images. Loading the initial/final latent arrays and creating the smoothed-alpha counterfactual occur after the failing assertion in the source. The equal-color null assertion precedes it and was passed, but the original script did not save that scalar either.

Preserved identities: original `diagnose.py` SHA256 `2bfab73f488abc5ac611e9b84da74f7010e9cface89338b7eb68baa1b7f661cd`; frozen `layered-raw-inverse/pupil-stencil.py` SHA256 `2be60901ed7a3ee8eb007c8611a4d690fe1ecc859ecaf6e375cb5cd0603e14d6`. Both were rehashed read-only. Original failure files and implementation were not edited.

## The control's expected answer is correct

**DERIVED from the read implementation:** the shared-ray operator adds a near term `alpha*N` and a transmitted far term `(1-alpha)*F`, using the same pupil ray before aggregation. For constant supported sheets N=2000DN, F=1000DN, the exact response is `1000+1000*alpha`. Moving alpha from0.25 to0.75 therefore increases every supported prediction by500DN. The common normalized blur and bilinear physical-CFA query preserve constants in real arithmetic; adding black512 cancels in the prediction difference. This is not an opacity-estimation or photographic assertion.

With finite stored table masses, the exact-arithmetic difference becomes `1000*sum(marginal_weights)-500*sum(joint_weights)`. Both sums should be close to one because marginals are aggregated from the stored joint mass. That formulation does not promise that tens of thousands of sequential f32 additions reproduce it within0.02DN.

The checked source104 table uses16384 pupil points aggregated into56173 joint entries and887 marginal entries. Its recorded stored-joint f64 sum is1.0000000001073162. The CUDA forward adds all marginal terms, then all joint terms, into three serial f32 accumulators. It uses `--fmad=false`; no compensated or pairwise summation is present. **ARGUED, unconfirmed cause:** ordinary accumulation error could exceed a stringent0.02DN response bound even when coefficient mass and geometric sampling are correct. A close f64 sum of stored weights does not certify the actual f32 kernel's DC response. The failure's actual magnitude was not retained, so this review cannot distinguish a small accumulated bias from a larger arithmetic/runtime defect. It does not justify loosening the threshold or modifying the kernel.

The positive control is deliberately stronger than the preceding null in one respect. Equal N/F sheets with checker versus smoothed checker alpha compare two predictions against each other; a shared absolute bias can cancel. Passing that difference-only null does not establish absolute constant conservation or a correct derivative across two different constant alpha levels. The original historical forward/adjoint controls remain evidence at their stated inputs/tolerances; this new failure neither silently supersedes them nor becomes a success because they passed.

The current source checks a fully supported scoring apron before either control. Source104 shifts are approximately−15.71/−54.81native pixels, followed by finite bilinear support, the sigma0.7 common blur and the final bilinear query; the required66pixel margin exceeds that combined reach. Thus the documented zero-padding exception is not an evident explanation from the reviewed code. This is a source/support argument, not an independently rerun support measurement.

## Logging-only follow-up prepared, not executed

`diagnose-record.py` is a separate copy that saves the already-computed equal-color maximum difference before its assertion, then saves the already-computed positive response array plus minimum/mean/maximum, per-phase summaries, table metadata and maximum500DN error before the identical positive assertion. It writes `early-control-observations.json` and `positive-control-delta.npy` in a fresh output directory, also retaining the observation in the terminal result. No extra prediction is called; pupil, sheets, alpha values, sample support, blur, dtype, thresholds and later code remain unchanged.

Prepared copy SHA256: `24a2f08c685ee712d6b165683a4ff312674de2c8331cb489a37348186cb59a5a`. A parse-only AST check verified all17 original assertions remain identical; the original file was rehashed unchanged after creating the copy. No GPU, Torch import, numerical control or source decode was executed by this reviewer. Root may run the copy once with a fresh output directory under the existing envelope. Repeated failure with recorded magnitude would characterize this failed control; it would still not execute or validate the saved-alpha intervention.

The next permitted decision is bounded interpretation of that actual response, not a parameter campaign or alpha optimizer. Insect image quality remains the primary work. This numerical diagnostic provides no complete photograph or quality improvement.

## Root's single logging replay: diagnostic remains incomplete

**MEASURED by the root-run copy; VERIFIED against its saved receipts by this reviewer.** Root ran the unchanged logging copy once through `execute-visibility-record.py`, with fresh output `outputs/raw-quality-2026-10-26/structured-visibility-record-1` and process receipt `structured-visibility-job-record-1/process.json`. The exact child invocation was:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\experiments\raw-quality-2026-10-26\structured-visibility\diagnose-record.py' --out 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\outputs\raw-quality-2026-10-26\structured-visibility-record-1'
```

The expected failing exit code was 1, at the same positive-control assertion. Outer wall time was 3.734 seconds and inner time 3.218 seconds; peak job commitment was 2,225,192,960 bytes under 4 GiB. There were no terminated or remaining owned processes. The same Python 3.12.10, Torch 2.11.0+cu128, CUDA 12.8, RTX 5090 and single worker were recorded, with MKL, NumExpr, OpenMP and OpenBLAS thread counts fixed to 1. These are bounded-run observations, not speed comparisons; host load was not measured for a performance claim.

`early-control-observations.json` records the equal-color null maximum difference as **0.01025390625 DN**, passing the fixed 0.02 DN bound. The positive response has minimum **499.958251953125 DN**, mean **499.9586180480571 DN**, maximum **499.9588623046875 DN**, and maximum error from the expected 500 DN of **0.041748046875 DN**, exceeding the same fixed bound. All four physical CFA phases have nearly identical means (499.95861725–499.95861835 DN); the complete response array spans approximately 0.00061035 DN. The array is preserved as `positive-control-delta.npy`.

This is a small, nearly constant numerical response error in this control. Its form is consistent with the previously noted serial f32 accumulation hypothesis, but neither a precision ablation nor an independent kernel computation was performed, so the specific cause remains **UNVERIFIED**. The replay establishes the failed tolerance and its magnitude. It does not reject the visibility hypothesis, measure saved-alpha smoothing, or demonstrate a useful photographic improvement. No saved-alpha intervention was reached; `fit_steps=0`, `original_raw_reads=0`, `inputs_unchanged=true` and `photographic_quality_admitted=false` remain recorded.

This review is closed. The bounded saved-alpha diagnostic remains incomplete, with both original failure and logging replay preserved. No threshold, parameter, pupil implementation or optimizer was changed, and no further correction or numerical campaign is authorized by this review. Work returns to the primary insect photographic lane.
