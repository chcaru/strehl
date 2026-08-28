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

# 8. Making the delivery print-correct

Section 7 established the defect: `image_out.rs` was embedding
`strehl sRGB (IEC 61966-2-1)` and 300 dpi on 26 of 26 masters, and the delivery
step was casting to uint8 through PIL and passing none of it on -- 0 of 26
shipped PNGs declared a colour space or a print size.  This section is the
repair, and it is deliberately a *delivery* repair: the Rust writer was never
wrong, so the Rust diff here is again **zero**.

## 8.1 Why chunk splicing and not a re-save

The binding constraint was that **pixels must not change** -- ORCH's
`verify_delivery_all26.py` compares decoded pixels against the masters and had
to still read 26 exact / 0 differing afterwards.

Re-saving through PIL to attach metadata would re-run the deflate compressor
over the samples.  The output *should* be pixel-identical, and "should be" is
not the standard this project works to.  Splicing chunks into the byte stream
instead cannot alter image data because it never touches IDAT: the guarantee is
**structural rather than tested**, and the test then confirms a property that
was already true by construction rather than being the only thing standing
between the deliverable and a silent re-encode.

`tag_png()` in `experiments/DELIVER-V5/build.py` parses the chunk stream,
verifies every CRC on the way in, drops any pre-existing
`iCCP`/`sRGB`/`gAMA`/`cHRM`/`pHYs`, and inserts `iCCP` + `pHYs` immediately
after IHDR -- a position that satisfies the ordering rules for both.  The write
is atomic via `os.replace`, so an interruption cannot leave a torn 60 MB file in
a deliverable.

**The profile is copied out of a shipped master rather than synthesised.**  That
is the difference between the preview *claiming* the same colour space as the
print master and being *checkably* the same: the md5 of the profile read back
out of the PNG equals the md5 read out of the TIFF.  A synthesised profile would
have made the same claim untestably.  `iCCP` alone, not the 1-byte `sRGB` chunk,
and not both -- the PNG spec says a file should not carry both.

## 8.2 Commissioning the tagger before running it on 1.2 GB

The whole change rests on "pixels did not change".  **A comparison that cannot
detect a change confirms that claim on any input**, so arm A2 is not decoration;
it is what gives A1 meaning.  `commission_tagger.py`, 6 of 6 PASS on a real
delivered crop:

| arm | claim | result |
|---|---|---|
| A1 | decoded pixels identical after tagging | PASS, `(398, 380, 3)` both sides |
| A2 | **NEG CONTROL** -- `+1` in one channel of one pixel is detected | PASS, 1 differing pixel |
| A3 | profile read back equals the **master's**, by md5 | PASS, `d79b117b6798` both sides |
| A4 | `pHYs` reads 300 dpi | PASS, 300.0 x 300.0 |
| A5 | idempotent -- second tagging is byte-identical | PASS, 227287 bytes |
| A6 | IDAT bytes literally untouched | PASS, `26205c824ecfe437` unchanged |

A5 matters because the retag pass runs over a tree that may already be partly
tagged; A6 is the structural claim of section 8.1 stated as a measurement.

## 8.3 What landed

`python build.py --retag` tagged **185 of 185 PNGs in 10.1 s, 0 failed**, with
the profile taken from the master (2716 bytes, md5 `d79b117b6798`).

`delivery_audit.py` then re-read every file and partitioned it.  The partition is
exhaustive by construction and the script asserts it sums, because a summary that
counts only successes cannot distinguish a file that passed from a file that was
never examined:

| directory | n | outcome |
|---|---:|---|
| `crops-1to1/` | 78 | profile+dpi OK x78 |
| `crops-worst-case/` | 52 | profile+dpi OK x52 |
| `full-resolution/` | 26 | profile+dpi OK x26 |
| `known-defects/` | 1 | profile+dpi OK x1 |
| `overview/` | 26 | profile+dpi OK x26 |
| `what-stacking-does/` | 2 | profile+dpi OK x2 |
| **partition** | **185** | OK 185 / no profile 0 / wrong profile 0 / no-or-wrong dpi 0 = **185 == 185 found** |

One distinct profile across all 185: `d79b117b6798  strehl sRGB (IEC 61966-2-1)`.

