# V-M97kill -- independent verification of the election-time masking KILL

Verifier: an agent that did not author M97, M97e, M123 or the SYNTHESIS fold.
Subject: SYNTHESIS facts **1770-1774** and disciplines **915-917**, folded at
`4e06f50`; primary sources `docs/research/M123-outlier-mask.md` (`5bd4997`),
`docs/research/M97e-robust-election.md`, and `crates/strehl-core/src/outlier.rs`
as corrected at `bfbff8e`.

**Method.** Every measured number below was re-derived by rebuilding the M123
instruments from `bfbff8e` in an isolated worktree (`C:\dev\strehl-out\V-M97kill-tree`,
created with `git worktree add --detach`) and re-running them against the owner
real captures on `D:\`. Two additional probes were written to attack the parts
the milestone did not test. Nothing in the shared tree was edited; the two probe
sources live in the isolated worktree only and were never committed.

---

## Verdict

**DEFECTS FOUND** -- in the folded corpus rows, not in the kill.

Every headline *measurement* reproduces to the digit. Two of the five facts
overstate what those measurements support, and one of them (1771) states a
**mechanism that I refuted by direct experiment**:

| item | claim | verdict |
| --- | --- | --- |
| 1 | `ShiftFree` 29.55% trap vs 6.87% foam, 4.3x inverted | **CONFIRMED** (reproduced exactly; direction is the damning one) with two omissions |
| 2 | zero-dose 24.51% / 23.54% at 0.35 / 34.57% at 2.00 | **CONFIRMED**, and 0.00 px is provably the identity |
| 3 | mean \|s\| 0.9521 px = 2.7x `DEFAULT_MIN_SHIFT_PX`; no threshold exists | number **CONFIRMED**; the *conclusion* **REFUTED** as stated |
| 4 | 26-91 vs 357-593 tiles, caused by motion destroying correspondence | counts **CONFIRMED**; mechanism **REFUTED** |
| 5 | stale docstring, 352 tests at `bfbff8e` | **CONFIRMED** except one clause, which is **REFUTED** |
| 6 | killed five times, four prior reports, same verdict | **REFUTED** as stated; the honest count is three |

**The top-line conclusion is nonetheless supported.** See the last section.

---

## Commands run

```text
git worktree add C:\dev\strehl-out\V-M97kill-tree --detach bfbff8e
cargo test -p strehl-core                      # in the worktree, at bfbff8e
  -> test result: ok. 352 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.14s
  -> Doc-tests strehl_core: 0 passed; 0 failed
cargo build --release -p strehl-cli --example m123-outlier-real --example m123-trap-decompose
  -> Finished `release` profile [optimized] target(s) in 2m 19s
.\target\release\examples\m123-outlier-real.exe --out C:\dev\strehl-out\V-M97kill-out
.\target\release\examples\m123-trap-decompose.exe
.\target\release\examples\v-mech-probe.exe     # my probe, worktree only
.\target\release\examples\v-bar-sweep.exe      # my probe, worktree only
git show bfbff8e^:crates/strehl-core/src/outlier.rs   # read via python subprocess, bytes, never redirected
```

### Re-run of `m123-outlier-real` at `bfbff8e` (full output, abridged to the arms in evidence)

```text
crop 1024x1024 green luma, 1024 tiles of 32px, k=6, blur_radius=6
disagreement bar = 1 + k*sqrt(2/N) = 1.2652   displacement bar = 1 + k = 7.0 on 2 dof
min_shift_px = 0.35  resolution_margin = 3

case           arm             mean        sd       p50     p99.9     fire%   gated%   mean|s|  p99.9|s|
flat-null      ShiftFree     22.066   30.2727    10.822   226.281     2.44%    0.00%    2.6646   20.2378
defocus[TRAP]  Raw            1.780    1.8678     1.055    16.474    29.60%        -         -         -
defocus[TRAP]  LowFreq       41.943  111.5599     8.069  1437.959    61.80%        -         -         -
defocus[TRAP]  ShiftFree    283.356 1086.9609    24.056  7668.743    69.42%   29.55%    0.7260   16.2530
motion[PLANT]  ShiftFree   3251.387 7468.6521   314.203 70413.234    91.94%   62.78%    0.5328    7.1245
foam[PLANT]    ShiftFree   1708.043 11041.3888  120.426 139878.031   77.86%    6.87%    4.8378  161.8759

