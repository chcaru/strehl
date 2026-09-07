# M194b controller and strict-reader review

Independent of root-authored orchestration/scoring and consumer code; this
review makes no independent claim about this reviewer's producer science.
No forty-output baseline is launched by this reviewer.

## Choice points and prospective mutation checks

Before running mutations: preserve the original source and complete artifact
package. Re-choose metadata rather than repeat earlier pixel/error controls.
Read one already-completed independent consumer TIFF through the actual
`score.py::read_tiff`, then create private copies with an Orientation8 tag and
an ICC-profile tag. Original and an unchanged byte-copy are valid controls.
The intended fixed CameraLinear active-grid interpretation must reject the
changed orientation/profile; pixel equality alone does not catch either.
Use no producer or product modification.

Once a complete trusted run index is available, re-seal independent copies with
deleted/reordered/failed command history, altered command/executable binding,
incomplete source snapshots, false output metadata and swapped repeat arms.
Mutations preserve unaffected actual artifacts and must fail structural
admission, not merely change a displayed score. A fresh digest is not evidence
that the mutated content obeys its internal contract.

## Findings from source reading before baseline

1. `score-benchmark.py::score_run` initially ignored `index.commands`, parent
   command logs, and child `m194b-consumer-command-v1` receipts. It could check
   matching pixel/plan receipts without checking which executable invocation
   produced them or whether all20 plans preceded any render. Requested repair:
   bind child command evidence into the index; require exactly20 planning
   commands followed by40 successful render commands, exact expected arguments,
   build/executable/environment bindings, and result hashes per case/arm.
2. The snapshot map now covers the indexed map exactly and binds compiled and
   generator sources. However, initially the scorer did not compare its loaded
   `score.py`/`score-benchmark.py` to their snapshot hashes; it only reported
   current hashes. Also `commission-forward.py` was not snapshotted despite
   `commission_source_sha256` naming it. Requested repair: add this source and
   check its binding; enforce the frozen scorer sources or explicitly name a
   prospective scorer amendment.
3. The TIFF reader initially admitted RGB16 based on array shape, photometric
   interpretation and Software alone. It did not examine orientation or ICC/
   transfer metadata. The desired numerical grid and untagged CameraLinear
   disposition should be explicit, with mutations proving rejection.
4. Build booleans and equal source maps are not sufficient by themselves:
   empty equal maps satisfy equality and the original scorer did not read the
   bound Cargo log. Requested exact build argv/environment, mandatory source
   entries, log binding and the matching compiler-artifact record. The externally
   trusted build-record digest remains the authentication boundary; a new
   self-hash cannot authenticate an arbitrary replacement executable.
5. The actual writer emits an ImageDescription declaring camera-native linear
   data and applied WB. The initial tag allowlist admitted any value for that
   existing tag. Requested validation of this disposition as well as ICC and
   orientation, plus actual binary size matching the build's declared size.
   A third prospective TIFF mutation will replace only the description with
   an incompatible sRGB/no-WB declaration; unchanged pixels must not excuse it.

## Executed TIFF-reader check and repair

Command run against an actual, completed independent consumer output:

```powershell
python -B experiments/m194b-known-scene/controller-review-tiff.py --receipt experiments/m194b-known-scene/work/independent-consumer-8240dcbdf7/full/receipt.json --out experiments/m194b-known-scene/controller-review-tiff-1
```

At reader SHA256
`1bed3c5c27a90849d9496b2f87f4505fc93ae663c65c0cbf6b9bc1df109cdc85`,
both changed Orientation8 and unexpected ICC were admitted with identical
numerical pixels. This is an independently measured rejection gap, not an
assertion that actual product output carried these tags. Original bytes stayed
unchanged. The report correctly says `pass:false` even though the diagnostic
script exits normally after recording its observations.

Root repaired the reader. Re-running the exact same command with output
`controller-review-tiff-2` at reader SHA256
`0d222a9685ada1cb170736b97d8a65502720cae28801dc5a29e354c81af78b4d`
passes all three dispositions: original byte-copy admitted, Orientation8
refused for changing the canonical map, and ICC refused as unsupported
CameraLinear metadata. The mutated file hashes match the first run exactly,
so this does not substitute easier mutations after the fix. Raw pixel hash of
the unchanged actual TIFF is
`1da243b458bf468cda17fc1d4a20b1000577437ce5b38e0fbc44d788ec845b8d`.

