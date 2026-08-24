# M97g — the M100 handoff: the patch was already applied, and the freeze never broke

**Commission.** The orchestrator asked me, as the agent holding the contended
CLI files, to apply M100's verbatim patch (`docs/research/M100-exposure.md` §4)
in one atomic commit spanning `main.rs` and `merge_cmd.rs`, then confirm three
things: `cargo test -p strehl-core color::`, the byte-freeze at
`54A5E20F…7E7A2`, and `--srgb --exposure 0` ≡ `--srgb`.

**I did not apply it.** It was already applied. What follows is verification of
the shipped state instead, which is what the commission actually wanted.

---

## 1. The patch is already in the tree

`git log -- crates/strehl-cli/src/merge_cmd.rs` names it directly:

```
925d03d M100: apply the exposure patch I let sit for hours, and prove it inert
        crates/strehl-cli/src/main.rs       |  65 +++++
        crates/strehl-cli/src/merge_cmd.rs  | 143 +++++++++-
```

`+65 −0` on `main.rs` matches M100's stated hunk sizes exactly. `strehl stack
--help` carries both `--exposure <STOPS>` and `--auto-exposure`. This is the
**third** dispatch tonight sent on the premise that the exposure feature is
unshipped: `M105` was stood down for it, `M105b` opened its report with it
(`19c0a61`, "the feature I was sent to build already ships"), and now this one.

**Re-applying would have broken the tree**, which is precisely the failure the
commission was structured to avoid.

### 1.1 Proving that, rather than asserting it

`patchcheck.py` takes the comparison tree as `argv[1]`, so it can be pointed at
the repo to ask whether the NEW blocks are at HEAD. A check that answers
"found" everywhere is worthless unless it can also answer "absent", so I built
the pre-patch tree from `925d03d^` (`src/prepatch.py`, reading git blobs as
**bytes** via subprocess — on Windows `git show x:y > f` re-encodes the stream)
and ran the same check against it:

| tree | NEW blocks located | reading |
|---|---:|---|
| pre-patch (`925d03d^`) | **0 / 12** | the probe can report absence |
| HEAD | **7 / 12** | the patch is in |
| HEAD, OLD blocks | **0 / 12** | the pre-patch text is gone |

0 versus 7 is a discriminating probe. The 5 NEW blocks that no longer match
verbatim are later drift — `b843a3f` touched `main.rs` after the apply — not
absence: the flags, the `MergeOptions` fields, `Exposure::resolve` and the
`AppliedExposure` arithmetic are all present and the crate builds.

---

## 2. The byte-freeze holds, and the break was in the record

This is the check the commission called non-negotiable, and it initially
**failed**: the default render came out `CF266004…`, not `54A5E20F…`.

It matched, to the character, the constant `$POST` hard-coded in the
orchestrator's own `experiments/ORCH-drift-check/freeze_control.ps1`. So the
disagreement was reproducible and not mine.

`2f11005` had already established the mechanism — *"the renderer never moved"*,
and three false breaks in one session came from fixtures whose record omitted a
binding parameter, **"bee-3-cpl lost `--gate`"**. M100 §3.3 records its fixture
literally as `bee-3-cpl --limit 60`, with no `--gate`. The control script, and
my first run copying it, both passed `--gate 2`.

So I ran M100's fixture as written, across the two bindings rule 47 now
requires (`src/freezegrid.ps1`):

| cell | fixture | SHA-256 |
|---|---|---|
| E | no `--gate`, `STREHL_ALIGN=0` | `2E0AE672…` |
| **F** | **no `--gate`, aligned default** | **`54A5E20F…7E7A2`** ✓ |
| G | `--gate 2`, `STREHL_ALIGN=0` | `257A0DBD…` |
| H | `--gate 2`, aligned default | `CF266004…` |

**Cell F reproduces M100's frozen hash bit-for-bit.** The measurement path has
not moved. Four cells give four distinct hashes, only the exactly-specified one
matches, and the fixture is sensitive to *both* `--gate` and `STREHL_ALIGN` —
which is the case for rule 47 stated as a measurement rather than as a policy.

**This is the fourth instance of the same failure mode, and it is the sharpest,
because the incomplete fixture was carried by the control script written to
adjudicate the freeze.** An instrument that omits a binding parameter does not
report "unknown"; it reports a confident wrong answer that reproduces.

### 2.1 The cell F record, to amended rule 47

| binding | value |
|---|---|
| stack directory | `D:\personal\macro\bee-3-cpl` (absolute) |
| `--limit` | `60` (frames 0..59 of 299) |
| `--gate` | **not passed** — `DEFAULT_GATE = 4.0`, `merge.rs:297` |
| `--srgb` / `--demosaic` / `--exposure` | none passed |
| `STREHL_ALIGN` | **unset** (alignment ON, sidecar path) |
| `STREHL_WARPMAP` | **unset** |
| `STREHL_CACHE_DIR` | `C:\dev\strehl-out\M97\cache` |
| `STREHL_FIX_HALO` / `_DELTA` | **unset** |
| `STREHL_CAPTURES` / `STREHL_FREEZE_REQUIRE` | **unset** |
| threads | not pinned; 32 logical processors |
| output | **49 449 626 bytes**, 3516x2344 16-bit RGB |
| SHA-256 | `54A5E20F44255BB526C61D4397D239D6F1D26A06D54A8A56FBC944B91B37E7A2` |
| HEAD at render | `c4d678d` (11:38:38) |

Two honest caveats on the last two rows, both of which the rule should absorb.

**"The commit SHA I measured at" is not well defined in a shared tree.** The
binary is a build of the *working tree*, not of a commit, and seven other agents
commit into this tree continuously — HEAD moved from `c4d678d` to `63d24ca`
while I was writing this section, without my binary changing. The SHA above is
HEAD at render time with my own crate paths verified clean; it is not a promise
that a checkout of `c4d678d` reproduces the byte count, because a rebuild would
pick up whatever else had landed.

**Rule 47 under-enumerates the environment.** It names three variables. The
binary reads **seven**: `STREHL_ALIGN`, `STREHL_WARPMAP`, `STREHL_FIX_HALO`,
`STREHL_FIX_HALO_DELTA`, `STREHL_CACHE_DIR`, `STREHL_CAPTURES`,
`STREHL_FREEZE_REQUIRE`. At least one of the four it omits moves pixels:
`STREHL_CACHE_DIR` selects which sidecar `strehl stack` reads, and §5 measures
two renders of an identical command line differing only in cache contents
(`DB43E708…` against `ADF81E01…`). A record naming only the three listed
variables is still unreproducible. The enumeration should be generated from the
source rather than written in prose.

---

## 3. Round-trip identity — and a probe of mine that was half dead

My first attempt reported four bit-identical hashes and PASS on both the binned
and demosaiced paths. **That was wrong and I nearly shipped it.** At current
HEAD `--srgb` alone prints `7032 x 4688 … Malvar-He-Cutler demosaic`: M95
(`56bd846`) made the viewing render full-resolution, so `--srgb --demosaic` and
`--srgb` are the *same render*. I had run one path twice and called it two.

Redone on the one viewing path that now exists, with the plant the first
attempt lacked (`src/roundtrip.ps1`):

| arm | SHA-256 | |
|---|---|---|
| `--srgb` | `18F57024…6840` | = M100's recorded demosaiced hash |
| `--srgb --exposure 0` | `18F57024…6840` | **B2 PASS, bit-identical** |
| `--srgb --exposure 0.5` | `2B934F1F…` | **plant PASS — the probe can see a gain** |
| `--demosaic` alone | `961481FB…` | 7032×4688 linear |
| default | `54A5E20F…7E7A2` | 3516×2344 binned |

Without the third row, `--exposure 0` being bit-identical is equally consistent
with the flag being **ignored entirely**. It is not: 0.5 stops moves the file.

**Correcting myself again:** I first concluded `--demosaic` was a silent no-op.
It is not. It is redundant *when `--srgb` is passed*, and still changes the
linear output on its own. The narrower true statement is that M100's two
separately recorded B2 hashes (`EB1E0FE7` binned, `18F57024` demosaiced) have
since collapsed to one, and current `--srgb` equals the **demosaiced** one —
independent confirmation of M95's headline in a place M95 never looked.

---

## 4. §4.3 applied: the CLI crate lints clean

`halo.rs` was untouched since `52c6a52` (05:16) and clean in the working tree,
so the courtesy patch collided with nothing. Both hunks applied verbatim; both
are semantics-preserving, including on NaN — `hi.partial_cmp(&lo) !=
Some(Ordering::Greater)` yields `None != Some(Greater)` = `true`, the same
branch `!(hi > lo)` took.

`cargo clippy --release -p strehl-cli --bins -- -D warnings` → **rc=0**, the
first green all night. The freeze was re-measured *after* the edit and still
reads `54A5E20F…7E7A2`.

---

## 5. The shared sidecar cache can be repointed silently

Three separate claims reached me tonight that a stale sidecar *silently*
contaminates a render. All three measure as **loud refusals**, and the one real
silent path is none of them.

**Refused, every time** (`src/mismatch.ps1`, 79-frame sidecar forced onto other
brackets via `STREHL_WARPMAP`):

| bracket | rc | outcome |
|---|---:|---|
| 79 frames | 0 | `ON (sidecar-override), reference frame 0, 79 placed / 0 refused` |
| 20 frames | **1** | hard error, **no output file**, both digests named |
| 40 frames | **1** | hard error, **no output file**, both digests named |

`check_stack` compares a **digest of the frame paths**, not a count, so a
different subset of the same size cannot pass. And `load_or_solve`'s count guard
(`sidecar has N frames but the bracket has M; re-solving`) entered the tree in
**`885e9f7` — the same commit that wired alignment in**, by `git log -S`. The
guard and the feature shipped together, so no build in this tree can read a
sidecar without also checking it. Truncated files are rejected too (M97b §13.2,
8/8 rungs).

**Accepted silently** (`src/poison.ps1`). Neither guard covers the *solve
configuration*. `strehl align` without `--out` writes to exactly the cache entry
`strehl stack` later reads (`align_cmd.rs:380`), and the cache key hashes the
canonical **capture path**, not the frame set — so every solve of one directory
collides on one file:

| cache state | identical `stack` command line reports | SHA-256 |
|---|---|---|
| after `align --limit 79` | `ON (sidecar), reference frame 0` | `DB43E708…` |
| after `align --limit 79 --reference 40` | `ON (sidecar), reference frame 40` | `ADF81E01…` |

Same directory, same `--limit`, no environment override anywhere, **different
pixels, no warning**. The plant fires, so the effect is not inert. `--resampler`
sits in the same blind spot — the field M95 attributes 59% of the high-band loss
to.

**This also corrects my own claim of an hour earlier.** I said the hashed cache
key made the re-solve thrash impossible. It does not: the key is the capture
path, so `--limit 40` and the full bracket still overwrite each other. My M97f
relocate protected the read-only corpus and did **not** stop the churn.

The fix belongs in `align_cmd.rs` (not mine): fold reference and resampler into
`StackIdentity`, or into the cache filename. Bars for whoever takes it — the
mismatch arm must stay rc=1; the config arm must move from silent-accept to
refused.

---

## 6. The exit-code trap: the rule survives, the mechanism and the consequence do not

The rule — **never read `$LASTEXITCODE` after a pipeline containing `-First`** —
is correct and I have adopted it. Three things stated alongside it are not.

All cells below are 5 reps, each pre-cleared to a value that is not the answer
(`src/racetest.ps1`, `racetest2.ps1`, `racetest3.ps1`).

| producer | filter | true code | observed |
|---|---|---|---|
| `cmd /c` builtin loop, 50–20 000 lines | `-First 3` | 1 | `1` — **immune, 40/40 reps** |
| python `.exe`, 200 lines | none | 1 | `1` |
| python `.exe`, 200 lines | `-First 3` | 1 | `-1` (4/5) |
| python `.exe`, 200 lines | none | **0** | `0` |
| python `.exe`, 200 lines | `-First 3` | **0** | **`-1`** (4/5) |
| python `.exe`, 200 lines, 10 ms/line | `-First 3` | **0** | **`-1`** (5/5) |
| python `.exe`, 20 000 lines | `-Last 3` | 1 | `1` |

**1. The corrupted value is `-1`, not `0`.** PowerShell *kills* the child when
`Select-Object -First` throws `StopUpstreamCommandsException`, and `-1` is the
exit code of a killed process. The program never returned it.

**2. It is not volume-dependent, it is producer-dependent.** A `cmd` builtin
loop is immune at every size I tried, from 50 to 20 000 lines, on stdout and
through `2>&1`. A real `.exe` traps at 200. This is why two careful probes of
the same shell version disagreed: mine used `cmd /c`, and `cmd` is not exposed.
It *is* a race — `[1 -1 -1 -1 -1]` in one cell — but the race is over process
teardown, not over how many lines were produced.

**3. The dangerous direction is the opposite of the one broadcast.** The claim
was that this produces false negatives only, because "a truncation artifact
cannot invent a nonzero". It can, and does: **a command whose true exit code is
`0` reads `-1`**, 4/5 without a delay and 5/5 with one. So a gate written
`if ($code -ne 0) { throw }` around a truncated pipeline **fails a command that
succeeded**. Truncation turns green red, not red green.

That direction is worse than it sounds in this project, because a phantom
failure does not sit quietly — it gets investigated, and tonight several
milestone-hours went into defects that had not happened.

The failing arm also reads `-1`, so a `-ne 0` gate stays red on real failures —
correctly, but by accident rather than by measurement.

---

## 7. Status / Verified / Not verified / Notes

### Status
**DONE.** Nothing applied from §4.1/§4.2 because both were already in; §4.3
applied and verified.

### Changes
- `crates/strehl-cli/src/merge_cmd/halo.rs` — M100 §4.3, two lint fixes.
- `experiments/M97b-align-visible/src/prepatch.py`, `freezecheck.ps1`,
  `freezegrid.ps1`, `roundtrip.ps1` — the verification harness.
- **No changes** to `main.rs`, `merge_cmd.rs`, `align.rs`, `warpmap.rs`.

### Verified
- `cargo test --release -p strehl-core color::` → **24 passed, 0 failed**,
  reproducing M100's B8 exactly.
- `cargo test --release -p strehl-cli --bin strehl` → **62 passed, 0 failed**;
  `-p strehl-core --lib` → **262 passed, 0 failed**.
- `cargo clippy --release -p strehl-cli --bins -- -D warnings` → **rc=0**.
- Byte-freeze `54A5E20F…7E7A2` reproduced on M100's fixture as recorded, both
  before and after the `halo.rs` edit.
- B2 round trip bit-identical, with a 0.5-stop plant proving the probe is live.
- `patchcheck.py` discriminates 0/12 against the pre-patch tree, 7/12 at HEAD.

### Not verified
- **Why 5 of 12 NEW blocks no longer match verbatim.** I attributed it to
  `b843a3f` from the commit log without diffing the regions. The feature is
  functionally complete and the crate builds and tests; the text drift itself
  I did not trace.
- **I did not re-verify M100's B3/B4/B5/B6/B7 bars**, the clipping census, or
  the +1.54 / +3.74 stop measurements. The commission said not to redo M100's
  milestone and I did not.
- Whether `--demosaic` being redundant under `--srgb` is intended by M95 or an
  accident. I only measured that it is so.
- `cargo clippy --bins --tests` — not run after the fix; only `--bins` is green
  by measurement.

### Candidate facts (rule 28)

- **Q1 (MEASURED).** M100's byte-freeze is **intact at HEAD**: `bee-3-cpl
  --limit 60` with **no `--gate`** and alignment at its default reproduces
  `54A5E20F…7E7A2` exactly. The apparent break was `--gate 2`, absent from
  M100's record and added by the control script written to adjudicate it. A
  2×2 grid over `--gate` and `STREHL_ALIGN` yields four distinct hashes, so the
  fixture is sensitive to both.
- **Q2 (DERIVED, method).** An instrument built from an under-specified fixture
  does not report "unknown" — it reports a **confident wrong answer that
  reproduces**, which is why `CF266004` looked like corroboration when the
  orchestrator's script and my run agreed. Reproducibility is not validity when
  both runs inherit the same missing binding.
- **Q3 (MEASURED).** At HEAD `--srgb` implies full-resolution demosaic, so
  `--srgb --demosaic` ≡ `--srgb` and M100's two separately recorded B2 hashes
  have collapsed into one; current `--srgb` equals its **demosaiced**
  `18F57024…`. `--demosaic` alone still changes the linear output, so the flag
  is redundant under `--srgb`, not dead.
- **Q4 (MEASURED, method).** A round-trip "bit-identical" PASS is
  indistinguishable from the flag being ignored. `--exposure 0` ≡ `--srgb` only
  became evidence once `--exposure 0.5` was shown to move the file. Discipline
  598 applies to identity tests, not only to null metrics.
- **Q5 (MEASURED).** Three dispatches in one night were commissioned on the
  premise that the exposure feature was unshipped, after it was applied in
  `925d03d`. Checking `git log -- <file>` before writing a brief costs one
  command.
- **Q6 (MEASURED).** `strehl align` without `--out` repoints the shared cache
  entry `strehl stack` reads. An **identical** `stack` command line, with no
  environment override, renders `DB43E708…` or `ADF81E01…` depending only on
  whether an unrelated `align --reference 40` ran first, and **prints no
  warning**. `StackIdentity` covers the frame set, not the solve configuration.
- **Q7 (MEASURED + DERIVED).** Three separate reports of *silent* sidecar
  contamination — torn files, wrong-subset files, short files — all measure as
  **loud refusals**: rc=1, no output file, both digests named. The count guard
  entered the tree in `885e9f7`, the same commit that wired alignment in
  (`git log -S`), so **no build here can read a sidecar without checking it**.
  DERIVED from that: a `bee-3-cpl` render could not have merged 40 frames while
  believing it had 299; the worst case was a wasted re-solve.
- **Q8 (MEASURED).** Rule 47 enumerates three environment variables; the binary
  reads **seven** (`git grep -oh "STREHL_[A-Z_]*"`). At least one omitted
  variable, `STREHL_CACHE_DIR`, moves pixels by Q6. A prose enumeration of an
  environment contract drifts from the source it describes; generate it.
- **Q9 (MEASURED, method).** The `$LASTEXITCODE`-after-truncation trap is
  **producer-dependent, not volume-dependent**. A `cmd` builtin loop is immune
  from 50 to 20 000 lines, on stdout and through `2>&1`, 40/40 reps; a real
  `.exe` traps at 200 lines. The corrupted value is **`-1`** — PowerShell kills
  the child on `StopUpstreamCommandsException` — not `0`. Two careful probes of
  the same shell version disagreed for exactly this reason.
- **Q9b (MEASURED).** Truncation **can invent a nonzero**. A command whose true
  exit code is `0` reads `-1` through `-First 3`, 4/5 reps without a delay and
  5/5 with one. So the hazard runs green→red: a gate written
  `if ($code -ne 0) { throw }` fails a command that succeeded. The stated
  consequence — "produces false negatives only" — is backwards.
- **Q9c (MEASURED, method).** A naive A/B of this trap returns a false negative
  because `$LASTEXITCODE` retains the previous command's value; every arm must
  be pre-cleared to a value that is not the answer. My first two probes returned
  "no trap" for this reason and I nearly filed it. Discipline 598 applies to
  exit codes.
- **Q10 (MEASURED, method).** Re-running a *fixed* linter that now reports zero
  violations cannot verify the fix: the reporter loop never executes, and the
  summary's em dash is encodable in cp1252 anyway. A separate plant printing
  `Δ → ≤ −` through both code paths is required, and does discriminate —
  pre-fix arm prints 0 violations with a `UnicodeEncodeError`, post-fix arm
  prints 1 and the summary, **both exiting 1**.

### Notes
The corpus-write fix `2f11005` requested of "the agent holding `align_cmd.rs`"
is **landed** — `8118dd7`, hashed cache root plus atomic write, verified
end-to-end. That commit's fact 1390 (cleanup does not lower the stray rate) and
my P15 (a new stray appeared after the sweep) are the same measurement from two
directions, and both point at the source rather than the sweep.
