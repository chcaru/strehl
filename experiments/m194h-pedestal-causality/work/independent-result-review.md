# M194h independent result interpretation review

Reviewer: pedestal_result_review, 2026-09-08 UTC. Saved artifacts only. No candidate, control, decoder, trace reconstruction or numerical checker was executed by this review, and no experiment source was edited. The experiment-decision and preregister were read before judging the result.

**VERIFIED narrow causal diagnosis; no product-change admission.** The actual cutoff intervention removes positive sub-floor weight in the primary pixel's complete inverse support and restores its HardFloor result. Re-choosing the assessment from the selected primary pixel to the predeclared secondary pixel and fixed window reverses the apparent quality conclusion. P0 also restores the secondary HardFloor defect, and loses much of P's flat-window benefit in every RGB channel. A successful explanation is not a successful repair.

## Actual completion and artifact association

The root wrapper's saved actual outer record is `work/independent-external-1-outer.json`: exit 0, no timeout, 4.672000000005937 seconds over the complete directly launched wrapper interval, empty stderr and raw exit `0\n`. Its raw stdout authenticates `independent-run-1/result.json` and `parent-tail.json`; the tail authenticates the same result. The wrapper identifies the actual child record and final checker result. The child's actual exit is 0 with direct exit, pipe EOF, terminal Job accounting, zero active processes, completed drain, no termination attempt, no cleanup errors and no error. Its command matches the fixed release after substituting that release's actual SHA256 and the actual checker source SHA256 into the two explicitly named placeholders. The first read-only review assertion compared the unexpanded template and rejected; reading those literal placeholders resolved that metadata mismatch. No subject or checker rerun followed.

**VERIFIED by direct saved-byte equality:** `independent-run-1/child-00.log` is exactly `independent-check-1/result.json`, 73,974 bytes, SHA256 `38ba525e7480887a4e9ae527aa122b03e2791edd66423fc1724bde560774dc83`. Source and release references, external raw streams, wrapper result/tail, child record/log, and all three arms' off/on/placebo TIFF references were rehashed from disk. Each arm's three TIFF byte buffers are identical.

The child records 1.0625 seconds of Job CPU and peak Job committed memory 80,216,064 bytes. The wrapper tail's parent CPU sample plus completed-child CPU plus reserved final allowance is 6.453125 seconds, within 60; this is a sample plus allowance, not independently measured whole-wrapper CPU. Actual outer wall fits its tail sample plus 3-second allowance and 120-second cap. These are completion/resource observations, not performance comparisons. The checker says `PASS_INDEPENDENT_SAVED_CONSUMER_CHECK_ONLY`, `independent_complete=true`, `subject_complete=true`, `verified_science_complete=true`, and `quality_go=false`.

The executed checker command is retained verbatim in `independent-run-1/child-00.json` at `command`; it starts with Python312 `python.exe -I -B`, invokes `independent-verify.py` with release SHA256 `79a8aa4ae9f5fe97115475f8365683c418e331fdede80b4fa7812c9e9b096e09`, source SHA256 `5ca8bd3628b6cde0d417215b3c3fb9b83af4ef35ba21e139cbefc3c6867356f6`, and writes `independent-check-1`. This review did not repeat that command. The review's separate read-only command was Python312 `python.exe -I -S -B -c` with JSON parsing, `Path.read_bytes`, byte lengths, SHA256 and explicit association assertions; tool call chunk `d6fd1e` returned `saved_associations: PASS`, exit 0. No NumPy import or image decoding occurred in that command.

## Predeclared interpretation, with exact JSON paths

All numerical paths below are in `independent-check-1/result.json`. Array indices are zero based. H/P/P0 off cases are 0/3/6.

