# M185 — independent verification of the development-flat retraction

## Verdict

**SAFE WITH AMENDMENTS.** Do not ask the owner to shoot the third/development-flat sitting now. The exact M152 replacement text is not safe to paste: it overstates adoption, scopes the holdout classification too narrowly, treats one input gate as sufficient commissioning, and says “either” after three heterogeneous conditions. The existing paper-flat burst is a strong but not yet registered replacement candidate.

## Claims tested

1. The development-flat role is checker commissioning rather than noise, PRNU, or natural-detail estimation.
2. M166 registers the 95% planted-selector and 1% fixed-mean controls.
3. A uniform field supplies the role.
4. M166's transfer sites need all-frame/all-RGB common-TIFF plant headroom.
5. The frozen identity is coffee bubbles.
6. The paper-flat stack is indeterminate in M141.
7. Twenty frames are admissible to the relevant construction.
8. M181's exact 1,768/1,768 result and term summaries exist and reproduce.
9. Coffee is a distinct 19-frame, zero-site capture whose median band ratio is 5.279854.
10. The selected burst's EXIF is ISO 100, f/5.6, 200 mm, 1/125 s and names the 100 mm macro plus 2x converter.

## Q1 — citation audit

| claim | cited location | result | direct reading |
|---|---|---|---|
| 1 | `M166-bar-definition-repairs.md:242-285` | **MISS** | Defines the paired transfer veto and says the plant is applied to the **scored** flat stacks. It never assigns the development flat, nor excludes noise/PRNU/detail purposes. The flat commissioning role instead follows from scorecard `:1243-1251,1347-1363` and M152 `:277-287`; the paired-transfer use is implicit, not stated. |
| 2 | scorecard `:1360-1363` | **VERIFIED** | Exactly `>=95%` planted 32-px selector above `Q=1.25`, fixed mean `<=1%` failures, plus the separate shifted-edge control. |
| 3 | none supplied | **VERIFIED substantively** | M152 `:285-287` expressly asks for broad, truly featureless ground and avoidance of 20–60 px texture. |
| 4 | M166 `:255-263` | **VERIFIED** | Every source common TIFF, all R/G/B, must remain in `[0,65535]` after the deterministic plant. |
| 5 | `m4-freeze.json:35-38`; scorecard `:1347-1349` | **VERIFIED** | Both name coffee bubbles; freeze line 38 also forbids cross-capture/category substitution. |
| 6 | `holdout-register.json:371-375` | **VERIFIED, bad provenance pointer** | The row says `INDETERMINATE — DO NOT ASSUME CLEAN`. Its embedded scorecard pointer `:299-303` is stale and now discusses high-frequency licensing; the current literal holdout rule is scorecard `:610-611`. |
| 7 | M166 `:213-226` | **MISQUOTED** | It defines generic matrices, one-hots and mean, but line 221 limits those matrices to medication/bee/foam. It neither says “no minimum” nor applies this construction expressly to the development flat. No minimum appears elsewhere, and the registered coffee control itself has only 19 frames, so 20 is not disqualified. |
| 8–10 | no file:line supplied | **VERIFIED below** | Confirmed from committed artifacts and direct execution/EXIF. |

## Q2 — downstream role

The development flat feeds the full-M4 checker's flat arm: an untouched/fixed mean must remain a null and a deliberately spatially varying selector must produce 20–60 px patchwork. The M152 input selector therefore rejects scene structure in exactly that band. A uniform field is appropriate; texture is harmful, not required. Noise calibration is a separate frozen artifact, and M4 does not consume this capture as PRNU calibration or natural-scene detail truth. The shifted-correspondence control consumes separate structured edge captures.

M166's `g/r` transfer veto is evaluated on the actual scored medication/bee/foam stacks. A development capture is logically needed to commission that checker before protected outputs are read, but M166 never expressly binds this development flat to that response. There is no optical-geometry, focus, CPL, or exposure-match requirement for the development flat. Twenty-frame Dirichlet, one-hot, and uniform arrays are mathematically valid. The unrun issue is empirical: this burst has not yet demonstrated the selector-positive/fixed-mean-null or paired-transfer response on exact common TIFFs.

## Q3/Q4 — conditions, holdout, and burn

- **Classification is required.** M152's validator rejects a `DEVELOPMENT_NOT_HOLDOUT` capture absent from M141's explicit-not-holdout rows. M181 bypassed that admission layer by rebinding `capture_files`; it did not establish registration.
- **A governing successor is required.** Coffee is hash-frozen and the scorecard still names it. A mere side manifest cannot override that. Adopt a versioned scorecard plus census/freeze successor naming the exact 20 files and sites (and implementing segment selection) before commissioning.
- **RGB headroom is required for every site used by M166's transfer plant**, but headroom alone is not commissioning.
- **Missing fourth condition:** run and pass the registered flat controls (`>=95%` selector, `<=1%` mean) and an adopted paired-transfer checker response control. No M4 matrix/plant/scorer implementation currently exists.