-- plant [POSITIVE CONTROL] planted translation on a real 109MSDCF defocus pair
0.00           ShiftFree    440.220 2601.9955    24.373 29001.314    57.52%   24.51%    0.9521   10.7785
0.15           ShiftFree    757.294 1369.3857   224.845 15049.905    34.67%   23.44%    0.9118   19.7872
0.35           ShiftFree   1207.553 1630.8275   595.734 13992.549    30.18%   23.54%    1.2153   55.1573
0.50           ShiftFree   1634.698 2145.0291   752.965 18252.170    29.79%   24.71%    1.6603   69.7476
1.00           ShiftFree   1540.854 3857.7652   112.230 29920.283    75.49%   34.77%    1.9326   28.1520
2.00           ShiftFree   4587.893 16685.2415  294.353 104626.133   76.17%   34.57%    3.6231   62.9914
```

Every figure in facts 1770 and 1772 that comes from this instrument reproduces
**to the digit**, on a clean rebuild, in a different worktree, by a different
agent. The M123 arithmetic is sound and the instrument is deterministic.

### Re-run of `m123-trap-decompose`

```text
stack             pair  tiles    rms|s| rms resid    expl%
109MSDCF TRAP        0    357    0.9414    0.8107    25.8%   scale +936.9 ppm
109MSDCF TRAP        5    593    0.4559    0.2960    57.8%   scale +777.4 ppm
109MSDCF TRAP MEAN                0.5496    0.3370    62.4%
coffee-bubbles       0    761    0.5002    0.3249    57.8%
coffee-bubbles       4   1009    0.3577    0.1502    82.4%
coffee-bubbles MEAN               0.5263    0.2360    79.9%
foam                 0     26   18.2595   16.5308    18.0%
foam                 5     91    1.1693    0.8936    41.6%
foam MEAN                         4.6529    3.5401    42.1%
```

Tile ranges 357-593, 761-1009 and 26-91 reproduce exactly, as do rms 0.5496 /
0.5263 / 4.6529 and the 62.4 / 79.9 / 42.1% explained fractions. The M12
resolvable percentages also reproduce exactly as the four-pair means:
`(357+380+404+449)/4/1024 = 38.82%`, `(761+870+943+991)/4/1024 = 87.04%`,
`(26+42+52+60)/4/1024 = 4.39%`.

---

## Claims checked

### 1. `ShiftFree` gates 29.55% of the stationary trap against 6.87% on `foam` -- CONFIRMED

Reproduced exactly (table above). `29.55 / 6.87 = 4.301`, and the direction is
the damning one: **the gate fires 4.3x harder on the tripod stack where nothing
moves than on the stack that moves.** Fact 1770 states it the right way round.
The trap and plant identities check out against the corpus, not just against the
report: `captures-needed.md:1784` records `foam` as a scene that *evolves across
the 249-second capture*, decorrelating within itself to 0.087/0.122/0.243, and
`M28` records `109MSDCF` as the *photometrically quietest in the corpus (fact
180), no known motion*.

Two things the fold dropped, both of which a reader of fact 1770 alone would get
wrong:

1. **The pre-registered PLANT was `coffee-bubbles`, and it went the RIGHT way.**
   `PREREGISTRATION.md:144` names `coffee-bubbles` as the plant, and it gated
   **62.78%** against the trap **29.55%** -- 2.12x in the *correct* direction.
   Fact 1770 quotes only the `foam` arm. M123 defuses this honestly in M5 (the
   2.12x is texture, because the true displacements separate by 0.96x), but the
   corpus row now reads as though every plant arm inverted. Only one did.
2. **6.87% is a fraction of all 1024 tiles, not of judgeable tiles.** M12
   reports `foam` firing on **98.9%** of what it can resolve against 58.6% for
   the trap. Per tile the gate is actually *willing to judge*, the ranking is
   already correct. The 4.3x inversion is a **coverage** artifact, and item 4
   below shows the coverage deficit is not caused by motion.

One further qualification on the phrase *any firing here is wrong by definition*:
the trap is a null for **subject** motion, not for image-plane displacement.
`m123-trap-decompose` measures a coherent **+777 to +937 ppm** scale change per
adjacent pair on `109MSDCF`, which is ~0.68 px of real displacement at the corner
of the 1024 crop. A displacement detector firing there is not firing on nothing.

### 2. The zero-dose positive control -- CONFIRMED, and 0.00 px is provably the identity

24.51% / 23.54% / 34.57% reproduce exactly, as do the intermediate 23.44 / 24.71
/ 34.77 and every `mean |s|`.

The load-bearing question is whether `0.00 px` is really no planted displacement.
It is, twice over:

- **By code.** `m123-outlier-real.rs:shifted()` computes `fx = dx.floor() = 0`,
  `t = dx - fx = 0`, `i0 = 0`, and returns `v[i]*(1.0 - 0.0) + v[i-1]*0.0`,
  which is `v[i]` exactly. No resample, no interpolation blur, no rounding.
- **By measurement.** My probe fed the untouched pair straight to `shift_tiles`
  with no call to `shifted` at all, and got a bit-identical row:

```text
109MSDCF real pair (a,b)      informative 797  usable 357  gated 251 (24.51%)  med sigma_px 0.1448  mean|s| 0.9521
109MSDCF planted 0.0 px       informative 797  usable 357  gated 251 (24.51%)  med sigma_px 0.1448  mean|s| 0.9521
```

So discipline 915 rests on a real zero-dose arm. **But the words are wrong.**
Fact 1770 says a quarter of tiles *fire on nothing at all*; discipline 915 says
*its response to nothing*. The zero-dose arm is a real `109MSDCF` defocus pair
carrying a **0.9521 px** displacement pedestal, about a quarter of which (in
variance, on that very pair) is coherent global scale drift. It is zero *planted*
dose, not zero displacement. M123 M8 says this correctly -- *a ~0.95 px pedestal
of defocus- **and drift**-induced displacement* -- and the fold dropped the
qualifier. The discipline survives (a dose-response with no null to rise from is
still fatal); the phrasing invites a reader to believe the gate fires on a null,
which is a stronger and false claim.

### 3. Mean `|s|` 0.9521 px = 2.7x the bar -- number CONFIRMED, conclusion REFUTED as stated

`crates/strehl-core/src/outlier.rs:630` (and `:576` at `bfbff8e^`) reads
`pub const DEFAULT_MIN_SHIFT_PX: f32 = 0.35;`. `0.9521 / 0.35 = 2.7203`, so
*roughly 2.7x* is right.

Two overstatements, then the substantive one:

- **0.9521 is one pair, and it is the larger of the two available figures.** It
  is pair 0 of `109MSDCF`, the single pair the positive control rides on. The
  eight-pair trap mean is **0.7260 px**, which is 2.07x the bar. M4 states both;
  fact 1772 quotes the bigger one as though it were the stack figure.
- **It is not *real defocus alone*.** Fact 1772 says *no subject movement
  whatsoever*, which is true, and then attributes the whole pedestal to defocus,
  which is not. On the plant pair the decomposition measures a coherent
  **+936.9 ppm** scale term, and across six pairs a global similarity explains
  **62.4%** of the field variance. The pedestal is defocus **plus magnification
  breathing**.

**The conclusion -- *there is no threshold in between* -- is refuted by direct
measurement.** M123 never swept the bar on real frames; it inferred the
impossibility from summary statistics. I swept it (6 adjacent pairs, `ShiftFree`,
`k = 6`, shipped `mask_tiles`):

```text
stack                       0.35px    0.50px    1.00px    2.00px    3.00px    5.00px    8.00px
109MSDCF TRAP               23.50%    16.98%     8.54%     4.79%     3.52%     1.74%     0.81%
  ^ fixed-resolution        23.50%    11.08%     0.52%     0.11%     0.11%     0.10%     0.02%
