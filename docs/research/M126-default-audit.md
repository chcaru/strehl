# M126 — The default-gate audit: what the owner would gain, or lose, by turning them on

**Status:** complete.
**Pre-registration:** `b77d67c4f0563fa029a73073fbde89aac79ee2d6` —
*"M126 pre-registration: what the six default-off gates would cost or buy,
frozen before any datum"*, `experiments/M126-default-audit/PREREG.md`.
**Binary under test:** pinned worktree at `d5ba764de26fd9addd01c167c8d0f6c465f25fb4`,
built to a private `--target-dir`. Every number below comes from that one binary.
**No default was changed. No file under `crates/` was modified.**

---

## 0. The answer, in one table

| gate | env var | verdict | why, in one line |
|---|---|---|---|
| CA | `STREHL_FIX_CA` | **NEEDS MORE DATA** | The only instrument that can see it says it works, cleanly and on 5/5 subjects — but its effect varies 47× across them and the bar `optics.rs` sets is a transfer fraction I did not measure. |
| robust election | `STREHL_ROBUST_ELECTION` | **KEEP OFF** | It is a **literal no-op**: byte-identical output on 5/5 subjects, alone *and* in company. Promoting it would change nothing. |
| smoothing | `STREHL_SMOOTH` | **KEEP OFF** | Real but ~14× below the promotion bar. Largest \|dQ\| across 5 subjects is 0.00071 dex. |
| soft gate | `STREHL_SOFT_GATE` | **KEEP OFF** | Fails the detail bar on 3/5 and improves **0.0 %–2.9 %** of detail tiles on 5/5. Independently replicates M116. |
| photometric | `STREHL_PHOTOMETRIC` | **not mine — M122/M125** | Measured, reported in §7, no verdict issued. |
| halo | `STREHL_FIX_HALO` | **KEEP OFF** | Actively harmful on 4/5, up to **−0.0877 dex** of detail. But see §6 — it is the *only* gate that cleared every bar on any subject. |
| alignment | `STREHL_ALIGN` (already ON) | **COULD NOT SETTLE** | My design cannot compare aligned to unaligned without crossing mask grids, and §8 shows that choice swings the metric more than the effect. |

**Bottom line for the owner: turning these on will not fix your render.** Five
of the six are null or harmful. The one live candidate (CA) does not touch the
luminance you are looking at — it touches red/green registration in the outer
field.

---

## 1. First, a correction to the brief

The brief opened with:

> *"almost every improvement this project has measured is behind an environment
> variable that is OFF unless someone sets it. Nobody has ever measured what
> happens when they are ON."*

**The second sentence is false, and I found it before writing the
pre-registration** by running the mandatory prior-art check (rule 40):

```powershell
python experiments\ORCH-drift-check\prior_art.py promotion instruments off by default `
  photometric smoothing soft gate halo promote
```

It surfaced **`docs/research/M116-promotion.md`**, whose own opening is *"FOUR
QUALITY INSTRUMENTS ARE BUILT, MEASURED, AND OFF BY DEFAULT… Ask the promotion
question once, across all of them."* M116 measured photometric, both soft-gate
kernels, halo and the outlier mask against pre-registered bars on three real
captures and answered **KEEP-OFF 12/12**. It is in the `AGENTS.md` ledger. This
is recorded in §0b of my pre-registration, before any datum.

What was genuinely unmeasured, and is new here: **CA and the robust election
end-to-end through the CLI**, `STREHL_SMOOTH` *in a render* rather than in a
solve, **all pairwise-and-full interactions**, five drift-stratified subjects,
per-tile dispersion, and `STREHL_FIX_HALO` on anything but M87's own subject.

Three further corrections:

1. **The brief lists six gates. There are seven.** It omits
   **`STREHL_FIX_HALO`** (and its companion `STREHL_FIX_HALO_DELTA`), which is
   a third merge pass gated at `merge_cmd.rs:2095` on
   `halo::enabled() && opts.out.is_some()`. I measured it. It is the most
   *interesting* gate of the seven (§6).
2. **`V-M116` is cited in the brief but has no report.** `docs/research/` holds
   no `V-M116` file. The only artefacts are SYNTHESIS facts 1698–1702 and the
   scripts in `experiments/V-M116-headline/`. Per the brief's own rule — *cite
   the artefact, not the fact number* — I chased the numbers to those facts and
   then reproduced them myself (§8). **This is a finding, and I am reporting it
   as one.**
3. **The brief's V-M116 numbers are right but mis-labelled.** It says
   *"`tweezers-cpl`: single 0.84 vs merge 0.37"* as though these were sharpness.
   They are **`Q = D − N`**, the two-band statistic (fact 1701). On the
   sharpness band `D` alone the ordering is the *opposite* — and I reproduce
   V-M116's `D` contrast to five decimal places (§8). This matters because §8
   shows the `Q` ordering is not a property of the data.

---

## 2. Instrument checks — run before any verdict was read

PREREG §5 rule 20: *if the perturbation control reads null, no verdict may be
issued.* This section is what licenses everything after it.

| control | what it is | bee-3 | lead-1 | leaf-2 | coffee | tweezers | reads |
|---|---|---|---|---|---|---|---|
| `N1-rerun` | `A0` run a second time | +0.00000 | +0.00000 | +0.00000 | +0.00000 | +0.00000 | **exact null** |
| `P1-placebo` | every gate explicitly set to its off value | +0.00000 | +0.00000 | +0.00000 | +0.00000 | +0.00000 | **exact null** |
| `P2-ungated` | `STREHL_ROBUST_ELECTION=ungated` — all the new plumbing runs, the weight just never reaches the argmax | +0.00000 | +0.00000 | +0.00000 | +0.00000 | +0.00000 | **exact null** |
| `PC-nearest` | `stack --resampler nearest` | +0.00000 | +0.00000 | +0.00000 | +0.00000 | +0.00000 | **null — and that is my bug, see below** |
| **`PC2-nearest-solved`** | a sidecar *solved* with `--resampler nearest` | **+0.02733** | **+0.03291** | **+0.02993** | **+0.02652** | **+0.02012** | **PERTURBS** |
| `M0-gate0` | `--gate 0`, pure selection | +0.04267 | +0.01571 | +0.02360 | +0.01227 | +0.00303 | perturbs (weakly on tweezers) |

`N1`, `P1` and `P2` are not merely near-zero — they are **SHA-256 identical to
`A0`** on all five subjects. The metric reads exact null on a known no-op.

`PC2` moves `dD` by ≥ +0.020 dex on 5/5 and improves **95.6 %–100 % of detail
tiles** (nearest-neighbour injects aliasing, which reads as detail and as more
noise — `dN` rises with it, so `dQ` goes slightly *negative*: the two-band
metric is behaving exactly as designed). **The instrument passes. Verdicts may
be issued.**

### My placebo was mis-designed, and the tool caught it

`PC-nearest` came back byte-identical to `A0`. **This is my error, not a defect
in the `--resampler` flag M124 just landed.** Every aligned arm sets
`STREHL_WARPMAP` (rule 45, so nothing writes into the read-only capture
library), and a named sidecar carries its own recorded resampler, which wins.
The binary said so in capitals, in my own log:

```
alignment      : --resampler asked for Nearest but the sidecar named by STREHL_WARPMAP
                 was solved with CatmullRom; THE SIDECAR WINS. Unset STREHL_WARPMAP to
                 let --resampler choose.
