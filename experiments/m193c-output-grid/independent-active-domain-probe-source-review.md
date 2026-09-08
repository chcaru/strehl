# Independent source review: retained-snapshot active-domain probe

Status: **source review complete; no remaining blocking defect identified in
the bounded diagnostic.** No probe/decoder import, RAW/TIFF read, image
computation, process launch or build was performed by this review. The actual
probe outcome is unknown. Native1's first-frame refusal remains unchanged.

Final reviewed files:

- `active-domain-probe.py`: 13,219 bytes, SHA-256
  `db541d3f826da7d32617002a90ed48d8c3cf2bb401f09b18331be67b6807086b`.
- `active-domain-probe-preregister.md`: 5,627 bytes, SHA-256
  `783df10b5e2108f9466ca5a81924c02e50298bd5dff8c6d9738a2229bae69563`.

I read both initial held files in full, the repaired boundaries, the borrowed
native file/budget/process interfaces, captured runtime metadata, and the
actual primary receipt's domain/hash field definitions. Both final file hashes
were checked. Only metadata and permitted project source were read; no decoder
implementation or forbidden licensed source was consulted.

## Question and actual data path

The inspected primary receipt is `native-derivative-1/frame-00/native/result.json`,
350,873 bytes, SHA-256
`e02482a38f3f15a2cc89ee83a809fdbdc590568db8a439754e956f20f8251427`.
It records selected original0, the explicit rectangle x0/y0/7032x4688,
one whole-active-u16 hash, and 4,688 row hashes. Its snapshot reference names
the retained first snapshot. The future external release must bind these
actual records and snapshot, not select another original or comparison result.

The probe uses that one saved snapshot through an in-memory byte buffer whose
SHA/extent are checked before decoding. It checks the independently observed
full and visible dimensions and origin before copying `raw_image[:4688,:7032]`
inside the RawPy context. The resulting C-order array must own its 65,932,032
bytes. The raw view and visible view are consumed/deleted before close;
post-close hashing uses the owned copy. This addresses the lifetime distinction
in rule32 without replacing the declared domain with the visible viewport.

All 4,688 candidate rows are hashed as little-endian u16, and every mismatch
against the saved primary rows is retained. The whole-domain comparison is
recorded independently of the completion status. Within the live context,
the actual visible view and the candidate's common 7028-column subset are
hashed separately and required to agree. This powers a correspondence check
between views, not a claim that the disputed four columns are invalid.

Statistics are restricted to columns7028 through7031 inside the explicitly
declared candidate domain: count, zero count, minimum, maximum and per-column
hash. No statistics are taken over the full allocated buffer or other padding.
There is no demosaic, postprocess, resize, second snapshot or output TIFF path.
The full allocated shape is checked only as geometry needed to bound the ROI.

The fixed XOR-one-code change at row2344/column7029 must change the actual row
digest, and restoration must recover its original digest. It does not rely
on agreement with the primary to be live. This is a deliberately small hash
instrument control; it is not a pixel-origin, physical-sensor, optical or
photographic-crop calibration.

`COMPLETE_DIAGNOSTIC_ONLY` permits whole-domain/row mismatch. Consequently an
actual read must inspect the agreement flag and full mismatch list, rather
than interpret completion as agreement. Even complete agreement would establish
decoder byte agreement on this one explicitly declared domain, while preserving
the original visible-domain difference. It cannot itself admit the native
derivative, qualify a common-TIFF route, or settle physical photosite validity.

## Initial findings and repaired source

The first held source was 11,103 bytes,
`1b2ff92cae904908863a5a6b0c2210fdcf7cbb1040ef76eaa23fa10ac63921f9`;
its specification was 5,334 bytes,
`5a680116d07a539b6e08b0b6cd33ac61910ed764ddc5b5b765302517c28b44a8`.
The following findings were resolved before execution:

- Recorded runtime bytes and version strings alone did not associate the
  actual imports. Root independently identified this too. The final worker
  additionally checks actual `sys.executable` and the resolved `__file__`
  paths for NumPy, its core extension, rawpy and its extension against the
  recorded FileRefs, and rehashes those files. Captured adjacent DLL files
  are checked as byte dependencies. This is not full interpreter hermeticity
  or proof of every loaded shared library.
- The release bootstrap allocated an unrestricted `read_bytes` result before
  checking its cap. It now reads at most MiB+1 and refuses at the declared
  bound before parsing/importing its helper.
- Terminal accounting completeness was assigned after a budget call that
  could already raise. It is now derived from typed terminal Job accounting
  before charging child CPU, so a resource refusal does not erase available
  accounting evidence. Missing complete accounting remains explicitly unknown.
- The final stdout write had no following budget check. It now has a
  post-flush check that revokes completion and returns nonzero on failure.
- Refusal rename/write operations could throw away the original failure.
  The final source preserves the original error, records secondary failures,
  retains bounded first-publication names when possible and returns nonzero
  even if a negative replacement cannot be persisted. The actual exit remains
  necessary; a leftover positive receipt after failed I/O is not admission.

The inspected changes do not alter ROI bounds, decoding, hash arithmetic,
mutation position, disputed-column population or interpretation.

## Bounds and final record meaning

The borrowed native Budget and Files implementations remain pinned. Parent
and child enforce the exact released original argv. NumPy-family thread
environment values are set to2 before the first numerical import. Input,
runtime and source files are rechecked before completion; the saved result
is itself rehashed on the successful publication path.

The fixed one-worker Job is capped at 30 CPU/60 wall seconds, 2 GiB committed
memory and 1 MiB log, further constrained by the carried real-stage balance.
The parent adds the actual terminal Job CPU once and enforces the unchanged
1200 CPU/1800 wall seconds, 4 GiB file and 128 MiB metadata stage totals.
The worker's smaller ceiling does not purport to cover parent source hashing
or publication work. The candidate-array byte count is explicit; Job committed
memory is the actual process-tree limit, not an RSS or Python-only claim.

Prior native/capture work and the additional preparation-metadata reservation
are inputs to the prospective release. Their literal association and byte
fit are the separate metadata preparer's responsibility. They are not reset
because the scientific observation refused. The native1 result and its
unvisited later inputs must remain preserved.

The saved result work is a prepublication observation. The stdout sample
includes successful result persistence/rechecks; its subsequent budget check
and root's actual exit/outer observation close the terminal boundary. Failed
publication may consume additional retained bytes and has no successful-total
claim. No runtime speed, geometry accuracy, quality or calibration conclusion
is supplied by this source review.
