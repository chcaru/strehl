# M95 -- Election quality: does the merge elect the sharpest frame available?

**Status: PRE-REGISTRATION. Bars fixed before any statistic was computed.**
**Milestone:** M95 (M85-sharpness lineage). **Commissioned by ORCH 2026-08-24 21:45.**

---

## 1. Why this is the last suspect

The owner's complaint is verbatim: *"those stacks don't look too good yet. i can
see the promise."* Four candidate causes have been closed by measurement:

| suspect | closed by | reading |
| --- | --- | --- |
| the gate / averaging | M85, fact 1196 | facet amplitude `0.985x` over a 61x change in `n_eff`; `0.997x` binned-linear |
| the combination stage | M95 merge-vs-frame | merged output **byte-identical** to the elected frame: 180,697 px, 47 frame/ROI combos, **100.0000 %** exact, max **0 DN** of 65535 |
| deconvolution headroom | M115 | headroom `1.0014 +/- 0.0184`; no reconstruction path to extra sharpness |
| the occlusion halo | M87, M121 | a selection artefact, not an averaging one; removal happens at `n_eff = 1.000` |

That leaves exactly one link in the chain untested. My own report says it in
§11.3, and it is the sentence this milestone exists to close:

> **I proved the merge faithfully emits the frame it chose. I did not prove it
> chooses the best frame.**

**Fidelity of emission does not imply optimality of choice.** If the election
systematically picks a slightly-defocused frame, every number in the table above
still holds and the renders are still soft.

---

## 2. The statistic under test, quoted from the product

`crates/strehl-core/src/focus.rs:1-8`:

```text
g(p)     = sqrt(Gx(p)^2 + Gy(p)^2)            3x3 Sobel, scaled by 1/8
focus(p) = box_mean_13(g)(p) / max(sigma_L(p), EPS)
```

Gradient **magnitude** (degree 1, not energy), box-averaged over `27x27`
(`boxfilter.rs:3`), divided by the predicted standard deviation of a **single**
luma sample. The merge elects, per pixel, the frame maximising `focus`.

### 2.1 The mechanism this milestone is testing

`focus.rs:44-48` already admits the weakness, in the product's own words:

> `sigma_L` is the noise standard deviation of a **single** luma sample at that
> signal level [...] It is **not** the standard deviation of the windowed
> gradient magnitude, which is smaller by roughly the window's tap count and is
> not even centred at zero, since `|grad|` is a rectified quantity with a
> **positive noise floor**.

And `focus.rs:26-28`:

> **No operator measured is** [noise-free]: 0 of 36 reached `N <= 1.02x`
> (fact 37). The escape from selection's noise penalty is estimation, not a
> better selector.

So the project already knows the selector is noisy. **What has never been
measured is how much focus that noise costs.** The hypothesis under test is the
**winner's curse**: an argmax over 299 draws of a rectified, positively-biased
statistic does not return the frame with the most signal, it returns the frame
where signal-plus-noise happened to be largest. With 299 frames the maximum of
the noise term is far into its upper tail, and the bias grows with the number of
frames and with the noise-to-detail ratio -- so it is **worst exactly where
detail is weakest**, which is where softness is visible.

This is a mechanism, not a mood. It predicts a specific, falsifiable signature,
and §5 states what would refute it.

---

## 3. The oracle, and why it is not the same statistic wearing a hat

ORCH's constraint: *"An oracle that is genuinely an oracle, not the same focus
measure under another name. If ground truth comes from the statistic under test,
the result is circular by construction."*

The oracle is **not another focus measure**. It is an unbiased estimator of the
*very quantity the elector is trying to maximise*:

```text
elector   E(f,p) = box27( |grad I_f| )(p) / sigma_L(p)          <- maximises signal + noise
oracle    O(f,p) = box27( |grad I_f|^2 )(p) - box27( E|grad n|^2 )(p)
```

For zero-mean noise `n` independent of the scene `s`:

```text
E[ |grad(s + n)|^2 ] = |grad s|^2 + E[ |grad n|^2 ]
```

The cross term vanishes, so the noise contribution is **exactly additive and
exactly computable** from the calibrated noise model and the Sobel tap weights.
Subtracting it yields an **unbiased estimate of `|grad s|^2`, the noise-free
squared gradient energy of the scene.**

