# M113-spectral: does scene SPECTRUM explain the scene-dependence of lateral CA?

**Status: the scene-dependence is CONFIRMED and strengthened to n=8. The SPECTRAL
ATTRIBUTION is NOT SUPPORTED — the one falsifiable prediction it makes was tested
and came out with the WRONG SIGN.**

The claim under test is my own. Corpus fact 1570 / my fact 8 recorded that
`needed` — the red lateral-CA coefficient a scene requires — differs 23.6 %
between two stacks, and attributed that to scene spectrum: a channel's effective
wavelength is its passband centroid weighted by the scene's spectral radiance, so
a scene weighted toward longer wavelengths in red should need a larger red
correction. I was explicit at the time that the attribution was *argued*, not
measured. ORCH nonetheless rewrote the owner's #1 capture request around it.

Verdicts, each against a bar registered in
`experiments/M113-spectral/PRE-REGISTRATION.md` before any new render:

| question | verdict | n |
| --- | --- | --- |
| Does `needed` vary by scene at all? | **YES, robustly** | 8 |
| Is it aperture? | **REFUTED** | 8 |
| Is it the teleconverter? | **REFUTED** | 8 |
| Is it magnification / focus distance? | **REFUTED** | 8 |
| Is it subject radial-structure sampling? | **REFUTED** | 8 |
| Is it a common scale factor (align/merge)? | **REFUTED** | 8 |
| Is it alignment or the merge? | **REFUTED** | 9 |
| **Is it SPECTRUM?** | **NOT SUPPORTED — prediction failed its sign test** | 8 |

## The measurement

Every number is measured in the **binned linear camera-native space**, the only
space I established in `M113-ca.md` to be uncontaminated by the colour matrix and
the guided demosaic. Every stack carries the chain-transfer instrument check
(discipline 810): `applied / eps_r`, where `eps_r = -704.5e-6` is a compile-time
constant in `optics.rs`, so its recovery calibrates the whole chain end to end.

**All 8 pre-registered stacks passed S0** with transfer in [0.9064, 1.0004],
inside the registered [0.90, 1.02] band. Nothing was excluded.

| stack | focus m | frames | needed_R ppm | needed_B ppm | B/R | transfer |
| --- | --- | --- | --- | --- | --- | --- |
| tweezers-cpl | 0.2738 | 100 | 616.4 | -191.2 | -0.3102 | 0.9722 |
| leaf-2-cpl | 0.2771 | 182 | 674.7 | -210.4 | -0.3118 | 1.0004 |
| bee-1-cpl | 0.2841 | 299 | 536.2 | -219.0 | -0.4085 | 0.9100 |
| couch-fibers-cpl | 0.2841 | 299 | 654.9 | -158.7 | -0.2424 | 0.9813 |
| lavendar-cpl | 0.2841 | 299 | 580.6 | -207.4 | -0.3572 | 0.9486 |
| dry-erase-marker-head-cpl | 0.2841 | 299 | 542.1 | -201.3 | -0.3713 | 0.9064 |
| bee-2-cpl | 0.2917 | 299 | 549.4 | -208.4 | -0.3792 | 0.9512 |
| bee-3-cpl | 0.2917 | 299 | 529.9 | -208.7 | -0.3938 | 0.9399 |

Spread 529.9 to 674.7 ppm — **27.3 %**, against a measured repeatability floor of
**19.5 ppm** (S1: bee-2 against bee-3, same subject, same focus distance). The
effect is roughly seven times the noise. It is real.

## What EXIF killed before any pixel was measured

Rivals 1 and 3 died on metadata. **Aperture is f/5.6 on every `-cpl` stack** —
only coffee-bean and foam differ at f/8 and both are non-CPL anyway. **Every
stack reports `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter` at 200 mm.** There
is no aperture ladder and no teleconverter contrast anywhere in this corpus, so
neither can be the source of a between-stack difference.

## The crux: bee-1-cpl

