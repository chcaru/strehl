# M193b — strict geometry consumer and bounded input construction

**Disposition: prospective denominator-integrity repair; native coverage and
real adapter geometry remain open.** The frozen M193 fixture keeps its original
identity PASS and cropped FAIL. The prospective consumer rejects both the
stale-hash denominator attack and the same attack with a recomputed self-hash
and rebound output descriptor.

This continuation was allocated in the AGENTS ledger before implementation. It
changes only `experiments/m193b-geometry-consumer/` and this report. Frozen M193,
including its pre-existing dirty contract amendment, is preserved. It does not
change product code, compare renderers, consume RAW or holdouts, or close a
scorecard item. No SYNTHESIS fold is proposed from an uncommitted report.

## Prior evidence and falsifiers

Read before implementation: `SYNTHESIS.md` architectural decisions and rule 6's
single-reference limitation; `M193-geometry-review.md` and its
`experiments/review-m193-geometry/challenge.py`; frozen
`experiments/M193-cover-overlap/reference.py`, `fixtures.json`, `contract-v1.json`;
`M164-dominance-manifest.md` external provenance binding; and
`M-COVER-NATIVE.md` separation of output sampling from common field of view.

`experiments/m193b-geometry-consumer/preregister.md` was written before
`consumer.py`. It names live pass/fail fixtures, stale and rehashed attacks,
strict schema/type/geometry refusals, duplicate/order/content controls,
one-frame decode retention, and complementary-focus refusal. Field-of-view
retention can be made falsely favourable by shrinking its denominator or lying
about output mapping. This repair targets the former and validates the latter's
structure; it does not authenticate an adapter's assertion.

## Authority and validation

`consumer.py::construct_overlap_paths(paths)` is the trusted registrar. The
trusted runner selects the input paths and receives `(manifest, binding)`;
`TrustedInputBinding` stores immutable canonical manifest bytes and can only be
created through this successful registrar path. Its public constructor rejects
calls. There is no public constructor accepting a candidate manifest or digest.

Every prospective geometry consumer (`validate_overlap`,
`validate_output_grid`, `output_retention`) requires this binding. It first
compares the candidate manifest's canonical bytes with the registrar's bytes,
then works on a detached snapshot. A candidate cannot redefine the denominator
by recomputing its own self-hash or rebinding a descriptor to that self-hash.

The trusted boundary is the runner's input selection, registrar execution, and
retained binding object. The candidate may supply JSON manifests/descriptors;
it may not replace trusted runner state. This is not a sandbox against arbitrary
Python execution, monkeypatching the registrar, a dishonest registrar, SHA-256
collisions, or malicious concurrent file writers. The forced hash-collision
comparison control tests compatibility of ordering, not cryptographic security.

`strict_json_loads` rejects duplicate keys, nonfinite values and noncanonical
numeric types. `_validate_manifest_structure` checks exact schema and fields,
fixed construction rules, SHA-256 syntax and self-hash, integer types excluding
booleans/floats, dimensions, multiplicities, source order, reference identity,
nonsingular Q32 transforms, registration split/count/consensus constraints,
held-out RMS representation/bar, source/reference gauge consistency of RMS and
maximum residual, uncertainty-to-support conversion, bounds and area. It then
replays the input-support intersection and deterministic maximal rectangle.

`_validate_grid` checks exact fields, string fields, hashes, genuine integer
dimensions/guards/residuals/transforms, nonempty support, and the unchanged v1
scale/rotation/residual bars. Only validated snapshots reach v1's retention
counter. Descriptor adapter/settings hashes remain syntactic identifiers; their
existence and mapping truth require separately commissioned real adapters.

## Bounded path constructor

