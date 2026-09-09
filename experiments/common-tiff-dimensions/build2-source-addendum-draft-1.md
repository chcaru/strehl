# Build2 source addendum

SOURCE ONLY,2026-09-08. No product, controller, scanner control, fixture generator,
checker, compiler or process helper executed during this edit. Root releases the
next attempt only after the independently authored16 scanner controls and final
source reviews. Original source1 and failed build1 evidence remain preserved.

## Exact owned delta for independent review

| File under experiments/common-tiff-dimensions | Bytes | SHA256 |
|---|---:|---|
|run-stage.py|33546|442226bd08b128f8bb97460fab6f8ab6280fd0950d1912313b87d583b7a33940|
|bounded-build-process.py|16517|1d52b3cd9a4f218b886049f9fcc29b95164e64eb7afb2717a1f3f9646987f31d|
|prepare-release.py|11640|62159c693f0d070e44dcd7e581aff875e1f1aacbd4fda20f7e928a06fecdebc5|
|capture-stage.py|3870|e5ba4fb688687711a11cf05d4e83ae8211af1805e6fe60d6d79fe17229545422|
|run-stage-contract.md|18587|0b43caaeef350c387c4bda2953bccf14e21789388ad718085c7f77030f6595ec|
|scratch-scan.py|2991|3a1aa413fd4c9d37bccb973a419e3f4c03291903d44b7198c53992e7b00d3e46|
|scratch-scan-rationale.md|7745|a89a2e7f57decf85fe0d9211e85e566af70ebd874556653b31d72cf8c4e7d817|

The first2264-B shim draft(be6da1fb1b69524565dc5bc7e074236c28777272ec1f938319dae3393e9c54fd)
is preserved as scratch-scan-draft-1.py and is not loaded. Its rationale remains
scratch-scan-rationale-draft-1.md. The independently detected dangling-reparse
gap was corrected before any shim/control execution.

A bounded source-only AST comparison used the exact original buffers read from
source-1.zip and verified each original extent/hash against source-freeze-1.
Controller:16 top-level functions unchanged; only authority differs, installing
the authenticated shim only for build before Budget construction. Constant
changes name new helper/shim pins, exact target2/build2 and required reviews.
The compile helper has six unchanged functions; run changes only the target
literal. Reversing target/common-tiff-dimensions-2 to -1 restores its entire old
16517-byte buffer. Prepare constructor has eight unchanged functions, changes
source_map/archive_sources/main and adds base_sources. Capture has three
unchanged functions; main changes only its build-attempt selector.

No Rust/product/parser/merge/noise/pixel code is edited. The independent checker
author owns its build-path-only change. All24 cases, population, tolerances and
nonbuild process machinery remain fixed. Source-only parsing is not a compiler
or control pass; the author does not independently verify the operator.

## Source2 freeze and command association

The exact original181-source freeze is25815B/
7b37fe67c8cee38e655d461ee9c5b498b60808b834d2b97d61ee3be9a76b6de4.
Its5661467-B source-1.zip hash is
0dbe11b91a4351e041bff97201506600fee03ab3b37bf1b32e5b34cd63016770.
These are the retained base, not a refreshed view of current paths.

Fresh work/source-2-delta.zip stores changed/new source bytes only. The new
source-freeze-2.json carries the full current source map, both base references,
delta reference and exact changed/new key list. Constructor validates the base's
unique complete inventory and every original buffer, then every current buffer
selected from delta-or-base. The original ZIP's order differs from JSON's sorted
key order(actual first difference atindex2); set equality with exact181 count
checks the population while the fixed archive hash binds original ordering.

Only six old entries may change: controller, compile helper, constructor,
capture, execution contract and independent-controls.py. New keys come from the
closed NEW_SOURCES list. No old key disappears; unexpected crate/source changes
refuse. Required new source closure includes shim, preserved first shim draft,
rationale, independent scanner controls/spec/review, this addendum and root's
build2-source-review.md. Freeze waits for all review sources to be final.
Historical rejected control/spec/rationale drafts may remain outside the active
release map; they are not runtime authority.

Build uses work/build-release-2.json, build-2 and target/common-tiff-dimensions-2.
Capture records work/build-external-2-{outer.json,stdout.bin,stderr.bin,exit.txt}.
Actual executable is build-2/strehl-common-input.exe. Later prepare/render/verify
paths and suffix1 remain, but their six-role build prerequisite selects build2.
All stages require the same source2 map. Neither this note nor a source archive
is a substitute for actual exit/Job/tail and independent numerical acceptance.

## Cost and preparation qualification

Retain the full failed build600CPU/300wall; one prospective fresh build gets the
same600/300. Unchanged later stages270/420 yield1470CPU/1020wall stage reservations.
Metadata retains first10/20 plus four fresh10/20 slices:50CPU/100wall,32MiB family.
The separate failed-build review retains10CPU/20wall/64MiB read/2MiB write;
independent scanner controls reserve5CPU/10wall/1MiB read/1MiB write.
Earlier source-preparation/formatter observations remain with their actual
records; their aggregate CPU is not invented. No unused slice authorizes retry.

Two preparer-source replacement attempts failed an exact text-anchor assertion
before writing the target source. The anchor was corrected, then source parsed
without importing or running the constructor. A metadata-only archive directory
read caught the old ZIP/JSON ordering distinction before candidate execution.
These are source preparation observations, not scanner controls or build results.

Root commits with its established byte-preserving Git procedure and verifies
every committed blob against current source bytes. Existing LF source bytes are
not normalized merely because Git warns about a future CRLF conversion. The
saved work/build2-integration.patch is the exact Git diff of the five modified
owned files plus the new shim; source pins above bind the actual buffers.
