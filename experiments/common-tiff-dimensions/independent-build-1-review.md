# Independent saved review: dimensions build1 refusal

2026-09-08. VERIFIED_SAVED_OPERATIONAL_REFUSAL. This is a saved-artifact
review of the first dimensions build, not a compiler, fixture, product,
checker or scanner rerun. The frozen source review remains unchanged.
Root supplied source-freeze context8017d2f3; this bounded pass did not reread
the181-entry map/archive and does not claim a new complete source audit.

The build is not admitted. The actual external controller exited1 without
external timeout. Its canonical result is REFUSED, with one attempted child
and no admitted executable. The child records a scanner exception before
a direct-exit/EOF observation. Its resulting exit code is3784556766
(0xE193C0DE), associated with owned failure termination rather than a natural
Cargo failure. The saved compiler log contains dependency compilation and
artifact records, no Compiling strehl-cli line and no build-finished record.
It provides no evidence of completed compilation of the product under review.

## Exact observed failure and its limit

The child error is a ValueError at scratch scan file inspection:

    target/common-tiff-dimensions-1/debug/build/proc-macro2-0ff67e0f32290390/out/probe/libproc_macro2.rmeta: canonical path

The parent subsequently refuses at run-stage.py child_call's expected clean
child terminal assertion. That latter message is the consequence; the retained
child record identifies the earlier scanner observation.

These artifacts do not record the pair of path spellings/stat identities
that caused canonical-path rejection. They do not establish disappearance,
replacement, a reparse point, a Rust/compiler error, a product defect or any
particular underlying race. A healthy compiler may create and remove scratch
files; that general possibility is not proof of this failure's cause. No
scratch-path inspection or source diagnosis was performed by this review.

Direct exit observed=false, pipe EOF observed=false and post-exit drain=null.
The specialized compile cleanup disposition remains UNVISITED, with no
attempt, no PID census and no claimed successful/natural compile cleanup.
The generic failure termination was attempted and succeeded on the owned
Job: its retained before snapshot had6 active processes and its terminal
snapshot had0. terminal_job_accounting=true; cleanup_errors and parent
finalization_errors are empty. Clean failure cleanup preserves accountability
but does not turn this attempt into a clean expected build outcome.

## Independently checked saved associations and accounting

I read the eight files below with fixed per-file caps and before/open/after
size, identity and timestamp agreement. I independently associated the
canonical result's sole child ref with actual child bytes, child log ref with
actual log bytes, raw stdout result/tail refs with actual files, tail result
ref, outer raw stdout/stderr/exit refs, exact outer/result invocation and
literal exit.txt bytes1 followed by newline. All agree by canonical Windows
location, extent and SHA256; absolute and repository-relative spellings are
treated as the same declared location.

The child Job's terminal user7500000 plus kernel5625000 ticks equals
13125000 ticks:1.3125 CPU seconds. This equals both the tail and result's
completed-child CPU. Parent CPU sample1.09375 plus that Job is2.40625;
live child CPU is0. The final accounting flags are true. These are recorded
CPU samples and cumulative owned-Job totals, not wall-derived CPU.

Actual outer controller wall is3.688000000009197 seconds, timeout=false,
exit1. Tail wall sample is3.6560000000026776; the2CPU/3wall final allowance
is retained. Thus recorded parent+Job+allowance is4.40625 CPU seconds and
outer wall fits the stated300-second allocation and sample-plus-tail envelope.
The child's own reported complete cleanup interval is2.7820000000065193.
Its peak Job committed memory429690880B is below the released3221225472B.
These comparisons describe this failed attempt's resource evidence only.
The attempt and its cost must remain retained; none authorizes a retry.

## Actual byte identities

Paths are rooted at experiments/common-tiff-dimensions: result/tail/child/log
are build-1/result.json, parent-tail.json, child-00.json, child-00.log;
outer/stdout/stderr/exit are work/build-external-1-outer.json,
build-external-1-stdout.bin, build-external-1-stderr.bin,
build-external-1-exit.txt respectively.

| Role | Bytes | SHA256 |
| --- | ---: | --- |
| child | 2422 | f242e8d3a46703f1e48dd89a27e81023a746c4c72855c78bd7b9bb2720bce8ea |
| exit | 2 | 4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865 |
| log | 3312 | 5163311a9878697553baf6be9262c8594770edda771222476b70c02d701fd5b9 |
| outer | 1625 | 43bdc3f65a594e37f4124e14b7d3e124fbaa38c5c9555739f7ebd9dbcfa2f947 |
| result | 262144 | ae5a36bc43999eb255aa9352f8d1a61ad4cfd793b44dd613c4224efe8d34b3fd |
| stderr | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| stdout | 463 | daea0d210280073d8d6ffc530ac3a2bb706391875668dd31aa7c5c0611cf6049 |
| tail | 614 | c650f644fa6e06467b3a663c2f0977058ba826646f06675aba8b9ab27937f374 |

## Review allocation and disposition

Root allocated this one saved-read review10CPU/20active-wall seconds,
64MiB reads and2MiB retained metadata. The initial read consumed270582B.
Its tool command exited0 in0.0878073 seconds; the inner active-wall sample
was0.015999999988707714. The inner CPU sample was0 at the process clock's
resolution; that does not mean zero actual cost. The fixed full10/20
reservation is charged, with no refund inferred from short samples.
The companion independent-build-1-read.json retains the same identities,
independent association checks and publication accounting. New report/ledger
bytes remain inside2MiB; their write/readback costs belong to this reservation.

No old or frozen source/report/result was edited. This failure is preserved
as an operational refusal. Root can separately commission source-only scratch
scanner diagnosis after committing the negative evidence. Any repair, new
source freeze or build attempt needs its own prospective release; this review
does not grant one.
