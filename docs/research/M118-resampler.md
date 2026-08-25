# M118 — the resampler A/B at merge time: the gain is real, and it is the kernel's datasheet rather than a fact about the photographs

**Agent:** M118-resampler. **Pinned SHA:** `4beac7300e318f6f0aaf10b6a88e57f311b9e814`,
measured in an isolated worktree at `C:\dev\strehl-out\M118-tree` with a private
`CARGO_TARGET_DIR`. Nothing under `crates/` was touched; nothing under `D:\` was written.
**Pre-registration:** `experiments/M118-resampler/prereg.txt`, committed at `16f2dd2`
before any outcome number existed.
**Every number below is transcribed from `experiments/M118-resampler/out/dump.txt`**,
which exists so that no figure here comes out of my notes.

---

## 0. Read this first — my brief's premise was false

My dispatch said the resampler comparison "has **never been measured** on real
frames at merge time" and proposed the sidecar-edit method as the cheap way in.
Rule 43 requires that an assertion of absence be established by search. I ran the
search before writing anything, and:

- **`docs/research/M113-kernel-verify.md` already did this**, on `bee-3-cpl`, 299
  frames, two merges from one solve with sidecars differing by exactly one line —
  **the identical method, described as novel in my brief**. It reported
  **+0.083 to +0.099 dex**, a byte-identical null, and 1:1 crops.
- **`docs/research/ORCH-kernel-decision.md` is a pre-registered GO/NO-GO** on
  exactly the question "should the default move to Lanczos-3", with criteria
  G1–G4 and N1–N4.
- `M95-kernel.md` landed Lanczos-3 switchable and deliberately did not move the
  default; `M95-resample.md` carries the −0.2360 dex decomposition; `M104c-mtf.md`
  records that a slanted-edge instrument already exists.

So I did not re-answer the headline. I scoped this milestone to what those
documents leave open, and I replicated their headline only as a calibration check
so my instrument can be read against theirs. **The single most useful thing I can
tell ORCH is not "lanczos3 wins" — it is *what that win is made of*.**

---

## 1. Verdict

| # | question | verdict |
| --- | --- | --- |
| 1 | Does lanczos3 beat the catmull-rom default end-to-end? | **Yes.** +0.0868 dex on `bee-3-cpl`, replicating M113's +0.083–0.099. Across three subjects **+0.0859 to +0.1125** |
| 2 | Is that gain a fact about the owner's photographs? | **Largely NO.** A closed form from `align.rs`'s own weights, **with no image at all**, predicts it to a mean of **0.0155 dex** over 12 cells against a mean effect of 0.1300. **The photographs move the answer by 11.9%** |
| 3 | Is the gain concentrated where the detail is? | **NO, on all three subjects.** Rule 9's flat-decile control **fails** for lanczos3 every time: M2 ≥ M1, by −0.0129 / −0.0002 / −0.0162 dex |
| 4 | ORCH's **N4** — does the election stratification reverse on a second subject? | **Not reversed on 2 of 3.** It reverses on `wrapped-text-1`, but by **2.5% of the effect**, and the correlation's *sign* is unstable (+0.382 / +0.059 / −0.293). **N4 as written is reading noise** |
| 5 | Does lanczos3 ring where `n_eff` = 1, with no phase averaging to save it? | **Slightly, and it does not blow up.** At `n_eff` **1.17** the excess-extrema ratio is **1.2513x**, against **1.1438x** at `n_eff` 53.67. Bounded, consistent with ORCH §8.3's 1.425x ceiling |
| 6 | Where do `nearest`, `bilinear`, `lanczos2` sit? | Measured end-to-end **for the first time**: **+0.1889 / −0.2181 / +0.0047** predicted, matched by measurement. `nearest` **tops the band metric** — exactly as pre-registered, and it is why the metric cannot name a winner |
| 7 | Is `lanczos2` worth having? | **No.** +0.0027–0.0052 dex from the default, 98.3–99.7% election agreement — and it is **unreachable from any command line** |
| 8 | By eye at 1:1 and x3, non-author read | **lanczos3 is visibly crisper** than the default on ink grain and on the bee's ommatidia, **with no dark rim on silhouettes**. It also makes the **lateral-CA fringes more conspicuous** — corroborating M110 |
| 9 | Cost | **2.91x–3.92x** catmull-rom, as a bound |
| 10 | Should the default move tonight? | **Not on this evidence, and not yet — but not because the kernel is wrong.** See §7 |

**Nulls, plants and the poisoning check all pass on all three subjects**: the
byte-identical re-render, 5/5 distinct hashes, and a metric plant that moves
±0.32–0.40 dex in both directions.

---

## 2. Method, and the one fact that makes it work

Five arms, **one solve per subject**, sidecars differing in exactly one line of
text. The warps are identical across arms *by construction*, so nothing but the
interpolation kernel differs.

The load-bearing detail, verified in source and empirically before the
pre-registration was written:

- `merge_cmd.rs::alignment_for` (the `STREHL_WARPMAP` path) validates **stack
  identity and frame count only**. It does **not** check the resampler, it never
  caches back, and it prints `alignment : ON (sidecar-override)`.
- `align_cmd.rs::load_or_solve` (the **cache** path) **does** check it —
  `map.resampler() != want_resampler` → *"re-solving"* — and `solve_config_key`
  hashes the resampler (the fact-1561 fix).

**So a hand-edited sidecar is honoured only via `STREHL_WARPMAP`. Any arm run
without that variable silently reverts to catmull-rom.** My brief proposed
"copy the sidecar, edit one line, re-merge" without naming the variable; done
that way the whole experiment would have been five renders of the default. Every
arm therefore asserts on the binary's own printed `resampler :` line, and the
analysis hard-errors if it does not match the arm.

Subjects, all at full length, `--gate 4`, reference = middle frame:
`bee-3-cpl` (299, the replication anchor), `wrapped-text-1` (130, dense ink
edges), `flat-on-ruler-cpl` (79, engraved steel).

---

## 3. Facts

**Y1 (MEASURED).** Lanczos-3 over Catmull-Rom, end-to-end through the shipped
merge, detail decile: **+0.0868 dex** on `bee-3-cpl` (299 frames, reference 149,
gate 4). M113 measured **+0.083 to +0.099** by an independent route on the same
subject. Pre-registered bar B1 was `[+0.060, +0.120]`. **B1 passes.**

**Y2 (MEASURED).** The same quantity across three subjects of very different
character: **+0.0868** (bee), **+0.1125** (text), **+0.0859** (ruler) — a range of
**0.0266 dex**. Per-arm ranges: `nearest` 0.0426, `bilinear` 0.0495, `lanczos2`
0.0025.

**Y3 (MEASURED — the headline).** A closed form computed from the weight
functions in `crates/strehl-core/src/align.rs`, phase-averaged over 512 phases on
the same 128-point FFT grid and the same 0.30–0.48 cyc/px radial band, **using no
pixel from any capture**, predicts:

```
nearest +0.1889   bilinear -0.2181   catmull-rom 0   lanczos2 +0.0047   lanczos3 +0.1082
```

Against 12 measured subject x arm cells: **mean |measured − predicted| = 0.0155
dex**, max 0.0485, against a **mean |predicted effect| of 0.1300 dex**. **The
photographs move the answer by 11.9% of the effect being claimed.** On
`wrapped-text-1` the agreement is 0.0010–0.0043 dex for bilinear, lanczos2 and
lanczos3 — three digits of a "measurement" that could have been computed from the
coefficients with no camera, no capture and no stack.

This extends M113 §11 (which found the same thing for its **synthetic** figure,
within 0.0036 dex) to the **end-to-end** number — the one anyone would actually
cite to justify moving the default.

**Y4 (MEASURED — rule 9).** The flat-decile control **fails for lanczos3 on all
three subjects**: the band gain is *at least as large* on the flattest tiles as
on the most detailed ones.

| subject | detail/flat gradient separation | M1 detail | M2 flat | M3 |
| --- | --- | --- | --- | --- |
| `bee-3-cpl` | **5.26x** | +0.0868 | **+0.0997** | **−0.0129** |
| `wrapped-text-1` | 2.21x | +0.1125 | +0.1127 | −0.0002 |
| `flat-on-ruler-cpl` | 1.63x | +0.0859 | **+0.1021** | −0.0162 |

It fails *most* on `bee-3-cpl`, which has the **strongest** stratum separation
(5.26x) and therefore the most powerful control. This is rule 9 doing exactly the
job it was written for, and it is the direct consequence of Y3: a gain that is
~88% transfer function cannot be concentrated in detail, because a transfer
function does not know where the detail is.

**Y5 (MEASURED).** `nearest`, `bilinear` and `lanczos2` have never been measured
end-to-end before. The bracket, detail decile, worst subject to best:
`nearest` **+0.1874..+0.2300**, `bilinear` **−0.2191..−0.1696**, `lanczos2`
**+0.0027..+0.0052**. **`nearest` tops the band metric on every subject** —
registered in advance as bar B4 precisely so that, when it happened, it would
read as evidence that the metric is aliasing-foolable rather than as evidence
that `nearest` is the best kernel. **B4 passes as predicted.**

**Y6 (MEASURED).** `Resampler::Lanczos2` is accepted by `warpmap.rs`'s
`resampler_from_name` but **rejected by `align_cmd.rs:151-156`**, which maps only
`nearest`/`bilinear`/`catmull-rom`/`lanczos3`. It is therefore unreachable from
any command line and had never been rendered. Reached here by sidecar edit, it
sits **+0.0027 to +0.0052 dex** from the default with **98.30–99.70%** election
agreement — indistinguishable from Catmull-Rom in every instrument here, at
**2.34x–2.86x** the cost. It is dead weight, not a missing option.

**Y7 (MEASURED — ORCH's N4).** The election-agreement stratification, lanczos3,
median split over 117 central-half tiles:

| subject | agreement | gain hi | gain lo | delta | corr | as % of effect | N4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bee-3-cpl` | 91.92% | +0.1080 | +0.0885 | **+0.0195** | **+0.3819** | 19.9% | not reversed |
| `flat-on-ruler-cpl` | 94.42% | +0.1006 | +0.0958 | +0.0049 | +0.0591 | 4.9% | not reversed |
| `wrapped-text-1` | 98.20% | +0.1125 | +0.1154 | **−0.0029** | **−0.2926** | **2.5%** | **REVERSED** |

