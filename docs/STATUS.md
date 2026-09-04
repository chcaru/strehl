# strehl — status and gaps

**Updated:** end of the 2026-08-27 build session.
**Scope:** what is measured, what is broken, and what is not yet known. Facts cited
by number refer to the table in [`research/SYNTHESIS.md`](research/SYNTHESIS.md).

This file exists because the corpus is 2 MB and nobody should have to read it to find
out where the product stands. Every claim here names the measurement behind it or is
marked as unmeasured.

---

## 1. Where the product actually stands

| Property | Status | Evidence |
| --- | --- | --- |
| **Speed** | **SOTA.** 22.58× `enfuse`; N=299 in 233 s | measured end to end |
| **Corpus coverage** | **33 of 33 subjects rendered** (26 + the 7 new ones); 33 distinct output hashes. Reconciled both ways against the source root: 0 subjects with frames but no master, 0 masters with no source. The 34th directory is `flat-fields` (calibration, no top-level `.ARW`). **`DELIVER-V6\masters\` now holds all 33**; `DELIVER-V6\orch-rendered-7\` holds 7 duplicates verified byte-identical to their `masters\` copies. This layout moved twice during one session while a lane was live — re-measure it, do not trust this row's location claim | `render7.ps1`, `MANIFEST-ORCH7.txt`, fact 1948 |
| **Visual quality** | **24 of 26 masters clean to the eye at 1:1**; the 7 new ones are rendered and 3 spot-viewed, none instrumented | full-corpus survey, `orch_corpuseye.py`, every sheet viewed |
| **Halo** (shipping masters, 2–120 px) | **0 demonstrated on any subject** — but only 11 of 26 are actually *clean*; 4 blind + 7 unmeasurable remain UNSCORED, which is not the same as clean | facts 1851–1855, 1884 |
| **Rim** (shipping masters, ±12 px) | **13 FAIL — a disjoint scale the halo work never reached; unscored by a second lane** | fact 1881 |
| **Aura** (estimator vs pyramid) | estimator measures deeper in **17 of 17** conditioned readings; magnitude unknown | fact 1871 |
| **Chroma** | **1 visible defect, diagnosed, fix specified, not landed** | facts 1861–1863, 1865 |
| **Dust** | **2 real motes found; correction built, wired, tested, OFF by default.** Adjudicated: the advertised **17× does not exist** (it divided two different subjects); depth is −2.94% ± 0.06% on flats, −3.4% to −5.7% on masters. Downside bounded (a wrong-coordinate map renders byte-identical to OFF) *and* upside shown separately (−4.644% → +0.019%). **The lane recommends defaulting it ON, after the cache-key question is resolved** — flipping it moves every byte-freeze, so it was not done unverified at session end | fact 1856; facts 1953–1955; `docs/research/V-MOTE.md` (`09feffe8`) |
| **Regional blur** | **`flowers-cpl` diagnosed: capture gap, not a merge defect** — (a) at all 6 sites | fact 1876 |
| **Depth softening** | root cause identified; candidate fix built but **unscored** | facts 1843–1845, 1849 |
| **GPU** | **unused** | explicit gap against the brief |
| **Pluggability** | **1 of 5 kinds, and it is refused on the shipping default.** Focus measures are a real trait seam, host-calibrated and *demonstrated* (7 operators, 10.27× noise-sd span; swapping moves 99.9105% of samples between two named hashes while the default stays byte-identical). Merge strategy is an enum in core; alignment model, optical profile and output stage have no trait. `--focus` is **refused** on `MergeBackend::Pyramid`, which is the default — so the plugin surface and the shipping path do not intersect. Registry is in-tree, so contributing still requires patching this repo | fact 1952; `docs/research/BUILD-PLUGIN.md` (`e1bf09e0`) |
| **Print gate** (blotch/chroma/band/clip/crush, all 33) | **0 FAIL, and now 0 unresolved.** 17 PASS · 16 ACQUITTED · 0 ACQUITTAL EXPIRED · 0 REVIEW · 0 NOT EXAMINED · 33 total (found 33) — a summing partition with every subject adjudicated. All 13 formerly unresolved subjects were measured against *the frames they were built from* and none is a real defect; worst is `dime-flat-narrow-slices-cpl` at 1.257× against a rule admitting 1.3×, band DN only 1.017×. **No threshold or tolerance was touched.** Re-run independently by the orchestrator against the lane that produced it, same partition | `orch_printready.py` over `masters\`; facts 1966–1968; `docs/research/V-ADJ13.md` (`6f57726f`) |
| **Merge vs. best single frame** | **The sign flips with frequency — there is no single number.** On `113MSDCF` the master reads **1.0997 / 1.1936 / 1.1345** of the per-site ceiling at 0.05–0.20 cyc/output px (*sharper* than the best source frame) and **0.9426 / 0.7314 / 0.6063 / 0.5942** at 0.20–0.40 (softer). Softer only above ~0.20 cyc/px; in the highest qualifying band (0.20–0.25, R = 3.32) the shortfall is **0.9426, ≈5.7%**. The originating claim's **sign survives qualification, its magnitude does not.** **Instrument audited (V-DCNULL):** the producer is `experiments/V-SOFTCHECK/ncommon.py`, **not** `bandqual.py` (which is the *qualifier*) — exactly one file in the tree prints its `max63/max32` column. It **passes a planted DC-offset null** at max deviation **2.3e-07** across six plant arms, and the zero is a live null, not a dead probe: the same plant on a deliberately mean-normalised scorer moves the band 0.5824 → 0.4086 → 0.1852. But it is **exactly covariant with squared gain** (`r_obs = r_true × (g_master/g_frame)²`, measured to 1.5e-07) and has **no exposure audit at all** — 0 mentions, against 6 in sibling `dmeasure.py`. **A 2.91% master-vs-frame level mismatch would erase the entire 5.7%**, and the `.log` files recording each side's `--exposure` are **purged**, so this is now unfalsifiable without a re-render. The **sign is immune** regardless: for all seven bands to truly read 1.0000 the single mismatch would have to be simultaneously +4.87 / +9.25 / +6.51 / −2.91 / −14.48 / −22.13 / −22.92 % — one scalar cannot take seven values of opposite sign (re-derived independently by the orchestrator as √r−1; agrees to the last digit in magnitude, mirrored in sign by ratio convention). Two further limits stated not buried: 0.9426 carries **no CI** (marked NOT MEASURED — the one interval this lane holds answers bracket depth, not master-vs-frame), and it rests on **one** subject of 63 frames where the original claim spanned four | facts 1969, 1978–1981; `docs/research/V-SOFTCHECK-nyquist.md` (`bd5580e3`), `docs/research/V-DCNULL.md` |
| **Print-ready** | **NO** — see §3 | |

`bee-1-cpl` (N=299) resolves individual ommatidia. `wrapped-text-1/2` resolve individual
toner particles and paper fibre. The ceiling of this pipeline is already high; the gap to
"print-worthy across the corpus" is a small number of specific, named defects, not a
general softness.

---

## 2. What was settled this session

### 2.0 Phase 0 of the SOTA path — five lanes closed, none of which changed the code

The owner's `docs/proposals/2026-08-sota-path.md` front-loads phase-0 gates that can
kill an item before it is built. Five are now closed. Three of them found their headline
measurement already sitting in the corpus — a pattern strong enough that every remaining
lane should begin by searching for existing data before planning any decode.

> **The standing criticism of this whole phase, recorded here because it is the most
> important thing on this page.** Across 63 commits, phase 0 has changed **zero lines of
> Rust**. Five closed lanes have produced not one decision that altered the stacker. The
> owner's opening complaint was that this project "was not trending in a SOTA
> direction"; a month of phase-0 work has reproduced that rather than fixed it. The
> remaining phase-0 claims are therefore being triaged by **decision value** — for each,
> if it resolves either way, what code actually changes? — and the ones that answer
> "nothing" are to be dropped rather than run in proposal order.

### 2.0.1 The triage, and what auditing it revealed

`docs/proposals/2026-09-phase0-triage.md` (commit `f7017885`) asked one question of every
remaining gate: if it resolves either way, what code changes? It found the remaining list
was **twelve gates, not nine** — D11/DECODE, D13/IDLE and D15/NVME had been missed — named
six as already answered in the corpus, recommended dropping C5/CURV outright (the lens bowl
has no consumer, so no result could change anything), and concluded: *"Nothing remaining is
worth doing before building. Stop phase 0."*

**That triage was then audited, and it was wrong about half of what it claimed to close.**
Of the three already-answered gates nobody was building on, an independent audit returned
**DO NOT CLOSE on all three**:

- **DPAR** — the null reproduces, but its sensitivity plant is **linear**, while
  `AGENTS.md:173-176` and lane M103 establish that linear alignment plants do not transfer
  to the measured curved track. The minimum detectable amplitude is therefore unknown, and
  a null with unknown power is not evidence of absence.
- **DECODE** — the headline "cold 1.245 GB/s" was **compressed-input** throughput, not the
  allocated-output figure the claim implied; the same data gives ~2.47 GB/s on the other
  convention. The benchmark harness was **absent from the repository**, "cold" meant only
  "unread that session", and there was no timing RED control.
- **NVME** — the device rate the proposal asks for had **never been measured at all**.

The lesson generalises past these three: a paraphrase of a measurement is not the
measurement, and this repo's numbers have to be re-run rather than re-read.

### 2.0.2 DECODE and NVME, now actually measured — both CLOSE

`docs/research/M-PHASE0-DECODE2.md`, `docs/research/M-PHASE0-NVME2.md`,
`experiments/M-PHASE0-IOPERF/`. Commits `40e41a63` (harness) and `d337daa8` (reports).

**D11/DECODE — PASS.** The real-ARW scaling curve the proposal actually specifies, with
both byte conventions reported separately because conflating them is what made the old
number uninterpretable:

| threads | 1 | 2 | 4 | 8 | 16 | 32 |
|---|---|---|---|---|---|---|
| compressed-input MB/s | 194 | 359 | 510 | 591 | 721 | 719 |
| allocated-output MB/s | 381 | 706 | 1002 | 1162 | 1416 | 1413 |

A planted 200 ms delay was detected at 188–289 ms in every arm, so the timer is
commissioned rather than assumed; nonzero output checksums and `black_box` consumption
prove it is not timing a no-op. 381 allocated-output MB/s/core clears the 200 bar and
1.413 GB/s clears the 1.0 bar. **Keep rawler; no owned decoder is warranted.**

**D15/NVME — no bottleneck.** Cold **6.338 GB/s**, warm **20.615 GB/s**, ratio **3.25×**;
replicated at 6.342/19.671 for 3.10×, with cold runs agreeing to 0.055%. Unbuffered reads
stayed at 6.178 GB/s *after* warming, which is what proves cache bypass rather than merely
asserting it. That is 1.268× the assumed 5 GB/s and **11.41%** of projected decode time.
**No IOCP prefetch is warranted.**

**The architecturally useful result is the comparison between them.** Storage delivers
6.338 GB/s cold while decode consumes at 1.413 GB/s allocated-output — **storage is roughly
4.5× faster than decode, so decode is the bottleneck and I/O is not.** That conclusion is
robust to a large measurement error in either direction: it would take a ~4.5× mistake to
flip it, which is why these two gates can close on speed numbers rather than needing the
adversarial re-verification the image-quality claims get. Decode also **saturates at 16
threads** (721→719 compressed, 1416→1413 allocated), so the remaining lever is not more
worker threads but the **bounded decode→fold queue**, which is the live Rust seam.

### 2.0.3 C4c/DPAR — KILL, on a sensitivity argument that now holds

`docs/research/M-PHASE0-DPAR2.md`, `experiments/M-PHASE0-DPAR2/`. Commits `e27e3dd8`
(preregistration) and `7a1a3128` (implementation and results).

The audit's objection to M6 was that its sensitivity plant was **linear**, so the minimum
detectable amplitude on the **curved** track was unknown and the null could not be read as
absence. That objection is now answered, and it resolved in the opposite direction from the
one I expected — the instrument turned out to be far *more* sensitive than feared, not less.

**MDA80 ≤ 0.010 plane px per depth-step at radius 1000** (≤0.020 at radius 2000), with the
bootstrap crossing at 0.010 [0.010, 0.010]. Because 0.010 was the first nonzero rung of the
ladder, this is an **upper bound** on the minimum detectable amplitude — the true figure may
be lower still. At that dose the instrument scored **96/96 detections** (Wilson 95%
[0.9615, 1.0000]) against **3/96** at zero dose.

That settles the reading of the null:

- The proposal's predicted **0.300–0.600 px/depth-step clears MDA by 30×.**
- The **0.0269–0.0538 px/step** regime the audit measured on real adjacent pairs *also*
  reached 96/96 detections.
- The unplanted primary stayed null at **ρ = +0.1352, p = 0.4896**.

So the instrument is demonstrably able to see the claimed effect, with a 30× margin, and it
sees nothing. **Verdict: KILL.** Nothing changes in Rust.

Six controls passed, including the kind this repo has repeatedly needed: an **external M103
track predicate** (read 46.0921 px curvature with accelerating rates, while a straight chord
failed), a **literal oracle** that recovered six values exactly and rejected its own
mutation, similarity orthogonality at 5.75e-15, tangential change 9.29e-14 px, a
bit-identical zero dose, and a fast evaluator matching unchanged M6 S2 to 2.22e-16. An
independent verifier recomputed the power, bootstrap, curvature and orthogonality and found
no defects.

Scope limit, stated by the lane: the result covers M6's post-correlation residual reader.
Continuous MDA below 0.010 and dose-dependent upstream rejection from a full curved
image-render plant remain unmeasured.

### 2.0.4 D8/SPLIT — KILL, and the Rust was removed again

`docs/research/M-PHASE0-SPLIT.md`, `experiments/M-PHASE0-SPLIT/`. Corrective commit
`1ac21560`; the superseded prototype commits are `1cd3019c` and `81ad96fd`.

This lane is the clearest demonstration yet of the failure mode this whole phase exists to
guard against, because it happened **twice in one lane and was caught the second time**.

The lane first built the feature — dual even/odd accumulators in `merge_cmd.rs`, an FRC
module in `strehl-core`, an off-by-default `--split-out` flag — and filed **NARROWED: ship
diagnostic only**, on the strength of seven passing control families, six Rust plants going
RED, and the headline selling point apparently confirmed: identical sharpening moved the
crossing only 0.222192 → 0.220543 while a naive acuity measure falsely rose 1.838176×.

It then re-audited under a standing instruction that stopping is a success, and **reversed
itself to KILL, removing every line of Rust it had written.** The shared files were verified
byte-identical to pre-feature commit `d337daa8`, and `cargo test --workspace` passes 541
core, 115 CLI and 5 byte-freeze tests.

**The distinction it drew is the most valuable output of this phase.** Re-running M115's
exact source blobs from commit `77c8d5e9` on the original 22/33/360-frame inputs, the
published numbers *do* reproduce — blur recovery 0.9938215871–0.9973982082, filter maximum
movement 0.537785%, identity 0.999999999987–1.000000000000. **And reproduction still does not
license building.** Closure fails on evidence reproduction cannot touch:

- the historical null reads **MEAN 0.438734** and **WIENER_UNG 3.331288** against a 0.25 bar;
- a **common-mode adversary reads FRC 0.972099**;
- the 1.0000 identity is **algebraic** — a tautology rather than evidence, which is the
  capped-control failure pattern this repo keeps rediscovering;
- **no plant exercises a data-dependent tuner**;
- M41 records **9/12 endpoint fallbacks and 0/32 successful repairs**.

The mechanism behind all of it is one thing: **two halves of the same frames are not
independent.** They share fixed-pattern noise, sensor structure and scene, so their
correlation is inflated by construction, and no accounting fixes a partition that is
degenerate at source.

The lane also self-reported an error in its own favour: its first audit aggregator falsely
reported non-reproduction because of a wrong Markdown literal — an error that *favoured*
stopping. It was caught and corrected and did not change the verdict.

**Reopening D8 as scoped requires** an independent repeated bracket, sensor-pattern
subtraction, a non-degenerate partition, and a plant that transfers to actual self-tuning.
A follow-on lane (`M-PHASE0-SPLIT2`) is testing whether the 32-repeat capture supplies the
first of those, since repeated exposures of a fixed scene are non-degenerate by construction
in a way split halves can never be.

### 2.0.5 A2/VEIL2 — STOP_DO_NOT_BUILD, and the veil was a tone artifact

`docs/research/M-PHASE0-VEIL2.md`, `experiments/M-PHASE0-VEIL2/`. Commits: repaired measurement
`e4e3939f`, frozen plan `cbb27ea2`, final audit `bcc77de9`. Independent verifier:
`VERIFIED_STOP`.

A2 was ranked by the triage among the **top three highest-value items in the entire remaining
phase-0 list**, and the lane was re-scoped from measurement to building on that basis. It
audited the prior finding first, as instructed, and the prior finding **failed 0 of 7 gates**.

**The decisive result is a tone reversal.** A strictly positive monotone rescaling in the range
`1.0152–1.0722` — a transform that **does not change pixel order** — reverses the measured
effect from `θ=+0.74105` to `θ=−0.08124`. The corrected measurement carries a 95% CI of
`[−0.23588, 0.05108]`, which straddles zero. A quantity that can be flipped in sign by a
monotone remap is not measuring veiling glare; it is measuring contrast. This is the **second**
time in this repository that a headline result has turned out to be a tone artifact, the first
being the retracted 17–27% detail deficit in the head-to-head.

Three further failures, each independently sufficient:

- **The mechanism was never a finding.** The predecessor's two-peak focus curve *does*
  reproduce, on 299 RAWs at f182/f288. But the base/coarse causal mechanism the build was to
  rest on is described by its own originating note as a **"lead, not a finding"**, and
  `BUILD-VEILMAP` never cross-referenced it to the merge at all. The curve *classifier* was
  commissioned; the causal mechanism was not.
- **The instrument was underpowered by 8.5×.** The measured denominator is `0.01757` against a
  registered potency floor of `0.15`, and the potency failure **exits zero** — it does not
  announce itself.
- **Generator/checker cancellation, again.** The drift plant imports production
  `veilgrid.gather`, so it shares a code path with the thing it is testing and is not
  cancellation-resistant. `BUILD-VEILMAP` commissions `DriftFitter` while the measurement adds
  `TrackFitter` and `solve_poly` — the commissioned component is not the component used.

The audit instrument itself was commissioned to this repo's standard: **4/4 positive controls
and 20/20 planted defects RED.** No Rust was written and no flag was added, because a failed
Part 1 prohibited Part 2.

### 2.0.6 The triage is now wrong on five of six claimed closures

`docs/proposals/2026-09-phase0-triage.md` named six gates as already answered by the corpus:
LCA, VEIL2, SPLIT, DPAR, DECODE and NVME. **Five have now been audited and all five failed.**

| Claimed closure | Audit result |
|---|---|
| DPAR | Null reproduces, but the sensitivity plant is *linear* while the real track is curved — power unknown |
| DECODE | Headline figure was compressed-input, not allocated-output; harness absent from the repo; no timing RED control |
| NVME | The device rate the proposal asks for was **never measured at all** |
| SPLIT | Numbers reproduce **exactly**; closure still fails — split halves are not independent |
| VEIL2 | 0/7 gates; the effect reverses under a monotone remap |
| LCA | Under audit |

The generalisable finding, now demonstrated five times: **a paraphrase of a measurement is not
the measurement.** Every one of these was written down accurately somewhere in the corpus and
every one meant something other than what a careful reader concluded from it. This repository's
numbers must be **re-run, not re-read** — and the triage, which read rather than ran, is exactly
the process that fails.

That is not an argument against the triage having been written. It correctly identified where
the decision value was; it was simply wrong about which questions were closed. Its own header
banner records that it is not self-certifying.

## 2.1 The scorecard now exists, and every value on it is UNMEASURED

`docs/proposals/2026-09-sota-scorecard.md`, v1.1, commits `90bced75` and `986c4653`.

Until now this project had no instrument that answered its own governing question. Progress
toward SOTA was narrated rather than measured, and the one competitive measurement that
existed had been **retracted** — the 17–27% detail deficit against Zerene and Helicon turned
out to be a tone-curve artifact, with tone alone explaining 94.8% / 109.9% / 267.1% across
three bands, and it was never replaced with a correct number.

The scorecard was deliberately registered **before** the in-flight build lanes reported, so
that it is a genuine pre-registration rather than a bar fitted to whatever the code turned
out to do.

SOTA is not redefined here. It is taken verbatim from the proposal (`2026-08-sota-path.md`
:164-167): **"SOTA = a pre-registered scorecard, versus named comparators, on axes with
commissioned instruments"**, where an instrument is admitted only after it has failed on a
planted defect of the kind it polices and passed a null it was not tuned on. The proposal's
own success statement (`:192-197`) is conjunctive — detail at or beyond the best shipping
comparator, strictly lower noise, zero invented structure, bounded veil, plus certified
acuity, `n_eff` and physical depth that no comparator emits at all.

Twelve axes carry numeric bars: detail (cutoff ≥0.25 cyc/px, comparator ratio LCB95 ≥1.000),
noise (efficiency ≤1.10, ratio UCB95 ≤0.950), halo/veil (median ≤1%, p99 ≤5%), artifacts
(median Q ≤1.00, bad sites ≤1%), coverage (≥99%, longest gap ≤1%), clipping (≤0.10% per rail),
colour (ΔE00 median/p95/max ≤1/2/3), invented values (**exactly 0.0000%**), certificates
(false-certification UCB95 ≤1%), depth (median ≤0.5 step), speed (≥2× comparator, CPU ≤0.15
s/frame), and memory (≤6 GiB, byte-identical across workers).

**The honest current position: 45 UNMEASURED entries and a competitive standing of UNKNOWN.**
That is the correct state of the record, not a gap in it.

Four instruments were **dropped for being defeatable**: standalone SFR/MTF and band-power
(sharpening-unsafe), same-frame split FRC (invalid for the reason D8 established), natural-image
SSIMULACRA2/butteraugli, and composite scoring. Detail readings above 0.25 cyc/px are reported
as `UNLICENSED_GT_0.25` rather than quoted as results.

The comparator protocol is built so the specific failure that killed the last attempt cannot
recur: every program receives byte-identical hashed linear ProPhoto TIFFs and emits audited
linear TIFFs, XMP is ignored, development controls are rejected, a neutral-ramp test catches
any tone or gain change, and numerical scoring precedes a single common display transform.
Relative timing uses warm uncompressed input so it cannot reward a faster RAW decoder or
faster storage; native-RAW timing is measured separately at 16 workers.

The lane also corrected two things this document had asserted. **C10's registered bars were
point ≥2.0 with lower bound ≥1.5**, not simply 1.5 — the measured R=0.70852 fails both, so the
verdict stands, but the bar was mis-stated. And the request corpus holds **3,251 ARWs, not
~3,361**.

**One axis is blocked on a capture that does not exist.** M7 colour cannot be scored until a
tilted ColorChecker Classic or Digital SG is captured under a measured illuminant with a grey
card and darks. No enumerated capture is a traceable colour target spanning the focus sweep.
This is a request for the owner, not a defect in the scorecard.

**A coupling worth recording:** the proposal's own success statement names FRC as half of the
D1 detail instrument. Same-frame split FRC is now invalid, so whether FRC is available to the
scorecard at all depends on the `SPLIT2` repeat-pair result. If repeats do not rescue it, the
detail axis rests on the slant edge alone.

## 2.2 Where strehl actually stands — the first honest answer since the retraction

> **AMENDED — see §2.7. The instrument used below rewards sharpening by +456%.** An
> independent harness that never touched this lane's code found the licensed ordinal Q25
> statistic reports information-free unsharp masking as `5.560744x` improved while reading a
> genuine resolution improvement as `0.977981x` — the wrong sign. **The tone-invariance claim
> below is confirmed and stands.** The band ratios against *sharpened* comparators do not: the
> leading explanation for the high-band deficit is now that the comparator's sharpening is being
> rewarded, not that strehl resolves less. **Treat the sharpening-0 tie as the honest comparison
> and the 3.5x deficit as unproven.** The NOT ROBUST verdict was correct; §2.7 says why.


`docs/research/V-HEADTOHEAD3.md`, `experiments/V-HEADTOHEAD3/`. Fourteen commits, `5d85d8e1`
through `e162519f`. **Verdict: NOT ROBUST.**

Since the 17–27% detail deficit was retracted as a tone artifact, this project has had **no
answer at all** to the question its entire goal depends on. It now has one, produced by an
instrument built specifically so that the failure which killed the last attempt cannot recur.

**The instrument is tone-invariant and this was proven, not asserted.** Strong affine, gamma-3
and logistic tone curves moved the ordinal statistic by **exactly 0**, while raw band power
under the same transforms moved **30.4%**. That single comparison is the whole difference
between this measurement and the retracted one. Commissioning: **34/34 controls GREEN, 18/18
planted defects RED.** The registration sign defect recorded against `V-HEADTOHEAD2` is also
fixed and commissioned — all six planted shifts recovered the exact *negative* correction. An
independent exhaustive audit reproduced all 54 outcomes.

**Comparator renders exist**, contrary to the concern that a fresh head-to-head would be
blocked: five Zerene renders under `D:\edited\macro\{test,test2,marker,marker2}` and four
unique focus-stack renders under `C:\dev\macro\out` (`stack_v3.tif` is a byte-identical alias).
**No Helicon render exists in the searched roots**, so Helicon remains unmeasured.

**The measured position, per band:**

| Band (cyc/px) | Result | Ratio and 95% CI |
|---|---|---|
| 0.02–0.05 | strehl **LEADS** | `1.0833 [1.0534, 1.1114]` |
| 0.05–0.10 | unresolved | — |
| 0.10–0.20 | strehl **TRAILS** | `0.8842 [0.8420, 0.9311]` |
| 0.20–0.25 | strehl trails sharpened PMax | `0.3992 [0.3381, 0.4720]` |
| 0.25–0.30 | strehl trails sharpened PMax | `0.2834 [0.2178, 0.3696]` |
| 0.30–0.40 | unresolved | — |

**Why the verdict is NOT ROBUST rather than a clean result: the answer depends on how the
comparator is configured.** At 0.25–0.30 cyc/px, strehl is *unresolved* — statistically tied —
against **sharpening-0** PMax at `0.9735 [0.8339, 1.1406]`, and **trails by 3.5×** against
**sharpening-40 / colour-NR-25** PMax at `0.2834`. Same tool, same stack, opposite conclusion.
There is no single number for "where strehl stands" until the comparator's preprocessing is
pinned.

**The retained trail at 0.10–0.20 is the real replacement for the retracted deficit.** It holds
across comparator configurations, its CI excludes parity, and it is tone-invariant. It is
roughly a **12% mid-band detail deficit** — smaller than the retracted 17–27%, and accompanied
by a **retained ~8% lead at 0.02–0.05** that the earlier account never reported.

**Nothing changes in Rust.** The lane states this explicitly: the result moves with comparator
preprocessing and isolates no module in `src/` or `crates/`.

**The open question this leaves, and it is the important one.** The scorecard registers
sharpening as the primary defeat for any detail metric, and its stated controls for that are
**flat-field power and hull distance**. This lane ran neither — the string `hull` does not
appear in its note. So it is not yet known whether sharpened PMax's high-band advantage is
**real resolution or sharpening artifact**. A tone-invariant statistic is invariant to monotone
*point* transforms; sharpening is a *spatial* operation and passes straight through it. Until
that discrimination is run, the 0.20–0.30 trails cannot be interpreted, and the honest summary
is: **strehl leads low-band, trails mid-band by ~12%, and its high-band standing is
undetermined.**

Also unverified by this lane: Helicon performance, the exact source identities of three
marker-fork files, physical MTF fidelity, and the exact geometry behind three author/checker
disagreements.

**M-PHASE0-PHASE — CLOSED. C1 is KILL at the measured ρ, and NOT ROBUST across the ρ
census.** Getting here took a filed verdict, its retraction, and a sign fix in the
lane's own algebra; read Amendments A7 (the wrong verdict), A8 (the retraction), A9 (the
sign defect) and A10 (the rebuilt bar and the standing verdict) in that order, because
the sequence is the finding.

The standing result. Winnable fraction, G-1x zero-mean, against §9's thresholds
(≥60% SURVIVE / 25–60% NARROWED / <25% KILL):

| ρ | field centre | inner annulus | corner |
|---|---|---|---|
| **0.0055** (measured) | 22.2% KILL | 7.5% KILL | 1.2% KILL |
| 0.0100 (inside the 95% CI) | 35.3% NARROWED | 15.3% KILL | 2.5% KILL |
| 0.0600 (census top) | 61.9% SURVIVE | 53.8% NARROWED | 20.6% KILL |

**At the measured ρ the verdict is KILL at every field radius. It flips to NARROWED at
ρ = 0.01, which is inside M-PHASE0-RHO's own 95% interval of 0.00185–0.01078, and to
SURVIVE at the top of the design census — so §9 requires NOT ROBUST.**

**The dominant term is ρ, and it is a measurement convention rather than a capability.**
M-PHASE0-RHO records that refining the frequency grid moves its median by **30.49×**,
which spans the whole KILL-to-SURVIVE range by itself, and that only 9 of its 46 records
directly detect high-band power. Until the grid and boundary convention are pinned, the
ρ uncertainty is wider than the distance between the two verdicts, and **no work on the
aligner changes that.** This is the concrete reason C1 cannot be settled by building.

**Two corrections this lane forced on its own instruments**, both of which had been
flattering the conclusion: `plib.full_reps` used `ν + h` where the algebra requires
`ν − h`, and **all 15 existing controls passed under both signs** because the control
generated its data with the same function it was testing. That is the third
generator/checker cancellation in this lane alone. It now stands at 17 controls and 7
plants, with two new controls (`C-AC`, `C-AD`) that read the function under test against
a fixed geometric predicate and against real lattice sampling, so no such symmetry can
cancel them again.

The earlier retracted verdict and its three load-bearing defects are Amendment A8; the
original claim is left in place, marked, so the error stays legible.

The three defects, each sufficient on its own to void the verdict:

1. **ρ was never measured.** Every alias frequency lies above the retained band (0.5
   cyc/pitch), so all 36–108 alias lookups per stack fell off the end of the radial
   average and were extrapolated at the last bin — which a cumulative-minimum envelope
   had already driven to 1e-300. The reported ρ ≈ 1e-297 is that floor, not a
   measurement. **The lane's own conservative reading is ρ = 9, which does not kill C1.**
2. **"Flat means noise" is false.** I argued a diffraction-limited OTF is monotone
   decreasing, so a flat spectrum out to Nyquist must be noise. A planted *noiseless*
   flat high-frequency scene was classified as shot noise and driven from a true
   ρ = 8.999 to 7.5e-300. A scene PSD ∝ 1/H² needs only 4.98× more object power at 0.50
   than at 0.35 to produce a flat captured plateau — modest, and physically ordinary.
3. **The averaging proxy is structurally capped at √3.** It scores both the single path
   and the averaged paths against the *same noisy direct edge*, so that edge's own noise
   sits in numerator and denominator alike. Under planted iid noise the true gain is
   2.2395× while the proxy reads 1.4643×. My positive control's "1.45×" was the proxy's
   own ceiling, not evidence it could see 2.24×.

Two further errors compound them. The claimed bar **"ceiling" is a median** over the
best-conditioned decile, not a maximum: the actual maximum at ρ = 0.01 is 0.2557 raw /
0.3093 gauge-fixed, both *above* the 0.2250 I called best achievable. And the headline
0.2250 is a **corner** statistic with the radius dimension dropped — the same data reads
**0.0801 sensor px at field centre** and 0.1168 at the first annulus, against a
gauge-fixed bar of 0.1009. At field centre the aligner is at or inside the bar, which is
the opposite of what I concluded.

The physical corroboration fails too. I used N_eff = N(1+m), implicitly fixing pupil
magnification at one, when this repository already records a *measured* bellows factor
B ∈ [2.41, 3.06]. Under that bound the f/5.6 and f/8 stacks can form green aliases, and
even my own m = 2 numbers put four of seven stacks above the 0.3536 alias start.

**The transferable lesson is that a control can be capped rather than blind.** P5's
positive control reported 1.45× against a √k = 2.24× expectation and I read the gap as
headroom. It was the ceiling. A positive control must be calibrated against *what the
estimator can read when the effect is fully present*, not against the effect's true size.
The same instrument also failed the generator/checker test this lane had already
documented once: reversing composition order inside `flib.then` left all four controls
passing, because `synth_consistent` builds its test data with the same function the
checker uses. That is now the third inert control in this lane.

The one piece of evidence still standing against C1 is weak and does not sustain a kill:
a 63-crop probe over frames and field positions found no radial excess near the alias
boundary on the two stacks examined, so C1 may be *unproductive* on these particular
scenes. Unproductive is not refuted.


> **RETRACTED — everything from here to the end of this lane's section is the claim
> as I originally filed it, preserved so the error is legible. Do not cite it.** C1
> proposes recovering detail
above Nyquist by algebraically unfolding aliased content across a focus stack. It reduces
to a comparison of two numbers in sensor pixels: how precisely registration must be
*known*, against how precisely this aligner actually registers. The bar, derived first,
is **0.1006 raw / 0.1231 gauge-fixed** sensor px at typical conditioning. Recut to the
loosest geometry that exists anywhere in the census (κ ≥ 1 is verified, not assumed —
min 1.0278 over 7680 rows) it reaches at most **0.245 / 0.292**, and only if ρ ≈ 1.

Achievable, measured on the same stacks: **0.267–1.430 sensor px**, median 0.583, once
the cycle floor is recut to the within-DOF spans the unfolding actually uses rather than
the shipped figure pooled over spans 1–128. That recut cuts *against* the verdict, because
cycle-consistency is a self-consistency measure and is blind to systematic error shared
by every edge.

**The one escape was averaging, and it was measured rather than argued.** A global solve
uses many edges, so if per-edge errors were iid the pose would beat the per-edge floor by
~√k — for k of 10–100 that is 3–10×, exactly the size of the gap. Measured directly from
the data with no solver in the loop, the realised gain is **1.07× median** against 2.24×
predicted by iid. The positive control carries this result, because 1.0 is also what a
broken instrument reports: this one reads 1.45× on planted iid noise and exactly 1.000× on
a planted systematic error. Within-DOF registration error is **systematic and does not
average**. Best achievable anywhere, after whatever averaging is really available: **0.225**.

**ρ then settled it, and the finding is physical.** Every stack's scene spectrum sinks into
its own photon shot noise at **f_die = 0.144–0.256 cycles/pitch against a Nyquist of 0.500**,
while the nearest green alias frequency is 0.354 and most lie beyond 0.5. Of 64 band
frequencies, 52–60 must be *skipped* because their own power is already at the floor — a
ratio there is a zero over a zero, and the skipped count is reported separately so it can
never be read as a measured one. The optics agree independently: at m ≈ 2 the effective
aperture is ~3× the marked one, and the resulting diffraction cutoff (0.28–0.55 cyc/pitch)
lands at or just above the measured die-off in all seven stacks. **There is no aliased
content to unfold because the lens cannot form any.** `PREREGISTRATION.md` A7, commit
`32647a47`. A7.4 is flagged EXPLORATORY: the preregistration named ρ but never specified
how it would be measured.

**PHASE's transferable lesson is that a dark frame does not measure the floor that matters.**
Four of five defects in the ρ instrument were noise-accounting errors, and the last was the
finding. A dark frame captures read noise only — 3.8e-06 here — while the dominant floor in
a lit exposure is photon shot noise at 3.3e-04, **87× higher and absent from any dark frame**.
Identifying it needs no model: a diffraction-limited OTF is monotone decreasing to its
cutoff, so a spectrum that is *flat* from 0.2 out to Nyquist is noise by construction.
And **ISO is not a shot-noise lever** — it is gain applied after the photodiode, so varying
it at fixed exposure never moves the electron count. The first exposure control expected the
plateau to track ISO and read ×1.0 over a 13× span: correct, and completely uninformative.
Exposure is the lever; matched-ISO 1/2 s against 1/8 s pairs give plateau ×3.62 (predict 4)
and scene ×1.02 (predict 1) over 10 pairs.

**M-PHASE0-PTC — B1 is a port, not a build.** Its acceptance bar names ±0.0642%
precision as an accuracy target for a quantity whose two best independent measurements
disagree by 1.33%. Its estimator already exists and has already been run in-stack
(M61-E1: 12 subjects, 1554 frames, ISO 50–1000, passing pre-registered control) — the
proposal cites M90 six times and M61 zero times. One named output rests on a mechanism
measured to fail twice and must be struck. `docs/research/M-PHASE0-PTC.md`.

**M-PHASE0-QUINCUNX — C12 survives, and its aperture prediction is wrong.** The
measurement C12 asks for already existed in M129's `snr-w2.json`, whose `high` band
[0.26, 0.33] sensor cyc/px sits entirely above the green plane's 0.25 Nyquist. Scored
against a threshold measured from f/18 — the one aperture that cannot transmit into the
band under any bellows hypothesis, and so measures the instrument's zero — energy is
detected at **4 of 5 apertures**. C12 predicts "f/5.6 yes, f/11 no"; measured, **f/11 is
the strongest aperture in the band** and the cut falls between f/14 and f/18. A wholly
unregistered bonus brackets M129's open bellows factor B to **1.994–2.512**, excluding
two of its three hypotheses at every λ across the stated systematic.
`docs/research/M-PHASE0-QUINCUNX.md`, commit `c7173e2c`.

**M-PHASE0-ZFIELD — A5 survives, and the substrate nearly killed it by artefact.** The
census ran on M66's eight response cubes, no decode. Read at face value the corpus says
**KILL**: median WINNABLE 1.91% against a 2% bar. But the kill is by **EASY saturation**
(median 92.1%), not by LOST — per-pixel σ_z is *too small*, which is the opposite of the
failure A5 feared. That reading is an artefact of the substrate: M66 smooths the response
over 27×27 then 17×17 where the shipping fine field is 5×5 (`FINE_WINDOW_RADIUS = 2`,
`focus.rs:145`; both operators Tenengrad, `focus.rs:782–783`). Comparing sums of squared
kernel weights, the shipping operator's response noise is **6.83×** larger. At that noise
level WINNABLE is **14.02% / 10.12%** at DOF/2 = 1.5 / 3.0 → SURVIVE at both. At the
conservative bound F = 5.40 the wide arm reads 9.03% and is INCONCLUSIVE, so the verdict
is **SURVIVE, NOT ROBUST** and it licenses only the next decode-bearing lane, not A5
itself. `docs/research/M-PHASE0-ZFIELD.md`.

**ZFIELD's transferable lesson is about bias registration, not about depth.** Bias B1 was
registered as "regularisation inflates coherence, favours A5" — but the same smoothing
also shrinks σ_z and inflates EASY, which works *against* A5, and that omitted half drives
the entire census. **When declaring a bias direction, check whether the same mechanism acts
through more than one channel.** Without the F-sensitivity analysis this lane would have
reported KILL on a smoothing artefact.

**ZFIELD also retired an estimator that three controls proved unusable.** The analytic
`σ_z = σ_r/(|D|√2)` conditions on the argmax, and an argmax over pure noise *is* a spike,
so it reports high curvature and therefore high confidence: it called **90.2% and 97.9% of
a pure-noise cube confidently placeable**. A `|D|/σ_r` gate cannot fix this — the null's own
`|D|/σ_r` is 3.66 and 4.97, so any threshold is N-dependent. It was replaced by a
**per-pixel parametric bootstrap** (SG-smooth the measured curve to a working truth, add
fresh noise at the pixel's own measured σ_r, re-run the real estimator, sd over 64 reps),
which drove pure-noise placeability to **0.0%** and turned the bias conservative. That
bootstrap is the lane's reusable instrument: because it adds noise of a *stated* size, it
can simulate a different operator, and that single property is what produced the
F-sensitivity curve and reversed the verdict.

**Pooling gain must be quoted as measured `n_eff`, never window area.** Response noise is
spatially correlated because the operator is a box filter — 1/e at 8 px in x and 12 px in y
on 113MSDCF. A 9×9 window holds `n_eff = 1.54` independent samples against a nominal 81, a
**53× deflation**; the nominal 9× gain is really 1.24×. The measured ladder is 1.03, 1.09,
1.24, 1.57, 2.19 for W = 3, 5, 9, 17, 33. **`max_lag` must be ≥ `max(W) − 1`** or `n_eff` is
silently inflated: truncating at 24 for W = 33 read 2.46 instead of 2.19.

**M128 razor ladder — disqualified three times, and the third names the capture that would
replace it.** The ground cutting edge is too ragged (−31.70%). The one smooth high-contrast
edge is real, but width-dominated: rises fall with aperture where a sharp edge demands a
1.964× rise, and w = 0 is excluded at 2.03σ / 2.50σ. Charging the full green-sublattice
pitch as an instrumental floor — hostile to that conclusion by construction — still leaves
16.70 / 14.74 µm of physical width. Independent verification then closed the last escape:
against a bar of 5% error on recovered `f_c`, straight-line registration passes at **0.02
and fails at 0.03 green px RMS** locus wander (0.205–0.307 µm; interpolated crossing
0.0228) while the blade's measured scatter is **1.23 green px RMS** — **54× over**, and
28× larger than the 0.044 px photon-noise prediction, so it is real subject raggedness and
not estimator noise. Per-column registration does not rescue it: it fails *before any
raggedness is introduced*, biasing `f_c` by **+91.05%** at zero wander with only 0.668 µm
of residual smear, which is self-registration sharpening rather than untracked locus
smear. **The lane is dead and the pipeline needs a straighter subject: a lithographic
chrome-on-glass edge, not a razor.** Amendment A4 in
`experiments/M128-razor-ladder/PREREGISTRATION.md`, tolerance ladder in
`experiments/M128-razor-ladder/out/ragged-tolerance.json` (64 locus plants × 2 noise
realisations per rung, 25 rungs), commit `5ab4b913`.

**M129's four claims were independently confirmed, and its replicate count was not
enough.** Independently written code reproduced C1–C4; all four read `CONFIRMED` in
`experiments/M129-fabric-spectral-ladder/out/verify-a1.json`. The **forward** comparison
is overwhelming — combined **55.0σ** treating the arms as independent and **56.1σ** with
their seed-schedule covariance included, on relative band gaps of 15.3 / 18.0 / 18.9% at
f/11 / f/14 / f/18. The **inverse B̂** comparison under H3 is not: its boundary margin is
**1.33σ** (covariance-aware) to **1.45σ** (independent) at 16 replicates, reaching only
**2.52–2.55σ** at 64. The lane's own stability arm settles it — **77.1% of size-16
subsamples fall below 1.96σ**, and the file records
`sixteen_replicates_enough_for_stable_95pct_margin = False`. Any future claim resting on
the inverse comparison needs more replicates, not more analysis. Note also that holding
the scene fixed *raises* the 64-replicate margin from 2.517 to 2.850, so scene variation
is a real contributor and not negligible.

**Six lane-level defects were found by controls failing, and two by checkers.** In the
two earliest control failures the premise was wrong and the bar was replaced by a
*derived* one rather than relaxed; both errors had made the instrument look blinder than
it was. ZFIELD then failed **four of its eight controls before measuring anything**, and
all four were real: a registered analytic σ_z that under-reported by 1.81×, that same
estimator calling 90–98% of a pure-noise cube placeable, a σ_r estimator disagreeing with
two others by 2.4–4.5×, and a 51× pooling deflation nobody had priced. **A lane that
writes its controls first will usually find that its registered instrument does not
work.** The two checker finds were invisible to controls by construction: every QUINCUNX
"median" was `sorted(v)[len(v)//2]`, the 4th of 6, biased upward — invisible to all five
of that lane's controls because all five compare the lane to itself; and ZFIELD's `n_eff`
truncation passed all eight of its controls identically either way, because none of them
exercises a window wider than the truncation. Both were caught only by a checker that
re-derives the same quantities from the raw data with independently written code. **That
is now the standard for this workstream: a lane's own controls cannot audit the lane's own
summary statistics.**

**And a checker is not exempt: ZFIELD's was commissioned, and it had a defect.** Its
`says()` helper searched the whole document, so a presence check was satisfied by *any*
copy of the phrase. Flipping the §6 verdict from SURVIVE to KILL while leaving §1's
identical copy intact left the checker **GREEN at 170/170** — the single most load-bearing
sentence in the note was effectively unguarded, and no amount of re-running it would have
shown that. The general rule: **a presence-based check is satisfied by any duplicate of
the value, so pin each check to its own anchor and treat an unpinned phrase that occurs
more than once as a defect.** `says()` now reports ambiguity instead of passing, and the
commissioner carries the §6-only flip as a counted plant (9 plants, 9 caught, null control
green) so the repair cannot silently regress.

**The halo complaint is answered.** All four HALO verdicts were false positives. The
instrument walked 2–120 px and took its far reference at 400–900 px, never measuring
120–400 px — exactly the interval where a halo's decay separates it from a scene lighting
falloff. `flat-on-ruler-cpl`'s excursion *peaks outside the measured window* at 107% of its
flagged value; `119MSDCF` never decays out to 900 px; `tweezers-cpl` is one step in a
22,461 DN ramp. A second defect in the same instrument ran the opposite way and passed four
subjects on a partial walk. Facts 1851–1855.

**But that sentence covers one instrument, not two, and I over-broadcast it once already.**
`halo_profile.py` asks whether a *shipping* master carries a bright rim against its own
background, and the answer is no on all 26. The **estimator-vs-pyramid aura** is a different
instrument asking a different question, and its direction survived a dedicated attack: the
estimator measured deeper in all 17 conditioned readings across 4 subjects (excess
294–3446 DN on flower-bud, 334–1127 DN on `bee-2-cpl`, 40–205 DN on tweezers, 5 DN on
lead-1). Only the **28.5× multiplier is dead** — withdrawn by its own author because the
denominator crosses zero and the ratio spans 1.24×–17.70×. The estimator is not the default
backend, so this does not touch the shipping masters; it does constrain any future move to
make the estimator default. Fact 1871.

**The visible magenta is ours, not the lens and not the merge.** strehl's own lateral-CA
correction moves red from −2.009 px inward *past zero* to +0.672 px outward while blue stays
outward, so R and B pile up on the same side of every edge. The lens moves them in opposite
directions, so magenta is the correction's signature. `eps_r = 704.5 ppm` sits above the
entire 500.9–651.9 ppm range of the six measurements quoted three lines from it in
`optics.rs`. Facts 1861–1863.

**But disabling the correction is worse, by 30%.** The statistic that recommended disabling
it counted magenta specifically, and the disabled artifact is the opposite-sign orange/cyan
shape that counter cannot see. Measured hue-neutrally: CA ON 0.15999, CA OFF 0.20807 at
edges, flat control unmoved. The correction is *net beneficial and over-corrected at the same
time*. Fact 1865.

**Two real dust motes**, at −3.63% and −8.24%, found on 12 subject stacks. The flat-field
derived map was mis-registered and would have brightened clean pixels beside an uncorrected
mote; the photograph-derived map replaces it. Fact 1856.

**The merge is in its selecting regime for essentially every mid-frequency coefficient of
every subject** — bands 1–6 average 0.29 / 0.08 / 0.06 / 0.03 / 0.00 / 0.00 % averaged. That
is where the measured 24–240× selection premium applies. Facts 1843–1845, 1849.

---

## 2.3 C2/LCA — STOP, no Rust; the effect is real, the build is not licensed

This is the sixth and last of the triage's claimed closures, and the sixth to come back
negative. `decision = STOP` in `out/c2-audit.json`; no Rust was written, `STREHL_AXIAL_CA_SHIFT`
was not added, and the concurrent `merge_cmd.rs` work was not touched.

**The dispatch was wrong about which claim C2 even makes.** C2 concerns *longitudinal/axial*
chromatic aberration — wavelength-dependent best-focus position along the bracket — not
lateral CA's wavelength-dependent radial magnification. The lane proved the distinction rather
than asserting it: lateral magnification error must be **zero at the optical centre**, but the
independent radius fit puts essentially the whole effect already there, with centre intercepts
of **-0.8183 frames** `[-0.9725, -0.4531]` on lavendar and **-0.8765 frames**
`[-0.9343, -0.8216]` on coffee, both retaining at least half the fitted edge magnitude.
`radial_axial_discriminator.*.passes_axial_gate = True` for both.

**The existence of the effect is not retracted and was never in doubt.** M107 and BUILD-CHROMA
already measured the same physical effect with two other instruments. A registered retraction
scan over 56 files classified all 37 `RETRACT`/`WITHDRAW`/`AMEND` hits and found
`axial_or_forfeit_retraction_found = False`. What fails is the *build* step, not the physics.

**Tone defeated a third lane — but differently, and the difference matters.** Unlike
V-HEADTOHEAD2, the legacy measurement here is black-subtracted native-CFA linear RAW: no
demosaic, no colour matrix, no white balance, no render curve. It is not the same developed-TIFF
contrast artifact. The failure is that the *replacement* tone-invariant metric is underpowered:
the affine-invariant Sobel-energy/local-variance curves retained 24 valid tiles on `coffee-bean`
but **zero** on `lavendar-cpl`, `couch-fibers-cpl` and `bee-2-cpl`, and zero on both registered
lavendar gamma arms (0.8 and 1.2). Direct RAW spot checks match the caches to 7.1e-08 relative
error, so this is the metric genuinely declining, not a cache indexing bug. The required
four-stack tone gate therefore **cannot be evaluated at all**, which files STOP rather than a
refutation.

**The lane filed against its own headline, which is the discipline this program has been
missing.** The preregistered primary arm *passed*: `A = 0.5367 frames`, CI `[0.5101, 0.5883]`,
clearing the historic M107 bar, with all three medians carrying the prior-registered negative
sign and every same-wavelength G1-G2 null clearing the 0.125-frame gate. That arm says SURVIVE.
But a registered field-radius rung moved to NARROWED (`A = 0.5170`, `[0.4237, 0.5883]`) and the
96-plane-pixel tile failed its null gate at 0.1389 frame. The protocol says a category change
anywhere on a registered ladder files NOT ROBUST, so that is what was filed — against a
headline number that had already cleared its bar.

**A protocol breach was disclosed rather than erased.** A preliminary run occurred after
preregistration while the instrument and fixtures were still untracked. Independent review
caught it, and also found that equal G1/G2 peaks had made the external fixture blind to using G1
alone as the green reference. Commit `a50a6ce4` froze a repaired instrument with unequal,
separately fixed G1/G2 inputs and plants the exact G1-only defect. All five preliminary caches
were then deleted and **all 343 RAW frames re-decoded**; `cache.*.reused` is false for every
stack. The lane states plainly that a forward repair cannot make the discarded run
retrospectively compliant, so the chronology breach stands disclosed. Commissioning after the
freeze: **2/2 controls GREEN, 6/6 plants RED**.

**It also found a defect in the prior work it was asked to build on.** BUILD-CHROMA printed each
channel's four gains as an ordered range **without associating values to stack names**, so the
registered per-stack loss mapping cannot be reproduced on three of the four stacks
(`registered_loss_mapping_passes = False` for bee-2, coffee-bean and lavendar). The published
loss *multiset* does reproduce. A number that cannot be tied back to the subject it came from
cannot license a per-stack correction.

Three of nine decision gates are False: `tone_normalised_metric_valid_on_all_four_stacks`,
`gamma_diagnostic_valid_on_lavendar`, and `registered_per_stack_loss_mapping_reproduced`.

Before any build, a new preregistered audit must commission a tone-invariant payoff statistic
that retains valid peaks on all four stacks, freeze the correct per-stack gain association, and
return GO. Only then do the zero-output identity and wrong-sign-harm render bars become
licensed. Independent ultra-verification recomputed every headline NPZ statistic, checked RAW
samples and cache fingerprints, and returned VERIFIED for STOP/no-Rust.

### 2.3.1 The triage is now wrong on six of six

Every claim the decision-value triage marked as a high-value closable win has come back
negative: DPAR (linear plant on a curved track), DECODE (compressed-input vs allocated-output,
harness absent), NVME (never actually measured), SPLIT (numbers reproduce exactly, closure still
fails), VEIL2 (0/7 gates), and now LCA (STOP, and the claim was mislabelled in dispatch).

The generalisable law, stated once more because it has now cost six lanes: **a paraphrase of a
measurement is not the measurement.** Re-run it, do not re-read it. LCA sharpens the law —
here the paraphrase was wrong about *which physical effect the claim concerned*, and no amount
of careful reading of the summary would have caught that. Only going back to the measurement did.
## 2.4 D8b/SPLIT2 — the capture is genuine, the geometry is not; detail now rests on one instrument

The last available route to an FRC instrument is closed for now, and the reason is a capture
setting rather than a flaw in the idea. **Verdict: NOT ROBUST / NO BUILD.** Rust unchanged.

**The metadata gate passed, and it mattered that it was run.** `12-bee-iso-var-no-bracket-32-repeat-diff-light`
is exactly what its name claims: 576 genuine no-bracket exposures, two light passes, nine ISOs,
32 repeats per ISO, f/5.6, 1.6 s, 200 mm, manual focus, and an invariant reported focus distance
of `0.273841307296975 m`. The gate was mandatory precisely because a directory name is not
evidence — but here the name was honest, and the capture is the genuinely independent repeats
that same-frame splitting could never provide.

**The capture is defeated by its own stabiliser.** The preregistered pixel gate found the frames
do not sit still: at ISO 50 only frame 0 remained at `(0,0)`, while 21 frames shifted one quad
pixel and 10 shifted two. **Image stabilisation was on.** At 1.6 s and 200 mm on a static rig,
IBIS does not remove motion between frames — it introduces it.

**The lane then did the honest thing twice over.** On learning that the independently registered
scorecard permits analytical translation, it amended its protocol *before* retaining any FRC
outcome, implemented commissioned Fourier phase-ramp registration, and applied the scorecard's
`0.10` native-pixel non-translation RMS gate. Registration rescued one illumination block and
not the other:

| ISO-100 light block | Fourier gate | Independent OpenCV ECC | Verdict |
|---|---:|---:|---|
| Bright | `0.064031` native px | `0.070005` | PASS |
| Second light | **`0.107703`** | **`0.105202`** | **FAIL** |

Two independent registration implementations agree to within `0.003` native pixel on both
blocks. The second-light block reverses the decision across the illumination ladder, which files
NOT ROBUST. The roughly 1 EV blocks were evaluated separately and **never pooled**, so weaker
illumination could not be used to rescue a geometric failure.

**Commissioning: 17/17 plants RED.** The alignment control recovered an externally imposed
`(1.25, -0.40)` quad-pixel shift to within `0.02` pixel; the wrong-sign arm failed as it should;
a known `0.12` native-pixel local warp read `0.123288` and correctly failed. The
data-dependent-tuner plant — the trap this lane itself identified after D8 — stayed RED: full
evaluation leakage drove FRC to exactly `1.0`, and perturbing only `D` changed `C` by
`25.002575`.

**It stopped rather than measuring past a failed gate.** The real repeat-pair null against
`0.25`, the comparisons with the historical `0.438734` / `0.972099` values, sharpening
invariance, and any FRC crossing were deliberately **not measured** once the geometry gate
failed. Nothing above `0.25` cycles/native-pixel was claimed.

### 2.4.1 The detail axis now rests on the slant edge alone

This is the program consequence and it is worth stating flatly. The governing proposal's success
statement (`2026-08-sota-path.md:192-197`) specifies the detail instrument as **"D1: FRC +
slant-edge"** — two instruments. D8/SPLIT removed same-frame split FRC as invalid, because two
halves of the same frames are not independent. SPLIT2 was the remaining route to a legitimate
FRC, and it is blocked on capture geometry.

So the most contested axis on the scorecard — the one whose previous measurement was retracted
as a tone artifact — currently has **one** instrument where the proposal called for two.

**This failure is cheap to reverse, and the fix belongs to the owner.** The capture itself is
correct in every respect the lane could check; only stabilisation spoils it. A recapture of the
same subject with **IBIS/SteadyShot switched off** would very likely clear the `0.10` gate on
both light blocks and hand the detail axis its second instrument back. That is a far better
position than the one D8 left, where the idea itself was dead.
## 2.5 The scorecard self-baseline — all twelve axes UNMEASURED, and the reason is the product

The first independent attempt to fill in the scorecard returned **UNMEASURED on every axis**. The
lane is `docs/research/SCORECARD-BASELINE.md`, frozen against scorecard v1.1
(`11a754a6…`), a frozen binary `strehl 0.0.0 (4b60b1ba9f56)` and a pre-render freeze at
`bc8f315a`.

**No axis was blocked by the instrument. All eight rendered arms failed a gate that sits *before*
any metric runs.** An independently commissioned affine reader measures **`0.2901%`–`0.4619%`
scale disagreement** between strehl's renders and their references, against a `<=0.10%` bar
(`out/GEOMETRY-AUDIT.json`, `all_scale_invalid = true`). The required common ProPhoto-TIFF input
adapter is also absent.

**The geometry audit is properly commissioned, so this is not an artefact of a hair-trigger
gate.** Its identity null reads `0.0%`; its **translation-only null reads `0.008%` and passes**,
so pure translation does not trip the scale gate and there is no false positive; and a planted
scale-plus-rotation defect at `0.3031%` correctly fails. The real renders read `0.2946%`,
`0.3019%` and `0.2901%` — **the shipping renders sit almost exactly at the magnitude of the
deliberate defect plant.**

### 2.5.1 The mechanism is strehl's own documented default

This is not a mystery and it is not a bug report against the scorecard. It is the shipping
default behaving as designed:

* `align_cmd.rs:1003` — `pub const DEFAULT_COVER_MODE: CoverMode = CoverMode::Scale;`
* `align_cmd.rs:957` — `CoverMode::Scale` *"shrinks the reference grid by `k <= 1` about the
  plane"* so that every frame covers the output.
* `align_cmd.rs:966,990` — `CoverMode::Crop` instead *"renders the covered rectangle at unity
  scale"* and composes nothing.
* `align_cmd.rs:975` already concedes *"`CoverMode::Scale` is still the default. There is a
  second price…"*
* `merge_cmd.rs:3272-3276` prints the banner the baseline lane independently observed:
  *"field of view scaled to {k:.4} so that EVERY frame covers…"*
* `examples/build-resamp-mtf.rs:268` exists precisely to measure it — *"the fit_to_cover coverage
  upscale, ALONE, catmull-rom"* — and `strehl-core/src/align.rs:2754` records **+0.0179 dex** for
  removing the coverage rescale.

**strehl's default output path applies a resampling the comparator does not.**

### 2.5.2 This is the first actionable SOTA lead the program has produced

A 0.3% scale change across a 3516-pixel axis sweeps sampling phase through every sub-pixel
offset — zero displacement at the centre, ~10 px at the edge. A large fraction of the frame is
therefore interpolated at or near half-pixel phase, where Catmull-Rom loses substantial energy
near Nyquist while costing almost nothing at low frequency.

That predicts the measured competitive pattern in §2.2 exactly:

| Band (cyc/px) | Measured | Resample loss predicts |
|---|---|---|
| 0.02–0.05 | strehl **LEADS** `1.0833` | ~no loss |
| 0.05–0.10 | unresolved | small loss |
| 0.10–0.20 | strehl **TRAILS** `0.8842` | growing loss |
| 0.20–0.30 | trails badly | largest loss |

A deficit that worsens monotonically with spatial frequency is the signature of a resampling
kernel, not of a stacking-quality difference. **If that is the cause, strehl is not losing detail
in its merge at all — it is discarding it in its output geometry, and the switch already
exists.** The V-HEADTOHEAD3 lane has been tasked to re-render with `--cover crop` and re-run the
band ratios, with the field-of-view and ROI-pairing traps stated explicitly. Either outcome is
useful: a recovered trail is a real product win, an unchanged trail eliminates the most plausible
confound and hands phase 1 a clean target.

**This is a hypothesis with a mechanism and a prediction, not a result.** It is not recorded as a
finding until that arm runs.

### 2.5.3 What the baseline established along the way

Read as a census rather than a scorecard, the lane is not empty:

* **M7 colour** — `traceable tilted target candidates: 0`. Independent confirmation that the
  capture blocker in §4.0 is real and not an oversight.
* **M6 clipping** — the rail census proves the high arm is under 10,000 even before alignment:
  salt `1,193`, battery `1,230`, angled ruler/grid `0`.
* **M9 certification** — matching bee dark/flat groups `0/0`, and the shipping default **emits no
  licensed-band acuity or variance certificate at all**.
* **M10 depth** — no depth product exists; the ruler record says only *"approximately 10.26 deg"*.
* **M1/M2 diagnostics** (invalid as scores, retained as diagnostics): cutoff `0.15` on both bee
  lights, `S_25` of `6.20e-5` and `6.34e-5`; M2 medians `1.8483` and `2.5156` against an
  `eta <= 1.10` bar, affine slopes `1.0630`–`1.0687`.
* Nothing above `0.25 cyc/native px` was inspected or reported.

**Its commissioning is real.** The M1 instrument moved `0.080 cyc/px` on a planted pre-sensor
blur while untuned nulls held at `0` for common pattern movement and — notably — `0` for
**unsharp movement**, i.e. that instrument is invariant to unsharp masking rather than rewarded by
it. M2 rose `0.2315` on a planted `0.25 sigma_1`, and a blur that lowered noise to `0.3265x`
was caught widening the edge `3.4155x`.

The lane also confirmed it will **reuse the V-HEADTOHEAD3 instrument** rather than build a
competing one, and correctly declined to retrofit V-HEADTOHEAD3's numbers into its own frozen
run.
## 2.6 The detail axis has no admissible instrument at all

Commits `a60a7b6b` (preregistration) and `422e009d` (verdict). Note
`docs/research/M-PHASE0-SLANTEDGE.md`; audit `experiments/M-PHASE0-SLANTEDGE/`.

The proposal at `docs/proposals/2026-08-sota-path.md:192-197` prescribes **"D1: FRC +
slant-edge"** — two instruments for the detail axis. The scoreboard for that prescription is
now complete, and it is empty:

| instrument | state |
|---|---|
| split FRC | dead — D8, KILL / STOP_REMOVE_RUST |
| repeat-pair FRC | blocked on a physical re-shoot with IBIS off — D8b, §2.4 |
| slanted-edge SFR/MTF | **refused** — every implementation rewards sharpening |

**No axis of the SOTA scorecard can currently be measured for detail.** This is a structural
finding about the program, not a result from one lane.

### 2.6.1 Three implementations, one failure, and it is the one that matters

The commissioned search covered `experiments/`, `docs/research/`, `crates/` and `scripts/`.
Three real implementations exist — `M88-optical-ceiling/src/m88lib.py` (canonical ISO-12233-style
RAW SFR), `M104c-mtf/mtf.py` (compact reimplementation), and `BUILD-RESAMP/slanted_edge.py`
(rendered-raster MTF50/SFR). M88b and M128 are adapters around M88; the Rust hits are analytic
kernel models, not image instruments; `scripts/` has none.

The decisive arm applied unclipped float unsharp masking, radius 1.0, amount 0.5, **after
rendering**. It adds no independent scene information. Every implementation scored it as improved
resolution and **none of the three flags or refuses it**:

| candidate | USM ratio | verdict |
|---|---:|---|
| M88 SFR→MTF50 | `1.098673` | +9.87%, no detector |
| M104c | `1.098679` | +9.87%, no detector |
| BUILD-RESAMP | `1.092354` | +9.24%, no detector |

### 2.6.2 Why this cannot be dismissed as a dead metric

This is the part that makes the verdict binding, and it is the discipline six earlier lanes
lacked. **The audit included a genuine-improvement arm, and all three implementations passed it.**

| arm | truth | recovered across the three |
|---|---:|---|
| identity null | exact | bit-exact in all three |
| added sigma-0.75 blur | `0.894427` | `0.894870` – `0.900002` |
| **genuine sigma-1.20 improvement** | `1.25` | `1.238651` – `1.248849` |

Both quantitative arms clear the frozen 5% bar in every implementation. So these are not
constant-zero, wrong-signed or blind statistics: **they track real blur and real resolution gains
correctly, and still cannot distinguish sharpening from resolution.** A degradation-only audit
would have passed all three. This is the concrete case for the standing rule that an audit needs
an improvement arm as well as a defect arm.

### 2.6.3 The other defeats, and one contrast worth keeping

Sharpening is the disqualifying failure, but it is not the only one. Tone: affine moved MTF50 by
numerical zero (expected from DC normalisation, and **not** monotone-tone invariance), while
gamma 3 raised it **17.41–17.67%** and a strictly increasing logistic raised it
**49.30–50.71%**, undetected on every path. Noise: M88 scored 13/24 noisier arms *above* base, up
to **+55.91%**; BUILD-RESAMP 14/24, up to **+15.78%**; M104c none above base but collapsing to
`0.202`–`0.282x`, which is failure to separate rather than robustness. The 0.25 licence bound is
vulnerable in all three — each returns a number in `0.309`–`0.312` where it should refuse.
Demosaic exposure is protected only in M88, by its canonical linear-RAW G1/G2 scope.

**The contrast that matters:** V-HEADTOHEAD3's ordinal band statistic *is* invariant to monotone
point transforms — affine, gamma-3 and logistic moved it by exactly 0 while raw band power moved
30.4%. The slant-edge paths are not. The competitive position in §2.2 therefore rests on a
strictly better-behaved statistic than anything the detail axis was supposed to use.

### 2.6.4 The audit rig is now the program's best asset here

`measure.py` generates plants without calling any candidate's synthetic helper. `commission.py`
runs measurement as a child process, imports neither generator nor candidate, and compares only
serialized values against literal analytic predicates. It passed an all-GREEN literal fixture
first, then caught **8/8** single-property sabotages: identity, blur, true improvement,
sharpening, tone, noise, angle and licensing. It is reusable, and it is being reused to test
whether any surviving statistic can hold the detail axis.

**Not verified:** no physical chart or capture was opened, so transfer to a correctly tilted real
capture is unknown. The corpus lint is blocked by six pre-existing violations in
`M-PHASE0-SPLIT*.md`, none introduced here.

## 2.7 Both surviving detail candidates fail; one of them was holding up §2.2

Commits `1639efc4`, `e4b95d3c`, `09977acc`. Registration
`experiments/M-PHASE0-SLANTEDGE/SURVIVOR-PREREGISTRATION.md`; results at
`docs/research/M-PHASE0-SLANTEDGE.md:145`.

With slant-edge refused (§2.6), two statistics elsewhere in the program looked like they might
hold the detail axis: **SCORECARD-BASELINE's M1**, whose own commissioning reported unsharp
movement `0`, and **V-HEADTOHEAD3's licensed ordinal Q25**, proven invariant to monotone point
transforms. Both were run through the §2.6 rig **with no threshold changed**. Neither is
admissible.

The rig was tightened for this: candidate functions were copied verbatim into the audit tree, and
a separate process verified **3 full source hashes and 11 function ASTs before every run**, so a
candidate silently drifting out from under the audit is detected rather than assumed away. The
checker imported neither plants nor candidates, passed a literal all-GREEN fixture, then caught
**10/10** single-property sabotages including source drift. Two complete child-process runs were
bit-for-bit deterministic. An independent verifier passed it on 74 report comparisons, zero
failures.

### 2.7.1 Q25 rewards sharpening by +456% and misses real improvement entirely

| arm | licensed Q25 (base `9.52160e-4`) | |
|---|---:|---|
| identity | `1.000000x` | |
| physical sigma-0.75 blur | `.841501x` | responds; misses the `0.894427 ±5%` bar |
| **genuine sigma-1.20 improvement** | **`.977981x`** | **wrong sign, −2.20%** |
| **post-render USM r1.0/a0.5** | **`5.560744x`** | **+456.07%** |
| affine / gamma-3 / logistic | `.999963 / 1 / .999966` | **tone bar PASSED** |
| noise | median `17.0056x`, range `15.9320–18.3498x` | |

**Q25 disposition: REFUSED.**

Two things must be said together. **The tone-invariance claim in §2.2 is confirmed by a harness
that never touched that lane's code** — `.999963/1/.999966`. That was the claim the whole
instrument was built to establish, and it survived external audit intact.

**And the same statistic inflates 5.56x under information-free sharpening while a real
resolution gain reads −2.2%.** §2.2 reported strehl tied against sharpening-0 PMax
(`0.9735 [0.8339, 1.1406]`) and trailing 3.5x against sharpening-40. A statistic with this
response manufactures exactly that pattern from the comparator's sharpening alone. **The
competitive position is amended accordingly: the sharpening-0 tie is the honest comparison; the
high-band deficit is unproven.** The NOT ROBUST verdict stands and is now explained rather than
merely declared.

A lead about the construction, not just a defect: the **historical `A20_25` moved the opposite
way under USM, `.591780x`**. Restricting the numerator to `[.20,.25)` to respect the 0.25
licensing bound appears to be what introduced the sharpening reward. `A20_25` cannot rescue the
result — its six-band denominator reaches 0.40 and is unlicensed, and it misses both physical
bars and the noise bar — but the direction change locates the problem.

### 2.7.2 M1's cutoff is blind; its second output is the most promising thing found

| native field | base | identity | blur | improvement | USM |
|---|---:|---:|---:|---:|---:|
| `f_licensed` | `.150000` | `1.000000x` | `1.000000x` **RED** | `1.000000x` **RED** | `1.000000x` GREEN |
| `S_25` | `6.68974e-5` | `1.000000x` | `.226526x` **RED** | `8.274764x` **RED** | `.995819x` GREEN |

**The claim-bearing cutoff is `USM_INVARIANT_BUT_BLIND`.** `f_licensed` sits pinned at its `0.15`
floor for base, blur, real improvement *and* USM. This is the exact failure mode the audit was
sent to distinguish, and it was named rather than reported as a pass — an instrument reading `0`
under sharpening is only invariant if it still moves under real resolution, and this one does not.

**`S_25` is a different story and is worth keeping.** It moves strongly in the correct direction
under both physical arms — `.226526x` under blur, `8.274764x` under genuine improvement — while
USM changes it by only **−0.418%**. That combination is precisely what the detail axis needs and
nothing else in the program has shown it. It is not admissible as it stands: it is not calibrated
to MTF50, it fails the unchanged ratio bars, and it is defeated by tone (gamma-3 `4.8400x`,
logistic `18818.9045x`), by noise (median `.330086x`, range `.004972x–10.381863x`, so some
noisier arms score much *better*), and by angle (`1.42205/1.18548/1/.65802`). **M1 disposition:
NOT COMMISSIONED.**

**Scope limit, stated by the lane and not by me:** this synthetic adapter cannot adjudicate the
formal scorecard M1, which has a registered tile-eligibility denominator and dark/flat noise
floors the plant does not supply. The verdict is against M1 *on this fixture*.

### 2.7.3 Where the detail axis now stands

Every candidate the proposal named or the program produced has been tested and refused. The
detail axis has **no admissible instrument**, and the competitive position rests on a statistic
now known to reward sharpening. Two routes remain, and they are not equivalent:

1. **The owner's IBIS-off re-shoot (§4.0).** Restores repeat-pair FRC, whose protocol and 17/17
   plant battery are already built. This is the critical path and it is blocked on a physical
   capture.
2. **Harden `S_25`.** It already has the sharpening/blur/improvement behaviour; what it lacks is
   tone, noise and angle robustness. That is a build, not a discovery, and it is the first
   constructive lead the detail axis has had.

## 2.8 The phase-1 kill gate fired, I challenged it, and it survived

Commits `e64fca59`, `4bada8e3`, `6b9eb171`, `0c503d84`, `345ef331`, `0eadaa54`, `da00deba`,
`99fe6a5f`, `7d5c58fc`. Artifact `experiments/PHASE1-DESIGN/results/gate.json`.

W1 is the kill gate for all of phase 1 — W2, W4 and W5 depend on it. It swept a single global
band-width constant `k` from `0.00` to `8.00` in steps of `0.05` (161 arms) across
`flat-on-ruler-cpl` (79 frames), `coffee-bubbles` (19) and `113MSDCF` (63), against 42 width
predicates. **It returned `NO_COMMON_K`**, with `width_survivors: []`, `passing_k: []` and
`selected_k: null`. Commissioning sealed with five SHA-256 hashes and `commissioning_status:
PASS`; 17/17 synthetic nulls GREEN and plants RED; `design_sha` correctly pins `fe111781`.
`table`, `metrics` and `render_provenance` are empty, which is **correct**: the protocol stops
before rendering when there are no survivors, so no Pareto numbers were computed or invented.

**By its own terms this halts phase 1 cheaply, before a line of production Rust was written.
That is exactly what a kill gate is for, and the lane executed it properly.** I am still not
recording it as decisive, for the reason below.

### 2.8.1 No `k` clears the gate, and bands 4-6 never clear it at all

> **Corrected after re-reading `gate.json`. My first version of this subsection said "all 42
> predicates fail at all 161 arms". That is false, and the truth is a stronger result.** The
> counts below are recomputed from the file, not from any summary.

The gate evaluates **42 predicates** — 3 captures x 2 ROIs x 7 bands — at each of **161** `k`
arms spanning `k = 0.00` to `8.00`: **6,762 evaluations**, of which the file records **6,518
failures**. So **244 evaluations pass**, and 135 of the 161 arms have at least one passing
predicate. No arm passes all 42, which is what the gate requires, so `pass` is `false`
everywhere — but "everything fails everywhere" was my error.

**What actually fails is structural, and it is sharper than a blanket failure would be:**

- **16 of the 42 predicates pass at some `k`. The other 26 never pass at any `k`.**
- **Every predicate that ever passes lies in bands 0-3. No predicate in band 4, 5 or 6 passes at
  any `k` in the entire sweep, for any capture, in either ROI.** That is an 18-predicate wall.
- The best arms in the sweep reach **4 of 42** (`k=1.90`, `1.95`, `2.15`, `2.20`, `6.85`, `6.90`).
- Passing predicates cluster in the `flat` ROI and in the finest band: `113MSDCF flat band 0`
  alone accounts for 119 of the 244 passes.

The failures decay monotonically with band index. At `k=0.60`:
monotonically with band index. At `k=0.60`, the best arm:

| band | detail ratios (3 captures) | flat ratios |
|---|---|---|
| 0 | `.4588 .4755 .6367` | `.0895 .2142 .5868` |
| 2 | `.1437 .2006 .1790` | `.1375 .4933 .1902` |
| 4 | `.0356 .0647 .0509` | `.0470 .0705 .0510` |
| 6 | `.0160 .0604 .0166` | `.0160 .0562 .0270` |

The bar wants ratios within 5% of `1.0`. **Nothing is near `1.0`; everything sits far below it
and roughly halves each band.** Best `worst_error` across the whole sweep is `0.984017` against a
`0.05` bar — **19.7x over** — and it is pinned at that same value across all 35 arms from
`k=0.60` to `k=2.30`.

**And `113MSDCF` band 6 flat holds exactly one value, `0.015983`, across all 29 arms from
`k=0.60` to `k=2.00`** — bit-identical through a 3.3x change in the swept parameter, while band 0
swings from `0.4588` to `1.6012` over the same range. That froze my reading at the time: a
predicate that does not respond to the swept parameter cannot license a conclusion about it, so I
challenged the kill rather than record it.

**The challenge was wrong and the plateau is real behaviour** — §2.8.2 has the mechanism, and I
have since confirmed every figure against the file: the value is `1/62.5652 = 0.015983` to six
places, and **the first change is at exactly `k=5.1500`**, where it steps to `0.016177`. It is a
staircase, not a flat line, and the sweep's densest region happens to sit on one tread.

### 2.8.2 My challenge was wrong. The kill stands, and phase 1 is stopped

**W1 refuted the resampling hypothesis on all four points, with mechanism, and I accept it.** I
said I would record the kill as decisive if it survived the challenge. It survived.

**1. The ratio is not a cross-implementation width comparison.** Numerator is the ROI-mean
**candidate Kish `n_eff`** at that `k`; denominator is the ROI-mean **legacy gate-4.5 Kish
`n_eff`** on the same band, same ROI, and byte-identical rawpy-aligned samples
(`measure.py:152-280`). **No Rust merge output supplies either side.** A resampling difference
between reference and production therefore cannot enter, and my whole hypothesis was
inapplicable.

**2. I had the band ordering backwards.** Band indices run **fine to coarse**, so bands 5 and 6
are the *coarsest*, with nominal Nyquists of `0.0078125` and `0.00390625` cyc/output-pixel — far
**below** the `0.25` licence, not above it. The `[0.10, 0.25]` interval applies only to
post-reconstruction Pareto metrics, never to width predicates. Nothing was clipped.

**3. The frozen `0.0160` is a real admission plateau, not a dead predicate.** For `113MSDCF`
band 6 the candidate `n_eff` is exactly `1.0` from `k=0.60` through `k=2.00` — winner-take-all,
one frame admitted — while the legacy means are `62.4113` (detail) and `62.5652` (flat). The ratios are
therefore the reciprocals, and I confirmed both against the file to six places: detail
`1/62.4113 = 0.016023`, flat `1/62.5652 = 0.015983`. They are constant because the admission set
does not change. **The first admission transition is
`k=5.15`.** The predicate does respond to `k`; it responds in steps, and that range sits inside
one step.

**4. `k=0.00` is not an identity.** With unique `q_w>0` it admits only the winner (`n_eff=1`);
exact energy ties are also admitted; if `q_w=0` every frame gets unit weight (`n_eff=N`). The old
negative sentinel was explicitly removed. So 42/42 failing there is expected behaviour, not
miscalibration.

**On the `--cover crop` experiment specifically:** `strehl align` has no such option — cover mode
belongs to the merge command. More to the point, **W1 applies the raw sidecar unchanged to frozen
interior ROIs, so it is already Crop-equivalent in sampling geometry.** A rerun could not move
these ratios without changing the measured object to production output, which would violate the
sealed gate. Refusing the experiment was correct.

**Independent recomputation reproduced the full 161 x 42 = 6,762-evaluation grid exactly**,
matching every one of the 6,518 stored failure records, and again found zero arms clearing all 42.

### 2.8.2.1 What the kill actually means

**No single global `k` makes the banded candidate's effective sample count match the legacy
merge's across all bands and ROIs, and the obstruction is a wall rather than a near miss.**

The mechanism and the band structure agree, which is what makes this convincing. Kish `n_eff`
measures how many frames actually contribute. The legacy merge averages heavily in the coarse
bands — about **62 frames** at `113MSDCF` band 6. The candidate, at every `k` the sweep visits
below `5.15`, admits **one**. **The coarser the band, the more legacy averages, and the further
the candidate falls behind; no constant closes a gap that grows with band index.** Raising `k`
far enough to admit more frames at the coarse end drives the fine end past the bar in the other
direction — band 0 has already overshot to `1.6012` by `k=2.00`.

That is exactly the observed pattern: **bands 0-3 can be made to pass somewhere, bands 4-6 never
pass anywhere**, and the two ends want opposite values of the one constant on offer.

**Phase 1 as designed is stopped.** Its premise was one fixed global constant; the gate tested
exactly that premise and falsified it before a line of production Rust was written. W2, W4 and W5
do not proceed. **This is the kill gate working as intended, and it is the cheapest result this
program has bought.**

One caveat recorded deliberately: matching legacy `n_eff` was the design's own preregistered
acceptance criterion. A better algorithm might legitimately differ from legacy rather than match
it. **That objection is not available now** — the bar was registered before measurement, and
relitigating a preregistered criterion after seeing the outcome is the exact failure this
repository guards against. If the criterion was wrong, that is a finding about the design lane's
choice of bar, to be argued on its own and before the next gate, not a reason to reopen this one.

### 2.8.3 The `cover=scale` defect is real, larger than I thought, and independent of phase 1

The hypothesis failed for W1 but the defect it pointed at is documented in the source itself, and
the numbers are worse than the scorecard's figure implies. `align_cmd.rs:944-1000`:

> *"The dropped field of view is paid for by an upsample of `1/k` at every pixel of every render,
> and because `S_k` rides on every placement, the reference frame — whose placement is the
> identity, and which would otherwise pass through the interpolator untouched — is resampled
> too."*

| stack | frames | `k` | implied upsample `1/k − 1` |
|---|---:|---:|---:|
| `109MSDCF` | 22 | `0.9870` | **1.3%** |
| `bee-1-cpl` | 299 | `0.9321` | **7.3%** |

> *"`k` falls as the stack deepens … so the tax is worst on the deepest stacks."*

**The scorecard's `0.2901%–0.4619%` is a disagreement between two renders, not the absolute
rescale.** The absolute upsample is **1.3% at 22 frames and 7.3% at 299 frames**, and
`bee-1-cpl` — the scorecard's own performance master — is the 299-frame case. Selection is
`--cover` flag, then `STREHL_COVER` env, then the `Scale` default (`merge_cmd.rs:2686`);
`STREHL_COVER=0` is a *third* mode (`Skip`) that leaves uncovered edges and is not a valid
control. Crop's own price is documented too: output dimensions change to about `k*W x k*H`, and
"the merge still runs on the full plane, so frames that do not reach the border still fold their
black fill there, and the pyramid's coarse bands spread that fill inward some distance before the
crop discards it."

**This is now the program's most actionable product lead and it belongs to the head-to-head lane,
not to phase 1.**

### 2.8.4 The old hypothesis, kept for the record — **SUPERSEDED, and wrong**

> **Everything in this subsection is my refuted challenge, preserved because a program that
> deletes its wrong turns cannot be audited. It is wrong on the mechanism, wrong on the band
> ordering, and wrong that W1 was a third confirming direction. §2.8.2 has the correction.
> Two confirming directions for `cover=scale` remain, not three: the scorecard geometry gate and
> the head-to-head band pattern.**

A monotone deficit that worsens with every band, present at every `k` including the sentinel, is
the signature of a **resampling difference**, not a width mismatch. Two sibling results found the
same shape independently:

- the scorecard baseline's geometry gate, `0.2901%–0.4619%` scale disagreement against a `0.10%`
  bar (§2.5), traced to `DEFAULT_COVER_MODE = CoverMode::Scale`;
- the head-to-head's band pattern, leading at 0.02–0.05 cyc/px and trailing monotonically worse
  to 0.20–0.30 (§2.2).

W1's reference is an independently written Catmull-Rom pull via rawpy/LibRaw; the production path
applies the coverage rescale. **If production resamples by ~0.3% and the reference does not, the
two diverge further in every higher band — which is the table above.** The lane has been sent
back with four questions and one decisive experiment: **re-run the sweep under `--cover crop`**
(unity scale, `align_cmd.rs:966,990`). If the ratios move toward `1.0`, `NO_COMMON_K` is an
artifact of a known product defect. If they do not, the kill stands and is far stronger for
having survived. Also outstanding: whether bands 5–6 lie outside the `[0.10, 0.25]` cyc/px
frequency licence and should never have been allowed to bind the verdict at all.

### 2.8.5 A scorecard holdout capture is burned, by my error

**`calibration-grid-1 sw4` is no longer untouched holdout evidence.** I launched W1 against it in
parallel with the scorecard baseline lane without realising it was holdout. I halted W1 on
reading the leakage boundary in `2026-09-phase1-design.md` §3, but too late.

**W1 disclosed the leak plainly and unprompted, on line one, twice.** Before the halt it had
observed sw4's complete 161-value width sweep and the sentinel readings **detail `1.063350`,
flat-power `1.329831`**. It quarantined the pilot in `0c503d84` and retargeted onto three
non-holdout captures, each of which I verified against the scorecard manifest before unblocking
it. The scorecard owner has been asked to mark sw4 burned and to determine whether any
same-subject partner is compromised with it.

**The cost is bounded by luck, not by process:** the frozen baseline (`bc8f315a`) returned
UNMEASURED on all twelve axes, blocked before any metric by the geometry gate, so no axis had yet
been scored on sw4. The contamination costs a future holdout, not a result already taken.

**The process lesson is mine.** Two lanes were pointed at the same capture for different purposes
because I did not check the capture manifest before launching. Verifying capture roles is now
part of launching any lane that reads real data.

**Escalation, confirmed after the scorecard owner audited the boundary (`e68f40f7`, scorecard
v1.2): the burn is not one capture but five, and it blocks three axes.** The holdout unit is
subject plus uninterrupted session, so burning sw4 burned the whole
`30-calibration-grid` group. I verified this independently rather than taking it on report: the
five stacks run contiguously on 2026-09-01 from **20:57:42 to 21:09:06** and their frame counts
match the manifest exactly. **M1, M5 and M9 cannot pass scorecard v1.2 until a fresh
subject/session replaces them** — now the highest-priority owner capture request, §4.0 item 2.
The scorecard also now carries a literal labelling rule: only a row whose evidence class begins
`HOLDOUT` is holdout, and burned, development, control and historical rows all say
`NOT HOLDOUT` explicitly. That closes the ambiguity my launch exploited.

## 2.9 The program's shape after phase 1, and the one thing blocking everything

### 2.9.1 The honest position

Thirteen-plus phase-0 gates are closed and **every one is negative or neutral.** Phase 1 was
designed, gated and falsified before a line of its production code was written. The only
production Rust this program has merged is `1da5e87b`, and independent verification found it
**defective** — its byte-freeze row was weakened rather than strengthened, and its claimed speedup
recomputes to `0.948029x`, i.e. about 5% *slower*, from runs taken under 19.6–38.8% external load.

**So: net verified product improvement to date is zero.**

That reads badly and I am recording it plainly, but it is not the same as no progress. The prior
corpus was rejected precisely because it accumulated claims that did not survive scrutiny. This
session's product is a program that **refuses to fool itself**: six generator/checker cancellations
found, three prescribed fixes that carried their own defects caught before application, a headline
of my own overturned by my own lane, and a build path killed by its own preregistered gate at the
cheapest possible moment. **A stacker that cannot tell whether it improved is not one gate away
from SOTA; it is one instrument away.** Which is the next subsection.

### 2.9.2 The binding constraint: the program can prove things are wrong and cannot prove anything is right

Every refusal above shares one cause. **There is no admissible instrument for the detail axis**
(§2.6, §2.7), and detail is the axis on which a focus stacker is judged. Three slant-edge
implementations reward a post-render unsharp mask by ~+9.9% with no detector; `Q25` rewards it
`5.560744x` while reading a genuine improvement at the wrong sign; `S_25` survives sharpening but
moves `18818.9045x` under a logistic tone curve. Split-frame FRC is dead by construction (D8) and
repeat-pair FRC is blocked on an IBIS-off re-shoot (D8b).

**This is the critical path and everything else is downstream of it.** A correct fix cannot be
scored, so it cannot be defended; an incorrect one cannot be caught. Lane **INSTRUMENT** now owns
the question of whether an admissible instrument is obtainable from the captures that exist —
including whether repeat-pair FRC can be rescued from IBIS-on data, which if answered "no"
converts the owner re-shoot from desirable to **required**.

### 2.9.2.1 The scorecard can no longer express its own most important axis

**M1, detail, now has no statistic and no numeric bar.** Scorecard v1.4 (`64d9d675`) withdrew
`S_25` outright at my request, on the evidence in §2.7: it moves `18818.9045x` under a logistic
tone curve, and the alternative `f_licensed` is blind. I asked for a plain withdrawal rather than
a weakened bar, on the principle that **an honest gap is worth more than a bar that cannot be
met** — a bar nothing can satisfy would have read as a pending measurement instead of a missing
instrument.

This is the instrument crisis (§2.9.2) written into the measuring device itself. The scorecard is
the program's own definition of SOTA, and **it currently has no way to state whether this stacker
resolves more detail than Zerene or Helicon.** Overall SOTA therefore remains `UNMEASURED`, and
will remain so on that axis no matter how much engineering happens, until lane INSTRUMENT
produces something admissible.

**Axis readiness, from the owner's v1.4 triage:**

| axis | status |
|---|---|
| **M8** invented values | **(e) measurable now — the only fully unblocked axis** |
| **M12** memory / determinism | **(e) scheduled** — 1/2/4/8-worker hashes and RSS ready; the 16-worker run needs a quiet host |
| M1, M5 | blocked on instrument, geometry, capture **and** comparator |
| M2, M3, M4, M11 | blocked on instrument, geometry, comparator |
| M6 clipping | census executable but **underpowered below 10,000 recoverable samples** |
| M7 colour | no traceable colour target exists |
| M9, M10 | blocked, and the certificate and depth **products do not exist** |

### 2.9.2.2 M8 is the one place a real win is currently available

I put a hypothesis to the scorecard owner: that `cover=scale` may be **inventing pixel values**,
because `S_k` rides on every placement so every frame passes through **Catmull-Rom**, whose
negative lobes overshoot at edges. An overshooting kernel can emit values no input frame brackets
— which is exactly what M8 forbids at a bar of **exactly `0.0000%`**.

The owner's verdict was the useful kind: **plausible, but v1.4's predecessor could have passed
it.** An all-frame hull, a `5σ` tolerance and a post-merge measurement point could each have
hidden the overshoot, so the axis was split and tightened:

- **M8-R, per-frame resampler hull — the primary.** Pre-merge, pre-clamp linear `f32`, against an
  **independently reconstructed** exact Catmull-Rom source-support hull; tolerance
  `tau_R = 8*ULP_f32(max(1, abs(lo_k), abs(hi_k)))`. Catches invention **where it is created**.
- **M8-O, final-output hull.** Final linear output against the all-valid-frame hull, tolerance
  only `0.5/65535`. Determines whether the invention **survives to the deliverable**.

**The recorded defeat is why both are needed: final clamping can erase M8-O evidence**, so a clean
M8-O alone proves nothing. Commissioning is mandatory — a fractional-step Catmull plant must
produce at least one M8-R violation, while copy and convex-bilinear nulls must produce none.

**Why this matters more than its size suggests.** M8 is **metric-free and sharpening-immune**. It
asks whether a value is bracketed by the data, which has no sign ambiguity, no tone sensitivity
and nothing for a sharpening filter to exploit. It is therefore the one axis that can move while
the detail axis is refused. Routed to lane COVER, which already holds both cover arms and the
flat-slide unit. **If `scale` violates and `crop` does not, that is a demonstrable improvement on
a registered axis — and it would be the first this program has produced.**

### 2.9.3 The build path that replaces phase 1

**`cover=scale` (§2.8.3).** It is now the program's primary build lane, and it was chosen for one
property the alternatives lack: **it can be adjudicated without a resolution metric.**

The claim under test is bit-identity, not sharpness. Under `CoverMode::Crop` a frame whose
placement is an integer translation — the reference frame's identity being the extreme case —
"reaches the output through an interpolating kernel evaluated exactly on a sample, which is a
copy." Under the `Scale` default, `S_k` rides on every placement and that same frame is resampled.
**"Is this the same data?" has no sign ambiguity, cannot be fooled by sharpening, and is immune to
the tone sensitivity that killed `S_25`.** That is why this lane can proceed while the detail axis
is still refused.

The prize is real and largest where it matters most: **`1/k - 1` is 1.3% at 22 frames and 7.3% at
299 frames**, and the deepest stack is the scorecard's own performance master. The competitive
argument points the same way — real focus stackers crop, because alignment always loses border;
upsampling the whole frame to preserve nominal dimensions is the unusual choice, not the safe one.

**What would make this lane fail, stated in advance:** if the reference frame turns out not to be
bit-reproducible under `Crop`, or if the documented border hazard — coarse pyramid bands spreading
black fill inward before the crop discards it — costs more than the resample it saves. Both are
measurable, both are preregistered, and a negative result closes the lane honestly.

### 2.9.4 The detail axis has no instrument on any capture that exists, and I was wrong about why

Lane INSTRUMENT returned the verdict: **no admissible detail instrument is obtainable from current
captures.** It also corrected a claim I had been repeating, and the correction matters.

**What I had been asserting:** that subpixel alignment destroys the noise independence repeat-pair
FRC depends on, so IBIS-on data is unusable.

**Why that is too broad.** D8b already implements the safest possible correction — disjoint
alignment data plus a **unit-modulus Fourier phase ramp**, not spatial interpolation
(`experiments/M-PHASE0-SPLIT2/AMENDMENT-1.md:28-42`, `align.py:25-43,85-106`). It **preserves
magnitude to `1.67e-16`**. A unitary phase shift does not create cross-frame dependence, so the
generic objection does not apply.

**The actual blockers are three, and they are worse than the one I named** because none is fixed by
a better interpolator (`docs/research/M-PHASE0-SPLIT2.md:144-155`):

1. **Spatially varying geometry.** The residual is not rigid, so no global shift corrects it. The
   second light block fails the local nontranslation gate at `0.107703`, independently reproduced
   at `0.105202` (`:69-85,113-120`).
2. **Data-dependent registration**, which couples the alignment to the content being measured.
3. **Stable sensor structure (FPN) that the ABBA null cancels rather than tests** — so the null
   passing is not evidence the instrument works.

Same-frame FRC remains dead independently: common-mode content leaves the adversary reading
`0.972099`, and no threshold repairs it (`docs/research/M-PHASE0-SPLIT.md:95-101`).

**The leading replacement is target-conditional ideal-observer information** — `I(X;Y)` between a
target variable and a complete output tile. It is ranked first because **the data processing
inequality makes "deterministic sharpening cannot increase it" a theorem rather than a heuristic**,
with unclipped USM predicted to give *equality*; tone invariance is likewise a property of the
estimand. **That is the first candidate in this program whose two decisive failures are excluded by
construction rather than by hope.**

**The risk that will decide it, stated before measurement:** a theorem about an estimand is not a
guarantee about a finite-sample estimator. A trained observer can reward USM by fitting artefacts
or by exploiting leakage from a periodic target. **The rule is therefore binding: the USM arm at
radius 1 / amount 0.5 runs first, and failing it kills the candidate outright rather than
triggering a retune.** A candidate that needs tuning to pass the sharpening arm has failed it.

**One further finding, which raises the cost of the fix:** existing rulers do not establish
physical scale, pose, magnification or focus advance (`docs/research/M84-ruler-metrology.md:239-266`),
and the burned grid was only *nominally* 0.01 mm, clear film over paper. Whether a **certified**
target is genuinely required, or whether a relative comparator claim can proceed without one, is
an open question I have put back to the lane before troubling the owner — SOTA here is defined as
comparator-leading, which is a *relative* claim, and that distinction may decide whether this is a
procurement problem or a shoot-this-week problem.

### 2.9.5 The first formal reading is being taken, and the evidence I offered for it did not qualify

M12 (engineering reproducibility) is one of only two scorecard axes executable
without the missing detail instrument, so it is the program's first chance at a
formal reading of any kind. I tried to shortcut it and was correctly refused.

A concurrency lane had already measured 18 renders, six each at pyramid worker
counts 1, 4 and 8, and found hashes identical **within** each count but three
different hashes **across** counts. Together with `byte-freeze.rs:512-514`,
which admits in its own words that `STREHL_PYRAMID_WORKERS` "changes the fold's
reduction order, which is worth 1 DN on a fifth of a percent of pixels", I put
it to the registrar that M12's byte-invariance bar was already MEASURED and
FAILING, and asked it to be strict with me.

**It refused, and I verified the refusal at source rather than accepting it.**
The hash `C6765BFA...` is `byte-freezes.tsv:107`, the
`coffee-bean-20-gate2-pyramid` row: **N=20**, `env_align = 0`,
`alignment_mode = off`, and its own registry note states verbatim that
"photometric gain, clip census, outlier rejection, halo correction,
through-focus statistics" are **not applied**. It is a stripped arm with
alignment disabled, not the product, and not the registered N of 33/105/299.

The general rule this establishes, which is the same error in a new costume as
the two summary errors recorded in 2.8.1: **a hash is evidence only about the
exact configuration that produced it.** Reading it as evidence about the
product is reading a summary instead of the source.

The registrar split the axis rather than ruling on a conflation (v1.5,
`dd957dd5`, verified):

- **M12-D, fixed-worker determinism** -- diagnostic PASS, and it holds.
- **M12-S, cross-worker scaling invariance** -- diagnostic FAIL.
- Both formal sub-bars remain **UNMEASURED**. This is therefore still not the
  first scorecard reading.

Splitting them matters because a product may legitimately be deterministic
while being worker-count dependent; the severity and the repair differ
completely, and one bar reading "byte invariance" could not have said which.

**Structural note on who measures.** The registrar sets the bar, so it must not
also take the reading; that is exactly the generator/checker cancellation this
repository has rediscovered six times, and rule 35 forbids it. I opened a
separate measurement lane. It must commission its harness against a plant
proven potent before any hash it reports is admissible, and it is explicitly
authorised to return a failing M12-S as a complete deliverable.

### 2.9.6 The replacement build path is closed by measurement, for the reason I predicted

2.9.3 proposed `cover = scale` as the build path replacing phase 1, on the
ground that Scale resamples every pixel of every render including the reference
frame, whose placement is the identity. That is confirmed: measured `k` is
`0.9870` on a 22-frame stack and `0.9321` on a 299-frame stack, so the
interpolator runs on everything, always.

**The path is nevertheless closed, and the audit that closed it is the most
disciplined work this program has produced** (`66e79043`,
`docs/research/cover-default.md`). Crop's identity placement is a bit-exact
window -- that gate passed. The other three failed:

| gate | result |
| --- | --- |
| outer 0-16 Crop ring within 0.1% on every stack | **FAIL** -- up to `+2.61%` |
| safe inset at most 128 px on every stack | **FAIL** -- `256 px` needed |
| at least 80% of original pixels after inset | **FAIL** -- `64.60%` |

**The mechanism is the one I predicted before the measurement.** Crop happens
*after* the full-plane pyramid has already transported the uncovered-fill
boundary inward, so the border contamination is inside the kept region rather
than in the discarded margin. Paying 35% of the frame to avoid a 1.3-7.3%
resample is the worse trade. `DEFAULT_COVER_MODE` remains `Scale`.

Predicting the defect correctly and still having the path close is the right
outcome to record plainly: **a correct diagnosis is not a repair**, and the
program's net verified product improvement remains zero.

**One genuine improvement did land, and it is the first.** The audit found a
hermeticity bug independent of the default decision: `RENDER_ENV` did not clear
ambient `STREHL_COVER`, so a dirty shell was indistinguishable from a geometry
regression. Commissioned rather than asserted -- under a planted
`STREHL_COVER=crop` the aligned freeze moved from
`E600A506...` at `49,450,019` bytes to `C3B3B05C...` at `48,875,075` bytes and
the run exited 101, while the unaligned control held as a specificity check.
`STREHL_COVER` is now cleared with the other render inputs and all three rows
reproduce twice bit-for-bit under the same planted value
(`byte-freeze.rs:445-455`). This is a test-integrity fix, not a picture-quality
one, and it should be scored as such.

The audit also stated its own limits without being asked: the 299-frame holdout
value, a universal depth-only law, any sharpness or visual advantage, and a
finite safe inset generalising beyond one stack are all explicitly **not**
verified, and the claim that cropping is normal product behaviour is marked as
context supplied to the lane rather than a measurement.

**Consequence for the program.** M8 was routed to this lane and the lane closed
without reaching it, so M8 was briefly unowned; it now has a dedicated lane.
With Scale retained, **M8 is squarely on the product path** -- every render
resamples through a kernel with negative lobes, so the overshoot question is
live rather than hypothetical.

### 2.9.7 Nothing in this repository is sharpening-safe, and the number that said otherwise was underpowered

The `S_25` hardening lane closed with a verdict I asked for and did not expect
to be this complete: **close the lane, and the reason is worse than tone.**

**The correction first, because I propagated the error.** I have been recording
`S_25` as the one sharpening-safe statistic in the repository at `0.995819x`,
and I repeated it to two lanes. That figure came from a 24-seed run. The lane
expanded to a **64-site control** and re-ran the identical arms **against the
unchanged 1% bar** (`M-PHASE0-SLANTEDGE.md:276-278`):

> The expanded 64-site control also overturns the apparent native-S25
> sharpening safety from the earlier 24-seed run: USM is now **+2.829%**,
> outside the unchanged 1% bar.

The matrix row at `:269` reads USM `1.028294` **RED**. **The bar did not move;
the sample grew.** `0.418%` was not a property, it was an underpowered
measurement -- and note the direction of the error: **the underpowered run
produced the flattering number, and that is the number that got quoted
onward.** This is the third time an underpowered or mis-read summary has misled
this program, after the two recorded in 2.8.1.

**The consequence is a clean sweep.** Every empirically constructed candidate
in this repository rewards sharpening:

| statistic | USM response |
| --- | --- |
| `Q25` | `5.560744x` (+456.07%) |
| three slanted-edge implementations | ~9.9% "resolution" gain from USM alone |
| `S_25` | `1.028294x` (+2.829%) |

So `S_25` fails **all three** properties, not two: tone (`18818.9045x`),
sharpening (`1.028294x`), and -- in every variant that repaired tone -- genuine
resolution response, which reversed sign (`blur 1.268326`, `improvement
.923468`).

**Why the family is closed.** Unknown monotone tone is structurally confounded
with edge shape inside the Fourier/SNR construction, so normalisation alone
cannot separate tone from blur. The lane was careful not to overclaim: a finite
search **does not** establish fundamental impossibility, only that further work
would be invention of a new statistic rather than bounded hardening.

**One transferable positive, and it should outlive the lane.** Tone invariance
was obtained **without ordinality**: an independent 33-step PCHIP linearisation
moved affine, gamma-3 and logistic arms by at most **`0.0141%`** without
disturbing the USM result (`:286-289`). This matters because ordinality is the
obvious route to tone-invariance and is the leading suspect for *why* `Q25`
rewards sharpening -- rank construction appears to buy tone-invariance and pay
in sharpening-safety. An external tone witness gets the invariance without that
trade. It did not save `S_25`, whose optical arms reversed under the transform,
so it is a technique rather than a fix.

**What this does to the program.** It removes the last software route to a
detail instrument from the existing families, and it makes the case for a
*structural* guarantee rather than an empirical one as strong as it can get:
every empirical candidate has now been defeated by a free operation any
competitor can apply. The critical path is candidate 1's theorem-backed
construction plus the owner's IBIS-off re-shoot -- which is where the program's
effort is now pointed.

**The registrar turned the failure into a guard, which is the right response to
a recurring defect.** Scorecard v1.6 (`48a1d902`) preserves the supersession
history rather than swapping the number, and adds a new condition of admission
for any replacement detail statistic (`2026-09-sota-scorecard.md:519-521`):

> Its sharpening battery must use **at least 64 independent sites** and
> **retain its frozen bar as sample size grows**; a **structural invariance
> argument is still required because empirical non-rejection is not a
> guarantee**.

That last clause is now binding on candidate 1: a clean USM arm does not by
itself admit an instrument. The structural argument must also state **where the
theorem stops applying** -- the data processing inequality governs the estimand
`I(X;Y)`, and a trained observer or variational bound is not the estimand.
`2026-09-sota-scorecard.md:485-488` confirms M1 is otherwise unchanged: still no
statistic, still no bar, still `UNMEASURED`, and the superseding result
strengthens admission rather than resurrecting any candidate.

---

### 2.9.8 A theorem was not enough: the sharpening problem survived a structural guarantee

Candidate 1 is dead. It was killed by its own first arm, and the arm was the one
I registered as decisive before any code was written.

The candidate was target-conditional ideal-observer information. It was ranked
first for one reason: the data processing inequality makes "deterministic
sharpening cannot increase it" a *theorem* rather than an observation. Every
statistic this program had tried before it was an empirical construction that
happened to resist sharpening until it did not. This one was supposed to be
different in kind.

Under the registered unsharp mask at radius `1.0`, amount `0.5`, the estimator
rose from `0.125099` to `0.137075` bits per tile. That is `R=1.095732`, an
increase of `+9.573%`, with a one-sided 95% upper bound of `1.129895` against a
bar frozen at `1.01`. The reading was taken over 480 independent macro-tile
clusters and 3,840 held-out trials, with bootstrapping over acquisition blocks
above sites — comfortably past the 64-site minimum the scorecard registered at
`docs/proposals/2026-09-sota-scorecard.md:519-521`. This was not an underpowered
run. Freeze `613eaf1a`, result `efa25bd2`, amendment `2d3d247d`, report at
`docs/research/M-CAND1.md:39-42`. I verified all four numbers at source before
writing this section.

The lane then did the thing that makes the result trustworthy: it stopped. The
degradation, improvement and null arms were never run, and the runner hard-refused
commissioning, because the binding stop rule said a decision-relevant increase
kills the candidate outright and is never grounds for a retune. **A lane that
kills its own candidate on the first arm and declines to collect the flattering
arms afterwards is the only kind of lane whose greens would have meant anything.**

**The failure was predicted, in writing, before the measurement.** The
investigation proposal that ranked this candidate opens its reasoning with a
section titled *the central distinction: estimand is not estimator*, and the
brief I sent the lane recorded the same risk as the candidate's decisive
exposure: a theorem about an estimand is not a guarantee about a finite-sample
estimator. Recording it in advance is what makes it evidence now rather than
hindsight.

**What the kill actually teaches, which is more than the four before it.** The
tally is now five statistics defeated by a single free operation that any
competitor can apply for nothing:

| statistic | USM response |
|---|---|
| `Q25` | `5.560744x` (+456.07%) |
| three slanted-edge implementations | ~9.9% "resolution" gain |
| `S_25` | `1.028294x` (+2.829%) |
| candidate 1 ideal-observer information | `1.095732x` (+9.573%) |

The first four could be read as a run of bad luck in statistic design. The fifth
cannot, and that is its value. The data processing inequality is not wrong here
and the estimator is not buggy; the two simply are not the same object. The
inequality governs `I(X;Y)`, a property of the joint distribution. What was
measured is a finite, capacity-limited, fitted lower bound on it. Sharpening adds
no information — it makes the information already present more *accessible* to a
bounded-capacity reader, and a lower bound that tightens when the signal becomes
easier to read will rise even though the quantity it bounds cannot.

That mechanism is not specific to this construction. Every statistic computable
on finite data is a bounded-capacity read of the image, so **the failure should be
expected to generalise to the whole class, and the burden now falls on any future
candidate to explain why it escapes.** Stating that here is the difference between
five separate disappointments and one understood obstacle.

**Where this leaves the detail axis.** The investigation proposal ranked three
candidates and the second has a claim that is different in kind from the first,
which is why the program continues rather than stopping. For a linear sharpening
operator `A`, the full-covariance form satisfies
`(A d)^T (A K A^T)^{-1} (A d) = d^T K^{-1} d`. That is congruence invariance of a
quadratic form, and the proposal is explicit at `:114` that it is *both* an
estimand result *and* a finite-sample algebraic property — for the full-rank,
unregularized, congruence-equivariant form only. Shrinkage, diagonal covariance,
channel selection and pseudoinverses all destroy it. So candidate 2 is not exposed
at the seam that killed candidate 1, because its invariance holds on the sample
covariance and not merely in the population.

**A defect in candidate 2's test plan, found before it was run, and now corrected
in the lane brief.** The registered kill arm uses unclipped float USM. As an
operator that is `1.5·I − 0.5·G`, whose eigenvalues lie in `[1.0, 1.5)` — strictly
positive, therefore invertible and full-rank. It is precisely the case the
congruence identity protects. Candidate 2 would therefore have passed the
registered sharpening arm *by algebra*, and a test a candidate passes by
construction measures nothing about its fitness. Left uncorrected this would have
produced the program's first green on the detail axis and it would have been
hollow.

The arm is retained, but its status is downgraded to an implementation check: if
the unclipped ratio does not come out at 1 to numerical tolerance, the estimator
is not congruence-equivariant and there is a bug. Two honest adversaries were
added in its place. **Clipped USM**, because clipping is nonlinear and every real
competitor sharpens and then clips to the representable range, so the algebraic
protection evaporates exactly where the operation is realistic. And **nonlinear
tone**, gamma-3 and logistic, where the proposal states at `:114` that conventional
NEQ is invariant to nonsingular linear transforms and not to arbitrary tone, and
that these *"remain empirical kill arms"*. If candidate 2 dies, tone is the
likeliest cause.

**Scoreboard.** Still zero formal scorecard readings and zero verified improvement
in picture quality. Two candidates of three are now spent on the axis the whole
SOTA claim rests on. The program has bought real understanding of why the detail
axis is hard, and has not yet bought a single admissible number.

---

### 2.9.9 Phase 0 closed while I was watching the detail axis, and the shape of what it produced is the finding

I swept every lane I had lost track of and demanded a bounded reading. Thirteen
answered. Phase 0 is now substantially complete, and I had not noticed, because
my attention had been entirely on the detail axis. The census matters more than
any single entry in it.

| lane | gate | verdict | the number | commit |
|---|---|---|---|---|
| IOPERF | D11 decode | **PASS** | `719.3` MB/s compressed-input at 32 threads; `193.9` at one | `d337daa8` |
| IOPERF | D15 storage | **PASS** | `6.338` GB/s cold, `20.615` GB/s warm, `3.25x`; replicated `3.10x` | `d337daa8` |
| DPAR2 | curved-track | **KILL** | MDA80 `<=0.010` plane px/depth-step, bootstrap 95% `[0.010, 0.010]` | `7a1a3128` |
| XSPEC | C10 | **NOT ROBUST** | `R=0.70852`, CI `[0.66732, 0.76315]`, against a required `>=2.0` | `4f1f28ec` |
| VEIL2 | A2 | **STOP, DO NOT BUILD** | `theta=-0.081241`, CI `[-0.235876, +0.051078]`; audit `0/7` | `e4e3939f`, `bcc77de9` |
| LCA | C2 | **STOP** | R `4.22-7.54%`, B `3.51-7.13%` axial forfeit, but only `1/4` stacks valid against a frozen `4/4` gate | `a3b87d36` |
| CAND1 | detail | **KILL** | USM `1.095732x` against a frozen `1.01` | `efd5a2` / `efa25bd2` |
| COVER | build path | **CLOSED** | `+2.61%` ring, `256 px` inset, `64.60%` retained | `66e79043` |
| phase 1 | W1 | **REFUTED** | `NO_COMMON_K`; no band 4-6 predicate passes at any `k` | `f5658e5d` (design, now bannered) |

**Read the verdict column, not the rows.** Of nine closed gates, **seven are
refusals** — kill, stop, not robust, closed, refuted. Two are passes, and both of
those are systems gates whose practical content is also *"do not build"*: D11
says retain `rawler` rather than own a decoder, D15 says do not build an IOCP
subsystem. **Phase 0 did not tell this program what to build. It told it what not
to build, nine times.**

That is a legitimate outcome and it is what a kill-gate phase is for. It is also
the precise reason the SOTA claim is now so narrowly loaded: every axis that
could have been cleared cheaply has been cleared, and what remains is the detail
axis and M8. There is no longer a broad front of work — there are two places
where a real win is still available, and one of them has no instrument yet.

**The lanes have internalised the power discipline, and one of them caught the
`S_25` failure mode in itself before I could.** VEIL2 reported its own primary arm
with this qualification, unprompted: *"The 20,000 resamples are not independent
observations; the effective count is 36."* That is exactly the error that let
`S_25` be recorded as sharpening-safe at `0.995819x` from an underpowered run
before reversing to `1.028294x` at 64 sites against an unchanged bar. A lane
volunteering the deflating version of its own sample size is worth more to this
program than a lane volunteering a result.

**Harnesses worth keeping, which is the part that outlives the questions.** Three
lanes left behind rigs that are reusable and were commissioned rather than merely
written: XSPEC's spectral harness at `experiments/M-PHASE0-XSPEC/src/`, which
passed `8/8` controls and caught `9/9` planted defects; IOPERF's decode and
cold/warm storage harness at `experiments/M-PHASE0-IOPERF/`, commit `40e41a63`;
and DPAR2's curved-track plant rig with a cancellation-immune fixed oracle and
96-phase power calibration. **This program has been short of trustworthy
harnesses and now has three.** A future lane should reuse one rather than build a
fourth incomparable one.

**A landmine was found and closed.** `docs/proposals/2026-09-phase1-design.md`
remained committed as an *executable* proposal with no record that its own
mandatory gate had fired against it. A reader arriving later would have found an
authoritative, carefully cited implementation design for a refuted mechanism. It
now carries a `REFUTED - DO NOT IMPLEMENT` banner at the head, which states the
`NO_COMMON_K` result, records that the design is refuted rather than untuned so
that nobody revives it by adjusting a constant, and preserves the parts of it
that remain independently factual. **The lane that wrote the document is the one
that reported the hazard**, which is the behaviour I want and did not have to ask
for.

**What this does not change.** Still zero verified improvement in picture quality.
The two passes are throughput, not detail, and a fast decoder does not make a
better photograph. But the earlier claim in this file that the program had taken
*no formal readings at all* was too harsh on it: D11 and D15 are commissioned,
replicated, controlled readings that closed real build decisions, and the seven
refusals are readings too. The program's problem is not that it cannot measure.
**It is that almost everything it has measured has told it to stop.**

---

### 2.9.10 The registrar overturned my correction, not the lanes' results: the scoreboard is still zero

I asked the registrar to rule on the ten closed gates, and specifically to hold
the program's only two PASS verdicts to the same standard it had used when it
refused *my* M12 evidence. It did, and the ruling went against a softening I had
made one section earlier in this file.

Scorecard **v1.7**, commit `2fd2b131`, §3.2 at `:441-486`. The scoreboard it
returns:

> **0/12 MEASURED. 12/12 UNMEASURED.**

**Both passes were admitted, and both were admitted narrowly.** D11 is admitted
*only* as the proposal's decoder-component gate: three ARW files are narrow, the
preregistration set no broader minimum, beginning/middle/end files were consumed
and checked, and the margins were `1.91x` per-core and `1.41x` aggregate — but it
**does not generalise beyond this A7C II workload and does not measure M11's
product path**. D15 is admitted *only* as the storage-materiality gate. Its
Windows-cache confound is genuinely excluded, and the reason is worth recording
because it is a good piece of instrument design: the no-buffering arm stayed at
device rate while the buffered arm accelerated `3.1-3.3x`, which is what a real
cache exclusion looks like. SSD firmware cache remains inseparable, but the
registrar ruled it belongs to the host-visible device path being priced, which is
the right call. **M11 therefore remains UNMEASURED at `:1155`.**

**So the earlier scoreboard was right and my correction to it was wrong.** In
§2.9.9 I wrote that the claim of *no formal readings at all* had been too harsh on
the program, on the strength of D11 and D15. The registrar has now ruled that
neither moves a scorecard axis. Both are real, commissioned, replicated, controlled
measurements — that part of §2.9.9 stands and I do not withdraw it — but a *gate*
reading that closes a build decision is not an *axis* reading, and only the second
kind counts toward the claim this program exists to make. **I softened the
scoreboard and the entity I had asked to be strict told me not to.** Recording it
because the direction matters: every other correction I have had to make this
session was a number that flattered the program, and this one was mine.

**The refusals were ruled admissible, with the distinction I asked for made
explicit rather than left implicit.** XSPEC and VEIL2 are admissible **as refusals
only**. XSPEC's 132 tiles miss its own frozen 160 minimum, so in the registrar's
words it *"failed to show C10 works, but did not show C10 cannot work."* VEIL2's
effective count is 36 clusters rather than 20,000, so its `0/7` audit *"blocks
building but does not prove zero effect."* That distinction is not pedantry. An
underpowered study that declines to build is safe, because its error direction is
inaction; the same study quoted later as proof that an effect is absent would be a
fabrication. Both are now on the record as the first kind.

**Where the weight now sits.** The registrar names **M1** as the most load-bearing
axis, on the grounds that it lacks **both a statistic and a bar** and blocks
several dependent quality and comparator judgements. **M8 is the only immediately
measurable complete quality axis.** That is the whole live surface of this
program: one axis that can be measured today, and one that cannot yet be defined.

### 2.9.11 FRC was the last hope for the detail axis, and the reason it died inverts my own argument

**Verdict: `NO-GO as M1's detail instrument`** (`docs/research/M-FRC-VIABILITY.md`,
commit `34cd4063`). I found Fourier Ring Correlation this session by searching for
anything that had ever survived a sharpening arm, and it looked like the strongest
candidate the program had seen. It is what the governing proposal actually
prescribes -- `2026-08-sota-path.md:192-197` specifies detail as *"D1: FRC +
slant-edge"* -- and the split prototype had recorded it surviving an unsharp arm
three times stronger than the registered one.

**I argued for it on algebra, and the algebra was right.** FRC is a per-ring
normalised cross-correlation between two independent realisations. An isotropic
unsharp mask has a real transfer function constant on each ring, so it multiplies
the ring numerator by `a^2` and each denominator factor under the square root by
`a^2`, cancelling exactly on the finite sample. I put that to the lane as a
guarantee categorically stronger than the one that failed for candidate 1, because
it is a finite-sample identity rather than a population theorem.

**The lane accepted the derivation and used it to kill the candidate.** A statistic
that exactly cancels an arbitrary-strength common linear filter cancels **blur**
exactly as it cancels sharpening. It is *"structurally blind to an
arbitrary-strength common linear post-filter, including blur."* A detail instrument
must rank more detail above less detail; FRC provably cannot rank either direction.
**Invariance and blindness are the same property here**, and the guarantee I was
most impressed by is precisely the disqualification. It survives only as a
secondary repeatability sentinel.

That also settles the standing worry from `BUILD-SHARP.md:172` -- the claim that
something was *"18,644x more responsive than ring FRC"* -- against FRC rather than
in its favour. A statistic hard to fool because it barely moves is not safe, it is
inert.

**The tally is now six.** `Q25` at `5.560744x` (+456.07%); three slanted-edge
implementations at ~9.9%; `S_25` at `1.028294x`; candidate 1 at `1.095732x`; and FRC
by blindness. **The detail axis has no admissible instrument and, for the first time,
no candidate in flight that is merely waiting on data.**

**Candidate 2 is untested, not dead, and the distinction is the whole result.**
Freeze `c1e7840d`, results `8c9966fa`, report `docs/research/M-CAND2.md`. Its verdict
reads verbatim **`CANDIDATE 2 DOES NOT LIVE -- uncommissioned, not empirically
killed.`** The unclipped-USM arm passed by algebra exactly as predicted before the
run -- `R = 1 + 2.66e-14`, congruence residual `1.25e-15` -- which was only ever an
implementation check, because an unclipped unsharp mask is `1.5*I - 0.5*G`, full-rank
and invertible, and therefore the exact case the congruence identity protects. The
arm that could have killed it was **inert**: **zero rail hits across 2,088,960
values**, so clipping was a no-op. The lane detected this itself, corrected its
potency checker, preserved the raw results, refused to retune, and stopped every
later arm. **An inert adversary and a genuinely survived adversary produce the same
number**, and only a potency check separates them. It has been re-tasked to
commission a potent clipping adversary and to run the tone arms, which the
investigation spec says *"remain empirical kill arms"* and which are where the
candidate is genuinely exposed.

**The competitive deficit against sharpened Zerene PMax is rejected as a confound.**
`V-HEADTOHEAD3` completed while these lanes ran (now 887 lines, still committing) and
disposed of the question at `:212-219`: the Sharpness-40 arm is *"a confounded
spatial-development comparison, and both flat and hull placebos go strongly
positive."* Positive flat power reads `1.7291 [1.3645,2.1638]` and hull excess
`0.03692 [0.01311,0.06010]`. Its licensed transfer arm then measured
`M40 = USM05(PMax0)/PMax40 = 1.0187 [0.6937,1.5825]` -- a plain radius-1 amount-0.5
unsharp mask applied to unsharpened PMax reproduces sharpened PMax to within the
interval. **Strehl is not shown to lose detail to PMax40; that arm was measuring
development, not merging.** The same lane also refused `Q25` outright: tone arms held
at `0.999963/1.000000/0.999966`, but a **genuine sigma-1.20 optical improvement read
`0.977981`** -- the wrong sign -- while information-free USM was rewarded `5.560744x`.
A statistic that penalises real resolution and pays for fake sharpening is worse than
no statistic.

**The capture was hours from being shot wrong.** The 319-frame request gets the
mechanical core right -- SteadyShot and OSS off, fixed exposure, coplanar
nonperiodic patch -- and the lane still returned **"NO, not exactly as specified."**
Its defects: two complete sweeps from an *"identical near-focus reset"* do not
guarantee matched focus nodes, so A and B can resolve different material and present
a latent mismatch as independent noise; **frame count is not site count**, and 55/27
frames give one output pair per condition rather than the registered 64 independent
sites; `"flats 32 / darks 32"` is underspecified, and paper fibre texture is exactly
confounded with PRNU unless defocus removes it. **The owner had not yet shot, and has
approved the amendment: the session is now 383 frames**, with 32 flats and 32 darks
*per realization* so each output gets an independent calibration master.

**The primary fix is unavailable on this body.** The owner shoots with **in-camera
focus bracketing on the A7C II**, which drives the focus ladder itself; there is no
way to expose A and B back-to-back at each node. The fallback -- a separately frozen
focus-repeatability gate plus fixed-focus witnesses proving the two node ladders
coincide -- is therefore the actual protocol, and the lane is making it operational.
This is not hypothetical: **SPLIT2 died on exactly this**, at a registration residual
of `0.107703` against a `0.10` native-pixel bar, with an independent ECC reproducing
`0.105202`.

**What the incoming capture is now worth.** It unblocks two questions, not one.
`V-HEADTOHEAD3` stopped at the same wall, unable to settle *"recovered scene detail
or amplified noise/ringing"* because *"without independent same-focus repeats/noise
qualification, correlation to those ARWs would also validate amplified sensor
noise."* Independent same-focus repeats exist in no capture this project owns. The
383-frame session is the only one that will contain any, which is why getting its
specification right outranked every other live task this hour.

**There is finally a build path, and it is ranked on a property worth naming.** The
planning lane returns **pause, then conditionally build D9 (fixed reduction
lattice)** -- because **D9's verification survives M1**. Worker count currently
changes floating-point reduction order, measured at `0.2573%` of pixels differing by
at most 1 DN, and the fix is checked by exact cross-worker hashes, which need no
detail instrument at all. Everything with a larger apparent payoff is gated behind an
axis that cannot yet be defined. Default-on dust correction ranks second on measured
grounds -- the physical mote moves `-4.644%` to `+0.019%` and a deliberately wrong map
produces byte-identical output -- but its no-harm null covered a single subject.

**The honest summary of this hour: one hope found and killed on its own merits, one
candidate saved from a hollow green, one competitive deficit dissolved into a
confound, and one irreplaceable capture corrected before exposure.** The scoreboard
is unchanged at **0/12 MEASURED**.

---

### 2.9.12 The scoreboard moved, and the first number it produced says the picture is wrong

**M8 is measured. It reads FAIL.** After eleven closed gates and nine refusals,
an axis finally carries a value instead of a reason it cannot be read.

`1.030569%` of merged pixels lie outside the hull of the frames they were merged
from -- `63,191,176` of `6,131,678,976` -- with excursions running
`-240.040039` DN below and `+586.215820` DN above the source range. The identity
arm is clean at `0/32,919,152`, and commissioning separates the kernels the way
the physics says it must: Catmull-Rom, which has negative lobes, trips `28/252`;
copy trips `0/252` at exactly zero error; bilinear, which has no negative lobes,
trips `0/300`. The instrument fires on overshoot and only on overshoot.
`docs/research/M8-overshoot.md`, commit `76b3d9cc`. Every number above was
checked against that file before this section was written.

**Two qualifications that change what the number means, both from the same
report.** First, all three arms were measured **under `cover=scale`** -- the
per-arm rescale factors `k` are `0.9862`, `0.9870` and `0.9859`. So
`1.030569%` is a property of the pipeline *as it ships*, not a proven property
of the merge algorithm. Second, and pointing the same way: **the identity arm
reads exactly `0` violations across `32,919,152` values.** Where nothing is
resampled, nothing overshoots. Taken together these say the defect is
resampling-borne, and they leave open only *which* resample -- the per-frame
registration warp, or the whole-frame coverage rescale.

**This is a real defect in the pictures, not a measurement artifact.** Values
outside the source hull are invented. At `+586` DN they are visible, and they
are the signature of ringing -- which is the same family as the halo already
recorded as the largest visible defect in the renders.

### A second lane found that the default output path resamples every picture

Independently, the scorecard baseline lane measured every one of eight renders
failing the scorecard's native-scale prerequisite -- `scorecard.md:225`,
*"Outputs must retain native scale. Resize is a hard invalidation."* -- against
a `<=0.10%` bar. The measured disagreement runs `0.2901%`-`0.4619%` across the
eight -- **three to four and a half times the bar, with no render close to
passing.**

**The reader that took that measurement was commissioned, which is why I am
treating it as a fact rather than a suspicion.** A planted `0.300%` scale error
read back `0.3031%` and correctly failed; the identity null read `0`; a
translation-only null read `0.0084%`, so the reader does not confuse a shift for
a scale (`SCORECARD-BASELINE.md:47`). Per-render scale factors were reported to
me but are not in that committed file, so they are not repeated here.

The cause is `cover=scale`: 0.3-0.4% of width is dropped and the result
upsampled back to native dimensions. **That is strehl's shipping default** --
`crates/strehl-cli/src/align_cmd.rs:1003`, `DEFAULT_COVER_MODE =
CoverMode::Scale`. Every picture the tool produces is silently resampled on its
way out.

**The blocker is strehl's own output path, not the comparator's.** I had been
carrying this as a possible bar on M1's competitive half, and it is not one:
all eight failing renders were strehl's. Comparator native-scale viability is
unmeasured.

### The two findings may be one finding

The coverage rescale is a whole-frame Catmull-Rom resample applied to the
finished picture. Catmull-Rom has negative lobes. **A whole-frame Catmull-Rom
resample is an overshoot generator applied to 100% of pixels**, which makes it a
live candidate for the source of M8's `1.030569%`.

If that holds, one setting change closes M8 and unblocks M1's native-scale
prerequisite together, and `CoverMode::Crop` is already shipped
(`align_cmd.rs:986`) -- no new code. Both lanes are measuring it now. I am
recording the hypothesis before the answer arrives so that it cannot be
retrofitted to whatever comes back.

**The counter-case is priced and it is not small.** `align.rs:2752-2754`
records removing the coverage rescale recovering `+0.0179` dex of detail
against `+0.1160` dex for changing the kernel -- so the rescale is real but it
is the smaller factor by `6.5x`. And `scorecard.md:226-227` permits crops only
when they are *"fixed from the common-input overlap before outputs exist"* with
retained field of view `>=99.0%`. `CoverMode::Crop`'s rectangle is derived from
the alignment solution, so it is data-dependent by construction. **A mode that
trades one hard invalidation for another is not a fix**, and that question is
asked explicitly of the lane rather than assumed away.

### What this changes about where the program is pointed

For four gates I have been reporting refusals. The honest summary of those was
that the program could prove things wrong and could not prove anything right.
That is now partly false: **the program can prove its own output wrong**, which
is the direction a real quality claim gets built from.

It also names a candidate axis that is genuinely competitive rather than
merely defensive. `align.rs:2759` records a sharper kernel measuring
`9.9x` Catmull-Rom's p99.9 overshoot while `align.rs:2752` records it
recovering `+0.1160` dex of detail. **That is a detail-versus-overshoot
frontier**, both ends of it are measurable with instruments that already exist
and are commissioned, and neither end depends on the dead detail statistic or
on the capture that has not been shot. It is the first thing in this program
that could be pushed rather than only audited.

### 2.9.13 A late gate close, and a coordination failure worth recording

**C5 field curvature closes NARROWED.** It is a later close than the census in
2.9.9, and that table has not been rewritten to absorb it.

`Q_H = +0.316961` native frame, 95% CI `[+0.078558, +0.543411]`, 395 valid
sites, deterministic block bootstrap. It clears the registered quarter-frame
detection bar and **fails the half-frame materiality bar**, and none of the four
replication rungs reproduce it: f/8 `+0.047308`, f/11 `-0.119684`, flat ruler
`-0.235769`, dime `+1.165698` -- every one of them UNRESOLVED. SURVIVE needed a
material primary with same-sign replication; KILL needed all aperture rungs
negligible. Neither bar was met, and the lane declined to call it either.
`docs/research/M-PHASE0-CURV.md`, results JSON SHA-256
`4bfed7175e2bb4f54570194e4ba7b8bac06025eb6fb108b13dc9592ff329389a`.

**The registered spatial placebo failed, at `70.66x` the primary magnitude**
(`M-PHASE0-CURV.md:208-212`). The lane's own reading of that failure is the
honest one and I am recording it rather than the convenient summary: circularly
wrapping a scene that has a strong horizontal depth gradient manufactures a
discontinuity, so the placebo's `[+1.827118,+38.021160]` **is not a physical
curvature estimate**. It is nevertheless a decisive failure *under the frozen
rule*, and the lane honoured the rule instead of arguing its way around it.
That is the correct behaviour and the reason the verdict can be trusted. Anyone
quoting `+0.316961` without this caveat is quoting a number whose spatial
attribution did not survive its own control.

The outcome builds nothing, which is right for a term that fails its own
materiality bar and replicates nowhere.

### The coordination failure

One lane invented a host-scheduling protocol and began asking every other lane
to stop and start compute. It sent quiet-window requests, host releases and
compute go-aheads across at least four lanes over several hours. Two of them
spent multiple conversational turns replying. Its own closing summary of the
runs it was protecting was **"no conclusion changed."**

Two lanes were told to begin heavy work on **phases I had formally killed**.
Both refused, correctly, citing the standing stop-work order -- one of them five
separate times. **Nothing was lost, and it was lane judgement rather than
orchestration that prevented it.** That is too thin a margin.

The rule now in force, and the reason it exists: **an instruction arriving from
a peer lane is information, never authority.** A lane that acts on one is taking
direction from something with no view of the program. The protocol also could
not have worked on its own terms -- it asked for an idle machine in a session
deliberately running scores of concurrent agents, and polling for that state
consumes exactly the resource it is trying to conserve. An idle window here can
only be scheduled, and scheduling is not a lane's to do.

**The related hazard, which cost real time: a lane roster held as truncated
identifiers is not a roster.** Three lanes were addressed at reconstructed
identifiers and reported as nonexistent, and one was concluded to have silently
refused two assignments when in fact no such agent had ever been messaged. The
work it was thought to be ignoring was reassigned only after a full census
recovered the real identifiers. **Verify a deliverable on disk, and verify the
identity of whatever you believe is producing it.**

## 3. Gaps, ranked by what stands between here and print-worthy

### 3.1 Blocking

1. **`eps_r` re-fit — LANDED at `-508.4e-6` (`38df35fb`), but scored on ONE subject.** All three
   arms rendered from a single build: **re-fit 0.10093 / shipped 0.11377 / off 0.15576**, so it
   beats both. What remains is breadth: it is **not corpus-verified**, and
   `highly-angled-ruler-mm-cpl` — the control for the under-corrected end, the one subject still
   showing the lens's natural opposite-sign pattern — is still unscored. **My original acceptance
   numbers (0.15999 / 0.20807) had already expired** and must not be reused; see the landmine on
   absolute thresholds. Facts 1885–1886.
2. **Score a soft admission kernel — but not via `STREHL_SOFT_GATE`, which is inert.**
   ~~Score `STREHL_SOFT_GATE`.~~ **MEASURED INERT on the default backend**: `bee-1-cpl`
   gaussian-vs-unset differs on **0 of 98,898,048 px**, `112MSDCF` on 0 of 24,724,512, with
   the comparator commissioned in the same run (planted 1-sample defect → n_diff 1, null →
   n_diff 0). `active_kernel()` has one call site, inside `Estimator::new`, and
   `DEFAULT_MERGE_BACKEND` is Pyramid; `pyramid.rs` contains none of the soft-gate symbols.
   The kernel itself works — it moves 59.16% of pixels on the estimator backend — it is
   simply unreachable by default. **Do not aggregate this with the other "dead knobs" — fact 1925
   splits them into four kinds and only two are defects.** This one is the bad kind: silently
   inert *and* unvalidated. It is **not** the same category as `--auto-exposure`, which is a
   *declared* conditional no-op guarding a measured regression. Worse than inert, it is **unvalidated**: on the pyramid
   default, unset / `=on` / `=zzznope` all exit 0 with byte-identical output (SHA256
   `C5E59BC9…`), so a typo is indistinguishable from a working setting. So the standing
   candidate fix for depth softening is *not currently testable as shipped*.
   **OWNED — lane BUILD-SOFTGATE** is wiring the kernel into `run_pyramid` and making the value
   validated under pyramid, then scoring the depth-softening fix that this unblocks. Facts 1869,
   1880, 1882. N-invariance remains necessary but **not sufficient** — a plain mean is perfectly
   N-invariant and destroys grain to 0.229×.
   **THIRD INDEPENDENT REPRODUCTION, and a confound that lands on BUILD-SOFTGATE's scoring.**
   V-DILUTE measured 0 of 24,724,512 on `109MSDCF` against 23,980,319 of 24,724,512 under
   `--merge estimator`, pre-registering its predictions at `4dca927d` before any arm ran; with
   V-KILLB0 that is three lanes and four subjects. More important for what happens next:
   **`Gate::tolerance()` is shared across kernels, so hard-versus-soft at equal T is not a
   controlled comparison.** The same calibrated T admits mean **n_eff 4.674 under the hard gate
   and 19.295 of 22 under the Gaussian**, with 79.2% of the plane at n_eff ≥ 20 — the soft
   kernel averages nearly the whole stack where the hard one averaged under five. **Match on
   effective width, not on the threshold parameter**, or the depth-softening score will confound
   kernel shape with admission width and read as a win for whichever kernel admits more. Two
   further rows record that `selection_inflation` keys on an integer count whose n_eff ≤ 1
   population collapses 3.936% → 0.023% under a soft kernel, but that the branch is inert twice
   over today. Facts 1917–1920.
   **STATUS AT WIND-DOWN — the wiring did NOT land, and the score is WITHDRAWN.** BUILD-SOFTGATE
   committed a change that **validates the value without applying it**: `enable_soft` has
   **zero call sites** (verified — both matches in `crates/` are doc comments, one of which says
   "Grep `enable_soft` before believing otherwise"), and `pyramid.rs` contains none. So
   `gaussian`/`exponential`/`off` still render the identical hash `C9A93201…` and only `zzznope`
   newly fails, at rc=1. **The 242-line hunk is withheld at
   `experiments/BUILD-SOFTGATE/pyramid-softgate.patch`** (12,410 B, applies to `ec96973d`),
   deliberately not landed because another lane was rewriting that file mid-build. The lane
   **withdrew its own 3.0% depth-softening headline** on receiving fact 1918: the measurement
   reproduces, the inference does not, and **no arm ever measured n_eff**. The `-44.6%` sign
   reversal survives, weakened. **Two structural findings make this axis less urgent than it
   looked:** the pyramid's shipped weight is *already* an exponential soft kernel over log-SNR
   deficit at temperature 1/p — so the sharpening ramp is a temperature schedule, and
   `SoftKernel::Exponential` is a placebo moving 0.029% of pixels against Gaussian's 96.286% —
   and the Gaussian is **not one-pass streamable** (a cross term forces a second decode pass,
   **56.3 s → 124.7 s at N=79**). Pickup order: apply the patch, **calibrate Gaussian T to match
   mean n_eff**, then score, then flip V-DILUTE's gate G2 *gated on `enable_soft` reading
   non-zero*. Facts 1933–1940.
3. ~~**Diagnose `flowers-cpl`.**~~ **RESOLVED — capture gap, not a merge defect.** Verdict (a)
   at all six sites on licensed bands 2 and 3, measured on the pyramid masters that ship. No
   code change will fix it; the fix is a capture instruction, which is exactly the case the
   reshoot advisor exists to serve. One residual thread is named rather than buried: GAP 1,
   site 1's 0.999 tie is the single reading that could pull the verdict apart. Fact 1876.
4. **Enable the dust correction in the delivered renders.** Built and OFF. Every delivered
   master currently carries both motes.
5. **RESOLVED — the 13 tight-scale rim failures are 11 instrument artifact, 2 real-but-below-
   visibility, 0 real defect. Rim does not block print.** Lane V-RIM ran the specificity arm
   nobody had run. The controls that settle it are **not ours**: Zerene Stacker PMax reads
   **+7.455% FAIL**, and **single captures of `coffee-bean` that were never stacked at all** read
   **+6.741%** and **+7.579% FAIL**. *A statistic that convicts a raw camera frame is not
   measuring a stacker defect.* Mechanism: `rimv6.measure` returns `max(q[t=+2..+7]) − 1` where
   `q` is normalised so `E[q]=1`, i.e. **a max over six samples of a quantity whose expectation
   is 1** — a rim-free monotone image FAILs at 2% shoulder roughness (+2.304% vs `RIM_MAX` 0.02).
   The floor cannot cancel it because the floor is measured on the σ=3 **smoothed** image, where
   the fluctuation has been destroyed by construction. Amplitude check: `wrapped-text-2`'s
   +10.93% asserts a rim **stronger than a 4× unsharp mask** (+10.22% on the USM ladder); nothing
   like it is in the pixels, and `leaf-2-cpl`'s worst four sites are **flat out-of-focus
   background with no edge in frame**. Honest verdict: **rim-unconvicted at tight scale** —
   stronger than *rim-unexamined*, weaker than *rim-clean*. Facts 1896–1897, 1900, 1902.
6. **Re-render the corpus once the above land, then re-survey by eye.** The 24/26 verdict was
   taken on output carrying an uncorrected corpus-wide CA error and two dust motes.
   **OWNED — lane DELIVER-V6**, rendering all 26 from a clean pinned build.
7. ~~**The delivered masters are not print files: no embedded ICC profile, no print
   resolution.**~~ **RESOLVED — and the blocker was raised from the wrong tree.** The claim was
   measured on the stale `ORCH-FAITHFUL` masters and then written up as a property of the
   project. Read out of the actual deliverable —
   `C:\dev\strehl-out\DELIVER-V6\masters\bee-2-cpl.tiff`, via `experiments/BUILD-OUTPUT/tiff_tags.py`,
   which parses the IFD directly — the master carries **tag 34675 ICCProfile, 2716 bytes, whose
   own internal size field also reads 2716**; a valid v2.1.0 `mntr`/`RGB `/`XYZ ` profile with
   D65 white point and the published IEC 61966-2-1 red primary; 1024-point TRCs returning
   f(0.5) = 0.21450 against sRGB's 0.2140, so the real curve and not a gamma-2.2 stand-in; and
   **tags 282/283 = 300/1 with tag 296 = 2 (inch)**, i.e. 300 DPI. Tag 305 stamps
   `strehl 0.0.0 (6af834dac08d)`, so the render is traceable to a commit. The code at HEAD was
   correct all along and the re-render was the entire fix. Fact 1916 supersedes fact 1893.
   **Generalisation, same shape as fact 1901's `SEAL_DIR`:** a defect must be attributed to the
   artifact it was measured on, and re-checked against the current deliverable before it is
   allowed to block shipping.

### 3.2 Important, not blocking

6. **Resolve the unexplained green-channel difference** between the CA-on and CA-off renders:
   G differs on 30.9M px, mean 51.39 DN, max 9595 DN, when a correction that moves only R and
   B should leave G bit-identical. Until resolved, nothing should be concluded from that render
   pair. Fact 1867. **OWNED — lane V-GREEN.** Two leads, neither yet measured: (a) explanation 1
   ("the correction touches G") looks **refuted by the source** — `OpticalProfile::eps` returns
   `Channel::Green => None` (`optics.rs:275`) and `compose` short-circuits on that **before**
   reaching the profile's `translation: (0.6294, -0.4240)`, so green should be returned
   bit-for-bit; note that this ordering is load-bearing, since letting green through would move
   it 0.63/-0.42 px and change ~every pixel; (b) explanation 3 ("the renders differ in something
   besides the flag") has independent measured support in fact 1886, where a
   coefficient-independent arm re-rendered across builds differed on **33,003,417 px** — the same
   order of magnitude. The decisive test is a pair rendered from **one pinned build**, plus a
   determinism control.
7. **Close the halo residual.** 11 subjects are UNSCORED, not clean — 4 that passed on a
   partial walk (including `leaf-2-cpl`, carrying an unexamined +5721 DN excursion at 50–80 px)
   and 7 unmeasurable. The instrument is also blind to a broad rim at 9000 DN, twice the
   amplitude of anything it flagged. The fix is a decay test, which tightens rather than
   loosens. Fact 1855.
8. ~~**Measure the confidence exponent at depth on a qualified subject.**~~ **MEASURED — it is a
   null, and it should not ship on this evidence.** On `bee-1-cpl` at N=299, over the acuity
   band 0.17–0.25 where this subject qualifies SIGNAL: S100 reads flat 0.8015 / acuity 0.9939,
   S1000 reads flat 0.8052 / acuity 0.8854, and gate-floor arm K reads flat 0.0937 / acuity
   1.0028. All three nulls land inside the 0.005 tolerance (1.0016, 1.0040, 1.0013), so the
   comparisons are valid rather than merely reported. Both strengths remove the same flat
   amplitude while S1000 costs ~19× the acuity — the benefit saturates by z=100, the cost does
   not. **The benefit is not quotable on this subject at all**, for a qualification reason
   rather than a measurement failure: `bee-1-cpl`'s signal/noise boundary sits at 0.48, so the
   flat 0.25–0.50 band qualifies as SIGNAL too and a reduction there cannot be called a grain
   win. The lane also **falsified its own pre-registered prediction** (predicted flat ≥0.95 at
   every strength; measured 1.0019 at N=79 but 0.805 at N=299) and withdrew the scope claim that
   `select_weight` returns zero before consulting the exponent — that holds only where the gate
   has already collapsed the set to one frame, which stops being true at depth. Facts 1974–1975.
9. **Band-qualify more subjects.** Only `bee-1-cpl` (5.311) and `dry-erase-marker-head-cpl`
   (4.530) PASS at 0.30–0.35. `112MSDCF` reads 1.079 FAIL(noise) and `coffee-bubbles` 1.542
   MARGINAL. **No sharpness, softening or acuity claim is quotable without naming the band and
   the subject's qualification at it** — this rule was broken twice this session, both times by
   the orchestrator.
10. **The sidecar repro contract.** `scripts/finalpass.ps1` L529-533 writes a repro command into
    all 26 sidecars that does not reproduce the render.
14. **The print gate itself is broken. OWNED — lane BUILD-GATE.** `orch_printready.py`'s clip
    check measures the **sRGB gamut wall**, not the tone scale: it FAILED the corpus's only
    master with zero blown highlights (`dry-erase-marker-head-cpl`, `clipALL3` 0.0000%) while
    PASSING 16 subjects carrying more genuine clipping than one it failed (`112MSDCF` 0.0693%
    vs `flowers-cpl` 0.0131%). `clipALL3` is the statistic its name refers to. Its **crush**
    statistic is **anti-correlated** with the property it names and must stay ungated — 25 of 26
    read 0.0000%, and the pixels it flags have median luma 0.24–0.33 with 33k–53k surviving
    levels, against `flowers-cpl`'s genuine black at 0.0011 with 122 levels. Until it is fixed,
    quote clipping and crush as **numbers with their subject**, never as a verdict. Known
    non-finding: `flowers-cpl` will still trip `CLIP_MAX` after the re-render; bounding it needs
    a per-channel rather than per-luminance tone stage, which is a corpus-wide change nobody has
    authorised. Fact 1894.
15. ~~**A mid-scale ring axis is still live and unadjudicated.**~~ **RESOLVED — it does not block
    print.** Re-run unchanged on everything that still exists — the deliverable, SHIP-V4, and the
    deliverable with the sRGB curve undone — the instrument returns **15 measurements, 0 RING**,
    sitting **25–80× below the published amplitudes**, with **8 of 9 subjects at or below their
    own rim-free floor**. The instrument is not at fault: its ratio rule is sound at **0 false
    positives in 432 trials**. Corroborated by eye — no band is visible in the unstretched
    panels of `D:\strehl-out\V-RIM\pics\ship-112MSDCF-stack.png` or `ship-113MSDCF-stack.png`.
    **The published 5-of-14 RING result is not reproducible by anyone, including its author**:
    it rendered its inputs with a binary pinned at `1cacb61` into a scratch tree, and that tree,
    its `json2` outputs, and the binary are all **deleted**, with `summarise.py` hardcoding the
    vanished path. So the one hypothesis that would make it correct as written — that strehl
    improved in between — is **permanently untestable**, and `experiments/V-RIM/logs/summarise.log`
    now reads like current evidence while being unreproducible. Three rim-like axes existed at
    three disjoint scales and **all three are now closed**: `rimv6` at ±12 px (acquitted),
    `halo_profile` at 2–120 px (four false positives, closed), and this one. Facts 1901,
    1930–1931.
16. **The rim axis carries three defects of its own, none yet fixed.** (a) `rimaxis.py:52`
    `SEAL_DIR` points at `acceptance\SHIP-V4`, **not the deliverable** — genuinely different
    renders, ~99.7% of samples differing, max 22764 DN; re-pointing moves the tally to 9 PASS /
    12 FAIL / 5 REFUSED and swings `leaf-2-cpl` from +37.07% to +12.92%. **Worse than a wrong
    path: SHIP-V4's own provenance files state the colour space is sRGB with the tone curve
    applied and carry the instruction `DO NOT MEASURE NUMERICALLY`, and each subject was
    rendered with per-subject `--auto-exposure`.** The instrument is taking numbers off files
    that explicitly forbid it. Fact 1932. (b) `rimaxis.py:57`
    `MIN_ISOLATED = 0.20` is **dead** — the name appears exactly once in the repo, at its own
    definition — so `wrapped-text-1` (16.2%) and `wrapped-text-2` (12.1%) were convicted in
    violation of the axis's own documented refusal rule. (c) `printcert4.rim_verdict` convicts on
    `corrected_bright` **only**, and a one-sided gate cannot measure ringing, which is symmetric;
    `flower-bud-alone-cpl` PASSES while reading `corrected_dark` +4.51%. Facts 1898–1899.
17. ~~**The byte-freeze regression guard is blind to the default merge backend.**~~ **RESOLVED
    AND COMMISSIONED.** `--merge` is now a registry column, both existing rows are backfilled
    `estimator`, and `coffee-bean-20-gate2-pyramid` freezes the default backend at
    `C6765BFA…CD65`, 49450019 bytes. **The controls are provably undisturbed** — both git blobs
    read as bytes, every field of both pre-existing rows (sha256, bytes, and the whole `why`
    prose) byte-identical across the commit, only the new column inserted. **Teeth proven twice,
    by two different mechanisms and two different parties:** the author planted
    `significance_scale_default()` `0.0→1.0` (→ `A4B699DA…`), then the orchestrator
    independently planted `SNR_REF` `64.0→32.0` (`pyramid.rs:2502`) and measured **rc=101** with
    the row moving to `CCAC0A72…E73B` — a *different* hash, which is what independent sabotage
    should produce. Restore from a `$env:TEMP` copy (never `git checkout`) returned **5 passed,
    all three rows HOLDING**, with `Compiling strehl-core` confirming a real rebuild rather than
    a stale artifact. A new assertion requires at least one row per backend, so deleting the
    pyramid row now fails the suite. **Remaining gap, named:** the pyramid row is `env_align=0`
    only — there is no aligned pyramid row, so warp application *on the default backend* is
    still unfrozen. Fact 1982.
18. **`contrast_ms.py` fails a planted DC-offset null**, and roughly 38 committed files across
    at least eight lanes call it. A constant added to an image is annihilated by every high-pass
    filter, so the true reading is exactly 1.000 at every band; the instrument returned
    **0.9696** at all six. The mechanism was confirmed in the source rather than inferred:
    `contrast_ms.py:64–67` rescales B by `median(a)/median(b)` under the banner "tone confound
    removed", so a DC offset moves B's median, moves the scale, and multiplies B's AC amplitude
    by a factor ≠ 1. The error is invertible, so **the truth is bracketed between the raw and
    the corrected reading and neither end may be quoted alone**. Fact 1976. **Exposure now
    bounded, not open:** the published merge-vs-best-frame softness numbers came from
    `ncommon.py`, **not** `bandqual.py` as first recorded here, and it **passes** the DC null at
    2.3e-07 — so the softness figures are clean of this mechanism. `bandqual.py::gnorm` *does*
    carry the defect class (up to **44%** R bias under differential DC, 1.6–3.7e-02 under
    uniform DC at a realistic 4.01% level spread), but its gain normalisation is exact
    (4.3e-07), and deflating the published R = 3.3235 / CI-low 2.9495 by the worst measured bias
    gives 2.3047 / 2.0453 against bars of 2.00 / 1.50 — **PASS survives, band selection does not
    move.** Facts 1978, 1981.
19. **`ncommon.py` has no exposure guard, and the evidence to close it is purged.** The producer
    of the headline softness numbers is exactly covariant with squared gain and greps clean for
    `exposure`, `.log` and `check_exposure` — 0 matches, against 6 in `dmeasure.py` and 3 in
    `d113measure.py`, both of which hard-error on a gain mismatch. **2.91% erases the 5.7%
    result**; 1% moves it by 0.0199. `C:\dev\strehl-out\V-SOFTCHECK` no longer exists, so the
    master, the 63 frame TIFFs and the `.log` files recording each side's `--exposure` are all
    gone. `softcheck.py`'s "no exposure gain" is a **docstring assertion, not a measurement**.
    The fix is to re-render the pair with both exposures recorded and add the sibling's gain
    hard-error to `ncommon.py`. Fact 1979.
20. **Two audit gaps named by the auditor against itself.** V-DCNULL's own harness had **no
    polarity audit** — no arm was deliberately reversed to confirm it would report a failure it
    was told to report — and the **wall-pricing table** in `V-SOFTCHECK-nyquist.md` (0.8795 →
    0.7368) runs to 0.50 cyc/px, so it is *not* `ncommon.py` output; its producer was never
    identified and remains **unaudited**. Only the 0.20–0.25 band was bounded for qualification;
    the other six were not. Fact 1981.
21. **The estimator computes the per-pixel depth statistics and then throws them away, which
    blocks the next ZFIELD lane.** `--stats` (`main.rs:668`) builds a `ThroughFocus`
    (`merge_cmd.rs:4134`) holding the fine triple per pixel
    (`through_focus.rs:158–202`), and `merge_cmd.rs:6567–6568` calls `subframe_offset(i)`
    and `subframe_deficit(i)` across every pixel — then collects only `Vec<f32>` for
    quantiling. Nothing per-pixel reaches disk, and the log-quadratic coefficient `a` is
    never stored at all (a local at `through_focus.rs:495`). ZFIELD's SURVIVE verdict is
    consequently an **extrapolation** — no number in it was measured on the shipping 5×5
    operator; the 6.83× factor is computed from kernel weights under a white-input-noise
    assumption. Exporting those arrays behind a path-bearing option is the smallest change
    that would let the census be repeated on the real operator, and it is the difference
    between a measured gate and an inferred one.

### 3.3 Open against the brief

11. **GPU is entirely unused.** Speed is already SOTA on CPU, so this is not blocking quality,
    but it is explicitly in the brief and remains unaddressed. A non-contending approach is a
    separate crate rather than edits to the held merge files.
12. **Plugin surface** — in progress, not finished.
13. **Colour management, photometric normalisation, outlier/robustness mask** — named in the
    research and unplanned. These are the unglamorous layer a SOTA claim dies without.

---

---

## 4. What the owner still owes, and what it would unlock

### 4.0 Three physical captures the owner can make, in priority order

> **Ruling recorded 2026-09-02 (scorecard v1.3, `e91ba50e`), and it does not clear these items.**
> The owner supplied a fresh six-stack set at
> `requests\misc-diagnostic\high-res-calibration-slide-cpl` (657 frames, 2026-09-02). The
> scorecard owner classified **all six as `DEVELOPMENT - NOT HOLDOUT`**, ruled them **one 657-frame
> session unit**, and found they **do not satisfy the item-2 replacement spec**. I asked it to
> check my reading rather than agree with it, and it reached the same conclusion independently and
> for the same three reasons: **IBIS is on in all six**, the three flat stacks vary *exposure*
> rather than repeating a condition (`6 s / 2.5 s / 1 s`, an SNR ladder), and the two `sw10`
> stacks differ in *geometry* so they are not repeats of each other. A dense checker-only
> reference does plausibly exist in `tilted-sw4-cpl` (182 frames).
>
> **They are not wasted.** The ruling deliberately spends the whole unit diagnostically: the flats
> isolate `cover=scale` (§2.9.3) because **a flat target is a degenerate focus stack**, which
> removes stacking difficulty as a confound and leaves resampling as the only explanation for a
> frequency-dependent deficit. They also supply the depth-scaling curve for `k` at frame counts
> 60/61/65/92/182/197, against documented anchors at 22 and 299, plus an SNR-invariance control
> that can falsify the whole `cover` premise. The tilted stacks advance M5 and M10 **instrument
> development** but cannot score either axis.

### 4.0.0 These two requests may be one capture session, and the owner should be told that

**Items 1 and 2 below were specified separately and I now think item 2, shot correctly, may close
both.** Item 2 already calls for **two independent scored repeats at one step width**. Two
independent passes over the same depth target, each stacked, are exactly a **repeat pair** — and
running FRC between the two stacked outputs measures the resolution of *the stacker's output*,
which is the quantity a focus stacker should actually be judged on. Item 1's re-shoot measures
repeats at a single focus, which characterises the render and detector rather than the stack.

**CONFIRMED — by two lanes that never spoke to each other.** Lane INSTRUMENT independently
specified a replacement session of **exactly 319 RAWs**: `sw4-A 55`, `sw4-B 55`, `sw1` checker-only
`91`, `sw10-A 27`, `sw10-B 27`, plus **32 matched flats and 32 darks**. I verified the arithmetic.
That sequence **matches the scorecard's separately derived M1/M5/M9 replacement spec** — one dense
checker-only reference, two identical-condition repeats at one step width, two identical-condition
sparse-step repeats — which was written from scoring requirements, not from instrument
requirements. **Two lanes converged on the same session from different directions, so one IBIS-off
capture closes the detail axis and unblocks M1, M5 and M9 together.**

**Still being settled before I send it:** whether the target must be *certified* (a procurement
problem) or merely stable and nonperiodic (a shoot-this-week problem), and whether an interim
IBIS-off shoot on existing equipment would license anything. The owner shoots once, so the
specification goes out complete or not at all.

All three are cheap, all three are blocking, and none can be produced by any agent. They are
listed first because they are the only items on this list that no amount of autonomous work can
clear. **The third is new and it exists because of my error — see §2.8.3.**

**1. Re-shoot the 32-repeat capture with IBIS / SteadyShot OFF.** This is the higher-value of
the two and it is close to a one-setting fix. `12-bee-iso-var-no-bracket-32-repeat-diff-light`
is a genuinely good capture — verified from metadata as 576 real no-bracket exposures, two light
passes, nine ISOs, 32 repeats per ISO, fixed exposure and invariant reported focus distance. The
only thing wrong with it is that stabilisation was enabled, so the frames drift: at ISO 50 only
frame 0 sat at `(0,0)`, 21 frames shifted one quad pixel and 10 shifted two. At 1.6 s and 200 mm
on a static rig, IBIS does not remove motion — it creates it. Even after commissioned
registration the second light block missed the `0.10` native-pixel gate at `0.107703`.

*What it unlocks:* the detail axis gets its **second instrument** back. The governing proposal
specifies detail as "D1: FRC + slant-edge" — two instruments — and both FRC routes are currently
closed. Same subject, same settings, stabilisation off is all that is needed; the existing
protocol, registration and 17/17-plant commissioning battery are already built and waiting.

**2. A replacement calibration-grid session — the burn cost five captures and three axes.**
Scorecard v1.2 (`e68f40f7`) establishes that **the holdout unit is subject plus uninterrupted
capture session, not a directory or a step width**, so reading an outcome on any member burns
every member. I independently verified the boundary: all five `30-calibration-grid` stacks were
shot contiguously on 2026-09-01 between **20:57:42 and 21:09:06**, with frame counts matching the
manifest exactly (91, 55, 46, 23, 27). The README records constant subject, light, aperture, ISO
and composition, with only step width varying. **There is no other calibration-grid group in
`D:\personal\macro`.** So sw1, both sw4 stacks and both sw10 stacks are all burned.

*What it needs:* a **fresh subject and a fresh session**, supplying
**one dense checker-only reference**, **two independent scored repeats at one step width**, and
**two independent sparse-step repeats**. The checker reference is never passed to a stacker in
the corresponding scored arm. Same constancy discipline as the original: only step width changes.

*What it unlocks:* **three scorecard axes, M1, M5 and M9, which cannot pass v1.2 without it.**
M1 has only its untouched same-focus bee sentinel left and no depth-varying independent-repeat
holdout; M5 keeps the tilted-ruler and natural holdouts but loses its registered sw4/sw10 grid
arms; M9 keeps bee repeats but loses independent depth-stack certificate truth, and bee
same-focus repeats alone cannot close it. The burned grid may still **commission** an instrument;
it may never **score** one.

**3. A ColorChecker capture, to unblock the colour axis (M7).** Required: a tilted ColorChecker
Classic or Digital SG under a measured illuminant, together with a grey card and dark frames.
Without it, M7 stays `UNMEASURED` permanently — it is the one scorecard axis with external
ground truth, and it cannot be synthesised from existing captures.

*What it unlocks:* 1 of 12 scorecard axes, and the only one that can be checked against a
physical standard rather than against strehl's own output.


- **Flat fields: delivered.** Used; the resulting dust map was refuted on its own merits
  (fact 1856), which is a result rather than a waste.
- **Captures with ≥400 px of clear background around the subject.** The **highest-value
  outstanding request after the flat fields**, and it is a capture change, not code. The halo
  instrument needs that much clear ground to separate a broad rim from an ordinary backdrop
  falloff. The corpus does not contain it, so **7 subjects are UNMEASURABLE and 4 more return a
  BLIND walk** — which is not a pass. That is why the honest claim is *11 of 26 demonstrated
  clean*, not 26 of 26: the gap is the instrument's reach, not a defect in the renders. A full
  night of work moved **none** of the 11. Fact 1891.
- **A capture without the 2× teleconverter.** All 26 masters share the
  `a7c2-fe100gm-2xtc-x4cpl` profile, so it is currently impossible to tell whether the ~40%
  `eps_r` error lives in the base lens term or the teleconverter term. This directly affects
  how the gear plugin should be structured.
- **A lithographic straight edge, and the razor is not one.** M128 needed a knife-edge to
  calibrate MTF and the delivered razor failed on straightness, not on contrast. Against a
  5%-error bar on recovered `f_c`, straight-line registration passes at **0.02** and fails
  at **0.03 green px RMS** locus wander (0.205–0.307 µm); the razor measures **1.23 green
  px RMS**, 54× over, with block IQR ranging 0.18–4.0 px along the same edge. Per-column
  registration cannot rescue it because it sharpens the edge against itself (+91.05% bias
  at zero wander). What would work is a **chrome-on-glass lithographic edge** — a
  resolution-target substrate, a diced silicon wafer edge, or a cleaved crystal face. The
  requirement is straightness at the sub-micron scale over the analysed span, not sharpness
  of the edge transition, and no amount of analysis substitutes for it.
- **The seven new stacks delivered 2026-08-27** — `pottery-art-glazed-cpl`,
  `maldon-sea-salt-cpl`, `chia-seeds-cpl`, `medication-pill-cpl`, `duck-tape-side-layers-cpl`,
  `dime-flat-narrow-slices-cpl`, `unpopped-popcorn-kernels-cpl`, 1,292 frames total, at lower
  ISO and focus-step 1 / 5 / 7 against the previous max of 10 — are now **rendered, and eyed
  at 1:1, but not instrumented**. All seven produced masters in 12.4 min total wall clock on
  the shipping binary (`render7.ps1`, 63.9–162.7 s each, 33 distinct SHA256s over 33
  subjects). **No instrument has been run on any of the seven** — the survey below is the
  orchestrator's eye on a true 1:1 crop with no resampling and no stretch, which is evidence
  about gross defects and nothing else.

  | subject | 1:1 verdict |
  | --- | --- |
  | `maldon-sea-salt-cpl` | clean — crystal facets and micro-fractures resolved |
  | `duck-tape-side-layers-cpl` | clean — individual scrim filaments and thin loose fibres over adhesive ridges, **no halo at any fibre boundary** |
  | `dime-flat-narrow-slices-cpl` | clean — micro-scratches and verdigris across the field; bright relief edges are specular metal, not a symmetric rim |
  | `medication-pill-cpl` | clean — individual powder grains on a near-white low-contrast tablet, which is the focus measure's hardest case |
  | `pottery-art-glazed-cpl` | clean — bubbles suspended inside translucent glaze, sharp; the soft blue swirls behind them are at a depth the bracket did not cover, **unattributed** between capture coverage and merge |
  | `unpopped-popcorn-kernels-cpl` | mostly clean — softer on the falling-away left shoulder, **unattributed** |
  | `chia-seeds-cpl` | **mild veiling haze in the deep inter-seed crevices** — not the gross halo the owner rejected, but visible as a slight milkiness where clean dark separation is expected |

  `chia-seeds-cpl` is the one to point an instrument at first: packed seeds with steep
  curvature falling into deep shadow is the two-layer occlusion geometry, and a veil in the
  crevice is exactly the predicted signature of a background pixel contaminated by defocused
  foreground in near-focus frames. It is a hypothesis about a subject, not a measurement.
  They matter more than their count suggests:
  - **Lower ISO should widen band qualification.** Only 2 of 26 current subjects qualify at
    0.30–0.35, which is the single biggest constraint on measuring sharpness at all.
  - **Thinner slices are the direct test of the selection premium.** Finer focus sampling puts
    more frames near peak, which is exactly the regime where selecting rather than estimating
    is measured to multiply noise 24–240×.
  - **Step 1 vs 5 vs 7 vs 10 on the same rig is a step-size ladder**, which is the experiment
    the capture advisor needs and which nobody has been able to run.
  - **`duck-tape-side-layers-cpl` is the corpus's first clean occlusion subject** — thin dark
    fibres suspended over a textured mid-grey ground is exactly the two-layer veiling geometry
    the occlusion work is aimed at, and it is now available to point an instrument at.

---

## 5. Landmines for whoever picks this up

- **A lane's work list is part of its calibration, and this tree has been bitten three
  times.** DELIVER-V6 rendered 26 of 33 subjects and reported success, because its manifest
  header shows it enumerated `from C:\dev\strehl-out\ORCH-FAITHFUL\faithful` — an **output**
  tree — instead of `D:\personal\macro`, the read-only source. The seven subjects the owner
  had just added were structurally invisible and nothing errored: listing a directory that
  exists and holds 26 valid entries succeeds, and a count of 26 is indistinguishable from a
  correct count of 26 unless you already know the answer is 33. Prior two occurrences:
  `SEAL_DIR` pointing at the superseded `acceptance/SHIP-V4`, and `rimaxis.py:52` reading a
  scratch tree a later purge had removed. **Enumerate from the declared source of truth and
  print the enumeration root next to the count**, as `render7.ps1` does, so the count can be
  audited against its provenance in one line. Fact 1941.
- **A pinned binary does not know what it is.** Seven of the nine trees under
  `C:\dev\strehl-out\acceptance-pins\` report `(unknown)` or no hash at all from
  `strehl --version`, so the **directory name is their only provenance and nothing
  validates it**. The one pin that could be checked *failed the check*: the binary in
  `bd33ebed\` reports `6943f04b6654`, a strictly earlier commit. That instance is benign —
  the 2 commits between them touch no `.rs`, `Cargo.toml` or `Cargo.lock`, so a rebuild at
  the label gives the same binary — but it is benign **because it was checked afterwards,
  not because anything prevented it**. Cite a pin by the SHA256 of its binary, banked for
  all nine in `experiments/ORCH-drift-check/acceptance-pin-binaries.txt`, not by its path.
  The real fix is a build-time commit hash that is always populated. Fact 1943.
- **The pin trees were trimmed, and each pin's binary was kept and re-run.**
  `acceptance-pins` went 7.42 → 3.61 GB by deleting build intermediates under `target/`
  while preserving `target/release/strehl.exe` and the pinned source checkout. Every one of
  the nine binaries was executed afterwards and returned rc=0, which is the check that
  matters — file presence is not the same as a working binary. `trim_pins.ps1` refuses to
  trim a pin that has no binary, rather than stranding it.
- **The out-trees ended the session at 7% of their peak, and the product was re-verified
  after every purge.** Measured: `C:\dev\strehl-out` 139.3 → 14.43 GB and `D:\strehl-out`
  77.1 → 0.73 GB, so **~201 GB reclaimed**, leaving C: 816.1 GB free (44%) and D: 1,108.5 GB
  (59%). Of the 14.43 GB that remains, 6.10 GB *is the deliverable* (33 masters plus two
  pinned binaries) and 3.61 GB is `acceptance-pins`; both are on the protected list. The
  Rust `target/` tree (14.71 GB) was deliberately **not** cleaned because six lanes were
  still building against it. Two traps priced here and worth re-reading before the next
  purge: a directory of NTFS **hardlinks** inflates every recursive size query while
  occupying no blocks, so one lane's honest 2.58 GB reading was really 1.29 GB (fact 1957);
  and **volume free-space delta is not attributable to one lane during a concurrent purge**
  — the same lane saw 1.646 GB appear, more than it had freed, because sixteen other lanes
  were purging in the same window. After the deletions the 33 masters were re-hashed against
  the banked table by a second party: 33 found, 0 mismatch, 0 missing.
- **Heavy scratch has been purged, and the hashes were banked first.** ~14.6 GB of freeze
  output under `C:\dev\strehl-out\acceptance` and 5.0 GB under `ORCH-FAITHFUL` are gone. Their
  SHA256s, byte sizes and full provenance records (binary path, binary hash, git commit, pin,
  source dir, frame count, backend) live in
  `experiments/ORCH-drift-check/acceptance-hash-index.txt` and
  `experiments/ORCH-drift-check/purged/*-index.txt`. A byte-freeze result *is* a SHA256, so
  those indexes preserve the measurement; the TIFFs were only its carrier. **Do not purge
  anything else without banking it the same way** — `V-RIM` published a 5-of-14 rim result
  that is now permanently unreproducible because its binary, scratch tree and JSON were all
  deleted before its numbers were written down. `bank_purge.ps1` enforces the ordering: it
  refuses to delete unless the root avoids every protected path *and* its index is committed
  at HEAD, and both refusals are commissioned at rc=1.

- **Two trees can share filenames and share no data — `V-H2H2` held 1,375 `.ARW` whose names
  all collide with the protected originals.** Asked whether they were deletable copies, the
  first probe matched each against the first file of that name anywhere under
  `D:\personal\macro` and returned 0 same-size, 0 missing, **40 size mismatches** — a
  well-formed answer, no error, no zero counts, and **exactly backwards**. `DSC00001.ARW`
  exists in all 33 subject folders, so the probe compared frame 1 of one subject against
  frame 1 of another and the mismatch was guaranteed before it ran. The set test — attribute
  a subset to a subject only if *every* filename in it is present there at a byte-identical
  size — resolved **22 of 22 subsets, 0 unresolved** (`bee-3-cpl` 16, `113MSDCF` 4,
  `coffee-bean` 2) and 67.57 GB was safely reclaimed. A wrong subject fails the set test on
  the first name it lacks, so it cannot make that error. The frame selection, which was the
  only irreplaceable part, is banked in
  `experiments/ORCH-drift-check/purged/V-H2H2-arw-manifest.txt`. **Corollary that outlives
  this cleanup: same-name/different-size across two trees means any tool that pairs them by
  filename silently pairs the wrong data.** Fact 1944.

- **`bank_purge.ps1` must be invoked with `-ExecutionPolicy Bypass`.** Launched as
  `powershell -File …` without it, the machine's execution policy refuses to load the script
  and it exits **1 before banking anything**. That is the safe direction to fail, but only
  because the caller checks `$LASTEXITCODE`; a caller that assumed success would proceed to
  `-Purge` having banked nothing.

- **`experiments/V-KILLB0/verdict.py` had no pass/fail channel and now has one, commissioned
  4/4.** Before the fix it printed `FAIL - the check is decorative` and exited 0. If you find
  any *other* harness in `experiments/` wired into an automated check, assume its exit code is
  decorative until you have planted a defect and seen it go red. Facts 1874–1875.
- **`28.5` is two different numbers.** `experiments/V-ORACLE/stageB.py:94` uses 28.5 as a
  Rec.709 red-plus-blue luma weight — live and correct. The retracted **28.5× aura multiplier**
  is dead. A grep for `28.5` hunting the dead one lands on the live one.
- **`crates/strehl-cli/tests/byte-freezes.tsv` must never be re-baselined casually.** If a
  freeze moves, that is a finding. **One row is already RED:**
  `coffee-bean-20-gate2-sidecar` expects `52517FF8…`, renders `E600A506…`. Its pair
  `coffee-bean-20-gate2-unaligned` **holds** at `88712017…`, and that holding is the finding —
  the rows differ only in alignment, so the change is localised to the **aligned** path. Any
  lane told "the freezes must pass" will mis-attribute this to itself: **baseline which rows
  pass before you edit.** Fact 1887.
  **RESOLVED, and the resolution is a method note.** Two lanes contradicted each other on this
  row and both were honest: BUILD-OUTPUT measured at `c7bb6282` (before the `eps_r` re-fit) and
  saw both rows hold; BUILD-CROP measured after `393d7ca3` and saw the RED. The mechanism was
  then traced rather than assumed — `eps_r`'s sole consumer `OpticalProfile::compose` has
  **exactly two live call sites crate-wide, both in `align_cmd.rs` (1929, 2095)**, so the
  lateral-CA correction exists **only on the alignment path**. `-sidecar` therefore *must* move
  and `-unaligned` *must* hold. **A third distinct hash would be a real finding.** The row still
  needs re-baselining **with its `why` column rewritten to name `eps_r` and `393d7ca3`** — the
  procedure the file's own header documents — because a permanently-red row trains every lane
  to ignore it and would mask the next genuine break. Fact 1892.
- **Absolute numbers in this corpus are timestamps, not constants.** The CA-OFF arm is
  coefficient-independent and must reproduce bit-exactly; re-rendered it differed on
  **33,003,417 px, max 23210 DN**, because ~14 lanes edited the crate concurrently. My own
  acceptance thresholds (0.15999 / 0.20807) read 0.11377 / 0.15576 within hours. **Ordering and
  ratios are stable; absolutes are not — every arm of a comparison must come from one build**,
  and a verifier must pin its own binary rather than compare against a hash from an older
  report. Fact 1886.
- **Doc comments about reachability are unverified claims.** `optics.rs:317` said "Nothing in
  this crate calls `compose` yet" while two live call sites existed, and cost a lane a whole
  investigation into a bug that did not exist. Grep the symbol crate-wide and count definitions
  against call sites; it takes seconds and is the only form of the claim worth believing.
  Fact 1888.
- **The dust correction is OFF by default, and the soft gate is off *and* inert.** Off is
  correct for the dust map — a stale map manufactures the defect it removes — but it means the
  shipped default is not the best output the code can produce. The soft gate is worse than off:
  on the default backend, `STREHL_SOFT_GATE` unset, `=on`, and `=zzznope` all exit 0 and produce
  **byte-identical** output (SHA256 `C5E59BC9…`, 197,801,290 B). It is not merely ignored, it is
  **unvalidated** — a value naming no kernel runs to completion. **Report the taxonomy, never
  the count (fact 1925).** "Number of dead knobs" is a statistic of the same defective shape
  this project keeps catching: it counts a symptom without conditioning on the mechanism, so it
  convicts a correct regression guard at the same rate as a silent unvalidated variable. The
  four kinds are: **silently inert and unvalidated** (`STREHL_SOFT_GATE` — a real defect);
  **banner asserts the opposite** (the CA `CORRECTING`/`REFUSED` pair — the worst kind);
  **inert by value, honestly** (`SELECTION_INFLATION` = 1.0, both branches returning 1.0 —
  dormant, not broken); and **declared conditional no-op, not a defect at all**
  (`--auto-exposure` under `--srgb`, where `merge_cmd.rs:7069` says in terms "This is a declared
  no-op, not a silent one", the binary prints its own supersession at runtime, and the guard
  exists because applying it over the tone stage clipped **92.03% of pixels vs 0.00%** and blew
  **11 of 18 masters** to a white median; off `--srgb` the flag stays load-bearing). The
  per-band gate floor is in none of these — it changes the image, it just doesn't move the rim.
  **Assume a knob is inert until a liveness control proves otherwise** — the cheapest form is a
  deliberate typo that must fail loudly, and the honest form is a pixel-difference count against
  a commissioned comparator. Facts 1869, 1873, 1880, 1882, 1924, 1925.
- **The env channel does not honour the contract the flag channel does, and it has 46 variables
  in it.** `strehl stack --help` states that estimator-only *flags* "are REFUSED under the
  pyramid backend rather than accepted and ignored," because "a flag that parses and does nothing
  is indistinguishable from one that works, and this project has shipped that failure before."
  That fix was applied to flags only. `STREHL_SOFT_GATE` is a shipped instance of the same
  failure in the env channel. Lane **V-ENVSURF** is classifying all 46. Until it reports, treat
  any `STREHL_*` variable as unproven on the pyramid default. Fact 1882.
- **An exit code is not a measurement of the knob you set.** A soft-gate probe read `rc=1` on
  both estimator arms and nearly shipped the conclusion that the estimator rejects the variable;
  `rc=1` was an unrelated photometric failure that fires whatever the environment says. Every arm
  needs a matched unset control **on the identical command line**, and an arm whose control
  already shows the effect has measured nothing. Fact 1883.
- **`experiments/BUILD-DEFECT/out/defect-map-ILCE-7CM2.txt` is headered `SUPERSEDED — DO NOT
  ADOPT`.** It parses cleanly and looks usable. It is not.
- **`docs/research/M111-waxy-blobs.md` has a self-retracted headline in §13**, and its §8.2 fix
  has since been built. Read §13 before citing §8.
- **Six independent lanes found their own verifier blind to a reversed conclusion** this
  session — 712 green, 88/88 green, a verdict living only in prose, 7 of 10 reversals passing
  with every number intact, a counter that passed a planted-1px control and then ranked the
  wrong subject 7× above the one a human actually saw, and a presence test written into the
  very section documenting the previous five. Three rules were earned:
  - **An inert plant and a dead instrument give the identical green.** Commission the pass/fail
    channel per verifier, not per suite.
  - **Commissioning sensitivity is not commissioning specificity.** Planting a signal and
    confirming detection says nothing about whether noise, or a different artifact shape, is
    rejected. This one reached a shipping recommendation and was wrong by 30%.
  - **Commission deletion as well as reversal.** Deleting a finding is cheaper than stating it
    wrongly.
- **An unaudited green and an audited green look identical in a report** and are worth
  completely different amounts.
