# BUILD-OUTPUT — the delivered file as a print master

Lane brief: make the emitted TIFF correct as a print master (ICC profile and
physical resolution), explain and fix the two subjects failing the highlight
gate, and adjudicate the three subjects flagged for shadow crush against their
source frames.

Everything below was measured on this machine. Where a number could not be
separated from a confound, that is said rather than smoothed over.

Instruments, all under `experiments/BUILD-OUTPUT/`:

| script | what it does | why it exists |
| --- | --- | --- |
| `tiff_tags.py` | walks the TIFF IFD byte by byte, dumps the ICC tag table | `tifffile` normalises a missing resolution to `(1, 1)`, so it cannot tell *absent* from *present-and-default* — which is the entire question |
| `clip_census.py` | per-channel clip/crush at `orch_printready.py`'s own thresholds, split into all-three-channels vs exactly-one, plus exact-boundary hits | a mean over the flattened three-channel array cannot separate a blown highlight from a colour on the gamut wall |
| `crush_luma.py` | reports the luminance and surviving-channel detail of the pixels a gate calls crushed or clipped | asks the question the gate's name implies: *are these pixels actually dark?* |
| `commission_icc.ps1` | four-arm commissioning of the new ICC test | rule 2 — a metric is worth nothing until a planted defect reads RED and a planted improvement moves the right way |

---

## 1. The before-state, read off real bytes

The brief asked what the delivered file *actually* contained. Not what the code
says it writes — what is in the bytes. `tiff_tags.py` on the delivered gallery:

```
C:\dev\strehl-out\SHIP-V2\dry-erase-marker-head-cpl--SHIP-V2.tiff   (198023555 bytes)
  270    ImageDescription           ASCII      count 620      'sRGB (IEC 61966-2-1): BT.709-6 primaries, D65 white point, sRGB transfer curve. For viewing. ...'
  282    XResolution                RATIONAL   count 1        1/1 = 1.0
  283    YResolution                RATIONAL   count 1        1/1 = 1.0
  296    ResolutionUnit             SHORT      count 1        (1,)  (none)
  305    Software                   ASCII      count 13       'strehl 0.0.0'
  ABSENT: 34675 ICCProfile
```

| file | ICC 34675 | 282 / 283 | 296 | 305 Software |
| --- | --- | --- | --- | --- |
| `SHIP-V2` gallery (**delivered**) | **ABSENT** | 1/1 | **1 = none** | `strehl 0.0.0` |
| HEAD `--srgb` | present, 2716 B, v2.1.0, sRGB TRC | **300/1** | **2 = inch** | `strehl 0.0.0 (643b719d3d15-dirty)` |
| HEAD `--linear-srgb` | present, 696 B, **identity TRC** (`curv` count 0) | **300/1** | **2 = inch** | build-stamped |
| HEAD camera-native | **ABSENT (correct)** | 1/1 | 1 = none | `strehl 0.0.0`, unstamped |

**The finding is not the one the brief anticipated.** The code at HEAD is
already correct on all three colour modes: `96b7e119` landed the ICC work and
`c14284a8` landed resolution and the build stamp. The **delivered gallery is
stale** — those 26 masters were rendered 09:25–10:24, and both commits landed
later the same day. The masters that exist right now have no ICC profile and no
defined print size; the code that would give them both is committed and
working. This is an artifact problem, not a code problem, and it is routed to
the orchestrator: the gallery needs re-rendering, the writer does not need
re-fixing.

So the useful work available in this lane was not to add the tags. It was to
find out what the *tests* could not see.

### 1.1 What the ICC tests could not see

Three real holes, each verified by planting the defect and watching the suite
stay green.

**Hole 1 — the two colorimetric profiles could be exchanged silently.**
`only_the_colorimetric_paths_get_a_profile` ends with `assert_ne!(srgb, lin)`.
An inequality fixes no identity: swap the two arms of `icc_for` so `--srgb`
files carry the linear profile and `--linear-srgb` files carry the sRGB one,
and every assertion in the crate still passes. `the_profile_is_structurally_
well_formed_and_deterministic` checks each profile against itself;
`the_derived_primaries_match_the_published_srgb_icc_columns` checks the matrix,
which the two profiles share. Nothing compared a profile to the pixels it was
attached to. The cost of that swap is not cosmetic and was already measured by
earlier lanes: `BUILD-RENDER-icc/potency.py` puts it at **50.39 DN mean over
99.5 % of pixels**, and `BUILD-RENDER-print/icc_potency.py` ARM B at **92 DN**.

