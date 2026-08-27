import io
P = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW\AUDIT-user-surface.md"
T = """# Audit: where the user-facing surface diverges from the shipping binary

Read-only. Nothing was fixed. Source quotations come from the shipping pin
`9b05d0b7`, read through Python `subprocess` as bytes and verified by re-hashing
each extracted file to git's own blob id (400 checked, 0 mismatched). Behaviour
was measured against `acceptance-pins/9b05d0b7/target/release/strehl.exe`, sha
`44C2F2CD2E5B289491AB81C2...`, confirmed equal to the SHIP-V4 seal.

---

## 0. A correction I was asked to make, which the measurement refuses

I was told to strike `--exposure` from the findings, on the evidence that two
renders of subject `109MSDCF` at `+3` and `-3` stops produced different SHA-256
values. **I reproduced that experiment exactly -- same binary, same subject,
same flags -- and obtained the same two hashes, `D749F1FDCD07355F` and
`A5846DD2B0ACDC3A`. The pixels are bit-identical.**

```
np.array_equal(A, B) : True
samples              : 98898048
samples differing    : 0  (0.0000%)
mean DN  +3 / -3     : 47719.0880 / 47719.0880
commanded gain ratio : 8.000 / 0.125 = 64.000x
observed  mean ratio : 1.0000000
```

**The hash difference is one TIFF tag.** Enumerating every tag in both files,
the only one that differs is `ImageDescription` -- the banner text recording the
gain. The bytes move because the tool *writes down* the exposure, not because it
*applies* it.

This is the same unsound gauge I disclosed further down as my own instrument
defect: **file hashing cannot answer "did this flag change the image", because
metadata rides in the hash.** The correction and the original error share one
root cause.

**The finding stands and is now stronger.** See item 2.

---

## VERIFIED defects, ranked

### 1. The stale "default" is not a doc string. It is a runtime error message.

**File:** `crates/strehl-cli/src/merge_cmd.rs:420-429`, the `bail!` in
`MergeBackend::parse`, at pin `9b05d0b7`.

**Reaching the terminal verbatim:**

```
unknown merge backend "bogus"; valid values are `estimator` (the default,
the regularised-winner noise-gated merge) and `pyramid` (the Laplacian
multi-band merge)
```

**Actual:** `DEFAULT_MERGE_BACKEND = MergeBackend::Pyramid` (`merge_cmd.rs:406`).
All 26 shipped provenance files read `merge backend   : pyramid (default)`.

**Evidence:** run, not read -- `strehl stack <dir> --merge bogus`, rc=1.

**Severity: HIGHEST.** The string is printed at the exact moment the user is
already confused about `--merge`, and it tells them the wrong answer with
authority. `stack --help` is correct; the falsehood survives only on the error
path, which is why it outlived every review.

### 2. `--exposure` is accepted on exactly one path and does nothing there

**Log line:** `exposure        : +3.00 stops (gain 8.000x), as asked`

**Measured, subject `109MSDCF`, 22 frames, `--srgb`, pin binary:**

| commanded | 8 settings from -6 to +6 stops | +2.60 stops |
| --- | --- | --- |
| distinct images produced | 1 | 1 |
| mean DN | 47719.0880 | 47719.0845 |

**A commanded range of 4096x produces one bit-identical image.** Only `+2.60`
differs, by 0.0035 DN in the mean -- 7 parts in 100 million, and it is the one
value in the sweep whose gain (6.063x) is not a power of two. That is float
rounding residue in a cancellation that is otherwise exact, and it matches the
0.0753%-of-pixels residual I measured on a second subject at gain 0.927x.

**There is no other path to check.** The linear path refuses the flag outright:

```
Error: --exposure and --auto-exposure are viewing controls and need --srgb;
the default output is the linear measurement file and must not be rescaled
```

So the flag is **accepted on one path and inert on it**.

**Mechanism, from the shipped provenance itself.** The provenance describes the
exposure as "ONE multiply in linear light, before the curve" and then names the
tone rule as "linear-sRGB luma p99.9 -> 0.90 on the binned grid (M100)". A
percentile-anchored rule is scale-invariant, so it divides the multiply straight
back out. **The provenance contains both halves of its own cancellation.**

**Both commissioning arms passed on these exact files**, so the null is
readable: the renderer is deterministic (identical flags twice -> identical
pixels), and `--pyramid-exponent 4.0` moves 90.98% of samples.

**What this does and does not mean for the 26 masters.** They are **correctly
exposed**, and no self-accusation is warranted -- but the credit belongs to the
tone rule, not to the flag. The claim that the chosen gain "really did reach the
pixels" is refuted. Any gain yields the same master.

### 3. The README hands the user a command containing the inert flag

`DELIVER-V5/full-resolution/README.md:157` quotes a command line ending
`--srgb --auto-exposure`; line 163 says that flag is cancelled by the tone
stage. **Severity: MEDIUM** -- the document contradicts itself within one
screen, and the README's own account of the mechanism is confirmed correct by
item 2.

### 4. `STREHL_SOFT_GATE` panics instead of erroring

`crates/strehl-core/src/merge.rs:1403`. Values `1`, `4.0`, `on` each return
**rc=101** with `thread '<unnamed>' panicked at ...merge.rs:1403:23`, where
every other bad input returns rc=1 and a clean `Error:`. Not a false statement --
the variable is absent from `--help` and the README -- but a product that panics
on a typo reads as unfinished. **Severity: MEDIUM.**

### 5. One README quantitative claim carries no subject and no frame count

`README.md:366` -- `- **Noise: 4.5x better** than the single-frame input.`
Direction and comparator present, subject and frame count absent. Confirmed by
reading the full enclosing section. **Severity: LOW-MEDIUM.**

---

## Clean negatives

- **The `--auto-exposure` reproduce contract HOLDS.** `image_out.rs:617`
  promises that handing the printed number back to `--exposure` yields the same
  file. Measured: `--auto-exposure` and `--exposure=+2.60` are **byte-identical**,
  sha `18E6EDA98DEC9930`. **But the test is vacuous** -- it would pass on a
  completely dead flag, because nearly every exposure yields one image. It is
  satisfied, and it is not evidence the flag works.
- **All 28 `stack` flags A/B-tested on decoded pixels**; only `--exposure` is
  inert. `--stats`, `--target-n-eff`, `--confidence-tail` leave pixels untouched
  by design.
- **`--pyramid-exponent` is not a no-op.** My harness flagged it; a sweep showed
  2.0 is simply its default. Phantom avoided.
- **No environment variable is documented but dead.** All eight in `stack --help`
  are read by shipping code.
- **`STREHL_MERGE` works** -- log prints `estimator (STREHL_MERGE)`.
- **The README never advertises the soft gate**, so `softgate.rs` never having
  executed is not a false statement.

---

## SUSPECTED -- deliberately not promoted

- **`BUILD-SHARP.md:4666-4669`** (supplied to me as confirmed). Both citations
  exist: the document describes the merge as band-limited to plane Nyquist, and
  `align_cmd.rs` records "**On** by default since the flip." **I did not promote
  it, because the two citations name different stages** -- the align gather
  versus the merge plane geometry from `merge_cmd.rs:6302` -- and I have not
  established that flipping the first falsifies the second. Needs the owner of
  that file.
- **36 README ratio lines** flagged by a window heuristic as missing attribution.
  **I calibrated before reporting: three of four flagged lines were correctly
  attributed** in prose outside the window. Forwarding the raw set would have
  manufactured phantom violations. Only item 5 survives.

---

## The pattern behind three of these

`merge_cmd.rs:426` says `estimator` is the default; it is, of the estimator's
own era. `--exposure` was described to me as a no-op on a path that does not
ship; it is inert on the path that does. `BUILD-SHARP` describes a band limit
that is true of one stage while another was flipped.

**Every one is a true statement about the wrong path or the wrong stage, and
none is distinguishable from a lie without running the shipping binary.** Two
of the three were believed by the people closest to the code. The audit
therefore records, per item, *which path or stage the statement is true of* --
because "it is true of the estimator backend" is exactly how a wrong sentence
survives review.

---

## Defects in my own instruments

1. **A false acquittal of `--exposure`** from hashing whole files; metadata rides
   in the hash. Retracted, re-measured on pixels. The correction in section 0
   arrived on that same gauge, so the defect cost this audit twice.
2. **A false null from a broken search** -- `Select-String -Path 'crates\\**\\*.rs'`
   does not recurse. Its positive control caught it.
3. **A commissioning gate that fired on me** -- the pixel harness passed `--limit`
   twice; the run refused to proceed.
4. **Two false "no effect" env results** from baselines that had already inferred
   the estimator backend via `--photometric off`.
5. **A control render I read before checking its exit code**, which crashed the
   run rather than silently reporting a null against a missing file.

---

## Gaps

- **The cancelling line is still not isolated.** The mechanism is established
  (percentile-anchored tone rule) and now corroborated by the provenance text,
  but I did not point at the statement that divides the gain out.
- **`--fix-ca` remains untested** -- the profile name I passed was rejected.
- **Only the `stack` subcommand was swept**; `align`, `probe` and
  `argmax-baseline` were not.
- **The README was audited for internal consistency, not for whether its
  measurements are true.**
- **No test exists** asserting that a flag which claims to apply a gain applies
  one, which is why item 2 shipped and why it was reported to me as fixed.
"""
io.open(P,"w",encoding="utf-8",newline="\n").write(T)
print("wrote", P)
