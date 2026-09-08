# Independent native release preparation review

Root reviewed the complete 19,648-byte preparation source
`work/prepare-native-release-1.py`, SHA256
`d73e04c2e0ef948a9f73275826b741025bc40150dd67f27c5fe8915c3c25d7f2`,
against the held native parent and actual runtime-capture parent. This is a
source review, not a native execution or an admission of any real derivative.

**VERIFIED by source inspection:** the preparer now requires actual build3,
private2 and dependency capture results. Build3's independently read result and
copied executable have literal pins; caller-supplied private, runtime, capture
and prior-work hashes are checked against the bytes parsed. The capture must
carry the held parent, specification and process helper, matching before/after
source and input maps, actual released commands, terminal child accounting and
the exact captured runtime. Missing prerequisites stop before the release write.
The preserved prototype is not the execution preparer.

The choice points rechecked independently were stale-build substitution,
relative versus absolute FileRefs, a capture result with incomplete CPU,
successful child versus successful enclosing parent, erased earlier resource
use, and the interpreter flags actually consumed by the independent reader.
The exact copied build3 executable and four-test listing are bound. The nine
historical input triples are compared with literals from both held sources
through AST parsing, without importing either source or reading capture bytes.
The reader's original argument arrays match the native parent's expected arrays,
including the fresh per-frame cache path and omission of an extra UTF-8 xoption.
Source maps merge with conflict checks, and the final current-source and input
pass precedes the exclusive release write. No change to a scientific threshold,
population, production default or native implementation is made here.

The preparer cannot independently observe its prerequisite parent's operating
system exit or final stdout. Root must check those actual retained records and
an independent actual-capture read before releasing a native execution. Likewise,
a structurally valid prior-work object does not prove its values: root supplies
an explicit observed accounting record. Capture preparation accepts metadata
and code, not image payloads; real originals remain unopened at this review.
The runtime's recorded files will be rechecked by the released native parent and
reader. These dependency pins are not a claim of a hermetic interpreter.

No remaining source blocker was found for preparing an exact native release
after those prerequisites exist. The actual resulting manifest still needs its
own comparison with the observed prerequisites before execution. The review
does not run the preparer, reset the real-stage budget, or authorize a claimed
alignment result.

## Root's later prerequisite addition

After successful dependency capture, root added five required input filenames
to the preparer's existing `add(ref(...))` list: the actual independent capture
read, capture console/exit/outer observations, and the explanatory prior-work
record. The resulting source is 19,881 bytes, SHA256
`967e5d42ddd061538a3dd0895fad2eb705fe3654dd65f2e06624d92ca40b7af7`.
All previously reviewed logic is unchanged. This addition is root-authored;
its independent review is delegated to implementation_audit with the actual
capture read. It must not be described as independently verified by this note.

The final metadata list adds a sixth file, the adjacent decoder-DLL supplement.
The final preparer is 19,925 bytes, SHA256
`80427c42c6ee97cfc84c6308a2810c73b74e166f9b81ef4a28f07789aef4f9f1`.
The independent actual-capture read now verifies both additions and the limited
supplemental endpoint-observation method. Numerical sources remain unchanged.