`bee-3-cpl` replicates M113 closely (M113: +0.0968 / +0.0604, corr +0.30/+0.41).
**N4 does not fire on two of three new-or-anchor subjects, and where it fires the
reversal is 2.5% of the effect while the correlation's sign flips across
subjects.** Read together with Y3 this is not a puzzle: if the gain is ~88%
transfer function, there is almost no variance left for election agreement to
explain, so the sign of that correlation is free to wander.

**Y8 (MEASURED — the low-`n_eff` ringing question).** ORCH §6 named low `n_eff`
"the single weakest point in the GO case", because the anti-ringing argument is a
mean-field one. Two of my three subjects run as **near-pure selectors** with
essentially no phase averaging at all — `wrapped-text-1` at mean `n_eff` **1.17**
and `flat-on-ruler-cpl` at **1.15**, against `bee-3-cpl`'s **53.67**. Excess local
extrema for lanczos3, restricted to the top-1% gradient stratum:

```
wrapped-text-1     n_eff 1.17    1.2513x
flat-on-ruler-cpl  n_eff 1.15    1.1363x
bee-3-cpl          n_eff 53.67   1.1438x
```

**Removing the phase averaging entirely takes the excess from 1.14x to 1.25x.**
It does not approach the retired 9.902x, and it sits inside ORCH §8.3's measured
1.425x ceiling. This is an independent route to §8.2/§8.3 — whole subjects that
are selectors, rather than a stratification inside one averaged subject.