The 16-bit print deliverable was copied to `DELIVER-V5\print-masters\` (26 files,
4.79 GB) and censused **on the copies, not the sources** -- a copy is not a
verification.  26 of 26, 16-bit, `strehl sRGB (IEC 61966-2-1)` md5
`d79b117b6798`, `(300.0, 'inch')`, 0 not at 300 dpi.

## 8.4 The gates, before and after

| verifier | owner | before | after |
|---|---|---|---|
| `verify_delivery_all26.py` | ORCH | 26 exact / 0 differing, GREEN | **26 exact / 0 differing, GREEN** |
| `check_readme.py` | DELIVER-V5 | pass 24 + fail 0, exit 0 | **pass 24 + fail 0, exit 0** |
| `verify.py` | DELIVER-V5 | corruption caught 104 + missed 0, exit 0 | **corruption caught 104 + missed 0, exit 0** |

No count moved, so `manifest.json` did not need to move either.  Adding a
top-level `print-masters/` directory tripped nothing: `check_readme.py` asserts
counts *within* named directories and does not enumerate the tree root.

`delivery_audit.py` exits non-zero unless all 185 are green, so the metadata is
now a **gated** property of the deliverable rather than a number in a log.

## 8.5 Two things that are still wrong, and one is not mine to fix

- **The upstream writers still emit untagged PNGs.**  `build.py` writes only
  `overview/` and `crops-1to1/`, and those two now tag at the point of save.  The
  other 81 files -- `full-resolution/`, `crops-worst-case/`, `known-defects/`,
  `what-stacking-does/` -- are written by scripts under
  `experiments/ORCH-drift-check/`, which this lane does not own.  `--retag` fixes
  the artefact; it does not fix the source.  **A fresh run of those scripts will
  re-emit untagged files**, and that is routed to the orchestrator rather than
  silently patched in another lane's code.
- **The delivered README's directory table omits `full-resolution/` and
  `crops-worst-case/`.**  Pre-existing, in ORCH's half of the deliverable, and
  reported rather than fixed.  I added the `print-masters/` row because I created
  that directory.

## 8.6 The product statement

> **Print from `print-masters/`. The PNGs are previews.**  The 8-bit previews are
> safe to print from for 49 of the 50 tone regions measured across all 26
> subjects, but `dry-erase-marker-head-cpl` bands across 6.7% of its highlights,
> and the corpus as a whole sits at 0.93x the noise level at which banding
> disappears entirely -- so 8 bits is clean here only because sensor noise
> happens to dither it, and a subject smoother or cleaner than the ones measured
> has no margin left.

The second clause is the one with a future in it.  Banding in a smooth ramp is
suppressed by noise; this stacker's headline result is that it produces *less*
noise than the alternatives; those two pull against each other.  The measured
floor across 2,391 tiles is sigma = 0.28 codes against a zero-banding threshold
of 0.30 -- a 7% margin, spent by the very improvement the project is chasing.
Shipping 16-bit masters removes the question instead of managing it.

# 9. The CFA per-plane admission hypothesis: refuted twice, and no patch written

ORCH proposed a mechanism for a chroma-versus-luma asymmetry: that the CFA-native
merge takes its admission decision **independently per plane**, so the four
planes at one photosite can admit different frame sets; luma sums and cancels the
disagreement, chroma differences and amplifies it.  The instruction was to
establish what the code does, measure the mechanism before changing anything, and
**stop and say so if the mechanism could not be detected**.

It could not be detected, for two independent reasons.  No Rust was changed and
none should be.

## 9.1 The path I first read was not the shipped path

`Estimator::fold_inner` in `merge.rs` takes exactly one gate decision per quad
and applies it to all four planes.  That is true and it is **not the answer**,
because the estimator is not what shipped.

`DEFAULT_MERGE_BACKEND` is `MergeBackend::Pyramid` (`merge_cmd.rs:417`,
`5142ace5c`), and all 26 SHIP-V4 logs carry one banner:

    strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)

26 of 26, no other value.  **A structural claim about the wrong path is worth
nothing**, and I nearly filed one: `merge_cmd.rs:435` still tells the user
`estimator` is "the default".  That string was written in `c42cd7543` on
2026-08-25, one day before `5142ace5c` moved the default to pyramid on 08-26 and
did not update it.  It is a live defect in a file this lane does not own, and it
is reported to BUILD-PLUGIN rather than touched.

## 9.2 In the shipped merge the decision is already joint, by construction

`pyramid.rs`, `BandMerge` (`1bb1f0f54`):

| field | indexing | meaning |
|---|---|---|
| `num` | `[level * planes + plane]` | `sum(w * L)`, per plane |
| `usum` | `[level * planes + plane]` | `sum(L)`, per plane |
| **`den`** | **`per_level()` -- level only, NO plane index** | **`sum(w)`, shared by every plane** |

`den` is built by `let per_level = || sizes.iter().map(|s| vec![0.0; s.pixels()])`
at `pyramid.rs:1185` -- one vector per level, no plane term.  In `accumulate_level`
the denominator is fetched *outside* the plane loop (`let den = &mut self.den[k]`,
1534) and the same weight field `w` multiplies every plane (`num[i] += w[i] *
lv[i]`, 1545).  At output, `out[j] = num[j] / den[j]` (1870) divides every plane
by the same number.

The weights come from green luma alone: `add_frame` takes `planes: &[&[f32]]` and
a **separate** `luma` argument documented at 1316 as "the plane the selection is
made on -- green luma".

So the four planes cannot admit different frame sets.  There is one weight field
per (level, pixel) and every plane is normalised by it.

**The design anticipated ORCH's mechanism and rejected it, in ORCH's own terms.**
`pyramid.rs:1138-1141`: "Shared by every plane, because the selection is made on
green luma only ... letting a colour plane's own noise drive the decision is how
chroma noise becomes structure."  And `f8b99f27a` at 798: "Selected on the GREEN
plane alone and then applied to every plane ... a per-plane decision would let
chroma noise elect itself into structure."  **The proposed fix is the shipped
architecture.**  The estimator path carries the same rule independently --
`merge.rs:1640` says a per-plane admitted count is something "the estimator
deliberately does not carry".

## 9.3 The premise is inverted, on the table it was drawn from

The mechanism exists to explain "chroma is worse than luma in all four chroma
cells".  The cells come from `V-REVIEW-noise-verification.md` section "The
cells", whose section 8 states the convention explicitly: **"Ratio of medians,
comparator over strehl"** -- above 1.0 means strehl is quieter, so a *higher*
ratio is *better* and "chroma worse" means the chroma ratio sits *below* the luma
ratio for the same comparator.

`chroma_premise.py`, each chroma cell against its **own** comparator's luma cell:

| comparator | channel | ratio | its luma | delta | verdict |
|---|---|---:|---:|---:|---|
| `enfuse` | B-Y | 1.606 | 1.618 | -0.7% | not distinguishable (intervals overlap) |
| `enfuse` | R-Y | 1.813 | 1.618 | **+12.1%** | **BETTER than luma**, intervals disjoint |
| `focus-stack` | B-Y | 1.640 | 1.475 | **+11.2%** | **BETTER than luma**, intervals disjoint |
| `focus-stack` | R-Y | 1.661 | 1.475 | **+12.6%** | **BETTER than luma**, intervals disjoint |

worse 0 / better 3 / not distinguishable 1 = 4 chroma cells.  **PREMISE REFUTED.**

The test is potent: planting a corpus where chroma really is worse convicts 4 of
4.  A checker that could only ever print "refuted" would be worthless.

**Honest limit.** The two intervals share a denominator -- same strehl render,
same tiles -- so they are positively correlated and comparing them for overlap is
*conservative*.  Disjointness proves a difference; the overlapping `enfuse` B-Y
cell proves nothing either way and is not claimed as evidence in either
direction.  A paired tile-level resample would be sharper and that data is not in
the published table.

## 9.4 Where the flat-field observation probably belongs

ORCH saw `enfuse` look cleaner in a large flat field while the gauge says strehl
is 1.618x quieter in luma there.  Both can be true: **the gauge measures noise
amplitude and the eye in a flat field responds to its spatial spectrum.**  A
per-tile sigma is blind to low-frequency mottle.

That is not speculation about an unexamined axis -- it is already convicted.
`orch_mottle_visual.py` names `lead-1-cpl` at **2.43x (chroma)**, `coffee-bubbles`
at 1.4501x, `113MSDCF` at 1.30x, and points at the two instruments whose
construction is admissible because they **ratio the master against the frames
that made it**: `experiments/V-GATHER/` and `experiments/V-NEVERWORSE/`.  ORCH's
own visual check was refuted for lacking exactly that ratio.

So the chroma defect that does exist is subject-specific mid-scale mottle
measured against source, not a corpus-wide luma/chroma asymmetry, and not a gate
that never existed.  **That is where the effort should go**, and this lane did
not take it because `V-GATHER` and `V-NEVERWORSE` belong to other lanes.

## 9.5 What I did not do, deliberately

- **No correlation measurement between per-plane admitted sets.** Its precondition
  is false: there is one admitted set, so the disagreement is identically zero by
  construction and a correlation against it is undefined, not merely null.
- **No patch.** The requested fix -- one decision per photosite applied to all
  four planes -- is what `pyramid.rs` already does. Implementing it would have
  been a no-op dressed as a repair.
- **No sharpness arm.** Nothing changed, so there is nothing to hold.

# 10. A single re-certification harness

ORCH's problem, stated exactly: promoting a candidate binary means re-rendering
26 masters, re-running the print gate, re-running the head-to-heads and updating
the README by hand, and **if that takes hours the fix lane can only afford one
attempt.** The ask was one entry point that turns promotion into a decision
rather than an interpretation, plus the one number nobody had -- how long a full
re-certification actually takes on this machine.

`experiments/BUILD-RECERT/recert.py` is that entry point. Six timed stages:
`identity` (SHA-256, and a refusal list), `render` (26 masters through the
existing `scripts/finalpass.ps1`), `gate` (`orch_printready.py` through its own
entry point, so it may gain checks without this file changing), `pair` (every
noise number paired with a sharpness number on the same pixels), `h2h` (both
comparators on the published sites), `verdict`.

**Three findings below change the task rather than merely reporting on it, and
two of them are about the instrument I was told to trust.**

## 10.1 The baseline I was given does not reproduce

ORCH's brief states the print gate reads **17 PASS / 5 FAIL / 4 REFUSED**. I ran
it before building anything against it:

```
python experiments/ORCH-drift-check/orch_printready.py C:\dev\strehl-out\acceptance\SHIP-V4
  -> 17 PASS / 0 FAIL / 9 ACQUITTED / 0 EXPIRED / 0 REVIEW / 0 NOT EXAMINED
     exit 0, wall 180.2 s
