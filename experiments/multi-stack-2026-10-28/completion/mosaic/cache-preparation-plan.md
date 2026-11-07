# Bounded original-cache preparation

The complete 827-source campaign exposed a serial preparation phase: one RAW
decode and cache publication ran at a time, before pair measurement. Root
observed approximately 4% host CPU during this phase. This observation motivates
the additive prefetch module; it is not a measured speedup claim.

The mosaic consumer now prepares missing original cache entries before creating
its main resident cache, alignment guides or merge buffers. Each independent
worker owns one bounded `SourceCache` and a disjoint source-index sequence. It
uses the unchanged `load_or_decode` path, then drops its returned handle before
the next source. A dedicated Rayon pool caps both worker tasks and nested
decoder work. The maximum is 16 workers, further bounded by requested workers,
source count and the explicit memory limit.

The checked reservation includes one active u16 resident slot, four padded
decoded-frame buffers, the largest original file, a conservative cloned-session
and publication/control allowance, and a 2 MiB thread stack per worker. The
padded dimensions use the existing alignment preflight's 256 extra rows and
columns. A separate 512 MiB fixed allowance covers orchestration. Impossible or
overflowing plans are refused. Actual decoded identity, active dimensions and
padded buffer size are checked against the same header bounds.

Existing named cache files are skipped only as a scheduling decision. The report
calls them `existing_entries_deferred_to_consumer`; it does not call them valid.
Normal consumers still read and verify every cache entry before using its bytes.
A corrupt named file is neither silently overwritten nor decoded again by the
prefetcher. Atomic publication, decoder version, original identity hashing and
cache representation remain unchanged.

This patch changes the mosaic renderer's source provenance. It does not edit
any input to the `session-align` or mosaic-geometry algorithm hashes. A geometry
envelope from the current full campaign therefore remains eligible for normal
binding verification after this scheduling-only change; unrelated later edits
to consumed geometry/focus code may legitimately invalidate it.

Prepared controls exercise serial/four-worker synthetic publication through the
real cache, compare complete cache bytes, verify all four unique identities
exactly once, verify warm zero-work behavior, and require the normal consumer to
reject a planted corrupt warm cache. Planner controls cover joint reservations,
the worker cap, an impossible budget and checked-arithmetic overflow. Root owns
the fresh compile/test and all RAW scheduling.

The proposed real measurement is a bounded, fixed small source census with two
fresh cache directories: one requested worker versus four. Use identical source
identities and a frozen binary, compare every cache file's complete SHA256, then
run normal cache verification and a warm rerun. Record host load, exact command,
build identity, elapsed phase time and sampled peak private bytes. The current
full campaign must finish its allowed resource lane before this cold-cache
measurement. Do not redecode all 827 originals or invalidate their measured
geometry merely to time cache scheduling.

**VERIFIED:** root ran the fresh `mosaic_` test selection outside the sandbox;
`mosaic-expanded-controls-05` passed 23/23, including the prefetch planner and
serial/four-worker cache-byte, warm-skip and corruption-refusal controls. The
earlier controls-04 run encountered two sandbox filesystem access errors; those
were rerun rather than counted as successful controls. Binary-12 contains the
prefetcher. Root has authorized the bounded real cold-cache comparison after
the cached-only geometry replay. No real prefetch timing claim is made yet.

## Bounded real ABBA result

**MEASURED / VERIFIED:** ten physically copied insect originals from
`outputs/multi-stack/manifests/insect-middle-five.json`, fresh caches in order
1/4/4/1 requested workers, all cache payloads passed the normal consumer and all
ten complete cache files were SHA256-identical in every arm. Preparation phase
seconds were 3.441898 / 0.879843 / 0.871999 / 3.153053; outer command times were
5.208625 / 2.077623 / 2.081804 / 5.091067. Peak sampled private memory was at most
292470784 bytes. Conservative reservations were 967934492 bytes at one worker
and 2261125232 bytes at four, below the explicit4GiB limit. The warm reread
performed zero decodes (preparation0.001138s) and all normal cache checks passed.
A concurrent root-authorized diversity campaign was running; this is a bounded
ABBA measurement on that host, not an isolated speed claim or full827 timing.

Executable SHA256 `aadba7291fccf0b3f1379f385835ed68ddbcfd94f70dd7b40ce22feb81727e23`.
The exact commands/environment/build and full comparisons are retained under
`outputs/multi-stack/completion/mosaic-prefetch-{a1,b1,b2,a2,warm}-run-01` and
`mosaic-prefetch-build-01/{build-receipt,comparison}.json`. The harness links the
frozen CLI13 libraries and includes the production prefetch module directly.
No full827 cache was replaced or decoded by this measurement.
