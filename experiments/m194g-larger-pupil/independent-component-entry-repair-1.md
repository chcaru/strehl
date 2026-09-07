# Complete component reader entry repair

2026-09-07. Root record of the first complete v2 consumer invocation.

**MEASURED refusal:** commit `4a613525` froze
`independent-component-reader-release-2.json`, SHA256
`92ccac18316d1d58b81b958a363a06e02ba480d2e1f438cb784caf0682d3e8a0`,
before its exact command ran. The parent process collected exit1. The saved
`independent-component-verification-2/result.json` retains the actual traceback:
`verify` sent `reference-interval-amendment-1.md` through `Reads.external`,
which hashes bytes and then parses JSON. The Markdown bytes were correctly
pinned but are not JSON. No component comparison was completed or admitted.
The record's `inputs_unchanged: false` is its uncompleted default, not evidence
that a source changed; the failure occurred before its closing check.

**MEASURED earlier private result, narrower scope:** all193 checks in
`independent-component-controls-2/result.json` passed, SHA256
`527494d126e68f42e58050f1d74e903d4db8f16c4f8bdb116812f92b609d337c`.
They exercised the independent reader's component, payload, resource and
normalization consumers, plus the numerical author's entry. They did not
exercise the independent reader's own complete `verify` entry. A private
suite pass therefore did not establish that this entry accepted its genuine
document inputs. The failed complete command provided that missing check.

**Prospective repair:** use the existing bounded, hash-checking `Reads.bytes`
for this Markdown decision record. Keep JSON parsing on actual JSON records.
Add four private checks through the actual `verify` entry: genuine pinned
Markdown and producer result reads reach the controls dependency; a wrong
Markdown pin refuses; restoring the old JSON-parser choice reproduces its
named failure; restoring the correct entry reaches the dependency again.
The dependency is an explicit private sentinel, never a fabricated completed
private-control authority. The subsequent complete command remains necessary
to exercise the full cross-method comparison without that sentinel.

The prospective private population becomes197. Both complete numerical
producer results, all numerical sources, populations and accuracy bars stay
fixed. Freeze the repaired reader/control sources and fresh private command
before execution, then separately freeze the complete comparison against its
actual private result. Preserve all previous commands and output directories.
This is an input-type correction, not a numerical or resource amendment.
