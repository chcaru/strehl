# M193c independent grid reader wrapper — source review

2026-09-07. **SOURCE ONLY / UNEXECUTED.** This review concerns the root-owned
`independent-private-read.py` adapter around Curie's independent grid reader.
No numerical helper, reader instrument, TIFF, subprocess or RAW operation was
executed. The wrapper was read alongside the actual core API and Zeno's
`private-campaign-preregister.md`; this is not an independent recalculation
of Curie's coordinate or floating-point mathematics.

The intermediate source at 20284 bytes, SHA256
`bc168be0d8a4175eee0b099145b6717aca82a37ab199e9afe687330270a66421`,
still contained the direct-hash charging gap described below. The final
reread binds these corrected files:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| independent-private-read.py | 20408 | e943584dbd993639e804132451b11574a5d98f8c8a867ac274b5cef17938cdbc |
| private-reader-wrapper-preregister.md | 2773 | 0f20e75f6d45c562cf8a2e632e4fe0e491465da031bb5165862a82f7ed9c17f6 |

The initial defects were found before any wrapper execution; no passing
control is claimed for them. The fixes below are verified by source read.

## Consequential choices and repairs

**Actual observation versus declared launch.** The initial wrapper checked
the helper outcome but compared only the surrounding row's command and log
to the expected invocation. A row could therefore name the expected command
and a passing log while its actual helper observation named something else.
The added shared `bind_observation` checks actual observation argv against
the row and binds both log references by resolved path, SHA256, byte length
and `log_bytes`. It is consumed for the producer launch and all twenty-one
inner launches. The producer stage must also be `grid_producer`.

This choice is complementary to the pixel reader: valid image arithmetic
cannot establish which command the parent actually observed. A future
bounded metadata control should change only observation argv or its log
identity while leaving the surrounding row valid; it must refuse at the
actual binding helper. A stable row/log companion must pass. The final
campaign still owns collecting the genuine parent observation.

**Declared closure versus vacuous equality.** Equal empty source/input maps
could satisfy the original producer-closure assertion. The corrected wrapper
requires the producer's exact source map to equal its bound release map and
every declared producer-release input to appear in the final producer ledger
with its normalized fixed path/SHA/length. It also requires each producer
and compiler source binding to agree with the common campaign release and
reopens actual consumed files. Removing an entry coherently from both
producer before/after maps must not evade the release comparison. Removing
a required input coherently must likewise fail; relocation normalization
must not silently replace an expected hash.

**One cumulative reader allowance.** The initial wrapper and numerical core
each allowed 512 MiB of input reads independently, although the private
reader preregistration declares one cumulative 512 MiB ceiling. The revised
Store checks the sum of authority and numerical counters, and sets the
core's remaining read limit to `512 MiB - authority_reads`. The counters
never reset between controls, population and final rereads. A private
counter companion with individually sublimit counters whose sum exceeds
the limit is a direct falsifier; the same sum at equality is the companion.

One additional intermediate-source gap was reported: direct executable
comparison hashes, runtime hashes and `sources_after` hashes bypass those
counters. The final source charges its hash function through `Store.digest`,
including runtime, source-after and output-persistence reads. It removes
redundant executable hashes by comparing the already authenticated
SHA/length pairs, and charges the initial request buffer. No remaining
direct hash call bypasses that helper. This is an accounting correction,
not a change to the engineering limit or image tolerances. A file-operation
exception may prevent completion of its byte accounting; such a run refuses,
and its partial local sample cannot provide a complete budget carry.

**Last-write runtime binding.** The initial Python executable check stopped
before final result persistence. The corrected wrapper repeats it after
the final result write and source/input/output closure. A changed executable
introduced specifically at that write is the powered boundary choice;
a mutation before the first read would exercise a different boundary.
The executable reference may be outside the repository, as the campaign
contract explicitly allows, while other consumed FileRefs stay inside it.

## Ordering and consumer interfaces

