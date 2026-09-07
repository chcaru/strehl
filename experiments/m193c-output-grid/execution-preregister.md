# M193c source preparation and prospective execution boundary

2026-09-07. Root implementation decision following the charter and two
independent source reviews. No M193c compiler, component, synthetic renderer,
RAW decoder or registrar has run. Exact source/command releases still precede
those executions; user authorization to drive the program is already present.
M194g completed and was archived at `417472a9` before any product hook here.

## Narrow implementation decision

Keep the actual Pyramid body, full-resolution gather, resampler and writer.
Add only test-local includes beneath `production_truth`: the reviewed
`private-adapter.rs`, its separate `precision-witness.rs` child, and the
registration derivative when its source is complete. No product-default or
geometry-solver change is proposed. The ten private images are the exact
population in `private-protocol.md`; the derivative has its separate two-image
allocation. The root's wording amendment makes the noiseless source/probed
operator distinction explicit and distinguishes a green-label rename from a
spatial interchange. No slope, frame, site or numerical tolerance changed.

Adopt existing owned RAW decode with immediate postdecode shape validation,
before further owned image allocations, and a parent Job committed-memory
limit. This corrects the charter's unimplementable claim of shape validation
before the decoder's internal allocations. It is not a predecode shape proof
or an exact RSS ceiling. Retain inherited level fallback provenance and
independent full-active payload/level agreement. CameraLinear development is
only an intensity proxy for the unchanged registrar. Preserve first-refusal
and unvisited outcomes; no partial binding is promoted to complete coverage.

## Build and owned child processes

`bridge-build.py` adapts M194g's source-to-compiler-artifact record, adds explicit
`include_bytes`/`include_str` discovery and a bounded owned process tree. It
binds tracked crate sources, manifests/lockfile, reachable explicit local
includes, the process helper and existing M12 Job API source. The exact include
forms used here are supported; this is not a general Rust cfg parser or a
hermetic toolchain certificate. Compiler command/environment and artifacts are
recorded. A fresh target directory plus actual `Compiling strehl-cli` and one
matching JSON compiler artifact are required. Copy that executable, compare
bytes, and retain its actual complete test listing before test invocations.
Source/helper/input/executable/log bindings are checked through publication.

The build has a separate operational allowance of1800 wall/1800 observed
user-plus-kernel CPU seconds,64 MiB live combined compiler log and8 GiB Job
committed memory. Listing has30 seconds/1 MiB. None is a performance claim.
The private batch later has the charter's600 CPU/1200 wall ceiling, including
component work, renders, checks and publication; each child has at most240
wall seconds and16 MiB combined log. A parent reserves only the remaining
batch allowances. Full child Job CPU is added to parent CPU, including failed
children. A refusing stage is retained and does not consume a replacement slot.

`bounded-process.py` reuses the existing project-owned M12 Job structures and
API wrappers by exact source bytes. It starts a child suspended, configures
the Job before resuming, and terminates only that owned Job on terminal failure.
It retains the Job handle until termination is observed and final accounting
is read, then closes it. A failed assignment or missing terminal accounting
is unmeasured/refused, not complete child-tree CPU. The
[termination API](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject)
applies only to processes associated with that supplied Job handle.
An eight-chunk queue bounds log buffering; overflow retains a bounded prefix
and refuses. A timeout means the prospective allowance expired, not that a
healthy process was diagnosed dead. Final Job accounting, direct exit and
remaining descendants are observed. CPU polling can overshoot; final checks
must refuse such an attempt rather than claim exact enforcement.

The added memory flag is `JOB_OBJECT_LIMIT_JOB_MEMORY` (0x200). It limits
committed memory across the Job, and is distinct from working set/RSS. See the
[Microsoft flag definition](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information)
and [extended limit fields](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information).
This is a conservative operational control, not admission to any M12 memory bar.

Before scientific children, commission the actual process helper on a finite
standard-library child: exit-zero/exit7, exact65536-byte log/65537-byte overflow,
timeout, nested own child at timeout,128 MiB allocation under a64 MiB Job cap,
changed watched input and restored valid companion. A tenth control combines
real log overflow with an injected failure of only the final log-binding read;
the original overflow and named secondary read error must both survive. The
private binding wrapper is restored in `finally`; no source file changes.
Confirm actual exit/log/
tree-accounting and the named refusal boundary. An unrelated exception cannot
pass. These create no TIFF or RAW arrays. The source of the fake child and all
literal commands/bounds are part of the controller release, not generated from
the test's result. Keep the first actual failure; source fixes need a new run.

## Actual floating-point component before image interpretation

`precision-witness.rs` is a separate component observer, not a merge diagnostic
and not an alternate merge. It consumes the exact ten fixed cases, all58
selected source frames,32 fixed coordinate pairs and R/G1 at each pair:3712
rows. It generates one source CFA at a time through the reviewed source seam,
records the source hash, calls existing `demosaic_malvar_row` and
`Resampler::sample_checked`, and saves their actual f32 values/bits. It then
runs the actual `warp_frame_in_place_fullres` on that source and requires its
u16 value at every selected site to match the component's pedestal/rounding
operation. This final comparison can fail if the component construction
differs from the actual production warp. It emits no TIFF and draws no source
noise; no gate-floor probe is called in this component-only path.

All ten genuine image plans precede this component's source generation. Each
component case embeds its actual prepared plan and the exact pretty-JSON
hash/extent; the parent and independent reader match it with that case's
already saved plan. Each component case has at most576 rows in one<=1 MiB
JSON; the top result records completed cases and original failure. Compiled
source closure includes the component itself. One source's unwarped channel
planes are discarded before the next source; no aligned frame stack exists.

Curie's separate oracle reconstructs the literal source and a different
binary64/binary32 MHC/Catmull calculation, checks native support and all actual
component values, and then evaluates the actual output TIFFs. Thus the0.125 DN
engineering reserve can be assessed at the entire fixed component population;
it is not promoted to a universal bound on arbitrary images. If it fails,
preserve the failure and make no precision claim. The0.1 native-pixel paired
two-site bar,2.75 DN channel allowance,32 pairs and bad-map/restored controls
remain unchanged. Different actual native centres supply the paired x/y
components; this is not whole-frame registration accuracy.

## Planned output index

The prospective `m193c-private-grid-run-v1` index records all10 ordered entries
with ordinal/id, actual plan and plan-launch references, render receipt/TIFF/
render-launch references; a separate precision launch/result; build/release/
invocation, source/input before/after bindings, work, original error and
finalization errors. References are repository relative. All ten planning
processes finish before any component or render. The parent records actual
exit and exact one-test summary, never a filtered-empty test success.

`COMPLETE_PRIVATE_OUTPUTS_UNVERIFIED` means the finite outputs exist and their
execution identities agree. Only the separately frozen reader can issue
`PASS_GRID_ADAPTER_PRIVATE_ONLY`. Complete-file parsing/hash is distinct from
the fixed sampled geometric oracle. Private coherently rehashed faults must
fail through the consumer's coordinate/reference path, not merely through an
old hash. No real source is read until the separate two-image development
operation, exact nine-source input plan and independent decoder are ready.
