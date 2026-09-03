# COVER — exact cover-mode evidence and default decision

**Status: CLOSED — keep `scale` as the default.**

`crop` passes its necessary mechanism test against an external decoder:
rawpy/LibRaw predicts all 24,580,566 serialized samples exactly (max 0 DN,
RMS 0 DN, 0% different), while `scale` changes 98.1462% of the external
overlap. It nevertheless fails the shipping gate. On `109MSDCF`, the
seven-band crop carries a boundary-local level excess as large as 2.61% and
does not remain within 0.1% of the two-band control until a 256 px inset. That
is twice the preregistered maximum, and retaining only the post-inset rectangle
would leave 64.60% of the original plane. The second subject's scene structure
also defeats the registered specificity control, so this lane did not
establish any finite all-stack safe inset.

No sharpness, acuity, SFR, gradient, or visual-quality statistic appears in
this decision. The positive result is exact integers and the negative result
is fixed geometry plus absolute green-channel levels.

## 1. Frozen predicates, capture governance, and provenance

The authoritative predicates were committed before any comparison or treatment
render:

* preregistration commit:
  `c40a965e15acabd1c36da05559eb6a568dc524df`;
* `experiments/cover-default/preregistration.md` SHA-256:
  `D69F48B8DD11100901FC4FE04A24A90CB82EFC58C8D3B574509B7B3DA191BDDF`;
* `experiments/cover-default/audit.py` SHA-256:
  `7ADDB1254D7CD946183AA02F64016E67FF72E250D6E1746EDDB57297A9EE2A4D`.

The first Q1 compared two strehl-produced paths and was later recognised as an
internal differential rather than the requested transparency test. Before any
external decode or external-to-render comparison, the corrected predicate was
committed as
`fdea80e903d1ddc9c6f2576968446fa19a9295f6`
(`external-decode-preregistration.md` SHA-256
`C2A74BE71149CF8CD79BA6F7C921BF3D5AE6397B276675BCA5703C212A7DC640`).
The independently implemented checker was then frozen before measurement as
`a79ad2fa41ceb262ffd5f9ef3637394463943558`
(`external_decode.py` SHA-256
`A24DC1DA706077023637A653CBF3CC747948EBBC3B34CC6B844E583AA8B84B93`).
Both commits remained ancestors of the post-measurement branch.

`git merge-base --is-ancestor c40a965e HEAD` returned 0 after measurement. The
shared branch advanced while this lane ran, so later `HEAD` is not used to
identify the pixel-producing executable. The executable identifies itself and
is pinned by content:

```text
build command:
  CARGO_BUILD_JOBS=8 RAYON_NUM_THREADS=8
  RUSTFLAGS=--cfg cover_default_audit_20260903
  cargo build --release -p strehl-cli -j 8
    --target-dir D:\strehl-out\cover-default\target

observed build line:
  Compiling strehl-cli v0.0.0 (...)
  Finished `release` profile [optimized] target(s) in 1m 18s

executable:
  D:\strehl-out\cover-default\target\release\strehl.exe
  strehl 0.0.0 (4e5278870a5e)
  SHA-256 1AC423529D5AAD88B7141801E47DCD612FCA8061558578A88592DB715CE81A0F
  9,913,344 bytes
```

Only captures classified as non-holdout in
`docs/proposals/2026-09-sota-scorecard.md` were decoded. The measured inputs
were `109MSDCF`, `113MSDCF`, `coffee-bubbles`, and
`flat-on-ruler-cpl`. `D:\personal\macro` was read only. The 299-frame
`bee-1-cpl` performance holdout was not opened. All outputs and the one copied
diagnostic RAW were written beneath `D:\strehl-out\cover-default`. Rust,
Rayon, OMP, OpenBLAS, MKL, and NumExpr were capped at eight threads.

## 2. Harness commissioning

Before any result was read:

```powershell
python -B experiments\cover-default\audit.py commission
```

The fixed external predicates all fired:

