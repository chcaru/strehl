# Independent actual sensor-white coverage outcome read

VERIFIED saved outcome: the frozen parent exited 1 with `REFUSED`; its worker
exited 1 with `REGISTRAR_REFUSED`, after all eight controls passed. The first
nonreference registration failed. No nine-input manifest, common-overlap
rectangle or original-52 gauge was produced. The previously admitted native
TIFFs remain admitted; this separate coverage method did not complete.

The independent audit exited 0 with `PASS_SAVED_COVERAGE_OUTCOME_AUDIT` and
`subject_complete=false`. This verifies the saved refusal, associations and
accounting, not successful coverage. It read records and hashed opaque files;
it did not import the subject, decode RAW/TIFF, regenerate fixtures or rerun
registration. No algorithm, threshold or subject artifact was changed.

## Actual evidence and first refusal

The run used [release 2](sensor-white-coverage-release-2.json) from commit
`1f3c6bd7`. The [audit JSON](work/independent-sensor-white-coverage-1-audit.json)
contains the full checked FileRefs, command, runtime, controls and work records:
18,536 bytes, SHA256
`f5372a6fc28f9a0d34cc37356374beeca266ac5539d5fb93d3d1f2ff1b7c979a`.
It binds the actual [parent result](sensor-white-coverage-1/result.json),
[worker result](sensor-white-coverage-1/worker/result.json), root console/exit/outer
records and prior native admission. The audit checked 454 distinct files.

All 165 released local source pins and 300 input refs agree with the actual
before/after evidence. Worker copies of the frozen M193b consumer and M193
reference match their pins. Runtime records agree before/after: Python 3.12.10,
NumPy 2.4.4, OpenCV 4.13.0 and tifffile 2026.5.2, including the recorded OpenCV
build-information digest and interpreter pin; no hermeticity is claimed.

Independent ordering of the nine actual TIFF digests selects original 65,
selected-stack local 5, as constructor index 0 and reference. The next input is
original 104, local 8, constructor index 1. The actual traceback reaches
`register_to_reference` with:

```text
UNMEASURED_INPUT_REGISTRATION_INADEQUATE: too few total mutual landmarks
```

No failing landmark count or placement error was retained. The committed
prefix is reference identity only: **no nonidentity registration succeeded**. The seven
unvisited originals, in actual byte order, are **13, 78, 52, 91, 0, 39, 26**.
`native_manifest` and `original_gauges` are null. Reference identity is a
construction fact, not measured placement accuracy; original 52 was unvisited.
This outcome concerns this fixed registrar and pair, not every possible pair
or registration method.

## Eight controls

The audit consumed all eight saved control records and hashed their five
fixture TIFFs (3,318,880 bytes), without rerunning them.

| Control | Actual result and scope |
| --- | --- |
| `frozen-three-input-manifest` | Exact frozen positive manifest and fixture identities. |
| `identity-retention` | 99,918/99,918 retained; PASS. |
| `crop-retention-destroyer` | 97,188/99,918; `FAIL_GEOMETRY_FIELD_OF_VIEW`. |
| `rehashed-denominator-destroyer` | Old path reports 400/400 PASS; trusted-input consumer refuses the changed manifest with `UNMEASURED_DENOMINATOR_UNDEFINED`. |
| `restored-identity-retention` | Exact identity evidence restored. |
| `complementary-self-registration` | 256 mutual matches, zero self residual; liveness only. |
| `complementary-first-refusal` | Fixed complementary-focus pair refuses at index 1 with one committed reference. |
| `exact-gauge-direction-and-order` | Noncommuting/sign-sensitive map witnesses agree with separate exact 3×3 inversion/composition; wrong-order displacement is (-4,10). |

Self-registration and private gauge algebra do not establish native placement.

## Job and cumulative costs

Direct exit/EOF and completed drain were observed: active processes 0, total 2,
terminated 0, no termination attempted, observer error null and cleanup empty.
Root independently observed parent exit 1.
Worker CPU was 17.609375 seconds, wall 17.93799999996554 seconds, and peak Job
committed memory 8,062,197,760 bytes under 8 GiB. Actual remaining child limits
were 872 CPU/240 wall seconds. These are operational observations, not a
comparative performance claim.

