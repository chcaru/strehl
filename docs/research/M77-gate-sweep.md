# M77 — the spatial gate sweep: what opening the gate buys, and what it spends

**Status: measured. Every pre-registered per-stack verdict is INDETERMINATE, by
a control that failed, and the consequence registered for that failure is
honoured rather than argued around.**

Pre-registration: `experiments/M77-gate-sweep/PREREGISTRATION.md`, committed at
`00a1900` **before any number in this milestone existed**.

---

## 1. Headline

**The sweep ran, both sides of the tradeoff moved, and the pre-registered
decision rule cannot rule, because the control that anchors the noise statistic
failed on all five stacks. The reason it failed is the milestone's most useful
result: the selector's noise penalty has a strong `N` term.**

Four things came out of it.

1. **Fact 1036 reproduces exactly**, on a binary this milestone built, through
   the shipped CLI — and **it does not generalise**. At the shipped
   `DEFAULT_GATE = 4.0`, `n_eff/N` runs **0.0095 to 0.3011** across five real
   stacks (31.7×) and the singleton fraction runs **4.62% to 80.98%** (17.5×).
   *"On a real subject at the shipped default the estimator behaves as a
   selector"* is **true on `wrapped-text-1` and `foam` and false on `109MSDCF`,
   `coffee-bean` and `bee-1`**, where the merge averages 23–30% of the whole
   bracket.
2. **The selector's cost grows with bracket length.** On one fixed ROI on
   `coffee-bean`, gate-0 flat-ROI noise runs **1.099× at N = 10 → 5.170× at
   N = 105**. That is M66's defect shape — a quantity whose null moves with `N`
   — appearing in the *selector's price* rather than in a threshold, and it is
   why my gate-0 control, whose bar I transferred from a 30-frame static burst,
   could not be met at N = 22–299.
3. **The stacks disagree about the gate, and the disagreement is large.** With
   the controls set aside (**this is not the ruling**) three stacks show a rung
   above the shipped gate with material noise gain at no material detail cost
   and two do not. The knee sits at `n_eff` **1.727 to 144.963 — an 84× span**.
   No single gate is at the knee for more than one of these subjects.
4. **A third instance of the corpus's now-familiar defect shape, in the shipped
   detail guard.** `DETAIL_COLLAPSE_FLOOR = 0.90` is a fixed line against
   `RETENTION`, whose denominator is one arbitrary middle frame of a focus
   bracket. On these five stacks it reads **1.114× to 129.814×** at the shipped
   gate, so the guard tolerates a **19.2% to 99.3%** loss of merged detail
   before firing, and its companion `DETAIL_RISE_FLAG` is **permanently tripped
   on 4 of 5 stacks at every one of the 32 rungs measured**.

**Nothing under `crates/` was modified.** The shipped CLI already sweeps gates
and already prints both invariants; the whole measurement is one invocation per
stack.

---

## 2. What I read before designing — rule 40

`docs/research/M73-cylinder-invariant.md` (§5.5 texture stratification, §8 the
gate ladder, §12 outside charter, §13.6 the gap this fills),
`docs/research/M67-focus-correctness.md`, `docs/research/M62-sqrt-n.md`
(§7.3 P9, the P-table at §12), `docs/research/M69-focus-noise-sd.md` (my own
prior milestone), `docs/research/SYNTHESIS.md` facts 1035–1042 and 1043–1051,
`crates/strehl-cli/src/main.rs`, `crates/strehl-cli/src/merge_cmd.rs`,
`crates/strehl-cli/src/stack.rs`, `crates/strehl-core/src/flat_ratio.rs`,
`crates/strehl-core/src/plane.rs`, `crates/strehl-core/src/merge.rs`.

**M73 §13.6 names this milestone's charter and declines it**, which is how I
know I am not duplicating it: *"Image quality of the merged output. This
milestone scores index fields only. Whether a merge admitting 1.24 frames
produces a worse image than one admitting 12 is unmeasured."* M73 §8's ladder
measures **admission correctness** against the cylinder invariant, not image
quality; it is cited below, never repeated.

---

## 3. The instrument, and the build

**Fact 1 (INSTRUMENT).** No code change was needed. `strehl stack` takes
`--gate` with `num_args = 1..` (`main.rs:120`), folds **every** gate in the same
pass two, and prints three tables keyed by gate: the `mean n_eff` ladder
(`merge_cmd.rs:966`), **ACCEPTANCE INVARIANT 1 of 2** — flat-ROI high-pass sd
and `HP RATIO` (`merge_cmd.rs:1007`) — and **ACCEPTANCE INVARIANT 2 of 2** —
noise-corrected detail gradient and `RETENTION` (`merge_cmd.rs:1189`). A whole
eight-rung sweep costs one decode budget.

