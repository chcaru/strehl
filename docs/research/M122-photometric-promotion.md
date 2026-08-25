# M122 — Does blotch severity track measured level drift?

**Question 203.** *Does the severity of the merge's background "blotch" defect
track the measured inter-frame level drift, across the whole capture corpus?*

**Answer: yes — ρ = +0.70, one-sided permutation p = 0.0035, n = 14 stacks.**
**Verdict on the default flip: KEEP-OFF.** The correlation passes; the
pre-registered *no-harm* criterion fails. `STREHL_PHOTOMETRIC` was **not**
flipped. Nothing under `crates/` was touched.

Pre-registered in `experiments/M122-photometric-promotion/PREREGISTRATION.md`,
committed `98728d2`, **before any arm was rendered**. Every criterion below is
quoted from that file; none was renegotiated after the numbers existed.

---

## 0. Provenance

Pinned binary, verified before use (PREREGISTRATION §1):

```
C:\dev\strehl-out\M116-tree\target\release\strehl.exe
commit  4beac7300e318f6f0aaf10b6a88e57f311b9e814   (worktree clean)
sha256  51B9235B7ACA203A1B171C69B6A5198E1EF2034F7E5446CE4891250AF7BBB078
bytes   8959488
```

The same binary M116 used, so these numbers are directly comparable to M116's.

