# M193c coverage preparation 2 — independent actual metadata read

VERIFIED: the saved preparation and six control outcomes support the proposed coverage release. No remaining metadata blocker found. This is preparation evidence, not a coverage, registration, alignment-quality, or product-quality result. The coverage output directory was still absent at this read.

## Actual records and execution scope

The root-observed preparation receipt records exit **0** and **2.3172686 s** elapsed wall time. Its command names Python 3.12's pinned executable, `-B -X faulthandler`, the absolute successor preparer, its external source digest, and the ten required input/review option pairs. I read the saved outer receipt, console, and exit file; I did not independently observe that original OS process.

Deciding actual records, paths relative to `experiments/m193c-output-grid/`:

| Record | Bytes | SHA256 |
| --- | ---: | --- |
| `work/prepare-sensor-white-coverage-release-2.py` | 43,517 | `290ee0598f3704d6ddfeafe6516ba9b15a71aefe40a0ad8ce689a620bf538804` |
| `sensor-white-coverage-release-2.json` | 98,423 | `a6ab7a11ab053c61c12e3496414fca22b15afd31f43c642b9e6dc1d01b8b9801` |
| `work/sensor-white-coverage-release-2-preparation.json` | 16,181 | `3c3d02d2e78e86e2c961db2e4c135b672e71601a8d1965bec73afe79967c29be` |
| `work/sensor-white-coverage-preparation-2-controls/result.json` | 7,290 | `060b1a11566af2485a0006a76f6c28ac8dd3f50654d23da5a22894311adac643` |

The console reports `PREPARED_METADATA_ONLY`; the details correctly retain `PROPOSED_COMMANDS_ONLY`. The controls report `PASS_STABLE_METADATA_IDENTITY_ONLY`, null error, and no finalization errors. The console's 122,006 requested metadata-write bytes remain below the separately reserved 2 MiB. This write count is not a replacement for the nonrefundable reservation.

## Rechosen control evidence

I checked the six ordered records against the retained tiny fixture bytes and, for replacement, both retained filesystem identities. I did not rely on the six booleans alone and did not rerun the controls.

| Actual case | Deciding witness and disposition |
| --- | --- |
| baseline | The original 14-byte JSON returned with its recorded digest; all selected stable fields matched. |
| access-time-only | Recorded access time increased by exactly 2,000,000,000 ns; all five selected stable fields and content digest matched; the original bytes returned. |
| changed-content | The retained JSON contains `19` instead of `17`, with the same 14-byte extent and selected stable fields. Its digest changed; the actual refusal was exactly `same-buffer metadata SHA256`. No value returned. |
| mtime-only | Recorded modification time increased by exactly 2,000,000,000 ns; other selected fields and content digest matched. The actual refusal was exactly `stable same-buffer metadata identity`. |
| replaced-inode | Same bytes, extent, device, modification time and attributes; inode changed from **844424933091561** to **844424933091562**. The retained original and replacement still had these respective identities at this read. The actual refusal was exactly `stable same-buffer metadata identity`. |
| restored | The original 14-byte JSON returned again with its digest and selected stable fields intact. |

All seven retained fixture FileRefs matched actual bytes and hashes: 98 retained bytes, versus 112 requested fixture-write bytes including the replacement write. Each named refusal matched its expected boundary; none was counted merely because an unrelated exception occurred.

The successful access-time control establishes prospective power on this filesystem. It does **not** identify the failing field in preparation 1. That original combined predicate and its missing per-field observation remain the historical limit; no access-time cause is asserted retroactively.

## Release, population and accounting choices

I independently rehashed all **165 current source bindings** and all **291 non-image input references**. The 300 input paths were unique after resolution. The nine TIFFs were checked only by recorded association, ordinary-file status, extent, link count, and distinct device/inode identity; I did not open their payloads. No RAW or retained/deleted snapshot was opened. The predecessor's **153 sources and 145 inputs** remain present unchanged, including original failure evidence. Its recorded before/after source and input maps agree with that executed closure.

I followed all nine proposed rows through the actual native result, independent audit, fresh reader result, and read request. Indices remain **0, 13, 26, 39, 52, 65, 78, 91, 104**. Normalized path, SHA256 and extent associations match for primary receipt, reader, request, and TIFF. The original-0 primary remains historical reuse; the other eight primaries remain fresh, and all nine readers are the admitted fresh readers. Each recorded reader retains 11 native checks, eight domain controls, ten camera-white control groups, and successful status without finalization errors. The scalar check is explicitly `scalar-black-camera-white`. The audit's 4,688-row evidence per frame is associated, not independently pixel-recomputed here.

I independently summed the two preparation allowances with decimal arithmetic. Neither failed-attempt cost nor its allowance is refunded:

| Carried quantity | Before coverage |
| --- | ---: |
| CPU seconds | 324.453125 |
| Conservative wall seconds | 347.4812478 |
| File bytes | 2,157,421,716 |
| Metadata bytes | 20,967,233 |

Both preparation allowances are separately **30 CPU s / 60 wall s / 2 MiB files / 2 MiB metadata**. The actual short preparation times do not reduce them. The separate transient-copy reservation is exactly the nine TIFF extents plus 5 MiB: **1,785,427,283 bytes**. It is not charged twice in prior work. The combined pre-worker file charge is **3,942,848,999 bytes**, leaving **352,118,297 bytes** under the unchanged 4 GiB cap. CPU/wall and metadata caps remain 1,200 s / 1,800 s / 128 MiB.

The parent and worker command arrays equal the details' arrays exactly. They select the held `coverage-sensor-white-run.py`, the new release 2, fresh parent/worker caches under `sensor-white-coverage-1`, and only the registered actual-release/request digest substitutions. The same M193b consumer and held runtime requirements remain bound. OpenCV/tifffile import and build checks remain prospective worker checks; this metadata review does not claim they have run.

## Independent audit execution and limits

I used separate stdlib-only read/hash/JSON checks through the pinned Python executable with `-B -`; no author module, preparer, control, decoder, or registration helper was imported or executed. The final read returned exit 0 with `PASS_INDEPENDENT_ACTUAL_METADATA_ASSOCIATIONS`, six powered control observations, nine associated rows, exact commands/carry, and zero image payloads opened.

Two read-only audit setup failures are retained in the tool history: an exploratory read treated an embedded launch object as a FileRef (`KeyError: path`); the first combined audit then compared absolute and repository-relative build paths as raw dictionaries. That assertion failed after the complete source/non-image-input hash pass. The correction compares resolved path plus digest and extent, confirming all nine requests bind the same build. These were reviewer setup errors, not subject refusals; no subject bytes or criteria changed.

Root must still freeze the exact release/command package and observe the coverage execution. No successful coverage or alignment admission follows from this preparation report alone.
