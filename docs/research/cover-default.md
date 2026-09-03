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

A later, preregistered development extension over the released
calibration-slide session reproduced Crop identity at three exposures: all
72,106,680 emitted RGB16 samples matched external LibRaw predictions exactly,
while Scale changed 94.7696%--99.1441% of the registered overlaps. It also
**refuted** the source's unqualified "`k` falls as the stack deepens" claim:
the strict eight-point chain has reversals at N=60→61 and N=92→182. Neither
result repairs Crop's independent 256 px border blocker, so the default
decision remains unchanged.

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

The initial audit decoded only captures classified as non-holdout in
`docs/proposals/2026-09-sota-scorecard.md` were decoded. The measured inputs
were `109MSDCF`, `113MSDCF`, `coffee-bubbles`, and
`flat-on-ruler-cpl`. `D:\personal\macro` was read only. The 299-frame
`bee-1-cpl` performance holdout was not opened. All outputs and the one copied
diagnostic RAW were written beneath `D:\strehl-out\cover-default`. Rust,
Rayon, OMP, OpenBLAS, MKL, and NumExpr were capped at eight threads.

Scorecard v1.3 commit `e91ba50eb36a83b97700b541358beb77bcc8ed86`
subsequently released the six-stack
`high-res-calibration-slide-cpl` session unit as
**DEVELOPMENT — NOT HOLDOUT** specifically for flat-path identity, coverage,
and Scale-resampling diagnostics. The extension below spent that whole unit.
The capture tree remained read only; sidecars, copied references, and TIFFs
were written only beneath `D:\strehl-out\cover-default-slide-v2`. No holdout
was opened.

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

## 7. Development extension — released calibration-slide session

### 7.1 Frozen protocol, reference-gauge failure, and provenance

This extension was preregistered before any member of the released session was
aligned, decoded, or rendered:

* protocol commit
  `485619d2a7adce02d7eec33d6b07b01798ee2db7`,
  `slide-series-preregistration.md` SHA-256
  `AC66147457C8508ED04D3E34057236B585F3113BD66AE433CBEF0A0487FF1638`;
* initial instrument commit
  `b35b0e52fc3312fe05d52ff98999b3ba2482d25f`;
* external checker `slide_external_decode.py` SHA-256
  `07FDBE4CB32A7FE8539C40AA9B38AC50BC9B6D7DEB76D7B80BA15ACCEDE29722`;
* Rust reference renderer `cover-reference.rs` SHA-256
  `F1762977AA8AE7C1D95366F5C65A6857DC6AB012E9E7323A4054FF6CD2BF5C7E`.

The first real preflight stopped before exposing any `k`: the flat-1s
reference was numerically close to identity but not exact f64 identity. The
original registered result is therefore permanently
**`UNMEASURABLE_REFERENCE_NOT_BIT_IDENTITY`**. Before inspecting another
reference, a crop rectangle, a RAW decode, or a pixel result, commit
`342702793587bba3a50c89a0ac3f39fb62f7130a` froze a separately labelled
`ACTUAL_PRODUCT_DIAGNOSTIC`. Its amendment has SHA-256
`C3AABA922C36E36560D420156C3821D1ED2B28A7CE4A9669B90962DDA5FE6E13`.
It sets no post-result tolerance and forbids canonicalising, rebasing, or
rounding the placement. Commit
`7948bf35522c5453a2334c5e657d8819115a5f05` implemented that explicit mode.

All six actual references then proved non-bit-identical:

| stack | exact f64 bits `(a.re,a.im,b.re,b.im)` | maximum centred-corner displacement |
| --- | --- | ---: |
| flat-1s | `3fefffffffffffff,3be0000000000000,bc80000000000000,3cb0000000000000` | 2.3472018171527914e-13 px |
| flat-2p5s | `3ff0000000000000,0000000000000000,3c70000000000000,bcb0000000000000` | 2.2247786310271853e-16 px |
| flat-6s | `3ff0000000000001,3be0000000000000,3c80000000000000,bcb0000000000000` | 4.692938957858195e-13 px |
| tilted-sw10 | `3ff0000000000000,bc20000000000000,0000000000000000,0000000000000000` | 9.163039456629760e-16 px |
| tilted-sw4 | `3ff0000000000000,0000000000000000,3c80000000000000,3ca0000000000000` | 1.1443916996305594e-16 px |
| all-axis-sw10 | `3ff0000000000000,3c10000000000000,0000000000000000,0000000000000000` | 4.581519728314880e-16 px |

