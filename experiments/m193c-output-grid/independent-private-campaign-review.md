# M193c independent private-stage owner source review

**SOURCE-REVIEWED; not an executed private-stage admission.** This review reads
the owner/worker, its specification, the already commissioned process helper,
and the actual grid and derivative reader interfaces. It does not import their
modules, launch an experimental child, run a test, decode an image, access a RAW original,
or repeat the pixel arithmetic. Root owns the source/command release and the
subsequent actual twelve-product execution.

**Final source disposition: ready for root's source/command freeze.** The held
replacement identified in the final section repairs all three findings. No
additional source blocker was found in that narrow reread, and no runtime pass
is claimed.

## Reviewed source and initial disposition

The initial reviewed owner is `private-campaign.py`, 46,370 bytes, SHA256
`60b0c4cb7f0491968147a966ad8c288ba09f373dc46667fc19871fda6addc22d`.
Its specification is `private-campaign-preregister.md`, 10,886 bytes, SHA256
`05b671c28150cd96d98946c5f65c1b1dd62f325e6e5e9932f6125910d1b23cce`.
Both were held before this review; neither was executed here.

The initial source had a consequential late-publication gap and an always-
refusing grid request association, described below. Both required repair before
the first intended release. The process ownership and fixed stage population
agree with the stated bounded private scope. This is a source verdict, not
evidence that all four stages will complete within their resource limits.

## Concrete findings

1. **Terminal stdout is outside canonical revocation.** In the initial source,
   `owner()` line 745 serializes and prints the final success receipt after both
   guarded finalization blocks. A JSON serialization, stdout write, or flush
   failure there escapes without revoking `derivative-private-admission.json`
   and `result.json`. `worker()` line 605 has the analogous unguarded print after
   its provisional result is checked. The required independently observed exit
   and matching final receipt still prevent complete admission, but the
   specification's claim that late failures revoke canonical positive files is
   false for this path. Guard actual terminal receipt construction and output,
   preserve the original exception, revoke the positive files before fallible
   negative publication, and treat failed stderr reporting as secondary best
   effort. A private fault at the actual final stdout boundary, after initial
   positive bytes exist, is the economical falsifier; a successful JSON helper
   call alone would not exercise this choice point. No such fault was run here.

2. **Make the precision predecessor association explicit.** The initial
   `independent_population()` checks the precision schema, successful status,
   all 3,712 retained samples, and the actual hash of `precision.witness`, but
   does not compare that FileRef with `producer.precision.result`. The bound
   grid wrapper does pass the actual producer witness to its independent core,
   so this is an outer association omission, not evidence of incorrect samples.
   Compare resolved path, SHA256, and length, as the owner already does for each
   case's plan/receipt/TIFF. The bounded falsifier is a coherent replacement
   witness reference in an otherwise retained precision record; the original
   producer reference is the valid companion. Do not rerun image arithmetic to
   check this metadata association.

3. **Absolute and repository-relative request references cannot be compared as
   raw dictionaries.** Root found this after this reviewer's initial interface
   pass; that pass missed the representation difference. The worker creates
   `request_ref` through `state.ref(request_path, True)`, giving an absolute path.
   The grid wrapper constructs its returned `request` at lines 179/192 using a
   repository-relative path. Initial `independent_association()` line 469 tests
   direct dictionary equality, so every otherwise successful grid reader would
   be refused before the derivative stages. Compare authenticated normalized
   resolved paths and exact SHA256/byte extents for that association. Retain
   exact dictionary comparisons where the contracts intentionally preserve the
   original fields, including the release build FileRef. The valid companion
   is the same request file in these two actual supported representations;
   changing path to a different file, hash, or extent must still refuse. This
   repair belongs in the new owner, not the held grid wrapper.

All findings were sent directly to root and the owner author before execution.

## Independent choice-point audit

### One aggregate process owner, not a sum of overlapping observations

The owner launches one suspended worker through the pinned helper. The helper
assigns the process before resuming it and sets kill-on-close plus committed
memory limits, without enabling breakaway. The worker's stage Jobs are nested
under that outer Job; the producer may in turn own its individual Rust Jobs.
The owner adds only its one terminal Job CPU to its own process CPU. It does
not add the worker's locally accumulated stage CPU or the grid producer's
reported CPU. Thus the same descendant work is not counted again at each
nesting level. The worker's local accounting is a further early-refusal bound,
not the final resource authority.

