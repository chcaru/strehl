# M64 — the estimator is the default path

**Verdict: the estimating merge is now what `strehl stack` runs, and M62's
acceptance battery returns `CERTIFY` on the new default.** Measured
**5.4316x** against `sqrt(30) = 5.4772` at efficiency **1.0001**, where the
path that shipped before this milestone measured **0.7690x** — a 1.300x noise
*increase* — on the identical burst, ROI, seeds and binary.

Every number below was produced by `experiments/M62-sqrt-n/src/`, copied
**byte-identically** (SHA-256 verified, section 3.1) and run unmodified. I did
not write the instrument, I did not change its thresholds, and I am not its
authority: M62 is, and M62's own run is the one that counts.

Pre-registered at **`bd050ff`**, before the crate diff existed. Crate diff at
**`7213eff`**. Every criterion in `experiments/M64-estimator-default/PREREGISTRATION.md`
is reported below as MET or NOT MET, in the words it was written in.

---

## 1. What the default path did, and what it does now

### 1.1 Before

| | before M64 | after M64 |
|---|---|---|
| `strehl stack <dir> -o x.tif` | unregularised per-pixel argmax | **the estimating merge at gate 4.0** |
| `strehl merge <dir> -o x.tif` | **exit 1** — see below | the same path (hidden alias) |
| `strehl argmax-baseline <dir> -o x.tif` | did not exist | the old `strehl stack`, unchanged |

Two separate defects, not one.

**The obvious command ran the wrong algorithm.** `strehl stack` selected, per
pixel, the frame with the highest noise-normalised Tenengrad response and copied
its quad. A selector inherits one frame's noise, and because the frame is chosen
*using* that same frame's noise the choice is correlated with it, so the result
is worse than an unstacked frame. MEASURED at 0.7690x against an arithmetic
answer of 5.4772 (M62).

**The right algorithm had no default at all.** `strehl merge <dir> --out x.tif`
with no tuning flags exited 1 with `--out writes one image, but 4 gates were
given; pick one`, because the default was a four-rung diagnostic ladder
(0.5, 1, 2, 4) that writes no image. M62 measured this and recorded its
pre-M64 verdict as `REJECT`, blocking on `DEFAULT`. So the estimator was not
merely non-default — **there was no default merged output in the binary.**

### 1.2 The restructuring I chose, and why the alternative lost

`strehl stack` **is** the estimating merge. `merge` survives as a **hidden clap
alias**, so every committed harness that calls `strehl merge --gate ...` keeps
working byte-identically — M62, M52, M55, M38 and M48 all do, and M62's battery
drove the new binary through `merge` without a single edit. The old argmax moved
to `strehl argmax-baseline`.

**The alternative that lost: leave `stack` as the baseline and tell users to run
`merge`.** It loses on the brief's own complaint. "Stack" is the word for what a
focus stacker does and "merge" is jargon; a default that has to be explained is
not a default. It also loses on evidence: M62 measured that the thing a user
would have been told to run *did not run* (section 1.1).

**A second alternative was excluded by the owner, not by me:** a
`--mode selector|estimator` flag. The instruction was one knob, not two modes,
and I think it is right for a reason worth recording — a mode switch presents
selection and estimation as two legitimate choices, when the whole measured
result is that one of them is 7.1x worse at the only task with a known answer.

**Why `argmax-baseline` rather than deleting it.** It is the negative control.
M62's battery needs at least one invocation that scores at or below 1.05 or its
verdict is `CANNOT-CERTIFY` — a battery whose failing arms have all vanished
certifies nothing. The rename cost M62 one power arm (section 5.1); this
subcommand is where it went, and it still measures **0.769033477**, identical to
M62's published number for the old `stack` to every printed digit.

**The name.** `argmax-baseline` over `baseline` because it must be unreadable as
a second user mode. Its `--help` opens `THE NAIVE BASELINE, NOT THE DEFAULT` and
says not to ship its output.

---

## 2. The measured score of the new default

