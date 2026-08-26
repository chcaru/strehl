# V-chroma2: independent verification of BUILD-CHROMA `48d3acb` / `36075ed`

**HEADLINE — the §46 CA census is CORRECTLY SIGNED.** `GALLERY-FINAL` is the
CA-**off** arm and `SHIP-V1` is the CA-**on** arm, `cacensus.py` was invoked in
that order, and "25 improved, 0 worsened, 1 no-op" stands exactly as written.
Proven three independent ways, none of which reads a log line. The inverted
status line did **not** contaminate it, and could not have: `cacensus.py` parses
no status line, and both §46 arms were rendered by `strehl stack`, not by
`blend-render`.

Verifier: V-CHROMA2. Repo HEAD at time of writing `709b535`. Commits under
audit: `48d3acb` (item 1) and `36075ed` (items 2-3), parent `f643888`.
I wrote none of the code or analysis below. Nothing in `crates/` was modified.

| # | Claim | Verdict |
|---|---|---|
| 1 | status line inverted in `blend-render.rs` at `f643888` | **CONFIRMED** |
| 2 | the fix corrects the stdout | **CONFIRMED** |
| 3 | the fix is structural, not a second reconstruction | **CONFIRMED** |
| 4 | the 3 tests are commissioned (both inversion directions) | **CONFIRMED** |
| 5 | pixels byte-identical across the fix | **CONFIRMED** |
| 6 | split-half; green null on identical tiles | **CONFIRMED** |
| 7 | radial-field argument, `eps_b·r` = 0.368 px at corner | **CONFIRMED, with a units correction** |
| 8 | "it cancels in the differential" for `caprice.py` | **CONFIRMED — for a stronger reason than given** |
| 9 | "the corpus does not span aperture" | **REFUTED at corpus scale** |
| 10 | fairness of the 0.2%-vs-151 ppm comparison at n=1 | **CONFIRMED as a limitation** |
| 11 | how `cacensus.py`'s arms were produced and labelled | **CONFIRMED (no log line involved)** |
| 12 | is §46 correctly signed? | **CORRECTLY SIGNED** |
| 13 | sweep for other affected A/Bs | **CONFIRMED — none contaminated** |
| 14 | `restore.rs:573` abscissa is f = 0.40 | **CONFIRMED** |
| 15 | `MTF(φ+s) − MTF(φ)` ≡ 0 on uniform phase | **CONFIRMED** |
| 16 | is `0.69 × 0.6813 = 0.470` genuine convergence? | **NO — shared assumption** |

---

## 1-2, 5. The inversion is real, the fix corrects it, pixels do not move

I built `blend-render` from a clean `git archive f643888` tree (the parent of
`48d3acb`) and from `e42ab13`, and ran three arms on `coffee-bean --limit 2
--chunks 4`. **BUILD-CHROMA's hashes reproduce exactly.**

| arm | parent `f643888` prints | fixed prints | sha256[0:16] |
|---|---|---|---|
| `STREHL_FIX_CA` unset | `off (STREHL_FIX_CA unset)` | `CORRECTING, profile "a7c2-…" (gear matched "ILCE-7CM2" / lens 33094; default on)` | `13C89646A9655F42` |
| `STREHL_FIX_CA=off` | `CORRECTING, profile "off"` | `off (operator asked for "off")` | `3DBAED9940C3C235` |
| `STREHL_FIX_CA=a7c2-…` | `CORRECTING, profile "a7c2-…"` | `CORRECTING, … (operator asked for …)` | `13C89646A9655F42` |

BUILD-CHROMA reported `br_unset` = `br_unset2` = `13C89646…` and `br_off` =
`3DBAED99…`. My `p_unset`, `p_unset2` and `p_off` are `13C89646A9655F42`,
`13C89646A9655F42` and `3DBAED9940C3C235`. **Byte-for-byte agreement, from an
independently extracted tree.**