The six sidecars came from the preregistered eight-thread invocation of the
frozen aligner identified in section 1. The reference renderer was built from
`7948bf35` with
`RUSTFLAGS=--cfg cover_slide_audit_20260903` and had:

```text
D:\strehl-out\cover-default-slide-v2\target\release\examples\cover-reference.exe
SHA-256 3D3C400D833051F50E010985672CEF07BD6A3A9E29D2D9900952E6534CA3E83B
```

It loaded and identity-checked every sorted source `.ARW`, the full sidecar,
the registered reference, Catmull-Rom, all placements, and the source digest
before decoding only the reference. It then called production
`cover_or_explain` and `warp_frame_in_place`; it did not merge, elect,
pyramid-decompose, repair defects, correct CA, restore, expose, colour-map, or
apply a display curve.

An independent verifier found one provenance defect after the first geometry
measurement: the Python adjudicator checked that `stack-digest` was syntactic
hex but did not recompute it from the source inventory. No geometry equation
or result was affected, but its `"validation": "PASS"` claim was too strong.
The adjudicator was corrected to require six explicit read-only source
directories and to reproduce Rust's FNV-1a digest over every sorted
`(filename,size)` entry. Current `slide_series.py` SHA-256 is
`99823DB0838E2EE6684E6066E695E80F94994B41DA9A962D476E0FED935DA18F`.
The corrected command rejected planted digest/count changes, then revalidated
all 657 source entries and reproduced every geometry number unchanged:

| stack | N | recomputed = sidecar FNV-1a | inventory SHA-256 | sidecar SHA-256 |
| --- | ---: | --- | --- | --- |
| flat-1s | 60 | `00feb5f7eb369463` | `6BBAE09C4CF0CDACE84C50FCBE2D8C9D135C1B4DE9AEB1865B42B85B71DAEAEC` | `862C6FD8E1956FDD53F527A12809B3079226334265EDADFF8AA1F0EA3B9B828C` |
| flat-2p5s | 61 | `670ef0480ca81076` | `D39CC3AE911C7706AEB054CB470A05C16030965A225482C526115C8379DA4D71` | `0C2CF172F7577189D2EE6F19F281D1A5BA821E7EC4A2F4D13F0BB12B87D4C638` |
| flat-6s | 65 | `7cc19bab0cba440f` | `1DCC9A4FABCC29F5811AF075381CAFC8EF05F9A75A101DCE6C1CF024FABCCF5C` | `60A33EA0513E6408313EAA5698106FEC9B23FD6E8E325C246141C1905F2427F3` |
| tilted-sw10 | 92 | `3c8796d7fd1acf46` | `500753BD7F5F11C06882A9A3D2DECE82A07CE0BB93F52CADC13CD8A4E624B759` | `DB982BEDAE1172EB51D5787F4C6746C1FD552E33077CCAFAD5469BC96D6B10D1` |
| tilted-sw4 | 182 | `175c37dbe6abc528` | `9ABE7BBC11B05985A5E5F6D95F53443A64B9DE8A903EBB936E4DF343E2F61A98` | `AE39DE48B8FA3EFD8A6F65422A4FE9A62B8D687B47B8BB7F359B2DD843E99839` |
| all-axis-sw10 | 197 | `bf3746281784cbbb` | `9F83AC7BDD9FAF9CE255ECAC9F5820D4B8605CC21423B1ABFB5A0117F86056DD` | `133AAD1446F50F570CAFC9DF636661318A6688A7C1B8C2D5F2A9EC9BD2CDEBEC` |

The exact corrected geometry invocation was:

```powershell
$base='D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl'
python -B experiments\cover-default\slide_series.py measure-product `
  --source "flat-1s=$base\flat-sw4-cpl\flat-et1s-sw4-cpl" `
  --source "flat-2p5s=$base\flat-sw4-cpl\flat-et2.5s-sw4-cpl" `
  --source "flat-6s=$base\flat-sw4-cpl\flat-et6s-sw4-cpl" `
  --source "tilted-sw10=$base\tilted-sw10-cpl" `
  --source "tilted-sw4=$base\tilted-sw4-cpl" `
  --source "all-axis-sw10=$base\very-tilted-all-axis-sw10-cpl" `
  flat-1s=D:\strehl-out\cover-default-slide-v2\warpmaps\flat-1s.warpmap.txt `
  flat-2p5s=D:\strehl-out\cover-default-slide-v2\warpmaps\flat-2p5s.warpmap.txt `
  flat-6s=D:\strehl-out\cover-default-slide-v2\warpmaps\flat-6s.warpmap.txt `
  tilted-sw10=D:\strehl-out\cover-default-slide-v2\warpmaps\tilted-sw10.warpmap.txt `
  tilted-sw4=D:\strehl-out\cover-default-slide-v2\warpmaps\tilted-sw4.warpmap.txt `
  all-axis-sw10=D:\strehl-out\cover-default-slide-v2\warpmaps\all-axis-sw10.warpmap.txt
```