| Final cumulative accounting | Value |
| --- | ---: |
| Complete CPU, including prior costs | 348.203125 seconds |
| Internal final wall receipt | 372.5742478000466 seconds |
| Conservative next wall: prior 347.4812478 + root outer 25.1913279 | 372.6725757 seconds |
| Charged file extent | 3,946,512,222 bytes |
| Charged metadata extent | 21,311,576 bytes |

CPU comprises prior 324.453125 + worker 17.609375 + new parent 6.140625 seconds.
File accounting is prior 2,157,421,716 + full snapshot reservation 1,785,427,283
+ 19 retained outputs totaling 3,663,223 bytes. New metadata is 344,343 bytes.
The reservation is nine TIFF extents plus 5 MiB; it is not a claim all nine
were decoded. It remains charged after refusal, as do earlier deleted native
snapshots. No owned temporary copy remains. Both preparation allowances and
the failed preparation evidence remain bound: native base + 60 CPU/120 wall
seconds/4 MiB, without refunds. All cumulative stage caps remain satisfied.

## First audit failure and precise correction

The first held audit, 39,648 bytes, SHA256
`65522ce95d64cc80fd7f16e0a792ec7f669521e4f8e6b85fc94780782e6471ef`,
remains available at the same source path in Git `1f3c6bd7`. It actually exited
1 at `ValueError: actual held source bytes stable from release commit`, after
the preceding outcome/control/resource checks, and produced no successful
receipt. This audit failure is preserved separately from the registrar refusal.

The assertion exceeded the pre-execution claim. The committed
[release review](independent-sensor-white-coverage-release-2-review.md) had
already disclosed the contract difference; the corrected audit checks that
review's exact Git blob. It asserts, rather than excludes, exactly one path:
`experiments/M193-cover-overlap/contract-v1.json`, released SHA256
`19421729ac39273a5f61cda5068026f3458ba08c98f0aa954de7c219cbfabf47`
versus committed SHA256
`012a1ff307f78c79789d37a7cad0ab036f05a2331669f45c48543c492e8ccbd9`.
Only `status` and `algorithm_precommit_commit` differ: the old precommit status
and null become `FROZEN_PRE_COMPARATOR_OUTPUT` and
`dfaa2f639b85af0b568e7f8af1e8722548831c91`. The audit requires exact old/new
values, parsed equality after those two replacements, and no other byte
change after CRLF normalization. The other 164 source contents correspond to
Git after newline normalization; all 165 executed local bytes match release
pins. No historical commit or contract was rewritten.

Root authorized this correction before audit 2. Its source is 43,454 bytes,
SHA256 `ec4f22316255ad98e95c56ec2e07a6d7ef4301e0cc62451a79c9d9f2b66b3f44`.
Audit 2's actual exit 0 was captured explicitly. Both audit attempts used:

```powershell
& 'C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe' -B 'experiments/m193c-output-grid/work/independent-sensor-white-coverage-1-audit.py' --release-sha256 a6ab7a11ab053c61c12e3496414fca22b15afd31f43c642b9e6dc1d01b8b9801 --result-sha256 3068d412483c69e71a0a682410de1c506788faab74889c65d6f20c7607a06418 --outer-sha256 c2d1d3db94fad6b4986bef67cf25a2c6fb4ee2cd1ce8bb768e5fbfdf73aa7998 --console-sha256 3bd351c699e665f19e037d1b70d590cdfd8ed48fe63c8dc45b9e51339c17122a --exit-sha256 f1b2f662800122bed0ff255693df89c4487fbdcf453d3524a42d4ec20c3d9c04 --commit 1f3c6bd7
```

The source exceeds the initial 40 KiB sketch. Source, 18,536-byte JSON and this
report total less than 92 KiB, within the unchanged reserved 2 MiB future
metadata allowance. No global limit increased. The prior native audit remains
unchanged. No additional pair registration has been executed by this audit.
