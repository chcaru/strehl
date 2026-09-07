# M193c private run controller — independent source review

2026-09-07. SOURCE ONLY, UNEXECUTED. Reviewed
`private-grid-run.py`, 17409 bytes, SHA256
`0e471e6722a0a3205b0ef6558562c85d773b9dc060763aef726fbdf55592b265`.
This report binds that revision even if the owner subsequently repairs it.
No controller import, process launch, build, kernel call, image generation,
TIFF read or RAW access was performed. I read the project-owned process helper,
build driver and controller-control interfaces for correspondence; their
runtime commissioning is separate. I did not verify my own coordinate or
precision mathematics in this review.

Disposition: **source changes are needed before release**. The intended
ten-plan → component → ten-render order and producer-only success scope are
sound. The following are concrete failure/binding gaps, rather than evidence
that an actual run has failed.

## Required corrections

### R1 — preserve the expected binding, not the second hash

`Attempt.track` first compares `binding(p)` with the supplied expected
hash/extent, then constructs `normalized = ref(p)`, which reads the file
again. On a first-tracked child file, a change between those reads installs
the second, unapproved bytes into `self.inputs`. A subsequently stable changed
file then passes the ledger's final comparison. Release-listed files receive
another original-reference check, but not every build child is necessarily a
top-level release input. The copied executable, listing and other separately
tracked children are examples of the boundary affected.

Construct the normalized ledger entry from the **already supplied and
verified** hash/extent plus the resolved path. Never replace the external
expected hash with another read's result. A private source-level fault should
make the first hash report the expected bytes and the next observation changed
bytes, and require refusal rather than a rebound ledger; pair a stable input.
This is distinct from the correct `Attempt.read` implementation, which hashes
the same bounded byte buffer it parses.

### R2 — collect failed child artifacts and retain the active launch

The outer plan/component/render loops collect artifacts only after `launch`
returns successfully. A failed component can therefore leave its completed
case JSONs and terminal/partial files uncounted; a failed render can leave a
TIFF and receipt uncounted; a failed plan can leave a plan uncounted. The files
are preserved on disk, which is good, but `artifact_bytes` and the output
binding ledger omit them. If Job accounting is absent, `launch` raises even
before collecting its log. These omissions matter both to the failure report
and any later cumulative-budget handoff.

Inventory the known fresh attempt directory at finalization, including hidden
files and partial files, without traversing or changing outside that owned
directory. Compare unique file extents with the write/collect ledger and
account new or changed bytes honestly. Keep cumulative overwritten writes
separate from retained on-disk size. Account a returned partial write by its
actual written extent; the current pre-charge is a prospective reservation,
not necessarily `cumulative_written_bytes` if writing never starts.

Attach the active launch record to the parent result **before** the child
call. If saving the launch receipt fails because the budget or filesystem
refuses it, the current local record is otherwise lost and `failed_launch`
can still point to the preceding successful launch. Preserve the current
command, observation, accounting and error in the terminal negative result
or an explicitly retained partial child. Name a last successful launch as
such; do not label it the failed launch merely because a later plan/receipt
read failed.

Missing or nonterminal Job accounting must make cumulative accounting
explicitly incomplete. An unknown child's CPU is not zero and cannot support
a subsequent budget carry, even though the schedule correctly stops on the
failure.

### R3 — revoke a previously written completion before a fallible rewrite

The main publication path writes `run-index.json` twice, then checks closure.
If that last check fails, the fallback tries to overwrite the existing file
with the negative result. If this rewrite fails before truncation, the
canonical path can still contain `COMPLETE_PRIVATE_OUTPUTS_UNVERIFIED` while
the process exits nonzero. The final authority wrapper should of course reject
that exit, but canonical result publication should not depend on every future
consumer remembering this secondary fact.

Preserve a previously positive index under a clearly rejected filename before
attempting negative publication, using only checked paths inside the owned
attempt. Retain the original failure and any secondary rename/write failure.
If revocation itself cannot be completed, the parent-observed nonzero exit and
explicit publication-error record remain mandatory; do not describe the
canonical file as successfully revoked. Count these retained/rewrite bytes.

The existing post-second-write `closure` is useful: it checks after required
persistence and avoids a silent final-write time overrun. Its work values are
still sampled before that write/check. Label that scope or use a parent-owned
terminal observation for cumulative carry; do not call the sample exact
process-exit consumption.

### R4 — bind the declared receipt output reference