The `--gate` help states this milestone's charter in shipped text: *"The
sharpness cost of THIS gate on real frames is not measured in this corpus, and
no number here should be read as claiming otherwise."*

**Fact 2 (PROVENANCE).** The workspace `target/` is shared with other live
agents and could not be used for an attributable measurement. `cargo clean -p
strehl-core -p strehl-cli -p strehl-plugin` removed 2901 files (970.6 MiB) and
the very next `cargo build --release` still printed `Finished in 0.11s` with no
`Compiling` line, and `target/release/strehl.exe` carried a timestamp 3.5 hours
old: **another agent rebuilt the shared tree between my clean and my build.**
The measurement was therefore taken from a **private `CARGO_TARGET_DIR`** at
`experiments/M77-gate-sweep/target-m77`, whose build printed `Compiling
strehl-raw`, `Compiling strehl-cli` and `Finished in 1m 59s`. Every number below
comes from `target-m77/release/strehl.exe`, 8 256 000 bytes, mtime
2026-08-23 19:21:05, echoed by the harness into every log.

**This generalises and is routed to the orchestrator (§12):** in a shared tree,
`cargo clean -p` plus a rebuild is not sufficient to establish authorship of a
binary. A private `CARGO_TARGET_DIR` is.

---

## 4. Arm G0 — ROI selection, and the deviation

ROI selection is the whole experiment (discipline 438). The rule was fixed in
§4 of the pre-registration and computed **from input frames only** — no merge
output at any gate enters it, which is what keeps ROI choice from being circular
with the sweep that reads it. 256×256 tiles, stride 128, 32 px edge margin; flat
ROI minimises `max over frames of contam`, detail ROI maximises `max over frames
of cg`, where `contam = hp_sd / (HP_NOISE_GAIN · model_sigma)` is the shipped
`structure_contamination` and `cg = sqrt(max(0, raw_rms² − noise_rms²))` is the
shipped corrected gradient (`merge_cmd.rs:305`).

**Fact 3 (DEVIATION, declared).** The registered arm G0 sampled ≥ 12 frames at a
fixed stride, which §4 step 2 permits. §4 step 4 states the rule's purpose in its
own words — the tile must be flat *"in EVERY sampled frame rather than on
average"*. The stride defeated that purpose: on `foam` the shipped CLI reported
the selected tile's reference high-pass sd running **28.761 DN (frame 1) to
502.786 DN (frame 44)**, and frame 44 was not among the 15 sampled. A second arm
**G0′** was therefore run over **all** frames, changing nothing else. It is
**post hoc**, is labelled as such everywhere, and is judged by the **same
pre-registered K3 bar**, so the diagnosis it embodies could fail.

**Fact 4 (THE DIAGNOSIS FAILED).** It did fail. Closing the sampling loophole
moved gate-0 `HP RATIO` from 2.9220× to 2.6410× on `wrapped-text-1` and from
18.4330× to **18.6830×** on `foam` — the wrong way — and **K3 remained NOT MET
on all five stacks in both arms**. Under-sampling was not the dominant cause.
The cause is in §7.

**Fact 5 (NO FLAT ROI EXISTS ON THREE OF FIVE REAL STACKS).** With every frame
scanned, the flattest 256×256 tile in the entire plane still reads, as
`max over frames` contamination: `wrapped-text-1` **2.6339×**, `109MSDCF`
**1.1399×**, `coffee-bean` **1.0968×**, `foam` **15.8769×**, `bee-1`
**1.0666×**. **K1's bar (`contam < 1.10`) is MET on two.** On `foam` the best
tile in the image reaches **438.9 DN** of high-pass sd in one frame against a
37.1 DN median — a temporal spread of **15.807×**. `foam` has no flat region at
all, and no ROI-selection rule can manufacture one.

**Fact 6 (THE SHIPPED CONTAMINATION STATISTIC IS THE WEAKER OF THE TWO).** The
`HP RATIO`'s own denominator is the **median** per-frame high-pass sd, and the
CLI's printed `STRUCTURE FLOOR` is a median-based contamination. On `foam` it
reads **1.4413×** where the max-over-frames statistic reads **15.877×**. **The
median hides a tile that comes sharply into focus in a minority of frames; the
max does not.** On a focus bracket that is exactly the failure mode that
matters, because the merge's job is to find those frames.