Focus distance at the reference frame is *not* constant, and that builds a
natural experiment into the corpus. bee-1-cpl is the **same subject** as
bee-2/bee-3 but sits at the **same focus distance as couch-fibers-cpl**. The two
hypotheses therefore predict different numbers for it, 118.7 ppm apart, and one
render decides.

**bee-1-cpl reads 536.2 ppm — 3.5 ppm from the bee mean, 118.7 ppm from couch.**
It tracks its subject, not its magnification. **Magnification is refuted**, and
S3 confirms it independently: holding focus distance fixed at 0.2841 m across
four different subjects still leaves a 118.7 ppm range.

## The spectral hypothesis's own prediction, tested

S6 was registered in advance: Spearman rank correlation between `needed_R` and
scene R/G across all stacks passing S0, and **the physical argument requires the
correlation to be POSITIVE** — a redder scene needs a larger red correction.

**Measured: rho = -0.6905, p = 0.0580, n = 8. The sign is backwards.**

Scene R/G spans 0.9398 to 1.0400 (10.7 %) while `needed_R` spans 27.3 %, so the
colour range is real and the correlation is not merely noise-limited. The blue
channel gives nothing either: `needed_R` against B/G is rho = -0.1905, p = 0.65.

I registered this bar in advance as **weak evidence either way**, because a
three-channel ratio cannot see the spectral radiance *inside* a passband, and I
hold to that: this does not prove the mechanism is not spectral. But it is the
only direct test of the spectral prediction that existing data can support, and
it failed. **An argued attribution whose single testable consequence comes out
backwards has not earned a capture request.**

## The sign structure that DOES survive

`needed_R > 0` and `needed_B < 0` on all 8 stacks without exception: red is
under-magnified and blue over-magnified relative to green, a monotone spread with
wavelength. That is textbook lateral chromatic aberration and it is solid.

But S4 refutes a common scale factor as the source of the *variation*: if
alignment or magnification were scaling the whole image, eps_R and eps_B would be
multiplied by the same factor and `needed_B / needed_R` would be invariant.
**CV(B/R) = 14.9 % while `needed_R` varies 24.7 %**, so the two channels move
independently. Whatever varies between scenes is chromatic, not geometric.

## Alignment and the merge — my own outstanding Gap, now closed

S5 as first run appeared to fail catastrophically: a single un-aligned frame of
bee-3 read 192.0 ppm against the merge's 529.9, and couch 234.7 against 654.9,
suggesting the pipeline manufactured most of `needed_R`. **That reading was wrong
and the fault was in my test, not the pipeline.**

A single frame of a 299-frame macro bracket is in focus only in a narrow band.
The rest of the field passes the edge-energy floor but returns near-zero
displacement, and those windows dilute the global fit. Two controls establish it:

**Control A — blur the merge.** Gaussian blur of the all-in-focus merge does
*not* reproduce the deficit; `needed_R` goes 529.9, 535.8, 549.2, 551.3, 548.4,
559.1 ppm at sigma = 0, 0.5, 1, 1.5, 2, 3. Uniform low-pass slightly *raises* it.
So my first explanation — that blur attenuates the signal — is itself refuted.

**Control B — a flat subject.** `flat-on-ruler-cpl` is normal to the optical
axis, so one frame near best focus is sharp across the *whole* field and is
directly comparable to its own merge:

| arm | needed_R ppm |
| --- | --- |
| aligned merge | 631.7 |
| single frame, no align, no merge | 636.5 |

**Delta 4.8 ppm against a 60 ppm bar. Align and merge do not manufacture
`needed_R`.** Restricting the *bee* single frame to its sharpest quartile
recovers the same conclusion: 192.0 rises to 623.5 ppm, and couch 234.7 rises to
690.5 ppm. The deficit was dilution by defocused windows, exactly as predicted.

**A post-hoc rival, raised and then withdrawn.** Between those two results I
raised rival 6 — that lateral CA varies through the focus sweep, so the merge is
a depth-weighted mixture — because single frames across the sweep ranged 177.6
and 217.5 ppm, exceeding the between-subject spread. Control B kills it: on a
subject with no depth there is no mixture and no discrepancy.

