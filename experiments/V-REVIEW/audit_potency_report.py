import io
P = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW\AUDIT-potency.md"
T = """# Potency audit: does each user-facing control do anything?

Companion to `AUDIT-user-surface.md`. Two questions: whether the exposure fix
`9cb7f5d9` reaches the shipping path, and whether every CLI flag is potent.

**Gauge.** Decoded pixel arrays (`tifffile`), never file hashes. **Both
commissioning arms passed on the exact files used**: the renderer is
deterministic (identical flags twice produce identical pixels), and a
known-potent control moves a large fraction of samples. A null measured without
those arms is unreadable and is not reported as one.

**Binaries.** Working tree HEAD `a6d36f61` built to an isolated target dir, and
the shipping pin `9b05d0b7` (sha `44C2F2CD2E5B289491AB81C2...`). Subject
`109MSDCF`, 22 frames available.

---

## Part 1 -- the exposure fix does not reach the shipping path

`9cb7f5d9` is real work and its test is a good test. **It does not change what
the user gets.**

Measured on the **fixed** binary, `--srgb`, `109MSDCF --limit 4`, regression of
each render against the `--exposure 0` render:

| commanded stops | commanded gain | delivered slope | samples moved |
| --- | --- | --- | --- |
| -6 | 0.0156 | 1.000000 | 0.000% |
| -3 | 0.1250 | 1.000000 | 0.000% |
| -1 | 0.5000 | 1.000000 | 0.000% |
| 1 | 2.0000 | 1.000000 | 0.000% |
| 2 | 4.0000 | 1.000000 | 0.000% |
| 2.60 | 6.0629 | 1.000000 | 0.428% |
| 3 | 8.0000 | 1.000000 | 0.000% |
| 6 | 64.0000 | 1.000000 | 0.000% |

**Eight settings spanning 4096x produce one bit-identical image**, exactly as on
the unfixed pin. The `2.60` row is the only non-power-of-two gain and moves the
mean by 0.0030 DN -- float rounding, not exposure.

### Why: the fix was applied to a writer the default render does not use

`with_exposure_gain` is called at **`stack.rs:1737` and `stack.rs:1763`, and
nowhere else in the workspace**. There are **zero calls in `merge_cmd.rs`**,
which holds the writers the default pyramid render goes through
(`merge_cmd.rs:6551`, `:6672`). `9cb7f5d9` touched `image_out.rs` and
`stack.rs` only. So `Develop::exposure_gain` keeps its default of `1.0` on the
shipping path and `image_out.rs:1258` multiplies by one.

### Why its test passes anyway

The test is better than most: it commissions its slope estimator against planted
`2.0`, `0.5` and `1.0` arms, filters clipped samples, enforces a floor so
"nothing was examined" fails instead of reading green, and carries a bit-exact
null arm. Its docstring even names the hash defect that hid the bug.

**But it calls `develop_pixel` directly with `srgb: false, contrast: 0.0`**, and
that configuration is **unreachable from the CLI**, which refuses the flag
without `--srgb`:

```
Error: --exposure and --auto-exposure are viewing controls and need --srgb;
the default output is the linear measurement file and must not be rescaled
```

So the test proves the arithmetic is right in a configuration the user cannot
ask for, while the configuration the user is *required* to ask for goes through
an unfixed writer. **Verdict: real bug, real fix, fix not on the shipping
path.** The test is not weak; it is aimed at the wrong path.

---

## Part 2 -- potency sweep of the CLI surface

Each flag rendered against a baseline on the **same explicitly named backend**,
so backend inference cannot shift the comparison.

| flag | backend | samples moved | verdict |
| --- | --- | --- | --- |
| `--pyramid-gate 8.0` | pyramid | 96.96% | potent |
| `--resampler nearest` | pyramid | 97.17% | potent |
| `--photometric off` | estimator | 97.20% | potent |
| `--pyramid-select hard-max` | pyramid | 96.40% | potent |
| `--gate 8.0` | estimator | 96.30% | potent |
| `--pyramid-sharpen 1.0` | pyramid | 96.19% | potent |
| `--resampler lanczos3` | pyramid | 96.08% | potent |
| `--pyramid-bands 3` | pyramid | 95.96% | potent |
| `--pyramid-exponent 4.0` | pyramid | 84.08% | potent |
| `--pyramid-base weighted` | pyramid | 31.92% | potent |
| `--auto-exposure` | pyramid | 0.33% | **inert in effect** |
| `--exposure 3` | pyramid | 0.00% | **INERT** |
| `--confidence-tail 0.2` | pyramid | 0.00% | **INERT** |
| `--target-n-eff 2` | estimator | 0.00% | inert BY DESIGN |
| `--flat-roi 100,100,512,512` | estimator | 0.00% | inert BY DESIGN |
| `--detail-roi 100,100,512,512` | estimator | 0.00% | inert BY DESIGN |
| `--stats` | estimator | 0.00% | inert BY DESIGN |
| `--fix-ca a7c2-fe100gm-2xtc-x4cpl` | pyramid | 0.00% | **not a defect** |
| `--demosaic` | pyramid | 0.00% | **not a defect** |

### The finding class: documented but inert

**`--confidence-tail` is inert on the artefact it names.** Its help says
"Per-channel tail fraction for the confidence union mask". Swept from `0.02` to
`0.90` -- a 45x range -- it produces **one bit-identical confidence map**, and
does not move the image either. The map is **proven responsive** on the same
run: `--pyramid-gate 8.0` moves it by 16.27% and `--pyramid-bands 3` by 9.66%,
so the null is readable.

`--exposure` and `--auto-exposure` are covered in Part 1 and in
`AUDIT-user-surface.md`.

### Inert by design, and correctly so

`--target-n-eff` says in its own help "**A CALIBRATION AID, NOT A SECOND
KNOB**"; `--flat-roi`, `--detail-roi` and `--stats` are diagnostics. These move
no pixels because they are not supposed to. **They are not defects and should
not be counted as any.**

### Two phantoms I caught before reporting them

- **`--fix-ca` reads inert and is not.** It logs `lateral CA : CORRECTING` and
  moved 0.0000% on two subjects, which looks exactly like the `--exposure`
  defect. The mechanism is the opposite: **the correction is on by default**
  (`gear matched; default on`), so naming the already-selected profile changes
  nothing. Disabling it with `STREHL_FIX_CA=off` moves **97.05%** of samples.
  The stage is potent; the flag is redundant.
- **`--demosaic` reads inert and is not.** `--srgb` already implies it. Against
  `--binned` the geometry changes from 2344x3516 to 4688x7032.

Both would have been false convictions. Both were caught by asking for the
mechanism before writing the number down.

### One thing the sweep found on the side

**`--confidence-tail` is accepted without complaint on a backend that cannot use
it.** The tool is capable of refusing such combinations -- `--confidence-map`
with `--merge estimator` gives a precise, helpful error naming the alternative --
so silent acceptance here is inconsistent with the tool's own standard.

---

## Not tested, and why

- **`--stats-placebo` takes a `<DIR>` argument**, which my sweep did not supply,
  so it failed to run and is **unverified** rather than inert.
- **`--focus`, `--index-map`, `--n-eff-map`, `--limit`, `--out`** were not swept.
- **`--srgb`, `--linear-srgb`, `--binned`** change the container or geometry, so
  a same-shape pixel comparison does not apply to them.
- **One subject, four frames.** A flag potent only on deep stacks or on other
  content would read inert here. The potent rows are safe from this; the inert
  rows are the ones that would benefit from a second subject.
- **`--confidence-tail` was swept on the pyramid backend**, where its artefact
  lives. Whether it has an effect reachable only through the estimator is
  unverified.

## Instrument defects in this round

1. **My first `--confidence-tail` sweep was invalid** -- I set
   `STREHL_MERGE=estimator` and asked for `--confidence-map`, which the tool
   refuses. It **failed loudly on all six settings** rather than returning a
   convenient null, and I re-ran it on the right backend.
2. **My sweep baseline included `--srgb`**, which implies a demosaic, so
   `--demosaic` read inert as an artefact of the baseline rather than of the
   flag.
3. **I passed `--stats-placebo` as a bare switch** when it takes a directory.
"""
io.open(P,"w",encoding="utf-8",newline="\n").write(T)
print("wrote", P)