**I added a third arm BUILD-CHROMA did not run, and it is what makes the
direction certain rather than inferred.** An *explicitly named* profile cannot be
mislabelled — that row was always printed correctly. Its output is
`13C89646A9655F42`, **byte-identical to the arm the line labelled `off`**.
So the "off" arm is the correcting one and the `"CORRECTING, profile \"off\""`
arm is the uncorrected one. Both directions inverted, established by pixels.

**Item 5 — pixels are unchanged by the fix.** All three hashes are identical at
`f643888` and at `e42ab13`. The fix moved only reporting, and it holds across
every commit in between, not merely across `48d3acb` itself.

**Why the `=off` row matters more than the flip.** `profile_from_setting` maps
`off`/`false`/`0`/`""`/absent to `Ok(None)`. The old line's guard was
`Ok(k) if !k.is_empty() && k != "0"`, so `STREHL_FIX_CA=off` printed
`CORRECTING` while correcting nothing. That row was **wrong from the day the
line was written**, not merely since the default-on flip `96571ee`
(2026-08-26 02:45). Any A/B whose off-arm was spelled `off` rather than left
unset was mislabelled in its log for the whole life of the line. I verified this
on the `0d9fd28` binary (2026-08-25 18:10, hours before the flip): `=off` there
printed `CORRECTING, profile "off"` and produced pixels byte-identical to unset.

## 3. The fix is structural — CONFIRMED

`optics.rs:890-900` is a one-line projection, not a second derivation:

```rust
pub fn profile_for_capture(...) -> Result<Option<&'static OpticalProfile>, CaConfigError> {
    Ok(resolve_for_capture(setting, body_model, lens_type3)?.profile)
}
```

`Display for CaDecision` (`optics.rs:722-765`) takes the CORRECTING/off word from
`self.profile` — the same value the gather consumes — and never from the reason,
with an `INCONSISTENT (…)` catch-all on the structurally unreachable pairing.
The bug class is closed, not merely the instance.

**One residue I want on the record, not as a defect but as a live edge.** The
status line calls `resolve_for_capture_env` on the identity of `paths[0]`, while
the gather calls `profile_for_capture_env` per frame (`align_cmd.rs:1410`). Those
are two *calls*, not two *implementations*, so they cannot disagree in logic —
but they can disagree if frames in one stack carry different identities, or if
the environment changes mid-run. Unmeasured. BUILD-CHROMA also flags in its own
§23.6 that `merge_cmd.rs` retains a second `ca_status_line` implementation.

## 4. The commissioning — CONFIRMED, and my first attempt at it was wrong

I re-ran the commissioning in a **copy** of the tree, never in `crates/`, pinning
`optics.rs` to `$env:TEMP` and restoring from that copy with `os.utime(…, None)`
after each restore.

**My first run reported "0/3 caught, PLANT SURVIVED" on both plants — and that
was my instrument, not the tests.** `cargo test … -- --exact` with a bare test
name selected nothing: every line read
`test result: ok. 0 passed; 0 failed; … 452 filtered out`. **Zero passed is not
a pass.** I re-ran with a filter proven to select exactly one test and a hard
abort if `passed + failed == 0`:

| plant | tests RED |
|---|---|
| **A** — reinstate the second reconstruction (`Ok(profile_from_setting(setting)?)`), i.e. the historical bug class | 1/3 — `the_reported_profile_is_the_applied_profile` |
| **B** — invert the headline word on the operator-off row | 2/3 — `…_status_line_matches_the_decision_on_every_row`, `the_reported_profile_is_the_applied_profile` |

Every invocation reported `ran=1`. Restored file byte-identical to the pin
(`0C0F2FDCD27A7E7F`), all three green after restore. **2/2 inversion directions
caught. The suite is commissioned.**

## 6. The split-half — CONFIRMED, including the tile-identity property

I re-derived the fit from the stated model (`d = eps·u + T`, y and x sharing
`eps`, IRLS Tukey biweight c = 4.685) rather than importing `lateral.fit_model`,
and used **a different RNG seed** (777001, not their 20260826).