**Y9 (MEASURED — the noise term nobody reported).** Flat-decile spatial sd moves
almost not at all across the five kernels: `bee-3-cpl` 728.6–746.1 DN
(**2.4% span**), `wrapped-text-1` 678.5–707.2, `flat-on-ruler-cpl` 2239.0–2269.4
(**1.4% span**). **So this is not a "sharper but noisier" trade in the plain
sense** — total noise is flat and it is the *band distribution* that moves.
`nearest` is the exception by eye rather than by sd: its excess-extrema ratio
reaches **2.8807x** on text, which is the aliasing, not the variance.

**Y10 (MEASURED, as a BOUND).** Wall clock for the merge, on a shared machine
with three other `strehl` processes live (rule 16, so a bound not a value):
lanczos3 **2.91x** (bee), **3.21x** (text), **3.92x** (ruler) of catmull-rom;
lanczos2 2.34x–2.86x; `nearest` 0.37x–0.68x; `bilinear` 0.56x–0.69x. My
catmull-rom baseline on `bee-3-cpl` is **108.8 s** against M113's **107.683 s** on
the same 299 frames, which is what licenses comparing the two reports at all.

**Y11 (MEASURED — the method).** A hand-edited `resampler` line in a warp sidecar
reaches rendered pixels **only** through `STREHL_WARPMAP`; the cache path detects
the mismatch and re-solves. Five arms from one solve gave **5/5 distinct sha256s
on all three subjects**, and the binary printed the requested kernel in all 15
runs.

