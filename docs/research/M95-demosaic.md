# M95 arm 6 — the demosaic ladder measures loudness, not detail

**Milestone:** M95 (dispatched as M93; renumbered by the orchestrator, see
`M95-coverage.md` §8).
**Files owned and touched:** `crates/strehl-cli/examples/m95-demosaic.rs` (new),
`experiments/M95-demosaic/`, this report.
**Shipped code changed:** none. `image_out.rs`, `color.rs` and `demosaic.rs` are
untouched by this arm.

Pre-registration: `experiments/M95-demosaic/PRE-REGISTRATION.md`, written and on
disk before any arm-6 number existed.
Every number below is printed by `experiments/M95-demosaic/src/d9_summary.py`
from the JSON the runs wrote, and is reproduced in
`experiments/M95-demosaic/out/d9_summary.txt`.

---

## 1. Headline

The orchestrator ranked six LibRaw demosaics by top-octave power, found a spread
of **0.3518 dex**, and inferred that moving strehl from Malvar-He-Cutler to an
RCD/AAHD-class demosaic is *worth up to ~0.15 dex* of sharpness.

**Ranking demosaics by top-octave power does not rank them by quality.** Given a
known answer to compare against, a deliberately terrible demosaic — replicate
each CFA sample across its quad — reads **+0.5737 dex louder than MHC** while
carrying **0.3394 dex less real detail**, and **91.6%** of what it emits is not
in the scene at all.

That +0.5737 dex is **larger than the entire 0.3518 dex spread** the inference
was drawn from. A metric that puts the worst arm on the ladder a full ladder-span
above the shipped one cannot be read as a quality ordering.

The second finding cuts the same way and is about the shipped code:

**MHC matches the truth's total band power to +0.0047 dex.** On the
orchestrator's metric it would score as essentially ideal — a 1.1% match. Under a
decomposition that knows the right answer, **31.3% of that power is fabricated**
and MHC carries **0.1586 dex less true detail** than a perfect demosaic would.

So there *is* headroom in the demosaic, bar B2 fired, and it is roughly the size
the orchestrator guessed. But it was not visible in their measurement, and their
measurement would have been equally happy with an arm that is far worse.

---

## 2. The instrument, and why it can say something the power ladder cannot

A demosaic is an interpolator. The orchestrator already proved, on the binning
question, that an interpolator can *inject* top-octave energy rather than recover
it: `np.kron` block replication produced more power near Nyquist than the
full-resolution frame it was built from, which is why three successive "binned"
anchors crossed instead of bracketing. Zipper, maze and false-colour artifacts
are top-octave energy that is not in the scene.

Top-octave power sums the two. It cannot separate them, and nothing about the
six-algorithm ladder makes it able to.

Give the demosaic a problem whose answer is known and it separates exactly. For
band-limited `D` and truth `T`:

```
alpha(f) = sum_t D_t(f) conj(T_t(f)) / sum_t |T_t(f)|^2
P_sig(f) = |alpha(f)|^2 P_T(f)
P_eps(f) = P_D(f) - P_sig(f)          >= 0, the least-squares residual
```

`alpha` is estimated **per frequency bin, pooled over 400 tiles**, so a demosaic
is allowed to be any linear shift-invariant filter without being charged for it.
What it is charged for is what no such filter can produce: aliasing folds energy
in from *other* frequencies, and no `alpha` can absorb that, so it lands in
`P_eps`. That is the entire design and it is why the decomposition is meaningful
for a *linear* demosaic like MHC, whose whole error budget is aliasing.

**Ground truth** is a 2× box-downsample of a full-resolution LibRaw decode of
`DSC00150.ARW` — frame 149, the merge's own reference frame, the same file the
orchestrator measured. Demosaic error lives at the top octave of the decode grid
and averaging over a 2×2 quad attenuates it. `T` is 2344 × 3514, full-colour at
every pixel, camera-native (`output_color=raw`) so that no colour matrix smears
chroma artifacts across channels before they are measured.