| arm | max abs | RMS | differing fraction / result |
| --- | ---: | ---: | --- |
| one-value `+4096` defect | 4096 DN | 42.6666667 DN | 1/9216 |
| improved `+1024` defect | 1024 DN | 10.6666667 DN | 1/9216 |
| restored array | 0 DN | 0 DN | 0/9216 |
| correct crop origin | 0 DN | 0 DN | 0/1440 |
| left/right one-pixel origin plants | 3 DN | 3 DN | 1440/1440 |
| up/down one-pixel origin plants | 120 DN | 120 DN | 1440/1440 |
| 2% outer 16 px border plant | — | — | safe inset 16 px |
| improved 0.05% border plant | — | — | safe inset 8 px |
| unplanted border null | — | — | safe inset 8 px |

The independent identity-geometry solution was
`k=0.9974380871050387`; its closed form was
`0.9974380871050385`, a `2.22e-16` difference. Reducing the externally
specified support margin from 3 px to zero improved `k` to exactly 1.

This commissions worsening, improvement, restoration, origin bookkeeping,
the 0.1% border threshold, and the independent geometry port. It does not ask
strehl to state the expected answer.

## 3. Q1 — external LibRaw confirms Crop identity and Scale resampling

### 3.1 Input and invocation

The full-stack reference, `109MSDCF\DSC00020.ARW`, was copied into a private
one-frame directory. Source and copy both had SHA-256
`77AAEC0B9958B97E8B712332E2A3C67013373623B8BCF52CC5C88B912F0070CA`.
The explicit sidecar was produced by:

```powershell
strehl.exe align D:\strehl-out\cover-default\one-109-ref `
  --reference 0 --resampler catmull-rom `
  --out D:\strehl-out\cover-default\one-109-ref.warpmap.txt
```

It records exact f64 identity bits (`a=1+0i`, `b=0+0i`) and has SHA-256
`4C858562AF44E0646D9E45E445DEBAC17C6C9E4FEC28C325B9E653EB391E6C05`.
Independent geometry gives `k=0.9974380871050387`, an implied 0.256849%
upsample, and crop rectangle `(x=5,y=4,w=3506,h=2337)`.

Every arm first cleared inherited `STREHL_*`, then set
`STREHL_FULLRES_GATHER=1`, `STREHL_DEFECT=off`,
`STREHL_FIX_CA=off`, and the thread caps. All used:

```text
strehl.exe stack <one-frame-dir> --merge pyramid
  --pyramid-bands 7 --resampler catmull-rom --out <arm.tiff>
```

The direct arm set `STREHL_ALIGN=0`; the other arms set the explicit
`STREHL_WARPMAP`. No-fit additionally set `STREHL_COVER=0`; Crop and Scale
passed `--cover crop` and `--cover scale`. An initial command also passed
`--photometric off`; pyramid correctly refused it with exit 1 before an
evidence file was accepted. Those paths were removed and all four arms were
rerun without the estimator-only flag.

| arm | dimensions | bytes | SHA-256 |
| --- | ---: | ---: | --- |
| direct | 3516x2344 | 49,450,019 | `447F1A6EF5212CECCE4890C0823C50E3D66DC65ED23733BC957F0217C31BFCF4` |
| no-fit | 3516x2344 | 49,450,019 | `5836AFBBE435760B366E042345D987F96C36CD31ACEE0C3C0AB18D5A2999E436` |
| Crop | 3506x2337 | 49,162,127 | `9033579443C98A769770F71A239104E3529F53FB152308080A7EE4AC1C72C972` |
| Scale | 3516x2344 | 49,450,019 | `23A385AC2E5C0C70B1F436C3D9E5F3C13E905FB8DE9A177AA1D988DAFDBE2FC2` |

### 3.2 Original internal differential

Each row was emitted by:

```powershell
python -B experiments\cover-default\audit.py compare `
  <reference.tiff> <candidate.tiff> --origin <x> <y>
