# Audit: where the user-facing surface diverges from the shipping binary

Read-only. Nothing was fixed. Every source quotation is from the shipping pin
`9b05d0b7`, extracted through Python `subprocess` as bytes and **verified by
re-hashing each extracted file to git's own blob id (400 checked, 0
mismatched)**, so the redirect-corruption trap is not merely avoided but proved
avoided. Every behavioural claim was run against
`acceptance-pins/9b05d0b7/target/release/strehl.exe`, sha
`44C2F2CD2E5B2894...F490`, confirmed equal to the SHIP-V4 seal.

Subject for all renders: `coffee-bubbles`, 19 frames available, `--limit 3`.

---

## VERIFIED defects, ranked

### 1. The stale "default" is not a doc string. It is a runtime error message.

**File:** `crates/strehl-cli/src/merge_cmd.rs:420-429` (the `bail!` inside
`MergeBackend::parse`), at pin `9b05d0b7`.

**Claim as written, reaching the terminal verbatim:**

```
Error: reading --merge "bogus"
Caused by:
    unknown merge backend "bogus"; valid values are `estimator` (the default,
    the regularised-winner noise-gated merge) and `pyramid` (the Laplacian
    multi-band merge)
```

**What the binary does:** `DEFAULT_MERGE_BACKEND = MergeBackend::Pyramid`
(`merge_cmd.rs:406`). All 26 shipped provenance files read
`merge backend   : pyramid (default)` (MEASURED: 26 files name a backend, all
26 identical).

**Evidence:** run, not read. `strehl stack <dir> --merge bogus` returns rc=1 and
prints the text above.

**Severity: HIGHEST of anything found.** This is worse than the brief describes.
A doc comment is read by someone browsing; **this string is printed at the exact
moment a user is already confused about `--merge`**, and it tells them the wrong
answer with authority. It is the only place in the shipping surface that still
asserts it. A reviewer would reach it inside five minutes by typing one wrong
flag value, and would conclude the tool does not know its own default.

**Mitigating, and it matters for triage:** `stack --help` is **correct** --
it says `pyramid (DEFAULT)` and "`pyramid` (the default)". The falsehood lives
only on the error path.

### 2. `--exposure` changes no pixel, while the log says it was applied

**File:** gain resolved correctly at `strehl-core/src/color.rs:682`; consumed at
`merge_cmd.rs:6550` and `merge_cmd.rs:6671`.

**Claim as written:** `exposure        : +2.00 stops (gain 4.000x), as asked`.

**What the binary does:** nothing to the image. MEASURED, `--srgb`,
`np.array_equal` on the decoded arrays:

| commanded | gain | pixels differing | mean DN |
| --- | --- | --- | --- |
| baseline | 1.000x | -- | 4142.3638 |
| `--exposure -2.0` | 0.250x | 0 | 4142.3638 |
| `--exposure 2.0` | 4.000x | 0 | 4142.3638 |
| `--auto-exposure` | 0.927x | 74,463 (0.0753%) | 4142.3634 |

A 16x span of commanded gain moves **zero pixels**, which rules out "the gain
was too small to see". `--auto-exposure` is **not inert but nearly so**: it
moves 0.0753% of pixels, and a real 0.927x gain would move essentially all of
them and drop the mean by 7.3%; the mean moved by one part in ten million.

**Mechanism, partially localised.** The gain reaches
`Render::with_saturation` (`color.rs:288`), where it sets **only the highlight
ceiling**, and `clip_highlights` is documented as "the identity, bit for bit"
below the knee (`color.rs:362`). That predicts exactly what was measured: a
handful of near-highlight pixels move and nothing else does. **I did not isolate
the line that cancels the normalisation multiply**, so the fix owner still has
that to find.

**Severity: HIGH, but already known and already disclosed.** The shipping README
states it at line 163 -- "`--exposure` and `--auto-exposure` are **cancelled by
the tone stage**" -- and line 745 tracks it as settled. This audit is
independent confirmation on a different gauge, plus the quantified
`--auto-exposure` residual, which I did not find stated anywhere.

### 3. The README hands the user a command line containing the broken flag

**File:** `DELIVER-V5/full-resolution/README.md:157`

```
strehl stack "D:\personal\macro\<subject>" --out <out>.tiff --srgb --auto-exposure
```

Six lines later the same document says that flag is cancelled by the tone stage.
Line 191 explains the 26 delivered images are unaffected, so this is an
inconsistency in the instructions rather than in the corpus.

**Severity: MEDIUM.** A reviewer who copies the quoted command and then reads on
finds the document contradicting itself within one screen.

### 4. `STREHL_SOFT_GATE` panics instead of erroring

**File:** `crates/strehl-core/src/merge.rs:1403`