**Fact 7 (THE PYTHON AND THE RUST AGREE).** The ROI rule is Python; the sweep is
the shipped Rust. On the five selected flat ROIs, my per-frame high-pass sd
matches the CLI's own reported reference distribution to **0.99602×–1.00001×**
on the median and to five decimal places on the min and the max. Plane
convention, black level, box kernel and valid-interior convention all agree.
The 0.4% residual is an even-length median tie-break, not a disagreement about
the ROI.

---

## 5. Stacks, ladder and the registered result

Five stacks, chosen in advance to span the corpus's measured `n_eff/N` range and
to include M73's subject. Gates 0, 1, 2, 4, 8, 16, 32, 64.

**Fact 8 (FACT 1036 REPRODUCES EXACTLY).** `wrapped-text-1`, N = 130, shipped
gate 4: **`mean n_eff` = 1.238, `n_eff/N` = 0.0095, singleton 80.98%.** Fact
1036 records 1.238, 0.0095 and 81.4%. This is an independent reproduction on a
binary built by this milestone, through the shipped CLI rather than through
M73's harness.

**Fact 9 (AND IT DOES NOT GENERALISE).** At the same shipped gate, on the same
binary, in the same run:

| stack | N | ISO | `n_eff` at gate 4 | `n_eff/N` | singleton % | behaving as |
| --- | --- | --- | --- | --- | --- | --- |
| `wrapped-text-1` | 130 | 100 | 1.238 | 0.0095 | 80.98% | selector |
| `foam` | 100 | 1000 | 1.359 | 0.0136 | 71.07% | selector |
| `109MSDCF` | 22 | 160 | 4.987 | 0.2267 | 4.62% | **estimator** |
| `bee-1` | 299 | 100 | 70.146 | 0.2346 | 30.73% | **estimator** |
| `coffee-bean` | 105 | 50 | 31.614 | 0.3011 | 55.27% | **estimator** |

`n_eff/N` spans **31.7×** and the singleton fraction spans **17.5×**. Fact
1036's two subjects are `wrapped-text-1` and `wrapped-text-2`; **the collapse it
records is a property of that subject, not of the shipped default.** Fact 629's
corpus floor of 0.0118 at gate 2 is a *floor* and was reported as one; the
ceiling at the shipped gate is 25× above it.

**Fact 10 (COFFEE-BEAN IS BIMODAL WITHIN ONE IMAGE).** `coffee-bean` averages
31.614 frames per pixel while **55.27% of its pixels admit exactly one**. The
mean and the mode describe different halves of the same image. This is
SYNTHESIS fact 1045's within-stack dispersion appearing in the admission
statistic rather than in the response SD, and it is the strongest single reason
in this report to doubt that one gate can be right for one *image*, let alone
for a corpus.

---

## 6. The decision rule, one declared transposition, and the ruling

**Fact 11 (A TRANSPOSITION IN MY OWN PRE-REGISTRATION).** §7 defines
`dN(T) = HP_RATIO(T) / HP_RATIO(4.0)`, **names it** *"noise benefit of
opening"*, and sets the bar *"material noise gain: `dN >= 1.10`"*. `HP RATIO` is
a **noise** ratio — merged high-pass sd over the median per-frame high-pass sd
(`flat_ratio.rs:348-353`) — so lower is less noise. The formula as written
computes a noise **increase**, and requiring it to exceed 1.10 asks the merged
image to become 10% *noisier* as the gate opens. Under the literal reading no
rung can ever be (a)-SUPPORTED for the reason the milestone exists to test, and
the test is vacuous.

Both orientations are computed and both are in every table below. **The ruling
is taken on the orientation §7 names**, `dN_ben(T) = HP_RATIO(4.0)/HP_RATIO(T)`.
The bar's **magnitude** (1.10) is untouched, and the detail bar
(`dD = RETENTION(T)/RETENTION(4.0) <= 0.98`) was correct as written and is
untouched in both respects.

**Fact 12 (THE RULING: INDETERMINATE, FIVE OF FIVE).** §7 states
*"INDETERMINATE — K2 or K3 not met."* **K3 is NOT MET on all five stacks, in
both arms.** Every per-stack verdict is therefore INDETERMINATE and the corpus
verdict is INDETERMINATE. I am not entitled to (a) or (b) from this run and do
not claim either.

The registered arm G0, in full. `dD` is the ruling's detail column; `dN_ben` and
`dN_lit` are the two orientations of Fact 11; `eff` is arm G2.

`wrapped-text-1`, N = 130, flat ROI x32,y1056, contam 1.2437×:

| gate | `n_eff` | `n_eff/N` | `HP RATIO` | `RETENTION` | `dN_ben` | `dN_lit` | `dD` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1.000 | 0.0077 | 2.9220 | 7.6260 | 0.9357 | 1.0688 | 1.0045 |
| 1 | 1.062 | 0.0082 | 2.8870 | 7.6160 | 0.9470 | 1.0560 | 1.0032 |
| 2 | 1.122 | 0.0086 | 2.8490 | 7.6090 | 0.9596 | 1.0421 | 1.0022 |
| **4** | **1.238** | **0.0095** | **2.7340** | **7.5920** | **1.0000** | **1.0000** | **1.0000** |
| 8 | 1.469 | 0.0113 | 2.5170 | 7.5550 | 1.0862 | 0.9206 | 0.9951 |
| 16 | 1.963 | 0.0151 | 2.0580 | 7.4480 | 1.3285 | 0.7527 | 0.9810 |
| 32 | 3.222 | 0.0248 | 1.6220 | 7.1450 | 1.6856 | 0.5933 | 0.9411 |
| 64 | 12.119 | 0.0932 | 0.5790 | 6.4970 | 4.7219 | 0.2118 | 0.8558 |

`109MSDCF`, N = 22, flat ROI x1440,y416, contam 1.1399×:

| gate | `n_eff` | `n_eff/N` | `HP RATIO` | `RETENTION` | `dN_ben` | `dN_lit` | `dD` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1.000 | 0.0455 | 1.1340 | 1.1230 | 0.4780 | 2.0923 | 1.0081 |
| 1 | 1.884 | 0.0856 | 0.9130 | 1.1180 | 0.5936 | 1.6845 | 1.0036 |
| 2 | 2.891 | 0.1314 | 0.7490 | 1.1160 | 0.7236 | 1.3819 | 1.0018 |
| **4** | **4.987** | **0.2267** | **0.5420** | **1.1140** | **1.0000** | **1.0000** | **1.0000** |
| 8 | 10.469 | 0.4759 | 0.3510 | 1.1050 | 1.5442 | 0.6476 | 0.9919 |
| 16 | 18.657 | 0.8480 | 0.3350 | 1.0850 | 1.6179 | 0.6181 | 0.9740 |
| 32 | 20.024 | 0.9102 | 0.3320 | 1.0440 | 1.6325 | 0.6125 | 0.9372 |
| 64 | 20.995 | 0.9543 | 0.3320 | 0.9770 | 1.6325 | 0.6125 | 0.8770 |

`coffee-bean`, N = 105, flat ROI x32,y288, contam 1.0907×:

| gate | `n_eff` | `n_eff/N` | `HP RATIO` | `RETENTION` | `dN_ben` | `dN_lit` | `dD` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1.000 | 0.0095 | 5.1700 | 47.0240 | 0.0839 | 11.9124 | 1.0026 |
| 1 | 4.072 | 0.0388 | 1.6700 | 46.9890 | 0.2599 | 3.8479 | 1.0018 |
| 2 | 14.386 | 0.1370 | 0.6730 | 46.9730 | 0.6449 | 1.5507 | 1.0015 |
| **4** | **31.614** | **0.3011** | **0.4340** | **46.9030** | **1.0000** | **1.0000** | **1.0000** |
| 8 | 34.171 | 0.3254 | 0.4300 | 46.7980 | 1.0093 | 0.9908 | 0.9978 |
| 16 | 35.581 | 0.3389 | 0.4300 | 46.6280 | 1.0093 | 0.9908 | 0.9941 |
| 32 | 37.233 | 0.3546 | 0.4300 | 46.2010 | 1.0093 | 0.9908 | 0.9850 |
| 64 | 40.024 | 0.3812 | 0.4300 | 45.1380 | 1.0093 | 0.9908 | 0.9624 |

`foam`, N = 100, flat ROI x288,y928, contam 14.1384×:

| gate | `n_eff` | `n_eff/N` | `HP RATIO` | `RETENTION` | `dN_ben` | `dN_lit` | `dD` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1.000 | 0.0100 | 18.4330 | 3.7700 | 0.9930 | 1.0070 | 1.0272 |
| 1 | 1.087 | 0.0109 | 18.4330 | 3.7370 | 0.9930 | 1.0070 | 1.0183 |
| 2 | 1.177 | 0.0118 | 18.4010 | 3.7140 | 0.9947 | 1.0053 | 1.0120 |
| **4** | **1.359** | **0.0136** | **18.3040** | **3.6700** | **1.0000** | **1.0000** | **1.0000** |
| 8 | 1.727 | 0.0173 | 18.2040 | 3.6140 | 1.0055 | 0.9945 | 0.9847 |
| 16 | 2.452 | 0.0245 | 18.0140 | 3.5430 | 1.0161 | 0.9842 | 0.9654 |
| 32 | 3.903 | 0.0390 | 17.4050 | 3.4360 | 1.0517 | 0.9509 | 0.9362 |
| 64 | 7.468 | 0.0747 | 16.3460 | 3.2000 | 1.1198 | 0.8930 | 0.8719 |