```

| comparison | origin | samples | max abs | RMS | differing fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| planted wrong direct→Crop | (6,4) | 24,580,566 | 6235 DN | 195.437549 DN | 97.199841% |
| improved direct→Crop | **(5,4)** | 24,580,566 | **0 DN** | **0 DN** | **0%** |
| no-fit→Crop | **(5,4)** | 24,580,566 | **0 DN** | **0 DN** | **0%** |
| direct→Scale | (0,0) | 24,724,512 | 8656 DN | 215.449413 DN | 98.146321% |

The wrong-origin plant fired strongly and correcting only the externally known
origin returned every statistic to zero. These rows establish that Crop is the
exact serialized window of the direct and unity-scale no-fit arms, while Scale
is not a pass-through. They do **not** establish transparency to the RAW:
direct, no-fit, Crop, and Scale all share strehl/rawler decode, pyramid, and
output code. They are retained as a commissioned internal differential, not
promoted to external identity evidence.

### 3.3 Corrected external-decoder result

After the amended predicate and checker were committed, and after the host's
exclusive quiet window expired, commissioning ran before the external result:

```powershell
python -B experiments\cover-default\external_decode.py commission
```

All frozen hashes matched. Three literal RGGB encoder fixtures produced exactly
`(32768,32768,32768)`, `(65535,0,32768)`, and
`(65535,65535,65535)`; R/B-order and pre-black-gain plants moved them. A
candidate-side centre-green XOR `0x8000` produced exactly one difference,
max 32768 DN and RMS 6.60927763384 DN. Replacing it with XOR `0x0001`
improved max to 1 DN and RMS to 0.000201699147 DN; restoration returned max,
RMS, and differing fraction to zero. Thus both the render-side comparison and
its improvement direction fired before the result was read.

The measurement command was:

```powershell
python -B experiments\cover-default\external_decode.py measure
```

It copied rawpy's visible mosaic inside each of two independent LibRaw
contexts. Both copies were `uint16` RGGB `4688x7028`, had black levels
`[512,512,512,512]`, container white 16383, camera white balance
`[2930,1024,1518,1024]`, and SHA-256
`894A15258713A9B260DB20792CB847D70898CEBECBAEA0871790D242BC659830`.
The fixed float32 gains were
`[2.861328125,1.0,1.482421875]`. The independently encoded external
`3514x2344` overlap had SHA-256
`2BC36C76D8075F6532105C15675F6CA416E3D055B82955B35408D472E15A7B0C`;
its `(5,4,3506,2337)` prediction had SHA-256
`81F8B29B01592F5345581A7081183179CA247EAB244A05D984EB7FBBD96F0C76`.

| external comparison | samples | max abs | RMS | differing |
| --- | ---: | ---: | ---: | ---: |
| planted Crop origin `(6,4)` | 24,580,566 | 6235 DN | 195.437548515 DN | 23,892,271 (97.1998407%) |
| **Crop origin `(5,4)`** | **24,580,566** | **0 DN** | **0 DN** | **0 (0%)** |
| direct, rawpy overlap | 24,710,448 | 0 DN | 0 DN | 0 (0%) |
| no-fit, Crop window | 24,580,566 | 0 DN | 0 DN | 0 (0%) |
| Scale, rawpy overlap | 24,710,448 | 8656 DN | 215.440799045 DN | 24,252,367 (98.1462052%) |

Crop's R, G, and B channels were separately exact: each had max 0 DN, RMS
0 DN, and 0 of 8,193,522 samples different. Fixing only the planted origin
improved every registered statistic to zero; the Scale positive arm remained
strong. This establishes the end-to-end claim for this frozen reference:
LibRaw sensor integers, independently encoded without importing strehl, match
Crop bit-for-bit, while Scale resamples them.

An independent read-only verifier reimplemented the calculation inline from
rawpy, NumPy, tifffile, and the production arithmetic without importing the
checker or any repository Python module. It reproduced both expected-array
hashes and every aggregate number above, and confirmed no strehl, rawler,
render, build, or cargo path executed. It also checked the only potentially
different green-black ordering: all green sites in this RAW exceed black
(minima 553 and 546), so the two expressions differ at zero of 8,236,816
quads. The Q1 pyramid arm itself deinterleaves and clamps each site before
forming green, matching the preregistered construction.

## 4. Q2 — measured `k` and what “deeper” does and does not mean

`audit.py cover-scale` parses the serialized f64 bit patterns rather than the
human-readable decimals and independently tests all four plane corners with a
3 px support margin.

```powershell
python -B experiments\cover-default\audit.py cover-scale <warpmaps...>
```

| stack | frames | ref | `k` | `1/k - 1` | crop `(x,y,w,h)` | retained plane pixels |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| coffee-bubbles | 19 | 9 | 0.9886656557 | 1.146428% | 20,14,3476,2316 | 97.6814% |
| 109MSDCF | 22 | 11 | **0.9870480668** | **1.312189%** | 23,16,3470,2312 | 97.3444% |
| 113MSDCF | 63 | 31 | 0.9808883168 | 1.948406% | 34,23,3448,2298 | 96.1415% |
| flat-on-ruler-cpl | 79 | 39 | 0.9706671813 | 3.021923% | 52,35,3416,2274 | 94.1473% |

The 109 and ruler render banners printed 0.9870 and 0.9707 respectively, within
the registered `5e-5` print tolerance. The documented `0.9870 @ 22` claim is
reproduced.

The preregistered product-style prefix series did **not** confirm a monotone
depth law:

| 113MSDCF prefix | selected reference | `k` | implied upsample |
| ---: | ---: | ---: | ---: |
| 8 | 4 | 0.9789140578 | 2.154014% |
| 16 | 8 | 0.9798515712 | 2.056274% |
| 32 | 16 | 0.9802032051 | 2.019662% |
| 63 | 31 | 0.9808883168 | 1.948406% |

Here `k` rises as frames are added. This does not prove that additional frames
improve coverage: the product changes the middle reference, and therefore the
gauge, at every depth. It does refute the unqualified claim that the product's
`k` necessarily falls as a stack deepens.

A post-registered mechanism check held the full 63-frame map and reference 31
fixed, then added symmetric placements. It produced:

| frames included | `k` | implied upsample |
| ---: | ---: | ---: |
| 1 | 0.9974380871 | 0.256849% |
| 3 | 0.9967211794 | 0.328961% |
| 7 | 0.9958860288 | 0.413097% |
| 15 | 0.9938448839 | 0.619324% |
| 31 | 0.9895514550 | 1.055887% |
| 63 | 0.9808883168 | 1.948406% |

That conditional statement is geometric: with one fixed gauge, adding coverage
constraints cannot increase the maximum feasible `k`. It is not interchangeable
with the changing-reference product series.

The documented `0.9321 @ 299` value was **not freshly verified**. Its named
capture is a performance holdout. Prior BUILD-CROP provenance reports 0.9236
from a different sidecar/run, so neither value is adopted here as a fresh
measurement.

Map hashes for the four-stack table, in row order, were
`D481B9E216F77EA0A2BA3D708E49AB617C146CAEDCCCC92866945BDAF65CA894`,
`C32FA2C55A9BE4676E66B63D66C147BDAE3AEE436EB831BA45BF6A3F2EB1259E`,
`782529FEEE718668C8C6169B29378482B72291B9ABB83BA968119ADB0B9EBDEA`,
and `50D74F016ACD60B71227E20CD15303FB1D75B4FF54ECCC2D86D3A0B12A6EAA82`.

## 5. Q3 — border profile

### 5.1 Render arms

For `109MSDCF` and `flat-on-ruler-cpl`, four renders used the same explicit
Catmull-Rom sidecar per subject:

```text
clear every inherited STREHL_*
set STREHL_WARPMAP=<subject sidecar>
set STREHL_FULLRES_GATHER=1
set STREHL_DEFECT=off
set STREHL_FIX_CA=off
set all thread variables to 8