### 7.2 Geometry commissioning and Q2

Before the corrected measurement:

```powershell
python -B experiments\cover-default\slide_series.py commission
```

returned `COMMISSIONED`. A fixed external two-entry oracle produced FNV-1a
`9d06cf05b27f7b40`; changing one source size changed the digest, restoring it
restored the digest exactly, a wrong sidecar digest was refused, and a
59-versus-60 inventory was refused. Mixed-case names sorted in Rust's
case-sensitive order and a symbolic-link file type was refused. The existing
geometry plant moved
`k` from 0.9974380871050387 to 0.9872013651877134; the registered improvement
arm moved it back toward truth to 0.9948805460750854, and restoration returned
exactly 0.9974380871050387. Equality and reversal plants failed strict
ordering, threshold-nextafter plants straddled the registered limits, and
removing a planted subset constraint did not reduce `k`.

The separately labelled actual-product values are:

| point | N | `k` | `100*(1/k-1)` | Crop `(x,y,w,h)` | provenance |
| --- | ---: | ---: | ---: | --- | --- |
| documented anchor | 22 | 0.9870 | 1.317122594% | — | source assertion |
| flat-1s | 60 | 0.9862106434499731 | 1.398216156% | 25,17,3466,2310 | measured |
| flat-2p5s | 61 | 0.9869882377791444 | 1.318330019% | 23,16,3470,2312 | measured |
| flat-6s | 65 | 0.9859311178882552 | 1.426963999% | 25,17,3466,2310 | measured |
| tilted-sw10 | 92 | 0.9652763795078986 | 3.597272370% | 62,41,3392,2262 | measured |
| tilted-sw4 | 182 | 0.9676287511847108 | 3.345420315% | 57,38,3402,2268 | measured |
| all-axis-sw10 | 197 | 0.9378551850015397 | 6.626269811% | 110,73,3296,2198 | measured |
| documented anchor | 299 | 0.9321 | 7.284626113% | — | source assertion; holdout untouched |

All six new values lie strictly between the two source anchors, but the
preregistered chain is **`NOT_ORDERED`**:

* `k60=0.9862106434499731 < k61=0.9869882377791444`;
* `k92=0.9652763795078986 < k182=0.9676287511847108`.

Thus the weak magnitude range is corroborated, but the claimed unqualified
depth law does not survive. It must not be rescued by averaging.

The flat exposure/SNR control also failed. Its `k` span was
0.001057119890889191 against the frozen 0.0010 maximum, a failure by
0.000057119890889191. Integer edge-loss spans did pass
`(left,right,top,bottom)=(2,2,1,1)` px against the 2 px limits. The combined
registered verdict is **`EXPOSURE_SOLVE_SENSITIVE`**: these product solves
cannot be described as a purely geometric depth law.

The deterministic N=182→92 subset included both endpoints and reference 91.
It gave `k=0.9676287511847108`, exactly the full N=182 value, so removing
constraints correctly did not lower `k`. It differed from the independent
tilted-sw10 N=92 value by 0.002352371676812237, exceeding the 0.0010 bound.
The verdict is **`CAPTURE_STEP_WIDTH_SENSITIVE`**, not depth-density support.
Moreover, the tilted N=92 and N=182 maps report held-out errors of
12.095237912344203 px and 8.662102059714970 px respectively, both beyond the
aligner's 4 px usability threshold (`align_cmd.rs:472-478`). They are faithful
measurements of the global model the product applies, not established
physical-geometry truth.

### 7.3 Q1 at three exposures

The three registered references were copied to the private output tree and
hash-checked:

| case | private RAW SHA-256 | Crop TIFF SHA-256 | Scale TIFF SHA-256 |
| --- | --- | --- | --- |
| flat-1s | `3A5FC6993D0EC24468FD24684AABE7783FE06D3D85EEC040584330AF0153A03B` | `15227287E89FFE59F0EAF7FA8198382E5B04E17C152012D31375605691386B2F` | `407FB1F79227A37B3C60717959142ABC2EB78D8C936B347EEF7BD3D3CCAA5FF3` |
| flat-2p5s | `9FB1CC9C323D13D72467411F9FFE607F20C6D088EAEA374F4F0AB9C56098535D` | `E20DB21BBF801272562E8893A29369089BB63C9FAED368AB5D68C7A2C34C069A` | `AA087D09AFE085DA1AD9F116FFA00A8636AB884753467BB90A606EC22EAF7D97` |
| flat-6s | `A5225AEF221DAD3D6EB850940BE527E48A99548EF3CF23990AE4D09EA5B5A146` | `7A967457CD05A21C281D94BE12288533AA15C3B168BFB6F0E41F5FBFDDC6ED0E` | `8B34EAA79634AC6D960D4CE1DB365872F8AB02D99A85FF24BE63C1CAE20F26D6` |