Every invocation — argv, env, exit code, wall seconds, output SHA-256 and bytes
— is in `C:\dev\strehl-out\M122\ledger-measure.csv` (AGENTS.md rules 46, 47).
Per-run logs are in `C:\dev\strehl-out\M122\logs\`.

**Registration is frozen per subject.** `align` was solved once per stack into a
sidecar under `C:\dev\strehl-out\M122\warp\`, and both arms were rendered with
`STREHL_WARPMAP=<that sidecar>` and nothing else. The arms differ only in
`--photometric`. Protocol copied from `experiments/M116-promotion/run_measure.ps1`.

---

## 1. Instrument commissioning — the three reproductions

**M1 (MEASURED).** *My A0/A1 arms reproduce M116's bit-for-bit.* For the three
M116 subjects (`bee-3-cpl`, `foam`, `tweezers-cpl`) my six output TIFFs are
byte-identical to the SHA-256s in `C:\dev\strehl-out\M116\ledger-measure.csv`,
**3/3**, from a warp map I solved independently in an isolated cache dir. The
render path is reproduced, not merely re-run.

```powershell
powershell -File experiments\M122-photometric-promotion\run_campaign.ps1
# then compare ledger-measure.csv sha256 columns against M116's
```

**M2 (MEASURED).** *My drift estimator reproduces M24's four published numbers
and the M93 number exactly.* Replication arm, deltas all ±0.00:

| stack | frames | M24 published | M122 measured | delta |
|---|---:|---:|---:|---:|
| 109MSDCF | 22 | 0.91 % | 0.911 % | +0.001 |
| 119MSDCF | 33 | 2.88 % | 2.878 % | −0.002 |
| coffee-bean | 35 | 11.70 % | 11.701 % | +0.001 |
| 112MSDCF | 40 | 6.84 % | 6.836 % | −0.004 |
| coffee-bubbles | 19 | 8.93 % | 8.929 % | −0.001 |

(These use M24's own frame counts. The corpus arm in §3 uses `L = min(100, N)`,
so e.g. `coffee-bean` reads 12.065 % over 100 frames against 11.701 % over 35.)

```powershell
python experiments\M122-photometric-promotion\drift.py m24
```

**M3 (MEASURED).** *My blotch A/B reproduces fact 1637's three published numbers
exactly.* `tweezers-cpl` 0.7102 (published 0.710), `bee-3-cpl` 1.0638 (1.064),
`foam` 1.0126 (1.013).

```powershell
python experiments\M122-photometric-promotion\blotch_ab.py
```

**M4 (MEASURED).** *The correlation code is not the finding.* Self-test on
synthetic pairs: a monotone pair returns ρ = 1.000000 at p = 0.0005; a random
pair returns ρ = −0.305 at p = 0.191 against a null sd of 0.227.

```powershell
python experiments\M122-photometric-promotion\correlate.py
```

**M5 (MEASURED).** *`D:\` was not written.* `Get-ChildItem -Force -Recurse`
census of `D:\personal\macro` before and after the campaign: **4623 files,
253 730 319 986 bytes**, identical. (AGENTS.md rule 14 — `-Force`, so hidden
sidecars would have shown.)

---

## 2. The corpus, and what `--photometric` does to it

23 subject directories under `D:\personal\macro` carry ARW frames. Nine are
excluded by rules fixed in PREREGISTRATION §6.4 before any of them was scored:

| stack | rule | why |
|---|---|---|
| `112MSDCF` | E2 | A1 **exit 1** — `the eroded photometric region keeps only 886 px (minimum 1024)` |
| `coffee-bubbles` | E2 | A1 **exit 1** — same error, 442 px after eroding |
| `highly-angled-ruler-mm-cpl` | E2 | `align` exit 1, subject not normal to the optical axis; `--force-tilted` deliberately **not** passed |
| `dry-erase-marker-head-cpl` | E3 | A0 SHA == A1 SHA. The fit **refused all 100 frames** (`clipped fraction 3.245e-1 exceeds 1.000e-4`), gain span 1.0000 |
| `109MSDCF`, `flower-bud-alone-cpl`, `flower-bud-with-background-fern-cpl`, `wrapped-text-1`, `wrapped-text-2` | E4 | the in-run commissioning triple failed on that stack's own pixels |

**M6 (MEASURED).** ***`--photometric` is not safe to switch on for everyone,
independently of any correlation.*** On 23 stacks it **hard-errors on 2** and
**silently does nothing on 1**. If the default flipped, `112MSDCF` and
`coffee-bubbles` would stop rendering — a working command would start failing.
This alone blocks a default flip and is the most decision-relevant thing I
measured.

```
C:\dev\strehl-out\M122\logs\112MSDCF__A1-photometric.log     (exit 1)
C:\dev\strehl-out\M122\logs\coffee-bubbles__A1-photometric.log (exit 1)
C:\dev\strehl-out\M122\logs\dry-erase-marker-head-cpl__A1-photometric.log
```

**M7 (MEASURED).** *Bit-identity control (PREREGISTRATION §5.2).* Of the 20
stacks where both arms rendered, **19 have A0 SHA-256 ≠ A1 SHA-256**. The flag
demonstrably did something on every stack scored, so no null below is a plumbing
null. The one exception is `dry-erase-marker-head-cpl`, excluded as E3.

---

## 3. The two measured quantities

**M8 (MEASURED).** Per-stack level drift `Dpp` (M24's estimator verbatim: mean of
`raw_image_visible[0::2,1::2] − 512` per frame, normalised to the stack mean,
`100·(max−min)`), computed over **exactly the L frames the merge consumed**.

**M9 (MEASURED).** Per-stack blotch response `B12` = median over 12 windows of
laplacian-RMS(A1)/laplacian-RMS(A0). Windows chosen by ORCH's rule, unchanged:
brightest 20 % pool, then the 12 lowest `w[::8,::8].std()`, **both computed on the
symmetric mean `(A0+A1)/2`**, so neither arm chooses the pixels it is judged on.

### The 14 usable stacks

| stack | Dpp % | B12 | Sdd12 | T12 | hf0 smooth | gain span |
|---|---:|---:|---:|---:|---:|---:|
| `tweezers-cpl` | 13.765 | **0.7102** | 1.0005 | 1.0199 | 77.1 | 1.1451 |
| `coffee-bean` | 12.065 | **0.9052** | 0.9211 | 1.0008 | 193.6 | 1.0991 |
| `bee-1-cpl` | 11.271 | **0.9485** | 0.9901 | 1.0424 | 33.2 | 1.1405 |
| `foam` | 10.617 | 1.0126 | 1.0113 | 1.0084 | 3712.1 | 1.5307 |
| `flowers-cpl` | 10.447 | 0.9731 | 0.9805 | 1.0366 | 48.3 | 1.0523 |
| `lavendar-cpl` | 10.395 | 0.9705 | 0.8859 | 0.9708 | 38.9 | 1.1057 |
| `couch-fibers-cpl` | 8.909 | 0.9752 | 0.9911 | 0.9868 | 58.6 | 1.1395 |
| `113MSDCF` | 7.999 | **1.0699** | 1.0754 | 1.0565 | 666.3 | 1.0987 |
| `flat-on-ruler-cpl` | 5.892 | 1.0012 | 1.0010 | 0.9907 | 974.1 | 1.1069 |
| `leaf-2-cpl` | 5.315 | 0.9935 | 0.9937 | 1.0058 | 263.1 | 1.0550 |
| `119MSDCF` | 2.878 | 1.0013 | 1.0023 | 1.0089 | 229.4 | 1.0285 |
| `lead-1-cpl` | 2.026 | 0.9963 | 0.9967 | 1.0079 | 115.7 | 1.0187 |
| `bee-2-cpl` | 1.652 | 1.0042 | 0.9956 | 1.0263 | 57.3 | 1.0346 |
| `bee-3-cpl` | 1.629 | **1.0638** | 0.9664 | 1.0355 | 41.6 | 1.0433 |

---

## 4. The answer to question 203

**M10 (MEASURED). The severity of the blotch defect does track measured level
drift.**

```
Spearman rho( Dpp , 1 - B12 )  over n = 14 usable stacks

  rho              = +0.7011
  one-sided p      =  0.0035     (20 000 label permutations; MC se ~0.0004)
  two-sided p      =  0.0073
  permutation null sd = 0.2778
  Pearson (shape only) = +0.6225
