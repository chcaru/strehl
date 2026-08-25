# M124 — `--resampler` reaches `strehl stack`, and the default does not move

**Status: landed.** The kernel that `strehl align` has been able to choose since M95 is
now choosable on `strehl stack` as well. Nothing else changed. The no-flag render is
byte-identical to the no-flag render from before this commit, proven by hash rather than
by reading the diff.

This discharges **G3** of `docs/research/ORCH-kernel-decision.md` ("a `--resampler` flag
exists on `strehl stack`"). It does **not** execute that decision, and takes no position
on it. The default is still `catmull-rom`.

---

## 1. Why this existed as a gap

M118 §7 recommended exactly this change and handed over a diff rather than applying it.
Its fact 1674 recorded the two consequences of the gap:

- the merge's kernel was a **literal** — `Resampler::CatmullRom` written inside
  `align_cmd.rs::merge_config` — so no `stack` invocation could alter it;
- the shipped `lanczos2` variant was **unreachable from any command line**. M118's Y6
  could only be measured by hand-writing a warp-map sidecar.

The deeper reason to close it before any default moves is discipline 853, which M118
quotes: lanczos-3 costs **2.9×–3.9×** the default, and *a quality change that cannot be
declined is a tax, not a default*. The flag has to exist first. It now does.

---

## 2. What changed

Four files, +253 −22.

### `crates/strehl-core/src/warpmap.rs`

The name→variant mapping already lived here (`resampler_from_name`), used by sidecar
deserialisation. A **second, private** copy lived in `AlignArgs::resampler` in the CLI —
and that second copy is precisely how `lanczos2` became unreachable: the sidecar parser
knew the name, the CLI parser did not. Two mappings for one vocabulary is the defect.

- `resampler_name` and `resampler_from_name` widened `pub(crate)` → `pub`, with doc
  comments stating the contract (`None` is the only answer for an unknown name; it never
  guesses).
- New `pub const RESAMPLER_NAMES: [&str; 5]` — the single list of legal names, used both
  for the error message and by the test below.
- New test `every_listed_resampler_name_maps_to_a_distinct_variant`: every name in
  `RESAMPLER_NAMES` resolves, and no two resolve to the same variant. This is what makes
  the list and the mapping unable to drift apart again.

*This crate is outside the letter of the brief, which named only the CLI. Disclosed in §7.*

### `crates/strehl-cli/src/align_cmd.rs`

- `pub const DEFAULT_RESAMPLER_NAME: &str = "catmull-rom"` — the literal's old value,
  now named once and referenced by both commands' clap `default_value`.
- `pub fn parse_resampler(name: &str) -> Result<Resampler>` — the **one** parser, a thin
  delegate to `resampler_from_name` that turns `None` into the error in §5.
- `AlignArgs::resampler()` body is now `parse_resampler(&self.resampler)`. The private
  duplicate `match` is deleted.
- `merge_config(n, resampler)` takes the kernel as a parameter; the literal is gone.
- `load_or_solve(dir, paths, threads, resampler)` takes and forwards it.
- Three new tests, described in §6.

### `crates/strehl-cli/src/merge_cmd.rs`

- `MergeOptions` gains `pub resampler: Resampler`.
- `alignment_for` forwards it to `load_or_solve`.
- **New non-fatal stderr warning** when `STREHL_WARPMAP` is set and the sidecar's
  recorded kernel differs from the requested one ("THE SIDECAR WINS"). See §7.

### `crates/strehl-cli/src/main.rs`

- `Command::Stack` gains `--resampler <NAME>`, `default_value =
  align_cmd::DEFAULT_RESAMPLER_NAME`, parsed via `align_cmd::parse_resampler`.

**`merge` needed no separate work.** It is `#[command(alias = "merge")]` on
`Command::Stack`, not a second subcommand, so `strehl merge --resampler …` works by
construction. (`merge_cmd.rs` is a module name, not a command.)

---

## 3. The hashes (MEASURED)

**The whole invocation** (AGENTS rule 47), identical across every arm except the flag
under test:

| | |
|---|---|
| binary | `.cargo-target-m124\release\strehl.exe`, `--release` |
| command | `strehl stack D:\personal\macro\coffee-bean --limit 20 --gate 2.0 [FLAG] -o <out>.tif` |
| capture dir | `D:\personal\macro\coffee-bean` (105 ARW present) |
| frames | `DSC00016..DSC00035` — the prefix `--limit 20` selects, verified against the directory |
| `--limit` | `20`, explicit |
| `--gate` | `2.0`, explicit (never `default`; `DEFAULT_GATE` has moved before) |
| `--srgb` | not passed |
| `--demosaic`, `--photometric` | not passed |
| `STREHL_ALIGN` | **unset** — registration ON, i.e. the solving path, the only path the flag can reach |
| `STREHL_WARPMAP` | **unset** — a fresh solve, not the committed fixture |
| `STREHL_CACHE_DIR` | a private, **empty, per-arm** scratch dir under `C:\dev\strehl-out\M124\` |
| `STREHL_FIX_HALO`, `STREHL_FIX_CA` | unset |
| chunking | 10 chunks of ≤ 2 frames (reported, not asserted — a property of this host) |
| output size | 49,449,626 bytes, **every arm** |
| "before" tree | HEAD `8433f50`-era, unmodified working tree |
| "after" tree | this change applied on HEAD `581253c` |

| arm | flag | SHA-256 | wall |
|---|---|---|---|
| **A · default, BEFORE the change** (×3 runs) | *none* | `119936E656CD4E844F8345F23D8196B6B282C883C4B828318BADC6E222BAD709` | 8.1 s |
| **B · default, AFTER the change** | *none* | `119936E656CD4E844F8345F23D8196B6B282C883C4B828318BADC6E222BAD709` | 7.9 s |
| **C · explicit default** | `--resampler catmull-rom` | `119936E656CD4E844F8345F23D8196B6B282C883C4B828318BADC6E222BAD709` | 7.5 s |
| **D · lanczos3** | `--resampler lanczos3` | `DF11F4ECCC7940C9E2AEDAAE492099DAB0B3A9399345DDC24486774B4910D189` | 27.8 s |
| **E · nearest** | `--resampler nearest` | `197CCB053E61862B67E699047668A02AFC938F514925220150B6DA02C57B2737` | 5.4 s |
| **F · lanczos2** | `--resampler lanczos2` | `1F1B562DBBCF29B6B6008CE9D3C6A482BE88E553DDA7758E82EBBD622982F6BE` | 18.7 s |
| **G · bilinear** | `--resampler bilinear` | `FB51EFF297A4CF77375626A15B07E679FD91CBFE01E7CFC680A25F5DF3178B6D` | 6.5 s |

**A = B = C.** The default is byte-identical before and after, and passing the default
name explicitly is byte-identical to passing nothing.

**D ≠ E ≠ F ≠ G ≠ B, all five distinct.** The flag is wired to pixels. This is the check
the project demands by hash and not by code review, because `optics.rs` once had 287
passing tests and zero consumers, and `STREHL_FIX_CA` under `STREHL_ALIGN=0` was a silent
byte-identical no-op.

Every arm's stderr also printed the kernel it actually used (`resampler : CatmullRom`,
`… : Lanczos3`, …), so the flag is confirmed at two independent points.

**Whole matrix re-run after the final edit**, on a fresh rebuild with fresh caches: all
seven hashes reproduced exactly.

### Determinism, and why arm A is unusually well anchored

Arm A was run **three times** — fresh cache, warm cache, second fresh cache — and gave
`119936E6…D709` all three times. The solve is deterministic.

More than that: `119936E6…D709` is *already in the corpus*. It is the recorded hash of
the byte-freeze row `coffee-bean-20-gate2-sidecar`, and that row **HOLDS** in the test
run of §6. So the default render is pinned to a committed fixture at both ends of this
change, independently of the fact that HEAD moved under me while I worked.

Note the two are not the same invocation: the freeze row reads a committed sidecar
(`env_warpmap=coffee-bean-20.warpmap.txt`), while arm A *solves*. They agree because a
fresh solve of this bracket reproduces the committed sidecar's warps exactly — which the
registry's own `why` column already asserts (`EF745413...E93B3`). I re-measured that:
the sidecar this run cached is `coffee-bean-55f8b4c1af1e8037.warpmap.txt`, content SHA
`EF74541395DB1BA6…`, **the same file name and the same content before and after my
change**.

**Provenance caveat.** HEAD moved four times under me while I worked (other agents are
active in this tree). The "after" arms were measured with this change applied on
`581253c`; the commit's parent is `321398f`. The two commits in between
(`3fb8359`, `321398f`) touch only `docs/research/SYNTHESIS.md` and two
`experiments/` Python files — **no Rust source**, so the measured tree and the committed
tree are code-identical. Stated rather than assumed, because "I measured a slightly
different tree than I committed" is exactly the kind of gap this project's freeze
registry exists to catch.

### Cost (MEASURED as a BOUND, not a value — AGENTS rule 16)

Two runs of the whole matrix on a shared machine with other agents active. Ratios to the
no-flag arm, across both runs: lanczos3 **3.4×–3.5×**, lanczos2 2.3×–2.4×, bilinear
0.69×–0.82×, nearest 0.67×–0.68×. These are wall clock for the *whole* merge, one host,
two runs — a bound, not a value.

The lanczos3 figure sits inside M118 Y10's 2.91×–3.92× bracket, which corroborates that
bracket rather than re-measuring it. The bilinear figure's upper end (0.82×) sits *outside*
M118 Y10's 0.56×–0.69×; I attribute that to load on this host rather than to a real
change, since the same arm gave 0.69× on the other run — but I did not isolate it, and it
should not be treated as a refinement of M118. The `--help` text quotes M118's brackets,
not these numbers.

---

## 4. The kernel only reaches pixels through the solve (DERIVED, from the code)

The merge gathers each frame with `map.resampler()` — the kernel **recorded in the
`WarpMap`** — not with the flag directly. So:

- `STREHL_ALIGN=0` → no warp map exists, the flag is inert;
- `STREHL_WARPMAP=<sidecar>` → the sidecar's recorded kernel wins;
- otherwise → `load_or_solve` stamps the flag into the map it solves, and the flag decides.

This is not a defect, it is the sidecar contract: a warp map is a self-describing record
of *how* it was applied, and a flag cannot retroactively change what a committed file
says. But it is a trap for the third case, so §7 adds a warning rather than leaving it
silent.

`solve_config_key` already hashes the resampler, so two kernels occupy two cache entries
and neither can ever be served the other's warps. Measured: the default's cache key is
unchanged by this commit, and lanczos3 gets a different one
(`coffee-bean-d170d4e4996bd5e1`).

---

## 5. Unknown names (MEASURED)

```
> strehl stack D:\personal\macro\coffee-bean --limit 2 --resampler bogus -o out.tif
Error: unknown resampler "bogus"; valid choices are nearest, bilinear, catmull-rom, lanczos2, lanczos3
exit=1

> strehl align D:\personal\macro\coffee-bean --limit 2 --resampler bogus
Error: unknown resampler "bogus"; valid choices are nearest, bilinear, catmull-rom, lanczos2, lanczos3
exit=1
```

Byte-for-byte the same message from both commands, because it is the same function. It
names the offending value and lists the choices. No silent fallback. On `stack` it fires
**before any decode**, so a typo costs a fraction of a second and not a full merge.

---

## 6. Tests (MEASURED)

| suite | result |
|---|---|
| `cargo test -p strehl-cli` (unit) | **70 passed, 0 failed** |
| `cargo test -p strehl-cli` (byte-freeze, `STREHL_FREEZE_REQUIRE=1`) | **5 passed, 0 failed**, 184 s |
| `cargo test -p strehl-core` | **352 passed, 0 failed** |

Both freeze rows printed `HOLDS … reproduced twice`:
`coffee-bean-20-gate2-unaligned` = `D99F5D82…76CA`, `coffee-bean-20-gate2-sidecar` =
`119936E6…D709`. Both runs recompiled the crate under test (rule 33 — a green suite that
did not compile your change is not evidence).

Four new tests, all in files that already had `mod tests`:

1. `warpmap::every_listed_resampler_name_maps_to_a_distinct_variant` — the name list and
   the mapping cannot drift.
2. `align_cmd::the_merge_default_is_still_the_literal_it_replaced` — asserts
   `merge_config`'s default is the `CatmullRom` that used to be written there. This is the
   test that fails if someone moves the default without going through
   `ORCH-kernel-decision.md`.
3. `align_cmd::every_offered_resampler_name_reaches_a_variant` — every name the `--help`
   offers actually parses, including `lanczos2`.
4. `align_cmd::an_unknown_resampler_is_refused_by_name_and_offers_the_choices` — asserts
   the error text contains the bad name and all five valid ones.

`cargo check --workspace --all-targets` is clean, no warnings.

**clippy and rustfmt: the repo is already not clean, and I did not make it worse.**
`cargo clippy -p strehl-core -p strehl-cli --all-targets -- -D warnings` exits 101, with
**zero findings in any file I touched** — all are pre-existing in
`examples/m89-robust.rs`, `examples/m90-rho.rs`, `src/softgate.rs`. rustfmt likewise:
baseline at HEAD is `warpmap.rs` 0 diffs, `align_cmd.rs` 5, `merge_cmd.rs` 5, `halo.rs` 1.
I introduced three violations, found them, and fixed all three; final counts are exactly
the baseline. I deliberately did **not** reformat the pre-existing ones — that would be
sweeping other agents' files in a shared tree.

---

## 7. Findings, including what contradicts the brief

**F1 — `byte-freezes.tsv` needs no new row, and structurally cannot take one.**
This is the most important finding here and it is a real limitation, not a dodge. The
freeze harness *builds* each render command out of its row, and the header is checked
verbatim. There is **no `resampler` column**, so no row can pass the flag — and adding one
means editing the header, which the registry forbids (append-only). Worse, even if a
column existed: the parser **rejects solving rows** (`env_align=unset` +
`env_warpmap=unset` panics on sight), and the only two admissible modes — alignment off,
or sidecar override — are *exactly the two modes in which `--resampler` cannot change a
byte* (§4). So `--resampler` on `stack` is **unfreezable under the registry's current
design**. Freezing it would need either a new column plus a relaxation of the
solving-row rejection, or a freeze of the solved sidecar rather than the rendered TIFF.
Both are larger decisions than this change and I did not make either. The two existing
rows still HOLD, and they are what proves the default did not move.

**F2 — the default render's hash *is* an existing freeze.** Arm A/B/C's
`119936E6…D709` is the `coffee-bean-20-gate2-sidecar` row verbatim. That makes the
byte-inertness proof stronger than a self-measured before/after, and it inherits that
row's recorded caveat, which must not be papered over: **every aligned run of this
bracket prints "this solve could not certify itself … the registration below is
UNVERIFIED".** This change does not touch that and does not improve it. The hash pins a
registration the tool itself declines to certify — constant, but not certified.

**F3 — `strehl align --resampler lanczos2` now works too.** A side effect of collapsing
the two mappings into one. It was previously accepted by the sidecar parser and rejected
by the CLI parser for the same string. Nobody asked for this, but leaving the two parsers
disagreeing was the actual bug behind M118's Y6, and fixing it in one place fixes it in
both.

**F4 — I touched `strehl-core`, which is beyond the brief's letter.** The brief said to
lift the mapping to a shared function "if it currently lives in a private `impl AlignArgs`
method". It did — but a *public* copy also already existed in `warpmap.rs`. Copying the
private one into the CLI would have created a third; lifting the private one into a new
CLI-level function would have left two. I made the CLI delegate to the existing core
function and deleted the private copy, which is the only option that ends with one
mapping. Cost: a `pub(crate)` → `pub` widening in `strehl-core`.

**F5 — I added an unrequested stderr warning.** When `STREHL_WARPMAP` is set and the
sidecar's kernel differs from `--resampler`, the tool now says so and states that the
sidecar wins. Rationale: §4 means the flag is *legitimately* ignored there, and this
project has twice been bitten by a flag that was silently ignored. It is a **warning, not
an error**, deliberately: M118's D4 measurement route sets both, and turning that into a
hard failure would break a documented measurement path. It cannot fire on the freeze
fixture — `tests/data/coffee-bean-20.warpmap.txt` records `resampler catmull-rom`, which
equals the default — and the freeze suite passed with it in place.

**F6 — the default was not moved, and I was not tempted to move it by anything I saw.**
The measurements here say nothing about whether lanczos3 is better; they only say it is
*different* and *costly*. That question is pre-registered in
`ORCH-kernel-decision.md` and its G3 is now satisfied. Note for whoever runs it: this
change makes the GO side of that decision *cheaper to reverse*, since after it a user who
dislikes a moved default can pass `--resampler catmull-rom` and get, provably, the exact
bytes the whole corpus was measured through (arm C).

**F7 — nothing in the brief was wrong.** The flag did not already exist; `align_cmd.rs:150`
and `:85` were where the brief said; the literal was in `merge_config`; `lanczos2` was
unreachable. The one correction is `merge`: it is an alias of `stack`, not a second
command path, so there was no second gap to close.

---

## 8. What this does not do

- Does not change the merge algorithm, the exposure path, the colour path, or `DEFAULT_GATE`.
- Does not move any default.
- Does not measure image quality. Nothing here is a claim about which kernel looks better;
  §3's hashes are difference detectors, not quality metrics, and no number in this
  document came from an `--srgb` render.
- Does not make `--resampler` effective under `STREHL_ALIGN=0` or under a
  `STREHL_WARPMAP` override. It warns in the second case and is simply inert in the first.