```

**17 / 0 / 9, not 17 / 5 / 4.** The five failures and four refusals have since
been adjudicated into nine acquittals. Had the harness diffed against the quoted
numbers it would have reported **five spurious "FAIL -> PASS" improvements** on
the first candidate -- a harness manufacturing a win for a fix that had not
landed yet. A baseline is a measurement with an expiry date, so `recert.py`
measures its own and caches it (`logs/baseline-gate.json`) rather than carrying
a number in a docstring.

## 10.2 The gate cannot certify the subjects the fix is aimed at

The nine acquittals are `112MSDCF`, `113MSDCF`, `coffee-bubbles`,
`couch-fibers-cpl`, `flat-on-ruler-cpl`, `flower-inner-edge-cpl`, `foam`,
`lead-1-cpl`, `leaf-2-cpl`.

Cross them against the six subjects convicted of mid-scale mottle -- the defect
the pyramid fix exists to remove -- `coffee-bubbles`, `lead-1-cpl`, `113MSDCF`,
`flat-on-ruler-cpl`, `112MSDCF`, `foam`. **All six are inside the nine.**

An acquittal is pinned to a rendered value and expires when the render moves by
more than `ACQUIT_TOL` (5%). So a candidate that changes exactly the subjects it
was built to change **expires its own acquittals by construction**, and an
expired acquittal is not a pass -- it is an unadjudicated subject. The headline
`17 PASS` would be unchanged while the six subjects under test quietly left the
counted set. `recert.py` therefore separates two things the gate reports as one:
`PASS -> FAIL` regressions, and `ACQUIT -> EXPIRED`, and refuses promotion on
either. **The gate is sound; it simply was never built to adjudicate a change to
its own pinned subjects, and nothing in its output says so.**

## 10.3 Every noise number is paired with a sharpness number, or it is not reported

This is the property ORCH called non-optional, and the reason is on the record:
`focus-stack` reads 0.077 fine grain and 0.260 mid-band on
`119MSDCF__worst-on-subject`, 10-25x below both other arms, **because it is
blurred, not because it is clean.** A candidate can win every blotch number the
same way.

`recertlib.py` measures three bands, defined by importing `boxblur` and `srgb`
**from `orch_eye_check.py`** so they cannot drift from ORCH's:

| band | filter | scale | cyc/px | sharpness admissible |
|---|---|---|---|---|
| `grain` | `p - box(1)` | <= 3 px | >= 0.33 | **no** |
| `struct` | `box(2) - box(6)` | 5-13 px | 0.077-0.20 | yes |
| `mottle` | `box(10) - box(30)` | 21-61 px | 0.016-0.048 | yes |

`grain` carries no sharpness verdict on purpose: it sits above the 0.30 cyc/px
band this project has already withdrawn its resolution claims above. A statistic
is not admissible merely because it is computable.

Each cell reports a noise `floor` (MAD) and a `structure` amplitude, and the
verdict is driven by

```
paid = d_structure / d_floor      (computed ONLY where the candidate is quieter)
```

-- how much structure the candidate spent per unit of noise it removed.
`PAID_MAX = 0.25` is the harness's single absolute threshold and it is the only
number here that had to earn one.

## 10.4 Commissioning the measurement: three failures, and each was the metric

`commission_bands.py` (8 arms: null, narrow blur, wide blur, band-confined
denoise, blur ladder, heavier-blur non-reward, threshold invariance, degenerate
crop). It failed three times before passing, and every failure was a real defect
in my metric rather than a mis-set expectation:

1. **A broken measurement read as a clean result.** The MAD floor collapses to
   exactly 0 on crops more than half clipped black; `ratio` becomes `nan`; and
   `nan` fails every comparison, so the cell classified as **HELD**. A
   degenerate crop must **REFUSE**, never pass.
2. **`peak` is not a pure structure statistic.** p99.5 carries a noise term
   proportional to the floor, so *removing* planted band noise scored as a blur
   with `paid` = 1.06. The noise term is now measured per band from a pure-noise
   residual (`NOISE_PEAK`: 2.82 `struct`, 2.88 `mottle` -- not the Gaussian
   2.807, because box-difference filters correlate their input) and removed in
   quadrature.
3. **A plant must live in the band it tests, and must be shown to have landed.**
   White noise cannot move a 21-61 px band and a sigma=1.5 blur cannot move a
   crop whose floor is already 4.24 codes. An unlanded plant leaves a cell
   UNTESTED, and an untested cell is not a passed one.

It passes at **59 PASS / 0 FAIL / 7 REFUSED = 66 cells**, the partition sums,
every arm has at least 3 genuinely tested cells (`MIN_TESTED`, so an arm that
refuses everything cannot certify itself), and planted denoise (`paid` max
**0.000**) is cleanly disjoint from planted blur (`paid` min **0.406**) with
`PAID_MAX` = 0.25 between them.

## 10.5 Commissioning the harness is not the same test as commissioning the metric

A sound metric can still sit under a harness that promotes a blurred arm,
because aggregation is exactly where a trade goes missing.
`commission_recert.py` builds fake candidate arms out of the shipping masters
and runs the **real** pairing stage and the **real** verdict function over them.
4 / 4 arms:

| arm | what it is | required | got |
|---|---|---|---|
| NULL | byte-copy of the baseline | PROMOTABLE, all HELD | 45 cells, `d_floor` and `d_structure` both +0.0000 |
| DEGRADED | baseline blurred | NOT PROMOTABLE, naming structure | 12/12 `struct` cells BLUR_TRADE |
| IMPROVED | baseline noised, arm is the clean master | scored as an improvement | 12/12 `struct` cells CLEANER |
| INCOMPLETE | arm missing masters | INCONCLUSIVE | INCONCLUSIVE |

The load-bearing row is DEGRADED, and the reason is in its own numbers:

```
grain   median d_floor -0.7301 (quieter)   median d_structure -0.6026 (softer)
struct  median d_floor -0.1701 (quieter)   median d_structure -0.1539 (softer)
mottle  median d_floor -0.0108 (quieter)   median d_structure -0.0133 (softer)
```

**The blurred arm is quieter in all three bands.** Every noise statistic in the
project improves on it. A harness that scored noise alone would have promoted
it. This one refuses it and says why. And IMPROVED is the arm that stops the
opposite failure: it is quieter *and* structure **rises** (+0.0149), which is
what separates a metric that is merely conservative from one that can recognise
a genuine win. A suite of degradations alone cannot tell those apart.

## 10.6 A fix that was inert, and a control that shared its bug

The first full run rendered **zero masters**. `finalpass.ps1` died on
`Get-FileHash : The term ... is not recognized` -- a core cmdlet missing from a
shell that was otherwise working, which reads as a broken install and is not
one. This process runs under `pwsh` (PowerShell 7) and exports PowerShell 7's
`PSModulePath`; Python inherits it; `powershell.exe` (5.1) inherits it in turn
and cannot autoload `Microsoft.PowerShell.Utility` from 7's directories.

Two things are worth recording, and the second is the useful one.

**The verdict function certified this run.** Invoked with the render stage
producing nothing, the first version printed `VERDICT: PROMOTABLE`, because it
searched for reasons to refuse and an empty result set supplies none. Absence of
evidence was being read as evidence of absence. A verdict now requires its
evidence to exist and names the stage that is missing.

**The fix I wrote for the module path was inert, and my control said so.** It was
`dict(os.environ).pop("PSModulePath")`. On Windows `os.environ` is
case-insensitive with keys stored UPPER-CASED, so `dict()` of it yields a plain
dict keyed `PSMODULEPATH` and the pop matched nothing. `control_launcher.py`
then printed `PSModulePath: <unset>` for a variable that was plainly set, and
**refused to run** -- the right outcome reached through the identical bug, since
its diagnostic read the same plain dict. A fix and its own check sharing a defect
is precisely how an inert repair certifies itself. The refusal is what saved it:
had that control been written to pass on a clean arm rather than to demand a
reproduced failure, it would have gone green against a fix that did nothing.

Measured, three arms, one probe:

```
powershell, env as-is             exit 1   Get-FileHash not recognized
powershell, PSModulePath = 5.1's  exit 0   8DD1EBB0
pwsh,       env as-is             exit 0   8DD1EBB0
```

and end to end through the real launcher:

```
A  powershell 5.1, PS7 module path inherited : 0 master(s), 'is not recognized' PRESENT
B  pwsh + _ps_env()                          : 1 master(s), 'is not recognized' absent
CONTROL PASSED
```

## 10.7 The head-to-head digest check could never have passed

The published half-bracket is verified by a frame digest, `5e1f4bf433effb2c`,
recorded in `V-NOISE2\119\logs\align-A.log`. My first `h2h` stage scraped it
from `strehl stack`'s output -- and **`stack` does not print it; `align` does.**
The stage refused on every run, with a message that reads like a finding about
the frame set rather than what it was: a check nothing could satisfy. It is the
same shape as ORCH's inert cap sweep and as the `dL* >= 0.5` gate that 5 codes of
254 could reach, and it is the third instance tonight of a threshold placed
outside its own reachable range.

Asking the command that actually emits it, against the reconstructed bracket:

```
strehl align <half-A> --out <scratch>
  stack half-A: 17 frames, digest 5e1f4bf433effb2c        (5.2 s)
  published                     5e1f4bf433effb2c          MATCH
