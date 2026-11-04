# Independent HDR calibration source review

Reviewer: root/independent_review, 2026-10-28. Scope: isolated multi-stack worktree; read-only product review. Root owns all builds, RAW work and scheduling. This reviewer ran no Cargo, RAW decode, render, or UI control commands.

## Result and reviewed identities

VERIFIED by source inspection: no remaining blocker was found in the reviewed final HDR admission and gain-consumption paths after the supported-contradiction fix. This is not a photographic-quality or whole-scene calibration claim.

| Artifact | SHA256 |
| --- | --- |
| crates/strehl-cli/src/session-photometry.rs | 585fe0d44a048e4714fdba574fc6cf2ff2ca56e5df04f17b3a60faff8a6c8539 |
| crates/strehl-cli/src/session-consumer.rs | 4392797de7b7757bf3e82cd9874fd87f0253002d7cdfa858732ea90d47bb3165 |
| crates/strehl-core/src/session-fusion.rs | 9c81c65b6651eb5e78f491172f66165dcdeda83615dbc0c6bd5d5c6104fcabad |
| outputs/multi-stack/checks/photometry-suite-2.log | 110f2d34a1cde7ed3ed1a42612af20e52347d89f229d295b6f14add7a2936583 |

Review used bounded Get-Content line reads, rg symbol searches and Get-FileHash in C:/Users/chris/.codex/worktrees/multi-stack/strehl. Product sources were not edited. The preserved root test log starts with Compiling strehl-cli and ends with all 11 named photometry controls passing. This independently verifies the retained log contents; root remains the runner and source of process-exit/build-environment provenance. See challenge/hdr-calibration-implementation.md for its exact commands and environment.

## Closed blocker: contradictory acquisitions were being censored

The earlier finalize_pass selected only accepted pairs before establishing a pass-wide gain. Three good pairs spanning both tracks could therefore certify a scalar even while six fully supported nominated pairs showed incompatible color or exposure behavior. The renderer still consumed those acquisitions, so survivor-only agreement did not justify a pass-wide scalar.

The current assess_pair marks a supported excessive fitted correction as ContradictoryRadiometry at lines 448-451 and held-out spatial/color failure at 460-469. finalize_pass checks every retained pair for that kind and rejects before selecting survivors (547-564). All pair reports remain in the returned evidence. The new a09 control (1132-1178) calls actual assess_pair and finalize_pass paths with three spanning good pairs plus six alternating excessive-gain/color contradictions, then separately with six unavailable flat pairs. It asserts rejection and no corrected gain for the former, and permits the latter. Source inspection and the retained passing control close this specific finding.

Missing coverage/signal, flat-only overlap and textured correspondence disagreement remain UnavailableEvidence. That distinction is defensible for calibrating a scalar only where correspondence is supported, but it does not certify the omitted acquisitions' focus or illumination. The report states this limitation.

## Independent estimator, reference and null challenges

- Pair nomination is determined from geometry candidate flags, sorted source ranks, unique anchor/source acquisition indices and a deterministic at-most-nine sample across nominees (689-733). This avoids choosing pairs by favorable radiometric residuals. The candidates remain geometric hypotheses, not physical focus correspondence.
- The scalar estimator uses the log median of all four-color fitting-patch ratios. Fixed checkerboard spatial validation patches are excluded from fitting, and median, p95 and maximum residuals are tested. The maximum catches a localized adverse patch which a percentile alone could conceal. A final scalar from accepted pair fits is revalidated against pooled held-out values (588-617), closing the per-pair-fit self-consistency loophole.
- The anchor is an explicit primary when present, otherwise the alignment reference. It fixes output exposure units; it is not an independently proven ground truth. The anchor pass itself is not calibrated against an external illumination standard.
- Independent sources and at least three accepted pairs spanning half of both tracks constrain repeated-frame pseudo-evidence and a narrow focus interval. They cannot establish calibration everywhere in an arbitrarily long pass. At most nine pairs and the fixed patch grid are a stated bounded sample.
- Whole-patch eligibility requires original coverage and uncensored contributing CFA taps across all four colors. Positive signal is checked against the supplied model. This prevents black/missing/clipped values from fitting the gain; it also means conclusions apply only to retained supported patches.
- Centered textured compatibility rejects flat-only agreement and strong detailed mismatch. Its conservative noise allowance is an eligibility heuristic, not a fitted sensor-noise model or a measurement of temporal variance. It neither proves equal physical focus nor certifies arbitrary unsampled lighting changes.
- The flat, color, spatial, local-flare, blur/misregistration, clipping/missing-coverage, gain-squared variance, sparse/rank, pooled-final-scalar and survivor-selection controls are relevant mechanical falsifiers. Passing synthetic controls does not establish highlight recovery, motion robustness, or superiority to ordinary stacking.

## Integration and memory checks

VERIFIED by source inspection: session-consumer.rs 580-599 adds numerical workspace, retained report estimate, source-cache budget and decoder allowance before calibration. The module separately bounds numerical plus report storage (661-668); one reusable full-domain sampler and two compact patch sets avoid an aligned frame volume. Source identities are unique and each injected model must be trustworthy; original level values are checked bit-for-bit before sampling (637-657, 738-746).

The consumer writes photometry.json before require_gains, so a failed calibration retains its refusal evidence. Every target must supply a gain; no nominal fallback reaches the renderer. Total corrected gain is passed to prepare_with_masks at session-consumer.rs 383-397. session-fusion.rs 384-425 scales signal once and propagates injected absolute variance in original source units times total gain squared. The measured transfer beta is applied afterward. This is the required unit relationship, not a private noise estimate.

## Evidence still needed

UNVERIFIED by this reviewer: end-to-end HDR runtime acceptance on the user's full capture set, actual completed HDR photos/masters, photographic highlight/color/detail quality, full-session performance, and latest desktop result presentation. A clean refusal on the focus/flare-affected data is a valid result and must not be re-described as HDR recovery. Full outputs and native crops need one frozen display transform plus appropriate unchanged ordinary and joint-geometry controls before quality claims.
## Final lint-only source freeze

VERIFIED: current session-photometry.rs SHA256 is 66763ae97e9870f54fb4d305c87473f7d820ed5d8cdc0b9df19a742642aad1f3. Reversing exactly the disclosed collapsed candidate if-let guard and the clipped-anchor fixture parity expression is_multiple_of(2) in memory reproduces the prior reviewed SHA256 585fe0d44a048e4714fdba574fc6cf2ff2ca56e5df04f17b3a60faff8a6c8539. No source file was rewritten by this check. This establishes that the final cleanup has no additional source differences; arithmetic and admission conclusions above still apply. Compilation of this last syntax cleanup remains root-scheduled.
