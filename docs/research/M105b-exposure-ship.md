# M105b — Exposure on the viewing path: the feature was already shipped

**Stem.** Dispatched as `M105`. That stem is taken: `AGENTS.md`'s ledger already
carries an `M105` row recording a dispatch **stood down within 20 minutes on
2026-08-24** for the exact reason this report opens with. Rule 41 makes a
milestone number an identifier belonging to a dispatch, so this second dispatch
takes **`M105b`**. A ledger patch is in §7.

**Status of this section (§0 and §1) at commit time: written and committed
BEFORE any measurement was run.** §2 onward was appended after.

---

## 0. The commission, and the error in it

> *"The tool ships renders that are 1.5 to 3.7 stops underexposed, and the fix
> exists only in a Python experiment script."*
> *"Shipped source: there is no exposure logic in the CLI at all. I grepped
> `crates/strehl-cli/src` for `exposure|ev_|auto_ev|percentile|stops` and got
> two unrelated doc comments. Verify this yourself; if I am wrong it changes the
> whole milestone."*

I verified it. **It is wrong, and it changes the whole milestone.** Three
errors, all found before any code was written, in the order I found them.

### 0.1 The feature is shipped, and this is the second dispatch to be told it is not

`AGENTS.md` line 624, the `M105` ledger row, written by the orchestrator
**before this brief was sent**:

> **DISPATCHED ON A FALSE PREMISE AND STOOD DOWN WITHIN 20 MINUTES.** I
> repurposed an idle agent to build exposure into the CLI, briefing it that
> *there is no exposure logic in the CLI at all* [...] **The premise was false
> and the search behind it was scoped to one crate of two**: M100 had already
> built, tested and shipped the entire feature in
> `crates/strehl-core/src/color.rs`.

SYNTHESIS fact **1347** folds the same finding. The brief I received restates
the premise the ledger and the corpus had both already recorded as false.

MEASURED, at HEAD `519203f`, grepping **both** crates rather than one:

| symbol | file:line |
|---|---|
| `AUTO_EXPOSURE_PERCENTILE = 99.9` | `crates/strehl-core/src/color.rs:377` |
| `AUTO_EXPOSURE_TARGET = 0.90` | `crates/strehl-core/src/color.rs:391` |
| `AUTO_EXPOSURE_MAX_STOPS = 6.0` | `crates/strehl-core/src/color.rs:401` |
| `AUTO_EXPOSURE_STEPS_PER_STOP = 100.0` | `crates/strehl-core/src/color.rs:419` |
| `enum Exposure`, `Exposure::resolve` | `color.rs:423`, `color.rs:471` |
| `enum ExposureError` (3 refusals) | `color.rs:435` |
| `struct AppliedExposure`, `gain`, `reproduce_flag` | `color.rs:524`, `545`, `560` |
| `choose_exposure`, `exposure_stops_for` | `color.rs:613`, `color.rs:632` |
| `--exposure <STOPS>` CLI flag | `crates/strehl-cli/src/main.rs:131-158` |
| `--auto-exposure` CLI flag | `crates/strehl-cli/src/main.rs:159-182` |
| consumption in the render command | `crates/strehl-cli/src/merge_cmd.rs:43, 84-92` |

The orchestrator's own grep pattern *does* hit this: `main.rs:96` is
`/// it exactly. Pass --auto-exposure to have the gain chosen and PRINTED, or`.
The two hits dismissed as "two unrelated doc comments" are the feature's own
documentation.

### 0.2 `stack.rs` is not the `stack` subcommand

> *"`gallery.py` invokes `strehl stack ...`. So the owner-facing render path is
> the **`stack`** subcommand, not `merge`. That is fortunate, because it lets
> you ship this without touching a single contended file. You may write [...]
> `crates/strehl-cli/src/stack.rs` — the call site."*

MEASURED, `crates/strehl-cli/src/main.rs:369-419`:

```rust
Command::ArgmaxBaseline { .. } => stack::run(&StackOptions { .. }),
Command::Stack { .. } => merge_cmd::run(&MergeOptions { .. }),
```

`stack.rs` implements **`argmax-baseline`**, the legacy selector. The `stack`
subcommand is `merge_cmd::run`. So the brief's grant of a safe seam is void in
both directions: the file it offered me is dead code on this path, and the file
that actually renders the owner's photographs — `merge_cmd.rs` — is on the
brief's own **forbidden** list. Had I accepted the brief, I would have written
a correct auto-exposure into a function the owner's render never calls, and
nothing in the brief's acceptance criteria would have caught it.

### 0.3 The default-on question was asked and answered

The brief's first "consider and free to reject" item is whether auto-exposure
should be default-on for `--srgb`. `M100-exposure.md` **§3.6** is titled
*"Should `--auto-exposure` be on by default with `--srgb`?"*, answers **no**,
ships a printed advisory instead, and hands the decision to the orchestrator.
Its decisive argument is the asymmetry of the mistake: turning it on later
invalidates nothing, turning it off later invalidates every published render.

The brief's second item — whether `p99.9` is the right statistic — is
`M100-exposure.md` §3.2, a sweep of 7 percentiles x 5 targets x 2 statistics on
7 stacks.

### 0.4 What that leaves