```

This also settles an assumption the harness had been carrying untested: that
half-A is the 17 **even-indexed** frames of the 33 in `D:\personal\macro\119MSDCF`.
It is. `--out` is mandatory on that call -- `align`'s default target is the
shared warp-map cache that every other lane's `stack` reads, and a verification
step must not write into the input of nine concurrent runs.

## 10.8 The null re-certification, and the number ORCH asked for

The harness was run end to end with **the shipping pin as the candidate**. This
is simultaneously the end-to-end test and the strongest available self-test: the
correct answer is that nothing moved anywhere, so any movement is the harness's
own noise rather than a property of a candidate.

```
identity  0.0s      44C2F2CD2E5B2894... == the shipping pin
render    2682.6s   26 master(s), COMPLETE.txt present
gate      472.2s    baseline  17 PASS, 0 FAIL, 9 ACQUITTED ... 26 total (found 26)
                    candidate 17 PASS, 0 FAIL, 9 ACQUITTED ... 26 total (found 26)
                    no subject changed state
pair      110.9s    390 cells; all three bands d_floor +0.0000  d_structure +0.0000
h2h        15.0s    half-A verified: 17 frames, digest 5e1f4bf433effb2c == published
TOTAL     3280.8s
VERDICT: PROMOTABLE
```

**A full re-certification takes 54.7 minutes**, of which 82% is the render, on
this machine with between two and five other lanes rendering concurrently. The
render sustained **105.5 frames/min** over 4,825 frames -- `finalpass.ps1`'s own
`-WhatIfTiming` projects 119 min at 1.48 s/frame, so the projection is **2.7x
pessimistic** and should not be used to plan against.

The null is exact rather than merely small, and it was confirmed independently
of the metric:

```
26 byte-identical / 0 differing / 0 missing   (SHA-256, RECERT-NULL vs SHIP-V4)
```

All 26 masters reproduce the shipped bytes, **including all 26 `--auto-exposure`
choices** -- the confound the provenance file explicitly warns about ("may
choose differently") does not fire for an identical binary. The pairing stage's
`+0.0000` is therefore not a metric too dull to see a difference; there is no
difference to see, and the two facts were established by different instruments.

## 10.9 How many attempts the fix lane can afford

54.7 minutes per full pass answers ORCH's question pessimistically, because a
candidate does not need a full pass to be triaged. Measured, not projected, on
the six mottle-convicted subjects via `--only`:

```
render 576.7s   gate 93.6s   pair 35.1s   TOTAL 705.4s = 11.8 min
VERDICT: PARTIAL (6/26 subjects: ...) -- PROMOTABLE ... NOT a full certification
90 cells, all three bands d_floor +0.0000  d_structure +0.0000
```

**11.8 minutes to score a candidate against the subjects it was built to
change.** So the fix lane can afford roughly **five triage attempts per hour**,
and needs the 54.7-minute full pass only once, before promotion. That is the
difference between one attempt and five, which was the point of the exercise.

The targeted run also produced the empirical confirmation of 10.2. The gate on
those six subjects alone reads:

```
candidate : 0 PASS, 0 FAIL, 6 ACQUITTED, 0 ACQUITTAL EXPIRED, 0 REVIEW, 6 total (found 6)
```

**Zero of the six are passes. All six are acquittals.** The subjects the fix
exists to repair contribute nothing to the headline `17 PASS`, and the moment a
candidate moves their renders by more than 5% they become EXPIRED -- still not
failures, still not passes, simply unadjudicated. A harness that watched only
`PASS` and `FAIL` would report a perfect score for a candidate whose entire
effect had vanished into a third category.

## 10.10 What I did not verify

- **That the harness detects a real regression in a real candidate.** Every arm
  here is either the shipping pin or a synthetic perturbation of its output. The
  degradation and improvement arms are commissioned (10.5) but they are planted,
  not merged. Nothing has yet been scored on a genuinely different binary.
- **The `h2h` stage on more than one subject.** It measures `119MSDCF` at the
  three published sites because those are the sites whose fits are recorded in
  the manifest. Its comparator arms are fixed 17-frame artifacts and are not
  rebuilt; a second subject would need its own published manifest.
- **`PAID_MAX = 0.25` beyond its commissioning range.** It is subject-invariant
  across the 6 subjects x 4 crops of arm F, with planted denoise at `paid` max
  0.000 and planted blur at min 0.406. That is a gap, not a proof, and a
  candidate landing between 0.25 and 0.406 is in territory this threshold has
  not been tested in. It should be re-commissioned if one ever does.
- **Wall clock on an idle machine.** 54.7 min was measured with two to five
  other lanes rendering. It is an upper bound for a quiet machine, and I did not
  have one to measure.

# 11. The HEAD baseline: the shipping recipe blows the highlights

ORCH asked for a HEAD baseline rendered *before* the pyramid merge fix lands, so
that a future regression would be attributable to one change rather than to
twelve at once. The insurance paid immediately: the baseline is not a quiet
control, it is a stop-the-line defect.

## 11.1 It is fourteen commits, not eleven, and two of them are the merge

ORCH's brief listed 11 commits touching `crates/` since pin `9b05d0b7`. Measured
at the moment the pin was cut:

```
git log --oneline 9b05d0b7..HEAD -- crates/    ->  14
git diff --stat 9b05d0b7..HEAD -- crates/strehl-core/src/pyramid.rs crates/strehl-core/src/merge.rs
    crates/strehl-core/src/merge.rs   | 142 ++++++++++++-
    crates/strehl-core/src/pyramid.rs | 251 +++++++++++++++++++++--