`bee-1`, N = 299, flat ROI x2720,y1568, contam 1.0587×:

| gate | `n_eff` | `n_eff/N` | `HP RATIO` | `RETENTION` | `dN_ben` | `dN_lit` | `dD` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1.000 | 0.0033 | 3.4340 | 129.9210 | 0.1677 | 5.9618 | 1.0008 |
| 1 | 5.860 | 0.0196 | 1.1920 | 129.8750 | 0.4832 | 2.0694 | 1.0005 |
| 2 | 26.127 | 0.0874 | 0.6570 | 129.8500 | 0.8767 | 1.1406 | 1.0003 |
| **4** | **70.146** | **0.2346** | **0.5760** | **129.8140** | **1.0000** | **1.0000** | **1.0000** |
| 8 | 85.424 | 0.2857 | 0.5700 | 129.6470 | 1.0105 | 0.9896 | 0.9987 |
| 16 | 97.559 | 0.3263 | 0.6050 | 129.4080 | 0.9521 | 1.0503 | 0.9969 |
| 32 | 113.015 | 0.3780 | 0.4350 | 128.9920 | 1.3241 | 0.7552 | 0.9937 |
| 64 | 144.963 | 0.4848 | 0.3580 | 128.3130 | 1.6089 | 0.6215 | 0.9884 |