| stack | ch | eps ppm (theirs → mine) | noise ppm | \|eps\|/noise | `u` identical to G2's? |
|---|---|---|---|---|---|
| bee-2-cpl | R | 518.4 → **518.4** | 17.1 → 17.8 | 30.3 → 29.2 | **True** |
| bee-2-cpl | B | −144.2 → **−144.2** | 13.4 → 14.0 | 10.8 → 10.3 | **True** |
| bee-2-cpl | G2 | −30.0 → **−30.0** | 9.2 → 9.7 | 3.3 → 3.1 | **True** |
| bee-3-cpl | B | −174.8 → **−174.8** | 17.6 → 16.9 | 9.9 → 10.3 | **True** |
| coffee-bean | B | −182.8 → **−182.8** | 4.9 → 4.9 | 37.0 → **37.0** | **True** |
| couch-fibers-cpl | B | −94.3 → **−94.3** | 3.9 → 3.8 | 24.3 → 24.7 | **True** |
| lavendar-cpl | B | −148.9 → **−148.9** | 20.8 → 20.6 | 7.2 → **7.2** | **True** |
| tweezers-cpl | B | −169.1 → **−169.1** | 5.3 → 5.0 | 32.0 → 33.8 | **True** |

Every `eps` and every `n` reproduces **exactly**; noise floors differ only by
Monte-Carlo scatter, as they must on a different seed. Blue spans **7.2-37.0**
on my numbers as on theirs; the green null scores **1.2-5.6** against their
1.3-6.2.

**The null is on identical tiles, and this is measured rather than read.**
`np.array_equal(u_arm, u_G2)` is **True on all 13 rows**. Structurally this
follows from `c1_lateral.py:98-121`: the gate `S[pick[0], j] < gate` and the
focus ordering `argsort(-S)` are both computed from the arm-independent
structure array, and `u` is built from `field_position(…, "G1", …)` for every
arm. Only `d` differs. **That is what a null must do, and it does it.**

## 7. The radial-field argument — CONFIRMED, with a units correction

I wrote the Keys taps from the standard 1981 piecewise cubic with a = −1/2,
independently of `image_out.rs` and `c12_blue.py` (controls: taps at t=0 are
`[0,1,0,0]`; taps sum to 1.000000000000 at t=0.37; MTF(f=0) = 1.000000000000).

Sensor geometry: 3516×2344 per CFA plane, corner radius
`hypot(1758, 1172)` = **2112.85** plane px (`c12_blue.py` uses 2112.0, 0.04%
low — immaterial). With `eps_b = 174.4e-6`:

**`eps_b × 2112.85` = 0.368482 plane px. BUILD-CHROMA's 0.368 px is right.**

Its whole radial table reproduces exactly: shifts 0.0737 / 0.1473 / 0.2210 /
0.3683 px and amplitude losses 1.91% / 7.01% / 14.27% / 30.02% at field
fractions 0.2 / 0.4 / 0.6 / 1.0.

**The units correction.** ORCH's brief asked me to make sure the arithmetic used
energy and amplitude consistently. BUILD-CHROMA treated the 9.36% as *energy*
and solved `MTF = sqrt(1 − 0.0936) = 0.952050`, giving **0.1199 px** — which I
reproduce to four figures. But the 9.36% is **not** an energy.
`caprice.py:27-29` returns `rsig` = `1.4826 × MAD`, a robust **sigma**, and
`ORCH-veiling.md:3782` labels the pair verbatim:

> The obvious way to price the correction is HF **amplitude**: R -13.16%, B -9.36%.

On the amplitude reading the target is `1 − 0.0936 = 0.906400` and the
displacement is **0.1731 px = 0.470 of the corner shift**, not 0.1199 px =
0.325 of it.

**This does not damage the conclusion; it strengthens it.** The argument is that
the displacement which costs 9.36% lies inside the field rather than at the
0.039 px BUILD-SHARP priced. At r = 0.325 of the corner that is true; at
r = 0.470 it is more comfortably true. **The conclusion CONFIRMED, the specific
number 0.1199 px should read 0.1731 px.** (For the record, 9.36% *energy* would
be 4.79% amplitude — the conversion BUILD-CHROMA used is internally correct, it
is simply applied to a quantity that was already an amplitude.)