```

Three commits landed while the brief was being written, and `pyramid.rs` and
`merge.rs` -- the two files the brief said a build lane owns and the baseline was
meant to precede -- had **already changed by 382 lines inside the delta**. The
baseline is therefore not "pin plus eleven unrelated commits"; it already
contains part of the merge work.

HEAD pin cut at `f190a0ea`, binary sha256 `332FA6AE8B8DA54C2BD90D8EA13683F736A0B68F7C4191C0F193BCE8938FD9C9`
(sha16 `332FA6AE8B8DA54C`), built to the same layout as `9b05d0b7`. Render: 26
masters, 4,825 frames, 46.9 min, 0.58 s/frame.

## 11.2 The measurement

Rendered with the byte-identical shipping ARGV -- `--srgb --auto-exposure`, same
source directories -- so the only variable is the binary.

| subject | frames | SHIP-V4 clip | HEAD clip | mean x |
| --- | ---: | ---: | ---: | ---: |
| `lead-1-cpl` | 123 | 0.0230% | **98.4836%** | 2.056 |
| `leaf-2-cpl` | 182 | 0.0326% | **95.2152%** | 2.075 |
| `couch-fibers-cpl` | 299 | 0.0721% | **88.5476%** | 1.427 |
| `109MSDCF` | 22 | 0.0012% | **85.5716%** | 1.296 |
| `wrapped-text-1` | 130 | 0.0329% | **81.6986%** | 1.348 |
| `119MSDCF` | 33 | 0.0007% | **72.4665%** | 1.249 |
| ... 16 more | | | | |
| `coffee-bean` | 105 | 0.0000% | 0.0000% | 0.932 |
| `coffee-bubbles` | 19 | 0.0007% | 0.0000% | 0.874 |
| `dry-erase-marker-head-cpl` | 299 | 0.0000% | 0.0000% | 0.916 |
| `foam` | 100 | 0.0020% | 0.0001% | 0.851 |

`clip` is the fraction of *samples* at or above 65500 of 65535. **22 of 26
subjects regressed; 4 held; the partition sums to 26.**

The four that held are exactly the four whose chosen exposure is **negative**
(mean ratio 0.851-0.932). That is not a coincidence and it is the mechanism
stated as a prediction: the damage tracks the sign of the gain.

## 11.3 The mechanism, measured rather than assumed

The image is already at the top of the scale before auto-exposure is applied.
SHIP-V4's p99.9, as a fraction of full scale:

```
bee-1-cpl                  65294 / 65535 = 99.63%
pencil-steep-angle-cpl     65303 / 65535 = 99.65%
bee-2-cpl                  64709 / 65535 = 98.74%
pencil-flatter-angle-cpl   64520 / 65535 = 98.45%
```

There is no headroom. A positive gain applied after that point cannot brighten
anything; it can only push values into the rail. The chooser selects +0.88 to
+2.60 stops on these subjects -- `109MSDCF` picks **+2.60 stops, a 6.063x linear
gain**, applied to an image already at 99% of scale.

The encoded ratio corroborates the placement. On `pencil-steep-angle-cpl` the
chosen gain is 2.445x linear and the measured mean ratio is 1.513; `2.445^(1/2.2)
= 1.50`. The gain is being applied **before** the sRGB curve, and the curve is
the only reason the visible change looks like 1.5x rather than 2.4x.

I inferred "something has already normalised the image" from output alone, which
is as far as pixels can take you. The code-level account is `5f367a94`'s and it
is more specific: `strehl stack` routes through `merge_cmd::run`, which gained a
tone stage but not the guard `stack.rs` already carried, and **the tone placement
and `--auto-exposure` are the same rule** (`p99.9 -> 0.90`). Applying both
multiplies an already-normalised image by its own chosen gain. That names the
duplication my measurement could only show the consequence of, and it is the
better statement of the mechanism.

## 11.4 Isolated to one flag, by a controlled two-binary run

The corpus render cannot separate `--auto-exposure` from the other thirteen
commits, because every master used both. So both binaries were run on
`coffee-bubbles` (19 frames) with `--srgb` and **without** `--auto-exposure`:

| | SHIP-V4 `44C2F2CD` | HEAD `332FA6AE` |
| --- | ---: | ---: |
| clip >= 65500 | 0.0007% | 0.0007% |
| crush <= 35 | 0.1261% | 0.1072% |
| mean | 3976.2 | 3984.3 (ratio 1.00205) |

and the band gauge over 5 content-selected sites x 3 bands reads **HELD in 15 of
15 cells**, every `|d_floor| <= 0.0184` and every `|d_peak| <= 0.0010`, both
inside the 0.02 tolerance.

**So the answer to ORCH's question is: the other thirteen commits did nothing
measurable, and `9cb7f5d9` did all of it.** The formal census agrees on the
chooser's innocence -- 24 of 26 subjects choose the *same* exposure at HEAD as at
the pin, and the two that differ do so by 0.01 stops. The chosen value did not
change. Its application did.

Sites were selected on the **base** arm only. Choosing them on the candidate
would have let the candidate pick the ground it was judged on.

## 11.5 Two instruments, independently, name the same 22 subjects

`tone_census.py` (mine, commissioned below) and `orch_printready.py` (ORCH's,
which I only call) share no code and measure different things. Their verdicts:

```
tone census WORSE      : 22
print gate REGRESSIONS : 22
identical sets         : True
in gate not tone: []      in tone not gate: []
```

and neither touches `coffee-bean`, `coffee-bubbles`, `dry-erase-marker-head-cpl`
or `foam`. Agreement between two instruments that could have disagreed is worth
more than either number alone.

## 11.6 The candidate escaped judgement by breaking the judge

The gate partition moved `17 PASS / 0 FAIL / 9 ACQUITTED / 0 NOT EXAMINED` ->
`2 PASS / 8 FAIL / 2 ACQUITTED / 14 NOT EXAMINED`.

Fourteen subjects were **not examined**, and the reason is not a considered
refusal:

```
SKIP  119MSDCF   ValueError: could not convert string to float: 'REJECT-FLAT'
```

`orch_chroma.py:180` documents `REJECT-FLAT` as the sentinel its banding measure
returns when the analysis window spans less than 64 DN. A window blown to white
spans nothing, so the sentinel fires; `orch_printready.py` then calls `float()`
on it and raises. The clipping is severe enough to break the instrument that
would have reported it.

**My harness scored that as a 3-subject regression.** Its rule counted only
`PASS->FAIL`, so twelve `PASS->SKIP` moves and five `ACQUIT->FAIL` moves passed
through unnamed. The worse the candidate, the more subjects fell out of the
count -- a candidate could have escaped by damaging the corpus enough to crash
the gate on all 26. That is the same failure shape as a summary in which a
skipped check and a passed check print as the same glyph.

The rule is now: leaving `{PASS, ACQUIT}` for any of `{FAIL, SKIP, MISSING}`
blocks promotion. Corrected, the same cached gate output reads

```
moves 22   REGRESSIONS 22   expiries 0
  PASS   -> SKIP    x12  BLOCKS
  ACQUIT -> FAIL    x 5  BLOCKS
  PASS   -> FAIL    x 3  BLOCKS
  ACQUIT -> SKIP    x 2  BLOCKS