M62's battery, `spec_version 1.1`, unmodified. `N = 30`, seeds 0/1/2, 891,136
plane pixels per arm, 64x64 block bootstrap. Binary
`sha256 60646c68...b7661f40`, `crates/` clean.

```
=== CERTIFY ===   power supplied by SELECTOR-same-binary
    PASS         A0-ladder:1              1.0007
    PASS         A0-ladder:2              1.4152
    PASS         A0-ladder:3              1.7327
    PASS         A0-ladder:5              2.2379
    PASS         A0-ladder:10             3.1632
    PASS         A0-ladder:20             4.4723
    PASS         A0-ladder:30             5.4791
    PASS         B1a-const-selector       1.0007
    PASS         B1b-random-selector      0.9996
    PASS         DEFAULT                  5.4316   eff 1.0001  n_eff 29.539
    NO-POWER     SELECTOR-shipped         5.4316   eff 1.0001  n_eff 29.539
    POWER-OK     SELECTOR-same-binary     0.9768   eff 0.9773  n_eff 1.0
    PASS         ESTIMATOR-explicit       5.4777   eff 1.0014  n_eff 30.0
```

### 2.1 Every pre-registered criterion, in the words it was written in

| # | criterion | measured | verdict |
|---|---|---|---|
| PR1 | default within 2% of `sqrt(30)`, i.e. `[5.368, 5.587]` | **5.431624**, rel **0.833%** | **MET** |
| PR2 | efficiency `R/sqrt(mean n_eff)` in `[0.98, 1.02]` | **1.000076** | **MET** |
| PR3 | focus guard: `mean n_eff / N < 0.95` on the real 22-frame stack | **0.2267** (4.987 of 22) | **MET** |
| PR4 | `stack` and `merge` are the same path | ratio identical; output **SHA-256 identical** (`96f71f10...`) | **MET** |
| PR5 | knob reaches its estimator end, within 0.5% at gate 8 | **5.477678**, rel **0.0083%** | **MET** |
| PR6 | knob reaches its selector end, gate 0 at or below 1.05 | **0.976815** | **MET** |
| PR7 | the argmax baseline survives the rename and still fails | **0.769033477** | **MET** |
| PR8 | instrument calibrated on this binary | worst ladder rung **0.0809%**; worst placebo **0.000693** | **MET** |
| PR9 | in-crate: ideal mean scores `sqrt(N)` within 2% | 3.4251 vs 3.4641, **1.13%** | **MET** |
| PR10 | in-crate: mean `n_eff` at least 3.0 | **12.000** | **MET** |
| PR11 | in-crate: `R` at least 1.70 | **3.4251** | **MET** |
| PR12 | in-crate: `R` at least 0.80 of `sqrt(mean n_eff)` | 3.4251 vs bound 3.4641 (**0.989**) | **MET** |
| PR13 | in-crate negative control, gate 0 at or below 1.05 | **1.0033** | **MET** |
| PR14 | the test fails when `DEFAULT_GATE = 0.0` | it fails; output quoted in section 4.2 | **MET** |

M62's own required extras also hold: **determinism PASS** (two runs on identical
input, `sha_a == sha_b == 96f71f10...`, ratio `5.435394455104036` both times),
`blocking: []`, `power_ok: ['SELECTOR-same-binary']`.

### 2.2 The number I did not chase, and would have had to tune to get

`DEFAULT_GATE = 4.0` scores **5.4316**, not the **5.4778** that gate 8 reaches.
That is 0.83% short of the arithmetic answer in a band that allows 2%. **I chose
the gate before measuring it and I am not moving it now that a better-scoring
value is visible**, for the reason in the pre-registration: gate 8's tolerance is
`8*sqrt(2) = 11.3` sigma of the focus field's own noise, against a real focus
contrast the crate's own test
(`real_focus_contrast_is_far_larger_than_the_noise_scale`) pins at more than 20
sigma. Spending over half the discriminating margin to buy 0.8% of noise on a
plant where nothing is out of focus is exactly the failure mode M62 warned about
in its own section 4, and it warned about it before my diff existed.