This re-choice is supported by Microsoft's description of nested Job accounting:
a parent Job includes resources of its descendants, and termination charges
outstanding descendant resources upward. See the primary
[Nested Jobs documentation](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs).
This supports the source design; it does not establish that a particular future
process was assigned or terminated successfully. Actual acceptance still needs
the recorded zero exit, terminal accounting flag, zero active processes, empty
cleanup errors, and the final outer resource observation.

`State.work()` adds owner process CPU since process creation to observed terminal
child CPU; the wall clock begins at the first module clock read. Root's enclosing
invocation observation supplies the separately stated startup scope. The shared
caps remain 600 CPU seconds, 1,200 wall seconds and 128 MiB observed artifacts.
The Job's 8 GiB limit is committed memory, not RSS; polling is not a promise of
zero overshoot. Terminal excess must remain refusal. The owner is outside its
worker Job, so its CPU is added explicitly rather than assumed to be included.

### Actual stage chain and independent authority

The worker's literal order is grid producer, grid reader, derivative producer,
derivative reader. It stops at the first refusal and retains the attempted row
and unvisited suffix. Reader requests are made only from completed actual
predecessor records. The release build FileRef stays repository-relative and
byte-identical to the existing grid producer's field; actual request/result/log
references use declared absolute or repository roots rather than an implicit
package-relative interpretation. The initial consumer nevertheless compares the
grid reader's returned request dictionary directly; finding 3 records that
representation bug and the required normalized association repair.

`launch()` records the actual helper observation and checks its command and log
association. The direct derivative test has a literal exact test argv, a named
passing test line and the one-test summary. The owner reopens all four stage
launches after actual worker completion and binds their commands to the released
arrays and their reader requests to actual predecessor records. The grid wrapper
already performs the finer 22-observation chain, including ten plans before the
precision test and ten renders. The source-owned sequential loop establishes
stage ordering; this review does not claim an independently executed chronology
control for the new owner.

The worker's only successful status explicitly remains unverified. The owner
consumes the independent reader records before issuing its derivative gate.
The producer's own pass booleans cannot replace either reader. The campaign gate
is private synthetic input/output commissioning only; it cannot admit native
RAW derivatives, common-TIFF registration, coverage, physical calibration, or
image quality.

### Fixed reader populations and twelve actual file identities

The grid interface matches the current wrapper and core: the retained controls
must have 45 unique outcomes, comprising 35 expected refusals and ten valid
companions, followed by ten ordered case records and all 3,712 precision samples.
For every case, the owner cross-checks the actual plan, receipt and TIFF against
the producer. The independent core owns the sample arithmetic and exact control
stimuli; the owner does not turn a count into a second numerical verification.
The precision predecessor association finding above closes the remaining direct
link without duplicating that core.

The derivative interface matches the current source and reader: 32 source IDs
and 41 reader IDs in literal order, every pass genuinely `true`, plus the two
named output records. Those records use shape `[22,30,3]`, 54 affine comparison
sites and 660 signed-border sites, and the unchanged at-most-one-code bound.
The source32 records must equal the actual producer records. Reader41 is a
separate independently authored set, not another claim that the author verified
its own pixels. This is metadata/interface review only.

The declared product population is ten grid TIFFs plus `affine.tiff` and
`signed-border.tiff`. `products()` requires their actual device/inode identities
to be distinct, checks the prescribed paths, and requires the complete TIFF set
inside both producer directories to equal those twelve. Equal hashes in
different files remain legal and necessary for null arms. Reader mutation TIFFs
live separately and are counted as artifacts, not extra production renders.

### Sources, runtime, artifacts and finalization

Before entering a stage, the owner/worker authenticates the released sources,
inputs and runtime. Build authentication reopens both compiler and copied
executables, requires different paths with equal bytes/hash, examines the actual
compiler artifact message and rebuild line, and reads the actual test listing.
All compiled source bindings must be present in the release. The already reviewed
grid wrapper and derivative reader enforce their own exercised dependency sets;
the union release is not mislabelled as every module being imported by every
stage. All launched Python commands use the released interpreter and `-B`, with
fresh owned cache prefixes; ambient experimental and Python overrides are
removed. No new build or native decode is hidden in this owner review.