**A separate minor inconsistency, not a defect.** `optics.rs:386` says "the
**0.363** plane px of blue displacement the corner carries today" while the
report and `c12_blue.py` say 0.368. These are different quantities — 0.363 is
the *observed* corner displacement against which the 0.059 px leave-one-out
residual is an 84% reduction (0.363 × 0.16 = 0.058 ✓), whereas 0.368 is what the
shipped coefficient *applies*. Both readings are defensible and nothing turns on
the 1.4% gap, but the two numbers sit in the same paragraph of reasoning.

## 8. "It cancels in the differential" — CONFIRMED, for a stronger reason

`caprice.py:32-35` takes **two rendered TIFFs** and reads them with `tifffile`.
Both arms therefore pass through whatever writer produced them, and since
§36.1 states "one binary, one set of flags, one environment variable", the two
arms differ *only* in `STREHL_FIX_CA`. Any writer-side cost is common-mode.
So the claim is true.

**But the mechanism is not merely common — it is absent.** `image_out.rs:59-88`
is explicit that `write_binned` (which holds `COSITE_SHIFT`) is reachable by
exactly two invocations, `--linear-srgb` without `--demosaic` and
`--srgb --binned`, and that the gallery render "**never enters this function**".
`blend-render.rs:625` calls `image_out::write_demosaiced`, and its `write_frame`
doc says every line is copied from `merge_cmd::write_merged`'s `--demosaic`
branch. **`blend-render` never calls `write_binned`, so the 0.25-phase co-site
ran in neither of `caprice.py`'s arms.** The module header adds that on the
demosaiced path "that cost is not paid at all — Malvar-He-Cutler co-sites
inherently".

Consequently BUILD-CHROMA's rider — that the co-site "biases every blue-vs-green
HF comparison in the corpus — **including `caprice.py`'s**" — is **REFUTED**.
It biases the binned measurement renders; it does not touch `caprice.py`.
The 31.9% figure itself is arithmetically right: I get `keys_mtf(0.25, 0.35)` =
**0.8254** per axis and **0.6813** on both, to four figures.

## 9. The aperture census — REFUTED at corpus scale

BUILD-CHROMA's per-stack count is **exactly right for the six stacks it fitted**
(`bee-2-cpl`, `bee-3-cpl`, `coffee-bean`, `couch-fibers-cpl`, `lavendar-cpl`,
`tweezers-cpl`): five at f/5.6 and one at f/8 (`coffee-bean`). I confirmed all
six from EXIF independently.

**But it generalised six stacks to the corpus, and the corpus says otherwise.**
I read `FNumber` (0x829D) directly from the ARW IFDs across every folder in
`D:\personal\macro` (read-only; nothing written there). 27 directories, 26 with
frames — `flat-fields` holds none:

| aperture | subjects | which |
|---|---|---|
| f/5.6 | **20** | bee-1/2/3, couch-fibers, dry-erase-marker-head, flat-on-ruler, flower-bud-alone, flower-bud-with-background-fern, flower-inner-edge, flowers, highly-angled-ruler-mm, lavendar, lead-1, leaf-2, pencil-flatter-angle, pencil-steep-angle, tweezers, wrapped-text-1, wrapped-text-2, 119MSDCF |
| f/8 | **3** | coffee-bean, coffee-bubbles, foam |
| **f/11** | **3** | **109MSDCF, 112MSDCF, 113MSDCF** |

All 26 are `ILCE-7CM2` at 200 mm effective, single-aperture within each folder.

**"No f/11" is false. There are three f/11 subjects, carrying 22, 79 and 63
frames.** The corpus spans **two full stops**, f/5.6 through f/11. What is true
is that *the fit* did not use them: `optics.rs`'s `measured_at` string, "f/5.6
(5 stacks) and f/8 (1 stack) …; f/11 untested", is accurate about the fit and
should not be read as a statement about available data. The limitation is a
**choice of fitting set, not a property of the corpus** — which matters, because
it means the aperture question is answerable today without new shooting.

