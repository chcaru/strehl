# M154 - M10 ruler-angle provenance

## Verdict

**M10 remains UNMEASURED.**

`10.26 deg` is **DERIVED nominally correct**, but it is not a qualified
external-truth value:

```
MEASURED (owner-reported, unbounded): run  = about 10 cm
MEASURED (owner-reported, unbounded): rise = about 1.81 cm
DERIVED: slope = rise / run = 0.181
DERIVED: theta_nom = atan(0.181) = 10.259461685 deg
DERIVED: theta_nom rounded to 0.01 deg = 10.26 deg
```

The sole underlying source is
`D:\personal\macro\requests\8-tilted-planar\README.md:4`. It says:

> Subject is a ruler tilted up (vertically) from left to right at an angle of
> approximately 10.26deg (measured about: 10cm run against 1.81cm rise).

The file is **VERIFIED** at SHA-256
`3735dd46b11332e89badcc2614060a2b70a0aa0a9fbdcf32d1e78906720bfc51`.
Its measurement instrument, least count, endpoint definition, repeatability,
camera-relative coordinate frame, and uncertainty are not recorded.

Therefore the evidence supports this interval:

```
UNMEASURED: theta_ext uncertainty interval = unknown
```

It does not support a finite interval around `10.26 deg`. The decimal places
in a derived display value are not measurement precision. There is no evidence
that `10.26 deg` is materially wrong, but there is also no evidence that it is
accurate enough for M10.

## Holdout handling and prior burn

The holdout rule was read before any capture access. In particular,
`docs/proposals/2026-09-sota-scorecard.md:345-349` says that the unit is subject
plus uninterrupted session and that reading an outcome from any member burns
the whole unit.

No ARW was opened or decoded, no image was rendered, and no output, metric,
visual verdict, or sweep was inspected. External access was limited to the
request-level text README above, recursive searches over text metadata, and
directory listings. Already committed metadata inventories were also read.
Nothing was written, moved, renamed, or deleted under `D:\personal\macro` or
`D:\edited\macro`. This is the M154 session action record; the script's narrower
external access is separately recorded in its JSON output and does not pretend
to audit the interactive session.

**VERIFIED: the ruler unit was already burned before the scorecard called it a
holdout.** `docs/research/M-PHASE0-CURV.md:8-25,160-169` reports observed
outcomes from all three exact f/5.6, f/8, and f/11 ruler stacks.
`docs/research/M-PHASE0-LCA.md:17-27,125` reports another observed metric using
the same f/11 stack. Git history places the first CURV verdict at
`e3d6811bd06dc28237b2416059165eca105092f3`,
`2026-09-02T20:34:47-07:00`, and the LCA verdict at
`994ecb48ead3ac9522e4d8307ef8a6768db50f81`,
`2026-09-02T21:19:34-07:00`, both **VERIFIED** before scorecard registration at
`90bced75910d77766bc5c0f4f3bac3dcf604bab0`,
`2026-09-02T23:27:11-07:00`.

Under the absolute subject-plus-session rule, reading any one of those outcomes
burned every member. M154 caused no new burn, but the existing three-stack
ruler unit is not admissible score evidence regardless of whether its angle can
later be recovered.

## What M10 requires

The registered construction is **VERIFIED** at
`docs/proposals/2026-09-sota-scorecard.md:1048-1055`:

> Map ruler ticks to physical `x`; external truth is
> `z_true=x*tan(theta_ext)` after one fitted origin only. `theta_ext` must come
> from a measurement independent of image focus and be frozen with uncertainty
> small enough to contribute at most `2.5%` slope error. The README's
> "approximately 10.26 deg" is a candidate value, not by itself traceable
> truth. No slope is fitted from strehl's depth output.

The requested verbatim success clause is **VERIFIED** at
`docs/proposals/2026-09-sota-scorecard.md:1062-1065`:

> **Success.** **SCORECARD ADDITION:** valid target pixels `>=99%`; rank
> correlation `>=0.99`; median absolute error `<=0.5` focus step; p95 `<=1.0`
> step; ruler slope error `<=5%`; flat-null p95 range `<=0.5` step; synthetic
> layer confusion `<=1%`.