The separately preregistered description mutation was then executed in
`controller-review-tiff-3`. Replacing only the existing description with
`Standard sRGB encoded image. No white balance applied.` was admitted by the
same repaired reader. Orientation and ICC mutations continued to reject.
This narrower residual gap also preserved every numeric pixel and the
original artifact. Root then added exact writer-description validation. The
same four TIFF cases all pass their expected dispositions in
`controller-review-tiff-4/result.json`: the unchanged actual output is admitted;
Orientation8, unexpected ICC and incompatible description reject. The final
reader SHA256 is
`d292c8623827eb960bc28dc341398c7e164f5c14cd31af74663ee24c1ff5b5dd`.

The source review also confirms the fixed matrix and pairing logic: exactly
20 case keys, two named arms per case, eight explicitly ordered seed pairs
for each scalar scene, one common frozen crop, original index4 for every
single-frame comparator. There is no output-driven ROI or brightness fit in
this orchestration. The source code serially plans all inputs before rendering;
the new command evidence must prove that the actual run followed it.

`controller-review-index.py` is prepared before baseline execution. It will
re-seal a valid copy with absolute artifact references, verify that positive
control, then challenge12 independently chosen command/source/completion/pairing
contradictions and recheck the positive control. It refuses to touch a running
index. Its intended subject is the completed real artifact package; no mock
TIFFs or replacement native execution are used.

The first actual-index execution is retained in `controller-review-index-1`:
both valid controls refused because analysis sources had changed after the
render and needed an explicit reader revision. Therefore the reported negative
dispositions from that attempt are not counted as structural verification.
No native process or pixel output failed in this check.

The prospective rerun accepts root's externally bound reader-revision record.
For each private test copy it re-seals that record against the changed index
digest while keeping the original previous/current source hashes, and adds the
specific control name to the reason. This permits the intended structural
contradiction to reach its checker. The original index, source snapshots,
revision and all output files remain immutable. This is a regression fixture,
not authorization for changing the real run's evidence.

An attempt with reader-revision-v1 was also retained in
`controller-review-index-2`. The reader was still changing and the valid
controls refused the stale current-source binding; those negative dispositions
are likewise not counted. The reviewer then waited for explicit release of
the frozen v2 binding.

## Final actual-package result

**VERIFIED within the controller/reader contract.** Root released immutable
index SHA256
`37f99736bd32dfb4891bd8fa2b033cacc2c58e9265515fa53cb5921dd80d9c08`
and reader-revision-v2 SHA256
`e46f0ddc09a7894ae4d1899e648977b9aace84da7b2dc45e3d95f049afafa363`.
The executed command was:

```powershell
python -B experiments/m194b-known-scene/controller-review-index.py --index experiments/m194b-known-scene/baseline-1/run-index.json --expected-index-sha 37f99736bd32dfb4891bd8fa2b033cacc2c58e9265515fa53cb5921dd80d9c08 --reader-revision experiments/m194b-known-scene/reader-revision-v2.json --reader-revision-sha e46f0ddc09a7894ae4d1899e648977b9aace84da7b2dc45e3d95f049afafa363 --out experiments/m194b-known-scene/controller-review-index-3
```

It completed with exit0 and all14 dispositions passed. Both unchanged
absolute-path controls read all40 actual outputs successfully. All12
independently re-sealed contradictions were refused:

| Mutation | Actual refusal |
|---|---|
| Missing final planning command | Wrong command count |
| First render before final plan | Wrong complete invoked environment |
| Failed final parent command | Failed controller command |
| Missing child binding | Missing `consumer_evidence`; no score emitted |
| Missing source snapshot | Snapshot map fails exact coverage |
| Failed completion with retained pixels | Incomplete/wrong benchmark index |
| Duplicate paired repeat | Unexpected/duplicate case |
| Swapped full/single labels | Wrong single-frame gauge or subset |
| False parent argv | Parent arguments differ from indexed operation |
| Changed child executable | Pinned exact test invocation mismatch |
| Changed child subset | Wrong complete invoked environment |
| Changed child result hash | Result differs from indexed case |

The original run index remained byte-identical and reviewed sources stayed
unchanged during this successful check. Final integration-reader SHA256 is
`7ec0b8b5b2d18987165aecb461725d95cb789bbaf4bfd43ec40d9a70b6093a29`.
Exact before/after bindings and all dispositions are in
`controller-review-index-3/result.json` (SHA256
`2867034545938475b938e68db13a5591a4c57f5ef55c63f6b57f49c924d1b656`).

This verifies the declared recorded execution, fixed matrix/pairing, source
and output bindings, and tested refusal paths. It does not independently
verify this reviewer's producer model, establish camera fidelity or assign
an image-quality/SOTA result. The other independent reviewer owns the
numerical, producer and coherent geometry/configuration challenges.

Root owns all fixes. The report will distinguish source-only findings from
executed mutation evidence and record the source revisions actually checked.
