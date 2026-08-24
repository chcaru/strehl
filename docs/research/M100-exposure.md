# M100 — Exposure control on the viewing path

**Status: pre-registration. Nothing below §2 has been measured yet.**
This section is committed *before* any measurement, so that the bars cannot be
moved to fit the answer. Git is the witness: if a bar in a later commit differs
from a bar in this one, the diff says so.

## 1. Pre-registered falsification bars

The problem, as MEASURED by the orchestrator and taken here as given:
`strehl stack --srgb --demosaic` on `D:\personal\macro\bee-3-cpl` puts the white
background at **0.5734** in sRGB with luma p99.9 at **0.5947** and **0.000000%**
of pixels at either clipping limit. The RAW background green photosites sit at
**0.296** of `(raw-black)/(white-black)`, which sRGB-encodes to 0.5752 — so
strehl is faithful and the *capture* is ~1.76 stops under-exposed. `--srgb` is
documented as the mode "for something to LOOK AT", and a viewing render that
discards 0.75 stops of output headroom is not fit for that purpose.

I am adding `--exposure <STOPS>` and `--auto-exposure` to the **viewing** path.
These are the bars. Each one is a *falsification* bar: failing it kills or
changes the feature, it does not get explained away.

### B1 — Byte-freeze (hard, non-negotiable)
The default output — `strehl stack --out X` with no `--srgb`, no `--demosaic`,
no exposure flag — must be **SHA-256 identical** before and after this change.
Every number in this project's corpus was measured on that file.
**Fail ⇒ the change is reverted, not patched.**

### B2 — Round-trip identity
`--srgb --exposure 0` must be **SHA-256 identical** to `--srgb` alone, on the
binned path and on the demosaiced path. This catches the entire class of
accidental-rescale bug where a "no-op" gain is not a no-op.
**Fail ⇒ the change is reverted.**

### B3 — Clipping ceiling
For the auto rule as finally shipped, measured on **at least five** stacks under
`D:\personal\macro`:

* fraction of output pixels with **any** channel at 65535 ≤ **0.50%** on every
  stack;
* fraction with **all three** channels at 65535 (genuinely blown white) ≤
  **0.20%** on every stack.

**Fail on any stack ⇒ the rule's parameters are rejected and re-chosen, and the
failure is reported with its numbers.** A rule tuned on one scene is not a rule.

### B4 — Effectiveness
The feature must actually solve the stated product problem. On every stack
tested, the encoded luma p99.9 of the auto-exposed render must be ≥ **0.90**
(today's bee-3-cpl figure is 0.5947).
**Fail ⇒ the rule is too timid and its target is re-chosen.**

### B5 — Planted-gain recovery (negative control)
Scale a linear image by a known 2^k for k ∈ {−1, −0.5, +0.5, +1}. The chosen
exposure must move by **−k to within 0.001 stops**, and the developed output
must be invariant to within **1 LSB of 65535** per channel. A rule that cannot
recover a planted gain cannot be trusted to find a real one.
**Fail ⇒ the rule is not a gain estimator and does not ship.**

### B6 — Reproducibility of the automatic choice
`--srgb --auto-exposure` prints the stops it chose. Re-rendering with
`--srgb --exposure <that number as printed>` must produce a **SHA-256 identical**
file. If the printed number does not reproduce the image, the print is
decoration.
**Fail ⇒ either the print precision or the gain path is wrong; fix, do not
document around it.**

### B7 — Refusal
`--exposure` or `--auto-exposure` without `--srgb` must **exit non-zero with a
message naming `--srgb`**. Silently ignoring a flag is worse than not having it,
because the linear output is the measurement output and a user who thinks they
brightened it has a corrupted measurement.
**Fail ⇒ blocking defect.**

### B8 — Clean crate
`cargo test -p strehl-core color::` passes and
`cargo clippy -p strehl-core --lib -- -D warnings` exits 0.

### What would make me abandon the feature
If no (percentile, target) pair clears B3 and B4 simultaneously on all five
stacks, then no single scalar gain is a defensible automatic choice for this
corpus, and the honest outcome is to ship `--exposure` alone and report
`--auto-exposure` as a negative result.

## 2. Method

*(written after §1 was committed)*

## 3. Results

*(written after §2)*

## 4. Verbatim patches for files M100 may not edit

*(written after §3)*