`State.binding()` bounds reads, rejects nonregular/reparse files, hashes an open
file with pre/post identity checks, and retains expected bytes in its closure.
The JSON path authenticates a bounded buffer and parses that same buffer.
Publication saves use bounded JSON, exclusive creation, write/fsync/readback and
an artifact reservation. The process helper retains the original child failure
and its cleanup errors, while failed-stage rows and failed inventories remain
negative evidence.

The outer scan includes the whole owned output tree, including hidden files,
reader mutations, unfinished artifacts and logs. Per-path observed high-water
extents retain deleted-path charges. Renames can therefore be charged again at
a new path; this is conservative observed-space accounting, not exact write
traffic or unobserved transient allocation. No worker byte total is added to
the parent's scan. The retained inventory excludes only its own index and the
terminal result, which receive final external FileRefs. Failure-only salvage
may exceed a previously exhausted allowance but cannot restore successful status.

Before the terminal stdout gap, the existing finalization reopens sources,
inputs, indexed files, gate, index and result after positive publication. It
preserves first versions and rewrites negative records on errors. A negative
write can itself fail, so the independently observed process exit and final
receipt remain required alongside a file on disk. Finding 1 required the terminal
repair to preserve this distinction rather than treat stdout failure as a
successful run with incomplete logging; the final reread below checks that repair.

## Read interfaces and scope

The actual source reads for this review included:

| Source | Bytes | SHA256 |
| --- | ---: | --- |
| `bounded-process.py` | 10,522 | `1dba8d87c8818aecf98078d1a926e5ff9c059a7d242cf5c46fcc962f14dfc5ab` |
| `independent-private-read.py` | 20,408 | `e943584dbd993639e804132451b11574a5d98f8c8a867ac274b5cef17938cdbc` |
| `independent-grid-read.py` | 50,979 | `435b147a390a2917c8d032d3a254b0fd3fb689d51f72ad101b432652ce21d0d7` |
| `independent-derivative-read.py` | 61,341 | `8c571654667f8ef66520aedfd1bddceb991c8a86d1a7355a4ed21cf2ba85eced` |

The derivative source was concurrently subject to root's separate mathematical
and parser review. Its hash here identifies the interface actually inspected,
not a promise that it will be the final released implementation. No held source
was changed by this reviewer. The previously completed process-controls11 and
compiled-build-only records remain separate evidence; this review does not
extend their executed scope to the unrun twelve-product stage.

## Final held replacement and disposition

The independently reread replacement is:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `private-campaign.py` | 48,401 | `25d666a54973883ac91f8095add61349a6bbda96a9977ddb9e6f29c12c8fa420` |
| `private-campaign-preregister.md` | 11,764 | `21dc02994b6ca2e27fcc26010209c95beca6f6d050c96548b0d1ff717980aa00` |

Both final hashes and extents were read from the actual files after the author
declared the replacement held. The author reports AST-only parsing; this
reviewer performed source reads and file hashing, not a helper execution.

The worker's final payload construction, serialization, write and flush now sit
inside the same exception path that marks its result refused and retains the
first canonical bytes. The owner's terminal output is similarly guarded and
calls `revoke_owner()` for both gate and result. `remember_failure()` keeps an
existing primary error and appends later failures. `best_effort_stderr()` catches
its own serialization/write/flush exception, so failure to print a diagnostic
does not skip the remaining revocation attempts. The immutable first file and
three explicitly bounded later refused slots avoid overwriting earlier evidence
when another finalization attempt fails. Failed-status writes remain best effort;
an inaccessible filesystem cannot be claimed to have persisted a negative file.
The actual nonzero exit remains essential in that case.

`independent_association()` now verifies both request FileRefs against the
current file, compares their normalized resolved paths, and retains exact SHA256
and byte-extent equality. Thus the actual absolute worker reference and actual
repository-relative grid reader reference denote the same admitted input; this
does not permit a different file or different bytes. Other deliberately identical
build and producer references keep their original contract.

The grid precision consumer now directly compares its retained witness with
`producer.precision.result` by actual verified path/hash/length. It retains the
same 3,712-sample population and delegates numerical checking to the same
independent reader. No metric, threshold, image count, process budget, or held
grid wrapper was changed by these repairs.

**No remaining source blocker was found for freezing the intended private
release.** Root must still bind the final full source set, runtime and literal
commands before running it. Neither the new terminal-output failure boundary
nor the complete enclosing private stage has been executed by this review;
actual outcome, resource compliance, and twelve-product admission remain to be
observed. This conclusion does not promote source reasoning to a process or
pixel result.