```

```powershell
python experiments\M122-photometric-promotion\correlate.py
```

Rule 39: the ratio is reported against the null it is measured against. ρ = 0.70
is 2.5 null-sd from zero.

**Power check (registered in advance so it could not be invoked selectively):**
IQR(`B12`) = 0.0323 ≥ 0.02 **PASS**; IQR(`Dpp`) = 7.087 pp ≥ 1.0 **PASS**. The
corpus carried real variation in both axes, so the test had power to fail.

**M11 (MEASURED). The correlation is not the "smooth backgrounds are smooth"
confound.** PREREGISTRATION §6.3 A1 registered the worry that a stack's baseline
`hf0` could drive both axes. It does not: ρ(`Dpp`, `hf0`) = −0.029, and the
**partial** ρ(`Dpp`, 1−`B12` | `hf0`) = **+0.7550** — *stronger* with the
baseline removed, against a registered floor of +0.20.

**M12 (MEASURED). The size of the fitted correction tracks the drift.**
ρ(`Dpp`, gain span − 1) = **+0.7714**. The correction the code fits is measuring
the same physical quantity my estimator measures, independently.

**M13 (MEASURED). Fact 1638's visual claim reproduces under a rule-based window
selection.** The symmetric-mean rule independently landed on both coordinates
fact 1638 cites by hand. At `tweezers-cpl` x=912 y=400 under one shared stretch,
the default arm shows the soft oval patches and the photometric arm shows none
(hf 78.7 → 49.7). At the blur control x=400 y=656 the tweezer edge and grain are
preserved (hf 1056.1 → 1079.2, **up** 2 %).

```powershell
python experiments\M122-photometric-promotion\look.py tweezers-cpl bee-3-cpl
# C:\dev\strehl-out\M122\sheets\
```

**M14 (MEASURED). The fix is additive-subtractive, not multiplicative — which is
why it cannot be blurring.** On `tweezers-cpl` the eight responding windows start
at hf 56.7, 62.1, 64.7, 68.1, 70.5, 75.6, 78.7, 78.9 and all land within
45.0–52.8. It drives an excess down to a **common floor** rather than scaling
everything by a constant. A blur would scale the textured windows too; 11 of the
12 textured windows (hf0 1624–3565) read 1.013–1.031, i.e. slightly **up**.

*Caveat on the textured set, recorded because it initially looked like a
problem.* A variant of the texture control that forces ≥ 256 px separation
between window centres reads 0.8846 on `tweezers-cpl`, which would have failed.
Inspecting the windows shows why: the textured set has no brightness gate, so one
window at x=1680 y=528 with `hf0` = 55.7 — smooth background, ranked "textured"
because a large-scale gradient inflates its `std` — leaks in and reads 0.845, the
same blotch removal as the smooth set. The genuinely textured windows are
unanimous. The registered criterion is `T12` and `T12` passes; the separated
variant fails for a reason that is a defect in the variant.

**M15 (MEASURED). Neither fact-1640 broken-link test fired.** L1 needs a null ρ
with a real responder present — ρ is +0.70, not null. L2 needs a stack with
`Dpp < 1.5 %` reading `B12 < 0.85` — the lowest-drift usable stacks read 1.0042
and 1.0638, no strong fix without drift. **Fact 1640's mechanism chain survives
this test intact.**

---

## 5. Controls

**M16 (MEASURED). Commissioning triple, per stack, on that stack's own pixels
(§5.1).** null must be exactly 1.0000, plant+ > 1.30, plant− < 0.77 — plant−
being the one that matters, since the effect under test is a reduction. It
**passed on 14 stacks and failed on 5**, all of them stacks whose background is
already textured (high `hf0`), where a voronoi plateau plant of amplitude 2·sdd
does not move an already-large laplacian enough to clear the bar. Those five are
excluded as **not interpretable**, not as nulls. `109MSDCF` — my intended
low-drift control — is among them: plant+ 1.2857 (needs > 1.30), plant− 0.7778
(needs < 0.77), both just outside.

**M17 (MEASURED). The blur control has power (rule 20 — the input that would
make the gate fail).** A σ=0.5 gaussian blur of A0, scored as if it were the test
arm, is caught on **every** stack: textured-window ratios 0.5528–0.8177, median
0.7287, all far below the 0.90 detection bar. The texture control is not a gate
that cannot fire.

**M18 (MEASURED). Blur control clean on every responder.** The three stacks with
`B12 < 0.97` read `T12` = 1.0199, 1.0008, 1.0424 — all ≥ 0.97. **P4 passes, K3
does not fire.** The effect is confined to smooth windows.

**M19 (MEASURED). Low-drift control.** With `109MSDCF` excluded by E4, the
lowest-drift usable stack is `bee-3-cpl` at 1.629 %, and it reads `B12` = 1.0638
≥ 0.97 — no benefit where there is no drift. **P5 passes.** For the record,
`109MSDCF` itself (0.911 % drift, the quietest stack in the corpus) reads
`B12` = 1.0050 and `T12` = 1.0004: no benefit, exactly as the mechanism predicts.
That reading is *consistent* but not *interpretable*, because its own
commissioning failed, and I am not entitled to lean on it.

---

## 6. The verdict, read off the pre-registered criteria

| criterion | requirement | result | |
|---|---|---|---|
| P1 | ≥ 12 usable stacks | 14 | PASS |
| P2 | ρ ≥ +0.50 and one-sided p < 0.05 | +0.7011, p = 0.0035 | PASS |
| **P3** | **no stack with `B12` > 1.03** | **113MSDCF 1.0699, bee-3-cpl 1.0638** | **FAIL** |
| P4 | every responder has `T12` ≥ 0.97 | min 1.0008 | PASS |
| P5 | lowest-drift stack has `B12` ≥ 0.97 | 1.0638 | PASS |
| K1 | ρ < +0.20 or p ≥ 0.05 | — | clear |
| **K2** | **any stack `B12` > 1.03** | **two stacks** | **FIRED** |
| K3 | any responder `T12` < 0.97 | — | clear |
| power | IQR(B12) ≥ 0.02, IQR(Dpp) ≥ 1.0 | 0.0323, 7.087 | PASS |

> ### VERDICT: **KEEP-OFF**
>
> Question 203 is answered **yes**. The promotion is refused anyway, because K2
> fired. `STREHL_PHOTOMETRIC` stays OFF by default.

**M20 (MEASURED). One of the two harm readings is an artefact of the published
statistic; the other is real.** `hf` is an *absolute* laplacian RMS, so it scales
with image level, and the photometric arm normalises frames to a reference frame
and can move the output level. On `113MSDCF` the smooth-window level ratio is
**1.0684** and `B12` is **1.0699** — dividing gives **1.0014**, i.e. that entire
"harm" is a 6.8 % gain, not one extra unit of structure. On `bee-3-cpl` the level
ratio is 1.0005 and the level-normalised response is **1.0633**: real, and
consistent across **12 of 12** windows (1.009–1.123).

```powershell
python experiments\M122-photometric-promotion\posthoc.py
```

**This does not rescue the flip.** Under the registered statistic K2 fires twice;
under the (post-hoc, unregistered) level-normalised statistic it still fires once.
KEEP-OFF is robust to the artefact. It is reported because the artefact is a
property of the instrument that produced fact 1637 and you will want to know
about it (see §8).

**A1 (ARGUED). What `bee-3-cpl` is telling us is coherent, and it is the reason
the flag must stay opt-in.** On that stack 11 of the 12 smooth windows have
`hf0` between 28.4 and 51.2 counts, which is what ~47 averaged frames of photon
noise looks like at that level — there is no blotch there to remove. Yet `Sdd12` = 0.9664 (plateau
amplitude down 3.4 %, in 11 of 12 windows) while `B12` = 1.064 (noise-band energy
up 6.4 %, in 12 of 12). The correction removes what plateaus exist **and adds
noise**. Where drift is large the removal dominates and you win; where drift is
near zero you pay the noise and gain nothing. That is a *cost*, not a bug — and
it is exactly the shape of thing that must not be imposed on every user by
default. The gate's admission set is not the cause: mean `n_eff` A1/A0 is 0.99994
median across the corpus (0.9999 on `bee-3-cpl`).

**A2 (ARGUED). The harm is measurable but not visible.** Under one shared stretch
at `bee-3-cpl` x=2832 y=400 (its worst window, ratio 1.1231) the two panels are
indistinguishable by eye. I am not softening K2 with this — the criterion was
registered and it fired — but the magnitude deserves its context: I would call
this "a reason not to impose it", not "a reason to warn people off the flag".

---

## 7. Everything that argues against my own conclusion

Listed because the conclusion is worth less without them.

1. **`foam` is a direct counterexample to proportionality.** 10.617 % drift —
   fourth highest — and `B12` = 1.0126, no response at all. Its smooth-window
   `hf0` is 3712 counts, ~90× `bee-3-cpl`'s, so its "smooth" windows are not
   smooth and a blotch could hide under its own texture. That is a floor
   argument, and floor arguments are exactly what a motivated reasoner reaches
   for. It may simply be a stack where the mechanism does not operate.
2. **The plane-detrended-sd statistic shows no correlation at all.**
   ρ(`Dpp`, 1−`Sdd12`) = **+0.1253, p = 0.3237** — a clean null. `Sdd12` is
   arguably the *more* direct measure of "level plateaus", which is what fact
   1640's mechanism predicts. My headline rests on the laplacian statistic and
   the second statistic does not corroborate it. On `tweezers-cpl` — the
   milestone's strongest subject — `Sdd12` = 1.0005, i.e. no effect whatsoever
   where `B12` says 29 %.
3. **The other drift estimator weakens the result.** ORCH's six-fixed-window
   estimator `Dwin` agrees with `Dpp` only at ρ = 0.613, and
   ρ(`Dwin`, 1−`B12`) = **+0.2923, p = 0.1522** — *not significant*. If you pick
   the estimator that argues against me, the headline does not survive at
   p < 0.05. I chose `Dpp` before seeing any of this, on the stated grounds that
   it reproduces four folded numbers exactly and that fixed windows land on the
   subject in subject-filling stacks — but the honest statement is that
   **the result is estimator-dependent**.
4. **Eight `-cpl` stacks show a perfectly linear drift ramp** — linear fit
   explains ≥ 0.99 of variance with jitter ≈ 0.03 % (`dry-erase-marker-head-cpl`
   1.000/0.025 %, `flower-bud-alone-cpl` 1.000/0.028 %, `flowers-cpl`
   1.000/0.030 %, `tweezers-cpl` 0.999/0.040 %). That is too clean for lamp
   drift. It looks like focus breathing scaling content across the frame edge —
   question 202's confound. If so, the x-axis of my correlation is partly *not*
   the quantity `--photometric` corrects, and both `Dpp` and the fitted gain
   would inherit the same artefact, which would explain their ρ = +0.77
   agreement without either being illumination.
5. **The usable set is biased toward smooth-background subjects.** All five
   commissioning failures are high-`hf0` stacks. The instrument is
   systematically blind exactly where a blotch would be hardest to see, so the
   corpus I correlated over is not the corpus.
6. **n = 14, and one point dominates.** `tweezers-cpl` supplies the only large
   response (0.710); the next is 0.905. Spearman limits the leverage, but a
   14-point rank correlation resting on one extreme is not a strong corpus
   result.
7. **My low-drift control failed its own commissioning.** `109MSDCF` was named
   in the brief and pre-registered as the low-drift control and it is excluded by
   E4. `bee-3-cpl` inherited the role and passes — but it also fires K2, so the
   stack discharging P5 is the same stack failing P3.
8. **M116 was right.** Its KEEP-OFF verdict (+0.00477 / −0.00003 / +0.00835
   against a +0.010 bar) is not contradicted here. It measured sharpness with a
   sharpness bar and the defect is tonal, so it could not have seen this; and its
   conclusion — do not flip — is the same as mine.

---

## 8. Two things you may want to fold that are not question 203

**M21 (MEASURED). `photometric_ab.py`'s `hf` ratio is not level-normalised, and
on one published subject this changes the sign.** The published `foam` figure of
1.013 sits on a smooth-window level ratio of **1.0185**; normalised it is
**0.9943**. `foam` reads as a slight *increase* in the folded fact and a slight
*decrease* once level is divided out. `tweezers-cpl` (level 0.9888 → 0.7183) and
`bee-3-cpl` (1.0005 → 1.0633) are essentially unaffected, so **fact 1637's
headline is safe** — but any future stack whose photometric arm moves level will
read a spurious ratio of exactly that size, and `113MSDCF` here is a 6.99 %
example of it. Recording the level ratio alongside was ORCH's own idea; it
just is not divided out.

**M22 (MEASURED). The A1 diagnostic block lies when it succeeds.** On
`bee-3-cpl` the A1 log fits and applies a gain (span 1.0433, region 1 148 768 px
after eroding) and then prints
`STATUS: NO per-frame gain term is fitted or applied`. Seen on every A1 run.
`C:\dev\strehl-out\M122\logs\bee-3-cpl__A1-photometric.log`. Not mine to fix;
it is in `crates/`.

**A3 (ARGUED). AGENTS.md ledger gap.** Rule 41 wants a ledger row per milestone
written at dispatch. There is no `M116` row and no `M122` row; the last is
`M113`. The ledger is yours — flagging, not editing.

---

## 9. The default flip: not made

PREREGISTRATION §9 permits the flip only on a PROMOTE verdict. The verdict is
KEEP-OFF, so **nothing under `crates/` was read into an edit, modified, or
committed.**

Ownership was checked anyway, as instructed:

```powershell
git --no-pager status --porcelain crates/strehl-cli/src/main.rs   # clean
git --no-pager log -3 --oneline -- crates/strehl-cli/src/main.rs  # 2764605 M97q ...
```

`crates/strehl-cli/src/main.rs` is **clean and unowned** — the flip was blocked
by my own criterion, not by another agent. The patch, for the record, would have
been at line 283:

```rust
-        #[arg(long)]
-        photometric: bool,
+        #[arg(long, default_value_t = true, action = clap::ArgAction::Set,
+              num_args = 0..=1, require_equals = false, default_missing_value = "true")]
+        photometric: bool,
```

plus a `--no-photometric` negation, plus a test pinning the new default. **Do not
apply it.** Even setting K2 aside, M6 stands on its own: two stacks in this
corpus stop rendering entirely when the flag is on.

---

## 10. What this milestone does not claim

- Not that `--photometric` improves sharpness. It does not measure sharpness.
- Not that the correlation is causal. It is a 14-point rank correlation with a
  plausible mechanism and one honest counterexample.
- Not that `--photometric` should be discouraged. On `tweezers-cpl` it removes a
  visible defect and preserves detail; **as an opt-in flag on high-drift subjects
  it is doing real work.** The recommendation is precisely: keep it opt-in,
  document that it pays off above roughly 8–10 % drift, and fix the hard error
  before anyone considers this question again.

---

## Proposed facts for folding (numbered locally, per rule 28's corollary)

- **P1** Blotch severity tracks measured inter-frame level drift across the
  corpus: Spearman ρ(`Dpp`, 1−`B12`) = **+0.7011**, one-sided permutation
  p = 0.0035, null sd 0.2778, n = 14. *(answers question 203, yes)*
- **P2** The correlation is not a baseline-smoothness confound: partial
  ρ | `hf0` = **+0.7550**; ρ(`Dpp`, `hf0`) = −0.029.
- **P3** The gain the code fits tracks the independently measured drift:
  ρ(`Dpp`, gain span − 1) = **+0.7714**.
- **P4** `--photometric` **hard-errors (exit 1)** on 2 of 23 corpus stacks
  (`112MSDCF` 886 px, `coffee-bubbles` 442 px against a 1024 px minimum) and is a
  **silent no-op** on 1 (`dry-erase-marker-head-cpl`, 100/100 frames refused for
  clipping, A0 byte-identical to A1).
- **P5** On a near-zero-drift stack the correction **costs** noise: `bee-3-cpl`
  (1.63 % drift) reads `Sdd12` 0.9664 but `B12` 1.0638, level-normalised 1.0633,
  consistent in 12/12 windows, with mean `n_eff` unchanged at 0.9999.
- **P6** The fix drives smooth-window laplacian RMS to a **common floor**
  (`tweezers-cpl`: eight windows from 56.7–78.9 all land at 45.0–52.8) rather
  than scaling it, while textured windows read 1.013–1.031. It is not smoothing.
- **P7** `photometric_ab.py`'s `hf` ratio is not level-normalised; on `foam` the
  published 1.013 becomes 0.9943 once the 1.0185 level ratio is divided out.
- **P8** The plane-detrended-sd statistic does **not** corroborate P1:
  ρ(`Dpp`, 1−`Sdd12`) = +0.1253, p = 0.3237. The two statistics disagree on
  `tweezers-cpl` (1.0005 vs 0.7102).
- **P9** M122 verdict: **KEEP-OFF**, on pre-registered criterion K2. Question 203
  is answered yes and the default was still not flipped.

---

*Instruments: `experiments/M122-photometric-promotion/{run_campaign.ps1, drift.py,
blotch_ab.py, correlate.py, posthoc.py, look.py}`. Outputs:
`C:\dev\strehl-out\M122\`. `experiments/ORCH-drift-check/` was read and never
modified. `docs/research/SYNTHESIS.md` was read and never modified.*
