# Independent read: startup attribution 1

VERIFIED SAVED NEGATIVE OUTCOME, 2026-09-08. The one released subject stopped at the worker's committed-memory limit before any of the five arm records existed. The frozen checker completed its negative read: VERIFIED_PRIVATE_STARTUP_NOT_COMMISSIONED, not AUDIT_INCOMPLETE_NO_ADMISSION. Nothing here commissions startup attribution or repairs the historical117.8844ms sampling failure. This reviewer read saved metadata, source and complete small output bytes only; no subject, checker, monitor, native API, image or control was executed.

## Authority and commands

Plan6151B SHA256 fbf293dffc9c6da8e73852fc4d2e0563e0d0965a9f3be25ea3e76287fb92a5f4. Subject source24534B/48698b704042766c24aaeb5fe674d493e628cc58397ec0823e4c10a4a30afe44 and checker37387B/ff31a1edf0a632d487329f06923cde85be2dc1f8d1dfa36903216be2f140674e remain unchanged. Subject source freeze b417f402357dace9e39f8b64556f1aa52285b4ee; checker/root review freeze e85b1d0d. Release1698B/8ce381c38e4d8e75bc01fce459007030b999328e6ff16dd0936b9faa3c331cfd names one five-null-child attempt.

The exact expanded subject and checker argv arrays are in the two pinned outer JSON records below and were checked against the plan and released hashes. The subject command is the pinned Python312 python.exe, `-B`, the absolute startup-attribution-run.py path, `--plan` with startup-attribution-plan-1.json, and `--plan-sha256` with the full plan digest above. The checker command uses `-B startup-attribution-audit.py` and all eleven source/plan/outer/stdout/exit/result/worker path/hash options in its retained command array. No command was replayed by this reviewer. All paths below are relative to `C:\dev\blog\death-of-software\projects\strehl\experiments\m192e-campaign-runner`.

| File | Bytes | SHA256 |
|---|---:|---|
| startup-attribution-1-launch-outer.json |725|9cb4f98ef32cd7c2046ca484695f06bb8e51510d2c06241dbe464e2df76769d2|
| startup-attribution-1-launch-stdout.bin |505|7d14fc4ef49d9cd1b131b5f3b37f75ae5e3bd3936e12c111a23302fb00baf2cf|
| startup-attribution-1-audit-outer.json |1730|e94cfd446112ddd249f6b549ef69ba54c49f9ef724817193de07841f05fd02da|
| startup-attribution-1-audit-stdout.bin |8575|c1b06f21c545bfd895b3e6494ce6decb21acb15e6556933bdf355c5a58cfa7df|
| startup-attribution-1-audit-progress.json |2766|b4e9150fe814851a925df0861b009f63834a2b18a2f881b9d336621559210393|
| startup-attribution-1/child.json |1737|7c0fa886e5d4cae9e94774b63205fb0b7c221e1fd7ff623bc30ab7d62547f7a1|
| startup-attribution-1/parent/result.json |32768|60739d48a4288a4eeee0c84f84d3f6e56f4ab5408f288daecbfa76c32fe60c24|
| startup-attribution-1/worker/result.json |32768|30b039fc3c4e5c140e6618160d8751551def4f1ea54efddbab4e51de57186ded|
| startup-attribution-1/worker.log |1|c4694f2e93d5c4e7d51f9c5deb75e6cc8be5e1114178c6a45b6fc2c566a0aa8c|

Both external exits contain `1\n` (2B, SHA4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865). Both external stderr files are empty (SHAe3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855). Full slot encoding/padding, child/worker links, all nine inventory hashes and the actual advertisement were read independently.

## What the failure establishes

The configured Job limit readback is536870912 bytes,512MiB, flags8704/0x2200 (Job committed-memory limit and kill-on-close). Saved peak Job memory is561917952 bytes =535.88671875MiB:25047040 bytes above that limit. Peak process memory is560664576 bytes. These are committed-memory counters, not RSS, available RAM or a claim about image buffers. The named error is `ValueError('child committed-memory bound')`.

Owned termination attempted/succeeded are true. The pretermination snapshot has two active processes; the final snapshot has zero. Terminal Job accounting is true, but direct_exit_observed and pipe_eof_observed are false, post_exit_drain is null and the owned exit is0xe193c0de. Cleanup errors are empty. This establishes final accounting after intervention, not natural completion. The two-process count does not identify the second process or its purpose.

All four worker slots are byte-identical INITIAL_INCOMPLETE refusals. The parent retains a detailed REFUSED result with `natural actual worker tree`. No arms directory, startup-phase records, monitor observations, null output or private child receipt exists. All five names remain unvisited. Source creates an arm directory before invoking that arm, so this prefix precedes that durable boundary. Source loads the inherited sampler before the loop; that position does not identify the allocating library, call or cause. The only worker-log byte is ASCII `O` (hex4f), insufficient to infer an OOM message, OpenBLAS message or another diagnostic. No startup-control measurement was obtained.

## Accounting and capacity re-choice

Independent arithmetic:781250 user +937500 kernel =1718750 ticks,0.171875s complete owned Job CPU. Parent CPU was separately sampled at0.171875s. Count the Job once: parent sample + Job +0.25s reserved publication tail =0.59375s, below20s. Do not add the inner process count or an imagined null Job. Parent CPU remains sampled, not measured through process exit.

Subject outer0.4690000000045984s fits30s and parent sample0.4219999999986612 +0.5s. The checker's resource_admissible=true is its CPU/wall/accounting-error predicate; it does not test memory in this refused branch and is not overall resource acceptance. Clean completion, subject_complete, commission_pass and admission_allowed are false.

Checker sample0.125CPU/0.09399999999732245wall plus its0.25CPU/0.5wall reserve fits10CPU/20wall. Actual checker outer0.125s fits that tail, with empty stderr and a complete8575B negative JSON. Exit1 means uncommissioned evidence. Preserve the actual negative record and failed costs; a later attempt cannot relabel this passed.

Force census and complete-file hashing give9 files/231114 bytes. Parent's sampled inventory263882 differs by one32768-byte slot, consistent with subsequent staging consumption; this is not another permanent payload or a memory quantity. Twelve sources total306162B. Sources + plan + actual subject outer/stdout/exit + outputs total544659B, below4MiB; outputs alone fit3MiB. Checker artifacts/report fit its separate1MiB family. A reviewer-only inventory assertion initially used Windows Path ordering; sorting the unchanged records by the reader's relative-string key yielded exact equality. The first report draft8441B failed the8KiB prewrite guard and wrote no file. Neither actual process was rerun.

## Bounded next step

A fresh resource-only startup2 with a1GiB committed Job limit is a justified finite operational hypothesis. The observed535.8867MiB peak exceeds512MiB and is below1GiB; that does not prove the later peak will fit. Preserve startup1 source, plan, outputs, negative audit and costs. Use versioned source/plan/output/audit names and bind this failed evidence into the new release.

Change only explicit memory authorization, configured Job limit, independent expected-memory checks and required fresh version/path/authority bindings. Preserve the five arms,150ms delays, sampling origin,100ms/90% gates, native call order, output identity checks, CPU/wall/output bounds and failure retention. Prove and independently review the source delta first. Do not substitute another sampler or bypass initialization to fit the cap. Another memory refusal remains operational failure; an untreated sampling failure or mispositioned delay remains uncommissioned. No automatic further increase, product rerun or changed sampling gate follows.
