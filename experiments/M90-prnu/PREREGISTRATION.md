# M90 — pre-registration

**Committed before any measurement arm was run.** The only numbers already in
hand at the time of writing are the two baseline identity hashes in §6, which
were produced by code that pre-dates every library edit this milestone makes.

Sign convention throughout: `err(S) = sigma_model(S) / sigma_truth(S) - 1`.
**Positive is conservative** (the model over-predicts noise); **negative is
over-confident**.

## 1. The four arms

| arm | gain | PRNU |
| --- | --- | --- |
| `S` shipped | `iso/436.8` (`profile.rs`) | none |
| `G` gain-only | `iso/446.223` (M71 §6.1 green, 0.224103 DN/e- at ISO 100) | none |
| `P` prnu-only | `iso/436.8` | kappa = 0.3096% G, 0.3102% R, 0.2528% B (M71 §8.1) |
| `B` both | `iso/446.223` | as `P` |

## 2. Registered bars

**PR-1 — identity (hard gate).** After the library change, the default path must
be **byte-identical**: SHA-256 of both baseline blobs in §6 unchanged. If this
fails, no other number in this milestone is reportable.

**PR-2 — placebo, model level.** An arm with the opt-in switched **on** but
`kappa = 0` and gain factor `1.0` must reproduce arm `S` byte-for-byte. If the
opt-in machinery perturbs the model by itself, every downstream number is void.

**PR-3 — placebo, pipeline level.** The same null correction run through the
full two-pass merge on a real stack must flip **zero** admission decisions and
leave `n_eff` bit-identical at every pixel. Any non-zero count voids the
blast-radius section.

**PR-4 — independent truth (non-circularity).** Arm `B` is truth *by
construction* against M71's constants, so its residual is identically zero and
that is not evidence. I will therefore measure `g` and `kappa` **myself**, from
the 360 flat fields, in Rust through `strehl-raw` (M71 used Python/rawpy), with
a within-half temporal PTC for `g` and a split-half two-green covariance for
`kappa`.