strehl.exe stack <capture> --merge pyramid
  --pyramid-bands <2|7> --resampler catmull-rom
  --cover <crop|scale> --out <arm.tiff>
```

The 109 sidecar SHA-256 was
`C29CAB9C6F944F4D03C4402998E54AAD4D4221CC450AC4BEF42A453DE848434D`;
the ruler sidecar was
`50D74F016ACD60B71227E20CD15303FB1D75B4FF54ECCC2D86D3A0B12A6EAA82`.
Every render exited 0.

| subject/mode | b2 SHA-256 | b7 SHA-256 |
| --- | --- | --- |
| 109 Crop | `02C1470ED0750248EFB5D321F05205CF1F1BD502931D2E50C0B65C46FFC2EC34` | `B2489C692AA924AEF230B21388407B902845219851C54FCA892E2DB362A0A83D` |
| 109 Scale | `23EBAA7DE115D1294DC7A2220EF371F54E4B6CCB5B3BE7495B31737875C12E47` | `F9101E47F21726125EB0D46A12B0415DC439EDBC30FA3DD2CA47AACCAAD4B684` |
| ruler Crop | `2516100269E3C702AF4B81240C219F97F74F3B82D68DF2FD84AF99039DA0AF11` | `7D04469B257EBE153422DA754A9E3339E8E08C1999EDC1A07EA0DB33F84EC1A3` |
| ruler Scale | `43C4144D3FCDD122EABAB8E048CD490D59627A531CD177FD2D56C715AF30CA75` | `0342CBCCFBB8B65279D89E1D8A28945E1227345504034BC889593E53C4D90746` |

### 5.2 Registered profile

For each arm:

```powershell
python -B experiments\cover-default\audit.py border `
  <bands7.tiff> <bands2.tiff> --threshold 0.001 --deep-start 768
```