**DERIVED from `construct_overlap_paths`, `_scan`, `_copy_checked`,
`_compare_files`, and `decode_input_path`:** source hashing uses 1 MiB chunks.
The sorted input multiset retains v1's exact `(digest bytes, byte length,
exact bytes)` ordering, duplicate multiplicity and bundle byte format. Equal
digest/length entries use streaming exact-byte comparison, rather than treating
a hash as proof of byte equality. Byte-distinct TIFFs with identical pixels
remain distinct inputs. Uncompressed, single-page, orientation-1 RGB16 is still
the admitted input format.

One input at a time is copied into a file-backed temporary snapshot while its
length and hash are rechecked. TIFF decode reads that verified snapshot, then
the decoded array is released after feature extraction/registration. Retained
image storage is bounded in N: one decoded frame, the reference feature set,
and the current feature set; feature limits remain v1's. Registration scratch
storage still scales with image dimensions. Paths, metadata, source rows,
support transforms, and the binding scale in N. A temporary file can hold one
source TIFF; this is a memory bound, not a claim of zero I/O or bounded disk
independent of image size. Intersection rows scale in image height and the
unchanged maximal-rectangle routine has quadratic height work.

Successful manifests keep `strehl.m193-cover-overlap.v1` and the frozen semantic
strings because their serialization and geometry are unchanged on supported
fixtures. The consumer implementation is prospective. Invalid-input refusal
precedence can change because decoding and registration now happen sequentially;
additional structural consistency checks may refuse results the old consumer
never checked. This does not widen the admitted TIFF format or repair fixed-
reference coverage.

## Author regressions

Command run, exit 0:

```powershell
python -X faulthandler experiments/m193b-geometry-consumer/author-checks.py
```

**MEASURED, author regression only:** nine recorded checks in
`author-results.json`. These are not independent verification.

| Input/control | Frozen v1 | Prospective consumer |
|---|---|---|
| Same-focus manifest | digest `a1cdb836fb8806398a0c5031bdff5844b63888376542d5cc78b37d0149c77265` | exact full manifest equality |
| Identity grid | 99,918 / 99,918 PASS | same |
| Original cropped grid | 97,188 / 99,918 FAIL | same |
| Stale-hash 20-by-20 denominator | 400 / 400 PASS | refuses before counting |
| Rehashed 20-by-20 denominator, descriptor rebound | 400 / 400 PASS | refuses before counting |
| Smaller rectangle through private structural checker | not checked | maximal-rectangle replay refuses |
| Mutating returned validated snapshot | not checked | original binding and later snapshot unchanged |
| Equal digest/length, different exact bytes | exact-byte tiebreak defined | both comparison directions and equality tested |
| Source changed after initial scan | not a path API | refuses before decode under stale binding |

The old consumer is the negative control for the two denominator attacks. The
original crop is an actual failing input; the identity grid is a passing input.
These are deterministic counts and refusals, not estimated ratios with sampling
standard errors. The author harness's first run failed because it looked up the
nonexistent result key `verdict` instead of `field_of_view_verdict`. Correcting
that harness key and rerunning produced the recorded result; no consumer change
was needed for that failure.

## Independent verification

**VERIFIED by the separate `roadmap_audit` reviewer:** the final independent
suite exits **0**, with **46 named refusals** and the positive controls retained.
The cases were written before inspecting `consumer.py`; the required external
input binding and API were communicated to the author before implementation.

Exact command, run from the repository root (about 6.9 seconds):

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B experiments/m193b-geometry-consumer/independent-verify.py
```

[`independent-verification.json`](../../experiments/m193b-geometry-consumer/independent-verification.json)
retains every rejection code, control result, and source hash. The checked
consumer hash is
`41e087797866505cc30384888ed83cd7a94dbcd7b757054433186003b37d2b26`;
the independent script hash is
`bbf25cd571a33d4987141032c18105c8a4baf6106bd8eb06365a7580d7b9e0a7`.
The consumer and three frozen v1 artifacts are hash-identical before/after
this invocation. The review's initial literal source-hash assertion contained
one extra character; correcting that reviewer typo allowed execution. No
consumer repair was needed for it.

The original manifest is reproduced exactly; identity remains
99,918/99,918 PASS and crop remains 97,188/99,918 FAIL. The same stale smaller
rectangle still fools frozen v1 into 400/400 PASS, establishing power on the
original failing path. The prospective consumer refuses it. It also refuses
rehashed in-bounds shrinkage and jointly changed transforms, uncertainty and
maximal rectangle, with the descriptor rebound to the new digest. The joint
mutation's rectangle is independently recomputed from its altered supports;
this is not merely an inconsistent area or a stale checksum. The original
input-constructor binding is retained throughout these attacks.