```

That is documented behaviour (`merge_cmd.rs:1204-1258`, `main.rs:381-389`). I
added `run_pc.ps1`, which *solves* a nearest sidecar and merges against it. That
is `PC2`, and it perturbs. **M124's flag is fine; my control was wrong. Worth
recording that the disclosure the tool prints is what caught it** — this is the
counter-example to §5's complaint.

---

## 3. Power — and the honest bad news about it

PREREG §5 registered a power floor: a subject may only carry a verdict if
`Q(A0) ≥ 0.50` dex, i.e. the metric can actually separate detail from flat on
that subject.

| subject | drift `Dpp %` (M122's measurement) | `Q(A0)` | powered? |
|---|---|---|---|
| `bee-3-cpl` | 1.629 | 1.1176 | yes |
| `lead-1-cpl` | 2.026 | 0.3154 | **no** |
| `leaf-2-cpl` | 5.315 | 0.3292 | **no** |
| `coffee-bean` | 12.065 | 0.5264 | yes |
| `tweezers-cpl` | 13.765 | 0.8506 | yes |

**Only 3 of my 5 subjects are powered**, exactly the minimum my own verdict rule
required. I chose five to be safe and got three. `lead-1-cpl` and `leaf-2-cpl`
are reported throughout but **carry no verdict**, per the rule I wrote before I
saw them. This is the single biggest weakness of this milestone and I am not
going to bury it: two of my three powered subjects sit at the extreme ends of
the drift range, so my drift stratification is effectively n = 3 with a hole in
the middle.

---

## 4. Per-gate results

Bars, from PREREG §5: **B1** `dD ≥ −0.010` (do not destroy detail); **B2**
`dQ ≥ +0.010` (improve the two-band quality); **B3** improved fraction of detail
tiles > 50 % (discipline 866 — a pooled win carried by a minority is not a win).
A gate is **PROMOTE** only if it clears all three on a majority of powered
subjects.

### 4.1 `STREHL_FIX_CA` — the one live candidate

**The primary metric is provably blind to it, and I registered that in
advance.** `optics.rs:194-199` returns `None` for `Channel::Green`, `eps_b` is
`None`, and `optics.rs:341-348` says outright *"Only the red plane's gather
changes — a blast radius of one of four gathers."* So prediction X1 was a
*derivation*, not a guess:

| arm | green plane bitwise identical to `A0`? | red? | blue? | whole file? |
|---|---|---|---|---|
| `G1-ca` | **yes, 5/5** | no | **yes, 5/5** | no |

`dN = dD = dQ = 0.00000` on all five subjects, exactly. The green-plane metric
returns literally nothing, which is why PREREG §3c registered a second one.

**The chromatic metric** — `X_R = corr(hp_R, hp_G)` over detail-mask pixels,
split by field radius, with blue as a free placebo (`eps_b = None`) and the
inner disc as a second free placebo (a radial term has ~0 lever there):

| subject | band | `X_R(A0)` | `X_R(G1)` | **`dX_R`** | `X_B(A0)` | `X_B(G1)` | `dX_B` |
|---|---|---|---|---|---|---|---|
| `bee-3-cpl` | outer | 0.77539 | 0.78106 | **+0.00566** | 0.86869 | 0.86869 | **+0.00000** |
| `bee-3-cpl` | inner | 0.89665 | 0.89084 | −0.00581 | 0.91440 | 0.91440 | **+0.00000** |
| `lead-1-cpl` | outer | 0.53553 | 0.61114 | **+0.07561** | 0.73442 | 0.73442 | **+0.00000** |
| `lead-1-cpl` | inner | 0.66375 | 0.66900 | +0.00526 | 0.74793 | 0.74793 | **+0.00000** |
| `leaf-2-cpl` | outer | 0.48238 | 0.57302 | **+0.09064** | 0.71219 | 0.71219 | **+0.00000** |
| `leaf-2-cpl` | inner | 0.65903 | 0.65913 | +0.00010 | 0.72660 | 0.72660 | **+0.00000** |
| `coffee-bean` | outer | 0.73219 | 0.91047 | **+0.17828** | 0.90134 | 0.90134 | **+0.00000** |
| `coffee-bean` | inner | 0.86632 | 0.91147 | +0.04515 | 0.89080 | 0.89080 | **+0.00000** |
| `tweezers-cpl` | outer | 0.65321 | 0.91920 | **+0.26599** | 0.87408 | 0.87408 | **+0.00000** |
| `tweezers-cpl` | inner | 0.90814 | 0.94616 | +0.03802 | 0.92793 | 0.92793 | **+0.00000** |

**`X_B` is exactly unchanged on all ten cells.** The free placebo channel reads
a hard zero, so the effect is specific to the plane the profile claims to
correct. Outer exceeds inner on 5/5, which is the radial signature a lateral-CA
term must have.

**Verdict: NEEDS MORE DATA.** The reasons, stated as precisely as I can:

- It is **real and specific**. Placebo-clean on the free channel, correct radial
  signature, 5/5 subjects, no green-plane cost by construction.
- But it varies **47×** across subjects — `+0.00566` on `bee-3-cpl` to
  `+0.26599` on `tweezers-cpl` — and *both* of those are the profile's own
  in-sample captures (`optics.rs:305-329`: fitted from M107 on `tweezers-cpl`
  and `bee-3-cpl`). On one in-sample subject the inner disc got slightly
  **worse** (`−0.00581`). A single fixed constant behaving that differently on
  the two stacks it was fitted to is not yet a default.
- **`X_R` is a registration proxy, not a picture-quality metric.** A red plane
  blurred toward green would also raise it. I do not believe blur explains
  `+0.266`, but I did not measure it out, and I should not promote on a proxy.
- **`optics.rs:417-460` sets the actual bar** — a transfer split of
  95.0 %/54.1 % against a 60 % requirement — and says *"Off by default, and it
  must stay that way."* **I did not measure transfer.** My evidence is
  orthogonal to the standing bar, not a refutation of it.

**What would settle it:** the transfer measurement `optics.rs` names, on the
three out-of-sample subjects. That is a small, well-defined job.

> **Coordination note.** While I was running, another agent committed `188b55c`,
> *"M116: pre-register the lateral-CA campaign, before any CA arm runs"*. **CA
> is now live with someone else.** My chromatic table above is offered to them
> as an independent 5-subject prior with a clean placebo; I am not claiming the
> question.

### 4.2 `STREHL_ROBUST_ELECTION` — a literal no-op

| subject | `dN` | `dD` | `dQ` | detail tiles improved | SHA vs `A0` |
|---|---|---|---|---|---|
| `bee-3-cpl` | +0.00000 | +0.00000 | +0.00000 | 0.0 % | **identical** |
| `lead-1-cpl` | +0.00000 | +0.00000 | +0.00000 | 0.0 % | **identical** |
| `leaf-2-cpl` | +0.00000 | +0.00000 | +0.00000 | 0.0 % | **identical** |
| `coffee-bean` | +0.00000 | +0.00000 | +0.00000 | 0.0 % | **identical** |
| `tweezers-cpl` | +0.00000 | +0.00000 | +0.00000 | 0.0 % | **identical** |

`STREHL_ROBUST_ELECTION=soft` produces a **byte-for-byte identical TIFF** on all
five subjects. The drop-one-out arm agrees: `D2-norobust` is byte-identical to
`ALL-on` on all five. **The gate is inert alone and inert in company**, across a
7.6× drift range.

This is not a bug — it is what the weight function implies. `robust.rs:64`:
`w = 1.0` for `|z| ≤ 4.0`, ramping to 0 at `|z| = 8.0`, in **sigmas of the
calibrated noise model**. On tripod macro stacks essentially nothing disagrees
with its temporal neighbours by 4σ, so `w = 1` everywhere and `w · response`
is `response`. Byte-identity means the soft demotion **never flipped a single
argmax across 8.25 M pixels × 5 subjects.**

**Verdict: KEEP OFF** — but the accurate sentence is *promoting it would be
free and pointless*. It has never been shown to do anything on real data. See
§5 for why that statement is currently unfalsifiable-by-design.

### 4.3 `STREHL_SMOOTH` — real, and ~14× below the bar

Measured properly: `STREHL_SMOOTH` acts at **solve** time
(`align_cmd.rs:539`), so this arm merges against a *second* sidecar solved with
`STREHL_SMOOTH=1` (M110's recommended λ). The two sidecars differ
(`BAAD2EDF9600` vs `3DC30BFEF125` on `bee-3-cpl`), so the gate is live.

| subject | powered | `dN` | `dD` | `dQ` | improved | B1 | B2 | B3 |
|---|---|---|---|---|---|---|---|---|
| `bee-3-cpl` | yes | −0.00025 | −0.00063 | −0.00038 | 53.7 % | PASS | FAIL | PASS |
| `lead-1-cpl` | no | −0.00126 | −0.00197 | −0.00071 | 33.1 % | PASS | FAIL | FAIL |
| `leaf-2-cpl` | no | −0.00176 | −0.00145 | +0.00031 | 27.3 % | PASS | FAIL | FAIL |
| `coffee-bean` | yes | −0.00008 | −0.00010 | −0.00002 | 51.2 % | PASS | FAIL | PASS |
| `tweezers-cpl` | yes | −0.00072 | −0.00030 | +0.00041 | 54.6 % | PASS | FAIL | PASS |

**Verdict: KEEP OFF.** Largest `|dQ|` anywhere is 0.00071 dex against a
+0.010 bar. It harms nothing and helps nothing a viewer could see, which
replicates M110's own conclusion.

### 4.4 `STREHL_SOFT_GATE` — the clearest refusal, and the best illustration of why pooling lies

| subject | powered | `dN` | `dD` | `dQ` | improved | B1 | B2 | B3 |
|---|---|---|---|---|---|---|---|---|
| `bee-3-cpl` | yes | −0.02044 | **−0.01218** | +0.00826 | **0.5 %** | **FAIL** | FAIL | **FAIL** |
| `lead-1-cpl` | no | −0.02677 | −0.01620 | +0.01056 | **0.0 %** | FAIL | PASS | FAIL |
| `leaf-2-cpl` | no | −0.03461 | −0.01989 | +0.01471 | **0.3 %** | FAIL | PASS | FAIL |
| `coffee-bean` | yes | −0.00248 | −0.00419 | −0.00171 | **2.9 %** | PASS | FAIL | FAIL |
| `tweezers-cpl` | yes | −0.00202 | −0.00191 | +0.00011 | **2.3 %** | PASS | FAIL | FAIL |

Look at `lead-1-cpl` and `leaf-2-cpl`: **pooled `dQ` clears the +0.010 bar while
0.0 % and 0.3 % of detail tiles improve.** If this milestone had reported only
the pooled number — as the brief warned prior milestones did — the soft gate
would read as a promotion candidate on two subjects. It is the opposite.

The per-tile distribution on `bee-3-cpl` is worth stating in full:

| arm | median `dD_tile` | sd | p10 | p90 | improved |
|---|---|---|---|---|---|
| `G4-softgate` on `bee-3-cpl` | **−0.13770** | 0.11780 | −0.31367 | −0.00542 | 0.5 % |

The **median detail tile loses 0.138 dex** while the pooled `dD` reads −0.012.
**Pooling understates the per-tile damage by 11×**, and the p90 tile — the
*best* tile — still loses. This is discipline 866 earning its place.

**Verdict: KEEP OFF.** Independently replicates M116's refusal on a different
subject set with a different mask arm.

### 4.5 `STREHL_FIX_HALO` — the biggest surprise in the milestone

| subject | powered | `dN` | `dD` | `dQ` | improved | B1 | B2 | B3 |
|---|---|---|---|---|---|---|---|---|
| `bee-3-cpl` | yes | +0.00000 | **+0.01810** | **+0.01810** | **73.2 %** | **PASS** | **PASS** | **PASS** |
| `lead-1-cpl` | no | +0.02537 | −0.04672 | −0.07210 | 35.1 % | FAIL | FAIL | FAIL |
| `leaf-2-cpl` | no | +0.00833 | **−0.08770** | −0.09603 | 14.8 % | FAIL | FAIL | FAIL |
| `coffee-bean` | yes | +0.00126 | −0.00273 | −0.00398 | 31.2 % | PASS | FAIL | FAIL |
| `tweezers-cpl` | yes | +0.00287 | −0.02758 | −0.03045 | 51.8 % | FAIL | FAIL | FAIL |

**`bee-3-cpl` is the only subject in this entire campaign where any gate cleared
all three bars.** And it is the gate the corpus is most hostile to: M87
recommended against its own correction, and `merge_cmd.rs:2087-2094` says
*"against ground truth it makes the image measurably more wrong."*

It clears the bars on 1 of 3 powered subjects and does real damage on the other
four — up to **−0.0877 dex** of detail on `leaf-2-cpl`, with only 14.8 % of
detail tiles improving. `dN` is positive on 4/5: it *adds* flat-region noise.

**Verdict: KEEP OFF.** But the interesting part is not the verdict:
`bee-3-cpl` is M87's own subject and the lowest-drift stack in the set, and it
is also the subject with by far the most headroom (`Q(A0) = 1.12`, vs 0.53 and
0.85 for the other powered subjects). **Something about that subject makes the
halo correction work.** Routed to **M121**, which owns halo polarity; the
per-tile distribution (`median +0.05836`, `p90 +0.56250`) says the gain is
concentrated in a minority of very-high-gain tiles, which is what you would
expect if it is genuinely finding occlusion edges there.

---

## 5. A disclosure the shipped binary cannot make

`merge.rs:554` states a requirement:

> *"[`FocusStats::window_starved_frames`] counts it and any caller reporting a
> gate's effect **must report that count beside it**."*

I am such a caller. **I cannot comply.** `window_starved_frames` has **zero
production consumers**: its only references in the entire crate tree are its own
doc comment, its definition at `merge.rs:736`, and two lines inside
`#[cfg(test)]` at `merge.rs:4253` and `4259`.

