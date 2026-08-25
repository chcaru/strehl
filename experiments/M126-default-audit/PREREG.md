# M126 — pre-registration: what the dormant default-off gates would cost or buy

**Frozen before any outcome datum was computed.** Nothing in this file was
written after a score existed. The evidence that this is true is the commit
that carries it: no `scores.json`, no metric script output and no rendered arm
other than the timing probe disclosed in §0 exists at that commit.

Measured against the pinned commit `d5ba764de26fd9addd01c167c8d0f6c465f25fb4`,
in a detached worktree at `C:\dev\strehl-out\M126-tree`, binary built once into
a private `--target-dir` at `C:\dev\strehl-out\M126\target`.

---

## 0. What I had already looked at when I wrote this

Full disclosure, because "pre-registered" is a claim about ordering and the
ordering is checkable.

1. `AGENTS.md` in full; `SYNTHESIS.md` §5 disciplines 877-885; the M116, M122
   and M110 reports; SYNTHESIS facts 1698-1702 (V-M116).
2. The source of every gate: `optics.rs`, `merge.rs`, `align_cmd.rs`,
   `merge_cmd.rs`, `merge_cmd/halo.rs`.
3. **A timing probe and a worker-plan read.** I ran `stack` twice with no
   scoring, to size the design: 20 frames unaligned on `tweezers-cpl` (6.4 s)
   and 100 frames aligned (29.5 s), plus one `align` solve (14.2 s). I read the
   wall clock, the worker plan line, and the align solve's held-out error. I
   deleted the probe TIFF without opening it. **No metric was computed on any
   image before this file was committed.**
4. **I did not run `prior_art.py` after the fact — I ran it first, and it
   changed this design.** It surfaced `M116-promotion.md`, which had already
   asked a large part of this question. See §9.

## 0b. The prior art, named (rule 40, rule 43)

The brief I was given says *"Nobody has ever measured what happens when they
are ON."* **That sentence is false and I am recording it here rather than in
the report's conclusion**, because rule 43 makes an assertion of absence a
claim, and this one would have stopped me looking.

- **`docs/research/M116-promotion.md`** asked exactly the promotion question for
  four instruments — photometric, soft gate (both kernels), halo, outlier mask —
  on three real captures against pre-registered bars, and answered **"none of
  the four instruments clears its pre-registered promotion bar."** It is listed
  in the AGENTS.md milestone ledger.
- **SYNTHESIS facts 1698-1702 (`V-M116`)** independently re-verified it and
  refuted its travelling headline (fact 1699: the merge-vs-single-frame
  comparison ran with `STREHL_ALIGN=0`).
- `M110-track-jitter.md` measured `STREHL_SMOOTH` and shipped it off, saying it
  is *"nothing a viewer can see"*.
- `M123-robustness-mask.md`, `M89`, `M60`, `M28` refused the **outlier** mask
  four times. `robust.rs` (election-time) is a different module and has not been
  measured end-to-end through the CLI.
- `M107`/`M107b`/`M114` own lateral CA; `optics.rs:417-425` records a measured
  transfer split (95.0 % one way, 54.1 % the other against a 60 % bar) as the
  standing reason it is off.
- `M122` (live, unfolded) and `M125` own photometric normalisation.

**What is therefore genuinely new here, and all this milestone claims:**

| new | why it is new |
|---|---|
| `STREHL_FIX_CA` measured end-to-end through `stack` | M116 excluded it by dispatch |
| `STREHL_ROBUST_ELECTION` measured end-to-end through `stack` | unreachable at M116's SHA (its P12/P15); wired since |
| `STREHL_SMOOTH` measured **in a render** | M110 measured the solve and could not show a render effect |
| **interactions** — all-on, and drop-one-out from all-on | every prior milestone measured one gate alone |
| **drift stratification across 5 subjects** | M116 used 3, one of which (`foam`) it proved has no metric power |
| **per-tile dispersion and improved-fraction** | discipline 866, written *because* M116 gave none |
| `STREHL_FIX_HALO` measured at all | M116's P14: found, named, never measured |

Everything else in this report is a **replication** of M116 and is labelled so.

---

## 1. The gates under audit

