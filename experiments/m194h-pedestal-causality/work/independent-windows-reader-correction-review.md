# Independent Windows reader correction review

2026-09-08. PASS_SOURCE_REVIEW_ONLY for the five reader corrections listed below. This reviewer did not author those five corrections. The reviewer authored the separate metadata control; root must independently review that control before executing it. Original source reviews and refusal are preserved in b2475a48f4fb73000b9748142c3e2cbc121850ab. No corrected helper, control, candidate import, build, numerical/decoder or product function was executed here.

## Exact corrected pins

- prepare-stage.py:11367 B, a01b865ec3cb460958cf8a172aefc3bd13239878bfe0a52dee442214207903ef.
- capture-stage.py:4300 B, 8255efc220ffa171310e1aa1e31aa031771fe92e7190ce8c3165d3da72358dfd.
- work/check-run.py:5859 B, beb4472383f6193f936342ad1a3bdfc86feeeb29fc541b5ebc0c072011c3b877.
- build-and-run.py:34864 B, 5738d18ac41044361b6083ed38fa743dedee2a3005470130c19b2b5d1e2dadb3.
- independent-verify.py:69266 B, 800afb0cc1dbfd6528c163fd53fcc67eb325ab7c53943babd40689f0830bdd65.

The old policy incorrectly equated complete path-stat and handle-fstat tuples. The correction removes only ctime from cross-API equality. It retains each API's full initial/final tuple including ctime. Common dev/ino/size/mtime fields remain; nlink remains where the original tuple included it, and the checker also retains attributes. The wrapper's original tuple did not include nlink; this delta does not claim to add that separate policy.

Preparation and capture retain initial/final path tuples and open/close handle tuples separately, compare all existing shared fields and actual extent. The driver retains the original read cadence, size/hash/FileRef predicates and callbacks; full initial/final path and open/close handle identities plus cross-API shared identity are required. Checker Files.read/actual and initializer-source observation use the same division. Files.read now stores both full path and full handle identities and requires both on repeated reads. Ctime drift within either API is still a refusal; stable differing API conventions alone are allowed.

Read-only git diff against b2475a48 confirms the driver changes only read plus new shared_identity. Checker changes only Files.read, Files.actual, numpy_source_observation plus new shared_identity; its mathematical/decoder/metric and resource bodies are untouched. Preparation additionally preserves actual first refusal10/20, changes receipt attempt suffix1 to2 and cumulative preparation30/60 to40/80; capture consumes that prepared attempt2. Those explicit orchestration changes are not described as identity-only byte changes. Capture/checker process, terminal and science paths otherwise remain held.

The root's observed ctime disagreement motivates this narrower predicate; it does not establish universal Windows timestamp behavior or prove these corrections executed successfully. The actual first refusal remains negative and fully charged. No content hash is replaced by metadata identity and no old outcome is retroactively admitted.

## Prospective control and validation scope

Separate windows-file-identity-control.py selects the actual closed read paths and powers stable-different-ctime, path-only/handle-only ctime drift, shared-inode mismatch and restored positives on fixed source bytes. Its exact protocol names35 rows, seven entry points, finite10CPU/20wall/1MiB and external actual-exit/stdout association. Root caught the initially omitted digest dependency; it is now selected, and math supplies strict()'s full closure. Static AST/symtable checks found no unprovided globals in all five selected groups (3/1/2/5/13 definitions). These are source checks, not control outcomes.

Validation commands were read-only git diff b2475a48 over the five exact paths, source reads and Python312 -I -S -B stdin SHA256/AST/symtable/plain-metadata constructor scripts. No selected definition or candidate main was called. Ordinary source hashing and metadata sizing do not establish numerical or runtime success. Exact new source bindings plus independent root review and once-only release remain required before the proposed control/preparation/build sequence.