The success clause's final ruler bar is **VERIFIED** as `5%`. The exact
computation imposes the stricter **VERIFIED** input-truth allocation of `2.5%`.
The latter determines the required angle precision.

Let the frozen nominal slope be `m0 = 0.181`. Requiring
`abs(m0 / m_true - 1) <= 0.025` gives:

| Quantity | Value | Label |
| --- | ---: | --- |
| admissible true slope | `[0.176585366, 0.185641026]` | **DERIVED** |
| admissible true angle | `[10.014357337, 10.516726712] deg` | **DERIVED** |
| lower/upper angle allowance around nominal | `-0.245104348 / +0.257265026 deg` | **DERIVED** |
| final `5%` bar alone | `[9.780579707, 10.787069261] deg` | **DERIVED** |

Thus an angle merely known within `+/-1 deg` produces up to
`11.022604%` slope error, **DERIVED**, and an angle rounded to the nearest
degree (`+/-0.5 deg`) produces up to `5.231674%`, **DERIVED**. Neither meets
the `2.5%` truth allocation. Around this nominal angle, M10 needs approximately
`-0.245/+0.257 deg`, not degree-level knowledge.

## Derivation and uncertainty

### Inputs and provenance

| Input | Value | Provenance and label |
| --- | ---: | --- |
| horizontal run | about `10 cm` | **MEASURED owner report, uncertainty unrecorded**; external README line 4 |
| axial rise | about `1.81 cm` | **MEASURED owner report, uncertainty unrecorded**; external README line 4 |
| camera | `ILCE-7CM2` | **VERIFIED** over all inventoried ARWs by `docs/research/M141-capture-inventory.md:80-84` |
| focal length | `200 mm` | **VERIFIED** over all inventoried ARWs by the same source |
| lens metadata string | `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter` | **VERIFIED** over all inventoried ARWs by the same source |
| capture mode | in-camera focus bracket, camera fixed and focus moved | **VERIFIED repository record** in `AGENTS.md:1100-1107`; the external README line 4 also calls it a focus bracket |

The rig facts verify the requested hardware identity, but they do not determine
the target's pose. Sensor pitch, focal length, aperture, working distance, and
magnification cannot yield `theta_ext` without an independent target-pose
measurement or an image-derived estimate. An image-derived estimate would
violate M10's independence condition and, for these captures, the holdout rule.

### Nominal reconstruction

The derivation does not use the committed `10.26` value as an input:

```
m = h / r
  = (1.81 cm) / (10 cm)
  = 0.181

theta_nom = atan(m)
          = 10.259461685 deg
          -> 10.26 deg when rounded to 0.01 deg
```

This exact rounding match makes the README's rise/run pair the numerical origin
of the angle. It does not manufacture an uncertainty bound.

For bounded inputs `h in [h_lo,h_hi]` and `r in [r_lo,r_hi]`, with positive
lengths, the propagated angle interval would be:

```
theta_ext in [atan(h_lo/r_hi), atan(h_hi/r_lo)]
```

The source gives no `h_lo`, `h_hi`, `r_lo`, or `r_hi`, so this propagation
cannot be completed from existing evidence.

As a sensitivity illustration only, suppose the displayed digits are treated
as rounding bins: `10 cm` to the nearest `1 cm`, and `1.81 cm` to the nearest
`0.01 cm`. That unsupported convention gives:

| Quantity | Value | Label |
| --- | ---: | --- |
| run interval | `[9.5, 10.5] cm` | **ASSUMED**, not evidence |
| rise interval | `[1.805, 1.815] cm` | **ASSUMED**, not evidence |
| slope interval | `[0.171904762, 0.191052632]` | **DERIVED from ASSUMED inputs** |
| angle interval | `[9.754081236, 10.816165801] deg` | **DERIVED from ASSUMED inputs** |
| worst frozen-slope error | `5.290859%` | **DERIVED from ASSUMED inputs** |

This conditional interval fails even the `2.5%` allocation. It is not offered
as the actual uncertainty; it demonstrates why the displayed precision cannot
stand in for a bound.