**Hole 2 — the most dangerous mode was never covered.** The test exercised
`OutputSpace::CameraLinear.develop(None)` but not `OutputSpace::Srgb.
develop(None)` — an uncharacterised body rendered with `--srgb`, which produces
camera primaries carrying an sRGB transfer curve. It looks like sRGB to every
check a reader can perform except the primaries. If `icc_for` were ever keyed
on `dev.srgb` alone, every existing assertion still passed.

**Hole 3 — a fourth state had no answer at all.** `icc_for` matched on
`(matrix.is_some(), srgb)`, so `Develop { matrix: Some(_), srgb: false, tone:
Some(_) }` fell into the `(true, false)` arm and received the **linear** sRGB
profile. Those pixels have had `s_curve` applied in linear light — see
`develop_pixel`, where the S-curve runs unconditionally and the sRGB encode
does not — so they are neither linear sRGB nor sRGB. Unreachable from the CLI
today because `OutputSpace::develop` sets `wants_tone` from `applies_curve`,
but `Develop` is a public struct with four independently settable fields, so
the state is constructible and a test has power over it.

### 1.2 What changed

`icc_for` became a total match on `(matrix.is_some(), srgb, tone.is_some())`,
with the third state answering `None` — the same wrong-profile-is-worse-than-
none policy the camera-native paths already followed, applied one step further
in. Four lines deleted, five added; the doc comment carries the reasoning and
the two potency numbers.

`the_embedded_profile_states_the_transfer_curve_the_pixels_carry` is new. It is
deliberately a **file-level** test: it writes a small TIFF per mode through
`write_rgb16_described`, reads tag 34675 back out with the `tiff` decoder,
walks the ICC tag table as raw bytes, and asserts

* `rTRC` is `curv` with count 0 **iff** the render did not apply the sRGB curve,
  and a sampled curve with `TRC(0) = 0`, `TRC(1) = 1`, `TRC(0.5) ≈ 0.2140`
  **iff** it did — 0.735 being the same curve stored backwards;
* `gTRC` and `bTRC` are byte-identical to `rTRC`;
* the `desc` string says "gamma 1.0" iff the TRC is the identity, so the
  human-readable and machine-readable halves cannot disagree;
* the `rXYZ`/`gXYZ`/`bXYZ` colorants match `srgb_to_xyz_d50()` to 2e-5;
* the tag is **absent** on both camera-native modes and on the tone-in-linear
  state.

The tag table is walked by hand rather than through a shared parser on purpose.
A parser shared with the writer agrees with the writer by construction, which
is the failure mode this test exists to prevent.

### 1.3 Commissioning

`commission_icc.ps1`, four arms, each a real edit compiled and run. The source
file is copied to `$env:TEMP` and restored from the copy in a `finally` block —
`git checkout --` is never used — and the mtime is bumped afterwards so cargo
cannot serve a binary built from the mutated file. The script aborts an arm if
its `Replace` was a no-op, because a silent no-op would make a planted defect
look like a clean tree.

```
ARM CLEAN (known-good, expect GREEN)
  new test  : the_embedded_profile_states_the_transfer_curve_the_pixels_carry -> OK
  test result: ok. 30 passed; 0 failed

ARM SWAP (planted defect: sRGB and linear profiles exchanged, expect RED)
  new test  : ... -> FAILED
  pre-existing ICC tests:
      only_the_colorimetric_paths_get_a_profile=ok
      the_profile_is_structurally_well_formed_and_deterministic=ok
      the_derived_primaries_match_the_published_srgb_icc_columns=ok
      the_primary_columns_sum_to_the_pcs_white=ok
      the_transfer_curve_is_stored_in_the_decoding_direction=ok
  test result: FAILED. 29 passed; 1 failed

ARM THIRDARM (improvement reverted: tone-in-linear gets the linear profile, expect RED)
  new test  : ... -> FAILED       [all five pre-existing ICC tests: ok]
  test result: FAILED. 29 passed; 1 failed

ARM BACKWARDS (planted defect: TRC stored in the encoding direction, expect RED)
  new test  : ... -> FAILED       [all five pre-existing ICC tests: ok]
  test result: FAILED. 29 passed; 1 failed
```

Read the right-hand column. **On all three planted defects every pre-existing
ICC test stayed green.** The new test is the only thing in the crate with power
over any of them, which is what makes it worth its lines.

