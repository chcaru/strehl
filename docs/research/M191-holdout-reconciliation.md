# M191 — M8 holdout reconciliation

**Date:** 2026-09-05

**Repository snapshot audited:** `136c67664997b5886c0ea5fc7c4b879b8eba0b61`

**Disposition:** evidence for the scorecard owner's prospective population ruling; this
memo does not make that ruling.

## Executive result

The literal live table contains **13 rows / 2,800 frames** whose evidence class begins
`HOLDOUT`: 12 quality rows and one performance row. Their full admissibility partition
is:

| Classification | Rows | Frames |
|---|---:|---:|
| **BURNED** | **5** | **1,344** |
| **CLEAN** | **1** | **30** |
| **INDETERMINATE** | **7** | **1,426** |
| **Total** | **13** | **2,800** |

M8's population is the 12-row **quality subset**, not the performance row. Its
partition is **4 BURNED / 1 CLEAN / 7 INDETERMINATE = 12 rows**, or
**1,045 + 30 + 1,426 = 2,501 frames**.

The seven indeterminate rows are not unexamined rows and have not passed anything.
Each has a known pre-registration outcome read. Their uncertainty is wholly normative:
the scorecard says those pre-existing unrelated masters are not score outputs, but does
not say whether that status also immunises their subject/session units from its later
burn rule.

Under the narrow reading of that exception, only the 30-frame battery ISO-100 unit is
clean, which is not a defensible diverse M8 population. Under the grandfathering
reading, those seven units join it, producing **8 clean units / 1,456 frames** spanning
occlusion, fine crevices, multilayer structure, low contrast, motion texture,
specular/metal structure, translucent facets, and neutral slanted edges. That is enough
in number and kind for a prospectively registered M8 campaign, although the scorecard
sets no numerical minimum.

**Verdict: INDETERMINATE — the scorecard does not state whether the
pre-existing-unrelated-master exception immunises seven named subject/session units
from the later session-burn rule.**

## 1. Scope and non-consumption

This audit read only committed labels, filenames, manifests, EXIF-derived timestamps,
prior reports, and records of earlier outputs. It did **not** decode or visually inspect
a currently labelled holdout frame, render a candidate product, or compute a quality
metric. The sealed `requests\7-aperture-pairs` capture was not accessed.

Classes in this memo mean only:

- **CLEAN:** no committed record of an outcome read on any member of the unit;
- **BURNED:** a committed record identifies such a read;
- **INDETERMINATE:** the read is known, but the governing text does not establish
  whether an exception preserves or spends the unit.

None of these classes is a quality result or a score.

## 2. Which table is authoritative

`experiments/M141-capture-inventory/capture-stacks.csv` is the authoritative flat
metadata inventory used here for paths, filenames, frame counts, apertures, and
timestamps. M141 describes its product as:

> “The reusable inventory is
> `experiments/M141-capture-inventory/capture-manifest.json`; flat CSV views are
> `capture-stacks.csv` and `capture-segments.csv`.”
> (`docs/research/M141-capture-inventory.md:7-9`).

It is **not**, by itself, the authoritative live holdout table: the CSV has no evidence
class column. The current normative labels are in the scorecard, whose literal rule is:

> “only a row whose evidence class begins `HOLDOUT` is holdout. No other wording
> implies holdout status.”
> (`docs/proposals/2026-09-sota-scorecard.md:610-611`).

The older M141 report contains a 16-row working holdout register
(`docs/research/M141-capture-inventory.md:166-176`). It predates the live scorecard
revision and does not supersede that literal rule. The current quality-labelled rows are
the three fabric rows (`docs/proposals/2026-09-sota-scorecard.md:626-628`), the bee
repeat (`docs/proposals/2026-09-sota-scorecard.md:634`), and eight further rows
(`docs/proposals/2026-09-sota-scorecard.md:644-654`): **12 quality rows**. The same
literal rule also includes the `bee-1-cpl` `HOLDOUT — PERFORMANCE` row
(`docs/proposals/2026-09-sota-scorecard.md:655`). M8 excludes that row because its input
is “Every scored quality capture” (`docs/proposals/2026-09-sota-scorecard.md:1518`),
but this reconciliation does not silently omit it. This memo therefore uses the
scorecard to enumerate all 13 literal holdouts, identifies the 12-row M8 subset, and
uses the M141 CSV/manifest to resolve metadata.

## 3. Exact governing rule

The rule applied is:

> “The holdout unit is **subject plus uninterrupted capture session**, not a directory
> or step width. Rendering, tuning, or reading an outcome on any member burns every
> member of that unit.”
> (`docs/proposals/2026-09-sota-scorecard.md:714-716`).

