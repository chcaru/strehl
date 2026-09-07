# M193c parent/build/precision — independent source review

2026-09-07. **SOURCE REVIEW ONLY / UNEXECUTED.** This review read the owned
Python/Rust source, the prospective execution/reader protocols, and Microsoft's
Job Object documentation. It did not import the helpers, run the old M12
campaign, compile, generate a source array, read RAW bytes, or execute a
component, controller control, renderer or metric. Root is the producer;
roadmap_audit is this source reviewer; Curie's separate numeric/pixel reader
remains the intended independent consumer.

**Final disposition: ready for the first finite process-control source/command
freeze.** The five source findings below have been repaired and independently
reread. There is no remaining source blocker to commissioning the ten named
process controls. This is not a passed control run, compiled build, precision
admission or grid-adapter admission. Build/component/image commands retain
their own later source, actual-listing and independent-reader prerequisites.

The initial source inspection used these bytes:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| bounded-process.py | 8418 | e5f94ac716773d3d6f6a45f8dfdb4bcb7fb9b6cf0a3bf259a51e347220c6595c |
| bridge-build.py | 13185 | 408c743e97b76ef93f23cae4c0afa9996212b9b0b5dc142eae2ba1fa5eaa857e |
| precision-witness.rs | 7603 | cc925d04b5e434c93e641c3c832d04034832a3e41ef716029bad6b401c2c5092 |
| private-adapter.rs | 23732 | 5576bec563753e7a5c420cd1f1bb8d46690a71ff03bc636189c99065ab4f6b77 |
| ../m12-scorecard/m12-harness.py | 117908 | 6cfb408992f37b225f102da4d62ba836f9c5b67c92bdd418ff460987866a1bb9 |

## Concrete defects and changes requested before release

These are static defects, not executed failed controls. They must not be
reported as measured failures or as evidence that the new controls pass.

1. **Late log binding could replace the primary process failure.** The
   original `bounded-process.run` called `binding(log)` unguarded in `finally`.
   A final open/read error would escape instead of returning the original
   CPU/log/source refusal, child exit and cleanup observations. Root added a
   separate `final child log binding` cleanup error, preserving `error`.
   The later `late-log-binding` control is an appropriate prospective witness:
   combine a real log overflow with an injected final log-read failure, then
   require both named causes and the exact retained 65536-byte prefix.
   Root also guarded `process.stdout.close()` into cleanup errors and moved
   the returned final wall sample after final log binding. These are static
   repairs; the combined failure control is still unexecuted.

2. **The precision component lacked the no-file sentinel guard.** The normal
   producer's `execute` refuses existing `M193C-NO-SUCH-RAW-*.ARW` paths before
   using the full-resolution warp. The separate witness bypassed `execute`.
   The owned `warp_frame_in_place_fullres` still calls `strehl_raw::identity`,
   whose owned implementation opens the path if it exists, even though it
   does not decode pixels. Root added the all-nine absence guard at the start
   of `witness_case`. Thus a coincidentally present file cannot silently turn
   this component into a RAW-header read. A private sentinel-presence refusal
   may test this boundary without supplying any RAW file or decoding it.

3. **Expected test duplicates were silently removed.** The original build
   reader converted `release.expected_tests` directly to a set. A repeated
   expected name could therefore pass the comparison with the actual listing.
   Root added an exact nonempty list-of-strings and uniqueness requirement
   before conversion. Keep actual listed duplicates rejected too. Future
   build-metadata controls should distinguish an empty/duplicate/bool expected
   population from a missing or extra actual listed test; a successful empty
   filter is not a component execution.

4. **Failure accounting was described more strongly than observed.** On a
   refused child, the initial helper took its last accounting snapshot before
   closing the Job handle to kill its processes. That is observed user-plus-
   kernel CPU before cleanup, not a terminal total for the failed tree. The
   prospective parent must not label its sum “full child CPU” unless it retains
   the Job handle through termination, waits/requeries terminal accounting,
   and only then closes the handle. Alternatively it must disclose the
   unobserved cleanup interval and use the weaker observed-accounting claim.
   Polling also permits overshoot; no exact no-overshoot claim is justified.

   Root chose the stronger implementation: query the live owned Job, use
   `TerminateJobObject` only on that handle if processes remain, poll its
   accounting for zero active processes within a separate five-second cleanup
   interval, record terminal accounting, then close it. A failed assignment
   never receives the terminal-accounting claim. All ten proposed controls
   require `terminal_job_accounting` to be genuinely true. The documented
   termination scope is the supplied Job and its nested child Jobs, not
   unrelated system processes.
   [Microsoft TerminateJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject).

5. **The new control entry hashed different bytes from those it parsed.**
   Its first draft used `binding(release)` followed by an unbounded second
   read and plain `json.loads`. I requested one bounded 4 MiB+1 read, hash and
   duplicate/nonfinite-rejecting parser on that same buffer, matching the
   existing build entry. Final rehashes cannot replace authenticating the
   actual initial parse buffer. This is an entry repair, not a new scientific
   criterion or a claim that an executed mismatch was found.
   Root implemented that same-buffer bounded strict parser; the final reread
   confirmed its extent/hash check precedes parsing.