The exact external comparison was:

```powershell
python -B experiments\cover-default\slide_external_decode.py measure-product `
  --case flat-1s `
    D:\strehl-out\cover-default-slide-v2\refs\flat-1s\DSC00046.ARW `
    D:\strehl-out\cover-default-slide-v2\warpmaps\flat-1s.warpmap.txt `
    D:\strehl-out\cover-default-slide-v2\q1\flat-1s\crop-reference.tiff `
    D:\strehl-out\cover-default-slide-v2\q1\flat-1s\scale-reference.tiff `
  --case flat-2p5s `
    D:\strehl-out\cover-default-slide-v2\refs\flat-2p5s\DSC00050.ARW `
    D:\strehl-out\cover-default-slide-v2\warpmaps\flat-2p5s.warpmap.txt `
    D:\strehl-out\cover-default-slide-v2\q1\flat-2p5s\crop-reference.tiff `
    D:\strehl-out\cover-default-slide-v2\q1\flat-2p5s\scale-reference.tiff `
  --case flat-6s `
    D:\strehl-out\cover-default-slide-v2\refs\flat-6s\DSC00047.ARW `
    D:\strehl-out\cover-default-slide-v2\warpmaps\flat-6s.warpmap.txt `
    D:\strehl-out\cover-default-slide-v2\q1\flat-6s\crop-reference.tiff `
    D:\strehl-out\cover-default-slide-v2\q1\flat-6s\scale-reference.tiff