The same paragraph makes input preparation distinct from outcome consumption:

> “A `HOLDOUT` capture may be decoded to build the frozen common input and input-only
> site manifest, but no output, metric, visual verdict, parameter sweep, or
> code-acceptance decision may be seen before the registered score run.”
> (`docs/proposals/2026-09-sota-scorecard.md:716-718`).

## 4. Uniform session-cut rule

M141's committed continuity implementation quantifies interruptions by timestamp gaps
while also checking within-stack file-number continuity:

> “VERIFIED yes only when DSC file numbers are consecutive, EXIF times are monotonic,
> and no inter-frame gap exceeds max(60 s, 10x the median gap, 2x the longest exposure
> + 10 s).”
> (`experiments/M141-capture-inventory/inventory.py:828-831`; implementation and
> fields at `experiments/M141-capture-inventory/inventory.py:415-443`).

I applied that threshold uniformly to consecutive captures of the same subject. Because
the governing unit is explicitly not a directory, adjacent same-subject directories
were also compared: they join only when their boundary gap is no greater than the
larger of the two stack continuity thresholds. Otherwise the boundary cuts a session.
Timestamps below are EXIF wall-clock capture times at UTC−07:00; timezone is immaterial
to the within-camera gap calculation.

Material boundary checks:

| Boundary | Gap | Applicable threshold | Result |
|---|---:|---:|---|
| fabric f/5.6 → f/8 | 276.932 s | 60.000 s | cut |
| fabric f/8 → f/11 | 35.325 s | 60.000 s | join |
| fabric f/11 → f/14 | 56.186 s | 60.000 s | join |
| fabric f/14 → f/18 | 60.714 s | 60.000 s | cut |
| bee `DSC00583` → `DSC00584` | 110.286 s | 60.000 s | cut |
| `bee-1-cpl` → `bee-2-cpl` | 469.059 s | 60.000 s | cut |
| `bee-2-cpl` → `bee-3-cpl` | 65.491 s | 60.000 s | cut |
| battery ISO 100 → ISO 200 | 455.062 s | 132.150 s | cut |
| battery ISO 200 → ISO 400 | 443.446 s | 132.140 s | cut |
| flower-only → flower/fern | 149.297 s | 60.000 s | cut |
| angled ruler → flat-on-ruler | 469.725 s | 60.000 s | cut |

The bee internal break is recorded directly in the manifest
(`experiments/M141-capture-inventory/capture-manifest.json:5376-5396`). The exported
same-setting segments show the first timestamp block at
`experiments/M141-capture-inventory/capture-segments.csv:81-89` and the second at
`experiments/M141-capture-inventory/capture-segments.csv:90-98`.

## 5. Row-by-row reconciliation

The session bounds below come from the M141 inventory
(`experiments/M141-capture-inventory/capture-stacks.csv:6,9,16,20-25,29-30,35,48-52,56-58`)
plus the uniform boundary rule above.

