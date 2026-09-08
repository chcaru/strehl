# Independent actual dependency-capture read

2026-09-07. **VERIFIED BY RETAINED RECORD AND CURRENT FILE INSPECTION.** The
actual evidence supports COMPLETE_DEPENDENCY_RUNTIME_CAPTURE_ONLY. No blocking
command, prerequisite, source, dependency-byte, terminal or resource mismatch
was found among the declared records. The six-file dependency selection has a
known adjacent-DLL omission described below; it is not full decoder binary
closure. This reviewer did not recapture runtime, import any subject or
numerical dependency, decode RAW, read image pixels or execute a process test.
This is dependency evidence only, not native derivative or decoder agreement.

## Actual terminal chain

The release/source checkpoint is 3bc87c03. Paths below are relative to
experiments/m193c-output-grid.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| runtime-capture-release-1.json | 27467 | 7a2436afe602b2d53fdf95600e6285c26ca390a429cb5c6255b1be8206502a30 |
| runtime-capture-1/result.json | 58261 | 0cb18db67c7a87674999f0714e964ff19883b43fbd88f7a2436b44d5c41e43fa |
| derivative-runtime-1.json | 2226 | 413975cbbbf5b1dc33407e6be1aa23e9195dc4471f1ee7e9de99f903dccd9442 |
| runtime-capture-1/capture.log | 275 | b2a8f2167d78d8d4f5549999a519ffe23448247151d04962e8a584ef1b3e5d22 |
| work/runtime-capture-1-console.txt | 620 | eddfb927b3c436aa3e530f9ef04440eb4b06660f9ecbaebfa762b95e7da13c7a |
| work/runtime-capture-1-outer.json | 1048 | cc5495d5b575cf55fff2cc42c395452475e2a7a642e91112932f73b52fd383a8 |
| work/runtime-capture-1-exit.txt | 3 | 13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354 |

The actual parent argv in the result and root's outer record equals the exact
released parent vector after the sole release-SHA substitution. It invokes the
pinned Python312 executable with -B, -X faulthandler, the owned cache-parent
prefix, runtime-capture.py, and the exact release/hash/output arguments. The
actual child argv equals the released reader vector: the same Python, -B,
faulthandler, cache-reader, independent-derivative-read.py and only the
--capture-runtime argument naming derivative-runtime-1.json. These vectors are
preserved in the hashed release/result and were fully compared, not inferred
from a script name. The capture branch takes no image or RAW argument.

The result has schema m193c-runtime-capture-v1, its required successful status,
null error and empty finalization errors. The final parent console binds its
exact 58261-byte result hash and repeats that success without errors. Root's
outer observation records integer OS exit zero and the matching release/argv;
the exit file is exactly 0 followed by CRLF. This audit reads root's retained
observation, rather than claiming a second independent wait on the process.

The one child log line is CAPTURED_DEPENDENCY_RUNTIME_ONLY with the exact
runtime FileRef. Its absolute runtime path and the parent's repository-relative
ref resolve to the same file with identical SHA256 and extent. The actual helper
log ref similarly resolves to the parent's log ref. Both files were rehashed.

The helper reports actual child exit zero, direct exit observed, pipe EOF,
terminal Job accounting, final active processes zero, no primary or cleanup
error, and the exact child command. The ordinary drain has one observation,
first/last active zero and completed=true. Explicit termination fields are
attempted=false, succeeded=false and before_accounting=null. This is not
inferred from total_terminated_processes. This ordinary capture exit does not
replace the separate controls4 delayed-descendant tests.

## Actual dependency and source bindings

All 135 released current source hashes/lengths match both result maps. All
fourteen actual input refs match both input maps and current files. Build,
private admission and independent-review associations equal their release
fields. A scoped git diff over all these paths against 3bc87c03 returned no
changed path. The metadata/byte pass rechecked 163 distinct consumed files,
including the sources, inputs, interpreter, module files and terminal records.
It used only standard-library JSON/path/hash operations and did not import the
files it inspected.

The captured schema is m193c-derivative-reader-runtime-v1. Its observed version
fields are Python 3.12.10, NumPy 2.4.4, rawpy 0.27.0 and LibRaw 0.22.1. The full
Python build string remains in the actual JSON. These are the released child's
reported versions bound to actual module bytes, not a new version query or
independent re-import by this reviewer.

The six distinct actual module refs equal the parent's runtime_module_refs.
The paths are beneath the pinned Python312 installation's Lib/site-packages;
each was streamed and hashed without interpreting its contents:

| Relative installed file | Bytes | SHA256 |
| --- | ---: | --- |
| numpy/__init__.py | 27212 | b16a4f347c6583c878e1973a208564e01686b79cc70911ad0157e05d8eecda37 |
| numpy/_core/_multiarray_umath.cp312-win_amd64.pyd | 3714560 | f4523c2dfe641a904605029ce4a5046388bd61b18afc0594d34018b5e6d848f8 |
| numpy.libs/libscipy_openblas64_-63c857e738469261263c764a36be9436.dll | 20415488 | 63c857e738469261263c764a36be9436ebdeaa272e340a828f42047a97131080 |
| numpy.libs/msvcp140-a4c2229bdc2a2a630acdc095b4d86008.dll | 575056 | a4c2229bdc2a2a630acdc095b4d86008e5c3e3bc7773174354f3da4f5beb9cde |
| rawpy/__init__.py | 4700 | 24a06e984ef21c4c01569105f862c347f8a92446ec361c40835aa15dfa921eff |
| rawpy/_rawpy.cp312-win_amd64.pyd | 205824 | 51fecc08ba36294590a9a4b35f0ce246f0349a9b9ee509a13d6589ba7150b897 |