That is the structural difference and it is the only one that matters:

- rectified **magnitude** carries a noise bias that **cannot** be subtracted,
  because rectification is nonlinear -- which is precisely `focus.rs`'s own
  admission;
- squared **energy** carries a noise bias that **can** be subtracted exactly.

The elector maximises the noisy quantity. The oracle estimates the clean one.

### 3.1 The confound this introduces, and the control for it

Magnitude and energy are different functionals of the within-window gradient
distribution, so **even with zero noise they could rank frames differently.**
That confound is real and it is controlled by **N0** below: on a noiseless
synthetic ramp the two must agree. If they do not, the measured offset is
"elector vs energy-oracle" and **must not** be reported as "elector vs truth".

---

## 4. The instrument: cross-fitting on G1 and G2

An oracle that is also an argmax has **its own** winner's curse. Comparing them
would measure the difference of two curses, which is not the question.

An RGGB quad carries two green photosites: `G1` at `(0,1)` and `G2` at `(1,0)`.
Measured this session, `o1_cube.py`: each is `(2344, 3514)`, **exactly the
product's `plane_shape`**. They view the same scene through the same optics at
the same instant with **independent read and shot noise**.

```text
SELECT the frame on G1        ->  e1(p) = argmax_f E_G1(f,p)      modelled elector
                                  o1(p) = argmax_f O_G1(f,p)      oracle
EVALUATE the detail on G2     ->  O_G2( e1(p), p )  vs  O_G2( o1(p), p )
```

Because the evaluation channel is independent of the selection channel, **the
curse cancels for whichever rule did the selecting, on exactly equal terms.**
Both rules select on G1 and are scored on G2. Neither gets to mark its own work.

This is the single design decision that makes the number mean anything, and it
costs nothing: the split was already in the sensor.

### 4.1 Why drift does not invalidate this

Arm M is unaligned (`STREHL_ALIGN=0`) and drift spans **73.4 to 165.3 plane px**
across the stack (`s2_rois.json`). That collage effect is what retired my own
`sigma_eq` axis, so it has to be faced rather than assumed away.

It does not bite here, because **the elector compares frames at a fixed pixel
coordinate with no alignment.** Whatever content sits at pixel `p` in frame `f`,
the elector's job is to pick the `f` with the most detail at `p`. Drift changes
*what the content is*; it does not change *whether the choice was right*. The
oracle answers the identical pointwise question on the identical data.

Consequence for reporting, fixed now: the **primary** unit is a *detail deficit*,
which is well-posed under drift. A **frame offset** is only physically meaningful
where drift is small, so it is reported for `ROI-LOWDRIFT` (0.403 px/step) and
reported-with-caveat elsewhere.

---

## 5. PRE-REGISTERED BARS

Fixed before any statistic was computed. The cube build (`o1_cube.py`, pure
decode, no statistics) was launched first; **no number had been produced when
this section was written and committed.**

### B1 -- model fidelity. KILL SWITCH.

The modelled elector must reproduce the **real** election. The real election map
is recovered from the rendered TIFFs by byte-identity -- at `--gate 0` the merged
output equals exactly one frame's bytes, which my own report established at
100.0000 % over 180,697 px, so the map is recoverable wherever the winning frame
is among the rendered set.

- **PASS:** `e1` agrees with the recovered map on **>= 80 %** of testable pixels.
- **FAIL:** below 80 % I **do not report an election offset at all.** I report
  that I could not faithfully model the shipped elector, and the milestone
  returns a negative result about my instrument rather than a claim about the
  product.

80 %, not 95 %, because `e1` selects on G1 alone while the product uses combined
luma; a residual disagreement is expected and is not evidence of infidelity.

### B2 -- oracle commissioning. Discipline 594.

On a synthetic ramp with **known** ground-truth peak, built by exact
frequency-domain blur (no resampling, per the standing warning that any plant
which resamples has already changed the quantity being measured):

- **PASS:** the cross-fitted oracle lands within **+/-1 frame** of truth on
  **>= 90 %** of pixels.
- **FAIL:** the oracle is not commissioned and no oracle-derived number is
  reported.