`T` still carries some of its own decoder. **K5 is the control that decides
whether that matters**, and it is reported below rather than assumed away.

---

## 3. The ladder

400 tiles of 64 × 64, ranked by the **truth's** in-band energy so no arm can
select its own favourable ground, band 0.30–0.48 cyc/px, luma.

| arm | power | signal | artifact | artifact share |
| --- | ---: | ---: | ---: | ---: |
| **MHC** — what strehl ships | **+0.0047** | **−0.1586** | −0.4993 | **0.3134** |
| BILINEAR — quiet failure | −0.4802 | −0.6950 | −0.8890 | 0.3901 |
| NEAREST — loud failure | **+0.5784** | −0.4980 | +0.5403 | **0.9161** |

Read the first and last rows together. **NEAREST is the loudest arm and the
second-worst arm.** BILINEAR is honest about being soft; NEAREST is not, and a
power metric prefers it.

Per channel, MHC:

| channel | power | signal | artifact | artifact share |
| --- | ---: | ---: | ---: | ---: |
| luma | +0.0047 | −0.1586 | −0.4993 | 0.3134 |
| R | −0.0407 | −0.4881 | −0.2325 | 0.6430 |
| G | −0.0498 | −0.2127 | −0.5547 | 0.3127 |
| B | −0.0322 | −0.3874 | −0.2851 | 0.5586 |

Red and blue are sampled at a quarter of the photosites and it shows: their
artifact share is roughly double green's. **Nearly two thirds of MHC's red-channel
top-octave power is not in the scene.** If a demosaic upgrade is ever done, this
is where the prize is, and it is chroma rather than luma.

---

## 4. What the eye says

`C:\dev\strehl-out\M95-demosaic\M95-demosaic-ladder.png` — four panels, identical
crop, identical exposure and transfer curve, 100%, no panel resampled. The mosaic
fed to all three demosaics is `T` sampled RGGB, so the leftmost panel is the
exact answer.

The eye agrees with the decomposition and disagrees with the power metric.
NEAREST is obviously the worst of the four — coloured fringing along every hair,
a blocky aliased texture across the whole subject — and it is the arm the power
metric ranks highest. MHC is close to truth; BILINEAR is visibly softer than both.

No sharpness number is printed on any panel. The numbers in this report were
pooled over 400 tiles and were not measured on that crop; labelling the crop with
them would attribute a measurement to an axis it was not made on.

This check is not decoration. M87 shipped a halo correction tonight whose own
metric reported +72.9% while erasing the bee's abdomen hairs. A metric that
outranks the eye has to earn it.

---

## 5. Bars, and how they fared

Both pre-registered before any result existed.

**B1 — is top-octave power monotone in demosaic quality?**
Registered: *fires if NEAREST reads higher power than MHC while reading lower
signal.*
**FIRED.** Louder by +0.5737 dex, less detail by −0.3394 dex.

**B2 — how much detail is the shipped MHC losing?**
Registered: *> 0.10 dex → real headroom; < 0.03 dex → negligible; between →
report the number and make no recommendation.*
**FIRED on the headroom side: +0.1586 dex.**

**B3 — weak consistency check, explicitly not a decision bar.**
Arm 4/5 measured strehl MHC against rawpy AHD on the *real* render at
−0.0332 dex. Arm 6's MHC signal deficit is 0.1586 dex against a *perfect*
demosaic. These are different quantities — one is a difference between two real
demosaics, the other a distance to an unreachable ceiling — and the second being
larger than the first is what you would expect, not a contradiction. I am not
claiming they corroborate each other.

---

## 6. Controls, including the ones that failed