## A post-hoc bar I had no right to trust, and why

S8 tried to remove the merge from every stack at once by measuring each on its
own reference frame, in-focus windows only. It reported the spread *growing* to
515.9 ppm and returned "spread survives". **I do not accept that result, because
I applied a new instrument without first measuring its repeatability.**

The bee triplet is a built-in replicate: the same subject, the same optics, three
captures. On the merged instrument they read 536.2 / 549.4 / 529.9 — a 19.5 ppm
floor. On the single-frame instrument they read **507.5 / 579.9 / 623.5 — a 116.0
ppm floor**, six times worse and comparable to the 144.8 ppm spread S8 was asked
to resolve. `lavendar-cpl` reads 174.5 ppm on that instrument, which is not a
measurement of anything. **S8 is UNDETERMINED by its own replicate control** and
neither its verdict nor its frame-count correlations are reported as findings.

The merged instrument remains the trustworthy one, and the merge is now
positively cleared by control B rather than merely assumed.

## Null controls

`optics.rs` carries `eps_b: None` — blue is a deliberate exact no-op, on the
stated principle that an unmeasured coefficient is *absent* rather than zero.
That hands the experiment a free perfect null: **`applied_B = +0.00 ppm` on all 8
stacks**, and the green and blue planes are byte-identical between the off and on
arms while red differs. The estimator has zero cross-channel leak and the
correction is red-only exactly as documented.

Every render arm used a **private `STREHL_CACHE_DIR`** (corpus fact 1561).

## An unrelated finding worth recording

**`STREHL_FIX_CA` is a silent no-op when `STREHL_ALIGN=0`.** The off and on
single-frame arms came out byte-identical on all three stacks initially tested.
The CA correction rides on the align/warp stage, so a caller who disables
alignment gets no correction and no warning. That is a foot-gun independent of
everything above.

## What the owner should shoot — the deliverable

**Do not send him out to shoot coloured gel sets as currently written**, and do
not replace them with an aperture ladder either: aperture is already constant
across the corpus at f/5.6, so a ladder would measure a variable that has been
*held fixed* rather than the one that varies.

The problem with the existing corpus is that **subject, colour, depth, material
and radial structure all covary** — every stack changes all of them at once. No
capture that varies subjects can separate them, which is why n=8 gets no further
than "scene-dependent".

The capture that settles it is **one fixed target, never moved, with a single
variable changed at a time**:

1. **A flat, achromatic, high-contrast target normal to the optical axis**, fixed
   on the rig and not touched between shots. Flat means the merge is a near
   no-op (control B: 4.8 ppm), so subject depth is removed by construction.
2. **Vary illumination spectrum only** — the gel set, but shot *within* that one
   fixed target rather than across different subjects. This is the direct
   spectral test, and it is the only design in which a difference can be
   attributed to wavelength. If `needed_R` does not move across gels on a fixed
   target, the spectral hypothesis is dead outright.
3. **Then vary the target's own colour** at fixed illumination, same geometry.
   Spectrum-of-the-scene and spectrum-of-the-light are different claims and this
   separates them.

That keeps the gels ORCH already asked for, but changes their purpose from a
between-subject comparison — which cannot work — to a within-target manipulation,
which can. Everything else about §24 should be dropped in favour of holding the
target still.

## Facts

1. `needed_R` varies **27.3 %** across 8 stacks (529.9 to 674.7 ppm) in the
   binned linear space, against a **19.5 ppm** replicate floor. Scene-dependence
   is confirmed at n=8, not n=2.
2. **All 8 stacks passed the chain-transfer instrument check**, 0.9064 to 1.0004.
3. **Aperture is f/5.6 and the optical path is `FE 100mm F2.8 Macro GM OSS + 2X
   Teleconverter` at 200 mm on every `-cpl` stack.** Rivals 1 and 3 are refuted
   on metadata alone; no aperture or converter contrast exists in this corpus.
