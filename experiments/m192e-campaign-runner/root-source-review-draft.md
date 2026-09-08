# Root source review of the paused M192e draft

SOURCE-READ, 2026-09-08. No import, control execution, product invocation or RAW access. These are pending checks for the already assigned M192e continuation; they do not commission the runner or identify the historical sampling failure. Complete the active M193c operational replacement before resuming this source draft.

- `durable.py`: 10210 bytes, SHA256 `3b04d925466d0470747ce9b1efce651c0a86e94017384f526a55edbdeed610e7`.
- `run.py`: 26568 bytes, SHA256 `2e21645adf391d8d7bd9d3a372b403b64399db640a92f33ce25466e4b4ad7162`.

1. `install_trace` writes only every100 observations. The three-run acceptance checks natural exit, markers, restoration and output identity but does not assert a positive checkpoint count in on/placebo. A run with fewer100 observations can therefore pass without exercising the adapter's durable publication during production. Add an explicit exercised-case assertion or retain an independently bounded integration control reaching that path; distinguish a storage-only control from an actual production observation. No statement that the present N33 fixture does or does not reach100 is measured here.

2. `Budget.family` recognizes root `child.json`, but its suffix check for the four publisher filenames requires a slash. Current parent/worker publishers use subdirectories and satisfy it; root-level publisher filenames do not. Keep the supported path domain explicit and test it if generalizing the runner. This is not a demonstrated defect in its present parent/worker paths.

3. `binding` and the output-root predicate call `resolve()` before checking `is_symlink()`. The predicate consequently describes the resolved target, not whether the supplied path was a link/reparse point. Preserve the actual intended identity contract; if the claim is no unresolved link input, inspect the original lexical path before resolution and use the existing Windows reparse attribute discipline. The observation is a source semantics issue, not evidence of a link in the actual corpus.

4. A4MiB checkpoint writes, flushes, replaces and hashes in the observer callback. This is bounded storage but may add sampling latency. The fixed off/on/placebo outputs and explicit sampling-gap result must decide the integration outcome; no timing overhead value or100ms pass follows from the source. The new sampler is the measured subject on this seam, so retain the maximum gaps even if TIFF bytes match.

5. Preserve the split between a recoverable INCOMPLETE snapshot and certification. `recover` currently returns may_resume=false/may_certify=false, which is appropriate. Commission rejection of changed campaign/run identity and inconsistent generations using re-sealed metadata; merely reproducing valid payload hashes does not challenge that association.

The next actual action remains completing `verify.py`, preregistration and a fixed release with independent review, then the previously proposed three N33/W8 invocations. A fresh full133 campaign is not authorized by this draft review.