| id | kind | result |
| --- | --- | --- |
| K1 | NULL, `D = T` | power 0.000e+00, signal 2.261e−09, alpha 1.0000000018, artifact share 0.000e+00 — **PASS, after F6** |
| K2 | determinism | MHC twice, bitwise identical — PASS |
| K3 | POSITIVE, blur dose | signal −0.1586 / −0.5430 / −2.0437 / −3.9387 at σ = 0 / 0.5 / 1 / 2 px, monotone — PASS |
| K4 | POSITIVE, artifact dose | artifact −0.4993 / −0.0435 / +0.4270 / +0.9890, monotone; signal flat within 0.02 dex — PASS |
| K5 | SPECIFICITY, truth source | ranking `MHC > NEAREST > BILINEAR` identical under AHD, VNG and LINEAR truths; MHC signal moves at most +0.0198 dex — PASS |
| K6 | CERTIFICATION vs Rust | worst disagreement 3.576e−07 over 8 cases, tolerance 1e−06 — PASS |
| K7 | band vs Nyquist | 0.30–0.48 cyc/px strictly below 0.5 — PASS |

**K4 is the control the whole arm rests on.** It is the one that shows the
instrument can say *this power is not scene detail*: adding in-band power that is
uncorrelated with the scene drives `artifact` from −0.4993 to +0.9890 while
`signal` moves 0.0166 dex. Without it, B1 is an assertion.

**K6 is what makes a Python measurement admissible evidence about Rust.** It is
itself certified: a deliberately planted one-tap defect in the ported `F_G`
stencil moves the output by 1.249e−01, four orders above the 1e−06 tolerance and
five above the observed 3.576e−07 agreement. Discipline 594 — the instrument is
shown saying otherwise.

### Failures

**F6 — K1 failed on the first run and the threshold I relaxed was my own.**
The run aborted with `CONTROLS FAILED: ['K1']` while printing `power
+0.00000000  signal +0.00000000  alpha 1.00000000  artifact_share 0.000e+00`.
The cause: the *code* demanded `|signal| < 1e-9`; the measured value is
2.261e−09, float64 round-off in `num/den` accumulated over 917 bins × 400 tiles.

I loosened a threshold after seeing a result, which is the exact move
pre-registration exists to prevent, and it should be judged as such. My defence
is on the record and a reader may reject it: the pre-registered text says
*"`alpha = 1`, `artifact` at float epsilon, `power = 0.0000`"* and contains **no
numeric bar on `signal`** — the 1e−9 was an implementation detail I invented
while coding, stricter than what I registered. Measured against the registered
text, K1 passed on the first run: alpha 1.0000000018, artifact exactly zero,
power exactly zero. The new tolerance is 1e−06, still **five orders of magnitude
below the smallest effect this arm reports** (0.0198 dex). The measured value is
printed in the run output so anyone can apply a stricter bar.

**F7 — my scope hypothesis about the real capture was refuted, and it ran the
opposite way.** Arm 6 mosaics a 2×-downsampled truth, so the band it tests —
0.30–0.48 cyc/px of the truth grid — is 0.15–0.24 cyc/px of the sensor grid. I
expected that to mean the synthetic ladder **overstates** real aliasing, because
the real demosaic's aliasing lives at a physically higher frequency where
diffraction has attenuated the scene further. `d3_scale.py` measured it:

```
real sensor grid   alias/tested per-bin power ratio : 0.15447   (-0.8111 dex)
synthetic truth    alias/tested per-bin power ratio : 0.04813   (-1.3176 dex)
synthetic ladder drives the demosaic 0.31x as hard as the real capture
```

**0.31×, not > 1.** The real sensor grid carries 3.2× *more* relative in-band
content than my synthetic truth does, so the ladder if anything **understates**
the drive the real capture presents. The escape hatch I went looking for is not
there. Caveat, stated because it cuts against my own conclusion: the real-grid
figure is measured on an AHD decode and therefore includes AHD's own top-octave
artifacts, which inflates it by an unknown amount.

---

## 7. What this means for the decision in front of you

1. **The six-algorithm ladder cannot support "an RCD/AAHD-class demosaic is worth
   up to ~0.15 dex".** It ranks by a quantity that a bad demosaic maximises. The
   conclusion may still be true — B2 says the headroom exists — but that evidence
   does not establish it.