The table reports the preregistered
`100 * ((mean_G(b7,d)/mean_G(b2,d))/R_deep - 1)`:

| inset annulus | 109 Crop | 109 Scale control | ruler Crop | ruler Scale control |
| ---: | ---: | ---: | ---: | ---: |
| 0–2 | +0.2695% | -0.0466% | +8.5878% | -2.1090% |
| 2–4 | +1.5719% | -0.0393% | +7.5920% | -2.3512% |
| 4–8 | +2.5450% | -0.0331% | +5.9397% | -2.6567% |
| 8–16 | **+2.6106%** | -0.0472% | +6.1955% | -1.4234% |
| 16–32 | +2.5074% | -0.0647% | +7.0256% | +1.0483% |
| 32–64 | +2.3850% | -0.0320% | +4.4328% | +0.3204% |
| 64–96 | +2.0988% | -0.0255% | +1.9894% | -0.1565% |
| 96–128 | +1.6906% | -0.0340% | +1.1980% | +0.2239% |
| 128–160 | +1.3093% | +0.0003% | +0.5249% | -0.0713% |
| 160–192 | +0.7887% | -0.0267% | +0.8766% | +0.2550% |
| 192–256 | +0.2808% | -0.0146% | -0.4635% | -0.0867% |
| 256–320 | +0.0343% | -0.0109% | -0.0014% | -0.0423% |
| 320–384 | -0.0053% | -0.0098% | -0.1592% | -0.0393% |
| 384–448 | -0.0041% | -0.0037% | -0.0741% | -0.0435% |
| 448–512 | -0.0077% | -0.0071% | +0.0501% | +0.0424% |
| 512–640 | -0.0044% | -0.0040% | -0.2162% | -0.0023% |
| 640–768 | -0.0039% | -0.0004% | -0.5645% | -0.2486% |
| 768+ | 0 by definition | 0 by definition | 0 by definition | 0 by definition |

The deep ratios were 0.9999192004 (109 Crop), 0.9999167020 (109
Scale), 0.9998628928 (ruler Crop), and 0.9987508396 (ruler Scale).

On 109 the specificity control is clean: Scale's registered safe inset is the
minimum 8 px, while Crop's is **256 px**. The effect is above 0.1% throughout
0–256 px, peaks at +2.61%, and then stays within threshold. A 256 px inset
reduces the 3470x2312 crop to 2958x1800, only **64.6047%** of the original
3516x2344 plane (66.3672% of the emitted crop).

On the ruler the algorithm returns 768 px for both Crop and Scale. The Scale
arm has no black-fill boundary, yet its band-depth ratio exceeds 0.1% in
multiple annuli. The structured scene therefore violates this profile's
specificity requirement at the registered threshold. **The ruler's 768 px is
not admitted as a pure black-fill reach.** It cannot be used to rescue Crop,
and it also prevents claiming that 256 px is safe across stacks.

The actionable safe-inset statement is consequently narrow but decisive:
**256 px is the smallest evidenced safe inset on 109; no finite general safe
inset was validated.** Crop should not ship as the default until the uncovered
fill/pyramid interaction is repaired and the profile passes a second,
scene-independent specificity control.

## 6. Q4 — product decision and freeze handling

The preregistered decision gates resolve as follows:

| gate | result |
| --- | --- |
| Crop exact and Scale measurably changes samples | **PASS** |
| outer 0–16 Crop ring within 0.1% on every stack | **FAIL** — up to +2.61% on admitted 109 profile |
| safe inset at most 128 px on every stack | **FAIL** — 256 px on 109; second stack not specific |
| at least 80% of original pixels after inset | **FAIL** — 64.60% on 109 |
| default flip handled deliberately in freezes/goldens | **NOT PREPARED**, because no flip is licensed |

Real focus stackers commonly crop, and stable nominal dimensions are not by
themselves a reason to resample. That product convention cannot overrule a
measured defect in this implementation: Crop happens after the full-plane
pyramid has already transported the uncovered-fill boundary inward.
`DEFAULT_COVER_MODE` therefore remains `Scale`.

The fixture audit found three 3516x2344 / 49,450,019-byte freeze rows and one
committed warp-map fixture; there is no separate image-golden fixture under
`crates/strehl-cli/tests/data`. None of the registry rows records `--cover`.
Only the aligned sidecar row currently reaches cover fitting; the two
alignment-off rows are specificity controls.

That audit exposed a hermeticity bug independent of the default decision:
`RENDER_ENV` did not clear ambient `STREHL_COVER`. Before the fix, running the
freeze under `STREHL_COVER=crop` returned exit 101: the unaligned row held, but
the sidecar row moved from expected
`E600A506F6D05A84A21C9DF93E4EB82AED98C8098EAF956BCF0E25985F3D4CB2`
at 49,450,019 bytes to
`C3B3B05C7BAE3B688C8C28CE3F711387207FF83E66FE758F41D5B35F9CD76E9D`
at 48,875,075 bytes. `STREHL_COVER` is now cleared with the other render
inputs. Under the same planted ambient value, the release freeze test passed
all three rows twice, bit-for-bit. No baseline moved.

A future default flip would still need either an explicit `scale` field/flag
for legacy freezes or a deliberate Crop rebaseline. Clearing an ambient
variable makes today's invocation hermetic; it does not pin tomorrow's
default.

## 7. Verification and limitations

Commands read to completion:

```text
python -B experiments\cover-default\audit.py commission
  -> COMMISSIONED

python -B experiments\cover-default\external_decode.py commission
  -> COMMISSIONED; literal encoder, candidate mutation, improvement,
     restoration, and frozen-input controls all passed

python -B experiments\cover-default\external_decode.py measure
  -> PASS; rawpy repeat and wrong-origin controls passed,
     Crop/direct/no-fit exact, Scale positive arm detected

independent inline rawpy/NumPy/tifffile reimplementation
  -> exit 0; reproduced mosaic/prediction hashes and every Q1 aggregate
     without importing the COVER checker or a repository module

rustfmt --edition 2024 --check crates\strehl-cli\tests\byte-freeze.rs
  -> exit 0

cargo test -p strehl-cli --test byte-freeze --
  --skip the_frozen_renders_still_produce_their_recorded_bytes
  --test-threads=1
  -> 4 passed

STREHL_COVER=crop cargo test --release -p strehl-cli
  --test byte-freeze
  the_frozen_renders_still_produce_their_recorded_bytes --
  --test-threads=1
  -> 1 passed; all three rows reproduced twice
```

`cargo fmt --all -- --check` was also attempted and failed on unrelated,
pre-existing formatting differences in files including
`crates/strehl-cli/build.rs`; the assigned Rust file passes direct `rustfmt
--check`.

Verified here: the corrected Q1 transparency result against two copied
rawpy/LibRaw decodes; its per-channel and cross-path exact integers; the
candidate-side defect, improvement, restoration, wrong-origin, and Scale
controls; four diagnostic `k` values; both 113 depth series; two subjects'
four-arm render provenance; every registered border annulus; output
dimensions; the freeze failure plant; and the repaired freeze under the same
plant.

An independent read-only verifier recomputed Q1 in signed integer chunks,
solved Q2 directly from the serialized f64 inequalities, and reimplemented the
Q3 annulus calculation without calling `audit.py`. It reproduced every reported
number and found no defect in the decision or the scoped freeze-harness change.

Not verified here: the 299-frame holdout value; a universal depth-only law
under changing references; external identity for any RAW other than the frozen
109 reference; any sharpness or visual advantage; or a finite safe inset that
generalises beyond 109. The assertion that cropping is common product-category
behaviour is context supplied to the lane, not a measurement made by this
audit.
