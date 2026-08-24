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

## 5. Status / Verified / Not verified / Notes

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

### Notes
The corpus-write fix `2f11005` requested of "the agent holding `align_cmd.rs`"
is **landed** — `8118dd7`, hashed cache root plus atomic write, verified
end-to-end. That commit's fact 1390 (cleanup does not lower the stray rate) and
my P15 (a new stray appeared after the sweep) are the same measurement from two
directions, and both point at the source rather than the sweep.