2. **A demosaic upgrade has real headroom: 0.1586 dex to a *perfect* demosaic.**
   That is a ceiling, not a forecast. No implementable demosaic reaches it, so
   the achievable gain is some fraction of 0.1586 dex and this arm cannot say
   which fraction without implementing a candidate and scoring it on the same
   ground truth — which is now a two-line change to `d2_ladder.py`.
3. **If it is done, the prize is chroma.** Red and blue carry 0.6430 and 0.5586
   artifact share against green's 0.3127.
4. **Scoring a candidate is now cheap and does not require reading GPL code.**
   `d2_ladder.py` scores any function `mosaic -> RGB` against a known answer with
   seven controls already in place. RCD's algorithm is publishable and
   re-implementable from the literature; the licence boundary in `AGENTS.md` is
   untouched by anything in this arm — no GPL demosaic implementation was opened
   and none is needed to score one.
5. **The demosaic is not the softness the owner is complaining about.** 0.1586 dex
   is a ceiling on the *whole* demosaic error, against a perfect demosaic, in the
   top octave only. Arm 4's warp gather costs comparable amounts and is already
   measured. Fixing the demosaic would not on its own change a render from soft
   to sharp.

---

## 8. The two items carried in from your previous messages

**The coverage rescale fix is measured dead and the measurement is committed**
(`1024ddc`, report `docs/research/M95-coverage.md`, facts P57–P65). Emitting the
cropped region at native sampling recovers **−0.0042 dex** — marginally negative.
NOW +0.1813 (sem 0.0031) → FIX +0.1855 (sem 0.0017), n = 960 per arm, priced
against the real 299-frame sidecar. The pre-registered DEAD bar fired. The
mechanism is `SNAP = −0.0003 dex`: with integer offsets and unit scale one
Catmull-Rom gather is free, so the whole cost is sub-pixel phase, and the
per-frame warp supplies the same phase the coverage scale did. Your bar was
"MERGE moves +0.3693 → within noise of +0.1301"; it does not move.

**Your `--srgb` implies `--demosaic` proposal is already shipped, by me, in
commit `56bd846`.** `main.rs:405` and `main.rs:436` both read:

```rust
demosaic: demosaic || (srgb && !binned),
```

`--binned` is the opt-out, exactly the polarity you proposed. The byte-frozen
measurement path passes neither flag so it is untouched. No patch is needed and
`main.rs` does not need to be opened. The docstring at `main.rs:85-89` documents
it. This also resolves the "8.2 MP" question for the last time: that figure was
the literal dimensions of the pre-`56bd846` `--srgb` file, it was correct about
that file, and that file no longer exists as a default.

---

## 9. Scope — what this does not cover, and what would falsify it

- **It is a synthetic round trip on one frame's scene content.** It does not
  measure the real merge output. It measures what a demosaic does to a known
  image, which is the only way to separate detail from artifact at all.
- **`T` is not a perfect truth.** It is a downsampled decode and carries some of
  its decoder. K5 shows the *ranking* is invariant across three decoders and MHC's
  signal moves at most 0.0198 dex, which bounds the contamination but does not
  remove it. A film scan or a three-shot colour-separation capture would remove
  it, and this project has neither.
- **The band is the top octave.** Everything below 0.30 cyc/px is not measured
  and MHC is close to exact there.
- **No unimplemented demosaic is scored.** This arm cannot say what AAHD, DHT,
  RCD or DDFAPD would score. It can only say that the evidence offered for them
  does not distinguish them from an arm that is worse.
- **The luma numbers are a BT.709 combination of camera-native channels**, not of
  colorimetric ones, because no colour matrix is applied before measurement.

**Falsifiers.** The conclusion breaks if: NEAREST could be shown to read lower
power than MHC on a different scene (B1 is a single-scene result); or K5's
invariance fails on other content, meaning the ranking is a property of the
decoder rather than of the demosaic; or the α-per-bin model is too generous, in
which case MHC's 0.1586 dex deficit is an *under*estimate and the headroom is
larger, not smaller.

