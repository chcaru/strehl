# M194h metadata correction after the first preserved refusal

Root decision, 2026-09-08. The autonomous program authorizes this narrow correction and its finite metadata verification. The scientific experiment and its12 renders remain unchanged and unrun.

## What actually happened

The first prepare-stage.py build invocation exited1 after0.06300000000192085 seconds of whole external wall, before constructing a source freeze, release, build directory or compiler process. Its canonical receipt records REFUSED, stable input, sampled0.046875 CPU/0.01600000000325963 wall; the complete prospective10CPU/20wall slice remains charged. Raw stdout is empty; stderr1129 bytes and actual exit/outer receipts remain in work/build-preparation-external-1-*.

Commit b2475a48f4fb73000b9748142c3e2cbc121850ab preserves all33 original source/evidence files. The exact changed-file set and every committed blob's equality to its working bytes were verified. Its13 replaced strehl-core/Cargo.toml lines are preserved CRLF bytes under the byte-exact commit; the meaningful four-line feature addition is the same reviewed change. No user proposal heading was committed.

The follow-up command read Path.stat and os.fstat before/after on exactly pyramid.rs, CLI Cargo.toml and prepare-stage.py. On pyramid.rs the two stable ctime values were1787691937435767000 and1788888507528517700ns; dev645901345302496490, inode9851624186970066, size208956, mtime1788888507528517700 and link count1 agreed across both APIs. The other two sources showed the same kind of split, with each API independently stable. This is actual local metadata evidence, not a changed-source observation.

Python3.12 documents Windows st_ctime/st_ctime_ns as deprecated while timestamp semantics transition; the API-specific discrepancy above is established by the local command, not inferred from documentation. [Python stat_result documentation](https://docs.python.org/3.12/library/os.html#os.stat_result.st_ctime)

## Minimal correction

Keep full path-before/path-after and full handle-open/handle-close identity comparisons, including each API's ctime. Compare shared dev/inode/extent/mtime/link fields across the path/handle boundary. Preserve source bytes, exact digest bindings, non-reparse checks and source-to-output authority. The checker retains both full path and handle identities across repeated reads. No numerical function or scientific acceptance threshold changes.

The original reports remain frozen in the committed history. Short correction addenda identify the new source bytes and the exact read-path changes. A single metadata control must call the actual corrected read paths on fixed owned source bytes. Stable API-specific ctime values must pass; path-only ctime change, handle-only ctime change and shared inode change must reject, followed by restored bytes/hash. It must exercise those predicates without a candidate main, numerical library, native input or child process.

## Finite corrected preparation

The existing first10CPU/20wall charge is never refunded. Three corrected once-only preparations each retain another full10CPU/20wall slice, yielding40CPU/80wall for preparation, including the failed first attempt. Their metadata receipts use preparation-2 names. Source-freeze-1 and stage release-1 names remain unused and fresh; build-1/components-1/subject-1 and target/m194h-pedestal-causality-1 are still untouched. No prior evidence is overwritten.

A separate10CPU/20wall/1MiB metadata-control slice includes the small initial three-source OS observations and the one fixed corrected-read control. Thus the complete finite metadata allowance is50CPU/100wall, with8MiB retained metadata overall. This amends only preparation's original30CPU/60wall line; all original charges stay, and build300CPU/240wall/8GiB plus4GiB scratch, component60/60/1GiB, render120/180/1GiB and checker60/120/1GiB stay fixed. There is no automatic retry.

Before proceeding, retain the powered metadata control and independent source review, then run the corrected preparation once and inspect its actual whole external exit/wall. Commit exact corrected source/release bytes before the first build. Explicitly require identical build/components/render source maps equal to the subject map and contained in the final independent checker's source map. Only the original12 consumer calls and one saved-output checker are authorized.
