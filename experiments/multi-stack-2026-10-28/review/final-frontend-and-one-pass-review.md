# Final frontend lint and one-pass routing follow-up

Independent reviewer root/independent_review,2026-10-28. Read-only product inspection; no builds, RAW decodes or renders run in this lane.

## Latest frontend lint

MEASURED lightweight review commands, each exit0:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/review/lint-audit-3.py
    python -X faulthandler -I experiments/multi-stack-2026-10-28/review/lint-diff-map-3.py

Input outputs/multi-stack/checks/frontends-clippy-3.jsonl SHA256 aac5d432dd69530bfccf2a9bc89f53d61d52f629c9075005e82d801fb80bfd84. The retained text log shows Compiling strehl-cli and Checking strehl-ui. JSON build-finished success=true.

VERIFIED:159 compiler warning records deduplicate to106 unique diagnostics and53 repeats after normalizing included source aliases. Of106sites,105 exact diagnostic spans map to unchanged baseline source/diff blocks against c149e52834fc1c86c2af0fe022713c39fa25f33c. The remaining large_enum_variant has the same inherited size cause: largest Stack fields and second-largest Align definition are unchanged; added Session is not the size cause. There are91crate-source sites and15experiment-include sites. No new diagnostic site remains in this log. Per-site source text, hashes, baseline locations and unchanged-block evidence are preserved in lint-span-audit-3.json.

This is warning-enabled success, not a strict -Dwarnings-clean claim. The earlier three new logical sites, including five duplicate warning records, are absent. The latest log covers the subsequently added session modules as built in that run; it does not prove unlogged future source changes lint clean.

## One-pass alignment guard

VERIFIED by source inspection: session-cmd.rs route_single_pass only returns a SinglePassCompletion for eligible one-directory, one-pass Combine/Repeat sessions. Existing ordinary commands return unchanged with None. The routed session reserves an isolated destination and sets STREHL_WARPMAP to its own warpmap.txt before any worker startup. SinglePassCompletion::alignment_args builds the ordinary Align command with the actual input directory, isolated map path, threads and resampler (214-231).

lib.rs calls prepare_alignment only when that completion is Some, after ordinary Stack environment/options configuration and before merge_cmd::run (1291-1294). Ordinary commands with None do not gain this call. Alignment failure propagates immediately; merge failure propagates through result? before completion.finish (1364-1366). The guard then re-resolves the exact census, rehashes originals, checks both output files, and only publishes completed.json after success. The adversarial test also checks the constructed ordinary alignment arguments, source-addition refusal and content-change refusal.

The retained real-run outputs/multi-stack/single-route-6/regression.json reports299sources, a newly solved isolated ordinary alignment and zero differing channels for both7032x4688photograph and float master against the unchanged baseline. Whole-master SHA256 is identical b97188c458778aa058257207868b530e7fcd8a38528b6d3e340e7bf229b142a5. The photograph file hash differs while pixel channels are identical; root reports the expected Software/build metadata difference. This reviewer read the receipt, not an independently rerun TIFF comparison. Timings overlapped other work and are not performance evidence.

No blocker found in this follow-up's reviewed guard or diagnostic classifications.