coffee-bubbles PLANT        60.45%    39.21%     3.04%     0.60%     0.44%     0.23%     0.13%
  ^ fixed-resolution        60.45%    37.21%     1.68%     0.10%     0.07%     0.02%     0.00%
foam PLANT                   5.49%    25.47%    58.11%    45.07%    29.23%    16.98%    11.17%
  ^ fixed-resolution         5.49%     5.31%     4.43%     1.97%     0.83%     0.37%     0.33%
```

(`fixed-resolution` freezes the resolution gate at the shipped `sigma*3 <= 0.35`
and moves only the magnitude test, so the two rows bracket the coupling that
`mask_tiles` builds in by using `min_shift_px` for both gates.)

At **`min_shift_px = 2.0 px`** the shipped gate fires on **45.07%** of `foam`
against **4.79%** of the stationary trap -- **9.4x in the correct direction**,
against a pre-registered separation criterion of 10x. With the tile supply held
fixed it is 1.97% vs 0.11%, **18x**. So the sentence *raising the bar past the
defocus floor discards the plant* is **false for `foam`**: bars from 1 to 3 px sit
above the 0.95 px defocus pedestal and restore the correct ordering.

What the data **does** support is the weaker, still-fatal statement:

> No single bar keeps *both* plants above the trap. At 0.35 px `foam` (5.49%) is
> below the trap (23.50%); at 1.0 px `coffee-bubbles` (3.04%) is below the trap
> (8.54%). The two plants demand opposite bars.

and the independent, bar-free result that actually kills it: **the underlying
displacements do not separate at all** -- `rms|s|` 0.5496 px on the still stack
against 0.5263 px on the moving one, a ratio of 0.96x. That is the sentence fact
1772 should be making. As written, *there is no threshold in between, which is why
this is a kill rather than a tuning exercise* is a universal claim with a measured
counterexample.

*Disclosure:* my sweep is post-hoc on the same two stacks, so it does not rescue
the mask -- it only refutes the universally quantified claim.

### 4. Fact 1771 -- tile counts CONFIRMED, mechanism REFUTED

The counts are exact: `foam` 26-91, `109MSDCF` 357-593 (`coffee-bubbles`
761-1009). The mechanism is not.

**The code says motion cannot do this.** In `outlier.rs:403-517`, the
information matrix `G` is accumulated from the gradients and Laplacian of frame
`b` alone, weighted by `1/(var_a + var_b)`. The residual `d = a[i] - b[i]`
(`:445`) enters only the right-hand side. `informative` is set false when
`det <= 0.0 || l_min < MIN_GRADIENT_INFO` (`:497`) and `sigma_px = 1/sqrt(l_min)`
(`:510`) -- both are functions of `l_min`, i.e. of one frame gradient content and
the noise model. The `usable` count in `m123-trap-decompose` and the resolution
gate in `mask_tiles` (`:674`) are the same quantity at a tighter bar
(`sigma_px*3 <= 0.35`, i.e. `l_min >= 73.47`). **Displacement magnitude does not
appear in any of it.** A large shift cannot inflate `sigma_px`.

**Two experiments confirm that reading.**

*(a) Remove the motion and the tile supply does not move.* Feeding the same frame
twice makes the true displacement exactly zero by construction:

```text
                                informative   usable   gated          med sigma_px   mean|s|