The final reviewed source pins are:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| bounded-process.py | 9622 | 0983606aa065a4d7f2b266082d16d88068bdfc5609336a0c53b3cd9a6f7b31df |
| bridge-build.py | 13425 | 6bdce51043154bfc0bc1086a1ee0696fd12abdaff47049ac2e6288f5d4990f1d |
| precision-witness.rs | 7697 | 6979f6e51b9bf9028002c9cdfff81f4925f293ce79386eb49fa4a84bec643cc9 |
| controller-controls.py | 9825 | 9e7d6d0b8dabd3104365347f1973abf8c5f2469d9a3bde46e4ae82b2fbd0c7fc |
| controller-child.py | 1415 | 5bbbb5cd88015250e2999e9b02c2e6131d232e5378bbf45fd2f0764458815d69 |
| execution-preregister.md | 8721 | 10511b44708fd3067698846006e71828c37f6d9c83a7d052556af8fdfb3fdbf1 |

The unchanged adapter and Job-helper pins remain in the initial table. This
review's only filesystem edit was this report. Initial defects, subsequent
repairs and unexecuted status are retained; no numerical threshold changed.

## Owned process boundary and resource meaning

The initial architecture is appropriate for a bounded private child: create
an unnamed Job, install its memory/kill limits, start only the new child
suspended, assign that child, and resume it through the pinned owned helper.
No process-name search or unrelated-process termination is used. Assignment
failure retains the direct suspended child's identity and explicitly kills
that child. The inherited Job handle is not made inheritable and neither
breakaway flag is installed. Closing the last kill-on-close Job handle is
documented to terminate its associated processes. This is a source-level
assessment, pending the actual finite controls below. Assignment-failure
cleanup was source-read and is not an additional executed control here.
[Microsoft basic Job limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information).

The `0x200` flag is `JOB_OBJECT_LIMIT_JOB_MEMORY`: it limits committed virtual
memory across the Job. A refused allocation can produce an ordinary child
`MemoryError`; the peak need not cross the limit for the limit to have acted.
It is not an RSS or working-set ceiling. The recorded extended-limit peaks
must retain their Job-memory names. The separately registered live-array
ledgers likewise cannot substitute for process RSS.
[Microsoft basic Job limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information),
[Microsoft extended Job fields](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information).

The helper polls the sum of the owned Job's user and kernel accounting. This
is deliberately different from the Windows Job user-time limit, which alone
would not enforce the same sum. Wall time has a separate monotonic check.
Queue storage is finite: eight queued chunks, with at most 65536 bytes per
data chunk, plus the producer/current-consumer chunks and OS pipe buffers.
It would be inaccurate to call the entire logging system exactly 512 KiB.
The retained file is capped independently and overflow is a refusal with a
prefix, not silent truncation of a successful invocation.
[Microsoft basic Job limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information).

Normal completion requires direct exit observation, EOF, a final resource
check and no active descendants; callers also reject any cleanup error and
require the appropriate exit code. A nonzero child is an observed child
outcome, not necessarily a process-helper exception. The actual child marker
and exit are needed to distinguish a deliberately refused allocation from a
Python startup/import error. Nested-timeout controls must see the live nested
child before interpreting cleanup; a parent-only timeout is not that power.

The helper caps the launched tree. It does not by itself cap the importing
Python parent's allocations, the `git ls-files` discovery subprocess,
source/artifact hashing, or parent publication. The separate build/list
allowances and later nonresetting private-batch allowance must be reported
with those scopes. `load_job_api` executes the exact pinned local harness
module under a different module name, including its `tifffile` import; the
`__main__` campaign is not invoked. This is reuse of owned APIs, not a claim
of a dependency-free or hermetic import. No such import occurred in this
review.

The new finite process-control source was read while root prepared it. Its
exact log boundary, real exit7, allocation-refusal marker, timeout marker,
nested-child marker, watched-input mutation/restoration and combined late-log
failure target actual choices. These remain prospective. Passing them would
commission those process boundaries, not the build's metadata population,
the image source, a kernel or the final pixel reader. The outer total must
include failed attempts and final persistence; a failed attempt does not
license an unnoticed replacement run.

The final literal order is `valid`, `nonzero`, `exact-log`, `overflow-log`,
`timeout`, `nested-timeout`, `memory`, `late-log-binding`, `changed-input`,
`restored`. The fake child uses no image/RAW input. Its memory fault attempts
128 MiB under the 64 MiB committed-memory cap, and requires its explicit
`MemoryError` marker and exit7. The timeout fault sleeps for30 seconds under
a one-second deadline; the nested case additionally requires two processes
and both start markers. Other children have10-second wall/CPU bounds and all
have65536-byte retained logs. The wrapper has a120-second monotonic wall check
since its `START` sample after standard-library imports, plus exact
source/input/artifact rechecks through result writing. This is not an
operating-system launch-to-exit measurement of its own Python parent.
These are source-declared operational limits, not measured timing results.

## Build identity, source closure and publication