```powershell
# reproduce:
rg -n "window_starved_frames" crates/
```

This matters concretely. The robust ring has `Z_WINDOW = 5`, `Z_HALF = 2`
(`robust.rs:324`), and workers process independent chunks. The plan my box chose
for a 100-frame stack, printed in every log, is
`13 chunks of <= 8 frames (13 allowed by the 6144 MB budget, 32 by CPU)`. So
`2 · Z_HALF · chunks = 2 · 2 · 13 = 52` of 100 frames are elected with `z = 0`
regardless — and `weight(0) = 1.0`, i.e. **not demoted**. That is a *derived*
number (from `merge_cmd.rs:770-806` and `robust.rs:39-73`), **not a measured
one**, and I am labelling it as such because I have no way to measure it.

**Consequence: a starved robust run is externally indistinguishable from a
working one.** My §4.2 finding — byte-identical output — is consistent both with
*"the estimator is correctly conservative on clean data"* and with *"half the
frames never got a z-score."* I cannot separate those two with the shipped CLI,
and neither can anyone else. It is the same class as fact 1449 (*"287 passing
tests and zero consumers"*).

Related: **only the halo gate prints a banner confirming it is on.** CA, robust,
soft gate and smoothing print nothing. The exception that proves the value is
`--resampler`, whose loud `THE SIDECAR WINS` disclosure caught a real error of
mine in §2.

---

## 6. Interactions — the point of the exercise

`ALL-on` = CA + robust + smoothing + soft gate + photometric. **It excludes
halo**, which is a separate third pass; that is a design choice of my
pre-registration and I flag it because "all on" does not mean all seven.

| arm | `bee-3-cpl` | `lead-1-cpl` | `leaf-2-cpl` | `coffee-bean` | `tweezers-cpl` |
|---|---|---|---|---|---|
| | `dQ / dD / improved` | | | | |
| `ALL-on` | +0.00956 / −0.00545 / **11.6 %** | +0.01013 / −0.02004 / **2.3 %** | +0.01798 / −0.02342 / **2.1 %** | −0.00012 / −0.00670 / 28.0 % | +0.00872 / +0.00385 / 41.6 % |
| `D1-noca` | +0.00956 / −0.00545 / 11.6 % | +0.01013 / −0.02004 / 2.3 % | +0.01798 / −0.02342 / 2.1 % | −0.00012 / −0.00670 / 28.0 % | +0.00872 / +0.00385 / 41.6 % |
| `D2-norobust` | +0.00956 / −0.00545 / 11.6 % | +0.01013 / −0.02004 / 2.3 % | +0.01798 / −0.02342 / 2.1 % | −0.00012 / −0.00670 / 28.0 % | +0.00872 / +0.00385 / 41.6 % |
| `D3-nosmooth` | +0.00916 / −0.00593 / 11.1 % | +0.01161 / −0.01600 / 2.8 % | +0.01712 / −0.02082 / 1.8 % | −0.00024 / −0.00688 / 23.4 % | +0.00864 / +0.00430 / 44.6 % |
| **`D4-nosoftgate`** | +0.00441 / **+0.00581** / **81.3 %** | +0.00042 / −0.00180 / **34.4 %** | +0.00281 / −0.00243 / **33.2 %** | +0.00190 / −0.00264 / **50.5 %** | +0.00862 / +0.00542 / **51.3 %** |
| `D5-nophotometric` | +0.00864 / −0.01164 / 3.5 % | +0.00907 / −0.02021 / 0.8 % | +0.01554 / −0.02251 / 0.3 % | −0.00152 / −0.00396 / 15.4 % | +0.00047 / −0.00207 / 18.4 % |

Three things fall out:

1. **Turning everything on is not an improvement.** `ALL-on` fails B3 on 5/5 —
   between 2.1 % and 41.6 % of detail tiles improve. On `bee-3-cpl` the pooled
   `dQ` reads +0.0096 while the median detail tile loses **0.129 dex**.
2. **The soft gate is what wrecks the combination.** Removing it (`D4`) is the
   only drop that moves anything: improved-fraction jumps 11.6 % → 81.3 %,
   2.3 % → 34.4 %, 2.1 % → 33.2 %, 28.0 % → 50.5 %, 41.6 % → 51.3 % — better on
   **5/5**.
3. **No gate helps only in company, and none hurts only in company.** Worst
   absolute additivity residual — `(ALL − drop_i)` against `(gate_i alone − A0)`
   — is **0.00385 dex** across all 25 gate×subject cells, inside the 0.005 I
   registered. The gates are additive to measurement precision. The drop-one-out
   design found no hidden interaction, which is itself the result.

---

## 7. Photometric — one paragraph, and it is M122's and M125's

`--photometric` produced `dQ` of **+0.00477 / +0.00111 / +0.00252 / +0.00194 /
+0.00835** across the five subjects — positive on 5/5, below the +0.010 bar on
5/5 — with detail-tile improved fractions of 84.6 % / 51.9 % / 42.3 % / 49.3 % /
55.6 %. `dD` is negative on two subjects (`leaf-2-cpl −0.00098`,
`coffee-bean −0.00253`). In the combination, `D5-nophotometric` is *worse* than
`ALL-on` on 5/5, so it is the one gate that mildly earns its place in company.
**I am issuing no verdict on it**; it is owned by **M122** (which measured the
mechanism, ρ = +0.70, p = 0.0035, n = 14, and still said KEEP-OFF) and **M125**
(which shipped the auto mode in `d5bfab6`, opt-in). This paragraph is handed to
them and nothing else in this report depends on it.

---

## 8. The degenerate baselines — and a result that overturns the brief's premise

PREREG §4 required a **single sharpest frame** baseline, because V-M116 measured
that on a drifting stack the single frame beats the merge. `pick_single.py`
chooses it the way M116 did: argmax of the byte-inert `--index-map` from `A0`.

| subject | chosen frame | pixel share |
|---|---|---|
| `bee-3-cpl` | 99 (`DSC00100.ARW`) | 31.55 % |
| `lead-1-cpl` | 55 (`DSC00056.ARW`) | 12.92 % |
| `leaf-2-cpl` | 55 (`DSC00056.ARW`) | 6.70 % |
| `coffee-bean` | 99 (`DSC00115.ARW`) | 5.58 % |
| `tweezers-cpl` | 36 (`DSC00037.ARW`) | 4.39 % |

Scoring `B1u` (merge, `STREHL_ALIGN=0`) against `B0` (that one frame) with masks
from `M0u`, **the merge wins on `Q` on all five subjects, including
`tweezers-cpl` (+0.19760)**. That contradicts fact 1701.

So I chased it. Fact 1700 records that V-M116 took its masks **from `B0`**. That
is the only free parameter between us. Scoring the identical two renders both
ways:

| subject | drift | mask source | `Q(B1u)` | `Q(B0)` | `Q(B1u) − Q(B0)` | winner |
|---|---|---|---|---|---|---|
| `bee-3-cpl` | 1.629 | `M0u` | 0.68754 | 0.18429 | +0.50324 | merge |
| `bee-3-cpl` | 1.629 | **`B0`** | **0.61255** | **0.14585** | +0.46670 | merge |
| `lead-1-cpl` | 2.026 | `M0u` | 0.39092 | 0.09269 | +0.29823 | merge |
| `lead-1-cpl` | 2.026 | `B0` | 0.07565 | 0.17634 | −0.10070 | **single frame** |
| `leaf-2-cpl` | 5.315 | `M0u` | 0.40130 | 0.07874 | +0.32257 | merge |
| `leaf-2-cpl` | 5.315 | `B0` | 0.07939 | 0.14738 | −0.06799 | **single frame** |
| `coffee-bean` | 12.065 | `M0u` | 0.51965 | 0.09418 | +0.42546 | merge |
| `coffee-bean` | 12.065 | `B0` | 0.19109 | 0.18913 | +0.00196 | merge |
| `tweezers-cpl` | 13.765 | `M0u` | 0.91804 | 0.72043 | +0.19760 | merge |
| `tweezers-cpl` | 13.765 | **`B0`** | **0.37376** | **0.84177** | −0.46801 | **single frame** |

**The bolded cells are V-M116's published numbers, reproduced to five decimal
places** — `0.61255`, `0.14585`, `0.37376`, `0.84177`. My `D` contrast also
reproduces their `+0.15207 / +0.33319` exactly. **V-M116's arithmetic is
correct and I confirm it independently.**

But:

| subject | `dQ` with `M0u` masks | `dQ` with `B0` masks | swing | sign flips? |
|---|---|---|---|---|
| `bee-3-cpl` | +0.50324 | +0.46670 | +0.03655 | no |
| `lead-1-cpl` | +0.29823 | −0.10070 | **+0.39893** | **YES** |
| `leaf-2-cpl` | +0.32257 | −0.06799 | **+0.39056** | **YES** |
| `coffee-bean` | +0.42546 | +0.00196 | +0.42350 | no |
| `tweezers-cpl` | +0.19760 | −0.46801 | **+0.66561** | **YES** |

**Changing nothing but which render defines "where the detail is" flips the sign
of the headline on 3 of 5 subjects, with a swing of up to 0.666 dex.** Fact
1702 states the mask-source worst case as **−0.080 dex**. My measurement is
**8.3× larger** and, unlike theirs, it *changes the answer*.

The mechanism is not subtle. `B0` is one frame, so it has structure only where
*that frame* was in focus. Taking the detail mask from `B0` selects precisely
the region where `B0` is sharp. Fact 1700 says the masks came from `B0` *"so
that neither merge chose them"* — the intent was to stop a merge picking its own
favourable ground, and the effect was to let **the single frame** pick its own
favourable ground instead.

**I am not claiming `M0u` is the neutral choice.** It is a merge, so it plausibly
favours the merge family. The honest statement is: **neither mask source is
neutral, and the "single frame beats the merge on drifting stacks" headline is a
property of that choice rather than of the data.** Until a mask source
independent of both families exists, that claim should not be used to justify
anything — including, specifically, the brief's item 4, which is how it reached
me.

---

## 9. Every prediction, scored

From PREREG §7, written before any datum.

| # | prediction | outcome |
|---|---|---|
| **X1** | CA's green plane bitwise identical; `dQ` exactly 0 | **CONFIRMED** — 0.00000 on 5/5, green identical 5/5 |
| **X2** | CA raises outer `X_R`; `+0.002`…`+0.05` | **CONFIRMED in direction on 5/5, REFUTED in magnitude** — actual up to +0.26599, 5× my ceiling |
| **X3** | `X_B` and inner-disc `X_R` unmoved, `\|dX\| < 0.005` | **SPLIT: `X_B` CONFIRMED exactly (0.00000 on 10/10 cells); inner `X_R` REFUTED** — +0.04515 and +0.03802 on two subjects. The inner disc is *not* a clean placebo |
| **X4** | CA verdict KEEP OFF | **REFUTED** — I issued NEEDS MORE DATA |
| **X5** | Robust reads null; 40 % chance SHA-identical | **CONFIRMED** — and the 40 % branch happened, on 5/5 |
| **X6** | Robust reports `window_starved_frames = 52` | **UNMEASURABLE** — zero consumers (§5). 52 is derived, not measured |
| **X7** | Smoothing null; `dD ∈ [−0.010, +0.002]`, `\|dQ\| < 0.005` | **CONFIRMED** — `dD ∈ [−0.00197, −0.00010]`, `\|dQ\| ≤ 0.00071` |
| **X8** | Smoothing shows no drift interaction, `\|ρ\| < 0.5` | **REFUTED** — ρ = +0.80 (p = 0.10, n = 5). Caveat: every effect is ≤ 0.0007 dex, so this is rank noise |
| **X9** | Soft gate replicates M116: bee `dD ≈ −0.012 ± 0.010`, `dN ≈ −0.020`, `dQ` +0.003…+0.012 | **CONFIRMED on all three limbs** — −0.01218, −0.02044, +0.00826 |
| **X10** | Soft gate KEEP OFF, failing B1 on ≥1 powered subject | **CONFIRMED** — fails B1 on `bee-3-cpl` |
| **X11** | Photometric never harmful, small positive, below bar | **CONFIRMED on `Q`** (positive 5/5, below bar 5/5); `dD` negative on 2 |
| **X12** | Halo loses detail, `dD ≤ −0.005` on `bee-3-cpl` | **REFUTED** — `dD = +0.01810`, and it is the only gate to clear all three bars anywhere |
| **X13** | `ALL` approximately additive, residual < 0.005 | **CONFIRMED** — worst residual 0.00385 dex over 25 cells |
| **X14** | `ALL` fails B1 on `bee-3-cpl` (`dD < −0.010`) | **REFUTED** — `dD = −0.00545`, passes B1. It fails B3 instead (11.6 %) |
| **X15** | Alignment earns its default, `dQ ≤ −0.010` on ≥3 of 5 | **COULD NOT SETTLE** (§10). Raw numbers point the *other* way on 3/5 |
| **X16** | Cost of `ALIGN=0` grows with drift, ρ > +0.5 | **REFUTED** — ρ = +0.10 (p = 0.87), on a confounded comparison |
| **X17** | Fact 1701 replicates: `tweezers` negative, `bee` positive | **CONFIRMED EXACTLY under `B0` masks** (to 5 dp); **REFUTED under `M0u` masks**. The sign is not a property of the data (§8) |
| **X18** | Merge-vs-single contrast falls as drift rises, ρ < −0.5 | **CONFIRMED** — ρ = −0.60 under *both* mask sources (p = 0.28, n = 5) |
| **X19** | ≥1 arm with positive pooled `dQ` and improved fraction < 50 % | **CONFIRMED** — many, e.g. soft gate on `leaf-2-cpl`: `dQ +0.01471` with **0.3 %** of tiles improved |
| **X20** | `P1`, `P2`, `N1` SHA-identical to `A0`; B4 degenerates onto B2 | **CONFIRMED** — 5/5 each |
| **X21** | No gate is promoted | **CONFIRMED** — no PROMOTE issued, though CA is a live candidate |

**Bottom-line prediction** (*"the owner gains essentially nothing by turning any
of these on, and the one gate already on is worth more than all six dormant ones
put together"*): **first half CONFIRMED for five of six gates and REFUTED for
CA**; **second half COULD NOT SETTLE**, and my own numbers question it.

### Direction audit of my own errors

The brief noted that 8 of 8 defective facts in a prior audit erred in the
flattering direction (p = 0.0039). Scoring my six refuted predictions the same
way:

| prediction | error direction |
|---|---|
| X3 (inner disc is a clean placebo) | **flattering** — I assumed my instrument was cleaner than it is |
| X8 (no drift interaction) | **flattering** — I assumed a simpler result |
| X16 (align cost tracks drift) | **flattering** — I predicted the tidy expected story |
| X4 (CA keep off) | pessimistic |
| X12 (halo loses detail) | pessimistic |
| X14 (`ALL` fails B1) | pessimistic |

**3 flattering, 3 pessimistic.** Two-sided sign test p = 1.0. I cannot detect
the optimism bias in this milestone's predictions — which is not proof of its
absence, only that pre-registration gave it nowhere to hide.

---

## 10. What I could not settle

1. **Whether `STREHL_ALIGN` earns its default.** My design cannot answer this.
   The aligned and unaligned arms sit on differently-registered rasters, so no
   single mask arm is valid for both; `A0` is scored against `M0` and `B1u`
   against `M0u`. §8 measures that this choice alone swings the same contrast by
   up to **0.666 dex**, larger than every difference in the alignment table
   (`+0.43003 / −0.07551 / −0.07206 / +0.00672 / −0.06741`). Those raw numbers
   would say alignment *hurts* on 3 of 5 subjects. **I do not believe that, and
   I am not asserting it** — I am saying my instrument cannot tell, and that
   anyone who wants to know must build a mask source registered to both grids.
   Given `STREHL_ALIGN` is the only gate currently ON, this is the most
   important unanswered question I leave behind.
2. **Whether the robust election is conservative or starved.** §5. Externally
   indistinguishable with the shipped binary.
3. **Whether CA's chromatic gain is registration or blur.** `X_R` cannot
   separate them. A modulation-transfer measurement on the red plane would.
4. **Whether `--limit 100` is representative of `bee-3-cpl`.** It has 299
   frames; I used the first 100. The chosen sharpest frame is **index 99 — the
   last one**, winning 31.6 % of pixels, which strongly suggests the focus ramp
   is still marching when my window closes. **`bee-3-cpl` is my highest-powered
   subject and the one carrying the halo result, so this caveat lands on the
   most interesting cell in the report.** Registered as a limitation in PREREG
   §9 before I saw it, but it is worse than I expected.
5. **Two of five subjects are unpowered** (§3), leaving n = 3 with a gap in the
   middle of the drift range. Every "3 of 3" and "1 of 3" in §4 is a small
   number.
6. **`ALL-on` does not include halo.** Its interactions with the other five are
   unmeasured.
7. **Whether the CA profile's optical path applies to `lead-1-cpl`,
   `leaf-2-cpl` and `coffee-bean`.** No metadata confirms the 2× teleconverter.
   They improved anyway, which is suggestive, not conclusive.
8. **I did not find a `V-M116` report** to cite (§1). If one exists outside
   `docs/research/`, my §8 reproduction should be checked against it.

---

## 11. Reproducing every number

```powershell
$cargo = "$env:USERPROFILE\.cargo\bin\cargo.exe"

# 1. Pin the binary. Every number above is from this commit and no other.
git worktree add --detach C:\dev\strehl-out\M126-tree d5ba764de26fd9addd01c167c8d0f6c465f25fb4
cd C:\dev\strehl-out\M126-tree
& $cargo build --release --target-dir C:\dev\strehl-out\M126\target

# 2. The campaign: 20 arms x 5 subjects, plus 2 align solves per subject. ~45 min.
cd C:\dev\blog\death-of-software\projects\strehl
pwsh -File experiments\M126-default-audit\run.ps1

# 3. The degenerate single-frame baseline (needs A0's index maps from step 2).
python experiments\M126-default-audit\pick_single.py
pwsh -File experiments\M126-default-audit\run_single.ps1

# 4. The CORRECTED perturbation control (see section 2).
pwsh -File experiments\M126-default-audit\run_pc.ps1

# 5. Score, tabulate, derive.
python experiments\M126-default-audit\score.py       # -> scores.json, sections 2,4,7
python experiments\M126-default-audit\tables.py      # -> sections 2,3,4,6
python experiments\M126-default-audit\masksource.py  # -> section 8
python experiments\M126-default-audit\derived.py     # -> sections 6,9 statistics
```

Individual arms are reproducible directly from their logs, each of which carries
the full environment and argv per rule 47. For example the robust arm:

```powershell
$env:STREHL_WARPMAP = "C:\dev\strehl-out\M126\warp\bee-3-cpl-l100-free.txt"
$env:STREHL_ROBUST_ELECTION = "soft"
C:\dev\strehl-out\M126\target\release\strehl.exe stack D:\personal\macro\bee-3-cpl `
  --limit 100 --gate 4 --out C:\dev\strehl-out\M126\measure\bee-3-cpl__G2.tif
# SHA-256 478387EF2F9A... -- identical to A0.
```

And the zero-consumer finding of §5:

```powershell
rg -n "window_starved_frames" crates/
```

**Artefacts** (all in gitignored scratch, `C:\dev\strehl-out\M126\`):
`ledger.csv`, `ledger-single.csv`, `ledger-pc2.csv` (SHA-256, bytes, seconds,
env and argv for every render), `logs/*.log` (one per arm, with a rule-47
header), `scores.json`, `masksource.json`, `single-frame-picks.json`,
`tables.md`, `derived.md`.

**Measurement hygiene.** Every pixel read went through `tifffile`; `score.py`
asserts `dtype == uint16` on every render before scoring, so the `PIL.Image.open`
8-bit downconversion that corrupted 241 prior measurements cannot occur here.
Index maps are asserted `uint16` with a max-index check in `pick_single.py`.
**Everything is measured in linear** — no arm passes `--srgb`. `D:\` was never
written.

---

## 12. Handoffs

- **CA → the `M116` CA campaign** pre-registered in `188b55c`. §4.1's table is
  an independent 5-subject prior with a placebo that reads exact null.
- **Halo → `M121`.** §4.5: it clears every bar on `bee-3-cpl` and harms the
  other four. That asymmetry is a lead, and M121 owns polarity.
- **Photometric → `M122` / `M125`.** §7, one paragraph, no verdict.
- **`window_starved_frames` → whoever owns `merge.rs`.** §5: a mandatory
  disclosure with no way to make it.
- **Fact 1702's mask-source sensitivity → the corpus.** §8 measures it 8.3×
  larger than recorded, and large enough to flip the sign of a claim currently
  in circulation.