**Y12 (ARGUED).** The end-to-end kernel gain is a poor instrument for a *product*
decision, not because it is wrong but because it is **almost content-free**. Any
future kernel A/B in this project should report the closed-form prediction beside
the measurement, and treat the residual — here 11.9% — as the part that is
actually about the corpus.

---

## 4. Nulls, plants, and the poisoning check

Every one of these passed on **all three subjects**.

**B5 null + B7 poisoning, in one construct.** The catmull-rom arm was rendered
**first, cold**. After every other arm had run, its cache was wiped and it was
re-rendered with a byte-identical command line. **Byte-identical output, 3/3
subjects.** That discharges reproducibility *and* the adversarial poisoning check
that fact 1561 demands, because the re-run happened after four differently-
configured solves had passed through.

**B6 P1 — the wiring plant.** A null alone cannot tell "reproducible" from "the
sidecar is ignored", and fact 1548 is this corpus's memorial to a bar that read
`0 px` and so did its broken plant. Five arms produced **5/5 distinct hashes** on
every subject, and the sidecar writer hard-errors if its anchor is not unique or
does not land.

**B6 P2 — the metric plant, both directions.** On the catmull-rom render:
Gaussian blur σ=0.5 px reads **−0.3649 to −0.4000 dex**; an unsharp x1.5 reads
**+0.3236 to +0.3270 dex**. The metric can move, in both directions, on this
wiring. The positive limb is also a live demonstration that **M1 rewards
manufactured power** — the unsharp plant adds no information and reads three
times lanczos3's gain.

**Bars that FAILED or could not be evaluated, reported as such:**

- **B3 fails for lanczos3 on all three subjects** (Y4). That is the pre-registered
  consequence: I declared that if `M2 >= M1` the detail metric is measuring
  something other than detail. I am reporting it rather than quoting M1 alone.
- **B2 is UNEVALUABLE at its registered 0.95 threshold on `wrapped-text-1`**: all
  117 tiles agree above 0.95, so the "disagree" cell is empty and the bar has no
  power (rule 20). I did **not** narrow it (rule 30). I reported it unevaluable
  and added median and 20/80 splits, which always have power, as a declared
  addition — that is what Y7's table is.
