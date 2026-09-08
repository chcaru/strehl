# One retained-snapshot active-domain diagnosis

Prospective diagnostic after native attempt1's first-frame refusal. No subsequent
original or coverage invocation is admitted. Preserve the original REFUSED result.

The observed question is precise: primary decoded active data are 7032 by 4688
at sensor origin (0,0); rawpy's visible view is 7028 by 4688 at that same origin,
within a 7168 by 5120 allocated buffer. The owned wrapper carries the linked
decoder's `active_area`. M165 independently recorded a 7028-wide visible image;
neither convention alone proves a bad decoder or physically valid sensor extent.

Use only the already retained original0 snapshot and primary receipt. Through
rawpy's public `raw_image` API, copy exactly the primary-declared 7032 by 4688
rectangle inside the decoder context. Never calculate a statistic over the
full allocated buffer. Independently hash this explicit candidate rectangle and
all 4688 rows, compare with the actual primary hashes, and retain every mismatch.
Also hash the independent visible rows and the same 7028-wide subset of the
candidate. Copy ownership and lifetime are explicit; no postprocess, demosaic,
resize, corpus read, second RAW snapshot or new output TIFF is allowed.

The public distinction is documented in
[RawPy's array API](https://letmaik.github.io/rawpy/api/rawpy.RawPy.html):
`raw_image` includes margins, while `raw_image_visible` excludes them, and
copies needed after close must be made while the owner lives. Documentation
does not predict the values of these four columns. No forbidden decoder source
is consulted. Inspect only the owned wrapper and permitted public API.

The independent full/row hashes can FAIL agreement if any candidate sample
differs from the primary bytes. A one-code mutation in disputed column7029,
row2344 must change the same row-digest path, and restoring it must restore that
digest. These are hash/instrument checks, not optical controls. A mismatch is a
completed diagnostic outcome, not a reason to hide the result or retry. Record
per-column hashes, zero counts and ranges only for columns7028..7031. Nonzero
samples show decoded content there; they do not by themselves prove physical
photosite validity or the correct photographic crop.

Interpretation is frozen before execution:

- Matching complete candidate and row hashes establishes independent decoder
  byte agreement on the primary's declared domain for this one snapshot. The
  visible-domain disagreement remains recorded. It can justify an explicit
  sensor-domain reader contract, with a new reviewed native release, not editing
  the refused result or treating this probe as native admission.
- Any mismatch preserves the exact whole/row disagreement. Do not crop it out
  of a success assertion or invent a common denominator. Further investigation
  must name the mismatching domain before another production run.
- Allocation, source, runtime, worker or budget refusal remains an operational
  refusal, not a decoder verdict. No gauge, quality or SOTA conclusion follows.

One parent and one worker use the held native parent's standard-library
file/budget functions and repaired bounded-process helper by exact source hash.
The exact release contains full source and input FileRefs, actual failed-native
evidence and runtime plus adjacent DLL pins, the complete literal parent/worker
argument arrays and carried work. Both process paths check their actual argv.
The worker imports NumPy/rawpy only after verifying runtime dependencies, sets
four numerical thread variables to2, and checks versions. Interpreter and
imported module paths are matched to the captured FileRefs. Dependency/source,
primary and retained snapshot bytes are checked again at completion.

Native1's complete measured CPU34.984375 and conservative wall29.3349305
(capture prior1.7583753 plus actual native outer27.5765552) are carried without
reset. Its file238504151 and metadata1675100 extents remain charged; add a
prospective1MiB file/metadata reserve for native outer/review/release and probe
preparation metadata, checking the enumerated population fits before release.
The shared original1200CPU/1800wall/4GiB files/128MiB metadata limits remain.
The single worker gets at most30CPU/60wall/2GiB committed/1MiB log within the
remaining shared allowance. The parent enforces the shared limits across its
hashes and final writes; the worker's30/60 limits do not purport to cover parent
work. Candidate retained array is65,932,032 bytes, plus small row buffers and
column operations; Job committed memory is not RSS.

Fresh directory `active-domain-probe-1`, files worker.json/worker.log/result.json.
Each JSON write is bounded to4MiB; output extent remains in the shared budget.
The saved result samples work before final publication; actual stdout carries
the terminal work sample. Parent charges actual terminal Job CPU once, with
explicit unavailable total if terminal accounting is missing. Failed output and
first publication copies remain. A final post-flush budget check can still
revoke publication. Failure
persistence preserves the original error and records later failures separately,
with nonzero return even if a refused replacement cannot be saved. Root must
observe actual parent exit and final receipt as well as the result file; a
nonzero exit never admits a stale positive.
Status `COMPLETE_DIAGNOSTIC_ONLY` means the finite comparison ran, not that its
hashes necessarily agreed. Independent review must inspect both agreement fields
and the full mismatch list, not just this status. No script execution has yet
occurred at this preregistration.