### 2.3 The default on real frames — a matched pair, post-hoc

Not pre-registered. Descriptive, run after the criteria above were settled, and
labelled post-hoc for that reason. Same binary, same 22-frame stack
`109MSDCF`, same ROI `2272,1344,256,256`:

| path | HP ratio (acceptance statistic) | legacy raw ratio | mean `n_eff` |
|---|---|---|---|
| `argmax-baseline` | **1.223x** `[1.016 .. 1.277]` | 1.068x | 1 by construction |
| `stack` (default, gate 4.0) | **0.749x** `[0.623 .. 0.782]` | 0.788x | 4.987 of 22 |

**1.633x improvement in the acceptance statistic on real data**, and the sign
flips: the baseline is noisier than a single frame, the default is quieter.
Detail retention over `1630,1044,256,256` reads **1.236x, verdict ok** — the
merge is not collapsing detail to get there, which is the failure fact 24
describes for a plain mean.

---

## 3. What I ran, and what I did not touch

### 3.1 M62's battery, copied rather than edited

M62's `out/` is tracked in git. Running its battery in place would have written
files into another live agent's tracked directory. I copied six files verbatim
into `experiments/M64-estimator-default/src/` and verified byte identity:

| file | SHA-256 (first 16) | identical to M62's |
|---|---|---|
| `harness.py` | `A3D2B12087B99FBB` | yes |
| `dngwrite.py` | `F99BADABDACC73BA` | yes |
| `01-pick-latent.py` | `E769701AF6E90753` | yes |
| `10-acceptance.py` | `22FA7C3AF05CCAF9` | yes |
| `11-focus-guard.py` | `CE76C27E58D9AA0F` | yes |
| `acceptance-spec.json` | `57D69F697F20C4C1` | yes |

`ROOT` derives from the script's own path, so `data/` and `out/` became mine and
**not one file under `experiments/M62-sqrt-n/` was created, modified or deleted.**
The binary and the constant source came from `$STREHL_BIN` and `$STREHL_SRC`,
which is the seam M62 built for exactly this.

Two files in that directory are mine and are labelled as mine:
`src/m64-extra-spec.json`, which carries only the arm M62's spec cannot have
(section 5.1) with **tolerances copied verbatim and none changed**, and
`src/20-readout.py`, which reads the JSON `10-acceptance.py` wrote and re-scores
nothing.

### 3.2 Reproduction

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cargo build --release
$env:STREHL_BIN = "<repo>\target\release\strehl.exe"
$env:STREHL_SRC = "<repo>"                       # the REPO root, not crates/
cd experiments\M64-estimator-default
python src\01-pick-latent.py
python src\10-acceptance.py --tag m64
python src\10-acceptance.py --spec src\m64-extra-spec.json --tag m64-extra
python src\11-focus-guard.py --tag m64
python src\20-readout.py --tag m64
```

---

## 4. The invariant, and the proof that it can fail

### 4.1 What it tests

`strehl_core::merge::tests::the_default_path_reaches_the_arithmetic_limit_on_a_static_burst`
runs the **whole default path** on a synthetic static burst — `green_luma`,
`FocusField::compute`, `regularise`, pass one, pass two at `DEFAULT_GATE` — which
is the chain `merge_cmd::Ctx::field_for` runs, not a hand-built fold. It binds to
the constant the CLI binds to, so the CLI cannot drift away from it.

```
sqrt(N) invariant: N = 12, ideal = 3.4641
  all-frames mean : 3.4251x  (harness calibration, must be ideal +/- 2%)
  DEFAULT_GATE 4  : 3.4251x  at mean n_eff 12.000, bound sqrt(n_eff) = 3.4641
  gate 0 selector : 1.0033x  at mean n_eff 1.000  (negative control)