The THIRDARM result is the planted *improvement* rule 2 demands, run backwards:
the arm reverts the change this lane made, and the test goes RED. A suite that
only ever plants degradations cannot distinguish a metric that is blind from
one that is perverse; this one moves in the correct direction on a known
improvement.

The BACKWARDS arm produced an unplanned finding worth recording.
`the_transfer_curve_is_stored_in_the_decoding_direction` sounds like it covers
exactly that defect. It does not — it tests the helper `srgb_eotf` directly,
not what lands in the file, so inlining the inverse at the call site leaves it
green. It has power over the helper, not over the master. That is the general
shape of the gap this lane found in three separate places: **tests that check a
function against itself rather than the artifact against the render.**

---

## 2. The two highlight failures

`orch_printready.py` failed two masters on `clip = mean(rgb >= 65500)` against
`CLIP_MAX = 0.001`:

| subject | reported clip | verdict |
| --- | --- | --- |
| `dry-erase-marker-head-cpl` | 0.3265 % | **a real defect, already fixed at HEAD** |
| `flowers-cpl` | 0.1657 % | **not a highlight failure; the gate is misreading it** |

### 2.1 Splitting the statistic

`clip_census.py` separates two populations a single mean cannot:

* **all three channels at the top** — a genuinely blown highlight, detail gone;
* **exactly one channel at the top, at *exactly* 65535** — the signature of
  `image_out::gamut_map`, which blends an out-of-gamut triple toward the
  neutral of the same BT.709 luminance by the smallest blend that works, and
  therefore lands the offending channel on exactly 1.0 by construction.

Every out-of-gamut pixel contributes to `orch_printready.py`'s count whether or
not anything is blown.

| subject | clipCH (the gate) | **clipALL3** | B==65535 |
| --- | --- | --- | --- |
| `dry-erase-marker-head-cpl` | 0.3265 % **FAIL** | **0.0000 %** | 0.9541 % |
| `flowers-cpl` | 0.1657 % **FAIL** | **0.0131 %** | 0.4458 % |
| `112MSDCF` | 0.0775 % pass | **0.0693 %** | 0.0777 % |
| `113MSDCF` | 0.0764 % pass | **0.0684 %** | 0.0749 % |
| `flat-on-ruler-cpl` | 0.0689 % pass | **0.0636 %** | 0.0692 % |
| `couch-fibers-cpl` | 0.0725 % pass | **0.0511 %** | 0.1049 % |

**The gate failed the one master in the corpus with literally zero blown
highlights.** `dry-erase-marker-head-cpl`'s `clipALL3` is 0.0000 %, the joint
minimum across all 26 subjects. And `flowers-cpl` was failed at `clipALL3`
0.0131 % while **sixteen subjects that passed have more**, up to `112MSDCF` at
0.0693 % — 5.3 times higher. On the statistic the gate's name refers to, the
ranking is close to inverted.

### 2.2 `dry-erase-marker-head-cpl` — real, and already fixed

Four arms, same 299 frames, `STREHL_ALIGN=0`, identical merged data (identical
`tone: black 0.00830, white 1.00473`), differing only in the develop stage:

| arm | clipCH | B==65535 |
| --- | --- | --- |
| pin `b9b6921e` (the binary SHIP-V2 was rendered with) | **0.6109 %** | 1.8010 % |
| HEAD with `STREHL_HIGHLIGHT_KNEE=off` | **0.6109 %** | 1.8010 % |
| HEAD, default knee 0.60 | **0.0000 %** | 0.0000 % |

The knee-off arm reproduces the pinned binary to four decimals, so the develop
stage is the only thing that differs and `highlight::desaturate` is the whole
of the difference. Under alignment, the delivered configuration:

| | SHIP-V2 (pin, aligned) | HEAD (aligned) |
| --- | --- | --- |
| `dry-erase-marker-head-cpl` | 0.3265 % **FAIL** | **0.0000 % PASS** |

What the pixels were: `crush_luma.py` on the SHIP-V2 master reports the clipped
population at median luminance **0.9720** with the **dimmest** surviving
channel at **0.9640**. These were bright near-white highlights whose blue
channel reached the ceiling roughly 1.5 % of full scale ahead of red and green,
taking the hue with it. That is precisely what the chroma roll-off exists to
prevent, and it removes it completely. **A genuine defect, correctly diagnosed
and fixed by BUILD-HIGHLIGHT before this lane arrived; the delivered master
predates the fix.**