MEASURED: values `1`, `4.0` and `on` each return **rc=101** with
`thread '<unnamed>' panicked at crates\strehl-core\src\merge.rs:1403:23`.
The message itself is good and names the valid kernels, but it arrives as a
**panic with a thread name and a source path**, where every other bad input in
this tool returns rc=1 and a clean `Error:`.

**Severity: MEDIUM.** A shipping product that panics on a typo reads as
unfinished. Not a false statement: the variable is absent from `--help` and the
README mentions no soft gate at all.

### 5. One README quantitative claim carries no subject and no frame count

**File:** `README.md:366` -- `- **Noise: 4.5x better** than the single-frame input.`

Direction and comparator are present; **subject and frame count are absent**,
and both are required by house rule. Confirmed by reading the full enclosing
section, not by a window heuristic.

**Severity: LOW-MEDIUM**, and it is the one I am confident in -- see the
suspected section for why I am not forwarding the rest.

---

## Clean negatives: things checked that are NOT defects

Stated so the absence is on the record rather than assumed.

- **Every one of the 28 `stack` flags was A/B-tested on decoded pixels.** Only
  `--exposure` is a no-op. `--stats`, `--target-n-eff` and `--confidence-tail`
  also leave pixels untouched, which is **correct** -- they are diagnostics.
- **`--pyramid-exponent` is NOT a no-op.** My first pass flagged it. A sweep
  showed `0.5`, `1.0`, `4.0`, `8.0` and `64.0` all change the image and only
  `2.0` does not, because **2.0 is its default**. Reporting it would have been a
  phantom.
- **No environment variable is documented but dead.** All eight named in
  `stack --help` are read by shipping code. The reverse gap is large -- 31 are
  read but undocumented -- which is under-documentation, not false statement.
- **`STREHL_MERGE` works.** The log prints
  `merge backend   : estimator (STREHL_MERGE)`. My first test said "no effect"
  and was wrong: its baseline passed `--photometric off`, which *infers* the
  estimator, so both arms were already the estimator.
- **The 26 provenance files agree with the constant** and record every
  `STREHL_*` variable with its built-in default.
- **The README does not present the soft gate as a working feature** -- zero
  mentions -- so `STREHL_SOFT_GATE` never having run on the shipped corpus is
  not a false statement.

---

## SUSPECTED, and deliberately not forwarded as findings

A window heuristic flagged 36 README ratio lines as missing a comparator,
subject or frame count. **I calibrated it before reporting and it is mostly
wrong**: of four flagged lines read in full context, **three were correctly
attributed** and only line 366 was a real gap. The attributions live in the
surrounding prose, outside a two-line window.

Forwarding the raw 36 would have manufactured phantom violations, which is the
failure this project has been bitten by before. **The house-rule sweep needs a
section-scoped reader, not a line-scoped one**, and until it has one the only
README item I stand behind is item 5.

---

## Defects in my own instruments, disclosed

Four, and two of them produced wrong answers I had to retract.

1. **A false null from a broken search.** `Select-String -Path 'crates\**\*.rs'`
   does not recurse. It reported no denoise function and only one `STREHL_*`
   variable. **Its positive control caught it** -- a search for a function known
   to exist returned zero. Re-run under ripgrep the control returns eleven.
2. **A false ACQUITTAL of `--exposure`.** My first differential hashed whole
   output files. TIFF metadata rides in that hash, so a flag that records itself
   in the header while never touching the image read as "changes output
   (works)". I published that verdict to myself and had to withdraw it. The tell
   was that the **mean DN was identical to six figures** on files whose hashes
   differed. **File hashing is the wrong gauge for "does this flag change the
   image."** Everything above is re-measured on decoded pixel arrays.
3. **A commissioning gate that fired on me.** The pixel harness passed `--limit`
   twice; the potency arm failed and the run refused to proceed rather than
   reporting a table built on a broken baseline.
4. **Two false "no effect" env results** caused by baselines that had already
   inferred the estimator backend, retracted above.

---

## Gaps: what remains unverified

- **The exact line that cancels the exposure multiply is not isolated.** The
  ceiling path explains the `--auto-exposure` residual; it does not by itself
  explain why the normalisation multiply at `merge_cmd.rs:6550` has no effect.
- **Flags were tested on one subject at three frames.** A flag that acts only on
  deep stacks, or only on a subject with different content, would read as
  working here. `--fix-ca` was **not** tested: the profile name I passed was
  rejected and I did not retry with a valid one.
- **Only the `stack` subcommand was swept.** `align`, `probe` and
  `argmax-baseline` were not flag-audited.
- **The README was audited for internal consistency and house rules, not for
  whether its measurements are true.** Its numbers are other lanes' work.
- **No test exists for any of this.** There is no test asserting that a flag
  which claims to apply a gain applies one, which is why item 2 shipped.
