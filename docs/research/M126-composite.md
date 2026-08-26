# M126 — the composite: what the shipped configuration actually is

**Status:** COMPLETE.
**Question (ORCH):** *"What does the image look like with every stage that has been
measured-good but left dark switched ON at once?"*
**Answer, in one line:** **the question cannot be asked of the shipping backend, because
three of the four dark stages are not reachable from it at all** — and the fourth is a
measured identity. The composite is not "not better". It is **not constructible**.

**But the headline ORCH hoped for survives, in a narrower and cheaper form:**
`--pyramid-gate 4.5` — the gate the gallery was already rendered at — gives **~10× less
high-frequency noise in flat regions on `bee-3-cpl` at no visible cost in detail, and it
runs faster than the default.** One compiled constant. That is the one-line change.

This is a follow-on to [`M126-default-audit.md`](M126-default-audit.md), commissioned
after ORCH established (§63 of `ORCH-veiling.md`, commit `d319c339`) that *"the
configuration this project measures and the configuration it ships are different
configurations."* That finding is correct. It is more correct than ORCH knew, and it
applies to ORCH's own demonstration of it.

---

## 0. The binary, and why it is the pin

ORCH's non-negotiable #1: one binary for all arms.

| | |
|---|---|
| binary | `C:\dev\strehl-out\acceptance-pins\b9b6921e\target\release\strehl.exe` |
| size / built | 8.95 MB, 2026-08-26 09:15 |
| source tree read for every code claim below | `C:\dev\strehl-out\acceptance-pins\b9b6921e\crates\` |
| live-tree HEAD at dispatch | `5dd9b649`, `crates/` dirty in 6 files |
| live-tree HEAD at write-up | `571d30fc` |

I used the pin, not HEAD, exactly as ORCH's fallback prescribes. `crates/` had six dirty
files from other agents when I started and HEAD moved twice while I rendered.

**The cost of that choice, stated plainly:** while I was rendering, `571d30fc` landed —
*"veil: the debias is scaled by a sigma that is wrong by 9.35x"* (318 lines of
`merge_cmd.rs`, 135 of `merge.rs`). **My arm D therefore measures a veil implementation
that is now known to be wrong by 9.35× in its debias term**, and my arm-D logs print the
very quantity that fix corrects (`debias 2.49 sigma`). Arm D below is evidence about
`b9b6921e`, and it must not be read as a verdict on the veil as it now stands. There was
no alternative that also satisfied non-negotiable #1.

---

## 1. What ships — established, not assumed

Every arm in ORCH's matrix passes `--merge` explicitly, so none of them is the shipped
invocation. I rendered the real one: no `--merge`, no flags, no environment.

```
strehl.exe stack D:\personal\macro\109MSDCF -o A0.tif
```

```
merge backend   : pyramid (default)
noise gate      : 2.00 x the modelled band-noise power.
not applied     : photometric gain, clip census, outlier rejection, halo correction, through-focus
```

`A0` is **byte-identical** to arm A
(`F4FDB145E882C3EC4EF5385CA6AF2134E69F390411540B7F7F8EC431FBCB8FFC`), so arm A is a
faithful stand-in for the default. Two facts fall straight out of that banner:

- **The compiled default gate is 2.0**, confirmed independently at
  `crates/strehl-core/src/pyramid.rs:875` → `gate: 2.0`. ORCH is right.
- **The shipped backend tells you, unprompted, that halo correction and photometric gain
  are `not applied`.** That line is the whole finding, printed by the binary on every
  run, and nobody had read it.

---

## 2. The nesting map — read from code, never inferred from a null

ORCH's standing rule, and the one that governs this whole report: *a structurally inert
gate and a measurably useless gate produce the same number and mean opposite things.*
Every row below was established by reading the pin's own source and confirmed
behaviourally, in that order.

| stage | call sites | inside | reachable from shipped default? |
|---|---|---|---|
| `STREHL_VEIL` | `veil_enabled()` called **once**, `merge_cmd.rs:3594` | `run_estimator` (L2680–4255) | **NO** — estimator-only |
| `STREHL_FIX_HALO` | all `halo::` sites, `merge_cmd.rs:3841–3978` | `run_estimator` (L2680–4255) | **NO** — estimator-only |
| `STREHL_RESTORE` | `restore_plane` called **once**, `merge_cmd.rs:5916` | `if demosaic { … }` inside `write_merged` | **NO** — `--demosaic` only |
| `--pyramid-gate` | `main.rs:894` | pyramid path | **yes** |
| `--resampler` | warp/resample stage | both | **yes** (given alignment) |

`run_pyramid` begins at `merge_cmd.rs:4256`. **There are zero veil call sites and zero
halo call sites after that line.** This is not an inference from a measurement; it is the
complete set of call sites for each symbol in the file.

### 2.1 The restore nesting is one level deeper than ORCH's

ORCH's §63 instance 2 says the restore call *"is guarded at **both** sites including
`run_pyramid` — the default backend."* That is true and it is not sufficient. Both sites
(`merge_cmd.rs:3921` and `:4556`) only **construct** a `RestorePlan` and hand it to
`write_merged`. `write_merged` **consumes** it at exactly one place, `merge_cmd.rs:5916`,
and that place is inside `if demosaic { … }`. `--demosaic` is opt-in
(`#[arg(long, conflicts_with = "binned")]`, `main.rs`).