| Assessment | Saved outcome | Exact numeric path |
|---|---|---|
| Primary red native (202,104), P to P0 absolute ideal error | 43.68697857197549 to 0.04025115259946688 DN; P0 equals H | `science.diagnostics.sites[6].absolute_error_dn`, `[12].absolute_error_dn`, `[0].absolute_error_dn` |
| Primary signed error | +43.68697857197549 to -0.04025115259946688 DN | `science.diagnostics.sites[6].signed_error_dn`, `[12].signed_error_dn` |
| Secondary red native (205,113), P to P0 absolute ideal error | 35.61110642077665 to 117.17485098474981 DN; P0 equals H | `science.diagnostics.sites[7].absolute_error_dn`, `[13].absolute_error_dn`, `[1].absolute_error_dn` |
| Fixed red window, P to P0 | 61 pixels improve by more than 10 DN; 320 worsen by more than 10 DN; 3,584 pixels | `science.diagnostics.paired_window[3].improvement_gt10dn`, `.worsening_gt10dn`, `.count` |
| Fixed green window, P to P0 | 25 improve; 362 worsen by more than 10 DN | `science.diagnostics.paired_window[4].improvement_gt10dn`, `.worsening_gt10dn` |
| Fixed blue window, P to P0 | 65 improve; 317 worsen by more than 10 DN | `science.diagnostics.paired_window[5].improvement_gt10dn`, `.worsening_gt10dn` |
| Fixed-window red MSE, P to P0 | 191.09414623437246 to 302.46446029772176 DN squared | `science.diagnostics.fixed_window[3].channels[0].mse_dn2`, `[6].channels[0].mse_dn2` |
| Fixed-window green MSE, P to P0 | 133.82983562911625 to 284.9111286051119 DN squared | `science.diagnostics.fixed_window[3].channels[1].mse_dn2`, `[6].channels[1].mse_dn2` |
| Fixed-window blue MSE, P to P0 | 210.84875697908555 to 336.158180506826 DN squared | `science.diagnostics.fixed_window[3].channels[2].mse_dn2`, `[6].channels[2].mse_dn2` |

The window remains native x=[104,216), y=[104,136). This is paired finite-window evidence from one previously selected noisy realization, not a repeat distribution or confidence interval. MSE can reward flattening actual texture; it cannot establish texture preservation. Here the fixture is flat, so the whole-window result is directly relevant to the stated noise/error tradeoff, but it remains a development case. Both selected sites were discovery cases, and their two opposite movements are not independent replications.

## The intervention was exercised, and the hull matters

`science.trace_consumer.primary_has_actual_removed_mass` is true. In `primary_inverse_support_partition[0]`, level 0 index 7296 has nonzero inverse coefficient [1,1], removes weight `3.3253328979299113e-07` from frames [0,2,3,4], fraction `0.7975394016406955`, and does not use mean fallback. The retained resolved coefficient is P `28.624650955200195`, H/P0 `-4.770263671875`. Additional rows retain the rest of the complete support; a single coefficient is not the explanation of the final pixel by itself.

The actual final primary CFA operand before the hull is P `2282.6845703125` and H/P0 `2249.6435546875`; the unchanged [2250,2313] hull clamps H/P0 to 2250. Those values are in `science.trace_consumer.selected_consumer_hull_and_signed_mhc[1/0/2].cfa_hull_operands[0]` under `pre`, `lo`, `hi`, `post`. Thus the selected improvement includes the unchanged hull's mediation; its near-zero final error is not proof that P0 universally recovers the ideal. Above-floor weighting remains P's by design, and P0 is not globally equivalent to H: the fixed-window MSEs and H-to-P0 paired rows differ.

The saved independent controls reject the actual classification-bit corruption, omitted nonzero primary support and doubled positive P weight, then restore the original row/support. Their exact path is `science.trace_consumer.independent_faults.faults[0..2].rejected` with `restored_partition`, `restored_support`, and equal original/restored row hashes. This is independent saved-checker evidence of powered controls; this review did not execute them again.

## Judgment and next action

There is no completion or interpretation blocker in the reviewed association. The primary-site hypothesis succeeds under its original conditional wording. It does not establish that sub-floor mass is generally bad: that same intervention removes the predeclared secondary benefit and worsens most threshold-crossing paired changes and every fixed-window RGB MSE against P. Report both directions together. Do not call this a SOTA result, select new favorable sites, tune the cutoff, replace the common ideal, or promote P0/experimental P to the product default.

**ARGUED next action:** close this explanatory experiment and retain HardFloor as the current default. Prefer the next concrete program consumer task over treating this particular global cutoff as an already promising repair. If pedestal quality work is resumed, first fix a separate decision question about average error versus sparse tail error on independent repeats plus texture, using unchanged H/P/P0 and powered texture-collapse controls. The present result supplies the tradeoff to test; it supplies neither temporal uncertainty nor a shipping decision.
