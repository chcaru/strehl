**NO — disqualified at step 1 by the absence of any same-site candidate with a matched, genuinely disjoint dark-and-flat calibration lineage.**

# M168 — can the existing archive support a cheaper same-resolution reference?

Status: **NO ARCHIVE-ONLY ROUTE; M135 ABSENCE FINDING INDEPENDENTLY CONFIRMED**

Target question: can a same-resolution independent reference physically commission an admissible comparative result from material already present under `D:\personal\macro` or `D:\edited\macro`?

## 0. Ruling

**VERIFIED — NO.** Same-site raw material exists, so the failure is not a lack of candidate pixels. The fatal fact is calibration lineage:

1. The only bona fide uniform flat-field series in the supplied archive contains 40 frames at each of nine `ISO 100` exposures from `0.004 s` through `0.2 s`.
2. The only in-scope dark series contains 22 frames at each of 23 settings. Its `ISO 100` exposures are `1 s`, `2.5 s`, `5 s`, and `10 s`.
3. Their `(ISO, exposure)` intersection is empty both exactly and under the M165 `0.0005 s` tolerance: `MATCHED_SETTINGS=0`.
4. Even ignoring that mismatch, no setting has enough frames for the currently commissioned M165 A/B/V calibration contract. Per optical state it requires three disjoint 32-frame flat groups and three disjoint 32-frame dark groups. The archive maxima are 40 flats and 22 darks at one setting; after the mandatory two dark settling exclusions, only 20 darks remain.
5. The archive contains no frozen A/B/V source assignment, moved-diffuser record, same-sitting temperature witness, focus-schedule record, held-out calibration block, or real pattern map. These are properties of the acquisition event and cannot be reconstructed by a later analysis.

M135 was therefore right about the combined fact it asserted. It was not merely searching for a higher-magnification M1 pair: the broader same-resolution candidates also lack qualifying disjoint calibration.

This finding proves that an **archive-only** same-resolution route cannot be physically commissioned today. It does not prove that every future same-resolution design must use all 1,602 frames in the current M1 request.

## 1. What counts as genuinely disjoint calibration

The current independently commissioned fixed-pattern boundary is M165, not a new rule invented by this lane. At minimum, a claim-bearing pair must have:

- non-overlapping dark and flat source frames for A and B;
- a never-fitted validation lineage V;
- matching body, raw mode, ISO, exposure, optical state, focus class and thermal class;
- separately identified flat states, with B and V moved or rotated;
- no source shared across lineages, optical states or sittings; and
- a passed held-out residual/coherence test.

M165 freezes 32 acquired dark frames and 32 flat frames per A, B and V group. Its map key includes sitting, optical state, lineage, temperature class and focus class. A historical subject pair cannot be retroactively given a same-sitting calibration by photographing flats and darks now.

This is not merely documentary strictness. If a fixed sensor field `F` occurs in both reference and output at the same detector coordinates, `Y1-Y2` cancels it from the noise numerator while `Cov(Y,R)` can count it as transferred scene signal. The resulting `Q_EIN` can be biased in exactly the favorable direction unless independent calibration, independent sensor support, or another separately commissioned control removes that path.

## 2. Independent archive census

A force-inclusive recursive census found:

```text
ROOT=D:\edited\macro FILES=387 BYTES=141333902406 ARW=0 DIRS=6
EXT=.avif COUNT=22
EXT=.jpg COUNT=3
EXT=.tif COUNT=362
HIDDEN_OR_SYSTEM_FILES=0

ROOT=D:\personal\macro FILES=10724 BYTES=487169829957 ARW=10509 ARW_DIRS=68
EXT=.ARW COUNT=10509
EXT=.dng COUNT=1
EXT=.log COUNT=1
EXT=.md COUNT=10
EXT=.png COUNT=2
EXT=.xmp COUNT=201
HIDDEN_OR_SYSTEM_FILES=0
```

`D:\edited\macro` contains no RAW calibration source. `D:\personal\macro` contains no JSON or CSV acquisition/calibration manifest and no hidden files omitted by the ordinary listing.

A full EXIF census found one camera-body key and one optical key across all 10,509 ARWs: `ILCE-7CM2`, `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`, `200 mm`. Of 362 edited TIFFs, 357 carry that same camera/optical key and five carry no camera metadata. There is therefore no provenance-bearing second-body or bare-lens arm hidden in the supplied roots.

### 2.1 Same-site candidates do exist

Direct EXIF reads identified plausible raw substrates:

| Candidate | Directly observed structure | Why it does not clear step 1 |
|---|---|---|
| Bee no-bracket ISO-100 group | Two 32-frame runs, `DSC00328–00359` and `DSC00584–00615`, `ISO 100`, `1.6 s`, fixed `FocusPosition2=57` | No true flat or dark exists at `ISO 100 / 1.6 s`; the two runs also use different lights. |
| M71 subject sweeps | Two 62-frame sweeps at `ISO 100 / 0.2 s`, one with CPL and one without | A true flat exists at that setting, but no matching dark exists; the optical states differ. |
| Calibration-grid families | Grid 1 has sw1/sw4/sw10; grid 2 has sw4/sw10, all `ISO 100 / 1 s` | One 22-frame dark group exists, but no uniform unresolved flat exists at 1 s and no A/B/V calibration partition exists. |
| High-resolution slide | 182-frame sw4 and 92-frame sw10 focus-bracket sequences at `ISO 100 / 1 s` | The sequences have the same missing true-flat calibration and no A/B/V calibration partition. |
| Paper no-bracket groups | Five frames per ISO/exposure setting at `0.125 s` and `0.5 s` | The README identifies visible paper texture and artifacts. At `ISO 100 / 0.125 s` a true flat exists but no matching dark does. |