### Coordinate-definition ambiguity

The word `run` conventionally means horizontal run, so `atan(1.81/10)` is the
best-supported reading. The note does not define the endpoints or say whether
`10 cm` is horizontal projection or distance along the ruler.

If `10 cm` were instead distance along the ruler, the angle would be
`asin(1.81/10) = 10.428012387 deg`, **DERIVED**. More importantly, if `s` is
distance along ruler ticks, the physical relation is `z=s*sin(theta_ext)`;
`z=x*tan(theta_ext)` is equivalent only when `x=s*cos(theta_ext)` is the
lateral projection. At the nominal angle, `tan(theta)/sin(theta)-1` is
`1.624849%`, **DERIVED**, which consumes most of the `2.5%` truth budget.

The scorecard should therefore define whether `x` is ruler arclength or lateral
projection before the physical-depth checker is implemented.

## Exhaustive occurrence and origin audit

### Search scope and controls

`experiments/M154-m10-angle/analyse.py` performed a binary-safe,
boundary-aware scan of every regular tracked blob in immutable Git commit
`7bb34024bc62a39919bf2de303f2d2a19976b058`, **VERIFIED**. It read the
commit through `git archive`, so concurrent commits or worktree edits cannot
mix states. It scanned **MEASURED 9,508** blobs totalling
**MEASURED 350,327,083 bytes**, applied no filename-suffix filter, and excluded
only M154's own paths to prevent a self-referential inventory. The commit,
UTC timestamp, and scan scope are frozen in the JSON artifact.

The scan found:

| Result | Count | Label |
| --- | ---: | --- |
| raw `10.26` substrings | `537` in `126` files | **MEASURED by immutable repository scan** |
| bounded exact `10.26` tokens | `73` | **MEASURED by immutable repository scan** |
| exact `theta_ext` tokens | `7` | **MEASURED by immutable repository scan** |
| combined bounded tokens | `80` in `26` files | **MEASURED by immutable repository scan** |
| ruler-angle-related tokens | `77` | **MEASURED and classified** |
| unrelated exact numeric `10.26` tokens | `3` | **MEASURED and classified** |
| whitespace-collapsed `approximately\s+10.26\s*deg...` matches | `6` | **MEASURED by cross-line scan** |
| repository matches for the source dimensions `10 cm run` or `1.81 cm rise` | `0` | **MEASURED by exact targeted scan** |

Most raw substrings are values such as `10.263...` or `110.264...`, not the
exact angle token. The JSON retains both raw counts and the boundary-aware
classification rather than relying on a truncated display.

A recursive text-only search of both read-only external trees,
`D:\personal\macro` and `D:\edited\macro`, for `10.26`, `theta_ext`, the rise,
and the run returned exactly the one README line quoted above. A separate
directory listing found the three capture-directory names carrying
`ang10.26deg`; directory names contain no derivation or uncertainty.

The authoritative complete occurrence ledger is
`experiments/M154-m10-angle/out/analysis.json` under
`repository_inventory.hits`. Every hit has file, line, column, context, token,
and classification. The ledger also records every cross-line phrase match.

### Every tracked ruler-angle occurrence

These are all **MEASURED** pre-M154 ruler-angle-related hits in the immutable
tracked commit. Repeated line numbers mean that the token occurs more than once
on that line.