4. **The bee-1-cpl crux refutes magnification**: 536.2 ppm, 3.5 ppm from the bee
   mean and 118.7 ppm from couch-fibers at the same focus distance.
5. **S6, the spectral hypothesis's own registered prediction, FAILED its sign
   test: rho = -0.6905, p = 0.0580, n = 8, where the physics required positive.**
6. **S4 refutes a common scale factor**: CV(needed_B/needed_R) = 14.9 % while
   `needed_R` varies 24.7 %.
7. **Align and merge do not manufacture `needed_R`**: on the flat subject
   `flat-on-ruler-cpl`, merge 631.7 against single un-aligned frame 636.5, delta
   **4.8 ppm** against a 60 ppm bar.
8. **The apparent S5 failure was window dilution, not a pipeline defect.**
   Restricting the bee-3 single frame to its sharpest quartile moves it from
   192.0 to 623.5 ppm; couch moves 234.7 to 690.5 ppm.
9. **Uniform blur does not attenuate this measurement**: 529.9 to 559.1 ppm over
   sigma 0 to 3. It slightly raises it.
10. **`applied_B = +0.00 ppm` on all 8 stacks**, with green and blue planes
    byte-identical between arms — `eps_b: None` is an exact no-op and the
    estimator has zero cross-channel leak.
11. **`STREHL_FIX_CA` is a silent no-op when `STREHL_ALIGN=0`.**
12. **The single-frame estimator has a 116.0 ppm repeatability floor** (bee
    triplet 507.5 / 579.9 / 623.5) against the merged instrument's 19.5 ppm, so
    it cannot resolve a 144.8 ppm between-subject spread. S8 is UNDETERMINED.
13. `strehl align` **refuses** `highly-angled-ruler-mm-cpl` on the ground that no
    single similarity describes a subject not normal to the optical axis. The
    refusal was respected rather than overridden with `--force-tilted`.

## Disciplines

1. **A new instrument must pass a replicate control before its readings are
   admitted as evidence.** S8 produced a clean, plausible, decisive-looking
   verdict from an instrument whose own repeatability was six times worse than
   the effect it was measuring. The replicate was available in the data the whole
   time and I ran the bar first.
2. **When a test of the pipeline fails, suspect the test before the pipeline —
   and find a subject for which the confound is absent by construction.** S5's
   apparent 64 % pipeline contribution dissolved against a flat target, where
   in-focus and merged are comparable by geometry rather than by argument.
3. **A between-subject comparison cannot test a single-variable hypothesis when
   every subject changes every variable at once.** The fix is not more subjects;
   it is one subject held fixed while one variable moves.
4. **Registering a bar as weak evidence in advance obliges you to honour it in
   both directions.** S6 came out backwards and I had pre-committed that this
   would not by itself refute the mechanism — so it does not, and the verdict is
   NOT SUPPORTED rather than REFUTED, even though the stronger word was available
   and would have made a better headline.

## Reader audit: the PIL 16-bit-RGB defect

ORCH's fleet notice: `PIL.Image.open()` silently returns `uint8` for a 16-bit RGB
TIFF. Audited by measurement, not by reading the source
(`experiments/M113-spectral/src/s9_pilaudit.py`).

The probe first reproduces the defect on a file of my own construction, so it is
known to be sensitive before it is trusted: source `uint16` 16116 levels,
`tifffile` exact, **PIL `uint8`, 256 levels, mode RGB**.

**M113-ca and M113-spectral are NOT affected.** Every number in both reports was
read through `cs.load_tiff_u16`, which does call `Image.open` — but only for the
**tags**. It asserts `bits == {16}` and `spp == 3`, verifies strip contiguity
rather than assuming it, and reads the pixels with
`np.memmap(path, dtype="<u2", ...)`. Measured against `tifffile` on five files
including both arms of bee-3-cpl: **byte-identical, `uint16`, every time**.