```

The verdict line now prints that transition mix, because the earlier line said
"PASS->FAIL" for moves that were nothing of the kind -- a verdict misdescribing
its own evidence.

`diff_gate` was extracted as a pure function so the rule could be commissioned
on synthetic states in milliseconds instead of 370 s of gate time. Six arms, all
passing: a null that must stay silent, planted `PASS->FAIL`, planted
`PASS->SKIP`, planted `ACQUIT->FAIL`, all three at once, and a planted
**improvement** (`ACQUIT->PASS`) that must *not* be named a regression. The
improvement arm is what separates this rule from one that calls every move a
regression, which would have passed all four damaging cases and still been
useless.

## 11.7 Commissioning the tone census

Three arms, all passing, run before every census:

- **known-clean** -- values confined to 8000-40000 read exactly `0.0000%` at
  both ends. A census that manufactures clipping fails here.
- **planted defect with a known count** -- 1234 samples forced to 65535 and 567
  to 0 in a 786,432-sample image are recovered as `0.15691%` and `0.07210%`,
  matching the predicted fractions to nine decimal places. Not "detects
  something": recovers the number that was planted.
- **planted improvement** -- a genuinely blown image pulled back down reads
  `41.3033% -> 0.0000%`. A statistic bounded below by zero would pass the first
  two arms and still be unable to score a repair, which is the bug this project
  has already shipped once.

Both ends are reported and both participate in the verdict, because a gate that
tests one end of the tone scale has tested half the tone scale.

The threshold is a **movement** against the same subject (`MOVE_PCT = 0.20`),
never an absolute level. Clipping is emphatically not subject-invariant -- a
specular highlight legitimately clips where a diffuse subject does not -- so it
has not earned an absolute threshold and is not given one.

## 11.8 What the shadow end says

The crush figures *improve* on the regressed subjects -- `109MSDCF` 2.4703% ->
0.0400%, `119MSDCF` 3.2596% -> 1.6479%, `leaf-2-cpl` 0.6155% -> 0.0117% -- for
the same reason the highlights are destroyed: everything moved up. That is not a
shadow-detail win and it should not be read as one. Trading 3.26% of crushed
shadow for 72.47% of blown highlight is not a trade.

One subject is worth naming separately. `flower-inner-edge-cpl` carries crush
inside the subject rather than in a backdrop, and a 1.168x brightening moved it
only 3.6395% -> 3.6062%. Its crush does not respond to exposure, which is
evidence that it is established before the tone path rather than by it.

## 11.9 The band numbers on this arm, and why they do not mean what they look like

The paired stage reports, across 26 subjects x 5 crops x 3 bands:

```
grain   tested 72  refused 58   d_floor -0.1047  d_struct +0.3152
struct  tested 64  refused 66   cleaner 18  blur_trade 23   d_floor -0.1024
mottle  tested 83  refused 47   cleaner 21  blur_trade 30   d_floor -0.0944
```

Half the cells refused, and the refusals are the defect: a crop blown to a
constant white has a degenerate noise floor, which is exactly the condition the
refusal exists to catch. The surviving cells read "quieter, paid for out of
structure" for the same reason -- a clipped region has no noise and no detail.

**These numbers are a consequence of the clipping, not an independent finding
about the merge.** The clean merge-quality comparison is 11.4, and it is HELD.
Reporting the blur-trade counts as a merge result would be reading the damage
and calling it a measurement.

## 11.10 Consequence for sequencing

`--auto-exposure` was inert on `9b05d0b7`, so the SHIP-V4 masters are what the
recipe produces when the gain is chosen and discarded. The correct baseline for
the merge-fix lane is therefore HEAD rendered **without** `--auto-exposure`,
which is exposure-matched to SHIP-V4 (ratio 1.00205) and differs from it by
nothing this gauge can resolve.

The chooser has never been validated against an applied result. It was written,
tuned and shipped while its output was discarded, and the first render that
applied it blew 22 of 26 subjects. Whatever the remedy -- clamp the gain to the
available headroom, choose against the post-normalisation histogram, or apply it
before the normalisation rather than after -- it is a decision for the lane that
owns the exposure path, not for this one.

## 11.11 What I did not verify

- **That reverting `9cb7f5d9` restores SHIP-V4 exactly.** I isolated the flag,
  not the commit; the no-flag run shows the other thirteen commits are quiet,
  which is a weaker statement than a revert would give.
- **Whether the byte-freeze registry still holds at HEAD.** 26 of 26 masters
  differ from SHIP-V4 and none is pixel-identical, so a freeze pinned to these
  renders cannot still match -- but `byte-freezes.tsv` is ORCH's file, its
  fixtures are not these masters, and I did not run it.
- **The four held subjects at the band level.** They held on tone and on the
  gate; I did not pair them, because the arm's verdict was already decided by
  the 22.
- **Any subject but `coffee-bubbles` without `--auto-exposure`.** The isolation
  rests on one 19-frame subject. It is a controlled comparison and the mechanism
  predicts the rest, but it is one subject.

## 11.12 The fix landed while this was being written, and it holds

`5f367a94 fix(exposure): stop --auto-exposure double-normalising the srgb
render` was committed by another lane during this work, from an independent
diagnosis. Rather than assume it, I cut a pin at `2f858c62` (binary sha16
`A058F737DFE695F7`) and put it on the same gauge.

Its own claim first -- that `--srgb --auto-exposure` is now byte-identical to
`--srgb` -- on `coffee-bubbles`, 19 frames:

```
np.array_equal(fixed --srgb --auto-exposure, fixed --srgb)  = True
np.array_equal(fixed --srgb,                 HEAD  --srgb)  = True
mean(fixed --srgb) / mean(SHIP-V4-pin --srgb)               = 1.00205
```

The second line matters as much as the first: the fix changed nothing on the
path that was already correct, so it is targeted rather than a broad revert.

But `coffee-bubbles` was one of the four subjects that **held**, so it cannot
show the blowout is gone. The decisive test is a subject that was destroyed,
rendered with the shipping recipe:

| subject | SHIP-V4 `9b05d0b7` | HEAD `f190a0ea` | fixed `2f858c62` |
| --- | ---: | ---: | ---: |
| `109MSDCF` (22 fr) | 0.0012% | **85.5716%** | **0.0013%** |
| `lead-1-cpl` (123 fr) | 0.0230% | **98.4836%** | **0.0231%** |

Restored to the pin's behaviour to four decimal places on both. The crush end
moves back with it -- `109MSDCF` 0.0400% -> 2.5191% against the pin's 2.4703% --
which confirms 11.8: the shadow "improvement" at `f190a0ea` was the brightening
and nothing else, and it reverses when the brightening does.

The binary now says so itself, in the render log:

```
exposure : --auto-exposure is SUPERSEDED and applies NOTHING.
           ... already places luminance p99.9 at 0.90 -- the identical rule.
           Applying both double-normalises and blows the highlights.
```

**A verification is not a re-certification.** Two subjects on the tone axis is
not 26 subjects on the gate and the band gauge. The corpus at `2f858c62` has not
been rendered, and until it is, the standing corpus evidence remains the pin's.

## 11.13 What this baseline was for, and what it turned out to be

ORCH commissioned this render as insurance: take a baseline before the merge fix
so a later regression is attributable to one change rather than twelve. It was
expected to read "did nothing".

It found a defect that had already reached the shipping recipe, on 22 of 26
subjects, at severities up to 98.4836% of the frame. The insurance paid before
the risk it was bought against ever materialised -- and the argument for taking
it was not that a defect was likely, but that attribution is cheap beforehand
and expensive afterwards.

It also found a defect in the instrument doing the finding, which is the part
worth keeping: the harness scored a catastrophically damaged arm as a
3-subject regression because twelve subjects had crashed the gate and fallen out
of the count entirely. **A candidate that breaks the judge must not thereby
escape judgement.**


# 12. Is the shipping default already beaten by a flat exponent of 1?

ORCH's proposition: the pyramid merge's selection-exponent ladder is under three
constraints that no single exponent can meet, a rebuild is underway for that,
but a cheaper question sits in front of it and needs no code change --

> Is the shipping default already beaten, on print quality, by a flat exponent
> of 1, a configuration reachable tonight with two existing flags?

The numbers offered to make it worth a render rather than an argument were
blotch 1.354x -> 1.152x, sharpness 0.755 -> 0.685, hull violations 72+ -> 0:
**9.3% less sharpness in exchange for eliminating manufactured detail entirely
and taking most of the blotch reduction.**

I rendered it. **The blotch side reproduces and the sharpness side does not.**
Flat-1 costs **19.63%** of struct-band sharpness, not 9.3% -- 2.1x the quoted
price -- and **not one of the 26 subjects reads FLAT WINS.**

## 12.1 The ladder, read from the binary and not from the brief

ORCH warned it had been wrong about a flag's spelling once and about a flag's
potency twice, and asked me to verify from the run's own banner. Both flags are
as described. `--pyramid-sharpen`'s help says verbatim: *"1.0 disables the ramp
and restores a single global exponent."*

The banner's headline `exponent : 2.00` initially read to me as contradicting
ORCH's claim of "exponent 8 at the three finest bands", and I was wrong -- the
full banner resolves it:

```
DEFAULT   exponent 2.00, ramps 1.4x/octave, per-band exp : 2 3 4 5 8 8 8
FLAT-1    exponent 1.00, ramps 1.0x/octave, per-band exp : 1 1 1 1 1 1 1
                                            (coarsest -> finest)