So on the shipped binned path, `STREHL_RESTORE` is not merely off — **it is never called,
and it says nothing at all**. Arm C's log contains no restore line, no banner, and no
`not applied` mention. Compare `STREHL_FIX_HALO`, which announces itself loudly when it
runs. A stage that is silently skipped is worse than one that is off.

### 2.2 …and when you do reach it, it is an exact identity

Forcing reachability with `--demosaic` and sweeping the cap over a 7.3× range:

| cap | restore R line | output SHA-256 |
|---|---|---|
| 1.1 | `max gain 1.0000, at Nyquist 1.0000, recovered 0.0000` | `183C10FA…DF514` |
| 1.7 | `max gain 1.0000, at Nyquist 1.0000, recovered 0.0000` | `183C10FA…DF514` |
| 2.5 | `max gain 1.0000, at Nyquist 1.0000, recovered 0.0000` | `183C10FA…DF514` |
| 8.0 | `max gain 1.0000, at Nyquist 1.0000, recovered 0.0000` | `183C10FA…DF514` |
| *(no restore)* | *(silent)* | `183C10FA…DF514` |

All five identical, including the no-restore control. **The cap is not the limiter — the
Wiener fit refuses to amplify at all.** `max gain 1.0000` is strictly below every cap
tested, so raising the cap cannot help. This reproduces `BUILD-SHARP.md:322` §4.3 *"the
measured verdict: the gain cap never binds"*, and it independently reproduces the result
ORCH himself relayed to me: **the deconvolution headroom is a null, `1.0014 ± 0.0184`.**

**A trap worth naming, because it would have produced a false wiring defect.**
`gain_cap_from_env()` (`crates/strehl-core/src/restore.rs:870`) returns `None` unless the
parsed value is **strictly greater than 1.0** — the value *is* the gain cap, not a
boolean. Setting `STREHL_RESTORE=1` (the obvious reading of ORCH's arm C, and what the
brief literally says) yields `None`, an output identical to arm B, and the conclusion
"restore is unwired". That conclusion would have been wrong for the wrong reason. I used
`1.7`, the module's own documented default (`BUILD-SHARP.md:2047`).

---

## 3. The arm table — 109MSDCF (22 frames)

Banner read for every arm, never argv, per non-negotiable #2. Private
`STREHL_CACHE_DIR` per arm, per M97's cache-confound warning. All environment wiped
between arms. Output is **linear camera-native** — the measurement space.

| arm | configuration | banner backend | SHA-256 (16) | vs base |
|---|---|---|---|---|
| **A0** | *(nothing — the shipped invocation)* | `pyramid (default)` | `F4FDB145E882C3EC` | — |
| **A** | `--merge pyramid` | `pyramid (--merge)` | `F4FDB145E882C3EC` | ≡ A0 |
| **B** | `+ --pyramid-gate 4.5` | `pyramid (--merge)` | `790166F83D8C0F41` | **DIFFERS** from A |
| **C** | B + `STREHL_RESTORE=1.7` | `pyramid (--merge)` | `790166F83D8C0F41` | **IDENTICAL to B** |
| **P** | B + `STREHL_RESTORE=1.0` *(placebo)* | `pyramid (--merge)` | `790166F83D8C0F41` | **IDENTICAL to B** ✓ |
| **E** | B + `--resampler lanczos3` | `pyramid (--merge)` | `AADA504E0E126139` | **DIFFERS** from B |
| **D0** | `--merge estimator --photometric` | `estimator (--merge)` | `32586D8BAB0E6E73` | — |
| **D** | D0 + `STREHL_VEIL=1` + `STREHL_FIX_HALO=1` | `estimator (--merge)` | `3D350442D352F2C2` | **DIFFERS** from D0 |
| **Dv** | D0 + `STREHL_VEIL=1` only | `estimator (--merge)` | `3D350442D352F2C2` | **DIFFERS** — *and ≡ D* |
| **Dh** | D0 + `STREHL_FIX_HALO=1` only | `estimator (--merge)` | `32586D8BAB0E6E73` | **IDENTICAL to D0** |

