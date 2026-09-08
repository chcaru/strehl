# Independent M192e rehearsal 1 saved-output read

VERIFIED saved evidence, 2026-09-08. The three-call rehearsal completed naturally and retained byte-identical TIFFs, linked terminal accounting and recoverable checkpoints. **Sampling/integration failed**: off failed the unchanged 100 ms maximum-gap bar; on and placebo passed. `PASS_BOUND_TERMINAL_REHEARSAL_ONLY` is an artifact/accounting result, not full integration, a 133-call campaign certificate, or timing-transition causation.

I read frozen sources and retained metadata, independently hashed outputs, reconstructed timestamp intervals and checkpoint unions, and checked terminal arithmetic. No product call, RAW read, image decode, model/fit, or authored-verifier rerun occurred. One ad-hoc read initially used the wrong advertisement field (`terminal_tail`); actual fields are `tail` and `sample_after_tail`. The corrected read passed. Three shell inspection typos were read-only failures; no subject evidence changed.

## Released commands and identity

Source commit `04a353e4d77e46b8e9cf9c2111fd8e111efe6707`; release `ae31343c0aa9a574e7f53b9893e1c71fc2325b56`; retained evidence archive `d273ba8437174bb13a6cb86211a7a9105bf1b9b3`. Let R be `C:\dev\blog\death-of-software\projects\strehl`, E=`R\experiments\m192e-campaign-runner`, P=`C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe`, and H=`9A8BFCEF7DA8F6BBF1927ADCB99039CD1D679DA851DEB99367C9A1D836A40D73`.

Actual command arrays retained in the two outer receipts are exactly:

```
P -B E\launch.py --plan E\preparation-1\plan.json --plan-sha256 H
P -B E\verify.py --plan E\preparation-1\plan.json --plan-sha256 H --outer E\rehearsal-1-outer\outer.json --outer-sha256 58F2505E97F5F2FFB2A2203BD5194F06E993955E25B560E012176B3AFE34D3F5
```

These abbreviations expand literally to the paths above. The launcher ran `P -B E\run.py` with the same plan/hash; its worker adds only `--worker`. The worker retained exactly three invocations, sequence 0/1/2, `native-n33-w8-off/on/placebo`, N=33, W=8. All three underlying sampler modes are `on`; the outer mode controls persistence. The unchanged product argv is the pinned binary followed by `stack D:\personal\macro\bee-1-cpl --limit 33 --out E\rehearsal-1\work\outputs\native-n33-w8-MODE.tiff --merge pyramid --pyramid-gate 2.0 --resampler catmull-rom --cover scale --linear-srgb --demosaic`. Actual invocation/log associations and terminal markers agree. I verified the plan's source FileRefs and the saved before/after input manifests, without opening RAWs.

Critical SHA256 pins (bytes):

- plan (6921): `9a8bfcef7da8f6bbf1927adcb99039cd1d679da851deb99367c9a1d836a40d73`
- final authored verification (3086): `a0f4f50e8f2b2c96778966b0714fbe3b6b84b94ace30c11084ba4ea7a784ee10`
- verification outer (895): `608920b43af5ffc76caa32bafe6978f227ef5947ccf1fdd4fc6b1103ab9d685`
- full launcher outer (601): `d30b7acbfbf77050bf1acf68240318445745a350dc826b467153f4aafce01f33`
- parent terminal outer (8192): `58f2505e97f5f2ffb2a2203bd5194f06e993955e25b560e012176b3afe34d3f5`
- parent canonical (65536): `760b11c100e977e3f1de0368bf49bc9de1d146243dd458ebae5b4af70e86b15e`
- worker canonical (65536): `7f82f2cf34564dd5f8ebe96556c6cfabebe8f2cd6965b7ac80f0227f4ced0076`
- controls (18392): `59311aa2ce4ec688acc2bcaf06befc3d3640f94eb7c79b0d062221dd688e6c9e`

## Re-chosen sampling boundaries and grouping

The frozen rule is max interval, **including start-to-first-observation and final closure**, <=100 ms, with coverage >=0.9. Coverage is sample_count/(sample_count+missed_intervals), not a continuously observed fraction of time.

| Persistence mode | Samples / missed | Coverage | Max gap ms | Final gap ms | Disposition |
|---|---:|---:|---:|---:|---|
| off | 3159 / 14 | 0.9955877718247715 | 117.8844 | 0.0467 | FAIL |
| on | 3161 / 59 | 0.9816770186335404 | 54.4005 | 0.5236 | PASS |
| placebo | 3156 / 64 | 0.9801242236024845 | 50.1861 | 0.0322 | PASS |