**A capture that would settle it**, for `docs/captures-needed.md`, which is
yours: three exposures of one static high-detail subject through R, G and B
filters at the same focus, giving a genuine full-colour ground truth with no CFA
in its history. That removes the only assumption in this arm.

---

## Candidate facts

**P66.** Ranking demosaic algorithms by top-octave power does not rank them by
quality. Against a known answer, a nearest-neighbour demosaic reads **+0.5737 dex
louder** than Malvar-He-Cutler while carrying **0.3394 dex less** detail
correlated with the truth, with **91.6%** of its emitted band power not present
in the scene.
*Significance:* retires the evidence offered for a demosaic upgrade; the
overshoot is larger than the whole 0.3518 dex six-algorithm spread the inference
came from.
*Label:* MEASURED.

**P67.** strehl's shipped Malvar-He-Cutler demosaic matches the truth's total
top-octave power to **+0.0047 dex** — indistinguishable from ideal on a power
metric — while **31.3%** of that power is not in the scene and it carries
**0.1586 dex** less true detail than a perfect demosaic.
*Significance:* prices the demosaic upgrade as a ceiling rather than a forecast,
and shows a power metric would have called the shipped demosaic perfect.
*Label:* MEASURED.

**P68.** MHC's error is chromatic. Artifact share is **0.6430** in red and
**0.5586** in blue against **0.3127** in green, tracking the quarter-density CFA
sampling of R and B.
*Significance:* directs any future demosaic work at chroma reconstruction rather
than luma sharpening.
*Label:* MEASURED.

**P69.** Band power emitted by a demosaic splits exactly into detail and artifact
by estimating a per-frequency-bin complex gain against a known truth pooled over
tiles: `P_eps = P_D − |alpha|^2 P_T`. Aliasing folds energy from other
frequencies and no gain can absorb it, so it lands in the residual.
*Significance:* a reusable instrument for any interpolation stage in this
pipeline, and the only one in the corpus that can distinguish recovered detail
from injected artifact.
*Label:* DERIVED.

**P70.** A Python port of `strehl_core::demosaic` agrees with the shipped Rust to
**3.576e−07** worst-case over 8 cases including odd extents and pure
checkerboard, while a planted one-tap stencil defect moves the output by
**1.249e−01**.
*Significance:* establishes that an external instrument may be read as evidence
about the shipped demosaic, and shows the comparison is live rather than vacuous.
*Label:* MEASURED.

**P71.** The `bee-3-cpl` capture drives the demosaic *harder* than a
2×-downsampled truth does, not more gently. Alias-band to tested-band per-bin
power ratio is **0.15447** on the real sensor grid against **0.04813** on the
synthetic truth — the synthetic ladder runs at **0.31×** the real drive.
*Significance:* refutes the diffraction escape hatch for demosaic aliasing on
this capture; the synthetic estimate is a lower bound, not an upper one. Confound
on the record: the real-grid figure is measured on an AHD decode and includes
that decoder's own artifacts.
*Label:* MEASURED.

**P72.** `--srgb` has implied full-resolution demosaic since commit `56bd846`;
`main.rs:405` and `main.rs:436` read `demosaic || (srgb && !binned)` and
`--binned` is the opt-out. The byte-frozen measurement path passes neither flag.
*Significance:* the "make `--srgb` imply `--demosaic`" proposal is already
shipped and needs no change to `main.rs`.
*Label:* MEASURED.

**P73.** A pre-registration binds only what it actually says. Arm 6's K1 null
aborted the first run against a `|signal| < 1e-9` bar that existed in the code and
not in the registered text, on a value of 2.261e−09 that is float64 round-off over
917 bins × 400 tiles.
*Significance:* a threshold invented at coding time is not a pre-registered bar,
and the honest repair is to say which of the two was relaxed rather than to
quietly widen it.
*Label:* ARGUED.
