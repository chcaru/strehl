# M104c — independent verification of the M95 binning patch at `56bd846`

**Milestone:** M104c. **Status:** VERIFIED, with two defects reported that
neither M95 nor the orchestrator named.
**Subject:** commit `56bd846`, M95's verbatim patch to `crates/strehl-cli/src/main.rs`,
applied by the orchestrator. M95 must not verify its own fix and the applier
must not be the only check on his own application.

**Method note.** Every number below compares a binary built from **`56bd846^`
(`28e0b35`)** against one built from **`56bd846`**, in two detached worktrees
under `C:\dev\strehl-verify`, so the shared working tree was never touched.
That isolates the patch. Verifying at `HEAD` instead would conflate it with
M99 and M103, which change merge output deliberately. Harness:
`experiments/M104b-demosaic/src/verify_m95.ps1`; raw logs and hashes in
`C:\dev\strehl-out\M104-verify\`.

---

## 1. The three checks

Run on **two stacks the orchestrator did not use**, at **two frame counts he
did not use** (his: `coffee-bean --limit 20`). `STREHL_ALIGN=0`, because a
`--limit` subset has a different bracket digest from the committed sidecar and
strehl correctly refuses to apply a warp map fitted on a different frame set —
so nothing was written beside the captures. Both arms are identical in every
other respect, and the patch rewires a CLI boolean, which is orthogonal to
alignment.

### CHECK 1 — the byte freeze. **PASS**

| stack | frames | pre-patch SHA-256 | post-patch | verdict |
|---|---|---|---|---|
| `flat-on-ruler-cpl` | 13 | `B9F25166…01B1` | `B9F25166…01B1` | identical |
| `wrapped-text-1` | 7 | `AD052246…3F1F` | `AD052246…3F1F` | identical |

**The negative control went red** (rule 39). An equality that cannot fail
proves nothing, so a change the patch has nothing to do with — one gate step,
`--gate 1.9` — was planted and CHECK 1's *own* comparison was required to
report it: `C7D5430C…ADC3F` against `AD052246…3F1F`, **differs**. The freeze
PASS is therefore a measurement and not a tautology.

### CHECK 2 — the emitted dimensions. **PASS, and one claim needs narrowing**

| stack | `--srgb` | `--srgb --binned` |
|---|---|---|
| `wrapped-text-1` | **7032 × 4688** | 3516 × 2344 |
| `flat-on-ruler-cpl` | **7040 × 4688** | 3520 × 2344 |

**`7032 × 4688` is stack-specific, not an invariant.** It is a property of the
sensor crop the decoder reports for that bracket. The invariant the patch
actually guarantees is **exactly twice the binned dimensions in each axis**. A
regression test hard-coding `7032` would fail spuriously on `flat-on-ruler-cpl`
and would be recording the wrong property. (My own M104b MHC render of that
same ruler is 7040 × 4688, from the same cause.)

### CHECK 3 — the gap the orchestrator could not close. **PASS**

The arm that proves the opt-out restores the old *behaviour* rather than merely
the old *dimensions*: post-patch `--srgb --binned` against **pre-patch**
`--srgb`.

| stack | pre-patch `--srgb` | post-patch `--srgb --binned` | verdict |
|---|---|---|---|
| `flat-on-ruler-cpl` | `A56652DA…3555` | `A56652DA…3555` | **byte-identical** |
| `wrapped-text-1` | `13EA6029…3D02` | `13EA6029…3D02` | **byte-identical** |

The boolean argument was right, and it is now measured on both stacks. This
needed the parent commit built; it cannot be settled by reading.

---

## 2. The attack: reaching the demosaic branch without asking for it

M95 shaped the patch around a real hazard — in `write_merged`, `if demosaic {…
return Ok(()); }` (`merge_cmd.rs:2881`) sits **before** the binned-colour
branch (`:2921`) and the byte-frozen measurement path (`:2959`), so a naive
default-on would have hijacked the corpus. I confirmed that ordering by
reading, then tried to reach the branch.

**I could not, and the attempts are the evidence:**

- **`--binned` alone, no `--srgb`.** Byte-identical to the measurement output
  on both stacks (`B9F25166…`, `AD052246…`). The new flag cannot disturb the
  frozen path.
- **No environment route.** No `env =` on `srgb`, `demosaic` or `binned`; the
  only `default_value_t` among the `Stack` arguments is `--exposure 0.0`; the
  CLI crate reads no `STREHL_*` variable. `demosaic` is reachable **only** from
  `--demosaic`, or `--srgb` without `--binned`.
- **The measurement invocation passes neither flag**, so
  `demosaic || (srgb && !binned)` is `false || (false && true)` — false by pure
  boolean logic, not by a value that happens to be false.

A false-for-the-wrong-reason boolean would still have to survive CHECK 3, which
requires the *binned* arm to reproduce prior bytes exactly, and ATTACK A, which
requires `--binned` alone to land on the frozen path. Both hold.

---

## 3. Two defects found — REPORT AND STOP, I own neither file

### 3.1 `argmax-baseline --srgb` was not migrated, and the asymmetry flatters `stack`

MEASURED, `wrapped-text-1 --limit 7`:

```
strehl stack            --srgb  ->  7032 x 4688   (32.97 MP)
strehl argmax-baseline  --srgb  ->  3516 x 2344   ( 8.24 MP)
```

`argmax-baseline` keeps its own `srgb: bool` (`main.rs:329`) and never reaches
the patched expression. The same flag now means full resolution on one
subcommand and binned on the other.

**Why this is more than cosmetic.** `argmax-baseline` exists to be *compared
against* `stack` — the `stack` help says *"Run `strehl argmax-baseline` to
reproduce the selector number yourself."* Rendering both with `--srgb` to look
at them now compares 32.97 MP against 8.24 MP. **Magnification reads as
sharpness** (discipline 606, and it fooled the orchestrator by eye once
already), so the naive baseline will look softer than it is. Rule 18 asks which
direction a stage can be fooled in: **this one is biased toward the project's
own thesis.**

The caveat string is honest — it says *"binned from one 2x2 quad per pixel —
NOT demosaiced"* — so nothing is misreported. The trap is in the comparison,
not the label.

### 3.2 `--demosaic --binned` is contradictory and resolves silently

MEASURED: emits 7032 × 4688. Because the expression is
`demosaic || (srgb && !binned)`, an explicit `--demosaic` cannot be overridden
by `--binned`; demosaic wins with no error and no warning. The precedence is
defensible, but clap has `conflicts_with` and this is its case.

---

## 4. What I did not verify

- **Not verified at `HEAD`.** Deliberate: `HEAD` carries M99 and M103, which
  change merge output on purpose, so a freeze test there measures them too.
  This report is about `56bd846` alone.
- **Alignment on.** Every arm ran `STREHL_ALIGN=0` (§1). The patch is CLI
  argument wiring and both arms were identical, but the default-alignment path
  was not exercised by this harness.
- `cargo test -p strehl-cli --bins`: **59 passed, 0 failed**, reproduced
  independently in the `56bd846` worktree.