Of the four candidate causes in the brief: not a specular highlight no software
can recover (it is fully recovered); not `--auto-exposure`, which chose **−0.24
stops**, a *reduction*; not merge overshoot (see §2.3); it was the tone path
letting channels separate at the very top, and the fix is shipped.

### 2.3 `flowers-cpl` — the merge is not manufacturing it

Exposure pinned to `--exposure 1.76` across all three arms so a brighter render
cannot be mistaken for a worse one:

| arm | clipCH | clipALL3 | B==65535 |
| --- | --- | --- | --- |
| one mid-stack source frame | 0.0338 % | **0.0000 %** | 0.0969 % |
| 176 frames, unaligned | 0.0374 % | **0.0000 %** | 0.1067 % |
| 176 frames, aligned | 0.1670 % | 0.0133 % | 0.4488 % |

A single source frame carries **90 %** of the unaligned stack's blue pin. The
merge adds 11 % — it is not manufacturing the highlight, and pyramid overshoot
is ruled out.

`--auto-exposure` is ruled out by a stronger result than a comparison:
`--exposure 1.76` and `--auto-exposure` (which chose **+1.91**) produce
**bit-identical** statistics — 0.1670 % / 0.0133 % / 0.4488 % to four decimals.
The tone stage re-normalises p99.9 luminance to `TONE_WHITE_TARGET = 0.90`
regardless of the gain already applied, and absorbs a 0.15-stop difference
entirely. Exposure is not a lever on this number at all.

The highlight roll-off is **inert** here: knees of 0.60, 0.45 and 0.30 give
bit-identical output. The reason is structural. `highlight::desaturate` works
in camera space against the container ceiling, so it only sees pixels the
*sensor* drove near saturation; `flowers-cpl`'s blue arrives at the ceiling
only after +1.9 stops and the tone stretch, both downstream. Lowering the knee
cannot help because there is nothing there for it to act on. This is recorded
in `DEFAULT_KNEE`'s doc comment so the next person does not re-run the sweep.

What remains is 0.0133 % genuinely blown — in family, sixteen subjects have
more — plus 0.4488 % of near-white pixels (dimmest surviving channel 0.9336,
median luminance 0.9706) sitting on the sRGB gamut wall with blue on the
ceiling. **Not ours to fix on this evidence**, and specifically not by moving
`DEFAULT_KNEE`, which the sweep shows would change nothing here while
desaturating legitimate bright colour everywhere else.

There is a real mechanism visible underneath: the tone stage derives one gain
from luminance and applies it to all three channels, which places luminance
correctly but bounds no individual channel. Anything that bounds that
population has to live there. That is a corpus-wide render change requiring
corpus-wide commissioning and an orchestrator decision — it is not a change to
make unilaterally on two subjects' evidence, and it is routed rather than done.

**Confound stated rather than smoothed over.** Alignment raises the blue pin
4.2× (0.1067 % → 0.4488 %) at the same *requested* exposure, but the aligned
merge's tone solved to `white 0.89626` against the unaligned `0.99533`, so the
auto tone stretched harder. Alignment concentrating a highlight that would
otherwise be smeared across frames, and alignment lowering p99.9 so the tone
stage stretches more, both predict the same sign. **I could not separate them**
— the CLI exposes no tone override — so I am not claiming which it is.

---

## 3. Shadow crush — all three adjudicated innocent

The brief flagged a strikingly bimodal distribution: 23 subjects at
0.000–0.020 %, three at 2.5–3.6 %, a 150× gap with nothing between. A gap that
clean is the signature of two mechanisms, and it is.

### 3.1 Nothing in this corpus is dark in all three channels

| subject | crushCH (reported) | **crushALL3** | which channel |
| --- | --- | --- | --- |
| `flower-inner-edge-cpl` | 3.6357 % | **0.0000 %** | B==0 on 10.6528 % |
| `119MSDCF` | 3.2637 % | **0.0000 %** | R==0 on 9.7840 % |
| `109MSDCF` | 2.5443 % | **0.0000 %** | R==0 on 7.6141 % |

`crushALL3` is 0.0000 % for 25 of 26 subjects and 0.0004 % for `foam`. Not one
of the three flagged masters has a single pixel dark in all three channels. All
of it is one channel pinned at *exactly* 0 — `gamut_map`'s signature again, at
the other end of the scale.

### 3.2 The "crushed" pixels are not dark

`crush_luma.py` reads the pixels the gate counts and asks what they actually
are:

