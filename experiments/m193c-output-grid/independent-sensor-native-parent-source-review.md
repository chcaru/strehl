# Independent source review: sensor-domain native parent

Root reviewed Zeno's explicit native variants before execution. This is a
source verdict, not an actual reader, reuse, derivative or coverage result.
The separate independent reader review is by Curie. The old native1 refusal
and all old held sources remain unchanged.

## Reviewed bytes and commands

- `native-sensor-derivative-run.py`: 53533 bytes,
  `10ec80290bc7bb5c2e7fc140cb831d539e517844281b40b372055b409113a1ed`.
- `independent-sensor-derivative-read.py`: 68424 bytes,
  `eeed1ea3c45927f81e34d99ca31dc57715f898b718dfef26dcf0ea2cddf3fbe7`.
- `sensor-domain-reader-preregister.md`: 15934 bytes,
  `7450a8e2ecef2b5c3c883e63fd2f636dc84c5bc6ac07df80fc1277bf5bdf7125`.

Actual source-reading commands from the repository root:

```powershell
git diff --no-index -- experiments/m193c-output-grid/native-derivative-run.py experiments/m193c-output-grid/native-sensor-derivative-run.py
git diff --no-index -- experiments/m193c-output-grid/independent-derivative-read.py experiments/m193c-output-grid/independent-sensor-derivative-read.py
Get-Content -LiteralPath experiments/m193c-output-grid/native-sensor-derivative-run.py
Get-Content -LiteralPath experiments/m193c-output-grid/sensor-domain-reader-preregister.md
```

The two diff commands returned 1 because their source files differ. They are
read-only comparisons, not failed subject executions. Root read the entire
changed parent and reader regions and the inherited `Files`, `Budget`,
`primary_result`, `native_summary` and independent-result checks that they call.
No subject/helper import, decoder call, new primary or synthetic numerical
execution was performed for this source review.

## Choices re-chosen

**Sensor domain:** The consumer compares the exact primary-declared ROI against
an independent full decoded sensor buffer. It does not redefine the primary
output as rawpy's narrower visible crop. The eight controls exercise different
origins, visible rectangles, buffer extents and ownership behavior; full and
every row hash remain exact. Metadata preserves the independent visible domain
and disclaims physical photosite validity. This is justified by the separately
completed and independently read active-domain diagnostic; it does not admit
the old failed native1 or predict agreement on the remaining eight frames.

**Reuse identity:** `first_reuse` authenticates the actual old refused result,
row, successful primary launch, independent dimension refusal, root exit,
console, dependency endpoints, source closure and all nine current original
observations. It reads both actual plans through their FileRefs, requires
canonical byte identity and complete parsed equality, and tests a changed
later entry while preserving original0. An original0-only comparison would fail
that control. A new matching first entry alone is insufficient for reuse.

**Historical paths:** Original0 retains the old plan, snapshot, primary receipt,
TIFF, producer command and environment. The original `primary_result` and
`native_summary` gates still apply. Its new request, execution release, source
authority, reader command and independent result are fresh. No old producer
execution is represented as a new process. No old output directory is written.

**Resources and failure:** Old work must be covered by the release carry. The
old primary launch is never passed to `budget.child`; the old snapshot and TIFF
remain retained inputs and are never deleted. Eight later originals use the
unchanged fresh snapshot/primary/reader path. Any failed reuse association or
first fresh reader stops progress, preserving the old result and actual new
refusal. The later metadata preparer must additionally carry actual diagnostic
costs and root metadata; that is a separate source/manifest review.

**Interface:** New explicit request, reader, release and parent schemas prevent
old visible-domain evidence from satisfying the new contract. Parent requires
the exact eleven native checks and eight domain controls, actual reader exit,
request/source/runtime/file associations, and complete nine-row success before
the awaiting-coverage status. The held coverage source accepts the old schema
only and requires a separately reviewed versioned update before use.

## Correction made before freeze

The draft specification said the CFA control detected a zero-origin shortcut.
Its primary origin (4,2) has the same Bayer phase as (0,0), as do all admitted
even origins, so that particular CFA assertion cannot reject the shortcut.
Root required the author to narrow the claim: the odd visible origin (7,5)
does differ and is tested; even-origin phase equivalence is arithmetic. The
independent ROI hash controls separately detect actual crop-offset mistakes.
The revised spec above incorporates this correction; no implementation or
acceptance threshold changed.

## Verdict

VERIFIED by source inspection: no blocking defect found in the reviewed native
parent delta or its reader association. This permits exact release preparation
and independent manifest review. The controls, full-plan reuse and all real
image agreements remain UNVERIFIED until that frozen command actually runs.
No Rust change, rebuild, default promotion, quality claim or SOTA admission is
part of this source review.