**Fact 13 (K1's REGISTERED CONSEQUENCE, HONOURED).** K1 is NOT MET on
`wrapped-text-1`, `109MSDCF` and `foam`. `flat_ratio.rs` establishes that
contamination *"IS ALSO THE FACTOR BY WHICH EVERY RATIO BELOW UNDER-REPORTS"*,
so **every `dN` above is a lower bound**, with the disclosed factor
**1.2437× / 1.1399× / 1.0907× / 14.1384× / 1.0587×** respectively. On `foam` the
noise column is not interpretable as noise at all.

**Fact 14 (WHAT THE RULE ALONE WOULD HAVE SAID — NOT THE RULING).** Setting the
controls aside, purely so the reader can see what the measurement contains:
**(a) on three stacks, (b) on two.** Free rungs above the shipped gate
(`dN_ben ≥ 1.10` **and** `dD > 0.98`): `wrapped-text-1` gate 16 (1.3285,
0.9810); `109MSDCF` gate 8 (1.5442, 0.9919); `bee-1` gates 32 and 64 (1.6089,
0.9884). None on `coffee-bean`, whose `dN_ben` caps at **1.0093** — its noise is
already gone at gate 4 — and none on `foam`, where the only rung clearing
`dN_ben` is gate 64 at `dD` = 0.8719. **This is reported as a split and never as
a majority.** Arm G0′ gives the identical split with the same free rungs.

**Fact 15 (THE KNEE SPANS 84× IN `n_eff`).** Largest `T` with `dD > 0.98`, and
its `n_eff`: `foam` gate 8 / **1.727**; `wrapped-text-1` gate 16 / **1.963**;
`109MSDCF` gate 8 / **10.469**; `coffee-bean` gate 32 / **37.233**; `bee-1` gate
64 / **144.963**. **On every one of the five, the knee is above the shipped
gate 4** — but on two of them there is nothing worth buying up there. M52 measured
that the gate achieving a chosen `n_eff` varies 28.9× across the corpus; this is
the same non-portability seen from the image-quality side, at 84×.

---

## 7. Why K3 failed — the selector's `N` term

**Fact 16 (K3 NOT MET, FIVE OF FIVE, BOTH ARMS).** K3 required, at gate 0,
`mean n_eff` = 1.000 **and** `HP RATIO` ∈ [0.90, 1.10]. The first limb is MET
everywhere, exactly. The second reads **1.1340× (`109MSDCF`), 2.9220×
(`wrapped-text-1`), 3.4340× (`bee-1`), 5.1700× (`coffee-bean`), 18.4330×
(`foam`)** — and 1.1340 / 2.6410 / 3.4340 / 5.2200 / 18.6830 under arm G0′.

**Fact 17 (THE MECHANISM, MEASURED).** `coffee-bean`, one fixed flat ROI, one
binary, `--limit` varying only how many frames the selector chooses among:

| N | gate-0 `HP RATIO` | gate-4 `HP RATIO` |
| --- | --- | --- |
| 10 | 1.099× | 0.510× |
| 25 | 1.534× | 0.460× |
| 52 | 4.195× | 0.446× |
| 105 | 5.170× | 0.434× |

**Pure selection costs 10% at N = 10 and 417% at N = 105 — a 4.70× growth in the
penalty, on the same pixels, from nothing but bracket length. The shipped gate
is flat over the same range (1.17× total).** This ROI is genuinely flat: its
per-frame reference high-pass sd runs 23.418–26.147 DN, a temporal spread of
1.12×, so this is not structure being recovered.

**Fact 18 (THIS IS M66's DEFECT SHAPE, IN A THIRD PLACE).** M66 proved
`Gate::tolerance()` has no `N` term while the expected max of `N` noisy
responses grows strictly with `N`; M62 confessed the same shape in its guard G.
Here the same shape appears in the **price of not gating at all**. It is the
strongest measured statement of the project's thesis I have seen: **the
estimator-versus-selector gap is not a constant, it widens with bracket length**,
and macro focus stacks are exactly where brackets are long.

**Fact 19 (MY OWN CONFIGURATION-TRANSFER ERROR, CAUGHT BY MY OWN CONTROL).**
K3's [0.90, 1.10] window was set from SYNTHESIS fact 890 — *"`merge --gate 0`
(same binary, `n_eff` ≡ 1) 0.9768x"*. **That number is on M62's 30-frame static
burst, where every frame is in focus and there is nothing for the selector to
select on**, and it is on the truth-referenced √N scale, not on `HP RATIO`. I
carried the value into a control on real subjects at N = 22–299 and left the
configuration behind. Given Fact 17, a bar of [0.90, 1.10] at gate 0 could only
ever have been met at small `N`. **The orchestrator warned me in this exact
form — "the configuration travels separately from the value and is the first
thing lost" — and I did it to myself in my own pre-registration.**

**Fact 20 (WHY THE FAILURE IS NOT COSMETIC, AND WHY IT IS ALSO NOT FATAL TO THE
CURVES).** The decision rule reads `dN` and `dD` **relative to gate 4** and never
touches gate 0, so nothing in §6's tables is arithmetically contaminated by the
gate-0 rung. What K3 was there to certify is the *scale* of the noise statistic —
that a change in `HP RATIO` is a change in noise — and Fact 17 shows the
statistic at gate 0 is dominated by a selection artefact rather than by noise.
That doubt does not stop at gate 0: it is a doubt about how much of the fall from
gate 0 to gate 4 is "noise removed" and how much is "selection artefact removed",
and the pre-registration attached INDETERMINATE to exactly that doubt. **I
honour it.** §6 is a measurement; it is not a verdict.

**Fact 21 (WHAT WOULD HAVE MADE K3 MEETABLE).** A control at gate 0 needs a
configuration in which selection has a known cost. M62's burst has one — zero —
and does not exist as a real capture (§10). A real-subject anchor would need a
capture in which the correct per-pixel frame is known independently, which no
capture in this corpus provides. **K3 was the wrong control, not a control that
failed by bad luck**, and Fact 17 is the measurement that shows why.

---

## 8. Every control, and its registered consequence

| id | control | bar | G0 | G0′ | consequence, honoured |
| --- | --- | --- | --- | --- | --- |
| **K1** | flat ROI is flat | `contam < 1.10` | 2 of 5 | 2 of 5 | **NOT MET on 3.** Every `dN` reported as a lower bound with its factor (Fact 13) |
| **K2** | detail ROI has detail | `cg ≥ 3×` flat's | 5 of 5 | 4 of 5 | MET on the registered arm. NOT MET on `foam` under G0′ (2.33×), which is why G0′ is not the ruling arm either |
| **K3** | selector anchor | `n_eff` = 1.000 and `HP RATIO` ∈ [0.90, 1.10] | 0 of 5 | 0 of 5 | **NOT MET on all five. Every verdict is INDETERMINATE** (Fact 12) |
| **K4** | monotonicity | `mean n_eff` non-decreasing | 5 of 5 | 5 of 5 | MET. The sweep is a sweep |
| **K5** | ROI choice not noise-driven | even/odd frames give same or adjacent tile | flat 3/5, detail 2/5 | flat 4/5, detail 4/5 | **NOT MET in part.** Attached to the per-stack rows: `wrapped-text-1` and `foam` (G0) and `coffee-bean` (G0′) carry an unstable ROI choice |

**Fact 22 (K5 IS INFORMATIVE ABOUT THE SUBJECT, NOT ONLY ABOUT THE RULE).** The
detail limb is unstable precisely where the detail ROI's winning frame differs
between the even and odd halves of the bracket — which is what a *dense* focus
bracket looks like. Scanning all frames (G0′) fixed it on four stacks and broke
it on `coffee-bean`, whose flat tile has 400 near-equivalent candidates within a
2% contamination band.

---

## 9. The bias side, and a third bare constant compared in the wrong place

**Fact 23 (DETAIL COST IS REAL, MONOTONE AND MEASURED ON ALL FIVE).** `dD` at
gate 64: **0.8558** (`wrapped-text-1`), **0.8719** (`foam`), **0.8770**
(`109MSDCF`), **0.9624** (`coffee-bean`), **0.9884** (`bee-1`). Corrected
retention falls monotonically with the gate on every stack and every rung. The
pre-registration's 0.98 bar sits 3–10× above this metric's own measured
gate-to-gate drift (0.2% on `109MSDCF`, 0.6% on `119MSDCF`, recorded at
`merge_cmd.rs:1524`), so these are movements the metric can resolve.

**Fact 24 (THE SHIPPED COLLAPSE GUARD IS INERT ON REAL SUBJECTS).**
`DETAIL_COLLAPSE_FLOOR = 0.90` fires on **absolute** `RETENTION`
(`merge_cmd.rs:1498`), whose denominator is the corrected gradient of **one
arbitrary middle frame** of a focus bracket. At the shipped gate that
denominator puts `RETENTION` at 1.114× / 3.670× / 7.592× / 46.903× / 129.814×.
The merged detail could therefore fall by

| stack | `RETENTION` at gate 4 | loss tolerated before COLLAPSE fires |
| --- | --- | --- |
| `109MSDCF` | 1.114 | 19.2% |
| `foam` | 3.670 | 75.5% |
| `wrapped-text-1` | 7.592 | 88.2% |
| `coffee-bean` | 46.903 | 98.1% |
| `bee-1` | 129.814 | **99.3%** |

**and not be flagged.** Fact 24 of the corpus measured the collapse this guard
exists to catch at −58% and −53%; on `bee-1` a −99% collapse passes.

**Fact 25 (AND ITS COMPANION IS PERMANENTLY TRIPPED).** `DETAIL_RISE_FLAG =
1.50` reads `INVESTIG.` on **4 of the 5 stacks at every one of the 32 rungs
measured** — 128 of 160 verdict cells. The constant's own registered
justification names the readings it was set against: *"1.257x and 1.027x
tonight"*. On real macro brackets the expected reading is 3.7× to 129.8×.

**Fact 26 (THE SHAPE, NAMED).** Both are **fixed lines against a statistic whose
scale is set by how out-of-focus one arbitrary reference frame happens to be** —
word for word the defect M66 proved in `Gate::tolerance()` and M62 confessed in
guard G. My own M69 reframing, now discipline 506, says the question is not
whether a constant is bare but **where it is compared**: `DETAIL_COLLAPSE_FLOOR`
is compared *directly against a drifting ratio*, which discipline 506 classifies
as the unsafe case. **This is routed, not fixed: `crates/` is untouched.**

---

## 10. The circularity, and the capture that does not exist

**Fact 27 (WHERE IT BITES).** The gate is denominated in `FOCUS_NOISE_SD`, and
M69 measured that constant to carry a **4.06×** span across texture scale with a
**1.70–3.99×** within-stack per-pixel dispersion (SYNTHESIS facts 1043, 1045).
"Gate 4" is therefore not one tolerance; it is a different effective tolerance on
each stack and on each *pixel*. **This bites any claim of the form "the right
gate is `T`", and I make none.** It does not bite the *shape* of the tradeoff
read against `mean n_eff`, which is a counted physical quantity — how many
frames were actually averaged — and is not denominated in the constant. That is
why every table in §6 carries `n_eff` and `n_eff/N` beside the gate (M67 fact
14's requirement, and M73 §8 followed it). **Reporting against `n_eff` removes
the between-stack part of the circularity entirely and the within-stack part not
at all**: at one gate, different pixels of one image are gated at different
effective tolerances, and both my ROIs average over ~65 000 such pixels. Fact 10
is that residue made visible.

**Fact 28 (A SECOND MODEL DEPENDENCE, WHICH CANCELS EXACTLY).** `RETENTION` is
built on `corrected_rms = sqrt(raw² − model_noise²)` and M69's fact 24 measured
the shipped model over-predicts read noise by 8–27%. The single-frame reference
is **fixed across the whole sweep**, so it divides out of
`dD(T) = RETENTION(T)/RETENTION(4.0)` **identically** — visible in the tables,
where `coffee-bean`'s `RETENTION` of ~47× produces a perfectly well-conditioned
`dD`. It does *not* cancel in the merged numerator, whose `model_noise` shrinks
with `n_eff`: on `bee-1` it falls 16.81 → 13.51 DN from gate 4 to 64 against a
raw rms of ~800, so the residual bias is under 0.06% of the corrected value and
is far below the movements in Fact 23.

**Fact 29 (NOT MEASURED VERSUS NOT MEASURABLE).** The variance side of this
question has a known-answer control and **it does not exist as a capture**.
`M62-sqrt-n.md:70` records *"the real branch is not run because no real burst
exists"*; `docs/captures-needed.md` §12 still lists the 30-frame static burst as
REQUESTED. Per M62 fact 916 it would have arbitrated **only** the variance side,
since a static burst has no focus variation and therefore no interior optimum —
so it would not have settled reading (a) versus (b) either. **What this milestone
actually needs, and what no capture in this corpus provides, is a real bracket in
which the correct per-pixel source frame is known independently of the focus
operator.** That is the precise shape of the owed data, and §12 routes it.

---

## 11. What I did not do

- **No spectra, no transform of any kind.** M70 owns the frequency-domain form
  of this question. Nothing here computes one.
- **No re-derivation of M73 §8's ladder.** Cited, never repeated (rule 40).
- **No choice of an operating gate.** M73 §8 declined to pick a point off its own
  curve; §10 above makes the same refusal with more force.
- **No ruling on M62's certification, and no change to `crates/`.** The
  acceptance-battery limb of any recalibration was priced by M62 by algebra and
  is not re-derived here. Independently checked at the line: `merge.rs:310` is
  `self.threshold * SQRT_2 * FOCUS_NOISE_SD`, **linear in the constant**, so
  M62's claim that rescaling σ by `c` is exactly rescaling the gate by `c`
  holds, and its committed gate sweep is the sensitivity curve.
- **No edit to** `SYNTHESIS.md`, `AGENTS.md`, `OWNER-QUESTIONS.md`,
  `docs/captures-needed.md`, or M70's report.

---

## 12. Routed to the orchestrator

1. **Fact 1036 needs its configuration attached.** It is a `wrapped-text`
   property, not a property of the shipped default. Facts 9 and 10 give the
   corpus-wide numbers. **Reading (b) — "at this magnification only one frame
   carries the pixel" — is defensible on `wrapped-text-1` and `foam` and is
   simply false on the other three**, where the shipped merge averages 23–30% of
   the bracket. The project's claims should say which subjects they describe.
2. **A new defect, unruled, in the shipped detail guard** (Facts 24–26):
   `DETAIL_COLLAPSE_FLOOR` tolerates a 19.2–99.3% detail loss and
   `DETAIL_RISE_FLAG` is permanently tripped on 4 of 5 real stacks. Same shape as
   `Gate::tolerance()` and guard G. Needs a milestone; I did not touch `crates/`.
3. **The selector's `N` term** (Facts 17–18) is a thesis-strengthening result
   that no milestone has claimed: the estimator-versus-selector gap widens with
   bracket length, measured 1.099× → 5.170× over N = 10 → 105.
4. **The shipped flat-ROI invariant's median contamination hides the failure
   mode that matters on a focus bracket** (Fact 6): median 1.4413× against
   max-over-frames 15.877× on `foam`.
5. **Build provenance in a shared tree** (Fact 2): `cargo clean -p` plus a
   rebuild is *not* sufficient to establish authorship, because another agent can
   rebuild in between. A private `CARGO_TARGET_DIR` is, and costs one flag.
6. **The capture owed** (Fact 29), for `docs/captures-needed.md`: a real focus
   bracket with independently known per-pixel correct frames. The static burst,
   still owed, would not settle this question even if delivered.

---

## 13. Reproduction

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:CARGO_TARGET_DIR = "experiments\M77-gate-sweep\target-m77"
cargo build --release --bin strehl        # must print Compiling

$env:PYTHONIOENCODING = 'utf-8'
cd experiments\M77-gate-sweep
python src\01-rois.py              # arm G0  -- registered, input frames only
python src\01b-rois-allframes.py   # arm G0' -- declared deviation, all frames
python src\02-sweep.py             # arms G1/G2 on the G0 ROIs
python src\02-sweep.py b           # arms G1/G2 on the G0' ROIs
python src\03-decide.py            # applies section 7
python src\04-crosscheck.py        # Python vs Rust on the same ROIs
python src\05-selector-n.py        # Fact 17, post hoc: selector cost vs N
```

Logs and JSON in `experiments/M77-gate-sweep/out/`; the `--limit` ladder behind
Fact 17 is `out/ndep-coffee-bean.log`. `D:\personal\macro` is read-only and was
never written to.