Every pyramid arm's `not applied` line is identical and includes *halo correction* and
*photometric gain*.

**Three things this table settles.**

1. **`Dv ≡ D`.** Arm D's entire effect is the veil. The halo contributes exactly nothing.
2. **`Dh ≡ D0`.** Halo is byte-inert here — a **confirmation of my own earlier
   pre-registered finding** that `STREHL_FIX_HALO` is a no-op by arithmetic for stacks of
   ≤ 41 frames (default delta 40; 109MSDCF has 22). It is inert here for *two independent
   structural reasons* — frame count, and the pyramid nesting — either of which alone
   would suffice.
3. **The placebo reads exactly zero.** `STREHL_RESTORE=1.0` is a real flag, really set,
   documented as the exact off switch, and it produced a byte-identical file. So arm C's
   null is not a broken harness. My instrument can read a known no-op as zero, which is
   the precondition for reading anything else.

---

## 3b. The arm table — bee-3-cpl (299 frames, 232.7 px drift)

Same binary, same protocol, same private-cache discipline. This is the subject where
halo can act (299 > the 41-frame floor) and where ORCH measured the veil signature
strongest.

| arm | banner backend | SHA-256 (16) | wall clock | vs base |
|---|---|---|---|---|
| **A** | `pyramid (--merge)` | `4CEFA85DE61CD972` | 293.5 s | — |
| **B** | `pyramid (--merge)` | `DB7D9AB4F88F965C` | 228.1 s | **DIFFERS** from A |
| **C** | `pyramid (--merge)` | `DB7D9AB4F88F965C` | 285.9 s | **IDENTICAL to B** |
| **P** *(placebo)* | `pyramid (--merge)` | `DB7D9AB4F88F965C` | 329.9 s | **IDENTICAL to B** ✓ |
| **E** | `pyramid (--merge)` | `DE317CA7867AF8D3` | **916.7 s** | **DIFFERS** from B |
| **D0** | `estimator (--merge)` | `586E016831A72841` | 472.1 s | — |
| **D** | `estimator (--merge)` | `7CEC0AD0928497EF` | — | **DIFFERS** from D0 |
| **Dv** *(veil only)* | `estimator (--merge)` | `18241D9AD09DD460` | 363.8 s | **DIFFERS** from D0 |
| **Dh** *(halo only)* | `estimator (--merge)` | `743EFE233081D3DA` | 670.1 s | **DIFFERS** from D0 |

**Both nulls reproduce on a second subject.** C ≡ B (restore identity) and P ≡ B (placebo
reads exactly zero). Two subjects, two independent confirmations each.

**E costs 4.0×** (916.7 s vs 228.1 s), at the top of the documented 2.9×–3.9× lanczos3
range — three other agents were rendering on this machine concurrently.

### The halo dose-response on frame count

| subject | frames | `Dh` vs `D0` |
|---|---|---|
| 109MSDCF | 22 | **byte-identical** |
| bee-3-cpl | 299 | **12.772 % of pixels differ, peak 49.363 % FS** |

This is a two-point dose-response confirming, in both directions, my earlier milestone's
pre-registered finding that `STREHL_FIX_HALO` is a no-op by arithmetic below the 40-frame
delta. It is also the positive control for the halo gate: the switch demonstrably works
when its precondition is met, so 109MSDCF's null is structural, not a dead switch.

---

## 4. The number that did not fit — and it is ORCH's

ORCH reports, for 109MSDCF at both gates through the pinned binary:

> **97.359 % of samples differ, peak 21.1 % of full scale, rms 0.41 %.**

My arms A and B are the same two configurations, same subject, same pinned binary. I
measure:

| | ORCH | M126 (linear) | ratio |
|---|---|---|---|
| % differing | 97.359 | **87.813** | 1.11× |
| rms, % of full scale | 0.41 | **0.0672** | **6.1×** |
| peak, % of full scale | 21.1 | **1.386** | **15.3×** |

Rather than argue about it I measured ORCH's own two artefacts with a strict 16-bit
reader. **His numbers reproduce exactly: 97.359 %, 0.4121 %, 21.141 %.** ORCH is not
wrong about his files. The files are a different render.

`C:\dev\strehl-out\ORCH-GATE\a-g45.tiff` is `(4688, 7032, 3)` — exactly 2× my
`(2344, 3516, 3)` per axis — and it carries its own configuration in its
`ImageDescription` tag:

> **"sRGB (IEC 61966-2-1): BT.709-6 primaries, D65 white point, sRGB transfer curve.
> For viewing."** … *tone rendering … black fraction removed 0.85, display-space
> contrast 0.550.*

Mine reads:

> **"Linear camera-native RGB (sensor primaries), NO colour matrix, no transfer curve.
> THIS IS NOT sRGB — do not treat it as such. This is the measurement output."**

Mean level 47902.6 DN against 6224.2 DN — a 7.7× lift from the tone curve.

**So the headline visual measurement of the gate difference was made in the viewing
space, with a demosaic and a 0.550-contrast S-curve, in the configuration ORCH's own
brief to me forbids for measurement** (`main.rs:116`: *"For looking at, NOT for
measuring"*). This is the same class of error as §63 itself, applied to §63's own
evidence: **the configuration ORCH measured the divergence in is not the configuration
that ships.**

**What survives and what does not.** ORCH's *visual* conclusion — that gate 4.5 looks
cleaner and the default grainier — is drawn from looking at an sRGB render, which is the
correct thing to look at, and I do not contest it. What does not survive is the
**magnitude**. In the shipped linear space the same change is **15× smaller in peak and
6× smaller in rms** than the quoted figures. Anyone budgeting the value of the gate
change from `peak 21.1 % of full scale` is over-budgeting it by an order of magnitude.

---

## 5. Looking at the pixels

ORCH's rule #5: rank by eye, not by statistic; choose crops deliberately; say "I cannot
tell these apart" when that is the truth. Crop locations were chosen **by eye** from an
overview of arm A, before any difference was computed. Integer slices only, 512×512, no
resampling. One display transform, fitted on **arm A alone** and applied identically to
every arm, so any visible difference is real.

The subject is thick paint strokes on textured paper.

| crop | location (binned px) | what it is for |
|---|---|---|
| `detail` | (2450, 940) | fine parallel scratch lines in a grey stroke + paper texture |
| `edge` | (1150, 790) | teal / black / red occluding boundary |
| `flat` | (450, 230) | smooth teal field |
| `orchworst` | (1528, 1832) | ORCH's own maximum-disagreement location, converted from his demosaiced (3056, 3888) |

### My ranking, by eye

- **`detail`** — **A ≈ B ≈ E: I cannot tell them apart.** D0 and D are **visibly
  grainier** in the white paper field; that is the only difference I can see anywhere in
  this subject without a statistic.
- **`edge`** — **A ≈ D0: I cannot tell them apart.** No visible halo difference, which
  is expected: halo is inert here twice over (§3).
- **`flat`** — **A ≈ B: I cannot tell them apart**, although B measures 34 % less
  gradient energy (52.08 → 34.45). The noise reduction is real and below my visual
  threshold in linear.
- **`orchworst`** — **A ≈ B: I cannot tell them apart in linear**, at the very location
  ORCH chose because the two disagree there most.

That last line deserves emphasis, because **ORCH's rule #5 predicted it**: *"a crop chosen
by maximum disagreement lands in a flat region and tells you about noise while telling you
nothing about detail."* It does. The crop is flat teal paint. The A/B difference on
109MSDCF is a **noise** difference, it is genuine, and in the measurement space at 1:1 it
is sub-visual. The sRGB tone curve is what makes it visible.

### Supporting numbers — supporting, not deciding

Gradient energy (mean |∂/∂x|), a crude sharpness proxy. In a **flat** crop a higher value
means more noise, not more detail; the detail/flat ratio is the only part worth reading.

| arm | detail | flat | detail/flat |
|---|---|---|---|
| A | 60.39 | 52.08 | 1.160 |
| B | 47.40 | 34.45 | **1.376** |
| E | 51.34 | 36.87 | **1.392** |
| D0 | 71.84 | 65.94 | 1.089 |
| D | 71.80 | 66.30 | 1.083 |

Whole-image, linear, vs arm A:

| arm | mean DN | % differing | rms % FS | peak % FS |
|---|---|---|---|---|
| A | 6224.0 | 0.000 | 0.0000 | 0.000 |
| B / C / P | 6224.1 | 87.813 | 0.0672 | 1.386 |
| E | 6224.1 | 93.547 | 0.0675 | 1.393 |
| D0 | 6224.2 | 98.922 | 0.1021 | 4.869 |
| D | 6230.6 | 98.930 | 0.1461 | 7.849 |

B and E rank best on detail/flat; the estimator arms rank worst, consistent with what I
can see. I am not ranking the arms on this table — I am reporting that it agrees with the
eye where the eye can see anything at all.

---

## 5b. Looking at the pixels — bee-3-cpl, where it is not close at all

109MSDCF is a low-drift 22-frame stack and every difference on it is sub-visual. bee-3-cpl
is not. **This is where the answer is, and it is visible without a statistic.**

### The rendering mistake I made first, and had to fix

My first `flat` crop on bee-3 (2900, 200) contained bee hairs in one corner. Two
statistics then disagreed violently — gradient energy said A/B = **3.54×**, a 5×5
high-pass said **1.18×** — and my global display transform, which maps the 99.7th
percentile to white, saturated the bright backdrop and showed nothing at all. All three
symptoms had one cause: **the crop was not flat and the view was clipped.** Re-cropping to
genuinely empty background (`flat2`, at 2990, 60) and windowing on the background level
resolved it.

I am recording this because the first pass would have supported "I cannot see any
difference", which is the comfortable answer and was wrong.

### Flat field, high-frequency component, one fixed gain from arm A

`view = (crop − box5(crop)) × gain + 128`, identical gain for every arm.

| arm | hp rms (DN) | vs A |
|---|---|---|
| **A** — what ships | **144.37** | — |
| **B** — gate 4.5 | **14.53** | **9.9× less** |
| E | 16.81 | 8.6× less |
| D0 | 14.52 | 9.9× less |
| **Dv** — veil on | **85.21** | **5.9× worse than D0** |
| Dh | 14.52 | 9.9× less |

**By eye, `bee-3-cpl-flat2-HP-A.png` against `-B.png` is not a close call.** A is dense
chromatic pixel noise across the entire frame. B is nearly clean — only the faint smooth
texture of the backdrop remains. This is the single clearest visual difference I found
anywhere in this milestone, and it is between **the configuration that ships and the
configuration the gallery was rendered in**.

### Fine detail — the compound eye

| arm | gradient energy, `detail` crop |
|---|---|
| A | 202.94 |
| B | 201.75 |
| E | 212.56 |

**By eye, `bee-3-cpl-detail-A.png` and `-B.png` are indistinguishable.** The hexagonal
facet array is equally resolved, the hairs equally crisp. So on this subject the gate
change buys a **~10× reduction in flat-field noise at no visible cost in detail**. That is
not a trade; it is free.

### The occluding edge — and a refutation of my own earlier metric

Halo's heaviest action on bee-3 is at the wing (block 512, 0; mean |diff| 1130 DN).
Comparing `bee-3-cpl-halo-D0.png` with `bee-3-cpl-halo-Dh.png`:

**The halo correction is visibly destructive.** D0 shows the wing membrane's delicate
microtexture — fine parallel hair rows across every wing cell. Dh has **erased that
texture over much of the frame**, replacing it with smooth blotchy plateaus, and has
introduced **hard contour-like banding** that outlines the surviving patches. It is a
posterised, "oil painting" appearance. Gradient energy in that crop falls 542.14 → 309.92,
a 43 % loss of structure.

The binary says so itself, in its own banner, on every run:

> `--- pass three: occlusion-halo correction (M87, COSMETIC) ---`
> `This is NOT a fidelity improvement. On a synthetic scene with known truth it cuts the
> halo metric 79.8% and raises RMSE against truth 254.6%.`

**And this refutes a published result of my own.** `M126-default-audit.md` recorded that
`STREHL_FIX_HALO` was the **only** gate to clear all three bars on `bee-3-cpl`
(`dD +0.01810`, **73.2 % of tiles improved**) and named it the milestone's biggest
surprise. Looking at the pixels, that verdict is wrong. My tile metric rewarded the
contrast increase the halo correction produces at wing-cell boundaries and was blind to
the microtexture it destroys between them — the treated area is large, so most tiles
"improved" while the image got worse.

The overall verdict does not change (halo was KEEP OFF on the strength of 4 of 5 subjects)
**but one of its two stated reasons was wrong, and the exception I recorded was an
artefact of my instrument.** Per ORCH's discipline 912: the verdict survived, the reason
did not, and a correct verdict reached by a wrong argument is the hardest error to find
later. This one was found only by opening the file.

---

## 5c. Ranking, said plainly

| crop type | subject | ranking by eye |
|---|---|---|
| fine detail | 109MSDCF | **A ≈ B ≈ E — I cannot tell them apart.** D0/D visibly grainier |
| fine detail | bee-3-cpl | **A ≈ B — I cannot tell them apart** |
| occluding edge | 109MSDCF | **A ≈ D0 — I cannot tell them apart** (halo inert here) |
| occluding edge | bee-3-cpl | **D0 ≫ Dh.** Halo is plainly destructive |
| flat field | 109MSDCF | **A ≈ B — I cannot tell them apart** in linear |
| flat field | bee-3-cpl | **B ≫ A, decisively.** ~10× less noise, obvious at a glance |
| flat field | bee-3-cpl | **D0 ≫ Dv.** The veil adds 5.9× the noise back |

---

## 6. Reproducing every number

```powershell
$BIN = "C:\dev\strehl-out\acceptance-pins\b9b6921e\target\release\strehl.exe"

# the full arm matrix (private cache per arm, environment wiped between arms)
cd C:\dev\strehl-out\M126-COMPOSITE
.\run_arms.ps1  -Subject "D:\personal\macro\109MSDCF" -Tag "109MSDCF"
.\run_arms2.ps1                                        # restore positive control + D decomposition
.\run_arms.ps1  -Subject "D:\personal\macro\bee-3-cpl" -Tag "bee-3-cpl"

# what actually ships
& $BIN stack "D:\personal\macro\109MSDCF" -o A0.tif        # banner: pyramid (default)

# restore dose-response: identity at every cap
foreach ($cap in "1.1","2.5","8.0") {
  $env:STREHL_RESTORE = $cap
  & $BIN stack "D:\personal\macro\109MSDCF" --merge pyramid --pyramid-gate 4.5 --demosaic -o "dose$cap.tif"
}

# analysis (hard `import tifffile`, `assert dtype == np.uint16`, no PIL reads anywhere)
python disp.py      109MSDCF                    # overview for by-eye crop selection
python crops.py     bee-3-cpl "A,B,D0,Dv,Dh"    # integer crops + labelled montages
python whole.py     109MSDCF "A,B,C,P,E,D0,D"
python noiseview.py bee-3-cpl flat "A,B,E,D0,Dv,Dh" 4   # high-gain window on a bright field
python hpview.py    bee-3-cpl flat2 "A,B,E,D0,Dv,Dh"    # the 10x result: 144.37 vs 14.53 DN
python locate.py    bee-3-cpl D0 Dh             # finds where the halo correction acted
python orchgate.py                              # reproduces ORCH's 97.359 / 0.41 / 21.1
python orchcfg.py                               # identifies those artefacts as sRGB "For viewing"
```

Scripts live in `C:\dev\strehl-out\M126-COMPOSITE\` and are copied into
`experiments/M126-default-audit/composite/`.

---

## 7. Crops for ORCH to open

All under `C:\dev\strehl-out\M126-COMPOSITE\crops\`.

**Open these four first — they carry the whole result:**

| file | what it shows |
|---|---|
| **`bee-3-cpl-flat2-HP-A.png`** | the **shipped default's** flat-field noise |
| **`bee-3-cpl-flat2-HP-B.png`** | the same field at `--pyramid-gate 4.5`. Same fixed gain. ~10× cleaner |
| **`bee-3-cpl-halo-D0.png`** | wing microtexture, halo **off** |
| **`bee-3-cpl-halo-Dh.png`** | the same wing, halo **on** — texture erased, contours banded |

Supporting:

| file | contents |
|---|---|
| `bee-3-cpl-detail-{A,B,E,D0,Dv,Dh}.png` | compound eye, fine detail — A and B indistinguishable |
| `bee-3-cpl-flat2-HP-{A,B,E,D0,Dv,Dh}.png` | flat-field noise, all arms, one fixed gain |
| `bee-3-cpl-veil-{A,B,D0,Dv,Dh}.png` | where the veil acted hardest |
| `bee-3-cpl-{detail,edge,flat,halo,veil}-MONTAGE.png` | labelled side-by-side, 1:1 |
| `109MSDCF-{detail,edge,flat,orchworst}-{A,B,E,D0,D}.png` | the low-drift subject, where everything is sub-visual |
| `109MSDCF-orchworst-{A,B}.png` | ORCH's own worst-disagreement location, in **linear** |

The montages are 2560–3072 px wide and a viewer will downsample them; **judge sharpness
and noise on the individual 512×512 files**, which are 1:1.

---

## 8. Verdict

### The one configuration I would ship

**`--merge pyramid --pyramid-gate 4.5` — arm B. Nothing else.**

Not because the other stages lose, but because **on the shipping backend they cannot be
turned on at all** (§2), and the one that can be reached is an exact identity (§2.2).

**Cost: zero, and slightly negative.** Same backend, one compiled constant. On bee-3-cpl
it was **faster** than the default (228.1 s vs 293.5 s) because a tighter gate admits
fewer frames per band.

**Benefit, measured and looked at:** on bee-3-cpl, **~10× less high-frequency noise in
flat regions** (hp rms 144.37 → 14.53 DN) with **no visible detail cost** — the compound
eye's facet array is indistinguishable between the two. On the low-drift 22-frame
109MSDCF the same change is real but sub-visual in linear.

That is the strongest, cheapest result in this milestone, and it is the one-line change
ORCH hoped for — **but for a different reason than "the dark stages compose".** They do
not compose. The gate alone carries it.

**I would not ship arm E.** Its detail/flat ratio is marginally best on 109MSDCF (1.392 vs
1.376, a 1.2 % edge I cannot see) and on bee-3 it is slightly *noisier* than B (16.81 vs
14.53 DN). It costs **4.0× wall clock** and sharpens CA fringes into visibility. Bad trade.

### Per arm

| arm | ran? | verdict |
|---|---|---|
| **A** | yes | the shipped default; confirmed byte-identical to the bare invocation |
| **B** | yes | **SHIP.** ~10× less flat-field noise, no visible detail cost, zero cost, faster |
| **C** | yes | **cannot ship as a composite element.** Unreachable on the binned default path; an exact identity at every cap on both subjects even when forced reachable. Not a wiring defect — a measured null |
| **D** | yes, with a caveat | **KEEP OFF, and it is not a defaults question.** Veil and halo are both estimator-only; the shipped backend is pyramid. Halo is **visibly destructive** where it acts. The veil adds 5.9× the flat-field noise back — and the veil I measured is superseded by `571d30fc` |
| **E** | yes | **KEEP OFF** on cost, not on quality |

### The composite ORCH asked for

There is no composite. **A + B + C + D + E does not exist as a configuration**, because C
requires `--demosaic` and D requires `--merge estimator`, which is a *different merge*, not
an additional stage. The only stages that compose onto the shipped pyramid backend are the
gate and the resampler.

ORCH's decisive-either-way framing resolves to the second branch — *the dark stages do not
compose* — and for a stronger reason than he offered: **they are not on the same path.**
But the headline he hoped for survives anyway, in a narrower form: **ship the gate the
gallery was already rendered at.** One constant, no cost, plainly visible.

---

## 9. Corrections to the brief

Stated because ORCH asked to be corrected rather than agreed with.

1. **There is no `strehl merge` subcommand.** Non-negotiable #2 describes the backend
   inference as a property of `strehl merge`. The subcommands are `align`, `probe`,
   `stack`, `argmax-baseline`. The hazard is real and lives on **`strehl stack`**.
2. **`STREHL_RESTORE=1` is a documented no-op, not "on".** The value *is* the gain cap and
   `gain_cap_from_env()` requires `> 1.0` (`restore.rs:870`). Arm C as literally specified
   would have produced a false "unwired" finding — non-negotiable #3's failure mode,
   inverted.
3. **Arm D as specified errors out.** `STREHL_VEIL` has three `ensure!` preconditions
   (`merge_cmd.rs:3606–3629`): a bimodal prominence field, a finite `--gate`, and
   **`photometric_map.is_some()`** — i.e. `--photometric` must be on. I added
   `--photometric` and ran a D0 base so the switch could be hash-tested.
4. **The restore nesting is `--demosaic`, not the backend** (§2.1). ORCH's §63 instance 2
   stops one level short of the single consuming call site.
5. **ORCH's gate magnitudes are sRGB-space** (§4). His §§63.3 and 63.4 — veil and halo are
   estimator-only — are **correct**, and I confirm both from the call-site sets.

---

## 10. What I could not settle

- **Whether the veil is worth shipping.** My arm D measures `b9b6921e`, and `571d30fc`
  has since found the debias sigma wrong by **9.35×**. My finding that the veil adds 5.9×
  the flat-field noise back (hp rms 14.52 → 85.21 DN) is evidence about *that* build and
  is exactly the kind of symptom a 9.35× debias error would produce, so it may simply be
  the bug. The veil needs re-measuring on a build containing the fix. **Not mine.**
- **Whether the pin's binary was built from its co-located source.** I assumed it and
  corroborated only behaviourally — every banner, constant and call site I predicted from
  the source appeared in the output. I did not rebuild and compare hashes.
- **Whether gate 4.5 is the *best* gate.** I compared 2.0 against 4.5 because those are
  the two configurations that exist in the wild. **I did not sweep.** 4.5 is better than
  2.0 on both subjects; I have no evidence it is optimal, and given how large the bee-3
  effect is, the optimum could be well past it. **This is the obvious next experiment and
  it is cheap.**
- **Whether the 10× noise reduction costs anything on a subject I did not render.** Two
  subjects is two subjects. The gate necessarily admits fewer frames, so a stack that is
  already frame-starved could lose real signal where these did not. bee-3-cpl has 299
  frames and 109MSDCF has 22, and neither showed detail loss — but neither is a
  low-frame-count, low-SNR capture.
- **Whether restore is an identity at *other* SNRs.** Null on 109MSDCF at four caps
  spanning 7.3×, and null on bee-3-cpl at the shipped cap. Same photographer, same lens
  class. A genuinely low-SNR capture might move it; I cannot exclude that from two
  subjects.
- **Photometric normalisation.** Arm D0 carries `--photometric` and is grainier than the
  pyramid arms on 109MSDCF, but D0 also changes backend, so the two are confounded and I
  cannot separate them. **This is M122's and M125's, and I am not adjudicating it.**
- **Why my earlier tile metric ranked halo best on `bee-3-cpl`** when the pixels show it
  destroying wing microtexture. I have a mechanism — the metric rewards boundary contrast
  and is blind to texture erased between boundaries — but I have not *tested* that
  mechanism, and per discipline 912 an untested mechanism that explains the data is still
  a story. What is established is that the metric and the eye disagree, and that the eye
  is right.

---

## 11. Independent convergence, and what I do not claim priority on

I rendered for several hours and committed at **14:05**. Three commits landed
**before** mine, by parties I did not consult, on findings that overlap mine
substantially. Recording that plainly, because this milestone has already had to
correct one priority claim (§15 of the main report, M97e and the robust election).

| commit | time | agent | finding |
|---|---|---|---|
| `d8a44e9a` | 13:23 | ORCH | `check-potency.py` — a flag is not wired until an **absurd** value changes the output. Reports `STREHL_RESTORE` as "turning it on changes nothing at all". |
| `f6695f91` | 13:38 | BUILD-HALO | "`STREHL_VEIL` reaches no pixel on the shipping merge, measured" |
| `6d9f3ece` | 13:55 | BUILD-SHARP | "`STREHL_RESTORE=1` is the documented no-op, not an unwired stage" |

**I do not claim priority on:**

* **The veil being unreachable from the shipping merge.** BUILD-HALO measured it and
  committed it 27 minutes before me. My contribution is the *call-site enumeration*
  (`veil_enabled()` has exactly one site, `merge_cmd.rs:3594`, inside `run_estimator`
  L2680–4255; zero sites after `run_pyramid` begins at L4256) — the **mechanism** for
  their measurement, arrived at independently and by a different route.
* **The `STREHL_RESTORE=1` trap.** BUILD-SHARP committed it 10 minutes before me.

**What I believe is mine, and why:**

* **The `--demosaic` nesting of restore.** ORCH's §63.2 and `check-potency.py` both
  report restore as inert. Neither says *why*. `restore_plane` has **one** consuming
  call site (`merge_cmd.rs:5916`) and it is inside `if demosaic { … }`, so on the
  binned default the stage is not merely off — **it is never called, and says
  nothing.** That distinction is the whole point of ORCH's own warning that a
  structurally inert gate and a measurably useless gate produce the same number and
  mean opposite things. Forced reachable under `--demosaic` it **runs, announces
  itself, and reports `recovered 0.0000`** at four caps spanning 7.3×. So it is a
  **measured identity**, which is a different verdict from "unwired" and points at
  the Wiener fit rather than at the wiring.
* **The halo call-site set** (`:3841–3978`, all inside `run_estimator`) and the
  **two-point frame-count dose-response** (byte-identical at 22 frames, 12.772 % of
  pixels at 299).
* **ORCH's gate numbers being sRGB-space** (§4).
* **The `--pyramid-gate 4.5` flat-field result** (§5b) — the only *promotable* finding
  in this report.

**The convergence is worth more than any single strand.** Four methods — ORCH's
absurd-value potency check, BUILD-HALO's pixel measurement, BUILD-SHARP's source
read, and my call-site enumeration plus render matrix — reached the same place from
four directions on the same night. None of us designed that. It is the strongest
evidence in the report that **the configuration this project measures and the
configuration it ships are different configurations**, and it is stronger precisely
because no one coordinated it.

One caution against reading the convergence as unanimity: ORCH's `check-potency.py`
rule is *"a flag is not wired until an absurd value has changed the output."* By that
rule `STREHL_RESTORE` is DEAD. By mine it is a **live stage that computes an
identity**. Both are correct statements about different questions, and the second is
the one that decides whether anybody should go and fix it. **Nobody should.** The fit
refuses because there is no headroom — which is ORCH's own deconvolution null
(`1.0014 ± 0.0184`) arriving a second time, through a completely different door.