| id | gate | how it is set | shipped state | owner |
|---|---|---|---|---|
| `CA` | lateral-CA correction | `STREHL_FIX_CA=a7c2-fe100gm-2xtc-x4cpl` | **OFF** (`optics.rs:476`) | M107/M114 — I measure, they rule |
| `ROB` | robust election | `STREHL_ROBUST_ELECTION=soft` | **OFF** (`merge.rs:525`) | mine |
| `SMO` | track-smoothness prior | `STREHL_SMOOTH=1` at **solve** time | **OFF** (`align_cmd.rs:539`) | mine |
| `SOFT` | soft admission gate | `STREHL_SOFT_GATE=gaussian` | **OFF** (`merge.rs:332`) | mine |
| `PHOT` | photometric normalisation | `--photometric` | **OFF** (`merge_cmd.rs:1296`) | **M122 + M125 — measured here only as part of the combined arms; I issue no photometric verdict** |
| `HALO` | halo correction | `STREHL_FIX_HALO=1` | **OFF** (`halo.rs:69`) | reconnaissance only, routed to M121 |
| `ALIGN` | registration | `STREHL_ALIGN=0` turns it **off** | **ON** (`align_cmd.rs:875`) | mine — the polarity is reversed |

`HALO` is a **seventh** dormant switch. The brief I was given lists six. It was
found by M116 (its P14) and never measured. I add it as a single alone-arm and
route the result to M121; it is **not** in the all-on or drop-one arms.

**This milestone writes no code under `crates/`.** No convenience flag is added.
Every arm is reachable from a shell today, which is the strongest form of the
"additive and off by default" requirement.

---

## 2. Subjects — 5, stratified by *measured* drift

