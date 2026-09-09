# Native sensor transfer: independent producer source review

SOURCE REVIEW, 2026-09-09. Initial disposition: **three corrections required
before source hold**. This reviews the unapplied producer against methodology
commit `a257cba972948564fd6041dc535d5e34f2ea6679`. It authorizes no build, test,
control, RAW read or numerical run. Root owns integration and release.

I recommended the RAW priority and contributed to the Crop/protocol choices,
as disclosed in `source-choice-review.md` and `protocol-choice-review.md`.
I did not author this adapter, hook or patch. This pass independently checked
orchestration and observation choices against the actual surrounding consumer
and writer source; it is not author self-verification or measured neutrality.

## Reviewed source and concrete corrections

All paths in this table are under `experiments/native-sensor-transfer/source/`.

| Source | Bytes | SHA256 |
| --- | ---: | --- |
| implementation-contract.md | 13483 | 09067540cd631bf1fbc91fe0ebfe1876da7b67c5894f9dd2a58846118fa9ad0c |
| native-adapter.rs | 23846 | 2cbc621f157622f9055167a2a5dd0894856c80a81da472eb3e1e96889db36af4 |
| core-hook.rs | 8092 | a2d71b5c79a1fd266bc6302b3975332cfeeb768d1d13d56536d75e89dededbed |
| native-observation.patch | 4907 | 2fda52067848153017fcb59e6b1bbb630b343ab5f1b76d96a90d7c727a77c553 |
| patch-construction.json | 3237 | 7d06c8a6ce2ae86db5a5a78e9d51d8e3cded865e6149248679020419312b6d24 |

1. **Hash-to-decode continuity.** `source_ref` checks the metadata surrounding
   its hash, but `run_pair` then establishes a fresh metadata baseline before
   decoding. A change between those two operations can associate an earlier
   hash with a later decode without the present length/mtime checks rejecting
   it. Return and retain the hashed baseline through decode and both route
   folds, checking it before decoding as well. This requires no extra decode
   or second source hash. Such metadata checks still are not a claim of an
   atomic snapshot or complete native-library identity.

2. **Map count meaning.** The final `map_callback_visits` value is computed
   from retained map records. The feature-on Off arm still reaches the actual
   callback, which returns before recording anything, yet reports zero visits.
   Name the field as retained records and label any expected callback count,
   or increment an actual visit counter. Preserve the distinction between
   actual On maps, constant Placebo metadata, Off early returns and absent
   feature-off calls. An actual map record proves the resolved seam was
   visited; it does not by itself count every pixel gather or establish an
   effective red/blue identity transform.

3. **Scalar operand provenance.** `band` observes the actual L/V/E/weight
   arrays, but recomputes `beta_for`, `cfg.exponent_at` and
   `significance_floor(gate)*scale` for its context. These context entries are
   source-derived evaluations from the actual configuration and supplied beta,
   not directly retained weight-closure locals. Either label that provenance
   explicitly in the producer/checker interface or, subject to root review,
   pass the existing production scalar locals without changing their
   arithmetic. A derived floor remains a derived floor in either case.

These were identified before any scientific execution. They are source and
evidence-association findings, not measured sensor defects. The producer and
root received them directly. No tolerance or scientific population was changed
to accommodate them.

## Independent consumer and observation assessment

The adapter uses the existing `BandWorker::fold`, `load_frame`, extraction,
variance construction, `BandMerge::add_frame_with_gain`, reduction and finish
methods. It implements paired orchestration rather than invoking the complete
public command. Comparing it with `run_pyramid_prepared` confirms that planning
uses the full native geometry, `canonical_band_chunks`, ceiling division for
the frame chunks and left-to-right `absorb`. It preserves reset boundaries
inside each route. Interleaving the two routes does not replace their canonical
reduction with one sequential accumulator. It is nevertheless a fixed Crop
consumer experiment, not certification of every public-command branch.