**M113-kernel-verify metrics are NOT affected** — `k2, k3, k5, k5b, k7, k8, k12,
k13, k14, k15, k16` all read via `tifffile.imread`.

**One real exposure: `k6_byeye.py` line 24** calls `KC.load()` from
`kernel_crops.py`, which is `Image.open` + `np.asarray`. Confirmed live on my own
render: PIL `uint8` max 159 where `tifffile` reads `uint16` max 40781. Those
arrays fed only the 1:1 PNG zoom crops, and were passed straight through
`KC.to8()`, so the destination was 8-bit regardless — but the ringing question is
a small-signal one, so it was re-run rather than argued
(`experiments/M113-kernel-verify/src/k17_bitaudit.py`):

| ROI | modulation ranking, 16-bit vs 8-bit | ringing-proxy ranking |
| --- | --- | --- |
| thorax hairs | `nn>l3>cr` / `nn>l3>cr` — SAME | flipped |
| hair tips vs background | `nn>l3>cr` / `nn>l3>cr` — SAME | flipped |
| leg + claw | `l3>nn>cr` / `l3>nn>cr` — SAME | flipped |

**Fact 1374's structural conclusion is reader-independent**: `nearest` out-resolves
`catmull-rom` on hair modulation in all three ROIs under both readers. The
ringing-proxy ordering does flip, but only because `cr` and `l3` sit within
0.03-1.3 % of each other on that crude proxy — an 8-bit read reorders a tie. The
ringing figure actually reported came from `k5`/`k5b`/`k12`, all `tifffile`.

**Two corrections to the triage list, both of which affect other agents.**

1. **`experiments/ORCH-drift-check/ca_radial.py` is a FALSE POSITIVE on the
   affected list.** Its `load_tiff_u16` is the *safe* pattern described above and
   was measured byte-identical to `tifffile`. This matters because it is the
   shared reader several milestones import; telling the fleet it is affected
   would cause correct work to be re-run, or a working reader to be "fixed".
2. **The list is incomplete for that directory.** Also reading pixels through
   `Image.open` + `np.asarray`: `patchwork16.py:66`, `patchwork_16bit.py:27`,
   `owner_sheets.py:28`, `patchwork_look.py:18`, `viewprep.py:26`. Of these
   `patchwork_16bit.py` is the worst case — a script *named* for 16 bits, which
   then computes `full = np.iinfo(a.dtype).max` and so normalises against **255
   instead of 65535** on top of already-quantised data.

The one-line guard that would have caught all of it is an assert on `dtype`
immediately after the load. `load_tiff_u16` effectively has one, in the form of
its `bits == {16}` tag check, which is why it survived.

## What the narrowing would have cost, measured by planting it

ORCH's triage questions are "is the statistic absolute?" and "does it divide a
small quantity by a large one?". For my estimator both answers are **yes**: `eps`
is fitted from `d = t + eps*(p - c)`, a sub-pixel displacement of order 0.1 px
over a radius of order 2000 px. That predicts maximal vulnerability, and a
compression toward a clean null would have read as "no difference between
scenes" -- silently reversing the headline finding rather than degrading it.

So the narrowing was planted rather than reasoned about
(`experiments/M113-spectral/src/s10_narrowctl.py`). **The prediction is refuted.**

| quantity | truth | narrowed | change |
| --- | --- | --- | --- |
| bee-3 `needed_R` | 529.9 | 527.9 | **-0.4 %** |
| couch `needed_R` | 654.9 | 655.6 | **+0.1 %** |
| bee-3 transfer | -0.9399 | -0.9354 | -0.5 % |
| **couch - bee-3** | **+125.0** | **+127.8** | **102.2 % retained** |

That is under a 118x narrowing (6522 to 55 distinct levels in a 256 px window).
**The triage rule, applied to my statistic, gives a false positive** -- it would
have sent me to re-run correct work, which is the same direction of error as the
`ca_radial.py` listing.

### Why, and where it does break