| File | Lines | What it is; traceability now |
| --- | --- | --- |
| `docs/proposals/2026-09-sota-scorecard.md` | `318,319,320,403,1041,1051 (2),1054` | capture labels and candidate/requirement text; nominal origin now traced, uncertainty still absent |
| `docs/research/M-PHASE0-LCA.md` | `125` | capture label only; no independent truth |
| `docs/research/SCORECARD-BASELINE.md` | `34` | approximate candidate statement; nominal origin now traced, uncertainty still absent |
| `docs/STATUS.md` | `932,5072 (2)` | approximate candidate/status text; nominal origin now traced, uncertainty still absent |
| `experiments/M-PHASE0-CURV/out/aperture-f11-measure.json` | `5` | capture path only |
| `experiments/M-PHASE0-CURV/out/aperture-f8-measure.json` | `5` | capture path only |
| `experiments/M-PHASE0-CURV/out/commission-initial-red.json` | `99` | capture path only |
| `experiments/M-PHASE0-CURV/out/commission.json` | `99` | capture path only |
| `experiments/M-PHASE0-CURV/out/primary-f5p6-measure.json` | `5` | capture path only |
| `experiments/M-PHASE0-CURV/PREREGISTRATION.md` | `122` | capture label only |
| `experiments/M-PHASE0-CURV/src/commission.py` | `40` | capture path only |
| `experiments/M-PHASE0-CURV/src/measure.py` | `38,47,56` | three capture paths only |
| `experiments/M-PHASE0-LCA/out/measurement.json` | `760,14676` | capture path only |
| `experiments/M-PHASE0-LCA/PREREGISTRATION.md` | `80` | capture label only |
| `experiments/M-PHASE0-LCA/src/measure.py` | `93` | capture path only |
| `experiments/M133-blocker-audit/bar-card-audit.json` | `1025,1032,1041 (2),1044,1053 (3)` | copied scorecard text; no independent truth |
| `experiments/M141-capture-inventory/analysis.py` | `44,45,46` | three capture identifiers only |
| `experiments/M141-capture-inventory/capture-manifest.json` | `7846,7850,7959,7964,7970,7980,7984,8093,8098,8104,8114,8118,8227,8232,8238,12257,12273,12289` | capture identifiers only |
| `experiments/M141-capture-inventory/capture-segments.csv` | `138,139,140` | three capture identifiers only |
| `experiments/M141-capture-inventory/capture-stacks.csv` | `53 (3),54 (3),55 (3)` | capture identifiers only |
| `experiments/M141-capture-inventory/holdout-register.json` | `94,106,118` | three capture identifiers only |
| `experiments/SCORECARD-BASELINE/out/INPUT-MANIFEST.json` | `193,201,209` | three capture identifiers only |
| `experiments/SCORECARD-BASELINE/prepare.py` | `85,89,93` | three capture identifiers only |

That is **MEASURED 77** relevant token occurrences in **MEASURED 23** tracked
files. All path-only records copy the directory label; none measures the angle.

The only **MEASURED 3** unrelated bounded tokens in the tracked commit are:

* `docs/research/V-EYES.md:212` (`+10.26`, a visual-audit table value);
* `experiments/m61-ptc-high-iso/data/rollup.txt:13` (`10.26`, a rollup value);
* `experiments/M90-prnu/out/rho2-flat-on-ruler-cpl.txt:17` (`10.26`, a result).

These values have no relationship to the ruler angle.

M154's own script, JSON ledger, and this report are intentionally excluded from
the baseline counts. They are provenance records, not independent measurements.

### Supplemental shared-worktree census

`experiments/M154-m10-angle/out/working-tree-census.json` preserves a separate
**MEASURED rolling** scan of the shared worktree. It scanned **MEASURED
135,909** files and **MEASURED 129,236,216,365 bytes** with no suffix filter,
finding **MEASURED 396** bounded tokens in **MEASURED 210** files. Those
included **MEASURED 355** ruler-related tokens and **MEASURED 41** unrelated
tokens across untracked source snapshots, Python bytecode, and Rust libraries.

Every supplemental hit has a file, line, column, context, and classification in
that ledger. The scan was not atomic because other lanes were committing and
editing the shared tree while it ran. It is therefore an occurrence locator,
not evidence of absence and not part of the immutable repository counts above.

### Git origin

Git pickaxe history establishes:

* The capture identifier `ang10.26deg` first entered the repository in
  `f0f63f71d802ab38ebfc5a776b3186dfd7fc7960` at
  `2026-09-02T20:03:41-07:00`, **VERIFIED**, as an external path in
  `experiments/M-PHASE0-LCA/PREREGISTRATION.md`; it contained no derivation.
* The approximate phrase and `theta_ext` first entered in
  `90bced75910d77766bc5c0f4f3bac3dcf604bab0` at
  `2026-09-02T23:27:11-07:00`, **VERIFIED**, when the scorecard was
  preregistered.