```

rawpy 0.27.0 / LibRaw 0.22.1 decoded each RAW in two independent contexts.
Both contexts reproduced their full visible-mosaic hashes. The checker then
independently applied the frozen RGGB, black-512, usable-white-15360, per-site
clamp, two-green average, float32 WB, and RGB16 rounding rules. Normalised WB
gains were `(2.775390625,1,1.5205078125)`,
`(2.7587890625,1,1.5322265625)`, and
`(2.7392578125,1,1.560546875)` for 1 s, 2.5 s, and 6 s.

| comparison | samples | max abs | RMS | differing samples / fraction |
| --- | ---: | ---: | ---: | ---: |
| flat-1s external→Crop, full emitted extent | 24,019,380 | **0 DN** | **0 DN** | **0 / 0%** |
| flat-1s unscaled external→Scale | 24,710,448 | 22,831 DN | 2997.023928606048 DN | 24,272,164 / 98.2263211092% |
| flat-2p5s external→Crop, full emitted extent | 24,067,920 | **0 DN** | **0 DN** | **0 / 0%** |
| flat-2p5s unscaled external→Scale | 24,710,448 | 57,937 DN | 7379.469079321559 DN | 24,498,939 / 99.1440503224% |
| flat-6s external→Crop, full emitted extent | 24,019,380 | **0 DN** | **0 DN** | **0 / 0%** |
| flat-6s unscaled external→Scale | 24,710,448 | 60,720 DN | 16953.854662869253 DN | 23,417,982 / 94.7695565859% |

Crop's R, G, and B channels were separately exact. The per-channel sample
counts were 8,006,460, 8,022,640, and 8,006,460 by case. Scale used the
preregistered common `3514x2344x3` rawpy domain; its last two plane columns
have no external binned-RAW counterpart and were not silently added after
inspection.

The categorical exposure predicate is therefore
**`CROP_EXACT_SCALE_CHANGED_AT_ALL_THREE_EXPOSURES`**. The Scale DN RMS changes
with exposure because the signal being interpolated changes; the
preregistration explicitly reports but does not require invariance of that
quantity. What is invariant is the exact-Crop/changed-Scale result. In
particular, the tiny nonidentity reference placements were consumed unchanged,
yet integer addressing and floating-point evaluation still serialized every
Crop sample exactly.

Commissioning preceded each real comparison. A candidate-side centre-green
XOR `0x8000` changed exactly one sample (max 32768 DN; RMS
6.686041046626796, 6.679295465157900, and 6.686041046626796 DN by case).
Replacing it with XOR `0x0001` was the registered improvement arm: max fell to
1 DN and RMS to 0.000204041780, 0.000203835921, and 0.000204041780 DN.
Restoration returned every statistic to exact zero. A one-quad wrong Crop
origin changed 95.5716800%, 97.4822835%, and 92.1876793%; correcting only the
externally specified origin returned all channels to exact zero. The real
Scale arms remained far above the 1% positive-control threshold.

An independent read-only implementation, importing neither COVER Python
module, reproduced all six aggregate rows, every Crop channel, all mutation
and origin controls, all RAW mosaic and candidate-array hashes, all six `k`
values and crop rectangles, both ordering reversals, the SNR span, and the
N=182→92 control.

### 7.4 Product decision after the extension

The extension strengthens the mechanism statement: on four externally decoded
references in total, including three exposure levels, Crop is a bit-for-bit
integer window and Scale resamples almost every sample. It weakens the source's
causal story: product `k` is neither strictly ordered by N nor invariant enough
across the flat exposure solves to qualify as a pure depth law, and the
step-width pair does not isolate frame count.

Neither finding changes the shipping gate. Crop still runs the merge pyramid
on the uncovered full plane before cutting out its smaller rectangle. The
separately measured 109 profile still requires a **256 px** safe inset, twice
the frozen 128 px maximum, and retains only **64.6047%** of the original plane;
the second subject still validates no finite general inset. **Keep Scale as the
default.** Crop remains useful as an explicit diagnostic, but making it the
default would exchange a proven resample for a larger unresolved border
contamination without an admissible universal crop.

## 8. Verification and limitations

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

python -B experiments\cover-default\slide_series.py commission
  -> COMMISSIONED; fixed FNV oracle, source mutation/restoration,
     geometry defect/improvement/restoration, strict-order, threshold,
     subset, and exact-reference controls passed

python -B experiments\cover-default\slide_series.py measure-product
  <six explicit --source bindings> <six explicit sidecar bindings>
  -> MEASURED; all 657 source entries reproduced all six sidecar
     digests; strict reference result UNMEASURABLE; actual-product
     results NOT_ORDERED / EXPOSURE_SOLVE_SENSITIVE /
     CAPTURE_STEP_WIDTH_SENSITIVE

python -B experiments\cover-default\slide_external_decode.py measure-product
  <three explicit RAW/sidecar/Crop/Scale cases>
  -> PASS; commissioning and repeated LibRaw controls passed;
     Crop exact and Scale changed at all three exposures

independent inline rawpy/NumPy/tifffile reimplementation
  -> exit 0; reproduced mosaic/prediction hashes and every Q1 aggregate
     without importing the COVER checker or a repository module

independent inline sidecar/source-geometry reimplementation
  -> exit 0; reproduced source identities, all six geometry rows,
     strict failures, SNR result, and subset result without importing
     the COVER adjudicator

python -m ruff check experiments\cover-default\slide_series.py
python -m ruff format --check experiments\cover-default\slide_series.py
  -> passed

rustfmt --edition 2024 --config skip_children=true --check
  crates\strehl-cli\examples\cover-reference.rs
  -> exit 0

cargo test --release -p strehl-cli --example cover-reference
  --target-dir D:\strehl-out\cover-default-slide-v2\target -j 8 --
  --test-threads=1
  -> 46 passed

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

Verified here: Q1 transparency for the original 109 reference and all three
released flat references against two-context rawpy/LibRaw decodes; every Crop
channel; candidate-side defect, improvement, restoration, wrong-origin, and
Scale controls; source names/sizes/counts and sidecar identity for all six
released stacks; six actual-product `k` values, reference bits, crop
rectangles, ordering, SNR, and subset controls; both earlier 113 depth series;
two subjects' four-arm border provenance and every registered annulus; output
dimensions; the freeze failure plant; and the repaired freeze under the same
plant.

Independent read-only verifiers recomputed Q1 in signed integer chunks, solved
Q2 directly from serialized f64 inequalities, found and caused correction of
the original source-digest validation omission, and reimplemented the Q3
annulus calculation without calling a COVER module. After correction they
reproduced every reported decision input.

Not verified here: the 299-frame holdout value; a universal depth-only law
under changing references; any sharpness or visual advantage; or a finite safe
inset that generalises beyond 109. The N=299 `k=0.9321` row and the assertion
that cropping is common product-category behaviour are supplied context, not
fresh measurements. The tilted maps' global-similarity geometry is a product
behavior measurement, not assumed physical truth. The six TIFFs are
content-hashed and their arrays independently checked, but no saved artifact
cryptographically binds each TIFF to the candidate executable; that binding
rests on the observed renderer invocations, their validation banners, and the
recorded build/hash chronology.
