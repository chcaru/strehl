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

## 4. What the owner still owes, and what it would unlock

### 4.0 Two physical captures the owner can make, in priority order

Both are cheap, both are blocking, and neither can be produced by any agent. They are listed
first because they are the only items on this list that no amount of autonomous work can clear.

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

**2. A ColorChecker capture, to unblock the colour axis (M7).** Required: a tilted ColorChecker
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