| # | Live row beginning `HOLDOUT` | Resolved subject/session unit | Frames | Class | Outcome-read record or clean basis |
|---:|---|---|---:|---|---|
| 1 | `requests\7-aperture-pairs\fabric-weave-f5.6-sw5-cpl` | fabric weave; 2026-08-29 17:27:06.011–17:33:01.672 | 210 | **BURNED** | M129 read the f/5.6 spectral outcome as `0.2771` (`experiments/M129-fabric-spectral-ladder/out/ladder.txt:19`). |
| 2 | `requests\7-aperture-pairs\fabric-weave-f8-sw5-cpl` | fabric weave; 2026-08-29 17:37:38.604–17:48:46.825; includes f/8, f/11, and non-holdout f/14 members | 150 | **BURNED** | M129 read the f/8 outcome as `0.2955` (`experiments/M129-fabric-spectral-ladder/out/ladder.txt:20`). |
| 3 | `requests\7-aperture-pairs\fabric-weave-f11-sw5-cpl` | fabric weave; 2026-08-29 17:37:38.604–17:48:46.825 (same unit as row 2) | 109 | **BURNED** | M129 read the f/11 outcome as `0.2946` (`experiments/M129-fabric-spectral-ladder/out/ladder.txt:21`); M-PHASE0-LCA also read its measured band outcomes (`docs/research/M-PHASE0-LCA.md:172-181`). |
| 4 | `requests\12-bee-iso-var-no-bracket-32-repeat-diff-light` | bee head; **two 288-frame sessions**: 2026-08-30 19:51:12.324–20:04:53.492 (`DSC00296`–`DSC00583`), and 20:06:43.778–20:19:20.929 (`DSC00584`–`DSC00871`) | 576 | **BURNED** | Both sessions were rendered after registration: a bright-session product is recorded at `experiments/SCORECARD-BASELINE/out/RENDER-MANIFEST.json:1-35`, and a second-light product at `experiments/SCORECARD-BASELINE/out/RENDER-MANIFEST.json:117-143`. Metrics were then read for the bright session at `experiments/SCORECARD-BASELINE/out/MEASUREMENTS.json:3-22` and the second-light session at `experiments/SCORECARD-BASELINE/out/MEASUREMENTS.json:48204-48222`. A later formal `UNMEASURED` label cannot undo these reads. |
| 5 | `duck-tape-side-layers-cpl` | duck-tape roll; 2026-08-27 21:01:55.905–21:05:26.488 | 197 | **INDETERMINATE** | A pre-registration master hash exists (`experiments/DELIVER-V6/BANK-33.md:71`), with a recorded visual verdict (`0146c167:docs/STATUS.md:787`) and metric outcome (`docs/research/V-ADJ13.md:78`). Narrow exception reading: burned. Grandfathering reading: preserved. |
| 6 | `chia-seeds-cpl` | chia seeds; 2026-08-27 21:40:55.869–21:44:35.085 | 130 | **INDETERMINATE** | Pre-registration master hash (`experiments/DELIVER-V6/BANK-33.md:65`), visual verdict (`0146c167:docs/STATUS.md:792`), and metric outcome (`docs/research/V-ADJ13.md:76`). Consequence depends on the same exception. |
| 7 | `flower-bud-with-background-fern-cpl` | flower/fern arrangement; 2026-08-23 21:39:27.357–21:42:11.737 | 299 | **INDETERMINATE** | Pre-registration master hash (`experiments/DELIVER-V6/BANK-33.md:74`) and subsequently documented quantitative occlusion outcome (`docs/research/M87-occlusion.md:708-714`). Consequence depends on the same exception. |
| 8 | `medication-pill-cpl` | medication pill; 2026-08-27 21:25:04.330–21:26:37.565 | 146 | **INDETERMINATE** | Pre-registration master hash (`experiments/DELIVER-V6/BANK-33.md:83`), visual verdict (`0146c167:docs/STATUS.md:789`), and metric outcome (`docs/research/V-ADJ13.md:80`). Consequence depends on the same exception. |
| 9 | `foam` | foam subject; 2026-05-25 16:25:55.386–16:30:04.060 | 100 | **INDETERMINATE** | Pre-registration master hash (`experiments/DELIVER-V6/BANK-33.md:77`) and metric outcome (`docs/research/V-ADJ13.md:75`). Consequence depends on the same exception. |
| 10 | `requests\misc-diagnostic\flat-round-3V-battery-cpl\flat-round-3V-battery-iso100-sw4-cpl` | round 3V battery, ISO 100; 2026-09-01 20:15:20.273–20:21:43.722 | 30 | **CLEAN** | No committed candidate render, quality metric, visual verdict, tuning decision, or code-acceptance read was found. The ISO-200 and ISO-400 control rows are separate sessions by 455.062 s and 443.446 s gaps. The only located image-sample-derived record is an explicitly `INPUT_ONLY_NECESSARY_CONDITION` rail census (`experiments/SCORECARD-BASELINE/out/RAIL-PREFLIGHT.json:38-47,158`); the baseline report says score rendering used only the bee repeats and describes this as an input census (`docs/research/SCORECARD-BASELINE.md:54-60`). It falls under the scorecard's input-only permission, not its candidate-outcome prohibition. |
| 11 | `maldon-sea-salt-cpl` | Maldon salt; 2026-08-27 21:50:45.442–21:53:41.040 | 255 | **INDETERMINATE** | Pre-registration master hash (`experiments/DELIVER-V6/BANK-33.md:82`), visual verdict (`0146c167:docs/STATUS.md:786`), and metric outcome (`docs/research/V-ADJ13.md:79`). Consequence depends on the same exception. |
| 12 | `highly-angled-ruler-mm-cpl` | highly angled ruler; 2026-08-23 20:10:02.129–20:13:29.058 | 299 | **INDETERMINATE** | Pre-registration master hash (`experiments/DELIVER-V6/BANK-33.md:78`) and physical focus-extent/monotonicity outcome (`docs/research/M84b-ruler-metrology.md:14-24`). Consequence depends on the same exception. |
| 13 | `bee-1-cpl` (`HOLDOUT — PERFORMANCE`; outside M8) | bee macro subject; 2026-08-23 11:42:25.240–11:46:55.268 | 299 | **BURNED** | M172 ran post-registration stack products from this exact unit (`docs/research/M172-worker-invariance-control.md:31-35`), read the delivered-pixel hashes, and used the differences for a code/negative-control decision (`docs/research/M172-worker-invariance-control.md:61-75`). |