| subject | crushPX | ch | **median luma** | >25 % luma | median brightest-other | **distinct levels** |
| --- | --- | --- | --- | --- | --- | --- |
| `109MSDCF` | 7.63 % | R | **0.2406** | 44.5 % | 0.6745 | **50 498** |
| `119MSDCF` | 9.79 % | R | **0.2463** | 48.2 % | 0.6553 | **53 130** |
| `flower-inner-edge-cpl` | 10.91 % | B | **0.3306** | **80.5 %** | 0.3738 | **33 239** |
| `flowers-cpl` — *a real black* | 0.0043 % | B | **0.0011** | 0.00 % | 0.0012 | **122** |
| `dry-erase-marker-head-cpl` | 0.0000 % | B | 0.0872 | 0.00 % | 0.1106 | **12** |

Median luminance 0.24–0.33 is **mid-tone**, not shadow. On
`flower-inner-edge-cpl` — the one the brief singled out because its dark region
is inside the subject rather than a black backdrop — **80.5 % of the "crushed"
pixels are brighter than quarter luminance**, and their surviving channels
carry **33 239 distinct values**. Nothing has been crushed. These are saturated
colours outside the sRGB gamut, projected onto the gamut surface: a bright blue
subject drives red negative, a bright yellow-green flower interior drives blue
negative, and a point on the gamut surface has one channel at exactly 0 by
definition.

Compare the last two rows. `flowers-cpl`'s crushed population is median
luminance **0.0011** across **122** distinct levels — *that* is a genuine
black, and the gate scores it at 0.0043 %.

**The statistic is anti-correlated with the property it is named for.** It
reads 10.9 % on the master whose crushed pixels are mostly mid-tone and richly
detailed, and 0.0043 % on the master with a real black. Its three high subjects
are the corpus's three most saturated — consistent with BUILD-RENDER's
independently measured, model-free 10.71 % out-of-gamut on
`flower-inner-edge-cpl`.

### 3.3 Against the source frames

The brief required measuring against source frames, not intuition. One
mid-stack `.ARW` per subject, same binary, same flags, `STREHL_ALIGN=0`:

| subject | master crushCH | one source frame | ratio |
| --- | --- | --- | --- |
| `109MSDCF` | 2.5443 % | 2.3571 % | 0.93 |
| `119MSDCF` | 3.2637 % | 3.2273 % | 0.99 |
| `flower-inner-edge-cpl` | 3.6357 % | **4.0770 %** | **1.12** |

The source frames carry 93–112 % of it. On `flower-inner-edge-cpl` the merge
measurably **reduces** the count. The tone path is not destroying shadow
detail; the sensor recorded colours sRGB cannot hold.

This comparison is exact rather than approximate, and that is worth stating:
whether a channel goes negative is decided by the colour matrix before any
gain, and the tone stage applies a single luminance-derived gain to all three
channels. The *sign* is therefore invariant to `--exposure`, `--auto-exposure`
and the tone stage, so a single frame and a merged master can be compared
directly without matching their exposures.

**Verdict: all three innocent.** `109MSDCF` and `119MSDCF` are saturated blue
subjects, `flower-inner-edge-cpl` a saturated yellow-green interior. None is a
black backdrop and none is a defect — the third category the brief did not list
but the data requires.

### 3.4 Should crush earn an absolute threshold? No.

`orch_printready.py` reports crush and deliberately does not gate on it. That
was the right call and it should stay. Rule 5: a statistic earns an absolute
threshold only if commissioned to be subject-invariant, and this one is the
opposite — its value is driven almost entirely by subject saturation, and its
ranking is inverted with respect to actual shadow loss. Any absolute threshold
between 0.02 % and 2.5 % fails the three most colourful masters in the corpus
for being colourful, while passing the master that contains a real black.

If a shadow gate is ever wanted, `crushALL3` is the candidate: corpus range
0.0000–0.0004 %, tight, and it means what it says. It has not been commissioned
against a planted shadow defect, so this lane is not proposing a number for it.

---

## 4. Verification