The interpreter is the unchanged absolute
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe,
104952 bytes, SHA256
4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a.
Its runtime FileRef equals the release's executable ref and actual argv path.
The module population lies within the registered 4-to-32 distinct files and
each file is below 128 MiB. This is the declared dependency selection, not a
claim that every operating-system library or transitive interpreter input is
captured.

Root's subsequent metadata inspection identified two DLLs directly inside the
rawpy package directory which runtime_record does not enumerate: it checks
package/.libs and the sibling rawpy.libs directory, but not these adjacent
files. This reviewer independently rehashed them without loading or interpreting
them:

| Adjacent rawpy file | Bytes | SHA256 |
| --- | ---: | --- |
| raw_r.dll | 1926656 | da20108e301a929170fe1af2acb2ef7e5de62347057f860139fda111d504fa39 |
| vcomp140.dll | 193152 | 55aba23cdcd6484fbb06f4155b8ca75adfce7a881f10afd0c49457165e677164 |

The unchanged six-file capture must not be described as independently pinning
these two files. Root's separate work/native-adjacent-dependencies-1.json,
1028 bytes, SHA256
c93af42e6fd2a26d2de7cdc6e7decf7156f9181a124fe4a9d2ab99e03a82a6aa,
binds their two actual absolute FileRefs and the captured runtime SHA above.
Its schema is m193c-adjacent-dependency-observation-v1. It expressly requires
root to verify the underlying DLL files before and after the native parent,
retain both observations in the outer record, and refuse admission on mismatch
or a missing observation even if the parent exits zero. Hashing only the
supplement JSON would not discharge that requirement.

This is a suitable narrow supplement for those two endpoint byte observations.
It does not retroactively enlarge the completed capture, prove which binary
Windows actually loaded, or provide a full interpreter/loaded-module closure.
The future actual before/after checks remain outstanding. No held reader,
numerical or capture source changes, build, private rerun or recapture follows
from this additional recorded-file scope.

The parent records no removed controlled environment names, no explicit child
overrides, and an empty remaining controlled subset for this run. The actual
runtime records OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS and
NUMEXPR_NUM_THREADS all equal to the string 2. Unrelated inherited environment
values are deliberately not reproduced; byte identity is not a hermetic-host
claim.

## Resource scopes and conclusion

The terminal child Job CPU is 4375000 ticks: 3593750 user plus 781250 kernel,
or 0.4375 seconds. Final parent stdout reports complete terminal accounting and
1.65625 CPU seconds total. Subtracting the child once gives 1.21875 parent CPU
seconds. This differs from the stored result's prepublication 1.59375-second
total. No nested child CPU is added twice.

The stored result's wall sample is 1.625 seconds, final stdout is
1.702999999979511 seconds, and root's outer observation is 1.7583753 seconds.
These are distinct scope boundaries, not repeated timing estimates. All remain
within the total 30 CPU / 60 wall allowance. The child's actual wall is 0.5
seconds within its remaining 58.96899999992456-second allowance; its remaining
CPU allowance is 28.9375 seconds. Recorded peak Job committed memory is 65204224
bytes, below the actual configured 2147483648 bytes. Memory is committed memory,
not RSS, and these observations are not a performance benchmark.

The 275-byte log and 2226-byte runtime fit their one-MiB caps; the result fits
four MiB. Recursive file enumeration with -Force finds only capture.log and
result.json within runtime-capture-1; the runtime JSON is at its separately
declared sibling path. No failure publication or unexpected file occurs there.
The actual final stdout result pin and current bytes agree after rechecks.

Disposition: the actual completed dependency-capture record and runtime may be
bound into the forthcoming native release. This establishes neither RAW decode
agreement nor a native output, registration placement, calibration or quality
result. Those remain separate future consumers and measurements.

## Narrow follow-on preparation delta

Root separately requested a source-only review of its first five-filename
addition to work/prepare-native-release-1.py (19881 bytes,
967e5d42ddd061538a3dd0895fad2eb705fe3654dd65f2e06624d92ca40b7af7).
Its final revision adds the supplemental dependency JSON as a sixth filename:
19925 bytes, SHA256
80427c42c6ee97cfc84c6308a2810c73b74e166f9b81ef4a28f07789aef4f9f1.
The complete final diff against 3bc87c03 adds only this independent capture
read, the three capture console/exit/outer files, work/native-prior-work-1.md
and work/native-adjacent-dependencies-1.json to the existing add(ref(...)) list.
That function verifies bytes, normalizes
repository paths and rejects conflicting references; the final input check
still precedes publication. No argument, population, mathematical condition or
threshold changes. No blocking discrepancy was found in that bounded delta;
the previously complete source review remains root's independent review of the
preparer author.

Root's proposed carry uses the final 1.65625 CPU seconds and the outer
1.7583753 wall seconds observed above. Its proposed one-MiB file/metadata amount
is a conservative reservation for capture evidence, not measured write I/O;
the eventual exact record and declared file population still have to fit before
native preparation. This review did not execute that preparer or establish
that any earlier native/RAW/coverage work occurred. Root records that stage
history explicitly in the forthcoming prior-work input.