`bridge-build.py` requires the externally hashed closed release and actual
`sys.orig_argv`, a fresh dedicated target, the exact build argv, visible
`Compiling strehl-cli`, and one matching compiler-artifact record. The checks
include the CLI package, manifest, main source path, binary target and test
profile. It records the original artifact, copies it, compares original/copy
bytes, and runs the copied executable's actual `--list` in another bounded
Job. This is useful source-to-artifact evidence; it is not a hermetic compiler
identity proof. The actual compile and listing still have to occur.

The source walk binds tracked crate contents, manifests/lockfile, the new
adapter and helper, the pinned Job source, reachable explicit Rust includes,
and the driver itself through the exact release map. The existing/new
`include!(concat!(env!("CARGO_MANIFEST_DIR"), literal))`, matching
`include_bytes`/`include_str` forms and explicit `#[path]` are recognized.
The supplied precision and derivative byte-includes use that form. They only
become reachable once the reviewed hooks exist, so source/command release
must follow those hooks and inspect the resulting complete map.

This is not general Rust dependency discovery. Direct literal
`include_str!("...")`/`include_bytes!("...")` are not traversed by this regex;
the direct literal instances found in the currently read crate sources are
already tracked files. A future untracked external literal include must be
explicitly supported/bound or refused, rather than inheriting the present
closure claim. A bounded closure control should use both an executable
external include and a byte include, mutate/omit each, and require refusal
against the fixed complete map. No dependency source was read for this review.

Source/input/driver checks occur after compilation/listing and after the first
result write. The finalizer reopens the release, compiler/list logs, original
executable and copied executable. A late mismatch revokes in-memory success,
retains the primary error separately from finalization errors, attempts to
write the refused result, and returns nonzero. A parent must require both
the actual zero exit and a final successful record; a provisional JSON file
cannot independently establish completion if its refused rewrite fails.
Pre-authorization/setup failures occur before the attempt record exists and
must remain in the parent launch log, not be mislabeled as an observed build.

## Precision path, finite population and inference limit

The witness consumes the producer's exact source generation and selected
original indices, with one source frame live in its outer loop. The six
nine-frame cases plus four one-frame cases give 58 selected source frames.
Eight x positions times four y positions times two measured channel sites
give 64 rows per frame and 3712 rows in total. Each case asserts its own
population; the outer invocation requires all ten ordered cases. The separate
reader must still verify the literal keys/order and all 3712 rows, including
the swapped/inverted one-frame cases, rather than pool only the successful
normal cases.

The component's geometry is consistent with the real full-resolution warp:
add twice the actual quad crop origin, retain R at `(x,y)` and G1 at `(x+1,y)`,
apply the post-cover/post-fault quad pull at half the full native coordinate
about `(80,60)`, and double the sampled coordinate. Scale's crop origin is
zero and its already composed pull includes the cover scale. These are not
the `(w-1)/2` centre or one shared sample position per CFA quad.

The actual owned MHC function constructs full native R/G channel planes from
black-subtracted u16 source values, then the actual Catmull `sample_checked`
supplies the f32 sample. Unity WB makes the component's pedestal addition and
round/clamp sequence agree with the production sequence. The witness then
calls the actual `warp_frame_in_place_fullres` on the source and compares its
u16 result at every same site. The production `demosaic_row` selects MHC when
the fresh-process `STREHL_DEMOSAIC` override is absent; the witness refuses
unexpected STREHL overrides. Fresh exact single-test invocation is therefore
part of this argument, including cached environment choices.

This actual-warp check can detect a disagreement between the component's
construction and the production path. It does not independently validate the
shared MHC/Catmull arithmetic or prove the 0.125 DN engineering reserve.
Curie's separately implemented rational/f64/f32 stencil and whole-support
checks are still required. Every support must avoid both sampler clipping
and MHC reflection; a finite positive aggregate coverage fraction alone is
not that proof. The other RGB components and unsampled image pixels do not
inherit the paired R/G1 coordinate bar.

The source frame survives only until its actual warp comparison completes;
the component channel planes are explicitly dropped before that warp and no
aligned frame stack is retained. The production warp separately allocates
its own mosaic, three planes and scratch. Thus “one source frame at a time”
does not mean one allocation or zero overlapping buffers. The external Job
and aggregate parent accounting remain necessary. The precision path calls
no band merge, product TIFF writer or gate-floor probe and draws no source
noise; the later genuine private render does include its enabled probe.

Case JSON uses the producer's bounded, exclusive-create serializer and
reopens the written bytes. Its maximum planned population is 576 rows per
case under the 1 MiB cap; the top record contains case FileRefs. A refusing
case is not included among completed cases. Previously completed case files
and the original error remain, while in-memory rows of an interrupted case
are not currently a persisted complete-case record. Do not report a partial
case as completed evidence. Receipt-write failure is returned with the
original component failure as context; an early environment/output setup
failure remains a launch-log failure. The parent must bind case/result files,
compiled source, actual copied executable and prior plans after child exit.

The prospective order is load-bearing: all ten pixel-free plans first, then
this component, then the fixed render schedule under the same source/build
closure. A witness's embedded self-generated plan alone cannot substitute
for those externally pinned plans. No current source review clears precision,
grid-adapter, RAW-development or native-registration admission.
