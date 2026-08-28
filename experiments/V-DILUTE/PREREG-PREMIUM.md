# PRE-REGISTRATION — candidate-set control against the selection premium

**Lane:** V-DILUTE. **Written before any arm was run.** Commit this file before
the harness produces a number, or the predictions below are worthless.

Baseline inherited, not re-invented: V-NEVERWORSE's `vn_ninv.py` gauge, facts
1843–1845 at `f1f40150`. Premium is defined there as

```
premium(arm, N) = band_power(arm on synthetic twin) / band_power(mean on same twin)
```

at 0.30–0.35 cyc/px, on a twin carrying identical scene content, independent
noise at the fitted sensor variance, and **no focus signal at all**. Target to
beat: **240.70x at N=79 on `112MSDCF`**.

---

## 0. Two things measured before predicting, which change the reading

**(a) `112MSDCF`'s band boundary is 0.25 cyc/px** (`vd_band.py`), consistent
with its siblings `113MSDCF` and `119MSDCF` at 0.25. It is not in V-LINEAR's
five, so this had to be measured. **The 0.30–0.35 band the premium is scored in
is above that boundary.**

**(b) The band is not merely faint, it is empty.** `vd_signal.py`, commissioned
in both directions (null 0.037; planted 0.22 cyc/px tone recovered at S/y=4074
at its own band and 0.0 in every other), estimates true scene power in units of
the post-averaging noise floor as `S/y = (2·rm−1)/(1−rm)`:

| band | 0.10 | 0.13 | 0.17 | 0.20 | 0.25 | **0.30** | 0.35 | 0.40 |
|---|---|---|---|---|---|---|---|---|
| S/y | 12.38 | 7.21 | 3.87 | **2.43** | 0.95 | **0.00** | 0.00 | 0.00 |

**Consequence, stated so it cannot be read as an attack on the premium number:**
the premium is *supposed* to be measured where the twin has no signal, so
scoring manufactured noise in an empty band is correct and the **240.70x stands
unaffected**. But an *acuity* statistic at 0.30–0.35 on this subject has nothing
to be sharp about. **Therefore: premium is scored at 0.30–0.35 (inherited);
sharpness is scored at 0.20–0.25 (qualified SIGNAL, S/y=2.43).** Reporting both
in one band would satisfy ORCH's criterion 2 in a band that fails his criterion 4.

Caveat carried honestly: `S/y` above is measured on the **mean**, which is
blurred by defocused frames, so it could understate scene content that only
selection recovers. The harness therefore also runs the **same selecting
operator on real and on twin** — the twin has zero signal by construction, so
any excess of real over twin is recovered scene. That test, not the table
above, is what licenses the final claim.

---

## 1. The mechanism I am predicting, stated so it can be killed

The premium is a **winner's curse**, not a candidate-count effect. In
`vn_pyr.merge` the score is `sq_i = smooth5(lap_i²)` and the value copied is
`lap_i` — **the score contains the very coefficient it selects.** `smooth5` is
separable `[1,4,6,4,1]/16`, so the centre tap carries `(6/16)² = 0.1406` of the
score's weight on the copied sample itself.

Selection therefore prefers whichever frame's *noise* happened to inflate its
own score, and then copies that noise. Formally, for a score with correlation
`ρ` to the copied noise, the amplification is roughly `1 + ρ²·2·ln N`.

**Two consequences that separate my account from a candidate-count account:**

1. **The floor for any single-frame-output arm is `premium = N`, not 1.** Output
   one frame ⇒ noise power `σ²`; the mean ⇒ `σ²/N`. So at N=79 the floor is
   **79**, and the measured 240.70 means the curse contributes only
   `240.70/79 = 3.05x`. **Decorrelation alone can therefore win at most 3.05x.**
   Anyone promising more from decorrelation alone is wrong.
2. **To beat 79 an arm must average several frames.** So the winning design must
   be *decorrelated selection of a set*, then **averaging within that set** —
   which does not blur, because the frames averaged are the ones in focus.

Predicted structure: `premium ≈ curse × N / n_eff`.

**The decisive control** is `oracle-decorr`: score frame `i` from an
*independent* noise realisation of the same scene. Candidate count is unchanged
at N; only `ρ` goes to 0. If the premium collapses to ≈79, correlation is the
mechanism. **If it stays near 240, my account is dead and ORCH's candidate-count
account survives.** I want that stated plainly in advance.

---

## 2. Predicted premium at N=79 on `112MSDCF` (baseline 240.70)

| arm | mechanism | **predicted** | interval | commits me to |
|---|---|---|---|---|
| `mean` | none | 1.00 | definitional | gauge sanity |
| `argmax` | full curse | **240.70** | ±5% | **I reproduced the inherited gauge** |
| `random` | select independent of noise | **79** | 60–105 | the floor is N |
| `oracle-decorr` | ρ→0, N held | **79** | 60–105 | **correlation is the mechanism** |
| `loo-frame` | score from frames i±1 | **85** | 60–130 | exact decorrelation works |
| `punctured` | centre tap removed | **170** | 110–235 | spatial puncture is partial |
| `pool-s` (σ=2) | ORCH lever 2 | **150** | 90–230 | pooling helps, partially |
| `capK` (K=8) | ORCH lever 1 | **156** | 100–210 | **capping is WEAK** |
| `peakfit` | ORCH lever 4 | **90** | 55–150 | pooling over i works |
| **`window-avg` (±4)** | decorrelated peak + average in-window | **9** | **4–22** | **the headline** |

