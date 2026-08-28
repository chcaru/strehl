import io

DOC = r"""# PRE-REGISTRATION: independent scoring of the DELIVER-V6 re-render (CA / magenta)

**Written before `C:\dev\strehl-out\DELIVER-V6` existed on disk.** Verified at
authoring time: `DELIVER-V6 does not exist yet - I am ahead of the render`.
Nothing in this document was informed by a V6 image or by a word of DELIVER-V6's
report. That is the entire value of it, so it is committed before V6 lands.

Lane: V-REVIEW (independent eye). Subject: the first render carrying the re-fit
`eps_r = -508.4e-6` (`optics.rs:461`, now the shipping default).

---

## 0. What I will NOT do

- I will not read DELIVER-V6's numbers or conclusions until my own are written.
- I will not use `BUILD-CROP/cafit.py`, `carefit.py`, `chromashift.py` or any
  estimator from the lane that **fitted the coefficient under test**. Scoring a
  fit with the estimator that produced it checks the fit against itself. My
  estimator is written independently, and its disagreements with BUILD-CROP are
  a finding rather than an error.
- Out of scope by ORCH's instruction, not to be re-diagnosed: the two dust motes
  on every master; `flowers-cpl` (capture gap, not a merge defect); depth
  softening at some boundaries. Not mine: the rim axis (V-RIM), the env surface
  (V-ENVSURF), the halo residual (closed).

---

## 1. The primary endpoint, and why it is not a magenta counter

ORCH has already measured the trap: the statistic that scored `--fix-ca off` as
"1.82x better" **counts magenta specifically**, and CA-off's artifact is the
opposite-sign orange/cyan shape that counter cannot see. A one-sided statistic
scores a sign flip as a cure.

So the primary endpoint is a **signed radial displacement**, not a colour count.

For each qualifying edge site I measure the sub-pixel displacement of the R
channel relative to G, and of B relative to G, **projected onto the radial
direction from the optical centre** (outward positive), by cross-correlating the
edge-normal gradient profiles. Per subject I report the median over sites:

- `d_R` -- signed radial displacement of red, in sensels
- `d_B` -- signed radial displacement of blue, in sensels
- `|d_R|` -- the magnitude, which is the primary endpoint

`|d_R|` is **sign-symmetric by construction**: an error in either direction
raises it, so an over-correction cannot disguise itself as a fix. This is the
specific property the 1.82x statistic lacked.

### Secondary endpoint: sign agreement (the visible-magenta mechanism)

Magenta at an edge requires R and B to land on the **same side** of it. So I
report `agree` = the fraction of qualifying sites where `sign(d_R) == sign(d_B)`.
The documented failure of the superseded `+704.5 ppm` was that red "crosses past
neutral onto the same side as blue". If the re-fit works, `agree` must fall.

### Tertiary endpoint: both colour lobes, separately

Because the owner judges by eye, I also report the edge chroma excursion as
**two separate numbers** -- a magenta-lobe amplitude and a cyan/green-lobe
amplitude. Reporting them separately is what prevents the one-sided failure:
a fix that merely trades magenta for cyan shows as one falling while the other
rises, which a single "chroma" scalar would hide.

---

## 2. Pre-registered predictions

Stated now, so they can be wrong.

| # | prediction | endpoint | what refutes it |
|---|---|---|---|
| P1 | The re-fit reduces red's radial error | median `\|d_R\|` ratio new/old **< 1** on a majority of scored subjects | ratio >= 1 |
| P2 | Red stops sharing blue's side of the edge | `agree` falls vs old | `agree` does not fall |
| P3 | Blue is unchanged (it was not re-fitted) | `\|d_B\|` ratio ~ 1 | `\|d_B\|` moves materially -- would indicate a global geometry change, not a CA fix, and would CONFOUND P1 |
| P4 | `highly-angled-ruler-mm-cpl` is the subject most at risk | it may be the only ratio > 1 | it improves like the rest |

**P3 is the internal control and it is load-bearing.** Blue was not re-fitted,
so blue should not move. If `|d_B|` moves as much as `|d_R|`, then something
global changed between builds and my red result is confounded rather than
causal. This is the same logic `optics.rs:44-49` used to refute +704.5 ppm.

---

## 3. `highly-angled-ruler-mm-cpl` is the control subject

It is the one subject showing the lens's **natural opposite-sign** pattern
rather than over-correction. A coefficient fitted to cure over-correction can
plausibly push it further from neutral. It is scored by the identical pipeline,
reported on its own row, and **a degradation there is a headline, not a
footnote**: "improves 25, wrecks 1" is a different product decision from
"improves 26", and it is not mine to make -- I report it to ORCH.

---

## 4. Site selection, with an absolute floor

A search that cannot fail is not a search. A top-N site picker returns
background on a low-texture subject and manufactures a verdict; that defect has
already produced two false CONVICTs on this project. Therefore a site qualifies
only if it passes **absolute** floors, not a ranking:

1. edge gradient magnitude above a fixed floor (stated in DN in the report);
2. radius from the optical centre above a floor -- **lateral CA vanishes at the
   centre**, so a near-centre site measures noise and must not vote;
3. the edge is locally straight, so the normal direction is well defined;
4. a minimum count of qualifying sites per subject.

A subject that fails (4) is reported **UNSCORED**, never clean. Skips and passes
will be separately counted in every summary, and the counts will sum to 26.

---

## 5. Sampling and registration

- **1:1, native resolution, no scaling.** An integer-zoom viewer manufactures
  block structure that is not in the data; this project has already been misled
  by exactly that, and ORCH was misled by it again tonight.
- Old and new masters are compared at **fixed coordinates**. Where a window must
  be registered onto a feature, the shift is **integer-only** -- sub-pixel
  resampling adds blur to the very quantity being measured.
- TIFFs are read with `tifffile.imread`, never PIL, which misreads this tool's
  output.

---

## 6. Commissioning, to be run and reported BEFORE any V6 score

The instrument is not trusted until it passes all five arms on the OLD masters,
which exist now. **A detection floor in ppm and in sensels will be stated.**

| arm | mutation | required outcome |
|---|---|---|
| NULL | a master against itself | `d = 0`, ratio exactly `1.000` |
| POSITIVE | plant a radial R rescale of a known `+X ppm` | recovers `+X` within tolerance |
| SIGN | plant `-X ppm` | recovers `-X` -- proves sign symmetry, the property the 1.82x counter lacked |
| BLUR-ONLY | blur all channels equally, no CA | statistic does **not** move materially -- this is what separates a CA finding from the build-difference confound |
| FLOOR | descending planted amplitudes | the smallest reliably recovered displacement, stated |

If the BLUR-ONLY arm moves the statistic, I cannot separate CA from the build
change and I will say the comparison is confounded rather than report a number.

---

## 7. Confounds I am declaring in advance

The old and new masters come from **different builds**. That is unavoidable --
the code changing is the point -- but it means:

- Any difference I find that is **not** attributable to CA is **CONFOUNDED** and
  will be labelled as such, not reported as a finding.
- Image dimensions and optical centre will be compared first. If geometry moved,
  everything downstream is confounded and I will report that instead of a score.
- The channel-**differential** design is the mitigation: `d_R` is a displacement
  between two channels of the *same* image, so it is largely insensitive to
  global tone, exposure and sharpness differences between builds. That is why it
  is the primary endpoint rather than any absolute per-channel measure.

---

## 8. How conclusions will be quoted

Per fact 1886: **orderings and ratios, never absolute thresholds** -- absolutes
in this corpus are timestamps. So the verdict is per-subject `new/old` ratios
and their direction, with the spread printed alongside. **I will not compare two
numbers closer together than the spread I printed.**

Final partition, counted, summing to 26:

| category | meaning |
|---|---|
| IMPROVED | `\|d_R\|` ratio < 1 by more than the printed spread |
| UNCHANGED | ratio brackets 1 within the spread |
| WORSE | ratio > 1 by more than the printed spread |
| UNSCORED | too few qualifying sites; per-subject reason |

A **new** defect the old masters did not have is a stop-and-report finding and
goes to ORCH immediately, ahead of the full report -- as does the magenta
verdict itself.
"""

p = "PREREG-v6ca.md"
with io.open(p, "w", encoding="utf-8", newline="\n") as f:
    f.write(DOC)
print("wrote", p, len(DOC), "chars")