109MSDCF real pair (a,b)                797      357   251 (24.51%)         0.1448    0.9521
109MSDCF self pair (b,b)                794      356   106 (10.35%)         0.1455    3.3690
coffee-bubbles real pair (a,b)          984      761   453 (44.24%)         0.0408    0.5894
coffee-bubbles self pair (b,b)          986      762   179 (17.48%)         0.0406    1.4058
foam real pair (a,b)                    719       26    26 ( 2.54%)         0.2263   24.6045
foam self pair (b,b)                    720       25     8 ( 0.78%)         0.2257    7.4859
```

`foam` with **all** of its motion deleted still supplies **25** usable tiles
against 26 with the motion present. Motion accounts for **one tile** of the
331-tile deficit against the trap.

*(b) Add motion to the still stack and the tile supply still does not move.*
Planting integer translations on the `109MSDCF` pair (`shifted` is exact at
integer `dx`, so no resample blur is involved):

```text
109MSDCF planted  0.0 px   informative 797  usable 357  gated 251 (24.51%)  med sigma_px 0.1448  mean|s| 0.9521
109MSDCF planted  1.0 px   informative 804  usable 356  gated 356 (34.77%)  med sigma_px 0.1472  mean|s| 1.9326
109MSDCF planted  2.0 px   informative 803  usable 354  gated 354 (34.57%)  med sigma_px 0.1468  mean|s| 3.6231
109MSDCF planted  5.0 px   informative 787  usable 360  gated 360 (35.16%)  med sigma_px 0.1387  mean|s| 4.6965
109MSDCF planted 10.0 px   informative 788  usable 352  gated 351 (34.28%)  med sigma_px 0.1468  mean|s| 6.8559
109MSDCF planted 20.0 px   informative 789  usable 350  gated 344 (33.59%)  med sigma_px 0.1399  mean|s| 8.8765
```

A **20 px** planted displacement -- four times the `foam` mean `|s|` of 4.84 px --
moves the usable count from 357 to 350, a **2%** change, and leaves
`med sigma_px` flat at 0.14. If large motion broke the linearisation and inflated
`sigma_px`, this row would look like `foam`. It does not.

**The confound is real and it is the dominant one.** The quantity that does
separate the three stacks is the reference-frame gradient information:
`med sigma_px` is **0.0408** (coffee-bubbles), **0.1448** (109MSDCF), **0.2263**
(foam), against a usable bar of `0.35/3 = 0.1167`. That ordering *is* the usable
ordering. Three further tells point the same way:

- `coffee-bubbles` **moves** and yields **more** usable tiles than the stationary
  trap (761-1009 vs 357-593). The claimed anti-correlation is not even monotone
  across the three stacks in evidence.
- Within **every** stack the usable count climbs monotonically with pair index
  (109MSDCF 357-380-404-449-459-593, foam 26-42-52-60-73-91). Nothing moves in
  `109MSDCF`, so a motion mechanism cannot explain a 1.66x swing inside it; a
  through-focus sharpness change explains all three stacks at once.
- M123 M5 already attributes the `coffee-bubbles` tile surplus to *contrast and
  texture*. The same explanation applies to the `foam` deficit; the report takes
  it in one direction and not the other.

M123 section 6 predicted this exact hole: *the two cheapest places to attack it
are ... M7 (check whether `foam` abstention is really the resolution gate by
reporting the veto reason per tile)*. It was never done. Fact 1771 is labelled
DERIVED, but it is stated as **This is a mechanism, not a coincidence**, and
discipline 916 generalises it into a rule about anti-correlated failure modes.
On the evidence, the abstention is **uncorrelated with motion and correlated
with low gradient information**. I did not isolate which property of `foam`
suppresses `l_min` (low contrast, gradient anisotropy, or the Schur projection of
the defocus direction eating the curvature-dominated bubble edges); that remains
unmeasured. What is measured is that it is not the motion.

*Incidental finding, reported not fixed:* on the self-pair rows above the gate
fires at all -- 10.35% on `109MSDCF` with `a` and `b` the same buffer. With
`d == 0` the solution should be `s = 0`. It is not, because the noise-covariance
correction `rl += (lap*d - 4.0*vb)*iv` (`outlier.rs:477`) leaves a non-zero
right-hand side which the Schur step converts into a displacement -- `mean |s|`
3.3690 px out of two identical planes. That correction is *correct* for the
intended input (two independent noisy frames), so this is not a defect report
against `outlier.rs`; it is a caution that any future user of `shift_tiles` who
feeds it correlated planes will be handed a fabricated displacement.

### 5. Fact 1773, the stale docstring -- CONFIRMED except one clause

Read at `bfbff8e^` via `git show ... | python subprocess`, decoded as bytes:

```text
 21 | //! motion**. This module implements two and is built so they can be measured
 27 | //! - [`Discriminator::LowFreq`] - disagreement after both planes are low-pass
 28 | //!   filtered. Defocus is approximately a low-pass, so it largely cancels;
 84 | pub enum Discriminator {          <- variants Raw(88) LowFreq(109) Shift(135) ShiftFree(153)
 91 |     /// **MEASURED FAILURE - this arm does not work, ...
```

So: header says **two**, enum documents **four**, `LowFreq` is marked a MEASURED
FAILURE 63 lines below the header sentence that praises it. Confirmed. (Fact
1773 says *forty lines below*; it is 50-63 depending on which line you count
from. Immaterial.)

**The clause that is wrong:** fact 1773 says *the **header** sentence "has not
yet been measured on real frames" about `DEFAULT_MIN_SHIFT_PX`*. That sentence is
not in the header. At `bfbff8e^` it is at **lines 574-575**, inside the doc
comment of `DEFAULT_MIN_SHIFT_PX` itself (line 576) -- 553 lines below the module
header:

```text
574 | /// bar and a coarser one may need a larger. It has not yet been measured on
575 | /// real frames; see the `NOT VERIFIED` note in the milestone record.
576 | pub const DEFAULT_MIN_SHIFT_PX: f32 = 0.35;
```

Both `M123` section 0 and the `bfbff8e` commit message locate it correctly on the
constant. The error was introduced by the fold.

And the characterisation attached to it -- *work commissioned by a claim its own
file had already refuted* -- does not apply to that sentence. **"It has not yet
been measured on real frames" was TRUE when M123 was commissioned**; M123 is the
milestone that measured it. The claim the file had already refuted is the
*other* one (the `LowFreq` question and the "two discriminators" count). Fact
1773 welds an accurate open question onto a stale one and calls both stale. The
headline of 1773 survives; that sentence of it does not.

`cargo test -p strehl-core` at `bfbff8e`: **352 passed; 0 failed**. Confirmed.

### 6. Fact 1774, *killed five times* -- REFUTED as stated

M123 section 0 does list **four** prior reports, so the count of *reports* is
right. The claim that they *reach the same verdict* is not. I read all four:

| report | what it actually concluded | a kill? |
| --- | --- | --- |
| `M28-robustness-mask-measured.md:14` | *"**It is** [separable], and the correction to R10 is one line: compare against the immediate neighbours"* -- a **positive** detector result, self-labelled *NOT INDEPENDENTLY VERIFIED* (`:3`) | **no** |
| `M60-robustness-mask-at-merge-time.md:281` | *"I did not build the mask"*, at the merge-time seam, redirecting the work to the raw stack | yes, average side |
| `M89-robustness-mask.md:294` | *"The metric works and should be adopted. The mask, as specified, should not ship"* | yes, average side |
| `M97r-outlier-mask.md` | `LowFreq` fails, **`ShiftFree` survives every control** (synthetic only; section 6 concedes the configuration is in-sample) | **no** |

Two of the four reached the **opposite** verdict on the detector question. M123
own section 5 counts them accurately -- *"This is the **fourth** milestone to
decline to ship this mask (M60, M89, M97r own section 6 caveat, now M123)"* --
and even that counts M97r via a caveat rather than a verdict, and excludes M28.

**Worse for the arithmetic, M89 is not a prior kill of *election-time* masking;**
it is the report that **commissioned** it. `M89:320-324`:

> *a robustness mask on the averaging stage alone recovers 6.0% of the available
> benefit and is close to pointless. **The correct next step is not this mask; it
> is to make the election robust**, and to do it after alignment.*

That is the direction fact 1770 declares killed. Counting the report that opened
the direction as one of the times it was closed inverts it.

There is also a stage conflation. M28, M60, M89, M97r and M123 all measure the
**average-time** chi2/displacement mask -- M123 M13 says so in as many words,
*"`outlier.rs` is unambiguously the average-time instrument"*. Only **M97e**
actually gated an election. So:

- kills of the **average-side** mask: **three** (M60, M89-as-specified, M123);
- kills of **election-time masking**: **one wired** (M97e, `robust.rs` LOO `z`)
  plus **one detector-level** (M123, of the `ShiftFree` arm that M97e section 6
  nominated as the next election-time discriminant);
- reports that concluded the thing works: **two** (M28, M97r).

"Five" is not reachable without counting two positive results and one
recommendation as kills. The corrected docstring at `bfbff8e` states it
defensibly -- *five reports on real data ... have asked whether to wire this into
the merge and none concluded yes* -- which is a claim about **wiring**, not about
verdicts. Fact 1774 hardened that into *KILLED FIVE TIMES* and *four prior reports
reaching the same verdict*, and both hardenings are wrong. The rule-40 lesson
that fact 1774 exists to teach is untouched: the prior reports **were** there and
**were not** searched.

---

## Defects

All are in the corpus rows, not in the code and not in the instruments.

1. **MAJOR -- fact 1771 states a refuted mechanism.** `SYNTHESIS.md:2329`:
   *"because **large motion destroys the local gradient correspondence the
   statistic requires**"* and *"This is a mechanism, not a coincidence"*.
   Reproduce: `outlier.rs:403-517` builds `G` from frame `b` only; feeding
   `foam` the same frame twice (zero motion) still yields 25 usable tiles of
   1024, and planting 20 px on the stationary trap leaves 350 of 357. The
   abstention is a gradient-information property, not a motion property.
   `coffee-bubbles` moves and yields the *most* tiles of all three stacks.
   Discipline 916 is built on this mechanism and inherits the weakness.
2. **MAJOR -- fact 1772 makes a universal claim with a measured counterexample.**
   `SYNTHESIS.md:2330`: *"Raising the bar past the defocus floor discards the
   plant ... There is no threshold in between"*. Reproduce: `v-bar-sweep`, 6
   pairs -- at `min_shift_px = 2.0 px` the shipped gate fires 45.07% on `foam`
   and 4.79% on the trap, 9.4x in the correct direction. The claim holds for
   `coffee-bubbles`, not for `foam`. The defensible form is *no single bar keeps
   both plants above the trap*.
3. **MINOR -- fact 1772 mis-sources 0.9521 px twice.** It is a single-pair
   figure (the eight-pair trap mean is 0.7260, 2.07x the bar, not 2.7x), and it
   is not *"real defocus alone"*: the same milestone measures +936.9 ppm of
   coherent magnification drift on that pair and 62.4% mean explained variance
   from a global similarity across six.
4. **MINOR -- fact 1770 and discipline 915 say "nothing" where the data says
   "no planted dose".** The zero-dose arm carries a real 0.95 px pedestal. M123
   M8 words it correctly; the fold dropped *and drift*.
5. **MINOR -- fact 1773 puts the `DEFAULT_MIN_SHIFT_PX` sentence in the module
   header.** It is at `outlier.rs:574-575` at `bfbff8e^`, in the doc comment of
   the constant, 553 lines lower; and that sentence was **true** when M123 was
   commissioned, so it is not an instance of *a claim its own file had already
   refuted*.
6. **MINOR -- fact 1774 overcounts.** Two of the four cited priors concluded the
   opposite, and M89 recommended the very direction being declared killed.
7. **MINOR -- fact 1770 attributes a pre-registration to ORCH that is not in the
   tree.** A repo-wide search for *two outcomes* / *the direction is dead* finds
   the phrase only in `SYNTHESIS.md:2328` itself. What exists is
   `experiments/M123-outlier-mask/PREREGISTRATION.md` (six criteria, three
   failed) and the M97e section 1 statement that ORCH registered the trap/plant
   bar before the build. Both were committed in the same commit as their own
   results (`5bd4997`), so *written before* is asserted, not git-provable.
8. **CONTEXT LOSS -- fact 1770 quotes only the arm that inverted.** The
   pre-registered plant `coffee-bubbles` gated 62.78% against the trap 29.55%,
   2.12x the right way. M123 M5 explains why that is not a rescue; the corpus
   row omits the arm entirely.

---

## Gaps -- what remains unverified, and why

- **The M97e leg was not reproduced.** Its 7.3723% / 0.3431% (21.5x) requires
  rendering `coffee-bean` (105 frames) and `foam` (100 frames) twice each with
  the `merge_cmd` seam that M97e section 5 says was **never applied to the shared
  tree**, and `merge_cmd.rs` currently carries another agent uncommitted edits. I
  checked only that the arithmetic is internally consistent (7.3723/0.3431 =
  21.49) and that M97e carries two independent instruments (in-process `moved`
  counter, cross-process TIFF diff) agreeing to half a point. **Its own
  disclosure remains open**: the M97e trap `coffee-bean` is the stack with the
  largest photometric drift in the corpus (11.70% peak-to-peak, fact 180), and
  M97e states it could not rule that out as the cause of the trap firing. Fact
  1770 cites the 21.5x as independent corroboration without carrying that caveat.
- **Fact 1189 (100% at the election vs 6% at the average) was not re-derived.**
  It is the economic half of the kill and it is inherited here.
- **No test exists for the changed behaviour, because there was no behaviour
  change.** `bfbff8e` is docs-only (I diffed it: the only non-doc hunk is an
  intra-doc link in `merge.rs:734`). The 352 passing tests therefore prove that
  nothing regressed; they do **not** exercise any claim in facts 1770-1774. The
  numbers in those facts are pinned by nothing in CI -- they live only in a
  report and in a doc comment. My re-run is currently the only reproduction.
- **The sub-cause of the `foam` abstention is unmeasured.** I proved it is not
  motion. Whether it is contrast, gradient anisotropy, or the Schur projection
  removing curvature-dominated bubble edges is open, and M123 section 6 already
  named the experiment (veto reason per tile) that would settle it.
- **One stack, one crop.** Everything here is the centre 1024x1024 of the green
  luma on 6-8 adjacent pairs of three stacks out of 24, exactly as M123 declared.

---

## Is the top-line conclusion supported?

**Yes. Abandoning these two discriminators is supported, and the defects above do
not touch the load-bearing evidence.** Three independent measurements, all of
which I reproduced myself, each suffice on their own:

1. **The trap false-positive rate is 29.55% against a pre-registered <= 1%** --
   thirty times the bar, and level with the destruction threshold the brief
   itself named. A mask that drops 29.55% of tiles from a stationary subject
   costs 29.55% of `n_eff` -- about 19% added noise by the pricing in the M123
   pre-registration itself -- to defend against a rare event.
2. **The displacements do not separate**: 0.5496 px rms on the still stack
   against 0.5263 px on the moving one, 0.96x. Whatever 2.12x of gated-rate
   separation exists is texture, and no threshold on a quantity that ranks
   backwards can be tuned into one that ranks forwards.
3. **The dose-response is flat across the range that decides the bar**: 24.51%
   at zero planted dose, 23.54% at the bar, 24.71% at 0.50 px. The instrument is
   mostly reading something other than the planted displacement.

Point 3 is the one worth keeping, and discipline 915 (run the zero-dose arm
first) is the right generalisation of it -- once the words *its response to
nothing* are corrected to *its response to no planted dose*.

**What is NOT supported is the wider reading the fold invites.** Precisely:

- The kill is of **two named discriminants at their shipped configurations**, not
  of the **stage**. M123 section 5 says so explicitly -- the third, unbuilt
  discriminator (analysis-by-synthesis against the running estimate re-blurred to
  the frame own focus) is untouched: *"Nothing here speaks to it."* And M89 6.0%
  vs 100% stage pricing, which says the election is where the defect must be
  caught, is unchallenged by anything in M97e, M123 or this verification.
- The `4.3x the wrong way` headline is **not** evidence that the statistic
  prefers stationary subjects. It is a coverage artifact of `foam` supplying 26
  of 1024 judgeable tiles, and that deficit is present with the motion removed.
  Per judgeable tile the ranking is already correct (98.9% vs 58.6%). The kill
  does not need it, and the corpus would be more accurate without it.

So: **KILL UPHELD, on facts 1770 and the trap/dose-response half of 1772.**
**Fact 1771 should be weakened from a mechanism to an observation, or replaced
with the measured one: the gate abstains in proportion to missing gradient
information, which on this corpus is uncorrelated with motion.** **Fact 1772
should lose the universal quantifier.** **Fact 1774 should say three.**

---

## Provenance

- Worktree `C:\dev\strehl-out\V-M97kill-tree`, detached at `bfbff8e`, created
  with `git worktree add --detach`; `crates/strehl-core/src/outlier.rs` in the
  shared tree is clean and unchanged since `bfbff8e` (`git log` + `git status`
  path-scoped), so the module measured here is the shipped one.
- Probes `crates/strehl-cli/examples/v-mech-probe.rs` and `v-bar-sweep.rs` exist
  **only** in that worktree and are deliberately not committed. They reuse the
  M123 loader verbatim (decode, `green_luma_with_clip`, centred 1024 crop,
  `profile::noise_model_for`) so that the only difference from the milestone
  instrument is what is printed.
- No file in the shared tree was edited by this verification other than this
  report. No TIFF was read at all, so the PIL 16-bit hazard (P40) does not arise;
  every pixel here came from `strehl_raw::decode` on the ARW originals.
- Old file revisions were read with `git show <rev>:<path>` through a Python
  `subprocess` returning bytes, never `git checkout` and never a PowerShell
  redirect.