I grouped by timestamp/poll identity, deduplicating overlapping final tails, incident context/following, and both surviving checkpoint generations. Conflicting duplicates would fail. The union contains respectively 1000/1161/1156 observations and 4116/4970/4943 unique phase events. Each arm has one distinct gap incident. Consecutive retained observations plus incident endpoints and final closure independently reproduce all three recorded maxima. This is not reconstruction of evicted full histories: aggregate missed counts and unseen maxima remain recorded witnesses, and no timestamp-union operation licenses a stronger complete-trace claim.

The off incident is start `33814477751300` to first observation `33814595635700` ns. The first phase starts `33814589750900`: **111.9996 ms precedes the first measured phase**. That first phase ends 0.0063 ms later, explaining the alternative 112.0059 ms number. The union of four measured phase intervals inside the failing gap covers only 5.8397 ms, including process-table 5.7187 ms. Thus phase maxima cannot explain this gap. The original start is before system/memory/Job creation, log opens, suspended Popen, assignment/resume and first polling phase. Existing evidence cannot partition the 111.9996 ms among those operations. A suspended process can already hold memory: it is incorrect to describe all pre-resume time as unexposed. Off wrote zero production checkpoints, so this failure is not caused by its production checkpoint writes.

On's worst gap follows observation poll1999; 54.2678 ms lies before the next Job-accounting phase. Placebo's follows poll1899; that intervening portion is 49.9112 ms. Only 0.0961/0.2129 ms respectively is covered by measured phase intervals inside these gaps. The source's synchronous every-100th `observe` checkpoint lies there. This identifies a source-compatible location, not measured serialization/fsync duration or a causal timing effect. Runs occurred once in fixed order; no claim that instrumentation improves cadence is justified.

## Output, recovery and terminal evidence

Independently streamed all three complete TIFF files through SHA256 with unchanged before/after file identity. Each is 197798956 bytes, SHA `3309e33318c701fb75c55507bfb49ad279d8950492b592ec247dbe2d1193ac9e`. Whole-file equality suffices for nonperturbation. Pixel hash `6efc261e892dcdb5d492ad3fd79bdc7e5a208d93d0227a41b258fb3b900f9b89` is the retained authored decode witness; I did not independently decode it. Seven old output identities were rehashed, and their before/after preservation manifests are identical.

All eight storage-control receipts are present. I checked padded injected-generation bytes/hashes, the separately retained `TRACE_OVERFLOW` refusal, before/after generation equality for partial/overflow cases, and restored linked generations. Three re-sealed identity/chain faults retain their actual rejected bytes and restoration. The restored publisher's canonical equals its first-positive bytes. These are controlled storage-path tests, not a real crash/power-loss trial.

On/placebo each exercised 31 actual production checkpoints; surviving sequences29/30 link by full-file previous hash. Their overlapping observations equal final observations. Off has only the initialized sequence-1 slots. All recovery receipts say `RECOVERABLE_INCOMPLETE`, `may_resume=false`, `may_certify=false`. Evictions remain explicit (off/on/placebo observations2159/2161/2156; events12333/12345/12318); recovery is not complete trace persistence.

Parent and worker first-positive files equal their canonical files. Unique advertisements bind exact tails/canonical/plan/PID and later samples; both canonical/tail records explicitly require an outer exit. Child terminal Job is inactive, natural exit0, direct-exit/pipe-EOF/drain complete, no termination or cleanup errors. Same-parent-handle creation identity matches before/after GetProcessTimes; terminal user+kernel CPU is 5.40625 seconds. Worker terminal Job CPU is 425.984375, including worker descendants. Combined is **431.390625**, below600; the enclosing Job independently records that same total and is not added again. I checked exact integer user+kernel sums. The verifier's wrong-total/negative-user/bool-active controls are retained, with restored original witness.

Parent post-tail sample is5.390625 CPU/103.688 wall, below actual terminal CPU5.40625 and103.75 whole-parent wall. Worker post-tail is8.984375 own CPU/101.735 wall; terminal worker Job includes it. Each saved publication interval is .03125 CPU/.031 wall, inside2/3. Whole launch helper exits0 at103.88999999999942 wall; its sample103.86000000000058 plus .5 covers the full interval. Separate wrapper CPU sample .453125 +.25 reserve is .703125 <=5; no measured complete-wrapper-CPU claim. Authored verifier exits0 at1.639999999999418 wall, stderr empty.

`Get-ChildItem -Recurse -Force -File` independently finds62 subject files/633163043 bytes plus3 outer files/9279 bytes, total633172322 <1GiB. The1GiB limit is retained storage, not RAM; observed child committed-memory peak3916533760 fits its8GiB Job limit. Subject bounds remain600 CPU/240 wall, worker210 wall, separate launcher5 CPU/255 wall. This successful finite rehearsal leaves **integration_pass=false**, **sampling_all_pass=false**, **full_campaign_certificate=false**. A bounded startup-attribution probe may be useful, provided it preserves the original clock/gate and separates recorded operation timings from OS-cause inference; no product rerun or changed acceptance bar follows from this read.