`INDETERMINATE` is not `HOLDOUT` (scorecard `:610-611`), but it is “do not touch” until classified. The conservative unit is the whole same-paper 2026-08-23 sitting: 360 flats plus two 62-frame sweeps = **484 frames**, not the selected 20. M71 already decoded and published outcomes from all 484, so the unit is already de facto burned. Formal classification as burned development-only loses no clean evidence: M164 rejects it as M1 truth (converter-on, IBIS-on, wrong configuration), and it has no registered protected role.

## Q5 — artifact and independent run

Committed artifact (commit `ae1869e1`): `experiments/M181-m4-feasibility/out/development-flat-resolution.json`:

```text
"eligible_tile_count": 1768
"initial_candidate_count": 1768
band min/median/p95/max = 0.629432166/0.746325992/0.833854556/0.956877856
signal minimum = 62.121293265
low maximum = 0; high maximum = 0
```

Direct unmodified-predicate rerun, with only the explicit-file provider rebound:

```text
flat m185-independent-flat-check: frame 20/20 survivors=1768
census.py_sha256=640a9b1433d2f6d0c5eee208cc69398abafd103688451ce3e7f4e4a74d3e0539
eligible=1768/1768
processed=20/20 all_frames=True
first=DSC00103.ARW last=DSC00122.ARW
elapsed_seconds=6.533
```

`verify.py` returned `GREEN: 7 checks`; M152 returned `Ran 16 tests ... OK`. Direct EXIF grouped all 20 as ISO 100, f/5.6, 200 mm, 0.008 s, lens `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`. Coffee's committed M152 row is 19/19, all 1,768 band failures, min/median `1.091006/5.279854`, joint zero (with 176 additional high-rail failures).

## Q6 — paste-ready replacement

> **RETRACTION — strike Item 3; do not shoot a separate development flat now.** Coffee bubbles and the patterned slide flats remain ineligible. The existing 20-frame `flat-fields\flat-fields\DSC00103.ARW`–`DSC00122.ARW` burst is a strong replacement candidate: M152's unchanged predicate retains `1,768/1,768` raw tiles, but this is not yet the registered commissioning population. Before using it, classify the entire 484-frame paper-flat subject/session as burned development-only/non-holdout; adopt a versioned scorecard and M152 census/freeze successor that expressly replaces `coffee-bubbles` and names the exact 20 files plus a deterministic site-selection/fallback order; on exact campaign common TIFFs, retain and freeze at least 100 sites after M166's all-frame/all-RGB plant-headroom gate; then pass the registered M4 flat controls (`>=95%` planted-selector detection and `<=1%` fixed-mean failures) and a separately adopted paired-transfer response control. If this burst fails for a capture-content reason, test a pre-registered order of the other already-measured paper-flat bursts before asking for another sitting. Restore a frozen capture sheet only if no existing burst can supply 100 usable sites; software, manifest, or classification failures are not reasons to reshoot.

Changes: explicit retraction; “candidate” instead of unsupported “leading replacement”; whole 484-frame burn unit; scorecard plus census successor instead of a vague manifest; actual commissioning rather than headroom alone; no “either” off-by-one; existing-burst fallback; and reshoot only for demonstrated capture-content failure.

## Commands run

```text
python -B experiments\M181-m4-feasibility\verify.py
→ GREEN: 7 checks: source-freeze, prohibited-path, inventory-integrity, rig-audit, development-resolution, probe-accounting, verdict-reduction

python -B experiments\M152-site-census\test_census.py
→ Ran 16 tests in 0.041s / OK

git grep -n -- M4-TRANSFER-V1 -- '*.py' '*.rs' '*.ps1' '*.js' '*.ts'
→ no output; exit 1
git grep -n -- 15240420260904 -- '*.py' '*.rs' '*.ps1' '*.js' '*.ts'
→ no output; exit 1
```

## Defects

1. **High:** the prescribed text omits actual commissioning and would suppress capture after only a rail check.
2. **High:** it does not amend the scorecard/frozen coffee identity; a successor side manifest alone is insufficient.
3. **Medium:** it risks burning/classifying only 20 frames rather than the 484-frame subject/session unit.
4. **Medium:** “either check” has no coherent referents, and failure of the named burst should fall back to other existing bursts before a shoot.
5. **Low:** “leading replacement” is unsupported; another burst also has 1,768 raw-eligible sites and none has common-TIFF/commissioning results.

## Gaps

Common TIFFs, RGB plant headroom, the exact selector/null response, and paired-transfer checker commissioning do not exist. The retraction is therefore a safe instruction to **defer shooting**, not proof that this exact burst has completed commissioning.