# M141 — capture inventory, holdout ruling, and remaining shoot

## Bottom line

- **VERIFIED:** `D:\personal\macro` contains **68 stack directories / 10,509
  ARWs**: **32 / 3,908** under `requests\` and **36 / 6,601** general stacks.
  The reusable inventory is
  `experiments/M141-capture-inventory/capture-manifest.json`; flat CSV views are
  `capture-stacks.csv` and `capture-segments.csv`.
- **INHERITED ruling, independently metadata-checked:** the
  `high-res-calibration-slide-cpl` material is **not clean holdout**. It is one
  **657-frame** session already designated and spent as development:
  **BURNED — deliberately spent development, not holdout**. The program record
  says this explicitly at `docs/proposals/2026-09-sota-scorecard.md:363-379`
  and `docs/STATUS.md:2535-2547`.
- **VERIFIED gap arithmetic:** existing material contributes **0 eligible
  frames** to the frozen holdout session. The owner still owes all **603
  session frames** in its **24 requested blocks**. The procedure is **604
  shutter releases** including the one throwaway histogram exposure
  (`docs/capture-requests/2026-09-319-frame-session.md:127-137`,
  `:228-255`, `:566-577`).
- **INHERITED additional prerequisite:** pre-shoot blockers **1** and **2**
  still require one exact-configuration development rehearsal; blocker **3**
  is closed (`docs/capture-requests/2026-09-319-frame-session.md:27-32`).
  The request does not assign that rehearsal a frame count, so it is additional
  to, but not included in, the **603 VERIFIED remaining session frames**.

## Method and inventory products

I read filesystem and EXIF metadata only with ExifTool **13.58 VERIFIED**. I did
not decode pixels, render a stack, inspect a visual result, or run the stacker.
A stack is one directory containing one or more `.ARW` files.

The manifest records, for every stack:

- exact path, subject/name, ARW count and bytes;
- first/last EXIF capture timestamp;
- filename-sequence and timestamp continuity, median/max gap, and every detected
  break;
- ISO, exposure, aperture, focal length, focus-distance and
  `FocusPosition2` distributions;
- stabilisation, release mode, camera and reported lens identity;
- step width where an `swN` path label supplies it;
- CPL state with its provenance; and
- contiguous setting segments for multi-setting directories such as the paper,
  bee-repeat, dark and flat campaigns.

The eight request groups are all present:

| Request tree | Stack directories (VERIFIED) | ARWs (VERIFIED) |
| --- | ---: | ---: |
| `10-paper-iso-var` | 1 | 110 |
| `12-bee-iso-var-no-bracket-32-repeat-diff-light` | 1 | 576 |
| `19-razor-edge` | 6 | 789 |
| `30-calibration-grid` | 5 | 242 |
| `6-11-extended-dark-frames` | 1 | 506 |
| `7-aperture-pairs` | 5 | 623 |
| `8-tilted-planar` | 3 | 270 |
| `misc-diagnostic` | 10 | 792 |
| **Total** | **32** | **3,908** |

**VERIFIED:** all **68** filename sequences are consecutive. **VERIFIED:** **67**
directories pass the documented temporal-contiguity rule. The exception is
`requests\12-bee-iso-var-no-bracket-32-repeat-diff-light`, whose **2 INHERITED**
documented
light passes have a **110.286 s** internal gap; the files remain one consecutive
**576-frame** sequence. See
`experiments/M141-capture-inventory/capture-manifest.json`.

**VERIFIED:** every one of the **10,509** ARWs reports camera `ILCE-7CM2`,
focal length **200 mm**, lens string
`FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`, and
`ImageStabilization: On`. Physical converter identity is not recoverable from
that string; the request correctly records the Viltrox identity as owner
testimony, not metadata
(`docs/capture-requests/2026-09-319-frame-session.md:38-48`).

**VERIFIED:** step width is path-recoverable for **29** stack directories and
not recoverable for **39**. **VERIFIED:** physical reproduction ratio is
metadata-recoverable for **0** stacks. `FocusDistance2` is retained as a coarse
proxy but is not promoted to magnification. This is important because the
request itself says coverage at **1.30× INHERITED** must be checked from image
data, not EXIF
(`docs/capture-requests/2026-09-319-frame-session.md:27`,
`:50-66`).

The current aggregate counts are consistent with the prior scorecard census
plus the new slide:
the scorecard recorded **10,067 files / 9,852 ARWs INHERITED**
(`docs/proposals/2026-09-sota-scorecard.md:290-291`), while this inventory finds
**10,724 files / 10,509 ARWs VERIFIED**. Both deltas are **657 VERIFIED**, the
new slide's measured frame count.

**VERIFIED stale-artifact warning:** `docs/research/SCORECARD-BASELINE.md:62-64`
instead reports **4,086 request ARWs INHERITED** and attributes **835 INHERITED**
to the slide. That does not match either the current filesystem
(**3,908 request ARWs VERIFIED**) or the scorecard's own prior request census
(**3,251 ARWs INHERITED**) plus the independently confirmed
**657-frame VERIFIED** slide. Use the M141 manifest for current inventory.

## Four-way characterisation of the new slide

Common metadata across all **6 VERIFIED** underlying stacks is
**ISO 100, f/5.6, 200 mm,
CPL, and ImageStabilization On VERIFIED**. `sw4`/`sw10` values below are
**INHERITED from directory labels** because Sony EXIF does not expose the step
width.

| Requested directory | What is present | Capture continuity | Scientifically useful for |
| --- | --- | --- | --- |
| `flat-sw4-cpl` | **186 frames VERIFIED** in three runs: **65 at 6 s**, **61 at 2.5 s**, **60 at 1 s**; **sw4 INHERITED**. Span **20:13:04.463–20:30:05.390 VERIFIED**. | Each member run is contiguous. The runs are separated by **228.789 s** and **93.066 s VERIFIED**, so the directory is a three-run exposure ladder, not one uninterrupted repeat burst. | A fronto-parallel depth null, flat-path identity/resampling test, real-photon SNR ladder, and detector for invented structure. It is not matched-repeat evidence because exposure changes across runs (`docs/STATUS.md:2527-2537`; `docs/proposals/2026-09-sota-scorecard.md:309-311,370-375`). |
| `tilted-sw4-cpl` | **182 frames VERIFIED**, **1 s VERIFIED**, **sw4 INHERITED**. Span **20:46:50.071–20:51:13.767 VERIFIED**. Coarse `FocusPosition2`: **57×76, 58×80, 59×26 VERIFIED**. | Contiguous: median gap **1.459 s VERIFIED**, maximum **1.499 s VERIFIED**. | Dense monotonic depth ramp for M5 coverage and M10 planarity/order commissioning; with `tilted-sw10`, a real sampling-density improvement arm. It is development only, never scored FRC/reference evidence (`docs/STATUS.md:2514-2525`; `docs/proposals/2026-09-sota-scorecard.md:312,377-380`). |
| `tilted-sw10-cpl` | **92 frames VERIFIED**, **1 s VERIFIED**, **sw10 INHERITED**. Span **20:52:52.160–20:55:04.626 VERIFIED**. Coarse `FocusPosition2`: **57×38, 58×40, 59×14 VERIFIED**. | Contiguous: median gap **1.458 s VERIFIED**, maximum **1.491 s VERIFIED**. | Sparse monotonic depth ramp and lower-sampling member of the `sw4`/`sw10` development pair. The first two encoder-bucket ratios are exactly **2.000 VERIFIED**, but EXIF is too coarse to prove gap-free coverage (`docs/capture-requests/2026-09-319-frame-session.md:50-66`; `docs/proposals/2026-09-sota-scorecard.md:313`). |
| `very-tilted-all-axis-sw10-cpl` | **197 frames VERIFIED**, **1 s VERIFIED**, **sw10 INHERITED**. Span **20:57:12.415–21:01:58.443 VERIFIED**. Coarse `FocusPosition2`: **56×10, 57×40, 58×40, 59×41, 60×40, 61×26 VERIFIED**. | Contiguous: median gap **1.460 s VERIFIED**, maximum **1.495 s VERIFIED**. | Strong all-axis ramp for field-geometry, plane/order and difficult coverage commissioning. Its geometry differs from `tilted-sw10`, so it is not a repeat arm (`docs/proposals/2026-09-sota-scorecard.md:314`). |

Together the **6 VERIFIED** stacks span
**20:13:04.463–21:01:58.443 VERIFIED**. The longest
inter-stack gap is **1,004.681 s VERIFIED** between the flat and tilted setups.
The scorecard conservatively treats that reconfiguration as part of one
physical-subject/session unit
(`docs/proposals/2026-09-sota-scorecard.md:363-368`).

## Holdout and burn ruling

The governing rule is exact: the unit is subject plus uninterrupted capture
session, and reading an output, metric, visual verdict, parameter sweep or
code-acceptance result on one member burns every member
(`docs/proposals/2026-09-sota-scorecard.md:343-348`).

### Burned or deliberately spent

1. **`30-calibration-grid`: BURNED / QUARANTINED.** The **5 VERIFIED** stacks total
   **242 frames VERIFIED** and span
   **20:57:42.542–21:09:06.266 VERIFIED**. W1 decoded and aligned all
   **55 frames VERIFIED** of grid-1 sw4 and read candidate outcomes
   (`experiments/PHASE1-DESIGN/quarantine/f5658e5d-grid-sw4-exposed/ACCESS.md:6-18`).
   The scorecard consequently burns all **5 INHERITED** session members
   (`docs/proposals/2026-09-sota-scorecard.md:304-308,345-360`).
2. **`high-res-calibration-slide-cpl`: BURNED — deliberately spent
   development, not holdout.** The scorecard classified all six before outcomes
   as one **657-frame INHERITED** development unit
   (`docs/proposals/2026-09-sota-scorecard.md:36-41`), and the program later
   states verbatim that it was “burned deliberately and knowingly” and “must
   not be used for any scored result” (`docs/STATUS.md:2544-2547`).

**Ruling on the new slide: BURNED, not clean and not indeterminate.** I err in
the restrictive direction: the entire six-stack sitting is one spent unit,
rather than trying to split it at the **16 min 44.681 s VERIFIED** reorientation
gap. Had it remained clean, any rendered output, metric, visual verdict,
parameter sweep or code-acceptance decision on any one member would have burned
all six. That condition has already occurred: the released unit was used for
development geometry work
(`experiments/cover-default/slide-series-preregistration.md:9-15`;
`docs/research/cover-default.md:85-90`).

### Currently registered clean holdout rows

**INHERITED from the scorecard:** **16 rows INHERITED** still begin with
`HOLDOUT`; no
contrary capture-burn record was found for them. They are the three registered
fabric apertures, three tilted-ruler apertures, the bee ISO-repeat directory,
duck tape, chia seeds, flower bud with fern, medication pill, foam, the ISO-100
battery stack, Maldon salt, highly angled ruler, and `bee-1-cpl`
(`docs/proposals/2026-09-sota-scorecard.md:315-334`). Exact paths, timestamps
and **VERIFIED** frame counts are in
`experiments/M141-capture-inventory/holdout-register.json`.

The same register separately lists the scorecard's explicit control,
development and historical rows. **VERIFIED:** **35** of the **68** inventoried
stack directories have no row in that explicit evidence table. Because the
scorecard says only a row beginning `HOLDOUT` is holdout
(`docs/proposals/2026-09-sota-scorecard.md:299-300`), those are classified
**INDETERMINATE — DO NOT ASSUME CLEAN**, not silently promoted.

## Gap analysis against the frozen session

Three cross-cutting facts decide every block:

1. The requested data must be one uninterrupted session; splitting it across
   sittings invalidates it
   (`docs/capture-requests/2026-09-319-frame-session.md:6-11`).
2. Existing development captures commission the instrument; the new session
   supplies the scored holdout value and cannot be partly spent
   (`docs/capture-requests/2026-09-319-frame-session.md:169-179`).
3. **VERIFIED:** all existing **10,509 ARWs** report stabilisation on, while the
   request requires body SteadyShot and lens OSS off
   (`docs/capture-requests/2026-09-319-frame-session.md:497-500`).

Existing analogues are therefore useful for rehearsal and commissioning but
credit **0 VERIFIED** frames toward the sealed score session.

Every shorthand `:line` citation in the table below refers to
`docs/capture-requests/2026-09-319-frame-session.md`; every `scorecard :line`
citation refers to `docs/proposals/2026-09-sota-scorecard.md`.

| Requested block | Frames | Ruling | Block-specific reason and citation |
| --- | ---: | --- | --- |
| reset pre-flight P0 | **6 INHERITED** | **NOT SATISFIED** | No named same-session reset burst exists (`docs/capture-requests/2026-09-319-frame-session.md:228`). |
| reset pre-flight P1 | **6 INHERITED** | **NOT SATISFIED** | No return-to-reset paired burst exists (`:229`). |
| start `sw4-A` | **6 INHERITED** | **NOT SATISFIED** | No sentinel tied to an eligible A pass exists (`:230`). |
| `sw4-A` | **55 INHERITED** | **NOT SATISFIED** | Old sw4 is burned; new slide sw4 is development-only and has no eligible matched B (`:231`; scorecard `:304-314,383-390`). |
| end `sw4-A` | **6 INHERITED** | **NOT SATISFIED** | No untouched-final-position sentinel exists (`:232`). |
| start `sw4-B` | **6 INHERITED** | **NOT SATISFIED** | No repeated-reset sentinel exists (`:233`). |
| `sw4-B` | **55 INHERITED** | **NOT SATISFIED** | No second eligible identical **55-frame INHERITED** pass exists (`:234`; scorecard `:383-390`). |
| end `sw4-B` | **6 INHERITED** | **NOT SATISFIED** | No paired endpoint sentinel exists (`:235`). |
| start `sw10-A` | **6 INHERITED** | **NOT SATISFIED** | No sentinel tied to an eligible A pass exists (`:236`). |
| `sw10-A` | **27 INHERITED** | **NOT SATISFIED** | Existing sw10 stacks are burned/development-only; the two new sw10 views differ in geometry (`:237`; scorecard `:313-314`). |
| end `sw10-A` | **6 INHERITED** | **NOT SATISFIED** | No untouched-final-position sentinel exists (`:238`). |
| start `sw10-B` | **6 INHERITED** | **NOT SATISFIED** | No repeated-reset sentinel exists (`:239`). |
| `sw10-B` | **27 INHERITED** | **NOT SATISFIED** | No eligible identical-geometry repeat exists (`:240`; scorecard `:383-392`). |
| end `sw10-B` | **6 INHERITED** | **NOT SATISFIED** | No paired endpoint sentinel exists (`:241`). |
| `sw1` checker-only | **91 INHERITED** | **NOT SATISFIED** | The exact old **91-frame VERIFIED** sw1 stack is burned; the new dense slide is sw4 and development-only (`:242`; scorecard `:304,312`). |
| flats A | **32 INHERITED** | **NOT SATISFIED** | No independent same-session, same-exposure diffuser group assigned to A exists (`:243`; calibration requirements `:464-481`). |
| flats B | **32 INHERITED** | **NOT SATISFIED** | No separately repositioned B diffuser group exists (`:244`; `:464-481`). |
| darks A | **32 INHERITED** | **NOT SATISFIED** | The existing dark campaign has one **22-frame VERIFIED** ISO-100/1-s group, not a warmed same-session A group (`:245`; `capture-segments.csv`). |
| darks B | **32 INHERITED** | **NOT SATISFIED** | No second independent warmed same-session group exists (`:246`; `:483-492`). |
| reference near | **32 INHERITED** | **NOT SATISFIED** | No fixed-focus view of the same patch at the required high reproduction exists (`:249`; reference protocol `:303-322`). |
| reference middle | **32 INHERITED** | **NOT SATISFIED** | Same missing same-patch/high-reproduction reference condition (`:250`; `:303-322`). |
| reference far | **32 INHERITED** | **NOT SATISFIED** | Same missing same-patch/high-reproduction reference condition (`:251`; `:303-322`). |
| reference flats | **32 INHERITED** | **NOT SATISFIED** | No independently repositioned reference-only master from that block exists (`:252`; `:319-320`). |
| reference darks | **32 INHERITED** | **NOT SATISFIED** | No warmed dark group matching that reference exposure exists (`:253`; `:321`). |

**VERIFIED arithmetic:** **24** not-satisfied blocks sum to **603 remaining
frames**. There are **0 already-satisfied** and **0 partially-satisfied** blocks
because the protocol forbids assembling a scored session from prior sittings.
The machine-readable ruling and per-block reasons are in
`experiments/M141-capture-inventory/capture-gap-analysis.json`.

## Read-only verification

Start-of-work and end-of-work recursive `Get-ChildItem -Force -File` counts are
recorded in
`experiments/M141-capture-inventory/readonly-verification.json`.

- `D:\personal\macro`: start **10,724 files / 487,169,829,957 bytes
  VERIFIED**; end **10,724 files / 487,169,829,957 bytes VERIFIED**.
- `D:\edited\macro`: start **387 files / 141,333,902,406 bytes VERIFIED**;
  end **387 files / 141,333,902,406 bytes VERIFIED**.

Both recursive file-count and total-byte pairs match **VERIFIED**. Neither
capture tree was written, moved, renamed, converted or deleted by this lane.