```

The ramp is clamped at 8. **ORCH's premise was verified, not refuted.** Both
lines are recorded in the shipped arms' own `.provenance.txt`, not merely in a
test run: same binary, same input set, same ARGV apart from the two flags.

## 12.2 Potency, before any interpretation

ORCH's guard #1: an arm that silently rendered the default is indistinguishable
from an arm that made no difference. `potency.py` decodes arrays and never
compares hashes -- a file hash is not a pixel gauge.

| arm | samples moved | mean abs delta on moved samples |
|---|---:|---:|
| flat-1 vs default | **99.5297%** | 255.9 DN |
| `--pyramid-exponent 4.0` (known-potent control) | 98.5235% | -- |

The positive control is awake, and the arms genuinely differ.

## 12.3 The gauge, and the two defects it caught in itself

`flatexp.py` pairs a blotch number with a sharpness number **on the same pixels**
-- mottle-band floor (21-61 px) against struct-band structure (5-13 px,
0.077-0.20 cyc/px), five content-chosen sites per subject. Sites are chosen on
the **base arm only**: a geometric grid lands on black backdrops, and choosing
on the candidate would let a blur pick the flattest places to be judged.

Commissioning is `commission_flatexp.py`, **8 arms, 8 PASS / 0 FAIL**:

| arm | blotch | sharp | verdict |
|---|---:|---:|---|
| null | 1.0000 | 1.0000 | NEUTRAL |
| blur | 0.9631 | 0.5921 | TRADE |
| improve | 0.6104 | 0.9920 | FLAT WINS |
| noise | 1.2813 | 0.9976 | FLAT LOSES |
| softonly | 0.9914 | 0.7680 | FLAT LOSES |
| shift 32px | -- | -- | UNREGISTERED |
| shift 12px | -- | -- | UNREGISTERED |
| shift 2px | 0.9985 | 1.0000 | NEUTRAL |

The load-bearing pair is `blur` and `improve`: a blur and a denoise **both** win
on blotch, and they are separated only because the blur pays 41% of sharpness
against the denoise's 0.8%. A suite that plants only degradations cannot make
that distinction.

Two defects in my own scorer were caught this way and neither would have been
caught by reading:

1. **The verdict hid a trade.** Run on the real coffee-bubbles pair it printed
   `NEUTRAL` on blotch 1.0065 while sharpness had fallen to **0.8587** -- it hid
   a 14.1% loss of detail behind a noise number that had not moved. That is
   exactly the failure ORCH named. The verdict is now two-sided on **both** axes
   and sharpness can convict alone; the `softonly` arm exists for that case.
2. **The floor was discarded with the peak.** `ratios` threw away the *blotch*
   measurement whenever the *sharpness* half refused. Those are independent
   claims -- measuring how loud a band is does not require it to contain detail
   -- and conflating them refused every flat crop in the corpus.

## 12.4 The registration guard was refusing on noise, and hiding the worst evidence

Three of the first sixteen subjects refused as UNREGISTERED. **None was
shifted.** Each arm's own log reports the same sidecar, the same reference frame
and the same N placed / 0 refused; the outputs have identical shape; and a
selection exponent reweights pyramid coefficients on a fixed grid, so there is
no mechanism by which it could translate an image. The guard was taking an SSD
argmin at **one** site over a +/-4 px search, and what that argmin was reading
was the **content difference between the arms** -- the quantity the experiment
exists to measure.

**The threshold is now measured, not chosen.** `regsens2.py` self-shifts three
real masters, so the shift is the only difference between the two sides:

| planted shift | max abs blotch-1 | max abs sharp-1 | max abs grain-1 |
|---:|---:|---:|---:|
| 1 px | 0.424% | **0.106%** | 0.088% |
| 8 px | 0.839% | 0.472% | 0.346% |
| 16 px | 2.639% | 1.333% | 1.174% |
| 32 px | 5.620% | 3.509% | 2.530% |

The effect under test moves sharp by 15-22%. A 1 px argmin -- all the evidence
there ever was -- perturbs the answer by **0.106%, a four-hundredth of the
effect**. 8 px is the last row negligible against it, so that is the tolerance.

**Two candidate replacements were built and both were killed by their own
controls.** Both are recorded, because a rejected instrument is a result:

- **Normalised cross-correlation** fails AGENTS.md rule 5 -- it is not
  subject-invariant, so it cannot carry an absolute threshold. NCC(0) ~= 0.89 is
  a **4 px** shift on `coffee-bubbles` (0.88873) and a **64 px** shift on
  `dry-erase-marker-head-cpl` (0.89158). It reports how much fine content a
  subject has, not how far it moved.
- **Low-passing into the base band**, on the banner's claim that the base is a
  plain mean across frames in both arms, **does not respond to a planted shift at
  all**: on `flower-bud-alone-cpl` the low-passed excess reads 41.2% unshifted,
  43.3% at +1 px, 41.5% at +4 px, 33.0% at +32 px. A hard low-pass removes the
  structure that localises SSD.

**Three defects in the replacement, each caught by commissioning and not by
reading:**

1. The rewrite searched +/-4 px against a tolerance of 8 and passed a **planted
   32 px shift as NEUTRAL** -- the same saturation defect one layer down, because
   an argmin pinned at the boundary of its own search reports 4, and 4 <= 8.
   `SEARCH_RADIUS` must exceed `TOLERATED_SHIFT`.
2. Well depth was measured at the **origin** rather than at the **argmin**. On a
   pair that really is displaced the origin is nowhere near the minimum, the
   surface there is flat, and the site was declared uninformative -- so both
   planted shifts passed. Whether a surface has a well *at the origin* is a
   different question from whether it has one *at all*.
3. An exact match at the argmin (SSD == 0) was mapped to `float("inf")` and then
   gated on `np.isfinite`, which classified the **deepest possible well** as
   uninformative. Every planted shift is a `np.roll` of an exact copy, so every
   one went through that door. **Real masters never produce a zero SSD, so this
   was invisible on real data and only a synthetic could expose it.**

What ships: every site is probed; a global displacement is the same at every
site and noise is not, so the per-axis **median argmin across sites** is the
primary clause, and a site whose surface holds a genuine well may also refuse on
its own. Both clauses are conditioned on. The registration **basis** is
partitioned in the output and asserted to sum -- `SSD-WELL=18, MEDIAN-ONLY=8`
over 26 -- so a subject admitted because no site could speak never prints as the
same glyph as one admitted because a site spoke and agreed.

**The fix did not flatter my conclusion.** The two subjects the broken guard had
been discarding carry the **largest sharpness losses in the corpus**:
`dry-erase-marker-head-cpl` at **27.5% softer** and `flower-bud-alone-cpl` at
**35.4% softer**, against a corpus median of 19.6%. The broken guard was
suppressing the strongest evidence against the arm under test.

## 12.5 A brightness bias that ran against flat-1, and had to be corrected

The tone census reports a `mean x` column against SHIP-V4. The DEF arm sits at
1.000 on every subject; **the FLAT1 arm runs from 0.9930 to 1.1145.** strehl
normalises tone from each image's own p99.9, and a flat exponent changes the
merged image that percentile is taken from.

This matters to one statistic and not the other:

- `sharp` is `structure` = p99.5 over MAD, a **ratio inside one crop**, so a
  global gain cancels and the number is untouched.
- `blotch` and `grain` are `floor` = MAD, which scales **linearly** with gain.

Measured directly between the arms at the scorer's own content sites
(`gainbias.py`, not inferred by dividing two comparisons against SHIP-V4): the
median FLAT1/DEF gain is **1.0391**. Flat-1's floor was inflated 3.9% for that
reason alone, so the reported blotch **understated** how much quieter it is.
**The bias ran against the arm this lane's recommendation goes against**, which
is precisely why it had to be corrected rather than noted and dropped.

## 12.6 The result, all 26 subjects

Arms `DEF-2f858c62` and `FLAT1-2f858c62`, pin `2f858c62`, binary sha16
**A058F737DFE695F7**, 26 subjects / 4,825 frames (4,526 placed across the 25
aligned subjects plus 299 on `highly-angled-ruler-mm-cpl`, where alignment is
REFUSED as a tilted subject under M86 -- identically in both arms, so it does
not confound the comparison), `--srgb --auto-exposure`, identical in every
respect but the two merge flags.

| | as reported | gain-corrected |
|---|---:|---:|
| blotch, mottle 21-61 px floor | 0.8525 | **0.8158** |
| sharpness, struct 5-13 px (0.077-0.20 cyc/px) | 0.8037 | 0.8037 |
| grain, <=3 px floor | 0.7462 | 0.7281 |

**Partition: 25 TRADE, 1 FLAT LOSES, 0 FLAT WINS, 0 refused.**

| | quoted by ORCH | measured here |
|---|---:|---:|
| blotch improvement | 14.9% | **18.42%** |
| sharpness cost | 9.3% | **19.63%** |
| sharpness spent per unit of blotch bought | 0.62 | **1.07** |

The blotch side of ORCH's table reproduces and is in fact slightly better than
quoted. **The sharpness side is 2.1x worse.** Flat-1 does not buy blotch
cheaply; it buys it at roughly one-for-one.

Per-subject, worst and best trades:

| subject | blotch (corr) | sharp | verdict |
|---|---:|---:|---|
| `flat-on-ruler-cpl` | 0.8439 | 0.9468 | best trade: 15.6% for 5.3% |
| `foam` | 0.7662 | 0.8887 | 23.4% for 11.1% |
| `lead-1-cpl` | 0.7668 | 0.7774 | 23.3% for 22.3% |
| `112MSDCF` | 0.8356 | 0.8226 | 16.4% for 17.7% |
| `113MSDCF` | 0.8582 | 0.8350 | 14.2% for 16.5% |
| `coffee-bubbles` | 0.9288 | 0.8587 | **worst trade: 7.1% for 14.1%** |
| `flower-bud-alone-cpl` | 0.8715 | **0.6463** | 12.9% for **35.4%** |

**The single most damaging fact for the proposition** is in that table. Those
first six rows are the six subjects convicted of mid-scale mottle -- the defect
flat-1 is proposed to fix. On `coffee-bubbles`, the subject with the **worst**
convicted mottle at 1.4501x, flat-1 delivers the **worst trade in the entire
corpus** and is the only subject scored FLAT LOSES. *The configuration does not
work best where the defect is worst.*

## 12.7 Tone, both ends

`tone_census.py` (commissioned 3/3, including a planted improvement) against
SHIP-V4. Both arms: WORSE 0, partition sums to 26.

Two directional movements sit below the census's move threshold and so did not
gate, but they are real and they are **against** flat-1:

| subject | clip DEF | clip FLAT1 | |
|---|---:|---:|---|
| `pencil-steep-angle-cpl` | 0.0607% | **0.2100%** | 3.5x more clipping |
| `foam` | 0.0020% | 0.0219% | 10.7x more clipping |

Flat-1 also *improves* crush, measured DEF -> FLAT1 on the same axis:
`leaf-2-cpl` 0.1814% -> 0.0851% and `flower-inner-edge-cpl` 3.6324% -> 3.4279%.

Incidentally corroborated: the DEF arm at pin `2f858c62` holds tone on **all 26**
subjects against SHIP-V4, confirming that the clipping regression this lane
found on the earlier HEAD pin `f190a0ea` is fixed at `2f858c62`.

## 12.8 The hull axis is NOT MEASURED, and that is a hole in this recommendation

Flat-1's strongest argument is hull violations 72+ -> 0: manufactured detail
eliminated. **I could not measure it on this binary, and I will not report a
number I could not form.**

BUILD-HULL's instrument needs a per-frame basis to compare the merge against.
strehl normalises tone per image (`TONE_WHITE_TARGET = 0.90`, p99.9 -> 0.90), so
a single-frame render is normalised on *that frame's* percentile and does not
share a scale with the merge. Measured on coffee-bubbles / 19 frames
(`hullscale.py`): median frame/merge gain **0.8503 with a 12.9% spread**. Under
`--linear-srgb`, whose help says "THIS IS THE MODE TO MEASURE IN", the spread is
**0.0696** -- better, still not one scale (`linscale.py`). `bhull2.py` on that
basis reports an implausible 18.8% violation rate, which is the normaliser and
not manufactured detail. Fitting a per-frame gain would fit away the very
excursions the hull exists to find.

BUILD-HULL's own runs used a **different binary** -- `pairprice.py:85` records
"ORCH-SHIP blend-render.exe, `--camera-linear` (never a tone curve)".

I checked whether the shipping binary can price it directly. `stack --help` has
no hull, ceiling, overshoot or envelope flag. `--confidence-map` exists and is
computed by strehl against its own frames, so it carries no photometric
mismatch -- but it measures *how centrally the output sits in the cloud of
observations*, a hedging score. Low means the merge elected a frame, which is
what selection is **supposed** to do. It would answer a different question, so I
did not run it and report a number I could not condition on.

## 12.9 Recommendation: do not move the default constant tonight

**Flat exponent 1 loses on the axes I can measure.**

1. It costs **19.63%** of struct-band sharpness -- **2.1x the 9.3% quoted** --
   for **18.42%** of mottle-band floor. That is roughly one-for-one, not the
   bargain the proposition rested on.
2. **Zero of 26 subjects read FLAT WINS.** 25 are trades and 1 is an outright
   loss.
3. **It fails worst exactly where the defect is worst.** On `coffee-bubbles`,
   the flagship mottle subject at 1.4501x, it is the only FLAT LOSES in the
   corpus: 14.1% of sharpness spent to buy 7.1% of blotch.
4. **We cannot pay for this with sharpness we have already spent.** V-SOFTCHECK
   has established, with an IMPROVE arm proving the estimator was free not to
   charge, that the masters are **already** soft against their own per-site
   complete-bracket ceiling -- 0.6949 on `109MSDCF`, 0.7533 on `119MSDCF`, all
   four CIs entirely below 1.0 at 0.20-0.25 cyc/px. Flat-1 spends another fifth
   of what remains.

**The condition under which this recommendation flips**, stated so it can be
tested rather than argued: if the hull benefit is real at the magnitude
V-GATHER measured -- the merge emitting detail present in *none* of its inputs,
on 13 of 19 subjects, by up to -96.4% -- and if a print buyer would rather have
a fifth less resolved detail than any manufactured detail at all, then flat-1 is
the better default and this recommendation is wrong. **I could not price that
side of the trade** (section 12.8), so I am reporting the cost I measured and
naming the benefit I did not.

"We checked and kept it" is a materially different claim from "we never checked."
This is the first.

## 12.10 Cost

Both arms, 26 subjects, 52 renders, interleaved smallest-first so paired results
accumulate from the first minute rather than after three hours: **3 h 35 m 13 s**
wall clock (17:04:59 -> 20:40:12), on a machine with nine other lanes rendering
concurrently. Memory, not disk, is the binding constraint -- 4.5 GB free with
44.7 GB held by other lanes' `strehl` processes -- so the arms were run
sequentially rather than in parallel.