I am not disputing the *decision* not to gate on aperture; nothing I ran tests
that. I am refuting the stated ground for it.

## 10. n = 1 at f/8 — CONFIRMED as a limitation

The comparison "651.9 ppm (f/5.6) vs 650.7 ppm (f/8), 0.2%, against a
within-f/5.6 spread of 151 ppm" puts a **single** observation against a spread
estimated from five. A sample of one has no dispersion of its own, so the
0.2% gap has no error bar: it is one draw from an unmeasured f/8 distribution,
and the honest statement is that f/8 is *consistent with* f/5.6, not that it is
*indistinguishable* from it. With a within-group spread of 151 ppm, a single
f/8 point could sit 0.2% from the f/5.6 mean by chance with high probability
even if a real aperture dependence existed. The test as run has essentially no
power. Given item 9 — three f/8 folders and three f/11 folders exist — n could
be raised without new data.

## 11-13. THE CONTAMINATION SWEEP

### 11. `cacensus.py` reads no log line at all

It takes two directories, `dirA` and `dirB`, computes `E = sd_B / sd_A` on an
edge set chosen from the **arm mean**, and calls `E < 1` "improved". Arm identity
lives entirely in directory provenance and argument order. **There is no status
line in the instrument, so the inverted line cannot have entered it.**

The two directories are `C:\dev\strehl-out\GALLERY-FINAL` and
`C:\dev\strehl-out\SHIP-V1`. Their per-subject logs carry the banner
`strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; …)`, which is
`merge_cmd.rs`'s prologue — **not** `blend-render`'s
(`strehl BUILD-BLEND -- …`). §46 never went through the harness that lied.
GALLERY-FINAL was written 02:08-02:34, *before* the 02:45 flip, so even its
`lateral CA : off (…unset)` line was true when written.

### 12. Verdict: §46 IS CORRECTLY SIGNED

Three independent determinations, agreeing.

**(a) Direction probe.** `struct`, `flat%` and the placebo ratios in
`cacensus.py` are direction-dependent, so the published table itself encodes the
argument order. Computing them both ways, `A=GALLERY-FINAL, B=SHIP-V1`
reproduces **every** number §46.2 publishes — `foam` 0.034 / 9.38% / 0.8026 /
0.8261 / 0.9766; `113MSDCF` 0.052 / 10.03 / 0.8530 / 0.9341 / 0.9948;
`couch-fibers-cpl` 0.117 / 10.91 / 0.8983 / 0.9663 / 0.9961 — while the reverse
assignment gives 0.059 / 1.2460 and matches nothing.