Other refusals cover foreign bundle/reference/content/multiplicity, absent or
dictionary-shaped trust, wrong schemas and fields, malformed bounds/counts,
bool/float integer impostors, malformed descriptor types, singular mapping,
negative residual, duplicate-key/truncated/nonfinite/invalid-UTF-8 JSON, and
unsupported compressed TIFFs. A returned validated snapshot can be mutated
without changing the original manifest or later validation. Reordered inputs
produce the identical manifest. Duplicate paths and a distinct path with
identical bytes preserve multiplicity; a one-pixel change produces a different
input binding and reference hash.

The independently seeded feature stimulus uses a **328x232** texture and an
origin-based similarity with scale 1.007, rotation -0.18 degrees, and translation
(-2.75, 1.625) pixels. It differs from v1's texture, aspect ratio, transform and
centre of rotation. Its admitted overlap is **73,644 sites**, and registration
finds 256 matches with held-out RMS **0.128567234 reference pixels**. Both its
overlap and the frozen overlap are checked by explicit integer inverse-support
membership followed by a histogram-stack rectangle algorithm, independently of
v1's row-interval and top/bottom search. Output retention is checked by directly
enumerating mapped lattice sites, including a fractional output translation;
the alternate identity passes and its cropped translated output fails.

The prior complementary-focus challenge still refuses in both constructors
with `UNMEASURED_INPUT_REGISTRATION_INADEQUATE`. Its same-focus feature control
has 256 matches and exactly 0 RMS. This preserves a known refusal; it supplies
no deep-stack coverage claim.

**MEASURED decoded-array lifetimes:** twelve uncompressed 208x144 RGB16 TIFFs
have identical decoded pixels and distinct metadata/byte hashes. Weakrefs wrap
the actual decode functions. Only registration/feature work is stubbed equally
in both constructor loops to isolate retention; the real feature test above is
separate. Both arms produce the same full manifest.

| Arm | Peak live decoded arrays | Their payload bytes | Live arrays after return |
|---|---:|---:|---:|
| Frozen v1 | 12 | 2,156,544 | 0 |
| Prospective path constructor | 1 | 179,712 | 0 |

The assertion requires **exactly one** prospective decoded array at peak. These
are deterministic observed lifetimes on a small synthetic input set, not
process RSS, a native-size memory benchmark, or evidence about SIFT accuracy.
Source inspection separately confirms streamed source-byte reads and the
file-backed single-input snapshot. No threshold, frozen algorithm, product
code, corpus file, scorecard, or SYNTHESIS entry was changed by the reviewer.

The independent disposition is **accept this scoped consumer repair and bounded
decode implementation**. A well-formed false output-map assertion remains
possible without a commissioned adapter; that explicit boundary prevents
promoting these fixture results to native geometry or blocker closure.

## Preservation and remaining work

Author regression hashes before/after were identical:

| Frozen file | SHA-256 |
|---|---|
| `reference.py` | `c08340f6f0658fae048dda92629a543b5a539462a93db196aaae29e1862ba790` |
| `fixtures.json` | `8f5ebcba9688f0d08e71d74f1e8c881702c932ba7d3386e1f9131ffa882ac693` |
| `contract-v1.json` including existing dirty amendment | `19421729ac39273a5f61cda5068026f3458ba08c98f0aa954de7c219cbfabf47` |

The next geometry work remains commissioned adapters that establish the actual
pre-output grid and check actual output dimensions, plus an input-only geometry
method that can place a deep focus sweep without chaining. This module does not
establish either result. No blocker removal or dominance/quality/performance
claim follows from these fixture tests.

Applicable-rule execution: preregistration and negative controls discharge
rules 11/20/35/36; the separate verifier addresses 12/24; exact frozen fixture
comparison and recorded commands address 8; hash preservation addresses the
frozen-input scope; one-frame decode lifetime is separately measured rather
than inferred from peak RSS. No sharpness/noise statistic, parameter sweep,
RAW decode, product observer, corpus write, process termination, SYNTHESIS fold,
or commit occurs in this continuation.