Drift is `Dpp %`, the peak-to-peak per-frame level drift measured by **M122**
(`docs/research/M122-photometric-promotion.md`, table "stack | Dpp % | B12 |
…"). I did not estimate drift myself; I am stratifying on someone else's
measurement so the stratifier cannot be tuned by my results.

| subject | Dpp % | frames on disk | frames used | CA profile |
|---|---:|---:|---:|---|
| `bee-3-cpl` | 1.629 | 299 | 100 | **in-sample** (M107 fitted on it) |
| `lead-1-cpl` | 2.026 | 123 | 100 | out-of-sample |
| `leaf-2-cpl` | 5.315 | 182 | 100 | out-of-sample |
| `coffee-bean` | 12.065 | 105 | 100 | out-of-sample **and not a `-cpl` capture** |
| `tweezers-cpl` | 13.765 | 100 | 100 | **in-sample** (M107 fitted on it) |

`bee-3-cpl` and `tweezers-cpl` are mandated by the brief. `--limit 100` on all
five for comparability with M116 and V-M116, and because it fixes the worker
plan (see §6). **`foam` is deliberately excluded**: M116's P8 measured its mask
separation at `0.1249` dex against `1.1176` on bee, and its detail mask is
`56.27 %` noise, so every foam cell can only return INCONCLUSIVE. Re-running it
would manufacture three more null cells that mean nothing.

**Registered power floor.** A subject is *powered* only if its A0 mask
separation `Q(A0) >= 0.50` dex. The threshold is set from M116's published
values (bee `1.1176`, tweezers `0.8506`, foam `0.1249`) before I have seen any
of mine. An unpowered subject returns INCONCLUSIVE **by construction** and
contributes to no verdict.

---

## 3. The metric, exactly

Deliberately **M116's metric, unchanged**, so that (a) my numbers are directly
comparable to its 12 published arm-subject cells and (b) V-M116's independent
reimplementation — which reproduced it to five decimal places — already covers
my instrument. Changing it would buy a novelty I do not want.

Read with `tifffile` only. `PIL.Image.open` is never called on a pixel path.

1. `g` = plane 1 (green) of the **linear, camera-native, binned** 16-bit RGB
   TIFF that `stack --out` writes with **no `--srgb`**. Rendering in sRGB is
   forbidden by the brief and by `main.rs:112` — *"For looking at, NOT for
   measuring."*
2. `hp = g - box5(g)`, the plane extracted **before** any separable filter
   (rule 23).
3. `struct` = local sd of the **mask arm** at 4x downsample under a 33-box,
   nearest-upsampled. The mask arm is `--gate 0` (`M0`) and **is never itself
   compared**, so no mask is derived from an arm under test.
4. flat mask = `struct <= q(0.20)`; detail mask = `struct >= q(0.80)`.
5. `N = log10(sd(hp[flat]))`, `D = log10(sd(hp[detail]))`, **`Q = D - N`**.
6. Effect of an arm = `dQ = Q(arm) - Q(A0)`, and **`dD` and `dN` are printed
   beside it everywhere** — discipline 864 forbids a bare sharpness number.

**Which direction it can be fooled in** (rule 18). `D` rises both when detail is
preserved and when noise is retained: V-M116's fact 1700 measured `--gate 0`
patchwork out-scoring the gate-4 merge on `D` on 3 of 3 subjects. That is
exactly why the headline is `Q = D - N` and not `D`. `Q` in turn cancels a
global level change (M116 P7), so an arm that only rescales levels reads null on
it — which is correct behaviour, not blindness, but it must be said.

### 3b. Per-tile dispersion — required, not optional

Discipline 866 exists because a pooled win was carried by 25.8 % of tiles.

- 64x64 tiles on the plane grid.
- A tile is a **detail tile** if its mean `struct` (from the mask arm) is at or
  above the detail cut; a **flat tile** if at or below the flat cut.
- `dD_tile = log10(sd(hp_arm[tile])) - log10(sd(hp_A0[tile]))` over detail tiles;
  `dN_tile` likewise over flat tiles.
- Report, per arm per subject: **median, sd, and the improved fraction** —
  `frac(dD_tile > 0)` on detail tiles and `frac(dN_tile < 0)` on flat tiles.

### 3c. A second metric, because the first is provably blind to `CA`

`optics.rs:194-199` returns `None` for `Channel::Green` and `eps_b = None`, and
`optics.rs:341-348` states it outright: **"Only the red plane's gather changes —
a blast radius of one of four gathers."** A green-plane metric therefore
*cannot* see the CA gate. Registering this in advance turns a blind spot into a
control.

- `X_R = corr(hp_R, hp_G)` and `X_B = corr(hp_B, hp_G)` over detail-mask pixels.
- Split by field radius: **outer** `r > 0.6 r_max` (where a radial term has its
  lever arm) and **inner** `r < 0.3 r_max` (where it is near zero by
  construction).
- `X_B` is a **free placebo channel**: `eps_b = None`, so blue is not corrected
  and `X_B` must not move.
- The inner disc is a **second free placebo**: the same correction, at ~0 lever.

---

## 4. Arms

Aligned group. Registration is solved **once per subject** and frozen; every
aligned arm reads it through `STREHL_WARPMAP` pointed at my own scratch
(rule 45). `W0` = free solve. `W1` = `STREHL_SMOOTH=1` solve (M110's `lambda* =
1`, Huber 1.0 px).

| arm | sidecar | env / flags | role |
|---|---|---|---|
| `M0` | W0 | `--gate 0` | mask arm, never compared |
| `A0` | W0 | `--index-map` | **baseline 1 — the current default** |
| `N1` | W0 | — | null: A0 without the map. Must be SHA-equal to A0 (rule 26) |
| `G1` | W0 | `STREHL_FIX_CA=a7c2-fe100gm-2xtc-x4cpl` | CA alone |
| `G2` | W0 | `STREHL_ROBUST_ELECTION=soft` | robust alone |
| `G3` | **W1** | — | smooth alone |
| `G4` | W0 | `STREHL_SOFT_GATE=gaussian` | soft gate alone |
| `G5` | W0 | `--photometric` | photometric alone (**M122/M125's to rule on**) |
| `G6` | W0 | `STREHL_FIX_HALO=1` | halo alone — recon, routed to M121 |
| `ALL` | **W1** | CA + ROB + SOFT + PHOT | **all five on** |
| `D1` | W1 | ALL minus CA | drop-one |
| `D2` | W1 | ALL minus ROB | drop-one |
| `D3` | **W0** | ALL minus SMO | drop-one |
| `D4` | W1 | ALL minus SOFT | drop-one |
| `D5` | W1 | ALL minus PHOT | drop-one |
| `P1` | W0 | `STREHL_FIX_CA=0`, `STREHL_ROBUST_ELECTION=off`, `STREHL_SOFT_GATE=0`, `STREHL_SMOOTH=0` | **placebo** — every gate at its documented off-value |
| `P2` | W0 | `STREHL_ROBUST_ELECTION=ungated` | **placebo 2** — the whole robust ring runs; only the weight is barred from the argmax |
| `PC` | W0 | `--resampler nearest` | **positive control** — a known picture destroyer, via M124's flag |

Unaligned group. `STREHL_ALIGN=0`, no sidecar. Its own mask arm, because the
content is on a different registration even though the raster is the same size.

| arm | env | role |
|---|---|---|
| `M0u` | `STREHL_ALIGN=0`, `--gate 0` | mask arm for this group |
| `B1u` | `STREHL_ALIGN=0` | the merge with `ALIGN` **off** |
| `B0` | `STREHL_ALIGN=0`, one-frame directory | **baseline 2 — the sharpest single frame** |

`B0`'s frame is chosen as the index that wins the most pixels in `A0`'s election
map. That is a choice the pipeline makes, not a metric. V-M116 attacked exactly
this choice by rendering all 100 frames and found the picks rank 2/100, 1/100
and 5/100 — near-optimal, not flattering. I inherit that validation and do not
repeat the 500 renders.

**The gauge, stated in the sentence that travels** (fact 1699 is a defect
report about precisely this): *every* number comparing the merge to a single
frame in this report is measured with **alignment OFF on both sides**. The
aligned default is compared to a single frame only in the supplementary
`A0@u-masks` row, which is **not pixel-exact** and is labelled so at every use.

---

## 5. Bars, and the verdict rule

Bars are M116's, verbatim, plus a dispersion bar it did not have.

```
B1  NO DETAIL LOSS   dD >= -0.010 dex
B2  A REAL GAIN      dQ >= +0.010 dex
B3  MAJORITY         detail-tile improved fraction > 50 %
B4  ABOVE THE FLOOR  |dQ| >= 3 x max(|dQ| over P1, P2, N1)  and  |dQ| >= 0.010
```

**B4 is registered as expected-degenerate.** M116 measured its control floor at
exactly `0` and said so. If mine is also exactly 0 then `3 x 0 = 0` and B4
collapses onto B2. I am recording that prediction *now* so that reporting it
later is a confirmation and not an excuse (rule 30: assert the tolerated
disagreement at its expected wrong value).

Per gate, over the **powered** subjects:

```
PROMOTE         B1 & B2 & B3 on >= 3 of 5, AND dQ >= -0.010 on every powered subject
KEEP OFF        fails B2 on >= 3 of 5, OR fails B1 on any powered subject
NEEDS MORE DATA anything else, or fewer than 3 powered subjects
```

For `ALIGN`, whose shipped state is ON, the polarity inverts:

```
KEEP ON         turning it off costs dQ <= -0.010 on >= 3 of 5 powered subjects
DEMOTE          turning it off gains dQ >= +0.010 on >= 3 of 5
```

**The instrument must pass before any verdict is issued.** `P1`, `P2` and `N1`
must read `|dQ| <= 0.002` and `PC` must read `|dD| >= 0.010`. If `PC` reads null
the metric has no power on this corpus and **no verdict may be issued at all**
(rule 20: an instrument with no failing input is arithmetic, not evidence).

---

## 6. The starvation hazard, registered before it can be mistaken for a null

`merge.rs:540-556` warns that the robust ring needs a chunk of at least
`Z_WINDOW = 5` frames (`robust.rs:324`), that `chunk_len = frames.div_ceil(
workers)` comes from a *memory* budget that knows nothing about the statistic,
and that a starved run **renders a byte-identical image and reports every frame
elected**. It requires `window_starved_frames` to be reported beside any claim
about the gate.

On this box the plan line already read, in the §0 timing probe:
`workers : 13 chunks of <= 8 frames (13 allowed by the 6144 MB budget, 32 by CPU)`
at 100 frames — so `chunk_len = 8 >= 5`, the gate is not fully starved, and
`2 * Z_HALF * chunks = 2 * 2 * 13 = 52` of 100 frames are elected with `z = 0`
regardless.

**Registered consequence:** a null on `G2` is reportable as "the gate ran and did
nothing" **only** if `window_starved_frames` is strictly less than the frame
count. If it equals the frame count the correct report is "the gate did not run",
and it is a fact about the *worker plan*, not about the gate. I will print the
plan line and the starved count for every `G2`/`ALL`/`D2`/`P2` arm.

---

## 7. Predictions — direction and rough magnitude, written before any datum

A prediction written after the data is not a prediction. Each line below gets an
explicit **CONFIRMED / REFUTED** in the report. I expect to be wrong somewhere;
the project's measured bias is optimism and I am inside it.

| # | prediction | rough magnitude |
|---|---|---|
| **X1** | `CA`'s green plane is **bitwise identical** to A0's green plane, so `dQ` is exactly `0.000000` on the primary metric. Derived from `optics.rs:341-348`, not guessed. | exactly 0 |
| **X2** | `CA` **does** move the secondary metric on the two in-sample subjects: outer `X_R` rises. | `+0.002` to `+0.05` |
| **X3** | `CA` leaves `X_B` and the inner-disc `X_R` unmoved — the two free placebos. | `\|dX\| < 0.005` |
| **X4** | `CA` verdict: **KEEP OFF**, and *not on my evidence* — on `optics.rs`'s standing transfer split. My data cannot overturn it because 3 of 5 subjects are out-of-sample and one is not even a `-cpl` capture. | — |
| **X5** | `ROB` reads null. I expect `\|dQ\| < 0.002`, and I give it a **40 % chance of being SHA-identical to A0** outright. | ~0 |
| **X6** | `ROB` reports `window_starved_frames = 52` of 100 on every subject. | exactly 52 |
| **X7** | `SMO` reads null in the render — M110 said "nothing a viewer can see" and I expect that to replicate. Slight negative on `dD` if anything, because a smoothed track is a biased track. | `dD` in `[-0.010, +0.002]`, `\|dQ\| < 0.005` |
| **X8** | `SMO` shows **no** drift interaction: its effect does not rank-order with `Dpp %`. | Spearman `\|rho\| < 0.5` |
| **X9** | `SOFT` **replicates M116**: `dD` negative on the high-contrast subject, `dN` more negative still, `dQ` small positive and below bar. | bee `dD ~ -0.012 +/- 0.010`, `dN ~ -0.020`, `dQ` `+0.003` to `+0.012` |
| **X10** | `SOFT` verdict: **KEEP OFF**, failing B1 on at least one powered subject. | — |
| **X11** | `PHOT` replicates M116: never harmful, small positive, below bar. | `dQ` `+0.000` to `+0.010` |
| **X12** | `HALO` **loses detail** — M87 measured its own correction erasing the bee's abdomen hairs while its metric reported +72.9 %. | `dD <= -0.005` on `bee-3-cpl` |
| **X13** | `ALL` is **approximately additive**: every drop-one delta lands within `0.005` dex of the same gate's alone-effect. **No gate helps only in company.** | `\|additivity residual\| < 0.005` |
| **X14** | `ALL` fails B1 on `bee-3-cpl`, because `SOFT`'s detail loss survives the combination. | `dD < -0.010` |
| **X15** | `ALIGN` is the **only** gate that earns its default: turning it off costs `dQ <= -0.010` on at least 3 of 5. | large, `\|dQ\| > 0.05` |
| **X16** | The cost of turning `ALIGN` off **grows with drift**: Spearman `rho` between `Dpp %` and `-dQ(B1u)` is positive. | `rho > +0.5` |
| **X17** | **V-M116 fact 1701 replicates**: `Q(B1u) - Q(B0) < 0` on `tweezers-cpl` (its 0.37376 vs 0.84177) and `> 0` on `bee-3-cpl` (0.61255 vs 0.14585). | `~ -0.47` and `~ +0.47` |
| **X18** | Across all 5 subjects, `Q(B1u) - Q(B0)` **falls as drift rises**. | Spearman `rho < -0.5` |
| **X19** | Every pooled headline hides a minority: at least one arm with a positive pooled `dQ` has a detail-tile improved fraction **below 50 %**. | — |
| **X20** | The placebo floor is **exactly zero** — `P1`, `P2` and `N1` all SHA-identical to `A0` — so B4 degenerates onto B2, as it did for M116. | exactly 0 |
| **X21** | **No gate is promoted.** The overall verdict is that the owner's render is very nearly the best this build can do, and the remaining defect is not in these switches. | — |

**Bottom line prediction, stated so it can be shown wrong:** *the owner gains
essentially nothing by turning any of these on, and the one gate that is already
on is worth more than all six dormant ones put together.*

---

## 8. Reproduction

```powershell
git worktree add --detach C:\dev\strehl-out\M126-tree d5ba764de26fd9addd01c167c8d0f6c465f25fb4
cd C:\dev\strehl-out\M126-tree
& "$env:USERPROFILE\.cargo\bin\cargo.exe" build --release --target-dir C:\dev\strehl-out\M126\target

cd C:\dev\blog\death-of-software\projects\strehl\experiments\M126-default-audit
pwsh -File .\run.ps1        # every arm, every subject; ledger + logs
python .\pick_single.py     # the sharpest single frame, from A0's election map
pwsh -File .\run_single.ps1 # renders it
python .\score.py           # pooled + per-tile + chromatic -> scores.json
```

## 9. What this design cannot settle, stated in advance

- `--limit 100` on `bee-3-cpl` uses the first 100 of 299 frames — a third of the
  sweep, not the photograph the owner makes. Registered for comparability with
  M116; the report must not claim it is the owner's render.
- `Q` cancels a global level shift, so `PHOT`'s trivial half is invisible to it
  by design (M116 P7). This is one reason photometric is not mine to rule on.
- The CA profile names a **2x teleconverter**, and no metadata I can read
  confirms which stacks were shot through it. On out-of-sample subjects I am
  applying a profile whose optical path I cannot verify.
- 5 subjects is not a corpus. A Spearman `rho` on n = 5 needs `|rho| = 0.9` for
  `p < 0.05` one-sided; I will report `rho` with its exact permutation `p` and
  will call anything short of that **suggestive, not evidence**.
- Nothing here measures the halo or the waxy plateaus, which M116 P11 argued are
  what the owner is actually seeing.