## 3. Predicted sharpness, at 0.20–0.25 cyc/px, noise-corrected, real stack

Relative to `shipping` = 1.000. Criterion 2: an arm that wins premium by losing
sharpness is refused.

| arm | predicted sharpness | refuse if |
|---|---|---|
| `mean` | **0.55** | — (it is the useless bracket) |
| `argmax` | 1.02 | — |
| `capK` (K=8) | 1.00 | — |
| `loo-frame` | 0.99 | < 0.95 |
| **`window-avg` (±4)** | **0.98** | **< 0.95** |

## 4. N-scaling

Run N = 19 / 39 / 79 (matched range, endpoints pinned, `vn_ninv.pick`).
Predicted: `argmax` grows ≈ 23 → 81 → 241; **`window-avg` stays within a factor
of 2 across the whole range**, because `n_eff` grows with N at fixed focus
range. Refuse the design if `window-avg` grows more than 3x from N=19 to N=79.

## 5. Kill conditions, pre-committed

1. `oracle-decorr` ≳ 200 ⇒ **my winner's-curse account is refuted**; report it.
2. `random` far from 79 ⇒ my "floor = N" arithmetic is wrong; every downstream
   number is then suspect and must be re-derived before anything is claimed.
3. `window-avg` premium < 22 but sharpness < 0.95 ⇒ **refused under criterion 2**,
   reported as a failure, not re-tuned into a pass.
4. `capK` landing below 100 ⇒ candidate capping is stronger than I predicted and
   ORCH's lever 1 deserves the credit; say so.
5. Intervals are **not** widened after the fact. A miss is reported as a miss.

## 6. What this cannot settle

Offline in NumPy on a 900×900 crop of one subject. It cannot price runtime cost,
cannot see CFA/quad-plane effects the Rust path has, and one subject cannot
establish corpus behaviour. Treat as a design screen, not an acceptance test.

---

# ROUND 2 PRE-REGISTRATION — written after round 1, before round 2 ran

Round 1 is scored in `V-DILUTE.md`. Three of its results drive round 2:
`oracle` cut the premium **4.10x with N held at 79**, so correlation is the
mechanism; capping did **nothing** (K=4 → 225.32 against shipping 226.39); and
every arm that cut the premium also cut sharpness, so the real deliverable is
the **frontier**, not a single arm.

**The reframe.** A Laplacian level `k` carries roughly `0.5/2^(k+1)` to
`0.5/2^k` cyc/px. So the premium band **0.30–0.35 is LEVEL 0**, while the
sharpness band **0.20–0.25 is mostly LEVEL 1**. `vd_signal.py` already measured
that this subject carries **S/y = 0.00 at 0.30–0.35** and **2.43 at 0.20–0.25**.

That yields a mechanism neither ORCH's brief nor round 1 stated:

> **The merge selects hardest in the band where the scene has nothing to
> select on, and the premium is manufactured there. The candidate-set control
> that costs nothing is to collapse the candidate set to ALL frames in bands
> whose scene content is below the noise, and to keep selecting where it is
> not.**

**I flag the obvious objection against myself:** an arm that averages level 0
attacks precisely the band the premium is scored in, which could be metric
gaming. The defence must be independent, and it is only valid if BOTH hold:
(a) `vd_signal` shows the band empty of scene content, measured before these
arms existed; and (b) sharpness is reported in **several** bands, not only
0.20–0.25, so a loss pushed into a neighbouring band cannot hide. Round 2
reports 0.10–0.15, 0.17–0.20, 0.20–0.25 and 0.25–0.30 for every arm. If
`lvl0mean` loses more than 5% in ANY of those, the "costs nothing" claim dies.

**This design is necessarily subject-adaptive and I predict it in advance:** on
`bee-1-cpl`, whose boundary V-LINEAR measured at **0.48**, level 0 carries real
signal and averaging it must be destructive. A fixed "average level 0" rule is
therefore wrong corpus-wide even if it wins here.

### Predicted premium / sharpness(0.20–0.25) at N=79

| arm | mechanism | premium | sharp | refuse if |
|---|---|---|---|---|
| `pool1` | spatial pool σ=1 | 110 | 0.90 | — |
| `pool4` | spatial pool σ=4 | 45 | 0.60 | — |
| `pool8` | spatial pool σ=8 | 35 | 0.45 | — |
| `axis2` | focus-axis pooling ×2 | 70 | 0.75 | — |
| `pwin2_1` | pooled peak, average ±1 | 22 | 0.70 | — |
| `pwin2_2` | pooled peak, average ±2 | 13 | 0.65 | — |
| **`lvl0mean`** | **average level 0 only** | **6** | **0.97** | **any band < 0.95** |
| `lvl0pool8` | heavy pool at level 0 only | 30 | 0.99 | any band < 0.95 |

### Kill conditions for round 2

6. `lvl0mean` premium > 40 ⇒ level 0 is **not** the premium's home and the
   level attribution above is wrong.
7. `lvl0mean` sharpness < 0.95 in **any** reported band ⇒ the band is not
   empty after all and the whole "costs nothing" claim is refused.
8. If `pool` sharpness does not fall monotonically with σ, the pooling account
   is wrong and must be re-derived before it is offered as a design.
