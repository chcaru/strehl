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
| **Visual quality** | **24 of 26 masters clean to the eye at 1:1** | full-corpus survey, `orch_corpuseye.py`, every sheet viewed |
| **Halo** (shipping masters, 2–120 px) | **0 demonstrated on any subject** — but only 11 of 26 are actually *clean*; 4 blind + 7 unmeasurable remain UNSCORED, which is not the same as clean | facts 1851–1855, 1884 |
| **Rim** (shipping masters, ±12 px) | **13 FAIL — a disjoint scale the halo work never reached; unscored by a second lane** | fact 1881 |
| **Aura** (estimator vs pyramid) | estimator measures deeper in **17 of 17** conditioned readings; magnitude unknown | fact 1871 |
| **Chroma** | **1 visible defect, diagnosed, fix specified, not landed** | facts 1861–1863, 1865 |
| **Dust** | **2 real motes found; correction built, wired, tested, OFF by default** | fact 1856 |
| **Regional blur** | **`flowers-cpl` diagnosed: capture gap, not a merge defect** — (a) at all 6 sites | fact 1876 |
| **Depth softening** | root cause identified; candidate fix built but **unscored** | facts 1843–1845, 1849 |
| **GPU** | **unused** | explicit gap against the brief |
| **Print-ready** | **NO** — see §3 | |

`bee-1-cpl` (N=299) resolves individual ommatidia. `wrapped-text-1/2` resolve individual
toner particles and paper fibre. The ceiling of this pipeline is already high; the gap to
"print-worthy across the corpus" is a small number of specific, named defects, not a
general softness.

---

## 2. What was settled this session

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
   simply unreachable by default. **Two** knobs are now confirmed dead on their shipping path
   (this one and `--exposure`); the per-band gate floor is not a third — it changes the image,
   it just doesn't move the rim. Worse than inert, it is **unvalidated**: on the pyramid
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
8. **Measure the confidence exponent at depth on a qualified subject.** "Harmful at depth" was
   refuted, but is *not* replaced by "it is fine" — it is unmeasured. Use `bee-1-cpl`.
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
15. **A mid-scale ring axis is still live and unadjudicated, and must not be conflated with the
    tight-scale acquittal.** Three rim-like axes exist at **three disjoint scales**: `rimv6` at
    ±12 px (now acquitted), `halo_profile` at 2–120 px with a 400–900 px far field (four false
    positives, closed), and a separate axis in `docs/research/V-RIM-verification.md` using a
    **0–140 px ring window with a 170–300 px null**, which reports **RING on 5 of 14 measurable**
    subjects (`coffee-bean`, `lavendar-cpl`, `flower-bud-alone-cpl`, `bee-3-cpl`,
    `flower-bud-with-background-fern-cpl`). **Three of those five are also among the thirteen** —
    exactly the coincidence that invites a false retirement. Two bands remain unwalked by anyone:
    **9–120 px and 120–400 px**, and the second is the geometry where a halo's decay separates
    from ordinary scene lighting falloff, which is what produced `halo_profile`'s false
    positives. Fact 1901.
16. **The rim axis carries three defects of its own, none yet fixed.** (a) `rimaxis.py:52`
    `SEAL_DIR` points at `acceptance\SHIP-V4`, **not the deliverable** — genuinely different
    renders, ~99.7% of samples differing, max 22764 DN; re-pointing moves the tally to 9 PASS /
    12 FAIL / 5 REFUSED and swings `leaf-2-cpl` from +37.07% to +12.92%. (b) `rimaxis.py:57`
    `MIN_ISOLATED = 0.20` is **dead** — the name appears exactly once in the repo, at its own
    definition — so `wrapped-text-1` (16.2%) and `wrapped-text-2` (12.1%) were convicted in
    violation of the axis's own documented refusal rule. (c) `printcert4.rim_verdict` convicts on
    `corrected_bright` **only**, and a one-sided gate cannot measure ringing, which is symmetric;
    `flower-bud-alone-cpl` PASSES while reading `corrected_dark` +4.51%. Facts 1898–1899.

### 3.3 Open against the brief

11. **GPU is entirely unused.** Speed is already SOTA on CPU, so this is not blocking quality,
    but it is explicitly in the brief and remains unaddressed. A non-contending approach is a
    separate crate rather than edits to the held merge files.
12. **Plugin surface** — in progress, not finished.
13. **Colour management, photometric normalisation, outlier/robustness mask** — named in the
    research and unplanned. These are the unglamorous layer a SOTA claim dies without.

---

## 4. What the owner still owes, and what it would unlock

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
- **The seven new stacks delivered 2026-08-27** — `pottery-art-glazed-cpl`,
  `maldon-sea-salt-cpl`, `chia-seeds-cpl`, `medication-pill-cpl`, `duck-tape-side-layers-cpl`,
  `dime-flat-narrow-slices-cpl`, `unpopped-popcorn-kernels-cpl`, 1,292 frames total, at lower
  ISO and focus-step 1 / 5 / 7 against the previous max of 10 — are **not yet processed**.
  They matter more than their count suggests:
  - **Lower ISO should widen band qualification.** Only 2 of 26 current subjects qualify at
    0.30–0.35, which is the single biggest constraint on measuring sharpness at all.
  - **Thinner slices are the direct test of the selection premium.** Finer focus sampling puts
    more frames near peak, which is exactly the regime where selecting rather than estimating
    is measured to multiply noise 24–240×.
  - **Step 1 vs 5 vs 7 vs 10 on the same rig is a step-size ladder**, which is the experiment
    the capture advisor needs and which nobody has been able to run.

---

## 5. Landmines for whoever picks this up

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
  **unvalidated** — a value naming no kernel runs to completion. Two knobs are now confirmed dead
  on their shipping path (`STREHL_SOFT_GATE`, `--exposure`); the per-band gate floor is *not* a
  third — it changes the image, it just doesn't move the rim, which is a different repair.
  **Assume a knob is inert until a liveness control proves otherwise** — the cheapest form is a
  deliberate typo that must fail loudly, and the honest form is a pixel-difference count against
  a commissioned comparator. Facts 1869, 1873, 1880, 1882.
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