Nothing to build. It leaves something worth doing instead, and it is the thing
the corpus actually lacks: **M100 verified its own work.** Rule 12 forbids
that. The orchestrator then re-ran the bars at HEAD, but the orchestrator
applied the patch and is a party to it — and is the author of the five
confirm-in-general-never-check-the-instance errors folded as facts 1297, 1304,
1324, 1341 and 1347.

**M105b is therefore re-scoped, by me, to an independent verification of the
shipped feature at HEAD, and ships no code.** Four milestones have landed on
the merge since M100 measured (M97's warp, M99's photometric term, M103's
alignment repair, M95's resolution fix), so M100's published choices are
predictions about a binary that no longer exists, and they can fail.

---

## 1. Pre-registered bars

Registered here, committed, **then** run. Every bar names the observation that
fails it. Where I had already seen a number before registering, I say so.

### V1 — the premise (already falsified; registered for the record)

> The brief's claim that no exposure logic exists in the CLI.

**Disclosure per rule 43: I ran this grep before writing this bar**, because
the brief instructed me to verify it first. It is registered as already-FAILED
with the evidence in §0.1, not as an open question. I am not claiming
predictive credit for it.

### V2 — does the shipped chooser still pick M100's number?

`strehl stack D:\personal\macro\bee-3-cpl --srgb --auto-exposure` on all 299
frames must print **+1.54 stops**, the value `M100-exposure.md` §3.4 publishes
for that stack.

* **PASS**: `+1.54`.
* **FAIL**: anything else. A drift of >= 0.02 stops means one of the four
  milestones that landed on the merge since moved the render's luminance
  distribution, and M100's published table is stale.

This bar has power to fail: M99 added a photometric term that rescales frame
brightness, which is exactly the quantity the percentile reads.

### V3 — round-trip identity (independent re-run of M100's B6)

The file written by `--auto-exposure` must be **SHA-256-identical** to the file
written by `--exposure=<the value it printed>`.

* **FAIL** on any hash difference. This is M100's contract for the printed
  number and it is the only thing making the choice reproducible.

### V4 — placebo, and a positive control beside it

The brief requires a placebo. A null-only arm is not evidence (rule 20), so
both arms run.

* **Placebo (must show NO effect).** `--srgb --exposure 0` must be
  SHA-256-identical to plain `--srgb`. FAIL on any difference.
* **Positive control (must show THE RIGHT effect).**
  `--srgb --exposure=1.00` must produce an image whose linear-light values are
  **exactly 2.0x** those of `--srgb --exposure 0`, measured on the unclipped
  population only. PASS if the median ratio is within **0.5%** of 2.000 and the
  interquartile range of the ratio is below **0.01**. FAIL otherwise.

  Registered mechanism for why this can fail: if the gain landed *after* the
  sRGB transfer curve rather than before it, the ratio would not be 2.0 and
  would vary with level — the exact defect `color.rs:524`'s doc comment claims
  is avoided. This control tests that claim against the emitted file rather
  than against the doc comment. **Rule 34 note:** this control shares no
  constant with the code under test — 2.0 comes from the definition of a stop,
  not from `color.rs`.

### V5 — byte-freeze of the measurement path

The brief makes this a hard deliverable. My change is empty, so the
before/after form is vacuous; I register the strongest form still available:

* **V5a.** SHA-256 of `strehl stack D:\personal\macro\bee-3-cpl --limit 60
  --out X` (no `--srgb`, no `--demosaic`) at HEAD `519203f`, recorded as an
  independent second reading for `M106`, which owns the attribution.
* **V5b — the one that is mine.** The same hash from a binary built at
  **`8041ce2`** (the commit *before* M100's patch `925d03d`) must equal the
  hash at `925d03d`. FAIL on any difference, which would mean the exposure
  feature moved the measurement path and every calibrated threshold in the
  corpus is void.

  I expect V5a to differ from M100's published `54A5E20F...`; the `M106`
  ledger row already records that it does. **V5b is a different claim** — it
  asks only whether *this feature* is implicated, and it does so by rebuilding
  both sides rather than by the orchestrator's restore-touch-rebuild
  assurance.

### V6 — is p99.9 dragged by a specular? (the brief's second open question)

The brief's worry: on an insect macro, a specular highlight on chitin lives in
the top 0.1%, so p99.9 may be measuring the specular rather than the subject.

* Measure `p99.99 / p99.9` and `max / p99.9` of linear-sRGB luminance on
  `bee-3-cpl`, with `foam` and `coffee-bean` (already-correctly-exposed, no
  large specular) as contrast cases.
* **The worry is SUBSTANTIATED** if `p99.99/p99.9 >= 1.15` on the bee stacks
  and materially lower on the controls — i.e. the top 0.1% is a steep tail that
  p99.9 is riding.
* **The worry is REFUTED** if `p99.99/p99.9 < 1.15`, i.e. the top 0.1% is
  flat and p99.9 is measuring the same population as p99.5 would.

### What would make me ship code after all

Any of: V2 fails and the drift is large enough that the shipped constants no
longer serve the corpus; V4's positive control fails, meaning the gain is in
the wrong place; V5b fails, meaning the feature broke the freeze. **Absent
those, M105b ships nothing and says why.** Per the brief: *"A milestone that
ships nothing and explains why is a good outcome here."*