* No pre-M154 repository file contains the README's rise/run inputs,
  **MEASURED by the full targeted scan**.

The external README is the only underlying numerical source found; later
repository copies add no independent measurement. M154 makes the nominal
arithmetic traceable by recording the exact source line and file hash, but
cannot retroactively add measurement uncertainty.

## Consequence for M10

This lane advances M10's design record only by resolving the origin question:

* `10.26 deg` is not an arbitrary constant; it is the rounded result of the
  recorded rise/run ratio.
* It remains ineligible as `theta_ext` because its uncertainty and
  camera-relative geometry are unbounded.
* M154 did not inspect a capture outcome, but the ruler unit was already burned
  by CURV/LCA before scorecard registration.

M10 therefore cannot advance to a physical-depth score from existing material.
A fresh registered ruler unit is required. Before any score output is seen,
measure its axial rise and lateral projection relative to the camera/sensor
coordinate frame, record endpoints and instruments, and provide bounds whose
propagated slope error is at most `2.5%` (**VERIFIED registered threshold**).
A later measurement of a reconstructed old setup cannot restore the already
burned unit.

Even after this angle blocker is closed, the repository still reports no
compatible physical-depth product or scored geometric-truth run
(`docs/proposals/2026-09-sota-scorecard.md:432`,
`docs/STATUS.md:932`). The flat-null and hidden synthetic arms also remain to
be run under the registered protocol.

## Defects for the orchestrator to correct

No orchestrator-owned file was edited.

1. `docs/proposals/2026-09-sota-scorecard.md:318-320` labels the three ruler
   stacks `HOLDOUT - QUALITY`, but CURV had already read outcomes from all
   three and LCA had read the f/11 stack before the scorecard commit. Proposed
   correction: mark all three **BURNED - DEVELOPMENT ONLY, NOT HOLDOUT** and
   register a fresh metrology-backed ruler unit for M10.
2. `docs/proposals/2026-09-sota-scorecard.md:402-403` says only the angle
   record may force a new metrology capture. Proposed correction: say the
   existing unit is already burned and its note also lacks a qualifying angle
   interval, so a fresh measured unit is mandatory.
3. `docs/proposals/2026-09-sota-scorecard.md:1041` names the burned three-stack
   unit as M10 input and calls it "10.26-degree." Proposed correction: replace
   it with a fresh untouched ruler unit whose camera-relative pose and
   uncertainty are frozen before scoring.
4. `docs/proposals/2026-09-sota-scorecard.md:1050-1051` leaves `x` ambiguous.
   Proposed correction: define `s` as ruler-tick arclength and use
   `z_true=s*sin(theta_ext)`, or explicitly define
   `x=s*cos(theta_ext)` as externally calibrated lateral projection before
   retaining `z_true=x*tan(theta_ext)`.
5. `docs/STATUS.md:932` says the ruler record says only "approximately
   10.26 deg." Proposed correction: say that the external README also records
   an about-`10 cm` run and about-`1.81 cm` rise, reproducing
   `10.259461685 deg` nominally, but records no instrument, coordinate
   definition, or uncertainty, and that the unit was already burned.
6. `docs/STATUS.md:5071-5073` says there is "no derivation" and calls the
   angle the single M10 blocker. Proposed
   correction: replace that claim with "the only underlying record gives
   about 10 cm run against about 1.81 cm rise, which derives 10.259461685 deg
   nominally, but gives no instrument, coordinate definition, or uncertainty;
   no qualifying interval exists; moreover, the old unit is burned and a fresh
   measured ruler unit is required."

## Reproduction

From the monorepo root:

```powershell
python projects/strehl/experiments/M154-m10-angle/analyse.py
```

The script reads only the external README, not any capture, writes
`experiments/M154-m10-angle/out/analysis.json`, independently reconstructs the
nominal and required intervals, scans the repository, and records Git
provenance. Its uniquely anchored source check was exercised with two planted
defects: changing the recorded rise to `1.80 cm`, and duplicating the exact
anchor line. Both make the check fail; the unmodified source passes.