The render association computes `ref(path(receipt["output"]))` and compares
it with the independently collected TIFF. `path` validates path/extent types
and containment but never checks the declared SHA/extent against the file.
Consequently a receipt with a false `output.sha256` or `output.bytes` can pass
this association as long as its path points to the correct actual TIFF.

Verify the declared output FileRef first, then compare normalized path,
declared SHA and declared extent to the independently collected TIFF. Also
check the render receipt's `plan_bytes`, alongside the already checked plan
object and SHA. The independent grid reader would reject these inconsistencies
later; the controller should not itself call them an actual consistent
producer receipt. Rehashed false-SHA/extent companions should fail at this
boundary without any image computation.

### R5 — complete the shared private-budget scope before launch

The controller initializes its own start clocks and child CPU total and has no
incoming budget/carry. Its 600 CPU / 1200 wall checks therefore cover this
producer process and its children only. They do not include a later independent
reader or two derivative TIFF stage. Root explicitly intends these stages to
share the charter allowance; that remains unfinished orchestration rather
than a property of this file.

Use one outer campaign owner for the common epoch, parent CPU, terminal child
Job CPU, retained/cumulative artifact accounting and remaining reservations.
Alternatively a subsequent stage may consume a separately validated cumulative
carry based on actual parent-observed process termination, not only this
script's pre-final-write work sample. A later process cannot reset the total
or treat an incomplete failure ledger as a full remainder. Include prior
failed attempts according to the frozen execution protocol. Keep a derivative
source or independent reader refusal from silently minting a completed private
campaign. No cap increase or new render is proposed here.

## Additional narrow parser/authority conditions

`strict` rejects named NaN/Infinity tokens and duplicate JSON keys, but accepts
overflow literals such as `1e999` as a Python infinity. Add a recursive finite
float check after parsing, as in the already held independent reader. This
does not change a numerical bar. A same-entry overflow fixture should refuse.

The release checks schema/scope and actual `sys.orig_argv` membership, but
does not require its own controller path to appear in `source_bindings`.
Require the narrow known source set (controller, helper, build loader and
actually imported Job helper), plus the independently enumerated compiled
source set already checked here. Empty/omitted source records must not make a
closure loop vacuously pass. Root's genuine release can and should contain
these entries; the consumer must check that obligation explicitly.

The accepted controller prerequisite is externally pinned and source checked.
Its local gate additionally checks ten passed rows, but not the exact ten
mode identities/order or the full prerequisite artifact/release closure.
Either bind this as root's already independently admitted prerequisite, with
that admission stated in the release, or close the concrete ten identities and
their referenced evidence here. Do not describe `len==10` and ten booleans as
independent revalidation of the process instrument. Similarly, the successful
build child is externally pinned; the new controller should retain the
build's actual compiler/listing process outcomes or rely explicitly on that
admitted build rather than claiming to rerun its entire commission.

These are bounded metadata/source fixes. They require no additional production
image, RAW read, parameter sweep or geometric recomputation.

## What the source already establishes

- Literal case enumeration is fixed. Each plan child completes and its actual
  plan is retained before the next phase; `all-ten-plans.json` is written
  before the precision child. The component plans are compared to those saved
  plans. All ten renders then use their individual pinned plan SHA and fresh
  output paths in the registered order.
- The source body constructs the exact ignored test command and verifies a
  single passing, nonignored test summary. It checks the actual compiled list
  for both private child names, compares copied/original executable bytes, and
  invokes the existing owned process helper with remaining allowances.
- Relevant environment overrides are explicit and other inherited prefixes
  are cleared by the helper. Actual sanitized overrides, removal names,
  command, timestamps, Job observation and log references are recorded.
- Bounded JSON parsing hashes its actual parsed buffer. Imported local helper
  modules are compiled from checked bytes instead of reopening source through
  an import cache. The compiled include set is compared to the bound build.
- Source/input/output closure runs between children and after final writes.
  The exception path stops the intended schedule; there is no favorable
  subset, substituted output, implicit retry or geometric tolerance change.
- `COMPLETE_PRIVATE_OUTPUTS_UNVERIFIED` is appropriately a producer completion
  state. The independent numeric/pixel reader and root's separately reviewed
  launch-authority wrapper still own the final private-only admission. Nothing
  here qualifies real registration, colour development, a common-TIFF route,
  quality, calibration, default promotion or full deep-stack alignment.

This report is a source-review finding inventory, not an execution result.
The repaired owner source should receive a narrow reread and frozen metadata
controls before its first actual private image command.