```

The negative control is inside the same test, so "R is large" cannot be
satisfied by a harness that is measuring nothing.

There is **no CI configuration in this repository** — no `.github/workflows`, no
pipeline file of any kind. The brief asked for a test that "runs in CI"; the
honest report is that the project's gate is `cargo test --workspace` plus
`scripts/corpus_lint.py`, the invariant runs in the first, and I did not invent a
CI system to be able to claim otherwise.

### 4.2 The power demonstration

A green tick proves nothing unless something makes it red, so I made it red
twice — once degenerately and once subtly.

`DEFAULT_GATE = 0.0`:

```
panicked at crates\strehl-core\src\merge.rs:2500:
the default gate averaged only 1.000 frames per pixel on a burst where every
frame is an equally valid measurement. Rule 36: a fixture that does not exercise
averaging cannot test an estimator.
```

`DEFAULT_GATE = 0.4` — not degenerate, `n_eff` near 3.9, the kind of quiet
regression that would survive an eyeball:

```
panicked at crates\strehl-core\src\merge.rs:2506:
the DEFAULT path scored 1.6749x on a static burst where sqrt(12) = 3.4641 is
provably correct and a selector scores about 1.0. The shipped default has
regressed towards selection.
```

`merge.rs` was restored from a copy in `$env:TEMP`, never with `git checkout --`.

A second test, `the_burst_fixture_can_fail_below_the_default_gate`, puts that
power in CI instead of in this report. It walks the ladder and requires that some
non-zero gate below the default score under the invariant's own floor:

| gate | R | mean `n_eff` |
|---|---|---|
| 0.25 | 1.3674 | 2.544 |
| 0.5 | 1.9212 | 4.876 |
| 1.0 | 2.8858 | 9.421 |
| 2.0 | 3.4198 | 11.971 |
| 4.0 | 3.4251 | 12.000 |

### 4.3 The limitation of my own fixture, stated because it is mine

**This fixture saturates far faster than M62's real-latent burst and therefore
cannot arbitrate the value of the gate.** At gate 2.0 it admits 99.8% of frames
where M62's real-latent burst admits 61%. Everything from about 2 upwards looks
identical here. It protects the proposition *the default is an estimator, not a
selector*, and nothing finer. Its own doc comment says so and derives why: the
gate rejects a frame when the winner beats it by more than `t*sqrt(2)` SDs, the
winner is a max over `N` and so sits about 1.63 SDs up at `N = 12`, and
`4*sqrt(2) = 5.66` exceeds that, so a rejection needs a frame 4 SDs below the
mean. On a smooth synthetic plant that essentially never happens.

`cargo test --workspace`: **222 passed, 0 failed**.
`cargo clippy --workspace --all-targets`: clean.

---

## 5. The two things I was told to check, and what the code actually said

### 5.1 Fact 84 — already wired, and its status clause is now stale

The brief lists fact 84 (spatial regularisation of the winner field, worth 35%
absolute error) as "verified, unbuilt". **It is wired, and it was wired before I
arrived.** `REGULARISER_RADIUS = 8` gives a 17x17 box, applied in
`merge_cmd.rs` for both passes, and the CLI prints its own citation on every run:

```
regulariser     : 17x17 box on the focus field (fact 84: -35% absolute error;
                  fact 86: width 3 is WORSE than none)
