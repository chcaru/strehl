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
| **Dust** | **2 real motes found; correction built, wired, tested, OFF by default** | fact 1856 |
| **Regional blur** | **`flowers-cpl` diagnosed: capture gap, not a merge defect** — (a) at all 6 sites | fact 1876 |
| **Depth softening** | root cause identified; candidate fix built but **unscored** | facts 1843–1845, 1849 |
| **GPU** | **unused** | explicit gap against the brief |
| **Pluggability** | **1 of 5 kinds, and it is refused on the shipping default.** Focus measures are a real trait seam, host-calibrated and *demonstrated* (7 operators, 10.27× noise-sd span; swapping moves 99.9105% of samples between two named hashes while the default stays byte-identical). Merge strategy is an enum in core; alignment model, optical profile and output stage have no trait. `--focus` is **refused** on `MergeBackend::Pyramid`, which is the default — so the plugin surface and the shipping path do not intersect. Registry is in-tree, so contributing still requires patching this repo | fact 1952; `docs/research/BUILD-PLUGIN.md` (`e1bf09e0`) |
| **Print gate** (blotch/chroma/band/clip/crush, all 33) | **0 FAIL.** 17 PASS · 3 ACQUITTED · 6 ACQUITTAL EXPIRED · 7 REVIEW · 0 NOT EXAMINED · 33 total (found 33). So **20 of 33 carry a standing clean verdict and 13 are unresolved** — expired and REVIEW are *not* passes, and the gate says so itself | `orch_printready.py` over `masters\` + `orch-rendered-7\`; facts 1947–1948 |
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