The first decoded frame supplies metadata/model/planning and remains the first
consumed frame. Each original is cloned once for no-map, then moved into the
placed route. `OneFrameSource` checks the requested index and takes its sole
frame once; the caller checks successful fold and empty handoff. The successful
loop's 50 decoded originals and 100 folds are supported by those checks. Counts
on a failed traversal must instead come from retained visited records and raw
terminal evidence; the final success formula cannot be applied to an incomplete
prefix. Existing full-frame synthetic probe and memoized compact BandGain work
remain separate work, as the contract records.

The fullres callback is at the existing resolved `t_site`, after the actual
gear/profile/WB resolution. It records that value without relookup. The fixed
real/probe and CFA-site order is checked at the callback. The prepared ROI is
borrowed after the actual real/probe work and before extraction; the original
ROI is saved before either route mutates its own frame. The original active
area and buffer dimensions are checked rather than scoring synthetic padding.
No-map and placed geometric identity remain distinct routes. Native MHC/WB/CA
and u16 roundtrip remain in the placed path.

Core observations are after the existing weight computation and before
accumulation. Plane coefficient reads follow production's existing cache
preparation; the observer does not prepare another pyramid. Luma, variance,
energy, weights, base weights and all four plane pyramids are actual arrays.
The injected variance is hashed before and after consumption. The base is
explicitly BaseMean, without a fictitious fifth gate. Actual empty versus
three-entry beta prefixes and white fallback remain distinguishable. The k3
probe is not attempted by the existing three-band cap; it is not an observed
MIN_SAMPLES rejection.

The alternative to trusting apparent passivity is already fixed: compare
complete collapsed f32 and native TIFF bytes within paper5 and dark2
off/on/placebo and feature-off witnesses. Optional Placebo arrays use constants.
Mandatory input hashes still read actual arrays in all feature-on arms;
therefore "placebo never reads merge state" would be too broad. Feature-off
output comparison is the witness for that shared diagnostic work. No claim of
whole-22-dark observer neutrality follows from the first-two-dark witnesses.

## Native writer, bounds and failure meaning

The adapter passes the completed compact planes to existing `write_merged`
with first-frame levels and actual WB, CameraLinear, demosaic enabled,
Exposure::None and no restoration. That writer addresses compact Crop planes
directly; it does not apply the full-domain crop twice. CameraLinear selects
neither matrix nor transfer curve, while the native demosaic remains active.
The separate prewriter payload retains all four collapsed planes, so writer
clipping or quantization cannot hide their disagreement. Whole-TIFF comparison
tests this writer path but supplies no independent photographic truth.

The fixed normal trace has 46 core fields and six input arrays. The source
array count plus scalar contexts and field framing fits below the 2 MiB trace
cap, with prepared ROI separately capped at 128 KiB. The fixed frame JSON
contains 256 row hashes and at most eight map records; these fixed paths and
metadata have substantial room under 64 KiB. These are source shape checks,
not executed serialization measurements. Variable refusal strings and runtime
metadata remain subject to publication refusal rather than a promise that all
possible errors fit.

`write_new` caps bytes before its create-only staged write, flushes/syncs, then
publishes by hard link. Its returned hash describes the supplied buffer; a
later saved-artifact verifier must authenticate actual published bytes. The
unchanged native TIFF writer runs before the adapter's 512 KiB extent check.
That check is a postwriter bound, not an online bounded writer. Root's released
owned-process/storage accounting must cover the actual stage and failure
prefix. The proposed memory envelope is a component sum, not a measured peak
or evidence that an arbitrary fixed memory limit is sufficient.

Initial incomplete.json precedes `run_pair`; ordinary returned errors attempt
failure.json and then panic. Assertions, poisoned locks, or publication panics
can leave only that initial receipt, previously published frame rows, stages
and the raw test terminal. failure.json is not guaranteed. No missing final
record means zero work; decode/fold attempts beyond the last published record
remain unknown. Preserve those files and actual process disposition. A fresh
path, successful return and terminal result are all still necessary; none of
them alone constitutes scientific admission.

## Scope and remaining hold

The actual original consumer, writer, owned Frame helpers and the full candidate
hook/adapter/patch were read. Patch construction is the author's retained
source claim; I did not apply it or independently execute its reversal.
Root's applied-source association and reverse proof remain required separately.
No RAW, image, simulation, test, build, candidate import or control ran here.
I authored only this review and sent source feedback; original crates and
methodology stayed unchanged.

