# Native sensor reader: explicit camera-channel white authority

Status: **SOURCE PREPARATION ONLY; UNEXECUTED.** This successor changes one
native metadata authority after an observed refusal. Root must freeze/review
these sources and exact commands before any helper control or RAW read. It
does not admit the failed attempt or change its retained files.

## Observation and source basis

The historical `native-sensor-derivative-1` parent is REFUSED. Its result SHA256
is `00ae754f28277c69196a55da5fff88c8c807de17f6c48123d73c8b3ee1a6eadb`;
the original0 independent result is
`58f4a7208a12a5a17913f1c048a54d106faa9a40e0ee3c849c83cbc71c962db7`.
That reader passed eight domain controls and its first five native checks,
including the full active u16 hash and all 4,688 row hashes. It then refused
with `ValueError: scalar white disagrees`. Retained metadata has generic white
16,383 and camera whites `[15360,15360,15360,15360]`; the primary scalar is
15,360. The remaining eight real inputs were unvisited. This is a scoped
metadata/source read, not a fresh decode or confirmation of the remaining checks.

Official public API consulted on 2026-09-07:
[rawpy RawPy documentation](https://letmaik.github.io/rawpy/api/rawpy.RawPy.html#rawpy.RawPy.camera_white_level_per_channel).
The page identifies camera-channel white as saturation metadata from the RAW,
represented by four integers or `None` when unavailable. It separately defines
generic `white_level` as a saturation level. The public descriptions do not
specify precedence between these properties, a zero sentinel in a present camera
list, a scalar reduction for differing channels, or physical calibration.
The retrieved page labels itself 0.27.1; the actual held execution runtime is
0.27.0 and remains pinned. Documentation research does not substitute a runtime.

Owned primary code `crates/strehl-raw/src/lib.rs:305–311` selects its first
resolved black/white entry, with white defaulting to u16 maximum when absent;
white is stored as f32. Its SHA256 is
`1513fd3e682f2edb8c54c7d47083f20f66525ad72a5687fb2e530bb5697fef2a`.
The owned `registration-derivative.rs:456–508` consumes that scalar in
`((sample-black)*(1.0f32/(white-black)))*green-normalized-as-shot-gain`, recording
white and its f32 bits. Its SHA256 is
`db2a4d0c36d3f0778481e8a9837feef1c2651258865799bbd143b6bb0840eecd`.
Neither source proves the primary metadata was present. No rawler, LibRaw,
GPL implementation, tag table, or external decoder implementation was opened.

The explicit comparison policy below is a **prospective method choice**, not a
claim that the API prescribes a universal precedence or that 16,383 is a
bit-depth ceiling. It compares the primary scalar against independently exposed
camera metadata, without choosing whichever rawpy value matches the primary.

## Successor scope and method

New complete source copies only:

- `independent-sensor-white-derivative-read.py`, derived from held
  `independent-sensor-derivative-read.py` SHA
  `eeed1ea3c45927f81e34d99ca31dc57715f898b718dfef26dcf0ea2cddf3fbe7`.
- `native-sensor-white-derivative-run.py`, derived from held
  `native-sensor-derivative-run.py` SHA
  `10ec80290bc7bb5c2e7fc140cb831d539e517844281b40b372055b409113a1ed`.
- This additional specification. The held sensor-domain and original native
  specifications still bind unchanged behavior.

`native_white_authority(metadata, source)` implements
`m193c-camera-channel-white-v1`:

1. Require exactly four true integer CFA indices, each in `[0,3]`; derive the
   sorted used-index set from actual source-origin CFA queries.
2. Retain generic white, requiring a true integer in `[1,65535]`. It is not the
   selected authority, is not required to match camera white, and cannot rescue
   absent, malformed, mixed, or disagreeing camera values.
3. Require camera metadata to be a list of exactly four true integers, each in
   `[1,65535]`. `None`, missing list extent, null/zero entries, bools, floats,
   negative and out-of-container values refuse. No absent-metadata fallback is
   implemented for this fixed nine-file population.
4. Every used channel must have the same value. Select that common value;
   require exact equality with `source.white`. No averaging, minimum, first
   matching channel, tolerance, clipping, or generic/camera either-match test.
   An unused entry, if any in another supported local RGGB mapping, must still
   be a valid integer but is not a scalar authority. This actual population uses
   all four indices, so all four values must agree here.
5. Return an explicit witness while leaving source and metadata unchanged.

The witness has exactly these eleven keys:
`method`, `generic_white`, `camera_white`, `used_cfa_indices`, `selected_white`,
`primary_white`, `generic_matches_selected`, `selection`, `fallback`,
`physical_calibration_claim`, `primary_metadata_presence_claim`.
`method` is the ID above; `selection` is
`equal-positive-used-camera-channels`; `fallback` is `forbidden`; both claim
booleans are false. The generic-match boolean records the actual equality,
without making either direction a success condition.

`validate_native_metadata` uses this helper and copies the old black and WB
checks exactly: primary positive range; exact black equality at each used
channel; actual R/G1/B coefficients normalized by local G1; the unchanged
`2**-20 * max(1,abs(target))` WB comparison. Its returned agreement adds
`white_authority`; the original metadata is retained in native check1 as before.
Acquisition retains the public properties without `int()` or `list()` coercions
that could conceal malformed types. Native check6 is renamed truthfully
`scalar-black-camera-white`. The other ten native checks are unchanged.

The old `validate_independent_metadata`, private branch, its 41 controls,
runtime capture/load, domain helper/eight controls, owned-buffer lifetime,
source origin, exact full and per-row hashes, black/WB arithmetic, all TIFF
parser/pixel/description checks and actual source/runtime rechecks are preserved.
The new native helper is not inserted into the private branch. There is no Rust
edit, build, private-image repetition, physical photosite/calibration claim, or
change to the product normalization.

## Literal controls before RAW access

Ten ordered groups run through the actual `validate_native_metadata` consumer
after the existing domain controls and before opening the snapshot/RAW. They
make 23 scalar metadata calls and no random, decoder, image, or pixel calls.
They share the same live reader budget; no budget is reset. The baseline is
independently re-chosen, not the failed real frame's constants:

```
indices=[0,1,3,2]; letters=[R,G,G,B]
black=[64,64,64,64]; generic_white=16383
camera_white=[12000,12000,12000,12000]; wb=[3,2,5,2]
primary: black=64, white=12000, wb_rgb=[1.5,1,2.5]
```

All mutations start from a new copy of that baseline. The actual consumer must
leave both its source and metadata unchanged on success and refusal. A normal
return on an expected refusal fails outside the exception handler; the exact
ValueError message must match, so an unrelated refusal is not success.

| Ordered ID | Literal intervention and required observation |
| --- | --- |
| `camera-white-authority` | Baseline succeeds with exact independently specified full authority witness, generic-match false and normalized WB `[1.5,1,2.5]`. Requiring generic equality fails this positive. |
| `global-match-wrong-camera-refused` | Set generic to12000 (exact primary) and all camera entries to11000. Must refuse `selected camera white disagrees with primary`; generic fallback or either-match would falsely pass. |
| `mixed-used-camera-white-refused` | Camera `[12000,12000,12000,12001]`; must refuse `mixed used-channel camera white`. A first/minimum/any-match reduction is insufficient. |
| `absent-camera-white-refused` | Camera `None`; exact `camera white metadata required; no generic fallback`. |
| `malformed-camera-white-refused` | Eight attempts: length3 and string `12000` refuse `camera white four-entry list`; final entry respectively `None,0,-1,true,12000.0,65536` refuses `camera white positive integer entries`. Other entries12000. |
| `malformed-global-white-refused` | Five attempts: generic `None,true,16383.0,0,65536`; each refuses `generic white integer range`. Present valid camera data does not hide malformed retained metadata. |
| `malformed-cfa-index-refused` | Three attempts: indices `[0,1,3]`, `[0,1,3,4]`, `[0,1,3,true]`; each refuses `camera white CFA indices`. |
| `native-black-regression-refused` | Black `[64,64,65,64]`; exact `used-channel black disagrees`. |
| `native-wb-regression-refused` | WB `[3,2,6,2]`; exact `green-normalized WB disagrees`. |
| `camera-white-restored` | Fresh unmodified baseline returns the same exact authority and WB witness. |

Each group has closed `{id,pass,evidence}`; malformed groups retain ordered
`attempts`. Each refused attempt records input/source, exact exception and
expected string, and input-preservation evidence. These controls do not prove
physical correctness of the RAW's metadata; they can reject the named wrong
selection, scalarization, type, and regression paths. If any control fails, no
RAW read follows and the first failure remains in the result.

## Exact interface delta

Only native identities change; private and runtime schemas are unchanged.

| Object | Schema / success or scope |
| --- | --- |
| Release | `m193c-sensor-white-native-derivative-release-v1`; scope `sensor-white-native-nine` |
| Request | `m193c-sensor-white-native-derivative-read-request-v1` |
| Per-frame reader result | `m193c-sensor-white-native-derivative-independent-frame-v1`; `PASS_SENSOR_WHITE_NATIVE_DERIVATIVE_FRAME_ONLY` |
| Parent result | `m193c-sensor-white-native-derivative-run-v1`; `COMPLETE_NINE_SENSOR_WHITE_DERIVATIVES_AWAITING_COVERAGE` |

The reader result retains the sensor result's exact fields and adds
`white_controls` (the ten IDs above, all literal true required). It contains
the same eleven ordered native `checks` except check6's new ID, and the same
eight ordered `domain_controls`. Its `checks[5].evidence` is
`{black,white,used_cfa_indices,normalized_wb,camera_white_availability,
metadata_presence_claim,white_authority}`. Other evidence and typed invocation
fields remain unchanged. Refused results retain any completed prefix and error;
they need not fabricate a full check/control population.

Release/request/parent key sets are unchanged from the sensor version. The
parent binds the new exact reader filename, new schemas/status and exact 11/8/10
populations. Both successor sources require this spec in released bindings;
the reader also persists it alongside its source snapshot. Root's source map
and released inputs must preserve prior failed source closures/receipts, current
copied build, actual runtime capture/six module pins and adjacent DLL endpoint
supplement. No held source is overwritten or relabeled.

## Execution, reuse and unchanged limits

No command is authorized by this file. Root will create and externally pin an
execution release after independent source review. Parent argv retains the
existing absolute Python path, `-B -X faulthandler -X pycache_prefix=<fresh>`,
new parent script, `--release`, actual external release SHA and new output.
Each of nine reader argv arrays retains the same flags and per-frame paths,
substituting only the new reader script and literal request-SHA placeholder.
The actual `sys.orig_argv`, runtime and input/source closure remain checked.

Original0 still reuses the successful primary receipt, TIFF, snapshot and child
launch from the *original* `native-derivative-1`, after complete fresh-nine plan
byte/content equality. It does not reuse either failed independent read. The
new sensor attempt created no additional primary image. There is no new resume
engine: the inherited original0 branch, its three full-plan controls, old-path
environment checks and no-unlink behavior remain unchanged. A complete new
attempt would use one historical primary plus eight new primary TIFFs and nine
fresh independent readers: 17 new children. Every historical failed parent
continues to be REFUSED; the original successful primary is not a successful
old package or a fresh zero-cost render.

Root must explicitly carry all actual prior-work fields, including both failed
native attempts and diagnostic/capture stages, from final stdout and observed
outer exits; no repeated primary CPU is added or refunded. The unchanged global
bounds remain1200 CPU seconds,1800 wall seconds,4 GiB cumulative file allowance,
128 MiB metadata; child240 wall seconds/16 MiB log/8 GiB committed Job memory.
The reader's existing remaining stage limits and128 MiB named-array cap apply
to these ten controls plus the actual read. New sources/metadata consume their
normal retained-byte budgets. An exhausted budget is a refusal, not permission
to reset the counters or waive an input.

First refusal preserves its original traceback/failing identity and leaves
remaining inputs unvisited, retaining original0's historical snapshot/TIFF.
All nine actual independent successes are still required before future coverage.
Existing coverage consumers recognize older schemas; compatibility requires a
separate reviewed source change, and is not silently granted here.