### Counted partition

- Rows **1–4 and 13**: 5 BURNED / 1,344 frames.
- Row **10**: 1 CLEAN / 30 frames.
- Rows **5–9 and 11–12**: 7 INDETERMINATE / 1,426 frames.
- Literal all-holdout partition: **5 + 1 + 7 = 13 rows** and
  **1,344 + 30 + 1,426 = 2,800 frames**.
- M8 quality subset (excluding row 13): **4 + 1 + 7 = 12 rows** and
  **1,045 + 30 + 1,426 = 2,501 frames**.

At the unit level, f/8 and f/11 share one session while the bee-repeat quality row
spans two.
For the M8 subset the partition is therefore **4 burned units, 1 clean unit, and 7
indeterminate units**: the row/unit counts happen to be equal, but for different
reasons. Including the separate performance row, the literal all-holdout partition is
**5 burned units, 1 clean unit, and 7 indeterminate units**.

Two corrections to a directory-level reading matter:

- f/5.6 is not in the f/8–f/14 session, and f/18 is not either. Only f/8, f/11,
  and f/14 are continuous. All three live fabric rows are nevertheless burned by
  their direct M129 reads; f/11 additionally burns the shared session through the
  post-registration LCA read.
- the 576-frame bee directory is not one unit. It is two 288-frame units. Both,
  rather than merely one ambiguous directory, have rendered members.

The M129 outcomes are capture-derived spectral measurements, not pre-existing master
artifacts, so the master exception analysed below does not reach them.

### Negative-search closure

I searched the committed tree and the post-registration history for each exact row
path/name, then reconciled every later reference. No additional candidate product or
output-derived read was found for the seven old-master units or the battery. The later
uses are input definitions, inventories, plans, documentary audits, or expressly
input-only censuses:

- M152 records zero candidate outputs, zero comparator outputs, zero stacker runs, and
  no visual inspection (`docs/research/M152-site-census.md:47-61`);
- M169 records that no capture, candidate, comparator, or protected holdout pixel was
  opened (`docs/research/M169-m3-veil.md:322-342`); and
- M181 reran M152's hash-pinned input eligibility producer, while recording that the
  common-input base/planted renders and scorer do not exist
  (`docs/research/M181-m4-feasibility.md:235-239,270-273`).

The later `M167-detail-battery` is an adversarial instrument-test “battery,” not an
outcome on the round 3V capture: its result records `captures_opened: 0`
(`experiments/M167-detail-battery/results.json:164,285,399,575`), and its report says
the original RAW pixels were not reopened (`docs/research/M167-detail-battery.md:149`).

Those later records do not convert an old-master unit into CLEAN; they only close the
search for an additional, unambiguously post-registration candidate read.

## 6. The masters exception is genuinely ambiguous

The current exception says:

> “The first render of any scored capture **under this protocol** seals v1.10;
> pre-existing unrelated masters are not score outputs. A later change to an
> instrument, bar, eligibility rule, comparator setting, capture, or aggregation rule
> requires a numbered revision and a fresh holdout capture. Existing score outputs may
> then be used only for development.”
> (`docs/proposals/2026-09-sota-scorecard.md:115-119`).

The later unit rule says:

> “Rendering, tuning, or reading an outcome on any member burns every member of that
> unit.”
> (`docs/proposals/2026-09-sota-scorecard.md:714-716`).

These sentences answer different questions on their face:

1. **Narrow/status-only reading.** “Not score outputs” classifies the old master
   artifacts only. It does not say that the underlying unit remains fresh. Under the
   later unconditional burn sentence, the seven known visual/metric reads spend their
   units. Final M8-quality result: **11 burned rows / units (2,471 frames) and 1 clean
   row / unit (30 frames)**; replacement capture is required.
2. **Grandfathering reading.** The exception deliberately excludes the old unrelated
   master lineages from this protocol's consumption accounting, so their underlying
   units remain eligible. Final M8-quality result: **4 burned rows / units and 8 clean
   rows / units (1,456 frames)**; no owner shutter time is required for M8.