* Bar PR-4a: my green gain agrees with M71's 0.224103 DN/e- to within **+/-3%**.
* Bar PR-4b: my kappa agrees with M71's 0.3096% to within **+/-20% relative**.
* Falsifier: **if my kappa < 0.15%** (half of M71's), the correction is
  materially smaller than the corpus believes and the case for flipping the
  default weakens accordingly. I report my number, not M71's (AGENTS rule 7).
* If either bar misses, the residual curves are drawn against **my** truth and
  the disagreement is reported as the headline.

**PR-5 — the crossover.** Fact 1064 puts the shipped model's zero-crossing at
**S = 504 DN per photosite**.

* Bar PR-5a: my computed photosite crossover lands within **+/-25%** of 504 DN
  (i.e. 378-630 DN).
* Bar PR-5b — a **new** claim, registered against the corpus: M71 §8.3 reports
  the green-luma crossover at **1009 DN**, i.e. twice the photosite value. But
  `plane.rs::green_luma_with_clip` emits `L = (G1 + G2) / 2` — the **mean**, not
  the sum — and `NoiseModel::green_luma_sigma` evaluates both planes at that same
  `L`. I predict the crossover **in the units the code actually calls
  `green_luma_sigma` with is 504 DN, not 1009 DN.** If the measured luma-domain
  crossover lands within +/-5% of 1009 DN, my reading of the code is wrong and I
  retract this claim in the report.

**PR-6 — which arm is best, across the range.** Registered predictions:

* PR-6a: arm `G` (gain-only) is **worse** than arm `S` — more over-confident —
  over some part of `S in [0, 15360]`.
* PR-6b: arm `P` (PRNU-only) is conservative (`err >= 0`) **everywhere** in that
  range.
* Falsifier: if `G` beats `S` everywhere, or `P` goes over-confident anywhere,
  fact 1064's "two errors cancel" account is wrong in a way that matters and I
  report that as the headline instead.

**PR-7 — blast-radius materiality.** The correction is **material** for a
downstream quantity if flipping the default moves it by more than **5% relative**
on at least one real stack. Quantities, all at `DEFAULT_GATE = 4.0`:

1. mean `n_eff`
2. admitted-frame fraction `mean_n_eff / N`
3. singleton exposure (fraction of pixels with `n_eff == 1`)
4. `mean_predicted_sigma_gain`
5. fraction of *(pixel, frame)* admission decisions that flip
6. fraction of pixels whose elected winner index changes
7. median `disagreement`

**Milestone-level falsifier: if every one of these moves less than 5% on every
stack tested, the correction is immaterial to the merge as shipped**, the
recommendation is "do not flip the default; fix the documentation instead", and
that is a complete result which I will report as such.

**PR-8 — signal resolution.** The error is signal-dependent, so a whole-image
mean understates it. Every PR-7 quantity is additionally reported binned by
merged green luma in octaves: `[0,125) [125,250) [250,500) [500,1000)
[1000,2000) [2000,4000) [4000,8000) [8000,inf)` DN.

* Bar PR-8a: the brightest populated bin must show a **larger relative move**
  than the whole-image mean. If it does not, either the plumbing is wrong or the
  effect is not signal-dependent, and I must establish which before reporting
  anything else.

**PR-9 — planted defect.** A wrong `kappa` (10x) planted into the corrected
model must make the harness's own consistency check fail with a non-zero exit.
Restore from a **temp file copy**, never `git checkout`; then set
`LastWriteTime` to now (AGENTS rule 33) and confirm green.

**PR-10 — double counting against M70/M76b.** Fact 1102 says kappa explains
**25.12%** of M70's unruled flat-residual floor error. I will call this double
counting **only** if I can point at a **shipped code path** that already carries
a level-dependent multiplicative variance term. If no such path exists, the
correct answer is that the 25.12% overlap is between two *analyses* and not
between two *model terms*, and adding kappa double-counts nothing.

**PR-11 — the fixed-pattern-versus-temporal split.** Registered decision rule,
written before looking: kappa belongs in a consumer's sigma **iff** that sigma is
meant to predict the spread of the quantity the consumer actually forms. For each
of the consumers M71 named — `focus.rs::normalise_by_luma_sigma`,
`Estimator::disagreement`, `Estimator::predicted_sigma` — I must be able to name
the estimator whose variance its sigma is supposed to be. If I cannot name it, I
have not answered the question and must say so rather than rule.

## 3. What would make me recommend NOT flipping the default

Any one of: PR-1 fails; PR-4b's falsifier fires; every PR-7 quantity moves less
than 5%; or the correction moves a *published, load-bearing* constant
(`FOCUS_NOISE_SD`, `DEFAULT_GATE`) in a way that cannot be re-derived in this
milestone.

## 4. What I will not do

* I will not re-run M71's estimator. A re-computation of the author's formula on
  the author's inputs confirms every choice they made (AGENTS rule 24).
* I will not measure `rho_warp` (M71 §11's named blocking measurement) unless the
  blast radius turns out to depend on it, and if it does I will say so rather
  than assume a value.
* I will not touch `merge.rs`, `focus.rs` or any file owned by a sibling
  milestone. If the correction cannot be delivered without one, that is a blocked
  dependency and I report it as one.

## 5. Arms that must show no effect (placebos)

* PR-2 and PR-3 above.
* A **zero-signal** arm: at `S = 0` every arm must agree exactly, because both
  corrections are proportional to signal. Any spread at `S = 0` is an
  instrumentation bug.

## 6. Baseline identity hashes (produced before any library edit)

Revision at capture: `206c80b55750780136e4cedd7d37eeef2d0905c5`.
Command:

```powershell
cargo run --release -p strehl-cli --example m90-prnu `
  --target-dir experiments/M90-prnu/target-m90 -- `
  identity --stack D:\personal\macro\109MSDCF
```

| blob | bytes | SHA-256 | fnv1a64 |
| --- | --- | --- | --- |
| `identity.bin` (model tables + synthetic merge) | 8545833 | `09E274381BFC8A1D5F966AA67D7F2B5139B27203A2C1043C19B99D77BF399EEA` | `36821ece6e6fbe0c` |
| `identity-real.bin` (109MSDCF, 22 frames, full plane) | 148347139 | `36C0470838497925889023B86116DCF2C81B3A37E1F8E51381AA2012E02C1FDE` | `f3477529886859b6` |

Reference values printed at capture: `109MSDCF` mean `n_eff` = **4.986550**,
`mean_predicted_sigma_gain` = **0.491569**, 22 frames, gate 4.0.