The closed request and campaign-release shapes match the prospective owner:
`m193c-grid-reader-request-v1` carries the release, actual build, producer
result, producer launch, Python runtime and remaining limits. The release
is `m193c-private-campaign-release-v1`, scope `private-twelve`. Only the
registered `ACTUAL_GRID_REQUEST_SHA256` token is needed in this reader's
exact original argv; its underlying release is reached through the pinned
request. The actual Python executable is checked and `-B` is required.

Request JSON is bounded and hashed before parsing from that same buffer.
The remembered request identity is constructed from those checked bytes.
The strict parser rejects duplicate keys, named nonfinite values and
overflow-real nonfinites. Consumed FileRefs retain their expected SHA/length
in the ledger, rather than rebinding a second read. Required wrapper/core/
TIFF-parser sources are explicit; modules are compiled from checked source
bytes only after the entry checks.

The wrapper reads ten literal plan-launch rows, the precision launch, then
ten render-launch rows. Every inner argv, environment, executable and actual
log is associated with the fixed ordinal/phase and corresponding saved
plan/output path. Each actual log must contain the one-test success summary.
Integer start/end observations must be ordered, and each preceding end must
be no later than the next start. Moving the final plan after the component
or the first render before it must refuse the actual scheduling assertion;
checking unordered summaries alone would not establish this property.

Build context comes from the externally bound build, actual compiler log,
original/copied executable bytes and compiler build-script stamp. The
expected plan software is not inferred from the subject plan. This wrapper
consumes a separately admitted build; it does not rerun compilation or
independently rederive Cargo's complete dependency semantics. The owner
continues to bind the exact compiled listing/source population before
launching the stage.

After these authority checks, the actual core `run_controls` runs first.
Its complete status and exact count require 45 controls: 35 expected
refusals and 10 valid companions. Only then does the wrapper call the
actual `read_population` for all ten cases and all 3712 precision samples.
The same live core Budget is passed to both. The wrapper does not pool a
failed case or precision subset into success, and it introduces no new
coordinate, DN, quantization, rank, observer or kernel tolerance.

The control and population receive mutable partial result dictionaries
attached to `active_child` before each call. A thrown exception therefore
retains the attempted numerical consumer state rather than just a later
generic wrapper error. Complete control precision and population precision
are persisted separately, avoiding unnecessary duplication in the terminal
authority record. These are result serialization choices, not extra
product TIFFs or independent numerical replications.

## Finalization and encompassing authority

Sources, release inputs, consumed authority files, numerical input files
and produced reader artifacts are rechecked through publication. A late
failure changes the result to `REFUSED_GRID_ADAPTER_PRIVATE`, preserves the
first record under a rejected name, and attempts a bounded negative write.
The original failure and finalization errors are retained; failure to save
the negative record is additionally logged and the process remains nonzero.
The outer owner must not admit a preserved provisional record on that exit.

Local CPU/wall limits share clocks captured before imports. The ndarray
backing cap belongs to the same live core Budget; it does not count all
Python objects or establish RSS. New wrapper/reader artifacts are reserved
through Store writes. Local work is explicitly a pre-publication sample.
Zeno confirms that one encompassing Job owns terminal CPU for worker,
producer, readers and derivative-private descendants, with the owner CPU
and complete 600 CPU / 1200 wall / 128 MiB artifact envelope. Its actual
terminal inventory includes partial files and distinct identities of all
twelve product TIFFs. These responsibilities cannot be discharged by the
wrapper's local result or by the producer's pre-write budget sample.

`PASS_GRID_ADAPTER_PRIVATE_ONLY` is consequently one consumer prerequisite,
not a complete private-campaign, derivative, RAW, registration-coverage or
quality admission. Source review of this wrapper and Curie's 45 unexecuted
instrument definitions does not claim those instruments have passed. The
owner’s source/command freeze and actual complete deciding records remain
required.

**Final source disposition:** the reported authority, ordering and accounting
findings are closed in the final pins above. No additional blocking wrapper
defect was found in the bounded reread. Freeze those sources, their exact
command/request and the encompassing owner before the first complete private
execution. This is readiness for that frozen execution, not an executed
reader or whole-campaign PASS.