The source preparation grant remains 64 MiB reads, 4 MiB new retention,
60 CPU seconds and 120 active process-wall seconds, without refund. Reads
and navigation were not instrumented as one complete process family; exact
cumulative CPU is unknown. A missing owned-source navigation path, a rejected
PowerShell pipeline syntax, and restricted-language metadata formatting errors
were tooling failures, not producer outcomes. Subsequent plain file metadata
reads supplied the pins above. No failed tooling attempt was counted as a
successful check or used to renew the allocation.

After the three corrections are reread and pinned, this can admit the producer
to root's integration/source-freeze work. Build freshness, source/binary/input
association, independent checker/control power, actual output neutrality and
finite owned execution are still unvisited requirements. This review establishes
no sensor-model agreement, stationarity, real placement accuracy, restored
historical M1/M2 evidence, photographic quality improvement or SOTA result.

## Corrected source disposition, 2026-09-09

**SOURCE-REVIEW CLEAR FOR ROOT'S INTEGRATION AND FREEZE WORK.** The initial
review above remains the record of the first candidate and its three findings.
This addendum supersedes its pending disposition for the exact corrected
sources below. The producer preserved the original candidate at
`51281d201be2c2a6a46e45d3c5b4afcad49dd678`. No scientific population,
methodology, tolerance or numerical kernel was changed to resolve the findings.

| Corrected source, under source/ | Bytes | SHA256 |
| --- | ---: | --- |
| implementation-contract.md | 15195 | 9328c626a7ec32b30cce2cc717ff158cefb59b64088e3eeb724669bb7010cc60 |
| native-adapter.rs | 24251 | fa96ad627f5d20321467a9a3b5343a495a23f8a965e165555f5285a1734aa884 |
| core-hook.rs | 8340 | 18443498ca68208067cf1440386b35981836b1352aca864761cf32974b4023eb |
| native-observation.patch, unchanged | 4907 | 2fda52067848153017fcb59e6b1bbb630b343ab5f1b76d96a90d7c727a77c553 |

I read the complete textual diff and the relevant final call sites, then
independently read file extents and hashes. `source_ref` now returns both its
FileRef and the same checked hash-time Metadata. `run_pair` checks that baseline
immediately before decoding, after decoding, and after both route folds.
The fresh predecode baseline is gone. This closes the reported association gap
within the stated length/mtime continuity model; it does not claim an atomic
snapshot or detection of every same-metadata replacement.

`retained_map_record_count` names the actual retained On/Placebo population
checked at each completed frame. `expected_map_callback_visits` correctly
includes feature-on Off's early-return callbacks, while an adjacent scope
string explicitly says calls were not individually counted. Neither field
turns the complete-traversal expectation into a measured pixel/warp count.

Frame records now state
`scalar_context_provenance=DERIVED_FROM_ACTUAL_CONFIG_AND_PREFIX`. The hook
change consists only of provenance comments; selected beta, effective exponent
and significance remain derived evaluations, and actual L/V/E/weight/config/
prefix observations retain their separate meaning. Root chose this labeling
correction instead of another hook. The trace layout, numerical expressions
and actual patch bytes are unchanged. The independent saved reader must retain
this distinction when using those values to reconstruct the weight relation.

The contract now explicitly preserves both remaining publication limits:
the TIFF extent check occurs after the unchanged writer, and failure.json is
not guaranteed for assertions or publication panics. Initial/partial files and
the actual raw terminal remain authoritative for failure interpretation;
unpublished attempted counts remain unknown. No broader process framework was
introduced to resolve these source findings.

This delta pass used the separately commissioned source-review-stage grant of
64 MiB reads, 4 MiB retention, 60 CPU seconds and 120 active process-wall
seconds. It consisted of source navigation, diff/read/hash inspection and this
append-only review publication; no candidate or scientific process ran. It
does not reset or refund the earlier review lane. Complete cumulative CPU was
not measured and is not manufactured from individual tool response times.
The numerical release, source application/reversal proof, actual build and
independent execution/control results remain root-owned future requirements.