**(b) Radial physics, using the project's own discriminator.** `strehl stack
--help` states that lateral CA "is zero on axis by construction" and that the
signature of correction is that "the RADIAL GROWTH is gone". On four subjects,
GALLERY-FINAL's edge R−G sd **rises 4.2× from centre to corner**
(`wrapped-text-1`: 0.0204 → 0.0855) while SHIP-V1's is nearly flat
(0.0208 → 0.0342). The B/A ratio is **1.021 on axis** and falls monotonically to
**0.400** at the corner. B−G shows the same shape, weaker
(1.0013 → 0.8583), consistent with `|eps_b|` = 174.4 ppm being 4.04× smaller
than `|eps_r|` = 704.5 ppm. **Only the arm with CA correction applied can be
flat in radius.** SHIP-V1 is that arm.

**(c) Ground-truth control.** I rendered `coffee-bubbles` twice from one pinned
binary with **explicit** `--fix-ca off` and `--fix-ca a7c2-fe100gm-2xtc-x4cpl`
— the flag path is not affected by the flip, so arm identity is known by
construction — and ran the same radial probe. The GALLERY-FINAL→SHIP-V1 pair
reproduces the known OFF→ON pair to 3-4 significant figures **at every radius**:
0.9738/0.9737, 0.8176/0.8172, 0.6799/0.6791, 0.6728/0.6722, 0.5557/0.5548,
0.4440/0.4436, 0.4199/0.4196. The reversed control runs 1.0269 → 2.3814, so the
discriminator is not degenerate.

**A cross-check on §46.1 that came free.** `mean|dG|` in the CA-only control
(0.001319 → 0.013818) matches the census pair (0.001326 → 0.013880), showing the
green movement is demosaic cross-talk from moved R/B rather than binary drift.

**And the census re-runs.** `cacensus.py GALLERY-FINAL SHIP-V1` over all 26
subjects reproduces §46.5 verbatim:

```
compared 26, skipped 0, total 26
edge R-G: improved 25, worsened 0, unchanged 1  (sums to 26)
MEDIAN   0.6533   0.7480   0.9452
```

with `highly-angled-ruler-mm-cpl` the 1.0000 no-op, and §46.4's deconfounded
median 0.6047 against raw 0.6320 over the same 19 rows, move −0.0273.

**§46 is correctly signed. CA correction improves 25 of 26 subjects and worsens
none.** This is also the direction V-CA found on separately-rendered arms and the
direction the gallery shows by eye; I tried to break it with (b) and (c) and
could not.

### 13. Nothing else is contaminated, but one guard is dead

Contamination requires that an arm label was *read from* the status line.
Setting `STREHL_FIX_CA` and labelling from that is ground truth and is what
almost every consumer does (`gallery.ps1:352-353` and `finalpass.ps1:227-238`
set it explicitly in **both** directions, the latter with a comment saying why).

Grepping `experiments/` and `scripts/` for parsers, **exactly two scripts
consume the line as evidence**: `ORCH-drift-check/clean.ps1:55-64` and
`clean6.ps1:67-76`, whose "confound guard: lateral CA must be OFF" counts logs
matching `lateral CA\s*:\s*off`.

**Both are clean, and I proved it behaviourally rather than by date.** They pin
`C:\dev\strehl-out\BUILD-BLEND\tree-lin-0d9fd28`. Running that exact binary
(sha256 `19786CC7FF01EBFF`):

| arm | line | sha256[0:16] |
|---|---|---|
| unset | `off (STREHL_FIX_CA unset)` | `521F541DAC22199C` |
| `=off` | `CORRECTING, profile "off"` | `521F541DAC22199C` |
| named | `CORRECTING, profile "a7c2-…"` | `2AB330240FB0F10F` |

**Unset and `=off` are byte-identical there** — the default-on flip had not
happened (`0d9fd28` is 2026-08-25 18:10, a strict ancestor of `96571ee` at
2026-08-26 02:45). All six archived `*-blend.log` files in
`ORCH-CLAMP\clean{,6}` record `lateral CA : off (STREHL_FIX_CA unset)`, and at
that binary **that was true**. Their merge-isolation results are unaffected.

**The defect I did find is that the guard cannot fire.** It tests
`lateral CA\s*:\s*on`, but the binary prints `lateral CA : CORRECTING`. I ran
both literals through the script's own two regexes:

```
CORRECTING line  matches ':on'=False ':off'=False -> bucket: no CA line at all
off line         matches ':on'=False ':off'=True  -> bucket: off
```

A confounded run is silently binned as "no CA line at all (legacy binary does
not print one)". **The `$on` counter is unreachable; this is an uncommissioned
negative control.** It happened to be reading true rows, so no result is wrong —
but it could not have caught the failure it exists to catch. Reported, not
fixed, per my brief.

**Everything else labelled from the line is in the always-correct row.** The
`V-BLEND/logs/*.log` files, `ORCH-veiling.md:2019` and §36.1 all quote
`CORRECTING, profile "a7c2-fe100gm-2xtc-x4cpl"` — the *named-profile* case,
which printed correctly at every commit (I confirmed at `f643888` and
`0d9fd28`). §36 additionally landed at `8b20264`, 2026-08-26 01:00, **before**
the flip, so its unset arm was genuinely off; and a corrected-vs-corrected null
could not have produced §36.2's 26% separation against a ≤0.6% placebo.

**Residual exposure, stated rather than closed.** Any A/B that spelled its
off-arm `STREHL_FIX_CA=off` *and* labelled from the log has a mislabelled log
line for the entire life of that code, not just since the flip. I found no such
A/B whose *conclusion* depends on it, but I did not re-run every experiment in
the corpus, and that is the gap I would look at next.

## 14. `restore.rs:573` records f = 0.40 — CONFIRMED

Line 573 reads verbatim:

```rust
for (f, want) in [(0.25, 0.9402), (0.40, 0.7425), (0.50, 0.6251)] {
```

My independent phase-averaged Keys MTF: **0.9402** at f=0.25, **0.8211** at
f=0.35, **0.7425** at f=0.40, 0.6250 at f=0.50. The middle constant belongs to
**f = 0.40**; at f = 0.35 the value is 0.8211, not 0.7425. **The brief's
"f = 0.35" is the mislabel and BUILD-CHROMA's correction is right.**

Note `restore.rs`'s module doc separately mentions "0.35 cycles/sample" for a
different quantity — where the Catmull-Rom/Lanczos3 ratio peaks — and 0.6251 as
the Nyquist value. Those are consistent; there is no error in `restore.rs`.

## 15. The amplitude-loss table is an upper bound — CONFIRMED

On a uniform phase distribution, `φ + s (mod 1)` is the same distribution, so
`E[MTF(φ+s)] − E[MTF(φ)]` is exactly zero. Measured over 200,000 phases at
f = 0.35, for s ∈ {0, 0.039, 0.1199, 0.1731, 0.25, 0.368, 0.5}: every difference
is **`+0.00e+00`**, against a base of 0.8211334499. Not "small" — identically
zero. BUILD-CHROMA and BUILD-SHARP §21 are right, and a table computed as
`MTF(s)` rather than `MTF(φ+s) − MTF(φ)` is an upper bound.

**With one qualification that BUILD-CHROMA already states and I want to keep
attached to the number.** BUILD-SHARP's measured mean distance-to-integer is
**0.2369** over 40,700 samples; exact uniformity gives **0.2500** (I verified).
0.2369 < 0.2500 means slightly *more* mass near integers than uniform, so a
shift moves phase away from integers on average and the true cost is a small
**positive** number, not zero. "Identically zero" is a statement about the
uniform idealisation. BUILD-CHROMA says exactly this — "the distribution is not
exactly uniform and the cost is not zero, but I did not measure the
distribution… an upper bound, not a prediction" — and that framing is correct.

## 16. `0.69 × 0.6813 = 0.470` is **not** independent convergence

I reproduce the arithmetic: `keys_mtf(0.25, 0.35)²` = **0.6813**, and
`0.69 × 0.6813` = **0.4701** against BUILD-SHARP's 0.47.

But this is an arithmetic consistency check, not two routes meeting. Both
derivations use the **same** Keys a = −1/2 kernel evaluated at the **same**
f = 0.35. More decisively, "R/B retention = green retention × co-site
retention" is the *definition* of composing two independent resamples in the
frequency domain — given 0.69 for green and 0.6813 for the co-site, 0.47 for R/B
is not a prediction that could have failed. Agreeing to three figures is
therefore evidence that neither party made a slip, which is worth something, but
it is **not** mutual corroboration of the physics and should not be cited as
two lanes agreeing. BUILD-CHROMA describes it as "an arithmetic cross-check from
a different direction", which is closer to right than "convergence"; I would
drop "different direction".

---

## What I could not verify

- **Whether the per-frame identity path can disagree with the prologue's
  `paths[0]` identity** (item 3 residue). No stack in the corpus is known to mix
  bodies or lenses, but I did not construct one to test it.
- **Whether any experiment outside `ORCH-drift-check` labelled an off-arm from a
  `STREHL_FIX_CA=off` log line.** I established the exposure window and swept the
  parsers; I did not re-run the corpus.
- **The aperture *decision*.** I refuted the stated ground ("no f/11") but ran no
  test of whether `eps_r` actually varies with aperture. Three f/11 subjects are
  available if anyone wants to settle it.