The bee runs establish that M135 should not be paraphrased as saying there are no repeated same-site exposures. There are. What does not exist is the conjunction **same site + independent observations + matched disjoint calibration**.

### 2.2 The calibration sets have zero setting overlap

Direct ExifTool grouping produced:

```text
TRUE_FLAT_TOTAL=360
TRUE_FLAT ISO/seconds(count): 100/0.004(40), 100/0.008(40), 100/0.01666667(40), 100/0.03333333(40), 100/0.05(40), 100/0.07692308(40), 100/0.1(40), 100/0.125(40), 100/0.2(40)
DARK_TOTAL=506
DARK ISO/seconds(count): 100/1(22), 100/10(22), 100/2.5(22), 100/5(22), 1000/0.125(22), 1000/1(22), 1000/2.5(22), 1000/5(22), 160/0.125(22), 160/1(22), 160/2.5(22), 160/5(22), 2000/0.125(22), 2000/1(22), 2000/2.5(22), 2000/5(22), 400/1(22), 400/2.5(22), 400/5(22), 800/0.125(22), 800/1(22), 800/2.5(22), 800/5(22)
MATCHED_SETTINGS=0
MATCHED_ISO_EXPOSURE_WITHIN_0.0005S=0
MAX_FLAT_FRAMES_PER_SETTING=40
MAX_DARK_FRAMES_PER_SETTING=22
M165_REQUIRED_PER_STATE=flat_A32+flat_B32+flat_V32,dark_A32+dark_B32+dark_V32
```

This is already fatal before testing aperture, focal length, stabilization, focus schedule, temperature or diffuser independence.

### 2.3 Flat-named subjects are not substitute flat fields

The archive names several geometrically flat subjects: a dime, ruler, razor, battery and the fronto-parallel high-resolution slide. Their notes identify texture, text, dimples, scratches, edges or grid structure. They are signal-bearing subjects, not spatially uniform unresolved calibration fields.

I decoded the full embedded `JpgFromRaw` from `flat-sw4-cpl/flat-et1s-sw4-cpl/DSC00016.ARW` in memory without modifying the source. It visibly contains a high-contrast resolution chart. Its statistics were:

```text
JPG_FROM_RAW_BYTES=1629438 SIZE=7008x4672 MEAN=0.304314 SD=0.192699 P01=0.094118 P99=0.792157
```

The word `flat` in that path describes the chart plane. Counting it as a sensor flat would fit the chart itself into the gain map and leak the answer.

## 3. Ordered decision

| Step | Verdict | Evidence |
|---:|---|---|
| 1. Same-site pair with genuinely disjoint calibration | **FAIL — FATAL** | Candidate pairs exist, but true flat/dark settings have zero overlap and no candidate has A/B/V calibration lineage. |
| 2. Sufficient reference power | **NOT RUN** | The brief required an early stop after a fatal step 1. No post-outcome power threshold was invented and no candidate pixels were scored. |
| 3. Cross-fit independence | **NOT REACHED** | Some file-level splits are possible, but they reuse the same detector footprint. No dither/footprint lineage or admitted map establishes independence from stable sensor structure. |
| 4. Fixed-pattern calibration path | **FAIL** | This is the same physical blocker exposed at step 1. The M165 map cannot be built from these files. |
| 5. Admission rule | **NOT REACHED** | Archive-only physical commissioning is already impossible. |

The current M135 synthetic gate of minimum reference-repeat coherence `>=0.50` is not silently adopted as a new M2 power rule. That question becomes legitimate only after an eligible calibrated pair exists and a rule is frozen before its pixels are read.

## 4. Commercial implication

The archive does **not** remove the need for new owner capture. The calibration problem cannot be repaired after the fact because the accepted map requires same-sitting thermal, focus, optical-state and diffuser lineage.

The same missing deterministic-pattern map therefore blocks the cheaper route too. In that specific sense it is no cheaper: it cannot reuse the existing archive and bypass the calibration acquisition.

This audit does **not** prove that every frame in the 1,602-frame M1 request is necessary for every conceivable future same-resolution protocol. A newly designed narrower protocol might have a different count, but it would still require new paired subject, dark, flat and validation captures and separate commissioning. Designing that instrument is outside M168 scope.

## 5. Reproduction

The archive was read only. Core commands were:

```powershell
$all=Get-ChildItem -LiteralPath "D:\personal\macro" -File -Recurse -Force
$raw=@($all|Where-Object{$_.Extension -ieq ".ARW"})
"ROOT=D:\personal\macro FILES=$($all.Count) BYTES=$(($all|Measure-Object Length -Sum).Sum) ARW=$($raw.Count) ARW_DIRS=$(($raw|Group-Object DirectoryName).Count)"

$fj=(& exiftool -j -n -ISO -ExposureTime "D:\personal\macro\flat-fields\flat-fields")|ConvertFrom-Json
$dj=(& exiftool -j -n -ISO -ExposureTime "D:\personal\macro\requests\6-11-extended-dark-frames")|ConvertFrom-Json
```

Candidate metadata was read directly with ExifTool from the bee, M71 sweep, calibration-grid and high-resolution-slide directories. No wall-clock result was collected or used.

## 6. What would make this ruling false

Produce an archive path, omitted from the two roots audited here, containing all of the following for one same-site candidate: matched raw darks and spatially uniform flats; non-overlapping A/B plus held-out validation sources; contemporaneous body/temperature/focus/optical-state records; and enough source hashes to bind those calibrations to the candidate captures. No such path or record exists in the supplied roots.