A displacement estimator is a **location** statistic, not a **dispersion** one.
Quantisation error is zero-mean and uncorrelated with sub-pixel position, and real
texture spans many steps and acts as dither, so averaging over ~600 windows of
256^2 px removes it. ORCH's destroyed quantities -- noise power, band SNR -- are
dispersion statistics, and quantisation variance adds to those *directly*.

A level ladder (`s11`) holds to **+2.1 % at step 8192 DN**, though `rms` degrades
from 0.0672 to 0.1882 px: bias survives, precision does not.

It does break, and the boundary is the level count spanned by the windows
actually fitted (`s13`, edge floor disabled):

| levels/window | `needed_R` | error |
| --- | --- | --- |
| 55 | 510.3 | +0.4 % |
| 12 | 518.3 | +2.0 % |
| 4 | 289.5 | **-43.0 %** |
| 2 | -288.4 | **-155.4 %, sign inverted** |
| 2 | -540.5 | **-202.7 %, sign inverted** |

**ORCH's nine-level case sits inside the failing regime**, and the failure is the
dangerous kind: at 4 levels it returns a confident, plausible, 43 % low number.

### The edge-energy floor is the defence

`grid()` admits a window only if mean gradient magnitude >= `MIN_EDGE_ENERGY =
60.0`. Re-running the low-contrast ladder at the shipped floor (`s14`):

| K | floor 0.0 | windows | shipped floor 60 | windows |
| --- | --- | --- | --- | --- |
| 20 | 289.5 (-45 %) | 693 | 440.8 (-17 %) | **144** |
| 60 | -288.4 (-154 %) | 693 | **no fit** | 5 |
| 150 | -540.5 (-202 %) | 693 | **no fit** | 16 |

All three cases where the unfloored estimator returned a confident wrong number
either refuse to fit or stay accurate under the shipped floor. **A support floor
converts a silent bias into a loud loss of support**, which is the behaviour an
instrument should have outside its range. The protection is graded, not absolute:
at K=20 it still returns a 17 % low value, but the window count collapsing from
605 to 144 is the visible warning.

### A control of mine that tested nothing

`s12` tried to establish this by lowering the floor on bee-3 and printed **NOT
CONFIRMED**. That output was wrong. At floors 5.0 and 0.0 the window count
saturated at **693, which is the entire grid** (21 x 33 positions at STEP=100), so
no smooth window was ever admitted and the control could not fire. The saturation
was visible in the window column from the first run. `s13` had to manufacture the
low-contrast condition instead of hoping to find it.

## Further facts

14. **A planted PIL narrowing moves `needed_R` by -0.4 % / +0.1 % and leaves the
    between-scene difference at 102.2 % of truth.** My statistic answers YES to
    both of ORCH's triage questions yet is essentially immune, so the rule as
    broadcast produces false positives.
15. **Location statistics are dithered by texture; dispersion statistics are
    not.** Bias holds to +2.1 % at step 8192 DN while `rms` degrades 2.8x.
16. **The immunity ends at roughly 12 distinct levels per fitted window**: -43 %
    at 4 levels and a full **sign inversion** at 2.
17. **The edge-energy floor is the defence.** It converts the silent -154 % case
    into a refusal to fit.
18. **A backtick inside a PowerShell DOUBLE-QUOTED string is an escape**, not
    only inside `@"..."@`. An anchor written as `"its `bits ..."` silently became
    a backspace byte plus `its ` and the guarded edit correctly refused.

## Further disciplines

5. **The triage question is not "absolute or ratio" but "value or position".**
   Ask whether the statistic reads the VALUE of pixels or the POSITION of
   features, and whether the samples actually fitted still span ~12 levels.
6. **A support floor is a defence against silent input corruption**, because an
   instrument that refuses to fit when its inputs degenerate cannot return a
   plausible wrong number.
7. **A control whose sampling saturates has not tested anything.** `s12` swept a
   threshold whose loosest setting already admitted every candidate window; the
   giveaway was a window count that stopped changing.