- **`flat-on-ruler-cpl`'s rule-9 control is underpowered**: its detail and flat
  deciles differ by only **1.63x** in gradient, because the subject is textured
  everywhere. Its B3 result agrees with the other two but should carry the least
  weight of the three.

---

## 5. The images

`C:\dev\strehl-out\M118\`

```
SHEET-bee-3-cpl-100.png            SHEET-bee-3-cpl-300.png
SHEET-wrapped-text-1-100.png       SHEET-wrapped-text-1-300.png
SHEET-flat-on-ruler-cpl-100.png    SHEET-flat-on-ruler-cpl-300.png
<subject>\<subject>__<resampler>__full.png
<subject>\<subject>__<resampler>__crop{1,2,3}.png        1:1, no resampling
<subject>\<subject>__<resampler>__crop{1,2,3}x3.png      x3 NEAREST magnification
```

Five arms side by side, three sites per subject. **The exposure is pinned** to the
single `--exposure=N` the baseline arm's `--auto-exposure` chose (1.54 / 2.27 /
1.96), so the sheet compares kernels and not exposures. **Crop sites were chosen
on the catmull-rom baseline** — the incumbent — so the site choice cannot flatter
the candidate, and they are applied to every arm to the pixel.

**My by-eye read, as a non-author of both the kernel claim and the CA
correction.** At x3 on `bee-3-cpl`'s compound eye and hairs, and on
`wrapped-text-1`'s ink grain: **lanczos3 is visibly crisper than the default** —
the ommatidia lattice separates, hair edges are tighter — **with no dark rim or
fringe on silhouettes against the pale background**. `lanczos2` is
indistinguishable from the default. `bilinear` is clearly the softest.
`nearest` is the crispest and obviously aliased, with staircasing on the eye's
silhouette and single-pixel colour speckle. **ORCH's N1 does not fire by my eye.**

**But M110's objection reproduces, unprompted and independently.** On the bee's
hairs the magenta/cyan lateral-CA pair is plainly visible in every arm, and
**lanczos3 makes it more conspicuous** by sharpening the fringes themselves.
Catmull-Rom has been buying fringe suppression with blur (fact 1452), and this is
what stopping that looks like. On a subject the owner is already unhappy with,
that is a product risk and not a metric one.

---

## 6. Disciplines

**D1.** **Before quoting a kernel A/B as a measurement, compute what the kernel's
own coefficients predict and report the residual.** Here the residual is 11.9% of
the effect; the rest is a datasheet. A number that a closed form reproduces to
0.001 dex with no image in it is not evidence about a photograph, however many
frames were merged to obtain it.

**D2.** **Pair every kernel gain with a flat-decile control computed on the same
tiles, and choose the strata from a cross-arm mean so no arm under test picks its
own scoring region.** Rule 9 caught this on all three subjects and no prior
end-to-end kernel number in this corpus reports it.

**D3.** **A stratification bar needs a threshold with power — check the
"disagree" cell is non-empty before you trust the verdict.** M113's 0.95
threshold is sound on `bee-3-cpl` (91.92% agreement) and vacuous on
`wrapped-text-1` (98.20%, zero tiles below). Report the effect size beside the
sign: a correlation of −0.2926 that moves the answer by 2.5% is not the same
finding as one that moves it by 20%.

**D4.** **To A/B a resampler at merge time, edit the sidecar and drive it through
`STREHL_WARPMAP`. The cache path re-solves on a resampler mismatch and will
silently give you the default.** Assert on the binary's printed `resampler :`
line per arm; distinct output hashes bound the failure only collectively.

**D5.** **When phase averaging is the mechanism protecting you, find a subject
where it is absent rather than stratifying inside one where it is present.**
`n_eff` 1.15–1.17 subjects exist in this corpus and make the low-`n_eff` ringing
question a whole-subject measurement instead of a sub-population argument.

---

## 7. Recommendation, and the diff

**I do not recommend moving the default tonight, and the reason is not the
kernel.** Three things, in order:

1. **ORCH's G3 is still unmet at HEAD.** `strehl stack --help` has **no
   `--resampler` flag**; the merge's kernel is set entirely by
   `align_cmd.rs::merge_config`'s literal. G3 requires the change be declinable
   before a 2.9x–3.9x cost is imposed. That flag should land first, and it is a
   `merge_cmd.rs`/`align_cmd.rs` change — **M109's files, not mine**.
2. **The metric that would justify it is 88% a datasheet (Y3) and fails rule 9
   (Y4).** The decision should rest on the 1:1 images and on G2's non-author
   judgement, not on "+0.085 dex".
3. **The CA interaction is real and I saw it independently (§5).** ORCH's own
   §4 says a sharper-and-more-fringed render is "a defensible engineering
   decision and an indefensible product one". Nothing I measured changes that;
   I add a second non-author sighting of it.

**What I do recommend now**, and it is cheap and uncontroversial — expose
`lanczos2` so the sidecar is not the only way to reach a shipped enum variant,
and so Y6 is reproducible from a command line. This is in **M109/M97's file**, so
it is handed over as a diff rather than applied:

```diff
--- a/crates/strehl-cli/src/align_cmd.rs
+++ b/crates/strehl-cli/src/align_cmd.rs
@@ fn resampler(&self) -> Result<Resampler> {
         Ok(match self.resampler.as_str() {
             "nearest" => Resampler::Nearest,
             "bilinear" => Resampler::Bilinear,
             "catmull-rom" => Resampler::CatmullRom,
+            // `warpmap.rs::resampler_from_name` already round-trips this name,
+            // so the variant was reachable by hand-editing a sidecar but not
+            // from any command line (M118 Y6). Measured: +0.0027..+0.0052 dex
+            // from Catmull-Rom at 2.34x-2.86x the cost -- exposed for
+            // reproducibility, NOT recommended as a setting.
+            "lanczos2" => Resampler::Lanczos2,
             "lanczos3" => Resampler::Lanczos3,
             other => bail!("unknown resampler {other:?}"),
         })
```

**The default change itself, for when G1–G4 are discharged** — recorded so the
decision is a one-line diff and visibly not mine to make:

```diff
--- a/crates/strehl-cli/src/align_cmd.rs
+++ b/crates/strehl-cli/src/align_cmd.rs
@@ fn merge_config(n: usize) -> (usize, Vec<usize>, Resampler) {
     (
         merge_reference(n),
         DEFAULT_SPANS.to_vec(),
-        Resampler::CatmullRom,
+        Resampler::Lanczos3,
     )
 }
```

Applying it without the `--resampler` flag would impose 2.9x–3.9x with no way to
decline, which is the thing G3 exists to prevent.

---

## 8. What this does NOT claim

- **It does not claim lanczos3 is not better.** It is, by every instrument here
  and by eye. It claims the *size* of the win is mostly predictable from the
  coefficients and is not concentrated where the detail is.
- **It does not discharge ORCH's G2**, which requires the **combined CA +
  Lanczos-3** arm. I rendered no CA arm. My §5 read is of the kernel alone.
- **It does not measure solving with a different kernel.** All arms share one
  solve; `align --resampler R` also changes the warps and is a different
  experiment.
- **There is no ground truth for a merged image.** Every metric here is
  reference-free or arm-relative. None is an accuracy measurement, and M1 in
  particular is demonstrated foolable in §4 by a plant that adds no information.
- **It does not claim `nearest` is a good kernel.** It tops the band metric
  because it aliases; that was registered in advance as the reading.
- **It does not price the change properly.** Y10 is a bound taken on a shared
  machine, not a controlled timing (rule 16).
- **M86's `0.98 → 0.29` is not quoted as a sharpness result.** It is about the
  displacement estimator's gain. It was the reason to look, not the answer.
- **`flat-on-ruler-cpl` carries the weakest rule-9 control** of the three
  (1.63x separation) and should not be leaned on alone.