The narrow reading is the more literal grammar: the exception states what the masters
*are not*, not what their units *remain*. The grandfathering reading is supported by
registration history: the original scorecard commit introduced the exception
(`90bced75:docs/proposals/2026-09-sota-scorecard.md:8-12`) while placing these seven
already-rendered subjects in its “Scored and control captures” table
(`90bced75:docs/proposals/2026-09-sota-scorecard.md:198-225`); commit `e68f40f7` later
retained them, added explicit `HOLDOUT` labels, and added the session-burn rule. Neither
history nor internal consistency is a substitute for missing normative text.

One non-governing cross-check points in the same broad direction: the current phase-1
design allows foam as sealed stress evidence while expressly calling it “historically
studied, not historically unseen”
(`fe111781:docs/proposals/2026-09-phase1-design.md:72`). That describes programme intent for
phase 1, not an M8 admissibility rule, so it cannot resolve the scorecard conflict.

The higher-ranked SOTA plan contains no matching “pre-existing unrelated,” “holdout
unit,” or “uninterrupted capture session” rule, so it does not break this tie. No current
sentence expressly says either “pre-existing reads do not burn the unit” or “the
exception changes artifact status only.” The ambiguity is therefore real, not an
unresolved repository search.

**What settles it:** one prospective, owner-authored numbered scorecard amendment naming
these seven units and saying either (a) they are grandfathered and remain fresh
notwithstanding the listed reads, or (b) the exception concerns output status only and
the units are spent. No new image read is needed to settle it.

## 7. Bottom line for the scorecard owner

M8's population rule is “Every scored quality capture”
(`docs/proposals/2026-09-sota-scorecard.md:1518-1521`); it gives no minimum number of
subjects or frames. Sufficiency below is therefore explicitly an engineering inference,
not a hidden numerical bar.

### Unconditional fact

There is **1 unambiguously CLEAN unit**: the 30-frame battery ISO-100 capture. It is not
sufficient in number or kind to carry a defensible M8 quality population by itself. It
provides one short reflective/edge rail and cannot establish breadth across the failure
geometries the campaign is meant to exercise.

### If the owner adopts the grandfathering reading

There are **8 CLEAN units / 1,456 frames**:

- duck tape — 197;
- chia seeds — 130;
- flower/fern — 299;
- medication pill — 146;
- foam — 100;
- battery ISO 100 — 30;
- Maldon salt — 255;
- highly angled ruler — 299.

That population is sufficient in number and kind for a prospectively registered scored
M8 campaign: it supplies long deterministic site censuses and materially different
occlusion, texture, contrast, reflectance, and edge geometries. This sufficiency is an
engineering inference; the scorecard states no minimum subject count. **No new owner
capture is required under this reading.**

### If the owner adopts the narrow/status-only reading

The seven old-master units are spent, leaving only battery ISO 100. **Owner shutter time
is required.** The minimal executable replacement I recommend is one new composite
299-frame bracket, prospectively registered before capture:

| Field | Required capture |
|---|---|
| Subject | A fixed composite: frayed woven fibres crossing a scratched reflective metal surface, with a darker textured surface behind both |
| Framing | Fill the frame so nearest fibres, central scratches/specular highlights, and far textured ground all remain in the focus sweep |
| Camera / lens | Sony A7C II + Sony FE 100 mm F2.8 Macro GM OSS + 2× Viltrox teleconverter |
| Aperture | Camera-reported **f/5.6** |
| ISO / exposure | **ISO 100**, one fixed exposure chosen before the bracket to protect metal highlights |
| Focus bracketing | In-camera focus bracketing, **step width 4**, **299 frames** |
| Focus direction | Start on the nearest fibre and run one uninterrupted bracket through the far background |
| Stability | Tripod; static subject and light; **IBIS/OSS off** |
| Quarantine | Disable automatic image review before starting. Take no same-session test frame. After the first scored exposure, make no playback/preview judgement, render, quality metric, visual read, tuning, or code-acceptance use before the registered score run |

Why this specification:

- f/5.6 retains high-frequency source detail for an alias-sensitive M8 census;
- step width 4 supplies dense focus-placement phases without requiring a non-executable
  exposure interleave;
- 299 frames provides a large deterministic site population;
- one static frame combines fibres, occlusion boundaries, dark texture, scratches,
  highlights, and a depth sweep, complementing rather than duplicating the clean
  battery rail.

This is deliberately one ordinary in-camera bracket with one exposure per focus
position. It does **not** require interleaving two exposures at a node. The “one new
composite stack is sufficient beside battery” conclusion is an engineering
recommendation, not a scorecard-stated minimum; if the owner wants replication rather
than the minimum defensible route, repeat the same protocol on a separately arranged
composite as a second subject/session.

INDETERMINATE — the scorecard does not state whether the pre-existing-unrelated-master exception immunises seven named subject/session units from the later session-burn rule.