### B3 -- N0, the magnitude-vs-energy confound (§3.1).

- **PASS:** on a **noiseless** synthetic ramp, elector and oracle elect the same
  frame on **>= 99 %** of pixels.
- **FAIL:** the offset is reported as "elector vs energy-oracle", explicitly not
  as "elector vs truth", and the functional difference is quantified.

### B4 -- THE FINDING. Both directions stated before looking.

Primary statistic: the **cross-fitted detail deficit**

```text
D = 1 - mean_p O_G2( e1(p), p ) / mean_p O_G2( o1(p), p )
```

- **CONCLUDE THE ELECTION IS LOSING SHARPNESS** if `D > 5 %` on **all three**
  detail ROIs, **and** the flat control reads `|D| < 1 %`, **and** the power arm
  P1 is monotone.
- **CONCLUDE THE ELECTION IS SOUND** if `D < 1 %` on all three detail ROIs
  **and** P1 shows the metric would have detected a one-frame offset. A null is
  only admissible with that power reading attached (discipline 595).
- **INCONCLUSIVE-BUT-BOUNDED** for `1 % <= D <= 5 %`: report the bound, claim no
  mechanism.

I have no preference between these outcomes and will report whichever the data
gives. A finding that the election is sound closes the last suspect and forces
the conclusion that the softness is in capture or optics -- which is a
project-level result, not a disappointment.

### B5 -- the unit the owner can feel.

ORCH: *"not a dimensionless score."* Convert the median frame offset to an MTF
cost at the binned Nyquist (**48.94 cy/mm**) and at **74 cy/mm**, using the
**measured** through-focus response of this capture, never a theoretical defocus
model. Report as *"the elected frame is on average N frames off peak, costing
X % MTF at Y cy/mm."*

---

## 6. Controls

| id | control | what it proves | required reading |
| --- | --- | --- | --- |
| **N0** | noiseless synthetic ramp | magnitude vs energy is not itself the effect (§3.1) | agreement >= 99 % |
| **N1** | oracle scored against itself | the deficit has a zero | `D = 0` by construction |
| **N2** | noiseless ramp, both rules | the deficit reads zero when the election IS optimal | `D` ~ 0 for both |
| **N3** | `ROI-FLAT`, contrast **1.18** | no detail means no findable peak; the metric must not manufacture one | `|D| < 1 %`, frame choice scatters |
| **P1** | force election to `peak + k`, `k = 1,2,5,10,25` | the deficit responds, monotonically, with the right sign | strictly increasing in `k` |
| **P2** | plant exact frequency-domain blur in one frame | both rules demote it | planted frame not elected |
| **P3** | G1/G2 independence | the cross-fit is not a sham | G1 == G2 on far fewer than half of pixels |

**P1 is the discipline-595 power control and it is mandatory**: if my headline is
that the election is sound, P1 is the only thing standing between that null and
a metric that always returns zero. ORCH's own warning applies directly -- *"A
metric that always returns zero passes a null perfectly."*

**Sign convention will be read off P1's own control**, not assumed, per the
warning that a sign error with accurate magnitude is invisible.

---

## 7. What I am not claiming

- Not that the aligned path behaves the same. Arm C's geometry control (F3)
  failed on 2 of 3 ROIs, so the aligned path remains my largest characterisation
  gap and nothing here extends to it.
- Not anything about colour. The lateral-CA correction is another lane's.
- Not that a better selector is the fix. `focus.rs:26-28` says the escape is
  estimation, not selection, and this milestone tests the size of the problem,
  not the remedy.

---

## 8. Bearing on the resampler-kernel decision

Stated here at ORCH's request, from the agent that measured it:

**My `+0.1160 dex` resampler-kernel result is withdrawn (§23 of
`M95-kernel.md`), and its withdrawal removes the measured basis for promoting a
sharper resampler kernel by default -- so the "G3 met" milestone recorded in
`docs/research/ORCH-kernel-decision.md` makes the change cheaper and more
reversible, but it does not make it justified, and nobody should read "all gates
met" as "go".**

The band that result was scored in is **12.8 % subject detail (CI 12.2-13.4) and
87.2 % noise**, with a dark-frame placebo at **1.0006** and a defocus null at
**+0.0033**.