```

The confusion is in the fact row, and it is precise rather than vague. Fact 84's
status clause reads *"`strehl stack` does not regularise yet — so this is the
single largest measured quality win still unbuilt"*. That was **true of
`strehl stack`** and false of `strehl merge`. After M64 `strehl stack` *is* the
merge, so **the clause is now false of both**, and it should be updated rather
than left to mislead the next agent the way it misled this brief. Proposed as P1.

I built nothing for fact 84. Making the merge the default wires it into the
default by construction, which is the whole mechanism of this milestone.

### 5.2 Fact 19 — not a feature, and the brief has the operator wrong

The brief says "Fact 19: the gated mean scores 0.534x on the flat ROI" and lists
it as unbuilt. Fact 19 says something different:

> On the same frames and ROI, a plain **mean gives 0.534x**

**A plain mean, not a gated mean.** That distinction is the project. The plain
mean that scores 0.534x is the same operator fact 24 measures collapsing detail
by 58%, so it is a *control* — the thing the gate exists to avoid becoming — and
not a feature anyone could wire. Fact 19 has no unbuilt component; it is a
measurement of two negative controls (argmax 1.253x, plain mean 0.534x) plus a
placebo (0.981x), and the merge already cites the pair as its acceptance
invariants and prints both on every run.

Where the shipped default actually sits between them, MEASURED in section 2.3:
**0.788x on fact 19's own legacy statistic while retaining detail at 1.236x**.
That is the number the brief was reaching for, and it did not exist until now.
Proposed as P2, with the caveat that fact 19's 1.253x was taken on a different
focus operator, so the pairing is indicative and not matched.

---

## 6. Refutations

### 6.1 The price list the brief told me to surface is on a different axis

> "M57 measured the sharpness deficit of the estimator end at 0.496–0.740 px —
> that measurement is the price list the knob exposes."

**Wrong as stated, and I checked it before writing any help text.** M57 section 9
sweeps `gate 0.00 ... 0.99` with mean `n_eff` running **16.0 down to 1.45** — the
opposite direction to `--gate`, which runs `n_eff` *up*. Its acceptance rule is
`acc = cf >= (gate * peak)` in `experiments/m57-shape-metric/src/m57lib.py`, a
**fraction of the winner's peak height**, copied from
`experiments/m41-r3-kill/src/m41lib.py` where `GATE = 0.5` is documented as
"frames within 50% of PEAK HEIGHT". The shipped `--gate` is
`best - focus <= t*sqrt(2)*FOCUS_NOISE_SD`, a distance in units of the operator's
measured noise. `experiments/m41-r3-kill/src/a4_shipped_gate.py` says so in its
own docstring: *"A fractional gate is not the shipped [gate]... Different
operator, different gate units."*

**Consequence for the deliverable, which is the point of raising it:** the only
axis the two share is mean `n_eff`, so that is the axis `--help` prices the knob
on, and the help says in the text a user reads that M57's pixels are the *scale*
of the price and not a value of `T`.

### 6.2 M52's row labelled "tenengrad (shipped)" is not the shipped binary

Found while sourcing the default-gate argument, and it is the finding I would
keep if I could keep only one.

M52 section 5.3's operator table gives `109MSDCF` mean `n_eff` of **2.905** at
gate 2.0 and **5.017** at gate 4.0 for the row named `tenengrad (shipped)`. The
shipped binary reports **2.891** and **4.987**. MEASURED twice independently: by
M62 (`PREREGISTRATION-M64.md` section 1, the pre-M64 baseline, "1.414 / 1.884 /
2.891 / 4.987") and by me at `7213eff` (`out/11-focus-guard-m64.json`, 4.987).

**The mechanism is in M52's own table and is fully explanatory.** That row
carries `own C = 0.015318`. The shipped constant is
`FOCUS_NOISE_SD = 0.015214` (`merge.rs:185`), which the binary confirms in the
same run: it printed `tol 0.086063` at gate 4.0, and
`0.086063 / (4 * sqrt(2)) = 0.0152137`. A constant 0.68% higher admits slightly
more frames, which is the whole of the 0.5-0.6% gap.

**So M52 is not wrong — the row is mislabelled for anyone quoting it out of
context.** Section 5.3's caption says each operator carries *"its own correctly
measured constant"* and its closing paragraph contrasts *"the host's 0.015214"*,
so the report knows. But `(shipped)` in that cell means the shipped **operator**,
not the shipped **pipeline**, and M52's own sections 4.1 and 4.2 give 2.891 for
the same stack and gate — the report contains both numbers, 30 lines apart.

**I know it misleads because it misled me.** My first pre-registration draft
cited "gate 4.0 lands at 5.017 on `109MSDCF`" as a shipped-pipeline number in the
argument for a different default gate. It is not one. Proposed as P3 and Q1.

### 6.3 `--target-n-eff` cannot do what its own help said

`--target-n-eff` printed `This is the parameter to set, not --gate`. That is
false for anyone passing `--out`: `report_target_solve` prints a solved gate and
the image is still written at `gates[0]`. This is M49's defect 11 and it was
unfixed; the help now says so, names the defect, and says what to do instead. I
did **not** wire it, because writing at a solved gate needs a third pass over
the frames and I would be shipping unmeasured behaviour into the default path in
the same milestone that makes it the default.

### 6.4 What I could not check

M62's blind spot is real and mine does not close it. Its battery — and my
in-crate test — measure **noise efficiency on a plant where every frame is in
focus**. Neither tests focus correctness, and the burst's noise is drawn from the
same `g` and `RN_e` the gate uses, so both are circular with respect to sensor
calibration (rule 34). `11-focus-guard.py` is the only arm that touches real
through-focus data and it reads the binary's self-reported `n_eff`; it shows the
merge still discriminates (0.2267 of N), **not that it admits the right frames**.
The sharpness cost of gate 4.0 on real frames is unmeasured in this corpus on any
axis, which the pre-registration said before the result existed and which
`DEFAULT_GATE`'s doc comment says in the source.

---

## 7. The knob

**One knob: `--gate T`.** T = 0 is pure selection; raising T admits more frames
per pixel along a continuum toward a gated mean. Repeatable, because every value
folds in the same pass two — a sweep costs one decode budget, not one per value.
`--target-n-eff` is documented as a calibration aid, not a second knob, because
that is what it is (section 6.3).

What `--help` now tells a user, in the text they read:

- **The noise side**, on the plant where the answer is known: `T=0` scores 0.98x,
  `T=2` 3.78x, `T=4` 5.43x, `T=8` 5.48x against `sqrt(30) = 5.48`. On real frames
  a plain mean of a 22-frame stack reaches 0.534x flat-ROI noise (fact 19) and
  the shipped gate reaches 0.890x (fact 320).
- **The sharpness side**: that same plain mean collapses detail 58% (fact 24),
  which is what the gate exists to avoid; and M57's price, on the shared `n_eff`
  axis — 12.4 down to 1.45 recovered 0.556 px of PSF width against an
  oracle-confirmed ground truth, and 0.496-0.740 px on 6 of 8 real cells at
  3.95-17.58 sigma.
- **The caveat, in the same paragraph as the price, not in a footnote**: M57
  swept a fractional peak-height gate running the opposite way, so those pixels
  are the scale of the price and not a value of `T`, and the sharpness cost of
  *this* gate on real frames is not measured in this corpus.
- **That a gate is not portable**: the gate achieving a chosen `n_eff` varies
  28.9x across the corpus (M52), so the default is a starting point and not a
  calibration.

`DEFAULT_GATE`'s doc comment in `merge.rs` states what the number costs before
what it buys, and names the two rungs it rejects and why.

---

## 8. Declared in advance, and what happened

The pre-registration section 5 declared three things at `bd050ff` so they could
not later be presented as discoveries. All three occurred.

**The rename converts M62's `SELECTOR-shipped` power arm.** It ran
`stack {burst} ...` expecting at or below 1.05 and now measures the estimator.
It scored **5.4316, `NO-POWER`** — exactly the outcome M62 pre-registered, and
not a FAIL. M62 kept `CANNOT-CERTIFY` off the table because
`SELECTOR-same-binary` (`merge --gate 0`) is untouched and scored `POWER-OK` at
0.9768. The lost arm's semantics live at `argmax-baseline`, which scores
**0.769033477** — M62's published number for the old `stack`, to every digit.
**I did not edit `acceptance-spec.json`.** That is the acceptance authority's
file; the arm is in my own spec, labelled as mine.

**M57's axis** — section 6.1. **Facts 84 and 19** — section 5.

---

## 9. Rule walk

- **Rule 12** (label every claim): section 11.
- **Rule 13** (disclose fixture changes): `DEFAULT_GATE` was drafted at 2.0 and
  changed to 4.0 **before committing the pre-registration and before measuring
  anything**; the change, both reasons and the fact that the nwide-3 argument I
  had built the 2.0 case on does not survive its own source are in
  `PREREGISTRATION.md` section 1.1 at `bd050ff` and in the commit message.
- **Rule 18** (mean gradient bounds collapse only): fact 322 is quoted as a bound
  against collapse, never as a resolution measurement.
- **Rule 20** (a criterion must be able to fail): section 4.2 makes it fail,
  twice, and section 4.3 states where it cannot.
- **Rule 22**: this section.
- **Rule 33** (never `-q`): every build printed `Compiling` for all four crates;
  clippy printed `Checking`.
- **Rule 34** (calibration circularity): section 6.4.
- **Rule 36** (prove the fixture exercises the mechanism): PR10 asserts mean
  `n_eff` at least 3.0 inside the test.
- **Rule 39** (negative control in the same test): gate 0, inside the same test.
- **Rule 40**: section 12.
- **Never `git checkout --`**: `merge.rs` restored from `$env:TEMP` (section 4.2).
- **Path-scoped commits**: `bd050ff` touched only
  `experiments/M64-estimator-default/`; `7213eff` touched only the four crate
  files. Six other agents were live and HEAD moved under me twice
  (`7d13140` to `654b1cd9`) without `crates/` going dirty.
- **`corpus_lint`**: one pre-existing `S3` in
  `docs/research/M60-prior-art-and-the-rival-explanations.md` (ends in 3
  newlines), a live agent's file. Reported, not fixed — the same call M59 made on
  the same file. No violation is attributable to M64.

---

## 10. What I did not do

- **I did not verify my own work.** M62 is the acceptance authority, its
  pre-registration at `b94649c` predates my diff, and its run is the one that
  counts. Everything above is what my run of its battery said.
- **I did not weaken a threshold.** Every number in section 2.1 is graded against
  the value written at `bd050ff`, and PR1-PR3 are M62's thresholds, not mine.
- **I did not tune to the test.** Gate 8 scores better than the default and I
  left the default where I had pre-registered it (section 2.2).
- **I did not touch** `docs/research/SYNTHESIS.md`, `AGENTS.md`,
  `experiments/M62-sqrt-n/`, `crates/strehl-cli/examples/`, or any read-only
  corpus directory. Nothing was pushed.

---

## 11. Claim ledger

| claim | label | source |
|---|---|---|
| The new default scores 5.4316x at efficiency 1.0001, `CERTIFY` | MEASURED | `out/10-acceptance-m64.json` |
| `stack` and `merge` produce SHA-256-identical output | MEASURED | same, `96f71f10...` |
| `argmax-baseline` scores 0.769033477 | MEASURED | `out/10-acceptance-m64-extra.json` |
| The default admits 4.987 of 22 frames on a real stack | MEASURED | `out/11-focus-guard-m64.json` |
| Default 0.749x vs baseline 1.223x HP ratio on real frames, detail 1.236x | MEASURED | `out/30-*.log`, `out/31-*.log`, post-hoc |
| In-crate default 3.4251x, gate 0 1.0033x, ladder in section 4.2 | MEASURED | `cargo test -- --nocapture` |
| The invariant fails at `DEFAULT_GATE` 0.0 and 0.4 | MEASURED | section 4.2 |
| Fact 84's regulariser is in the default path | MEASURED | `merge_cmd.rs`, CLI banner |
| M52 section 5.3's `tenengrad (shipped)` row carries C = 0.015318, the binary carries 0.015214 | MEASURED | M52 section 5.3; `merge.rs:185`; printed `tol 0.086063` |
| That constant gap explains the 2.905/2.891 and 5.017/4.987 discrepancies | DERIVED | ratio of constants vs ratio of `n_eff` |
| M57's price list is measured on a fractional peak-height gate | MEASURED | `m57lib.py`, `m41lib.py`, `a4_shipped_gate.py` |
| A fixed `T` is an N-dependent statement, since the reference is a max over N | DERIVED | `E[max of N normals]`; matches M62's ladder |
| Gate 4.0 is the right default | ARGUED | section 2.2; the sharpness side is unmeasured |
| Renaming beats documenting `merge` as the entry point | ARGUED | section 1.2 |
| There is no CI configuration in this repository | MEASURED | `git ls-files`, section 4.1 |

---

## 12. Reports relied on

Rule 40. **M62** (`M62-sqrt-n.md` and `PREREGISTRATION-M64.md`) — the instrument,
its ladder, its thresholds, its baseline, and the blind spot in section 6.4 which
is its statement and not mine. **M52** — the per-stack gate ladder, the 28.9x
solved-gate spread, and section 6.2. **M57** — the price list and section 6.1.
**M49** — defect 11 and the discipline of checking whether a finding reached the
code. **M15** — fact 84's 35%. **M2-verification** — facts 19 and 24. **M40** —
why `SELECTION_INFLATION` is 1.0. **M59** — the precedent for reporting the
pre-existing `S3` rather than fixing another agent's file. **M24** — the drift
figures the sensitivity report quotes.

---

## Proposed

Numbered for the orchestrator to fold. Rule 28: no absolute numbers proposed.

**P1.** Fact 84's status clause — *"`strehl stack` does not regularise yet, so
this is the single largest measured quality win still unbuilt"* — is now false in
both halves. `strehl stack` **is** the regularised merge as of `7213eff`, so the
regulariser is in the default path and the win is built. The measurement itself
is unaffected.

**P2.** The shipped default's position between fact 19's two controls, MEASURED
on the same stack and ROI as fact 19, together with its paired detail retention.
The pairing across fact 19's own numbers is indicative only, because fact 19's
argmax figure was taken on a different focus operator; the argmax figure in
section 2.3 is matched, same binary and same run.

**P3.** M52 section 5.3's row labelled `tenengrad (shipped)` does not reproduce
the shipped binary, because it carries a re-measured per-operator constant rather
than `FOCUS_NOISE_SD`. Anyone quoting that row as shipped-pipeline behaviour gets
a mean `n_eff` a few tenths of a percent high. The shipped ladder is M52 section
4.1's, and the same report gives both.

**Discipline D1.** A table row naming a *component* as "(shipped)" while
carrying a constant the shipped build does not have is a citation trap, because
the label survives the quotation and the constant does not. Where a row differs
from the binary in any constant, the cell should say which — the report that
contains section 5.3 also contains the correct value 30 lines away, and that was
not enough to stop it being misquoted in this milestone's own first draft.

**Question Q1.** Is any other published ladder in the corpus a re-measured-constant
run rather than a shipped-pipeline run? P3 was found by accident while sourcing
one number. The check is mechanical — any table quoting a constant beside a
result can be compared against the crate — and nobody has run it.

**Question Q2.** The gate compares each frame against a maximum over `N` frames,
so under the null of equal focus the winner is biased upward by roughly
`E[max of N standard normals]`, which grows with `N`. A fixed threshold is
therefore an N-dependent statement about statistical indistinguishability, and
M62's ladder is consistent with that. Should the gate be made `N`-aware? **Do not
build this without deciding first**: it would invalidate every gate calibration
in the corpus, since every published `--gate t` result was taken at that stack's
own `N`.

**Question Q3.** The corpus identifies the merge's mean `n_eff` with fact 212's
`nwide` — `merge_cmd.rs` names `nwide = 3` as the gate's calibration target — but
they are different acceptance rules: `nwide` is a fraction of peak height, `n_eff`
is a distance in units of the operator's noise. They agree closely on `109MSDCF`.
Is that agreement a property of the rules or of that stack? The pre-registration
declined to lean on the identification for exactly this reason.