```
cargo test --release -p strehl-core
test result: ok. 486 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out

cargo test --release -p strehl-cli
   Compiling strehl-cli v0.0.0
    Finished `release` profile [optimized] target(s) in 1m 01s
running 110 tests
test image_out::tests::the_embedded_profile_states_the_transfer_curve_the_pixels_carry ... ok
test result: ok. 110 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out

     Running tests\byte-freeze.rs
freeze `coffee-bean-20-gate2-unaligned` HOLDS: 88712017FE31362F35FF2FF5D4B98727CDEFCBAC489D9A7827F21EE0154A8620
    (49450019 bytes, alignment off, 10 chunks of <= 2 frames) -- reproduced twice
freeze `coffee-bean-20-gate2-sidecar` HOLDS: 52517FF8AE245F238C29F64A29E601C2D5C064CB4D86E93006512993837EC206
    (49450019 bytes, alignment on-sidecar-override, 10 chunks of <= 2 frames, 20 placed / 0 refused) -- reproduced twice
test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

**The byte-freeze did not move.** Both rows reproduced twice at their recorded
hashes. This was verified rather than assumed: the rows are rendered camera-
native through the untagged `write_rgb16`, and both are `srgb = no`, so a
change confined to the colorimetric arms of `icc_for` should not reach them —
but "should not" is not a measurement.

## 5. What I could not verify

* **Alignment vs. tone on `flowers-cpl`.** §2.3. The two hypotheses predict the
  same sign and the CLI exposes no tone override, so I did not separate them.
* **Whether re-rendering the gallery at HEAD fixes the gate corpus-wide.** I
  re-rendered two subjects, not 26. `dry-erase-marker-head-cpl` goes
  0.3265 % → 0.0000 %; `flowers-cpl` stays at 0.1670 % and still trips
  `CLIP_MAX`. The other 24 are unmeasured at HEAD.
* **`crushALL3` as a gate.** Proposed as the honest statistic, but not
  commissioned against a planted shadow defect. It should not be adopted on my
  say-so.
* **The `--linear-srgb` and camera-native geometry.** Those modes default to
  binned output (3516 × 2344) where `--srgb` renders full resolution; the ICC
  and resolution tags were checked on all three, the pixel paths only on
  `--srgb`.

## 6. Routed to the orchestrator

1. **The delivered SHIP-V2 gallery has no ICC profile and no defined print
   size.** Verified on real bytes, two files. It predates `96b7e119` and
   `c14284a8` by hours. The code is correct; the artifacts are stale. Re-render
   before shipping — every one of those masters is currently interpreted by
   whatever working space the reader happens to have.
2. **`orch_printready.py`'s clip gate is measuring the sRGB gamut wall, not the
   tone scale**, on both failing subjects. It failed the corpus's *only* master
   with zero blown highlights and passed sixteen subjects with more genuinely
   blown highlight than one it failed. `clipALL3` is the statistic the gate's
   name refers to. The FAIL text "clipped 0.327 %" is misleading as written.
3. **Crush has not earned an absolute threshold and should stay ungated**, for
   the reasons in §3.4. The three high subjects are the three most saturated;
   their "crushed" pixels are mid-tone with tens of thousands of distinct
   levels.
4. **`dry-erase-marker-head-cpl` is fixed at HEAD** by the highlight roll-off:
   0.3265 % → 0.0000 % under the delivered configuration.
5. **`flowers-cpl` will still trip `CLIP_MAX` after a re-render.** The residual
   is the gamut wall plus an in-family genuine highlight. Bounding it means
   changing the tone stage to bound per-channel rather than per-luminance —
   corpus-wide, needs corpus-wide commissioning, and is not this lane's call.

---

# 7. Is the DELIVERED file print-correct? (ORCH's four questions)

Sections 1-6 measured the **TIFF writer**.  This section measures the **26 files
we actually hand over**, which turn out not to be the same artefact at all.

## 7.1 The instrument, commissioned before any verdict

`png_probe.py` parses PNG chunks directly rather than asking an imaging library,
because the state that had to be distinguished is *absent* from *present and
equal to the library's default*, and a normaliser cannot express that
difference.  It keeps three states apart by construction: `ICCP` (a real
embedded profile), `SRGB` (the 1-byte sRGB chunk -- an intent flag, not a
profile) and `ABSENT`.

ORCH set the bar: *"a profile reader that returns 'sRGB' for a file with no
profile at all is the same failure -- give it a file you have stripped and
require it to report absent, not a default."*

`commission_png_probe.py`, **5/5 PASS**.  The load-bearing arm is not the strip,
it is the **plant**: the reader reported ABSENT on 26/26 delivered files, and a
reader with a broken `iCCP` branch prints exactly that, on every input, forever.
Only an input that certainly *has* a profile can separate those.

    ARM1  plant a real ICC (Windows sRGB, 3144 B)  -> ICCP, md5 1d3fda2edb4a,
                                                     desc "sRGB IEC61966-2.1",
                                                     space "RGB "        PASS
    ARM2  plant only the sRGB chunk               -> SRGB, icc is None    PASS
    ARM3  plant pHYs at 11811 px/m                -> reads 300.0x300.0    PASS
    ARM4  strip the iCCP back out                 -> ABSENT, no default   PASS
    ARM5  corrupt a CRC                           -> reported, not eaten  PASS

## 7.2 Q1 -- is a profile embedded, and is it the right one?

**Two different answers, because there are two different artefacts.**

| artefact | n | depth | ICC | XRes/Unit |
|---|---:|---:|---|---|
| `acceptance\SHIP-V4\*.tiff` (the masters) | 26 | 16 | **26/26**, one profile, `strehl sRGB (IEC 61966-2-1)`, md5 `d79b117b6798` | **300 / inch** |
| `DELIVER-V5\full-resolution\*.png` (**what we ship**) | 26 | 8 | **0/26 -- ABSENT** | **absent** |

The 16-bit masters are **correct**, and correct in the strong sense the brief
demanded: one profile across all 26, and it is sRGB because those masters were
rendered `--srgb`.  The three-way rule from section 1 still holds -- camera-native
gets no profile rather than a wrong one.

**The delivered PNGs carry nothing at all.**  Not a profile, not even the 1-byte
sRGB chunk.  Every consumer -- Photoshop, Lightroom, a print shop, a browser --
assigns its own working space and the colour silently shifts.  The metadata is
manufactured correctly by `image_out.rs` and then **discarded at the delivery
step**: `experiments/DELIVER-V5/build.py` reads the master with `tifffile`,
converts to `uint8`, and saves through PIL without passing any of it on.

**So the defect is not in the writer.  It is that the delivery throws the
writer's work away.**

## 7.3 Q4 -- DPI

- Masters: `XResolution` (tag 282) `= 300/1`, `YResolution` (283) `= 300/1`,
  `ResolutionUnit` (296) `= 2 (inch)`, on 26/26.
  At 7040x4688 that declares a **23.5 x 15.6 inch** print.  A DPI tag is a
  statement of intended print size, not a measurement, and 300/inch is the
  conventional choice for photographic print; it is honest and meaningful.
- Delivered PNGs: **no `pHYs` chunk on any of the 26.**  No declared print size.

## 7.4 Q2 -- is 8-bit sRGB actually costing us anything?

Measured, not asserted, and measured **paired**: we hold both the 16-bit master
and the 8-bit file derived from it, so this is the exact gradation the 8-bit
step destroyed, against the file that still contains it.

### The instrument, and the two defects commissioning found in it

`commission_banding.py`, **7/7 PASS** -- but only after it failed twice, and both
failures were real defects in my own detector:

1. **An absolute threshold that nothing could reach.**  I gated at `dL* >= 0.5`.
   Measured over the whole scale (`dl_range.py`), dL* per 8-bit sRGB code spans
   **0.274 to 0.509** -- only **5 codes of 254** clear 0.50.  Planted ramps with
   8 px and 40 px treads, textbook visible banding, fired on 3 of 9 tiles because
   the ramp walked out of that 5-code window.  **A gate nothing can satisfy
   certifies everything.**
   The deeper point is why: dL*/code varies by a factor of only **1.86 across the
   entire tone range**.  That is the sRGB transfer curve doing its job -- it
   exists to make one code step perceptually near-uniform.  So dL* is a property
   of the *encoding*, not of the image, and it cannot be the discriminating
   variable.  **Tread width is the only free one.**  The gate moved to tread,
   with dL* retained at 0.30 where it binds on exactly the 11 deepest codes.
2. **A perverse response to a planted degradation.**  Arm Q6 quantised a banded
   ramp *harder*, to 6 bits.  Treads got 4x wider -- and the banded fraction
   **fell from 100% to 66.7%**.  Tiles crushed to a single flat code scored
   `dL* = 0` and were certified clean, so the worse the damage the better the
   score.  Total gradation loss is the most severe banding available, not the
   least.  **A degradation-only suite cannot see this**; it is visible only
   because the ladder plants in both directions.

Final arms, all passing:

    NULL  real tweezers-cpl              0.0%    must stay quiet
    R1    noise-free, tread ~3 px        0.0%    0.25 mm: correctly invisible
    R2    noise-free, tread ~8 px      100.0%    must fire
    R3    noise-free, tread ~40 px     100.0%    must fire
    Q6    R3 at 6 bits                 100.0%    coarser must not score better
    DITH  R3 + 0.6-code noise            0.0%    IMPROVEMENT: dither must quiet it

### The corpus result

78 strata are possible (26 subjects x 3 tone strata).  **50 measured + 28 EMPTY
= 78**, an exact partition -- an empty stratum prints `EMPTY -- no tiles, NOT a
pass` and can never be read as a clean one.

Quantisation *is* severe: in smooth tiles the 16-bit master carries **850-4,700
distinct levels** where the 8-bit file carries **5-37**.  And it does not matter,
because the treads are **1-2 px** (0.085-0.169 mm at 300 dpi) rather than the
wide plateaux banding needs.

**49 of 50 strata read 0.0% banded.  One does not:**

    6.7%   dry-erase-marker-head-cpl [high]   tread 0.169 mm   sigma 0.28 code

**That subject is tied for the lowest noise in the corpus.**  Across all 50
strata (`corpus_sigma.py`, 2,391 tiles) sigma runs **0.28 to 3.84 codes**, and
the two strata at the 0.28 floor are `dry-erase-marker-head-cpl [high]` and
`coffee-bean [high]`.

**One of those two bands and the other does not, so low noise is necessary and
not sufficient.**  The mechanism ranks correctly -- the only banded stratum in
the corpus sits at the noise floor, and nothing above 0.31 bands at all -- but it
does not uniquely predict, and the honest statement is the weaker one.  What
separates the pair is the tread distribution: `dry-erase` is a smooth white
plastic barrel whose highlight ramps run further before turning over.  A claim
that the mechanism "predicted the failing subject" would have been a story
fitted to one cell after the fact.

### The margin is thin, and strehl's own headline win is what eats it

`dither_margin.py` sweeps dither on a 40-px-tread ramp (180 tiles/rung, 5 seeds;
monotone non-increasing within 3 binomial SE -- the worst rung rises 3.3 pp
against a 5.4 pp tolerance, and an exact-monotonicity test failed on sampling
noise before that tolerance was made principled):

    banded < 50%  at sigma ~ 0.05 codes
    banded <  1%  at sigma ~ 0.25 codes
    banded ==  0% at sigma ~ 0.30 codes

    corpus minimum sigma        0.28 codes
      margin vs 1% crossover    1.12x   consumed by 1.3x more frame averaging
      margin vs 0% crossover    0.93x   -- already below it

**Noise is the only thing making 8 bits safe here, and reducing noise is
strehl's headline result (2.4x over the fork).**  A merge averages frames and
sigma falls as 1/sqrt(N), so the quality axis the project leads on is the axis
that removes the dither.  A 1.3x increase in effective averaging puts the
quietest subjects under the threshold.  This is a real coupling and it is not
currently gated anywhere.

## 7.5 Q3 -- should a 16-bit path be added?

**No, because it already exists, and it is already correct.**  Not a plan, not a
prototype: 26/26 shipped masters carry the right profile and 300 dpi/inch today,
verified end to end by `ship_census.py` on all 26 -- stronger than the three
subjects the brief asked for.

**No Rust was changed.  `git status -- crates/` is empty, so no byte-freeze can
have moved by my hand.**  The correct fix costs no compiler:

1. **Ship the existing 16-bit TIFF masters as the print deliverable.**  They are
   correct now.
2. **The 8-bit PNGs are web previews, and even as previews they are wrong** --
   an untagged PNG is guessed at by every consumer.  They need at minimum the
   1-byte `sRGB` chunk and a `pHYs` at 300 dpi.  That is a change to
   `experiments/DELIVER-V5/build.py`, which is not mine; routed, not taken.

On the evidence, 8-bit is *adequate today* for 25 of 26 subjects and marginal on
the 26th -- but it is adequate by an accident of sensor noise that the project is
actively working to remove, and the masters that do not depend on that accident
already exist.

## 7.6 What I did not verify

- I did not re-run the Rust byte-freeze suite.  I did not need to and could not
  attribute a failure if I had: nine lanes are editing `crates/` concurrently and
  I changed none of it.  The claim is the stronger one -- **zero Rust diff**.
- The 6.7% stratum on `dry-erase-marker-head-cpl` is a *detector* verdict at
  0.169 mm treads.  I have not viewed it at 1:1 on a calibrated display, and per
  rule 48 the `view` tool resamples above ~400 px so I could not have.  Whether
  that 6.7% is visible in a print is untested.
- `MIN_TREAD_MM = 0.5` is a literature acuity threshold, not one this project
  measured.  It is stated so it can be moved, and every raw tread is printed.
