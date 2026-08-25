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

I verified it. **It is wrong, and it changes the whole milestone.** Four
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

MEASURED, `crates/strehl-cli/src/main.rs`, the two match arms at `385` and
`410`:

```rust
Command::ArgmaxBaseline { .. } => stack::run(&StackOptions { .. }),   // :385
Command::Stack { .. } => merge_cmd::run(&MergeOptions { .. }),        // :410
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

### 0.3b A fourth error, small but exactly what rule 38 exists to prevent

The brief cites the M95 resolution fix as `main.rs:349`. MEASURED: at HEAD
`519203f` that rule lives at **`main.rs:405`** and again at **`main.rs:434`**.
The line moved, and there are **two** of them — the rule is deliberately
duplicated into the `argmax-baseline` arm and the `stack` arm, with a source
comment saying why (*"Identical resolution rule to `stack`, and it must stay
identical: the two subcommands are compared against each other, so any
asymmetry here is a thumb on the scale"*).

Both citations still resolve because the brief quoted the *code*
(`demosaic: demosaic || (srgb && !binned)`) alongside the number, which is what
rule 38 asks for; a bare `main.rs:349` would have sent me 56 lines wrong, into
a different subcommand's argument list. The number in a brief decays; the
symbol does not. Worth recording because it is the same class of decay as
§0.2 — a brief describing the tree as it was rather than as it is.

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

### 0.5 The brief was corrected mid-flight, and the correction carries a fifth error

At **10:07**, after this work was measured and committed, the orchestrator
retracted one sentence of the brief — *"I consider it the most likely single
largest contributor to his complaint"* — having established (fact 1344,
discipline 667) that the owner's verdict was passed on
`C:\dev\strehl-out\*.png` from **2026-08-23 23:37–23:39**, not on the gallery,
and that those renders carried **five** defects at once. **That retraction is
correct and I have measured it independently in §4.8.** It does not touch any
bar in this report, because no bar was about the owner's opinion.

The correction also lists what *"does not change"*, and one item does:

> *"**`strehl stack --srgb` emits a render 1.5–3.7 stops dark.** Still true,
> still fact 1293 for the magnitude, still **fact 1339** for the fact that the
> correction is absent from the binary."*

MEASURED. Fact 1339's corrected headline reads **"THE MEASURED EXPOSURE
CORRECTION IS NOT WIRED TO THE COMMAND LINE"**, and fact 1346 reads
**"SHIPPED, TESTED AND UNWIRED, AND M100's PATCH FOR THE WIRING HAS BEEN
SITTING UNAPPLIED"**. Both were true when written and **both are now stale**:

```
$ git log -1 --format='%h %ad%n%s' --date=iso 925d03d
925d03d 2026-08-24 08:19:50 -0700
M100: apply the exposure patch I let sit for hours, and prove it inert

$ git show --stat 925d03d
 crates/strehl-cli/src/main.rs      |  65 +++++
 crates/strehl-cli/src/merge_cmd.rs | 143 +++++++++-

$ git merge-base --is-ancestor 925d03d HEAD   # exit 0
$ rg 'auto_exposure' crates/strehl-cli/src/main.rs
main.rs:182  auto_exposure: bool,
main.rs:418  auto_exposure,
main.rs:438  auto_exposure,
```

The wiring landed at **08:19:50**; the correction re-asserting its absence was
sent at **10:07**, 108 minutes later. Every render in §4 was produced by
driving those flags, so the claim is refuted by the existence of this report's
own results. **Facts 1339 and 1346 need amending in place**, exactly as 1341
was.

This is the fifth error found in this brief and its correction, and it is the
same shape as the first: **a row that was true when written, re-cited later as
though rows do not decay.** Fact 1339 has already been corrected once, in
place, for a different reason. Its *headline* was fixed and its *tense* was
not.

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

---

## 2. The answer, up front

**Nothing was built, because the thing I was sent to build shipped at
`925d03d` and works.** M105b is a verification, and the feature passes every
bar I registered against it -- including the two the brief raised as open
questions, both of which M100 had already answered and one of which I now have
a number for that the corpus did not.

| bar | result |
|---|---|
| **V1** the brief's premise | **FAILED** -- the feature exists; see §0.1. Second dispatch on this stem to be told otherwise |
| **V2** chooser still picks M100's value | **PASS** -- `+1.54` stops on `bee-3-cpl`/299, exactly M100 §3.4, after four milestones landed on the merge |
| **V3** printed flag reproduces the file | **PASS** -- SHA-256 identical, `E400A63A...` |
| **V4** placebo | **PASS** -- `--srgb --exposure 0` byte-identical to `--srgb` |
| **V4** positive control | **PASS** -- `--exposure=1.00` is **2.0000000** in linear light, IQR `8.9e-05`, on 99.997% of pixels |
| **V5a** byte-freeze of the measurement path | **PASS** -- `54A5E20F...` at HEAD `519203f`, **equal to M100's published value** |
| **V5b** rebuild either side of `925d03d` | **SUBSUMED** by V5a, which is strictly stronger; see §4.4 |
| **V5c** sidecar-state hazard *(unregistered, added mid-run)* | **REFUTED by its own control** -- I predicted the freeze was sidecar-dependent and it is not |
| **V6** is `p99.9` riding a specular? | **SUBSTANTIATED in premise, REFUTED in consequence** -- the tail is real and `p99.9` is not on it |

**Added after the 10:07 correction to the brief** (§0.5, §4.8): an independent
numpy recomputation of the exposure deficit from the tool's own emitted file
gives **1.534 stops**, against the shipped chooser's **+1.54** -- **0.006
apart, inside the quantum**. V2 therefore no longer rests on agreement with a
prior report's printed number.

Three findings that are not about exposure:

* **The byte-freeze is intact at HEAD** (§4.4), which contradicts the premise
  `M106` was dispatched on. I hand it three ruled-out mechanisms.
* **`strehl stack` writes into its own input directory** (§4.6) -- already
  known as fact 1296 and discipline 623, which I established *before*
  publishing it as mine. Corroborated independently, with fresh timestamps
  showing the writing is still live, and one disclosure: some of it is me.

---

## 3. Method

One binary, built from a **detached worktree at `519203f`** (`git worktree
add C:\dev\strehl-m105-wt HEAD`) because seven agents hold uncommitted work in
the shared tree and it does not compile. Own `CARGO_TARGET_DIR`. Rule 33:
`cargo build` printed `Compiling strehl-cli v0.0.0` and
`Compiling strehl-raw v0.0.0`, so the artifacts are this revision's.

Renders go to `C:\dev\strehl-out\M105`. Scripts are in
`experiments/M105b-exposure-verify/`; every JSON quoted below is mirrored to
`experiments/M105b-exposure-verify/data/` so a verifier re-runs rather than
re-reads.

**All measurement after §4.6 was moved onto isolated full-depth copies of the
stacks under `C:\`**, once I found the binary writing to `D:`.
`00-isolate.ps1` rebuilds those copies from the read-only sources so the later
scripts are re-runnable; it verifies to `iso60` 60, `iso-coffee-bean` 60,
`iso-foam` 60, `isofull-bee-3-cpl` **299**, `isofull-coffee-bean` **105**,
`isofull-foam` **100** — an independent confirmation of the frame counts §4.7
reports, taken from the filesystem rather than from the render logs. It sorts
by filename because `main.rs`'s `raw_paths` does, so its first *n* are the
same frames `--limit n` selects.

Writing it caught a bug that would have hit a verifier and not me: PowerShell
variable names are case-insensitive, so a loop-local `$src` and the root
`$SRC` are **one variable**, and the first iteration silently rewrote the
source root to `D:\personal\macro\bee-3-cpl`. It threw on iteration two rather
than reading the wrong frames, which is luck, not design. Recorded because the
same shape — a loop clobbering the constant it derives from — reads as a
missing directory rather than as a wrong answer only when the wrong path
happens not to exist.

---

## 4. Results

### 4.1 V2 -- the chooser still picks +1.54 (MEASURED, PASS)

`01-render.json`, `bee-3-cpl`, all 299 frames:

```
exposure        : +1.54 stops (gain 2.908x), chosen from the image
                  rule: linear-sRGB luma p99.9 -> 0.90 on the binned grid (M100).
                  reproduce this exact file with --exposure=1.54
```

`M100-exposure.md` §3.4 publishes `+1.54` for this stack. **Agreement is
exact**, and this bar had real power to fail: M97's warp, M99's photometric
term, M103's alignment repair and M95's resolution fix have all landed on the
merge since M100 measured, and M99 in particular rescales frame brightness,
which is the quantity the percentile reads. It does not move the choice.

**What that means, and the limit of it (DERIVED).** The percentile is taken
after the merge, so any change that preserves the *distribution* of output
luminance leaves the exposure alone. This is evidence that the shipped constants
are robust to merge changes, not that the merge did not change.

### 4.2 V3 -- the printed number reproduces the file (MEASURED, PASS)

```
--auto-exposure   E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112
--exposure=1.54   E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112
```

Independently reproduced on the full 299-frame stack. M100 verified this at
`--limit 60`; this is a different frame count, a different binary and a
different operator.

### 4.3 V4 -- placebo and positive control, side by side (MEASURED, both PASS)

**Placebo (must show no effect).**

```
--srgb              A559616F85CFAF41FF0A9F8C3067C9B8D80F5C52041F56D141CB793A0182CD00
--srgb --exposure 0 A559616F85CFAF41FF0A9F8C3067C9B8D80F5C52041F56D141CB793A0182CD00
```

**Positive control (must show the right effect).** `--exposure=1.00` against
`--exposure 0`, both linearised out of the sRGB encoding, on the 98,895,452
of 98,898,048 samples unclipped in both and above the sRGB toe:

| quantity | value | bar |
|---|---|---|
| median ratio | **1.999 999 967** | within 0.5% of 2.000 |
| relative error | **1.65e-08** | -- |
| IQR of the ratio | **8.94e-05** | < 0.01 |
| fraction of pixels used | 99.997% | -- |

This is the arm that makes the placebo admissible. It tests a claim
`color.rs:524`'s doc comment makes about itself -- that the gain lands in
**linear light, before the transfer curve** -- against the emitted file rather
than against the comment. Had the gain been applied to encoded values, the
ratio would be neither 2.0 nor constant, because the sRGB curve is not
homogeneous. Per rule 34 the control shares no constant with the code it tests:
`2.0` is the definition of a stop.

### 4.4 V5 -- the byte-freeze is INTACT, and M106 was dispatched on a premise I cannot reproduce (MEASURED)

`strehl stack D:\personal\macro\bee-3-cpl --limit 60 --out X`, no `--srgb`,
no `--demosaic` -- the byte-frozen measurement path:

| source | SHA-256 |
|---|---|
| `M100-exposure.md` §3.3, pre-M87 HEAD | `54A5E20F44255BB526C61D4397D239D6F1D26A06D54A8A56FBC944B91B37E7A2` |
| `M100-exposure.md` §3.3, `894f9f7` + patch | `54A5E20F...` (same) |
| **this milestone, HEAD `519203f`** | **`54A5E20F44255BB526C61D4397D239D6F1D26A06D54A8A56FBC944B91B37E7A2`** |
| this milestone, isolated copy under `C:\` | `54A5E20F...` (same) |

**PASS, and it is the same hash M100 published.** Five independent renders in
this milestone land on it, one of them from a copy of the frames at a different
path -- so the stack digest is content-addressed and the render is
path-independent.

**This contradicts the premise of `M106`'s dispatch**, which states that at
`925d03d` the identical command gives `CF266004...`. `519203f` is a
descendant of `925d03d`. I cannot reproduce the break, and I make no claim
about what the orchestrator measured -- `M106` owns the attribution. What I
can hand over is **three mechanisms ruled out**, each with a number:

1. **Sidecar state -- RULED OUT.** §4.5.
2. **`STREHL_ALIGN` -- RULED OUT as the explanation, but it is a live
   hazard.** With `STREHL_ALIGN=off` the same command gives
   `2E0AE672A8CE9BEF0C431040CD871DC2CAD8269B19474B64D9CFD1425C352EDB`. That is
   not `CF266004`, so it is not the cause -- **but an environment variable
   silently moves the byte-frozen path, and it leaves no trace in the command
   line a report would quote.**
3. **M100's exposure patch -- RULED OUT, and by a stronger argument than the
   one I registered.** V5b proposed rebuilding either side of `925d03d`. It is
   unnecessary: HEAD *includes* `925d03d` and reproduces the **pre-M87** hash,
   so every commit from before M87 through `519203f` -- M87's halo work, M95's
   cositing fix, M97's warp, M99's photometric term, M100's exposure patch,
   M103's alignment repair -- is byte-inert on the measurement path.
   **Disclosure: V5b was registered and not run.** It is subsumed, not skipped,
   and I am stating that rather than quietly dropping it.

### 4.5 V5c -- I predicted a hazard and my own control refuted it (MEASURED)

Registered mid-run in `03-sidecar.py`'s docstring, before the run, with the
reading fixed in advance.

**The mechanism I found at source** (`align_cmd.rs:901-953`): `load_or_solve`
uses `<dir>/warpmap.txt` if it parses, matches the stack digest and has
exactly the bracket's frame count; otherwise it re-solves and calls
`map.save(&side)`. **My hypothesis:** the render therefore depends on mutable
state outside the repository, and that -- not any commit -- is what broke the
freeze.

Four arms on an isolated 60-frame copy:

| arm | sidecar before | what the binary did | SHA-256 |
|---|---|---|---|
| **A** cold | none | solved | `54A5E20F...` |
| **B** warm | A's own map | **accepted the sidecar** | `54A5E20F...` |
| **C** cold2 | none | solved | `54A5E20F...` |
| **D** stale | a 30-frame map | rejected, re-solved | `54A5E20F...` |

* **Determinism control (placebo), A == C: PASS.** Without this, nothing else
  on the table is readable.
* **Claim under test, A == B: the hypothesis is REFUTED.** A cached sidecar
  reproduces a fresh solve **byte for byte**. The cache is faithful.
* **Corroborating, D == A: PASS.**

**I was wrong, the pre-registered reading said so, and the useful finding is the
one I did not predict:** the sidecar cache is sound, which is a real property of
`align_cmd.rs` that nothing had checked.

### 4.6 The binary writes into the read-only corpus -- ALREADY KNOWN, and I checked before publishing it

I found this at source mid-run and drafted it as a finding. **It is not new,
and rules 40/43 caught me before this report was committed.** SYNTHESIS fact
**1296** and `M97-warped-merge.md` §11 already record it, with the same
eleven-stack inventory; discipline **623** already prescribes temp-plus-rename;
`M103-halfdrift.md` §9 re-measured it at 08:20 today. **The prior work is the
citation, not this section.** What follows is a second, independent reading
that corroborates it, plus one thing that is mine.

The mechanism, read from source: `align_cmd.rs:951` writes `warpmap.txt` into
the **capture directory** after a solve. Its own comment reads *"Best effort: a
read-only capture directory must not fail the merge"* -- the author expected
the write to fail. It does not: `D:\personal\macro` is read-only by **policy**,
not by permission.

MEASURED here at 09:24, `Get-ChildItem -Force` per rule 14 -- still eleven
stacks, and the timestamps have **moved since fact 1296's 03:12-06:03 window**:

```
bee-2-cpl            40807  03:12:36     lead-1-cpl           17031  04:55:28
bee-3-cpl            40830  09:20:09     leaf-2-cpl           25024  08:53:04
coffee-bean           2098  09:24:21     tweezers-cpl         13918  04:38:35
flat-on-ruler-cpl    11107  04:56:07     flower-bud-alone-cpl 28097  04:37:48
flowers-cpl          24155  04:35:56     lavendar-cpl         40812  04:34:44
foam                 13916  04:57:46
```

**The part that is mine, and it is a disclosure, not a finding.**
`bee-3-cpl\warpmap.txt` at 09:20:09 is me. I destroyed the prior state before
observing it: my first probe's log records rejecting *"a warp map fitted on ...
digest 56d8292576b3fd13, 60 frames"*, so the directory held a **60-frame** map
before I arrived and holds a 299-frame one now. §4.5 establishes the change is
**byte-inert** for any render, so no measurement is corrupted, but it is a
corpus mutation caused by this milestone. `coffee-bean` at **09:24:21** is
**not** mine -- I had not touched that stack -- so the writing is still live and
concurrent.

**The avoidable part.** `merge_cmd.rs:1035` defines `STREHL_WARPMAP`, an
environment variable that redirects the sidecar. M103 used it and said so. I
did not know it existed and instead copied 7 GB of frames to isolate myself.
Both routes work; the env var is the cheap one, and the reason I missed it is
that I went to `align_cmd.rs`, where the *write* is, rather than to
`merge_cmd.rs`, where the *override* is. **DERIVED: an override that does not
live next to the write it overrides will be missed by anyone who finds the
write first.**


### 4.7 V6 -- the specular tail is real, and `p99.9` is not standing on it (MEASURED)

The brief: *"A specular highlight on chitin is exactly the content that lives in
the top 0.1% of an insect macro, and the owner's subjects are insects."*

Three stacks at their **full capture depth**, rendered `--srgb --exposure 0`
from isolated copies, so the tail measured is the capture's own:

| stack | frames | role | `p99.99/p99.9` | `max/p99.9` | **stops from `p99.5` to `p99.9`** |
|---|---|---|---|---|---|
| `bee-3-cpl` | 299 | SIGNAL | **1.1878** | **2.2320** | **0.0309** |
| `foam` | 100 | CONTROL | 1.0264 | 1.0264 | 0.1919 |
| `coffee-bean` | 105 | CONTROL | 1.0044 | 1.0050 | 0.0093 |

**The premise is SUBSTANTIATED.** The bee has a steep tail above `p99.9` --
`1.1878` against `1.0264` and `1.0044` on the controls -- and its
brightest sample is **2.23x** the percentile. There really is a specular
population up there, and it is a property of the insect stack, not of the
render.

**The consequence is REFUTED, and this is the number the corpus did not have.**
A steep tail only matters if a different percentile would choose a different
exposure. It would not: moving the operating point from `p99.9` to `p99.5`
moves the bee's chosen exposure by **0.031 stops**, and to `p99.0` by
**0.045**. That is 2-3 hundredths of a stop, at the scale of the shipped
1/100-stop quantum, and invisible. **`p99.9` sits below the knee, not on it:**
the distribution is flat up to `p99.9` and steepens above, so the statistic is
measuring the subject and the specular is in the top 0.01%.

**And the controls show the proposed cure is worse.** On `foam` the same move
costs **0.192 stops** -- 6.2x the bee's -- because `foam` is a genuinely
near-clipped capture whose distribution is steep in exactly the 99.0-99.9 band.
A lower percentile would be **less** stable across this corpus, not more. That
is a reason to keep `p99.9` that M100's sweep did not state, arrived at from
the opposite direction.

**Disclosed, because it fired against me: my first design was wrong.** I first
matched all three arms at `--limit 60`, reasoning that equal depth removes a
confound. It creates one. `--limit` takes the **first** n frames in capture
order, so 60 of `bee-3-cpl`'s 299 covers only the opening ~20% of the focus
sweep, while 60 of `foam`'s 100 covers 60% -- matched in frame *count*,
mismatched in scene *coverage*, which is the variable that decides whether an
in-focus specular is in the stack at all. It read `p99.99/p99.9` = **1.0051**
on the bee, and would have refuted the brief's worry on the strength of my own
subsampling. Both runs are committed -- `04-percentile.json` is the discarded
one, `04-percentile-full.json` is this table -- and the discarded arm is kept
rather than deleted so the reversal stays auditable. **This is rule 13 in a new
costume: the stimulus could not express the effect, and the null looked like
evidence.**

### 4.8 The artefacts the owner judged, measured directly (MEASURED)

The 10:07 correction asks for a paragraph on what this correction does *not*
fix. I do not republish another agent's measurement as mine (§4.6 is where I
nearly did), so I measured the judged files myself:
`05-judged-artefacts.py`, arms pre-registered in its docstring.

| file | written | pixels | MP | G/R | G/B | luma p99.9 | stops below 0.90 |
|---|---|---|---|---|---|---|---|
| `bee3-full.tif` | 23:37:47 | **3516x2344** | 8.24 | 1.0131 | 1.0113 | 0.3190 | **+1.496** |
| `lavendar.tif` | 23:38:59 | 3520x2344 | 8.25 | 1.0194 | 1.0371 | 0.3319 | **+1.439** |
| `marker.tif` | 23:39:17 | 3520x2344 | 8.25 | 0.9840 | 1.0067 | **1.0000** | **−0.152** |
| *control* `bee3-g0.tif` | 23:47:05 | 3516x2344 | 8.24 | — | — | 0.3291 | +1.452 |
| *control* `bee3-g1.tif` | 23:47:25 | 3516x2344 | 8.24 | — | — | 0.3234 | +1.477 |
| *placebo* `bee-3-cpl-srgb.tif` | 04:34 | **7032x4688** | 32.97 | 1.0177 | 1.0306 | 0.3108 | **+1.534** |
| *placebo* `bee-3-cpl-exposed.tif` | 04:39 | 7032x4688 | 32.97 | 1.0177 | 1.0306 | 0.8627 | +0.061 |
| *placebo* `coffee-bean-exposed.tif` | 04:39 | 7032x4688 | 32.97 | 0.9874 | 1.0423 | 0.9154 | **−0.024** |

**Binning: CONFIRMED, and confirmed the strong way.** `bee3-full.tif` is
3516x2344; the gallery's `bee-3-cpl-srgb.tif` — the *same stack*, rendered
full-resolution — is 7032x4688. **3516 x 2 = 7032 and 2344 x 2 = 4688
exactly.** The halving is established against a *measured* render of the same
capture, not against an asserted sensor size.

**Flat tone: CONFIRMED for 2 of 3, and the third is the interesting one.**
`bee3-full` and `lavendar` sit ~1.5 stops under. **`marker.tif` reads p99.9 =
1.0000 — it is clipping, not dark**, and `captures-needed.md` §22 independently
gives `dry-erase-marker-head-cpl` −0.00 stops of headroom and **3.6726%**
clipped. So **one of the three images the owner was shown was over, not
under.** That is the two-sidedness the brief insisted on, present in the very
artefact the complaint was about, and it is why a brightener would have been
the wrong build.

**An unplanned external check on V2, worth more than the arm that produced it.**
My placebo was mis-specified — I assumed every TIF under `ORCH-gallery/` had
been through the Python post-process, and the directory holds both `-srgb`
(raw tool output) and `-exposed` variants, so the arm swept in the uncorrected
files and read FAIL by construction. The accident is productive:
`bee-3-cpl-srgb.tif` is the tool's own `--srgb` output with **no** exposure
applied, and numpy puts it **1.534 stops** below 0.90. The shipped chooser
prints **+1.54**. **Delta 0.006 stops, inside the 1/100-stop quantum.** V2 no
longer rests on agreement with a prior report's printed number; it rests on an
independent recomputation from the emitted file, in a different language, by an
operator who did not write the chooser. Per rule 34 the statistic is specified
from BT.709 luminance coefficients and `numpy.percentile(method=
"inverted_cdf")`, neither taken from `color.rs`.

> **QUALIFIED BY §4.9, which was measured after this section was written.**
> The chooser reads luminance *before* the `[0,1]` clamp and this file is
> written *after* it, so a post-file recomputation is only valid where the
> chooser's percentile never exceeded 1.0. It does not on `bee-3-cpl`
> (implied **0.309497** against my measured **0.310812**), so the check above
> stands. **It would have been meaningless on `coffee-bean` or `foam` and
> would still have printed a number.** I did not know that when I wrote this
> paragraph.

**Grey cast: NO EVIDENCE, and my instrument is the reason.** I predicted that
"no colour management" would present as *missing white balance* — R and B
depressed relative to G by roughly the `cam_wb` ratios [2631, 1024, 1606]. The
judged files read G/R = 1.013 and G/B = 1.011, i.e. balanced. But the
**colour-managed** gallery render reads G/R = **1.0177**, which is no
different. Global channel means cannot discriminate a grey cast from correct
balance, so this arm returns nothing. **I am not claiming fact 1344 is refuted
on this point; I am saying I could not see it.** A saturation statistic would
be the right instrument and I did not build one.

**Three of five pre-registered readings fired for reasons that were not the
hypothesis, and I am flagging that loudly rather than quietly retuning.**
`BINNING` compared all three judged files against *one* stack's full size;
`GREY_CAST` used a statistic with no discriminating power; `PLACEBO` was
mis-scoped. The original block is kept verbatim in
`05-judged-artefacts.json` as `readings`, the corrected block sits beside it
as `readings_corrected` and is explicitly stamped *"Specified AFTER seeing the
pre-registered arms fire."* The determinism-style control — the 23:47 files
still reading half-resolution ten minutes later — **passed as registered**,
which is the only reason I trust the corrected block at all.

---

### 4.9 Item 5 — reconciling 0.90 and 0.92, and what it exposed (MEASURED)

The 10:22 stand-down asks me to reconcile `gallery.py`'s `TARGET = 0.92`
against `color.rs`'s `AUTO_EXPOSURE_TARGET = 0.90`, and says *"§3 swept five
targets, so the answer is probably already measured"*.

**It is not measured.** MEASURED, `experiments/M100-exposure/sweep.py:31`:

```python
TARGETS = [0.80, 0.85, 0.90, 0.95, 1.00]
```

**0.92 is not in the grid.** The sweep cannot answer the question, and the
premise of item 5 is false in the same way the brief's was — an assumption that
prior work covered a case, made without opening it.

**The two rules differ on four axes, not one.** Read at source,
`gallery.py:113-131` against `color.rs` / `merge_cmd.rs`:

| axis | `gallery.py` | shipped |
|---|---|---|
| target | **0.92** | **0.90** |
| statistic | `np.percentile(lin, 99.9)` with **no `axis=`** — flattens, so it pools R, G and B samples | BT.709 **luminance** via `display_luminance` |
| percentile method | numpy default `"linear"` (interpolated) | nearest-rank, `"inverted_cdf"`, matched deliberately |
| guard | 30-iteration **bisection** against a 0.5% clip budget | none; a single bounded, quantised gain |

M100 swept two statistics — luminance and max-channel. **`gallery.py` uses a
third that was never swept.** So item 5's "one of them is wrong" cannot be
settled by comparing two constants.

#### The decomposition is VOID, by the bar I registered for it

`06-reconcile-targets.py` decomposes the divergence one axis at a time. Its
pre-registered positive control was that my reimplementation of the *shipped*
rule must reproduce M100 §3.4 on the two stacks the gallery shares with that
table. **It FAILED**: `bee-3-cpl` +1.53 against +1.54 (one quantum, tolerable)
but `coffee-bean` **−0.14 against −0.18** — four quanta. My pre-registration
says *"every decomposition below is void"*, so **I am not reporting the
decomposition as a result.** The numbers are in
`data/06-reconcile-targets.json` for a verifier, flagged void.

The fixed-point placebo passed (max |stops| = 0.01 across all seven), so the
instrument is self-consistent. It is just not measuring the shipped rule.

#### Why it failed, and it is not an accident

The failure is one-sided: tiny on the stack that needs **brightening**, large
on the stack that needs **darkening**. MEASURED at source, `merge_cmd.rs`'s
`choose` closure and `image_out`'s order:

```
linear camera RGB --> display_luminance(rgb, matrix) --> p99.9 --> gain
                                                                    |
image_out:        x gain  ->  matrix  ->  CLAMP [0,1]  ->  sRGB curve  ->  file
```

**The chooser reads luminance before the clamp. The file is written after it.**
DERIVED from the rule's own definition (`gain = 0.90 / p99.9`, `gain =
2^stops`, so the percentile the chooser saw is `0.90 / 2^stops`), and checked
in `07-clamp-blindspot.py` against M100 §3.4's seven published choices:

| stack | published | implied chooser `p99.9` | above the clamp? |
|---|---|---|---|
| `lead-1-cpl` | +3.74 | 0.0674 | no |
| `flat-on-ruler` | +1.96 | 0.2313 | no |
| **`bee-3-cpl`** | **+1.54** | **0.3095** | no |
| `bee-2-cpl` | +1.54 | 0.3095 | no |
| `highly-angled-ruler` | +1.19 | 0.3945 | no |
| **`coffee-bean`** | **−0.18** | **1.0196** | **YES** |
| **`foam`** | **−0.32** | **1.1235** | **YES** |

**A post-file instrument is structurally blind to exactly the two stacks that
need darkening** — which is to say, blind to the two-sidedness this milestone
was told to protect. Both pre-registered predictions CONFIRMED (coffee-bean
above the clamp; my error one-sided *brighter*), and both controls PASS
(`bee-3-cpl` below the clamp, and within one quantum).

**Disclosure: `07-clamp-blindspot.py` first ran with the sign inverted**
(`TARGET * 2**stops` instead of `TARGET / 2**stops`) and reported an implied
percentile of **2.617** for a stack that is 1.54 stops too *dark*. **My own
control caught it** — I had registered *"a mechanism that also explains the
stack it should not touch explains nothing"*, and `CONTROL_bee3_below_clamp`
read FAIL. The wrong run is kept as
`data/07-clamp-blindspot-SIGNERROR.json`.

#### This qualifies my own §4.8 external check

§4.8 claimed the numpy recomputation meant *"V2 no longer rests on a prior
report's printed number."* **That is now qualified.** The table above gives
`bee-3-cpl`'s implied chooser percentile as **0.309497**; §4.8 measured
**0.310812** from the file. **0.42% apart, 0.006 stops** — so the check stands
*for this stack*, and it stands because `bee-3-cpl` is one of the five stacks
that never touch the clamp. **On `coffee-bean` or `foam` the same check would
have been meaningless and would still have looked like a number.** I did not
know that when I wrote §4.8.

#### The verdict on `gallery.py`, which is what the owner has been shown

`gallery.py` reads the emitted TIF, so **it inherits the blindness above**. On
`coffee-bean` my reimplementation of its rule returns **−0.120 stops**. And:

```
log2(0.92) = -0.12029
```

**`gallery.py`'s darkening on `coffee-bean` is exactly `log2` of its own
`TARGET`.** That is what a rule returns when its input has been clamped to 1.0
— it is pinned at the hardest rail it can reach, and the value it prints is a
parameter of its own source. **Discipline 616: a number that equals a parameter
of your own code is a bug report.** The shipped rule, reading before the clamp,
chooses −0.18.

So, plainly, as item 5 asks: **`gallery.py` is the odd one out.** Not because
0.92 is indefensible — it was never swept, so nobody knows — but because it
measures the wrong image. It is downstream of a clamp that has already
destroyed the highlights it is trying to protect, and on the two-sided cases it
saturates against its own target. **The recommendation in §7.1 stands and is
now stronger: put the gallery on `--auto-exposure`.** That is not a preference
between two constants; it moves the measurement to the only place in the
pipeline where the information still exists.

---

### 4.10 Sidecar-contamination audit (MEASURED) — prompted by the 10:30 hazard notice

The orchestrator reports `<stackdir>/warpmap.txt` oscillating under seven live
agents, and asks whether any published number used a shared sidecar. **Every
render in this report logged its own alignment provenance**, so this is an
audit rather than an argument. All 18:

| render | frames from | alignment line |
|---|---|---|
| `v2-auto-299` | `D:\...\bee-3-cpl` | **sidecar REJECTED** (map was 60 frames, digest `56d8292...`) → re-solved |
| `v3-repro-299` | `D:\...\bee-3-cpl` | ON (sidecar), ref 149, **299 placed / 0 refused** |
| `v4-exp0/exp1/plain-299` | `D:\...\bee-3-cpl` | ON (sidecar), ref 149, **299 placed / 0 refused** |
| `v5a-linear-60` | `D:\...\bee-3-cpl` | **sidecar REJECTED** (map was 30 frames, digest `4d9a244...`) → re-solved |
| `v5c-A/C`, `v6full-*`, `v6-coffee-bean`, `v6-foam` | isolated `C:\` copies | ON (**solved**) |
| `v5c-B`, `v6-bee-3-cpl` | isolated `C:\` copies | ON (sidecar), written by the immediately preceding arm |
| `v5c-D-stale` | isolated `C:\` copy | **sidecar REJECTED**, planted deliberately — see below |
| `v5d-alignoff` | isolated `C:\` copy | OFF (`STREHL_ALIGN=off`) |

Re-runnable as `08-sidecar-audit.ps1`, which reads only the `.log` files
committed at the time of each render — **written before this hazard was known,
so they cannot have been curated in response to it.**

**No number in this report is contaminated, and the two load-bearing ones are
clean the strong way: both came from renders that *refused* the shared
sidecar and solved fresh.** `v2-auto-299` — the render that produced the
headline **+1.54 stops** — rejected a foreign 60-frame map. `v5a-linear-60` —
the byte-freeze that reproduced M100's published `54A5E20F...` — rejected a
foreign 30-frame map.

The honest exposure surface is four renders: `v3-repro-299` and the three
`v4-*-299` arms consumed the 299-frame map that `v2-auto-299` had just written,
earlier in the same script. I cannot prove no other agent overwrote the file in
that window. Two things bound the risk, and I state both rather than the
comfortable one:

* The guard would have refused any map of a different frame count, and all four
  logged `reference frame 149, 299 placed / 0 refused`. The only undetectable
  substitution is another agent's **299-frame** solve of the same bracket with
  a different resampler, inside a few-minute window.
* **V4's result is differential and therefore immune to that anyway.** Its
  positive control compares `v4-exp1` against `v4-exp0` — two renders sharing
  one registration — and recovers the planted ratio as 1.999999967 over 98.9M
  px. A shared registration cancels. **An absolute measurement rides on the
  sidecar; a differential one does not**, and that distinction is worth more
  than my particular escape from it.

The only `D:` writes I made were to `D:\personal\macro\bee-3-cpl\warpmap.txt`;
**no other stack on `D:` was touched**, because §4.6 moved everything else onto
isolated copies.

**I am the agent who wrote the state observed at ~09:30.** `v2-auto-299`
rejected the 60-frame map and rewrote the file with 299 entries at reference
149 — which is the `ON (sidecar), reference frame 149, 299 placed / 0 refused`
the notice quotes. Disclosed in §4.6 when I found it, before this notice. I
never invoked `strehl align` directly and never used `--limit 40`, so the
`frames 40 / reference 20` state the notice reports is **not** mine.

#### Two corrections to the notice, both measured

**1. Truncated sidecars are NOT silently accepted — they are refused, loudly.**
The notice states *"a stale or partial sidecar does not announce itself"*. My
logs contain three refusals, each printing both digests and both frame counts:

```
alignment      : sidecar rejected (this warp map was fitted on stack "iso60"
                 (digest 4d9a2441fffe4c05, 30 frames) but was applied to
                 "iso60" (digest 56d8292576b3fd13, 60 frames)); re-solving
```

`v5c-D` was a **deliberately planted stale sidecar**, registered in §4.5 as the
positive control for exactly this hazard. It was rejected, and the resulting
render was byte-identical (`54A5E20F...`) to the cold solve. MEASURED, not
inferred: `align_cmd.rs`'s `load_or_solve` accepts only if the map parses, the
stack digest matches **and** `map.len() == paths.len()`.

**2. The real residual hazard is a different one, and it is M95-sharpness's own
variable.** MEASURED at source, `warpmap.rs:194`:

```rust
pub struct StackIdentity {
    pub name: String,      // human diagnostics only
    pub digest: u64,       // FNV-1a over (file NAME, file SIZE) per frame
    pub frames: usize,
}
```

**The guard covers *which frames*. It does not cover *how they were solved*.**
No reference frame, no resampler, no solver parameter is mixed into the digest.
So a sidecar solved at 299 frames with one resampler is **accepted without
comment** by another 299-frame run that wanted a different one — and the notice
itself says 59% of the high-band loss rides on that field. Reference frame
cannot drift (MEASURED: deterministic `floor(n/2)` across all 18 renders —
299→149, 105→52, 100→50, 60→30, 30→15), so **the resampler is the live one.**

**This is the finding to assign, and it is narrower than "make it refuse":**
it already refuses on identity and count. The gap is that **solve parameters
are not part of the identity.**

#### The proposed rule does not cover the incidents it was written for

Rule 1 says never run `strehl align` without `--out`. But the `bee-3-cpl`
oscillation was caused by **`strehl stack`**, whose `load_or_solve` writes the
sidecar as a cache side-effect and which has no `--out` for it. The knob that
works is **`STREHL_WARPMAP`** (`merge_cmd.rs:1035`), which I reported as PD5
before this notice. MEASURED at `merge_cmd.rs:1040-1073`, when it is set:

* it loads the named file and **never calls `load_or_solve`**, so nothing is
  written into the capture directory at all;
* it validates identity **and** frame count;
* it **fails hard rather than re-solving** — the doc comment says why:
  *"silently rendering a different registration than the one requested would
  make every control here unfalsifiable."*

**The two rules compose and neither is sufficient alone:** `align --out
<scratch>` to *create* a private sidecar, `STREHL_WARPMAP` to *consume* it
without writing. I did not use either — I copied 25 GB of frames instead,
because I found the write in `align_cmd.rs` and the override in `merge_cmd.rs`
only afterwards (PD5).

**This is the third independent discovery of this defect.** It is already fact
1296 and discipline 623 (`M97-warped-merge.md` §11, `M103-halfdrift.md` §9);
§4.6 records that I checked before publishing it as mine. **A defect found
three times by three agents is evidence the fix belongs in the tool, not in the
next briefing.**

---

### 4.11 Two corrections from the orchestrator, audited (MEASURED)

#### (a) The `$LASTEXITCODE` trap — my gate is sound, and the trap is not what it says

This milestone has exactly **one** exit-code gate, `01-render.ps1:26`:

```powershell
& $Exe @args 2>&1 | Out-File -FilePath $log -Encoding utf8
$code = $LASTEXITCODE
```

`Out-File` consumes the whole pipeline, so no `StopUpstreamCommandsException`
is ever raised. That is an argument, and an argument about an instrument is
exactly what the notice was burned by, so it was measured instead
(`09-exitcode-trap-v2.ps1`, five arms, positive **and** negative control).

**The first attempt failed honestly and is preserved.** With a 5-line subject
the positive control **did not fire** — the truncated arm read the correct code
— so the script returned `INCONCLUSIVE` (exit 2) rather than a clean bill of
health. A blind instrument returning a null is the failure mode of disciplines
611/615/616, and the guard caught it.

Under a 200,000-line subject the control fires. All arms exit 1 in truth:

| context | small+trunc | big+trunc | big, no trunc | **`Out-File` (mine)** |
|---|---|---|---|---|
| PS 5.1 Desktop, `-File` | **−1** | **−1** | 1 | **1 correct** |
| PS 7.6.5 Core, `-File -NoProfile` | 1 | 1 | 1 | **1 correct** |
| PS 7.6.5 Core, interactive | — | **0** | 1 | — |

**VERDICT: no bar in this report is affected.** The verdict rests on the PS 5.1
row, where the positive control fired *and* the negative control held, so the
instrument both saw the trap and attributed it to truncation.

**Two corrections to the notice, both measured.**

1. **The sentinel is not always 0.** Under PS 5.1 it is **−1**. This matters
   operationally: the recommended `if ($code -ne 0) { throw }` **does still
   fire** on −1, so under 5.1 the standard idiom is not fooled. Only the PS 7
   interactive case produced a genuine false green. **Telling agents the
   symptom is "reads 0" invites `-eq 0`-shaped checks that miss −1.** The safe
   instruction is the one about pipeline shape, not about the value.
2. **It is a race, not a consequence of truncation.** The identical script
   fired on both subjects under 5.1, on **neither** under 7.6.5 via `-File`,
   and on the big subject only when run interactively under 7.6.5. The trap
   needs the upstream to still be **running** when the pipe is torn down; a
   process that has already exited has already recorded its code. **The same
   line can pass and fail on different inputs**, which is worse than a
   deterministic bug and is a reason to prefer the shape fix everywhere rather
   than audit case by case.

#### (b) The sidecar mechanism — the danger is still misplaced, for the third time

Moving to `STREHL_WARPMAP` is right, and is §4.10's P17. But the newly stated
danger — *"a `--limit N` run finds a sidecar that happens to have N frames,
accepts it, and silently uses a solve made from a different subset with a
different reference frame"* — **cannot happen.** MEASURED at source:

* `raw_paths` (`main.rs:451`) does `paths.sort()` **then** `paths.truncate(n)`.
  `--limit N` is therefore a **deterministic sorted prefix**, so two
  `--limit 40` runs on one directory select the *same* 40 files.
* The identity is built from that truncated list (`merge_cmd.rs:1096` feeds
  `paths` to both the solve and `StackIdentity::from_paths`), so the digest
  covers exactly the frames used. A 40-frame sidecar accepted by a 40-frame run
  **is** a solve over the same subset.
* The reference frame is deterministic `floor(n/2)` — measured across all 18
  renders in §4.10 — so a fixed subset implies a fixed reference.

**The gap is a different field, and it is recorded in the file while going
unchecked.** `warpmap.rs:305/336` stores the resampler in provenance, with the
doc comment *"The resampler the solve was validated with."* `check_stack` is
one line — `self.provenance.stack.check(stack)` — comparing **only** name,
digest and frame count. **So the resampler is written into the sidecar and
never validated against the run consuming it.**

---

### 4.12 The 11:27 notice: an external control, and a gap of my own (MEASURED)

#### (a) My `bee-3-cpl` numbers are verified uncontaminated against an EXTERNAL reference

The notice repeats that *"a control cannot catch this — it contaminates
treatment and control identically."* That is true of a **passive** control, where
both arms consume whatever sidecar happens to be present. It is false of a
control that varies the sidecar deliberately (§4.5), and it is false in a
second, stronger way that only became visible when every surviving render was
hashed (`10-freeze-record.ps1`, second pass):

| SHA-256 | render | frames | directory | alignment |
|---|---|---|---|---|
| `A559616F…` | `v4-plain-299` | 299 | `D:\personal\macro\bee-3-cpl` | ON (**sidecar**) |
| `A559616F…` | `v4-exp0-299` | 299 | `D:\personal\macro\bee-3-cpl` | ON (**sidecar**) |
| `A559616F…` | **`v6full-bee-3-cpl`** | 299 | **`C:\…\M105\isofull-bee-3-cpl`** | ON (**solved**) |
| `54A5E20F…` | `v5a-linear-60` | 60 | `D:\personal\macro\bee-3-cpl` | sidecar **rejected** |
| `54A5E20F…` | `v5c-A/B/C/D` | 60 | **`C:\…\M105\iso60`** | solved / sidecar / solved / rejected |

**An isolated copy in private scratch, whose existence no other agent knew of,
cannot have been perturbed by a shared sidecar.** It is therefore an
*uncontaminated external reference* — the thing the notice says is unavailable.
The shared-directory render matches it **byte for byte**, independently at 299
frames and at 60. Same `gate 4.00`, same reference frame, same placed count.

**VERDICT: no number in this report needs retaking.** This is external
verification, not internal consistency, and it also confirms the 25 GB isolated
copies were byte-faithful.

The notice's specific mechanism is refuted for the fourth time. *"Any `stack`
run on `bee-3-cpl` that picked [the 40-frame sidecar] up was merging 40 frames
while believing it had 299"* — a 299-frame run **cannot** pick up a 40-frame
map; `load_or_solve` compares `map.len()` to `paths.len()` and refuses. My own
`v2-auto-299` log is a direct instance, refusing a 60-frame map and re-solving.
The narrow case that *would* accept it, a `--limit 40` run, is **legitimate**:
by P21 `--limit` is a sorted prefix, so a 40-frame map is a correct solve for
those 40 frames. The exposure is the resampler (P21), not the frame count.

#### (b) A gap in my own artefacts, found by acting on the notice — and closed

Acting on *"check any render you took tonight"* surfaced a real defect **in this
report**: bar **V3**'s hash `E400A63A…` was asserted in prose and in the §2
summary table, but **was never retained in any committed data file** — the
first render batch's manifest covers five renders, and V3 was in a later batch.
**That is the M106 failure mode reproduced in my own work**: a hash without the
artefact that would let someone re-derive it.

Closed by hashing the retained render: `v3-repro-299` = `E400A63A…`, **identical
to `v2-auto-299`**, so V3's PASS stands and is now backed by
`data/10-all-render-hashes.json` rather than by my say-so. Had the TIF been
deleted, the bar would have been unrecoverable.

#### (c) The habit is right, but the information was unretained, not unrecorded

`strehl stack` **already prints its own configuration**, including the gate when
the gate is the default:

```
gates           : 4.00  (UNCALIBRATED -- question 90; target is fact 212's nwide = 3)
frames          : 299 from D:\personal\macro\bee-3-cpl
alignment      : ON (sidecar), reference frame 149, 299 placed / 0 refused
```

All 18 logs here carry those lines and all 18 are committed, so every hash in
this report is now attributable to a complete invocation — **all at `gate
4.00`**, stated explicitly rather than implied, per the new habit.

So the M106 incident is not that the invocation was unrecorded; **the tool
recorded it.** It is that milestones committed a hash without committing the
tool's report beside it. **The cheap machine-checkable form of the new rule is
therefore to require the log, and parse the gate out of it, rather than to ask
agents to remember to write the gate down** — a rule that depends on memory
fails the same way the first time someone is tired. Offered to M108-freeze-test;
`10-freeze-record.ps1` is a working sketch, and it exits non-zero when any
record lacks directory, frame count or gate.

#### (d) The M86c watershed does not move anything here, and corroborates §5.1

`885e9f7` is `2026-08-24 03:15:23 -0700` (MEASURED, `git show -s`).

* **Unaffected.** Every render in this report was built at HEAD `519203f`, and
  the M100 hash V5a reproduces was published at `894f9f7`, `05:55:29` — **both
  after the watershed**. V5a is a comparison between two post-M86c points, so
  the alignment change is upstream of both sides and cancels.
* **Corroborated.** The artefacts §4.8 measured are timestamped
  `2026-08-23 23:37–23:47`, roughly 3.5 hours **before** alignment was wired
  into `strehl stack` at all. §5.1 listed "no alignment" as the fourth of five
  defects on the authority of a turn description; **it is now established by
  commit timestamp** — those renders *could not* have been aligned, because the
  code path did not exist when they were written. That upgrades §5.1's defect 4
  from ARGUED to DERIVED.

---

### 4.13 Self-audit against discipline 702 (MEASURED)

The 11:34 notice closes with *"worth checking against any harness you have built
this session that reports through stdout."* Two checks, both run rather than
reasoned about.

**(a) Encoding — immune, and verified in the failing mode.** All 11 committed
scripts are pure ASCII, and so is every `.log` they parse, so nothing here can
emit a character cp1252 cannot encode. Confirmed empirically rather than by
inspection: `07-clamp-blindspot.py` under `PYTHONIOENCODING=cp1252` with stdout
**piped** produced `rc=0`, 29 lines, 0 tracebacks — identical to the `utf-8`
arm. Worth noting that the brief's standing instruction to export
`PYTHONIOENCODING=utf-8` before every python call would have masked this defect
for me regardless: **an environment workaround written into a brief can hide a
tool defect from the very agents positioned to find it.**

**(b) Exit-code contract — one of my own harnesses had the defect.**
Discipline 702's second half is that a gate must distinguish *tool failure* from
*subject failure*. Audited:

| harness | before | after |
|---|---|---|
| `09-exitcode-trap-v2.ps1` | already 0 / 1 / **2 = INCONCLUSIVE** | unchanged |
| **`10-freeze-record.ps1`** | **`throw` → 1 and incomplete-record → 1: ambiguous** | 0 / 1 / 2 |

`10-freeze-record.ps1` is a gate — it exits non-zero when a freeze record lacks
directory, frame count or gate — and until now a missing input file and a
defective record produced the **same exit code**, which is exactly the ambiguity
that made the linter's silence unreadable. Fixed with a script-scope `trap`:

* `0` every record complete
* `1` **SUBJECT** failure, naming each incomplete record
* `2` **TOOL** failure, stating explicitly that it is *not* a verdict

Both failure arms were exercised under **piped** stdout, in an isolated probe
directory so no committed artefact was disturbed: tool arm `rc=2`; subject arm
`rc=1` reporting `fake-render: missing gate`, the precise case the new habit
exists for; healthy arm `rc=0`. `09` already carried a three-state contract,
built for §4.11(a) before the discipline was written, which is why its
INCONCLUSIVE verdict was available to be returned at all.

### 4.14 The withdrawn triage rule, re-derived for this estimator (MEASURED)

The orchestrator withdrew the absolute-vs-ratio triage rule after three
independent refutations and asked anyone resting on it to re-derive. This
milestone rested on it implicitly, so it is re-derived here from scratch.

**Answer up front, in three parts.** (i) The estimator is **clear**: the
reported exposure does not move until the data is narrowed to **8 bits, six
below the sensor's actual 14**. (ii) **No clearance in this report ever used a
differencing noise estimate** -- every control is a SHA-256 identity or an
integer dimension, neither of which estimates anything. (iii) But **my
pre-registered reasoning for (i) was refuted by my own measurement**, and one
of my two methodological predictions was simply wrong. Both are reported below
in preference to the favourable half.

Pre-registration committed at `7694309` and `dcb9e8d`, each **before** its run.
Scripts `11-quantisation-exposure.py`, `12-crossover-check.py`.

#### (a) Where the perturbation actually lands

The shipped rule (`color.rs:758-796`) is
`stops = round_100(clamp_6(log2(TARGET / p)))` with `p = percentile(luma, 99.9)`.
Expanding rather than triaging by shape: there is exactly **one measured term**,
and it is an **order statistic** -- the value at rank `k = nearest_rank_index(N,
99.9)`. `TARGET` is a compile-time constant carrying no error. So a perturbation
`e` lands in `p` and nowhere else, giving `dstops = -log2(1 + dp/p)`. The
perturbation is divided by `p`, **not** by the sample count: averaging does not
help, and the number of frames is irrelevant.

The load-bearing claim is that order statistics are **1-Lipschitz in sup-norm**,
so `|dp| <= max_i |e_i|` regardless of whether the perturbation is monotone.
Pre-registered as P-A and falsifiable. **CONFIRMED in all 28 dose-by-arm-by-
subject cells.**

#### (b) The three refutations, mapped onto this estimator

* **V-M113 (value vs position).** My statistic reads a pixel **value**, at a
  rank. I am in the **exposed** class and do not get to claim location-statistic
  dithering. But M113's threshold is *~12 distinct levels per fitted window*,
  and this statistic **fits nothing and has no window**. Measured for
  comparability: the 10,000-sample neighbourhood of the rank holds **9,198
  distinct levels** (linear subject) and **8,503** (sRGB subject) -- roughly
  **700x** above the threshold at which M113's immunity ends.
* **M111 (term disparity `D`).** `D` is **undefined** here: there are not two
  measured terms to be disparate. This is a genuine structural difference from
  the fleet's defect-detection contrasts -- and because structural argument is
  exactly what was withdrawn, it is recorded as a reason to *expect* a small
  number, never as a substitute for measuring one.
* **M115 (a common floor factorises into the noise factor).** There is no noise
  term for a floor to attach to. The honest translation is not immunity but
  **bias**: quantisation inflates variance, variance widens the upper tail, and
  p99.9 lives in the upper tail.

#### (c) The ladder, and the controls that make it readable

All three controls pass on both subjects. `C-NULL`: dose zero gives exactly
`0.0`. `C-POS`: a planted gain of 0.5 recovers `+1.0000` stops and 2.0 recovers
`-1.0000`, both exact. `C-RESPONSIVE`: at 4-bit the estimator moves `-0.03`
(linear) and `-0.02` (sRGB) stops, more than the reporting quantum -- so the
nulls below are a quiet instrument rather than a dead one, which is the
distinction the `STREHL_FIX_CA` notice turns on.

At the pipeline's two real steps -- 16-bit output `q = 1.526e-05` and 14-bit ARW
over black 512 / white 16383 `q = 6.301e-05` -- **`dstops = 0.0000` in both arms
on both subjects**. The first movement of the reported number appears at
**8-bit** on the linear render and **6-bit** on the sRGB render. Against a real
14-bit sensor that is **six bits of headroom**, and the margin is not marginal.

**Threat, stated before measuring and still live:** the renders on disk are
16-bit TIFs, so "dose 0" already sits on a `q0 = 1/65535` floor. The 16-bit row
is *at* that floor and is confounded; it is not read. The 14-bit row and coarser
are clean.

#### (d) Two numbers that did not fit, chased rather than rounded off

**Anomaly 1.** On the linear subject, 6-bit and 4-bit returned `dp = +5.942e-03`
**identical to four significant figures** from quantisers whose steps differ by
4.2x. Two doses cannot honestly give one answer. Mechanism, confirmed: `p0 =
0.32739154` rounds onto `21/63` and onto `5/15`, and **both are exactly 1/3**.
It is a coincidence of the grids, not of the code. The sRGB subject, whose `p0 =
0.593`, lands on `0.587302` and `0.600000` and shows no such coincidence -- it
is the negative control, and it behaved. *(Script `12` labels that outcome
`FALSIFIED` for subject 2, which is a **defect in my reading logic**: it applies
a subject-specific hypothesis verbatim to the control. The label is wrong; the
data is right. Recorded rather than silently reinterpreted.)*

**Anomaly 2.** The arm ordering **inverts at the coarsest doses**, on both
subjects. Script `11` aggregated this as "6 rows of 7, CONFIRMED", which hides a
crossover at the extreme of the ladder. The dense ladder discriminates: dither
dominates over a **contiguous** coarse range (bits 3-5 linear, bits 3-4 sRGB)
and quantisation dominates at every finer depth. The mechanism is visible in the
fraction of the Lipschitz bound each arm attains: **dither falls monotonically
from 0.81 at 3-bit to 0.009-0.12 at fine depths**, while **quantisation stays
scattered between 0.16 and 0.97 throughout**. Independent zero-mean error
averages out over the ~8,241 samples above the rank; error that is deterministic
in the pixel value moves that whole population together and does not.

#### (e) The fleet headline reproduces here, and my stated reason for it was wrong

I pre-registered (P-B) that the orchestrator's 16x result **should not**
reproduce, on the grounds that "a rank statistic is not a noise estimator, so
that mechanism has nothing to act on."

**The ordering I predicted was confirmed and the reason I gave for it was
refuted.** At the 14-bit dose, quantisation displaces the percentile **79x
further** than matched-RMS dither on the linear subject and **79x** on the sRGB
subject. That is the same phenomenon, larger: correlated error survives
averaging and independent error does not, and this is **not specific to
differencing estimators at all**. The practical consequence is identical in
direction -- **modelling quantisation as equal-power random dither under-states
its effect** -- and it under-states it here by about the same factor the
orchestrator measured for a completely different instrument.

**The number I am not quoting, and why.** Larger ratios are available: the
16-bit rows give 6.4x (linear) and **336x** (sRGB). The 336x is **not
trustworthy** and I decline to headline it -- at that dose the dither
displacement is `7.451e-09`, which is **0.2 of one float32 ulp** at `p = 0.593`
(`ulp ~ 3.5e-08`). It is measuring the representation, not the perturbation.
The 14-bit linear row survives this check at 13.6 ulps; the 14-bit sRGB row is
marginal at 2.1 ulps and is quoted only because the linear row agrees with it.

#### (f) A caveat I raised against the replacement guidance, refuted by my own data

I pre-registered a methodological objection: that for a **rank** statistic under
**quantisation**, a dose-response control would be **non-monotone by
construction**, because `|dp|` is the distance to the nearest grid point -- a
sawtooth in `q`, not a growing function of it. If true, an agent fitting a
monotone slope would read flatness as immunity.

**Falsified by measurement.** Spearman rho of `|dp|` against `q` is **0.9736**
(quant) versus **0.9824** (dither) on the linear subject, and **0.9868** versus
**0.9912** on the sRGB subject -- gaps of **0.0088** and **0.0044** against a
pre-registered threshold of 0.15. Both arms respond to dose alike. The sawtooth
is real but lives in the *normalised* quantity: `q` spans four orders of
magnitude and swamps it. **The replacement guidance needs no caveat from me: a
dose-response control is valid for this class of statistic.** The weaker true
statement is that the sawtooth is visible if the scale-free ratio `|dp|/(q/2)`
is plotted instead, and an agent whose ladder covers less than a decade of dose
could see scatter rather than slope.

#### (g) The differencing-estimator audit

Grep of all twelve scripts and every committed log for `split|half|diff|noise|
sigma|std|var|residual`: **no differencing noise estimator appears anywhere in
this milestone's instruments.** The controls are SHA-256 byte identity, integer
image dimensions, and order statistics. A hash does not estimate a quantity, so
it cannot mis-estimate one by 16x; this clearance survives the withdrawn rule
because it never depended on a statistic at all.

**One dependency is not mine to clear and is flagged rather than folded.** Every
render in this report was produced through the merge's own noise gate, whose
printed banner reads `gate unit : 0.021516 = sqrt(2) * FOCUS_NOISE_SD, the SD of
a difference`. That is a differencing-derived constant, and the orchestrator's
finding is precisely that such estimators book correlated quantisation error as
signal. Whether `FOCUS_NOISE_SD` was calibrated on narrowed data is a question
for the owner of `merge.rs`, which this milestone is forbidden to open.

#### (h) The `STREHL_FIX_CA` nesting hazard, applied to this feature

The notice warns that a structurally inert gate and a measurably useless gate
return the same number. This milestone's V2 bar has exactly that shape -- "a
gain of 1.0 must be bit-identical" -- so it is audited both ways.

*Read at source*, which the notice says is the only thing that settles it:
`merge_cmd.rs:3358-3398` places `// ---- exposure ----` at the **top level of
the writer**, with **no alignment conditional anywhere around it**. It cannot be
made inert by `STREHL_ALIGN=0`. Further, the no-op path **announces itself** --
`Exposure::Auto` falls back through an explicit
`eprintln!("--auto-exposure found no positive luminance; leaving it alone.")` --
and the report line fires on `!applied.is_identity() || applied.automatic`, so
an automatic run that chooses a gain of 1.0 **still prints**. M100 designed
against this hazard before it was named; the credit is theirs.

*Confirmed by hash*, independently of the code read: `v4-exp1-299`
(`A4FABFEB...`) differs from `v4-exp0-299` and `v4-plain-299` (both
`A559616F...`), so the flag is live and reaches the writer; and `v2-auto-299`
equals `v3-repro-299` (`E400A63A...`), so the auto round-trip token reproduces
its own render byte-for-byte.

**The arm I did not run:** `STREHL_ALIGN=0 --srgb --auto-exposure`. The code
read is dispositive by the notice's own criterion and the worktree is gone, so
this is stated as a limit rather than covered.

#### (i) External corroboration, from a measurement made for another purpose

`merge_cmd.rs:3360` records that M100 measured the same percentile on the
**binned** and **demosaiced** grids of one stack: **0.322559** and **0.322549**,
`dp = 1.0e-05`, described there as "the same answer to 1/100 stop". An entire
change of image formation moves the percentile by `1.0e-05`; 16-bit
quantisation moves it by `6.05e-06`. That is an independent, pre-existing bound
on this exact question, taken by a different milestone for a different reason,
and it agrees.

---

## 5. Where this correction lies

The thing being corrected is a **viewing** transform, and it is worth being
exact about where it sits, because the project has one hard boundary running
through this area.

```
CFA u16  ->  election + gated mean  ->  linear camera RGB  ->  [ WRITE ]   <- byte-frozen measurement path
                                                    |                         every corpus threshold lives here
                                                    v
                                          x 2^stops  (exposure)              <- M100, and the subject of this milestone
                                                    |
                                          camera -> sRGB matrix
                                                    |
                                          clamp to [0,1]
                                                    |
                                          sRGB transfer curve  ->  [ WRITE ]  <- the viewing render
```

Three properties of that placement, each of which this milestone tested rather
than assumed:

1. **It is downstream of every measurement.** `Exposure::resolve` refuses
   without `--srgb` (`color.rs:471`), so the linear file cannot be
   rescaled. V5a confirms the frozen hash is unmoved at HEAD.
2. **It is upstream of the transfer curve**, which is what makes it an
   *exposure* rather than a brightness slider. V4's positive control measures
   this on the emitted file at `2.0000000`.
3. **It is exposure only** -- one scalar multiply, no tone curve, no black
   point, no per-channel term. So a render that has had it applied is still a
   faithful render of the capture, differing by a number the tool prints.

### 5.1 What this correction does not fix — required by the 10:07 correction

**Exposure was one of five defects in the images the owner judged, and nothing
in this report ranks the five.** Fact 1344 establishes, and §4.8 confirms by
direct measurement, that the verdict *"those stacks don't look too good yet"*
was passed on `C:\dev\strehl-out\*.png` of 2026-08-23 23:37–23:39. Those
renders carried, simultaneously:

1. **Binning to half linear resolution** — MEASURED here: 3516x2344 against
   the same stack's 7032x4688, exactly half per axis. M95 has since fixed it.
2. **No colour management** (the grey cast). Present per the session record;
   **my instrument could not see it** (§4.8) and I do not confirm it.
3. **Flat tone / underexposure** — MEASURED here at **+1.496** stops on
   `bee3-full.tif`. This one, and only this one, is what M100's correction
   addresses. On the third judged file it is **−0.152**, the wrong way.
4. **No alignment.** Per the session record; M97/M103's work is on this and is
   not yet shipped.
5. **The halo** tracing every leg, claw and antenna — fact 1342's three
   components, unexplained and unfixed.

So the honest statement of scope is: **this milestone's subject is one of five,
it is the only one of the five already shipped and tested, and its share of the
owner's dissatisfaction is unknown and unmeasured by me.** The retracted
sentence claimed it was the largest contributor. I have no evidence for that
ranking and I am not supplying any; §4.8 establishes only *presence* and
*magnitude*, not *rank*.

**And it must not be confused with the capture-side deficit, which it resembles
numerically and does not touch.** `docs/captures-needed.md` §22 measures
**+1.69 stops** of unused sensor headroom on `bee-3-cpl` with 0.0000% clipped;
this milestone's display correction on the same stack is **+1.54**. They are
0.15 stops apart and they are *not the same quantity*, though the first largely
causes the second:

| | what it is | what it buys | SNR |
|---|---|---|---|
| §22, capture | expose 1.69 stops brighter at the sensor | **3.23x more photons** | **x1.80** (sqrt of the photon ratio) |
| here, display | multiply the render by 2^1.54 | the same photons, presented correctly | **x1.00 — exactly none** |

DERIVED, from Poisson statistics and not from any strehl constant: digital gain
scales signal and shot noise by the same factor, so it moves SNR by 1.00; a
longer exposure scales the signal by *g* and the shot noise by sqrt(*g*), so it
moves SNR by sqrt(*g*). **A gain of +1.54 stops recovers appearance and
recovers no information whatsoever.** Fact 1257's median +2.01 stops across 23
stacks — 4.04x the photons, ~2.0x the SNR — is a strictly larger and strictly
different lever, it is a request already made to the owner, and **no software
in this repository can substitute for it.** Nothing in this report should be
read as recovering any part of it.

---

## 6. Threats to validity

1. **V2's agreement could be luck of a coarse quantum.** The choice is
   quantised to 1/100 stop, so two renders differing by up to 0.7% in the
   percentile print the same number. MEASURED mitigation: the *gain* is also
   printed and reads `2.908x`; `2^1.54 = 2.9079`. But this bar cannot
   distinguish "unchanged" from "changed by less than half a quantum".
   **Partly retired after the 10:07 correction:** §4.8's numpy recomputation
   reads the underlying quantity as **1.534** in continuous units, so the
   agreement is no longer only visible through the quantum.
2. **V4's positive control tests placement, not calibration** (rule 34). It
   proves the gain multiplies in linear light before the curve. It says nothing
   about whether `AUTO_EXPOSURE_TARGET = 0.90` is the right target -- that is
   M100 §3.2's sweep and I did not re-run it.
3. **V5a is one command on one stack.** M100's freeze is defined by
   `bee-3-cpl --limit 60`, so that is what I measured. A break confined to
   another stack or another frame count would not appear here, and I make no
   claim beyond the single command.
4. **V5c's arms share a solver.** A == B shows the *cache* is faithful. If the
   solver itself were sensitive to something I did not vary, all four arms
   would move together and the table would still read PASS. The determinism
   control bounds this only for repeated runs in one environment.
5. **V6 rests on three stacks and one insect.** `bee-3-cpl` is the only
   SIGNAL arm. The tail statistic is a property of a subject, and one subject is
   not a population; `bee-1-cpl` and `bee-2-cpl` were available and I did
   not render them. The sensitivity number (0.031 stops) is the robust half of
   the result; the 1.1878 is the fragile half.
6. **I could not check what `M106` measured.** My §4.4 says only that I cannot
   reproduce the break at `519203f`. If the orchestrator's `CF266004` came
   from a binary, a stack state, or an environment I did not replicate, my PASS
   and their FAIL are both true and about different things.
7. **The prior state of `bee-3-cpl\warpmap.txt` is gone** and I am the reason.
   §4.5 shows this cannot have moved any render's bytes, but the argument is
   from a control on a copy, not from the destroyed file itself.
8. **Three of §4.8's five pre-registered arms fired for reasons that were not
   the hypothesis**, and their corrected replacements were specified *after*
   seeing the originals fire. Both blocks are committed and the corrected one
   is stamped as post-hoc inside the JSON. Weight §4.8's binning and tone
   results on the raw numbers a verifier can re-read — 3516x2344 against a
   measured 7032x4688; `p99.9` of 0.3190, 0.3319, 1.0000 — and not on my
   readings of them. The grey-cast arm is NO EVIDENCE and should not be counted
   in either direction.
9. **§4.8 measures three files from one evening.** It establishes that the
   judged artefacts were binned and mostly dark. It does **not** establish
   which of the five defects drove the verdict, and I make no such claim; see
   PQ4.

---

## 7. What I built, and what I did not

**I built nothing, and that is the deliverable.** No file under `crates/` was
opened for writing by this milestone. `crates/strehl-cli/src/exposure.rs` --
the file the brief told me to create -- **must not be created**: it would be a
second implementation of a shipped, tested feature, and the failure mode of
that is not a compile error, it is two exposure rules in one binary.

**No patch is proposed for `main.rs` or any other file the brief reserves.**
The brief requires a verbatim patch section; there is nothing to patch.

### 7.1 The one decision still open, and it is the orchestrator's

`M100-exposure.md` §3.6 recommends **against** defaulting `--auto-exposure`
on with `--srgb`, and explicitly hands the decision up: *"The orchestrator
decides; the flag is implemented either way, and switching the default is a
one-line change at the `Exposure::resolve` call site."* That decision appears
never to have been taken -- the brief re-raises it as an open question, which is
itself evidence it is still open.

**I agree with M100's recommendation, and I can now add a measurement it did
not have.** Its case rests on the asymmetry of the mistake, which is an ARGUED
claim. §4.7 supplies a MEASURED one on the other side of the ledger: on
`bee-3-cpl` the automatic rule gives `max/p99.9 = 2.232`, so putting
`p99.9` at 0.90 drives the brightest specular to ~2.0 in linear light and
**clips it by design**. That is correct behaviour for a viewing render and
wrong for a default, because a default that silently clips a highlight is a
default that quietly disagrees with the file it came from.

**If the orchestrator wants the owner to stop seeing dark renders, the cheap
fix is not a default -- it is gallery.py.** MEASURED: `gallery.py:63`
invokes `[EXE, "stack", src, "--out", dst, "--srgb", "--demosaic"]`, with no
`--auto-exposure`, and then re-implements the exposure in Python at
`gallery.py:115-131` with its own `TARGET = 0.92` and a 30-iteration
bisection against `CLIP_BUDGET = 0.005`. So the gallery the owner actually
looks at is **not exercising the shipped rule at all**, and the two rules do
not agree: 0.92 against the shipped 0.90 is 0.032 stops, and fact 1293 puts the
cliff between 0.90 and 0.95. `experiments/ORCH-drift-check/` is not mine, so
this is a recommendation and not a change:

* replace the Python exposure block with `--auto-exposure` and read the
  printed stops out of stderr;
* drop `--demosaic`, which M95's resolution rule has made redundant under
  `--srgb` (`demosaic: demosaic || (srgb && !binned)`).

That puts the owner's gallery on the shipped, tested, reproducible rule without
changing any default and without invalidating a single published render.

### 7.2 Ledger patch (rule 41) -- for the orchestrator to apply

`AGENTS.md`'s allocation ledger has an `M105` row for the stood-down
dispatch and none for this one. I must not edit `AGENTS.md`. Verbatim row to
insert immediately after the existing `M105` row:

```
| M105b | **RE-DISPATCHED ON THE SAME FALSE PREMISE THE M105 ROW ALREADY RECORDS.** Sent to build exposure into the CLI, told *there is no exposure logic in the CLI at all*, and told to write crates/strehl-cli/src/exposure.rs. Both claims were already refuted in writing -- by the M105 ledger row and by fact 1347 -- before the brief was sent. Told to assume the brief contained an error and find it; it did, and found two more. Re-scoped by the agent to an independent verification of the shipped feature, since M100 verified its own work and rule 12 forbids that. | docs/research/M105b-exposure-ship.md, experiments/M105b-exposure-verify/ | **reported. VERDICT: NOTHING TO BUILD; THE FEATURE PASSES EVERY BAR.** --auto-exposure still chooses **+1.54** on bee-3-cpl/299 -- exactly M100's published value -- after M95, M97, M99 and M103 all landed on the merge. Round trip byte-identical; placebo byte-identical; and the positive control reads the gain at **2.0000000 with IQR 8.9e-05** in linear light, testing color.rs's placement claim against the emitted file rather than its doc comment. **The byte-freeze is INTACT at HEAD** (54A5E20F..., five renders, one from a copy at a different path), which **contradicts the premise M106 was dispatched on**; it hands M106 three ruled-out mechanisms including a measured STREHL_ALIGN=off hash. **Its own registered hypothesis was refuted by its own control**: it predicted the freeze depended on sidecar state and measured a cached sidecar reproducing a fresh solve byte for byte. Answered the brief's p99.9 question with a number the corpus lacked -- the bee's specular tail is **real** (p99.99/p99.9 = 1.1878 against controls at 1.0264 and 1.0044) and **irrelevant**, because moving the percentile to p99.5 moves the exposure **0.031 stops**, while the same move costs foam **0.192**, so the proposed cure is worse. **Disclosed a discarded first design of that arm** whose --limit 60 matching confounded frame count with scene coverage and would have refuted the worry on its own subsampling. Corroborated fact 1296 after checking it was not new, and disclosed that it mutated bee-3-cpl/warpmap.txt itself. Recommends putting gallery.py on the shipped flag rather than changing any default. |
```

---

## 8. Proposed corpus entries

Numbered `P1..` per rule 28. Absolute numbers belong to the orchestrator at
fold time. Rule 44: I have diffed these against the rows this milestone already
has, which is none, and against facts 1253, 1257, 1293, 1296, 1347-1349.

### Facts

* **P1 (MEASURED).** **THE SHIPPED AUTO-EXPOSURE STILL CHOOSES M100'S NUMBER
  AFTER FOUR MILESTONES LANDED ON THE MERGE.** At HEAD `519203f`,
  `strehl stack bee-3-cpl --srgb --auto-exposure` on all 299 frames prints
  **+1.54 stops, gain 2.908x** -- exactly the value `M100-exposure.md` §3.4
  published, across M95's resolution fix, M97's warp, M99's photometric term
  and M103's alignment repair. *Implication:* the exposure rule is robust to
  merge changes because it reads the output luminance distribution, which those
  changes preserve; and M100's published per-stack table is not stale. The bar
  cannot resolve a change smaller than half the 1/100-stop quantum.
* **P2 (MEASURED).** **THE EXPOSURE GAIN IS EXACTLY 2.0x IN LINEAR LIGHT,
  VERIFIED ON THE EMITTED FILE RATHER THAN ON ITS DOC COMMENT.**
  `--exposure=1.00` against `--exposure 0`, both linearised out of sRGB:
  median ratio **1.999 999 967**, relative error **1.65e-08**, IQR **8.94e-05**,
  over 98,895,452 of 98,898,048 samples. *Implication:* `color.rs:524`'s claim
  that the gain lands before the transfer curve is now measured, not argued. Had
  it landed after, the ratio would be neither 2.0 nor constant, because the sRGB
  curve is not homogeneous. Per rule 34 the control shares no constant with the
  code: 2.0 is the definition of a stop.
* **P3 (MEASURED).** **THE BYTE-FROZEN MEASUREMENT PATH IS INTACT AT HEAD
  `519203f` AND REPRODUCES M100'S PRE-M87 HASH.**
  `bee-3-cpl --limit 60`, no `--srgb`, gives
  `54A5E20F44255BB526C61D4397D239D6F1D26A06D54A8A56FBC944B91B37E7A2` -- the
  value `M100-exposure.md` §3.3 records for a pre-M87 binary -- across five
  renders, one from an isolated copy at a different path. *Implication:* every
  commit from before M87 through `519203f` is byte-inert on the measurement
  path. **This contradicts the premise `M106` was dispatched on** and should
  be reconciled before that milestone attributes a break to a commit.
* **P4 (MEASURED).** **A CACHED WARP SIDECAR REPRODUCES A FRESH SOLVE BYTE FOR
  BYTE, REFUTING THIS MILESTONE'S OWN REGISTERED HYPOTHESIS.** Four arms on an
  isolated copy -- no sidecar, the cache just written, no sidecar again, and a
  frame-count-mismatched sidecar -- all give `54A5E20F...`. The
  no-sidecar-twice arm is the determinism control and passed first.
  *Implication:* `align_cmd.rs`'s cache is faithful, so sidecar state is ruled
  out as an explanation for any render discrepancy. I predicted the opposite and
  the pre-registered reading fired against me.
* **P5 (MEASURED).** **AN ENVIRONMENT VARIABLE SILENTLY MOVES THE BYTE-FROZEN
  RENDER AND LEAVES NO TRACE IN THE COMMAND LINE.** With `STREHL_ALIGN=off`
  the frozen command gives
  `2E0AE672A8CE9BEF0C431040CD871DC2CAD8269B19474B64D9CFD1425C352EDB` instead
  of `54A5E20F...`. *Implication:* a hash quoted beside a command is not
  reproducible unless the environment is quoted too. Not the cause of `M106`'s
  orphan hash, which is a different value.
* **P6 (MEASURED).** **THE SPECULAR TAIL ON AN INSECT MACRO IS REAL AND
  `p99.9` IS NOT STANDING ON IT.** At full capture depth, `bee-3-cpl` has
  `p99.99/p99.9` = **1.1878** and `max/p99.9` = **2.2320**, against
  `foam` 1.0264 and `coffee-bean` 1.0044. But moving the operating
  percentile from `p99.9` to `p99.5` moves the chosen exposure by only
  **0.031 stops** (to `p99.0`, 0.045), because the distribution is flat below
  `p99.9` and steepens above it. *Implication:* the shipped statistic is
  robust to the exact worry raised against it, and the proposed cure is worse --
  the same move costs `foam` **0.192 stops**, 6.2x more, so a lower percentile
  is *less* stable across this corpus. A reason to keep `p99.9` that M100's
  sweep did not state.
* **P7 (MEASURED).** **THE OWNER'S GALLERY DOES NOT USE THE SHIPPED EXPOSURE
  RULE.** `gallery.py:63` invokes `stack ... --srgb --demosaic` with no
  `--auto-exposure`, then re-implements exposure in Python at lines 115-131
  with `TARGET = 0.92` and a 30-iteration bisection against
  `CLIP_BUDGET = 0.005`. The shipped rule uses `0.90` and no bisection --
  **0.032 stops apart**, with fact 1293's cliff between 0.90 and 0.95.
  *Implication:* the renders the owner judges are produced by an unversioned
  script, not by the tested binary path, so a defect in either would not show up
  as a disagreement.
* **P8 (MEASURED).** **FACTS 1339 AND 1346 WENT STALE AT 08:19:50 AND WERE
  RE-CITED AS CURRENT AT 10:07.** `925d03d` (*"M100: apply the exposure patch I
  let sit for hours, and prove it inert"*, 2026-08-24 08:19:50 -0700, ancestor
  of HEAD) added 65 lines to `main.rs` and 143 to `merge_cmd.rs`, including
  `auto_exposure` at `main.rs:182`, `:418`, `:438`. Fact 1339's corrected
  headline still reads *"IS NOT WIRED TO THE COMMAND LINE"* and 1346 still
  reads *"UNWIRED [...] SITTING UNAPPLIED"*. Every render in this report was
  produced by driving those flags. *Implication:* **both rows need amending in
  place.** Fact 1339 had already been corrected once, for a different reason --
  its headline was fixed and its **tense** was not.
* **P9 (MEASURED).** **AN INDEPENDENT RECOMPUTATION OF THE EXPOSURE DEFICIT
  AGREES WITH THE SHIPPED CHOOSER TO 0.006 STOPS.** numpy on the tool's own
  uncorrected `--srgb` output for `bee-3-cpl` (`bee-3-cpl-srgb.tif`,
  7032x4688), using BT.709 luminance coefficients and
  `numpy.percentile(method="inverted_cdf")`, puts luma `p99.9` at **0.310812**,
  i.e. **1.534 stops** below 0.90. The shipped chooser prints **+1.54**; M100
  published **+1.54**. *Implication:* the chooser's number is now confirmed
  from the emitted file, in a different language, by an operator who did not
  write it -- not merely reproduced from a prior report. Per rule 34 neither
  constant comes from `color.rs`.
* **P10 (MEASURED).** **THE IMAGES THE OWNER JUDGED WERE BINNED, AND ONE OF THE
  THREE WAS OVER-EXPOSED, NOT UNDER.** Direct measurement of the 23:37-23:39
  artefacts: `bee3-full.tif` is **3516x2344**, exactly half per axis of the
  *same stack's* measured 7032x4688 full-resolution render -- binning confirmed
  against a render rather than an asserted sensor size. Tone: `bee3-full`
  **+1.496** stops under, `lavendar` **+1.439** under, **`marker` at luma
  p99.9 = 1.0000, i.e. clipping, −0.152** -- corroborated by
  `captures-needed.md` §22, which gives `dry-erase-marker-head-cpl` −0.00 stops
  of headroom and **3.6726%** clipped. *Implication:* corroborates fact 1344 on
  binning and tone from an independent instrument, and shows **the
  two-sidedness of the correction is present in the judged set itself** -- a
  brightener would have made one of the three images the complaint was about
  worse. The grey-cast component of 1344 is **not** confirmed here; see PD8.
* **P11 (DERIVED).** **THE DISPLAY CORRECTION BUYS EXACTLY ZERO SNR, AND THE
  CAPTURE-SIDE REQUEST BUYS 1.80x ON THE SAME STACK.** `bee-3-cpl` has
  **+1.69 stops** of unused sensor headroom (`captures-needed.md` §22, 0.0000%
  clipped) and takes a **+1.54 stop** display gain here -- 0.15 apart, and the
  first largely causes the second. But digital gain scales signal and shot
  noise by the same factor (SNR x1.00), while a longer exposure scales signal
  by *g* and shot noise by sqrt(*g*) (**x1.80** at 2^1.69 = 3.23x photons).
  Derived from Poisson statistics, not from any strehl constant.
  *Implication:* **the two are numerically similar and informationally
  unrelated.** No report should describe the shipped gain as recovering any
  part of fact 1257's +2.01 median.
* **P12 (MEASURED).** **TARGET 0.92 WAS NEVER SWEPT.**
  `experiments/M100-exposure/sweep.py:31` is
  `TARGETS = [0.80, 0.85, 0.90, 0.95, 1.00]`. `gallery.py`'s `TARGET = 0.92`
  therefore has no measured backing anywhere in the corpus, and M100's sweep
  cannot adjudicate it. *Implication:* the standing question *"0.90 or 0.92?"*
  has never had an answer; it has had an assumption that the sweep covered it.
* **P13 (MEASURED + DERIVED).** **THE EXPOSURE CHOOSER READS BEFORE THE CLAMP,
  SO ANY POST-FILE INSTRUMENT IS BLIND TO EXACTLY THE DARKENING CASES.**
  `merge_cmd.rs`'s `choose` closure takes `display_luminance` on the binned
  quad grid; `image_out` clamps to `[0,1]` before the transfer curve. DERIVED
  from `gain = 0.90 / p99.9`: the percentile the chooser saw is
  `0.90 / 2^stops`, which across M100 §3.4's seven published choices exceeds
  1.0 on **`coffee-bean` (1.0196)** and **`foam` (1.1235)** and on no others.
  Confirmed against measurement: a post-file recomputation lands within one
  quantum on `bee-3-cpl` (implied 0.309497, measured 0.310812) and **four
  quanta out on `coffee-bean`, always in the brighter direction**.
  *Implication:* **the two stacks a post-file instrument cannot measure are
  precisely the two that prove the correction is two-sided.** Any future
  exposure work that reads the emitted TIF must state which side it is on.
* **P14 (MEASURED).** **`gallery.py` IS PINNED AT ITS OWN TARGET ON THE
  DARKENING CASE, AND ITS OUTPUT IS WHAT THE OWNER HAS BEEN SHOWN.** Because it
  reads the clamped file, its rule returns **−0.120 stops** on `coffee-bean`,
  and `log2(0.92) = −0.12029` — **the answer equals `log2` of its own
  `TARGET`**, which is the hardest darkening a post-clamp instrument can reach.
  The shipped rule chooses **−0.18**. It also differs on three further axes:
  it pools R, G and B samples (`np.percentile` with no `axis=`, a statistic
  M100 never swept), uses numpy's interpolated default rather than the
  nearest-rank the shipped code deliberately matches, and adds a 30-iteration
  bisection against a 0.5% clip budget. *Implication:* discipline 616 in the
  field. **The fix is not to reconcile two constants but to move the
  measurement upstream of the clamp** — i.e. to `--auto-exposure`.
* **P15 (MEASURED).** **A STALE OR TRUNCATED WARP SIDECAR IS REFUSED, NOT
  SILENTLY ACCEPTED.** `load_or_solve` accepts only when the file parses, the
  stack digest matches **and** `map.len() == paths.len()`; on mismatch it prints
  both digests and both frame counts and re-solves. Observed three times in this
  report's logs (`v2-auto-299`, `v5a-linear-60`, `v5c-D-stale`), of which
  `v5c-D` was a **deliberately planted** stale map registered in §4.5 as the
  positive control for this hazard. Its render was byte-identical
  (`54A5E20F...`) to the cold solve. *Implication:* the 10:30 notice's claim
  that *"a stale or partial sidecar does not announce itself"* is refuted for
  this path; the sidecar's failure mode is wasted re-solving, not wrong numbers.
* **P16 (MEASURED).** **THE SIDECAR GUARD COVERS WHICH FRAMES, NOT HOW THEY
  WERE SOLVED.** `StackIdentity` (`warpmap.rs:194`) is `{name, FNV-1a over
  (file name, file size) per frame, frame count}`. No reference frame, no
  resampler, no solver parameter enters the digest, so a map solved with one
  resampler is **accepted without comment** by any run with the same frames and
  count. Reference frame cannot drift — it is deterministic `floor(n/2)` across
  all 18 renders here (299→149, 105→52, 100→50, 60→30, 30→15). *Implication:*
  **the resampler is the one field that can change under a run undetected**,
  and it is the field the 10:30 notice attributes 59% of the high-band loss to.
* **P17 (MEASURED).** **`STREHL_WARPMAP` ALREADY SOLVES THE SHARED-STATE
  HAZARD FOR `strehl stack`, AND `align --out` DOES NOT.** When the env var is
  set, `alignment_for` (`merge_cmd.rs:1040-1073`) loads the named file and
  **never calls `load_or_solve`**, so nothing is written into the capture
  directory; it validates identity and count, and **fails hard rather than
  re-solving**, by explicit design (`merge_cmd.rs:1030-1034`). The oscillation
  reported on `bee-3-cpl` came from `strehl stack`, which has no `--out` for
  its sidecar. *Implication:* the two controls compose — `align --out
  <scratch>` to create a private map, `STREHL_WARPMAP` to consume it without
  writing — and **neither alone covers the observed incidents.**
* **P18 (MEASURED).** **THIS MILESTONE'S ONE EXIT-CODE GATE IS SOUND.**
  `01-render.ps1:26` pipes into `Out-File`, which consumes the whole pipeline,
  so the short-circuit that defeats `Select-Object -First N` is never raised.
  Verified against the same 200,000-line subject that defeats the positive
  control, under both PowerShell 5.1 and 7.6.5. *Implication:* no bar in this
  report read a failing render as successful.
* **P19 (MEASURED).** **THE TRUNCATED-PIPELINE SENTINEL IS NOT ALWAYS 0.**
  Under PowerShell 5.1 Desktop a truncated pipeline over a command that truly
  exited 1 leaves `$LASTEXITCODE` at **−1**; under 7.6.5 Core the same shape
  yields **0**. *Implication:* the recommended `if ($code -ne 0) { throw }`
  still fires on −1, so only the value-0 case is a true false green. Advice
  phrased as "it reads 0" invites `-eq 0` checks that miss the −1 case.
* **P20 (MEASURED).** **THE TRAP IS A RACE, NOT A PROPERTY OF TRUNCATION.**
  One script fired on a 5-line and a 200,000-line subject under PS 5.1, on
  neither under PS 7.6.5 via `-File -NoProfile`, and on the large subject only
  when run interactively under 7.6.5. The upstream must still be **running**
  when the pipe is torn down; a process that has already exited has already
  recorded its code. *Implication:* the same line passes and fails on different
  inputs, so the shape fix should be applied unconditionally rather than
  case-audited.
* **P21 (MEASURED).** **A `--limit N` RUN CANNOT INHERIT A SOLVE OVER A
  DIFFERENT SUBSET.** `raw_paths` (`main.rs:451`) sorts and *then* truncates,
  so `--limit N` is a deterministic sorted prefix, and the digest is computed
  over that truncated list. Reference frame is deterministic `floor(n/2)` (18
  renders). *Implication:* the frame-selection hazard described three times is
  guarded. **What is not guarded is the resampler**, which `warpmap.rs:336`
  stores in provenance as *"the resampler the solve was validated with"* and
  which `check_stack` — a single call to `provenance.stack.check` — never
  compares. **The field is recorded in the file and ignored by the validator.**
* **P22 (MEASURED).** **A SHARED-DIRECTORY RENDER AND AN ISOLATED-COPY RENDER
  OF THE SAME BRACKET ARE BYTE-IDENTICAL.** `v4-plain-299` (`D:\personal\macro\
  bee-3-cpl`, sidecar loaded) and `v6full-bee-3-cpl` (private isolated copy,
  freshly solved) both hash `A559616F…`; independently, `v5a-linear-60` and all
  four `v5c-*` arms hash `54A5E20F…` at 60 frames. *Implication:* an isolated
  copy no other agent knew existed is an **uncontaminated external reference**,
  so this is external verification rather than internal consistency. No number
  in this report needs retaking, and the isolated copies were byte-faithful.
* **P23 (MEASURED).** **THE M106 FAILURE MODE WAS PRESENT IN THIS REPORT'S OWN
  ARTEFACTS.** Bar V3's hash was published in prose and in the summary table
  but retained in no committed data file, because the render manifest covered
  only the first batch. Re-hashing the retained render gives `E400A63A…`,
  identical to `v2-auto-299`, so the bar stands — but had the file been
  deleted it would have been unrecoverable. *Implication:* acting on an
  orchestrator notice, rather than filing it, found a real defect at home.
* **P24 (MEASURED).** **THE TOOL ALREADY RECORDS THE FULL INVOCATION.**
  `strehl stack` prints `gates : 4.00` even when 4.0 is the default, plus
  `frames : N from <dir>`, which together fix directory, effective `--limit`
  and gate. All 18 logs here carry them and all 18 are committed.
  *Implication:* the M106 incident is not that the invocation was unrecorded
  but that the tool's report was not committed beside the hash. **The cheap
  machine-checkable rule is to require the log and parse the gate from it**,
  rather than to ask agents to remember to write it down.
* **P25 (DERIVED).** **THE JUDGED RENDERS COULD NOT HAVE BEEN ALIGNED.**
  Alignment was wired into `strehl stack` at `885e9f7`, `2026-08-24 03:15:23`;
  the artefacts §4.8 measured are timestamped `2026-08-23 23:37–23:47`, about
  3.5 hours earlier. *Implication:* §5.1's fourth defect, previously carried on
  a turn description, is now established by commit timestamp — the code path
  did not exist. Upgrades that item from ARGUED to DERIVED.
* **P26 (MEASURED).** **THIS MILESTONE'S OWN FREEZE GATE COULD NOT DISTINGUISH
  TOOL FAILURE FROM SUBJECT FAILURE.** `10-freeze-record.ps1` exited 1 both when
  its input manifest was missing and when a freeze record was defective — the
  same ambiguity that made `corpus_lint.py`'s silence unreadable. Now 0 / 1 / 2,
  with both failure arms exercised under piped stdout. *Implication:* the defect
  named in discipline 702 was present in a harness written **the same session**,
  which suggests it is a default rather than an oversight: `throw` and `exit 1`
  are both the path of least resistance in PowerShell.
* **P27 (MEASURED).** **THIS MILESTONE'S SCRIPTS ARE ENCODING-IMMUNE.** All 11
  committed scripts and every `.log` they parse are pure ASCII;
  `07-clamp-blindspot.py` under `PYTHONIOENCODING=cp1252` with piped stdout gave
  `rc=0`, 29 lines, 0 tracebacks, identical to the utf-8 arm. *Implication:* the
  re-runnability promise in §3 survives a verifier whose console is not UTF-8.
* **P28 (MEASURED).** **THE SHIPPED AUTO-EXPOSURE IS CLEAR OF THE QUANTISATION
  HAZARD WITH SIX BITS OF HEADROOM.** Across a 3-to-16-bit dose ladder on two
  real renders, the reported exposure is unmoved at both of the pipeline's real
  steps (16-bit output `q=1.526e-05`, 14-bit ARW `q=6.301e-05`, `dstops=0.0000`
  in both arms on both subjects) and first moves at **8-bit** on the linear
  render and **6-bit** on the sRGB render, against a real sensor depth of 14.
  Controls: null exact, planted gains of 0.5 and 2.0 recovered exactly, and the
  instrument moves `-0.03` stops at 4-bit so the null is quiet rather than dead.
  *Implication:* the exposure number needs no quantisation correction, and the
  clearance rests on a dose-response with a live positive control rather than on
  the withdrawn triage rule.
* **P29 (MEASURED).** **MODELLING QUANTISATION AS EQUAL-POWER DITHER UNDER-STATES
  IT BY ~79x FOR AN ORDER STATISTIC, NOT ONLY FOR A NOISE ESTIMATOR.** At the
  14-bit dose, quantisation displaces p99.9 **79x** further than matched-RMS
  uniform dither, on both the linear and the sRGB subject. Mechanism, measured
  through the fraction of the 1-Lipschitz bound each arm attains: dither falls
  monotonically from **0.81** at 3-bit to **0.009-0.12** at fine depths as its
  independent zero-mean errors average over the ~8,241 samples above the rank,
  while quantisation stays scattered between **0.16 and 0.97** because error
  deterministic in the pixel value moves that whole population together.
  *Implication:* the fleet's 16x result generalises well beyond differencing
  estimators -- **any** statistic that averages over many samples inherits it --
  and the correction is to model quantisation as quantisation.
* **P30 (MEASURED).** **A RATIO BUILT FROM A DISPLACEMENT BELOW ONE FLOAT32 ULP
  IS AN ARTEFACT OF THE REPRESENTATION.** The largest under-report ratio in P29's
  ladder is **336x**, at 16-bit on the sRGB subject, and it is **discarded**: the
  dither displacement there is `7.451e-09`, or **0.2 ulp** at `p=0.593`
  (`ulp ~ 3.5e-08`). The quoted 79x rows survive at 13.6 ulps (linear) and 2.1
  ulps (sRGB). *Implication:* when a null arm approaches machine precision the
  ratio against it grows without bound and reads as a stronger effect; **divide
  by an ulp count before quoting a ratio whose denominator is a null.**
* **P31 (MEASURED, refutes a caveat this milestone raised).** **A DOSE-RESPONSE
  CONTROL IS VALID FOR A RANK STATISTIC UNDER QUANTISATION.** Pre-registered
  prediction that `|dp|` would be non-monotone in `q` -- a sawtooth of distance
  to the nearest grid point -- is **falsified**: Spearman rho of `|dp|` against
  `q` is **0.9736** (quant) versus **0.9824** (dither) on the linear subject and
  **0.9868** versus **0.9912** on the sRGB subject, gaps of 0.0088 and 0.0044
  against a pre-registered threshold of 0.15. *Implication:* the orchestrator's
  replacement guidance needs no exception for this class. The sawtooth is real
  but lives in the scale-free ratio `|dp|/(q/2)`; a ladder spanning less than a
  decade of dose could see scatter rather than slope.
* **P32 (MEASURED).** **TWO QUANTISERS 4.2x APART GAVE ONE ANSWER, AND THE CAUSE
  WAS ARITHMETIC RATHER THAN CODE.** On the linear subject, 6-bit and 4-bit both
  returned `dp = +5.942e-03` because `p0 = 0.32739154` rounds onto `21/63` and
  `5/15`, **both exactly 1/3**. The sRGB subject, `p0 = 0.593`, lands on
  `0.587302` and `0.600000` and shows no coincidence, which is the negative
  control behaving. *Implication:* a repeated value across doses is a grid
  collision, not a stuck instrument -- but only a second subject distinguishes
  the two, so **carry a subject whose baseline sits elsewhere on the grid.**
* **P33 (DERIVED, from source).** **THE EXPOSURE GATE CANNOT BE MADE INERT BY
  `STREHL_ALIGN=0`, AND ITS NO-OP PATH ANNOUNCES ITSELF.** `merge_cmd.rs:3358-
  3398` places the exposure block at the top level of the writer with no
  alignment conditional; `Exposure::Auto` falls back through an explicit
  `eprintln!` naming the reason, and the report line fires on
  `!applied.is_identity() || applied.automatic`, so an automatic run choosing a
  gain of 1.0 still prints. Independently confirmed by hash: `v4-exp1-299`
  (`A4FABFEB...`) differs from `v4-exp0-299` and `v4-plain-299` (`A559616F...`),
  so the flag reaches the writer. *Implication:* the hazard the `STREHL_FIX_CA`
  notice describes was designed against here **before it was named**, and the
  credit is M100's, not this milestone's. Not covered: an actual
  `STREHL_ALIGN=0 --srgb --auto-exposure` render was not taken.

### Disciplines

* **PD17.** **A conclusion can be right for a reason that is wrong, and that is
  more dangerous than being wrong.** P29's ordering was pre-registered correctly
  and its stated rationale -- "a rank statistic is not a noise estimator, so
  that mechanism has nothing to act on" -- was refuted by the same run that
  confirmed the ordering. Had the ordering been the only thing checked, a false
  mechanism would have been folded with a true number attached to it, and the
  next agent to reason from that mechanism would have been misled by a
  *confirmed* prediction. **Check the reason separately from the result, because
  a passing prediction does not audit its own justification.**
* **PD18.** **A required deliverable can be present as content and absent as
  structure.** The commission required a *where this correction lies* section.
  Its content shipped -- the pipeline diagram and its three tested properties --
  but its **heading did not**, so `### 5.1` rendered as a subsection of `### 4.13`
  and no reader scanning the table of contents would have found §5 at all. Found
  by grepping this report for the names of its own required sections rather than
  by recalling that they were written. **Audit a deliverable against its
  commission by searching for each required item by name.**
* **PD19.** **An aggregate over a dose ladder is not a summary of it.** Script
  `11` reported P-B as "6 rows of 7, CONFIRMED" while the single dissenting row
  sat at the **extreme** of the ladder on **both** subjects -- the signature of a
  crossover, not of noise. A count of agreeing rows treats an ordered ladder as
  an unordered bag and discards exactly the structure a dose-response exists to
  reveal. **Report the row where the sign changes; a monotone process does not
  have one.**

* **PD1.** **A brief's premise that a previous dispatch already refuted must be
  checked against the ledger before re-sending, not just against the code.**
  Rule 43 makes an assertion of absence a claim needing a search. It does not
  cover the case where the search was *already done and written down* -- fact
  1347 and the `M105` ledger row both recorded this exact premise as false,
  and the brief was sent again anyway. **The greppable tells are not enough when
  the refutation is already in the file the brief is written from.** Before
  re-dispatching a stem, read its own ledger row.
* **PD2.** **A negative claim about a workspace must name the crates it
  searched.** Restates fact 1347's lesson at the point of use: the brief's grep
  covered one crate of two and its hits inside the feature's own documentation
  were dismissed as *"two unrelated doc comments"*. **A scoped search that finds
  the thing and misreads it is worse than one that misses it**, because the
  author now believes they looked.
* **PD3.** **Name the call site from `main.rs`, not from the filename.** The
  brief offered `stack.rs` as the `stack` subcommand's implementation. It is
  `argmax-baseline`'s; `Command::Stack` routes to `merge_cmd::run`
  (`main.rs:385` and `:410`). A brief that grants a file boundary from a name
  grants
  a boundary that may not exist -- here it simultaneously offered dead code and
  forbade the live file.
* **PD4.** **Matching arms on frame COUNT can mismatch them on scene
  COVERAGE.** `--limit n` takes the first n frames in capture order, so 60 of
  299 samples the opening fifth of a focus sweep while 60 of 100 samples three
  fifths. My first V6 design did this and read the specular tail at 1.0051
  instead of 1.1878 -- a null manufactured by my own subsampling. Rule 13 in a
  new costume: **ask whether the stimulus still contains the effect after you
  subsample it.**
* **PD5.** **An override belongs next to the operation it overrides.**
  `align_cmd.rs:951` performs the sidecar write; `STREHL_WARPMAP`, which
  redirects it, is defined in `merge_cmd.rs:1035`. I went to the write, missed
  the override, and copied 7 GB of frames to isolate myself instead.
* **PD6.** **PowerShell variable names are case-insensitive, so `$src` and
  `$SRC` are one variable.** A loop-local name that differs from an outer
  constant only in case silently overwrites it on the first iteration. This
  repo's harnesses are PowerShell-heavy and this shape reads as a *missing
  path* rather than a *wrong answer* only when the clobbered path happens not
  to exist. Mine threw on iteration two; the same bug against a stack whose
  name collides with a subdirectory would have read frames from the wrong
  place and reported a number.
* **PD7.** **A fact row can be corrected in its headline and left stale in its
  tense.** Fact 1339 was amended in place once — its false claim struck, an
  accurate grep left standing — and was then re-cited **108 minutes after the
  code it describes had changed**, by the same author, as an item on a list of
  things that *"do not change"*. Disciplines 637 and 667 both say *establish
  what you are reasoning from*; this is that lesson for **corpus rows rather
  than images**. **When a row asserts the absence of code, amend it with the
  commit that would falsify it.** A corrected row reads as verified, which
  makes it the easiest kind to over-trust.
* **PD8.** **Before running a plant, name the observation that would look
  identical under the null.** My grey-cast arm compared global channel means,
  predicting R and B depressed by the `cam_wb` ratios [2631, 1024, 1606]. The
  colour-**managed** gallery render reads G/R = 1.0177; the *un*managed judged
  render reads 1.0131. The statistic has no discriminating power, and I learned
  that only because a mis-scoped placebo happened to sweep in the managed file.
  **A placebo whose reading is indistinguishable from the signal's has not
  failed — it has diagnosed a blind instrument.** Report the arm as NO
  EVIDENCE, not as a refutation.
* **PD9.** **A positive control that fails is worth more than one that passes,
  if you ask why before discarding it.** §4.9's control failed by four quanta
  on one stack and one on another. Discarding it would have been correct by my
  own pre-registration and would have thrown away the finding: the pattern was
  one-sided, and chasing it produced P13 — a structural blind spot that also
  **qualified a claim I had already published in §4.8 and believed**. **Read
  the shape of a control's failure, not just its verdict.**
* **PD10.** **State which side of an irreversible operation your instrument
  reads from.** A clamp, a quantiser, a `max(0,·)` and a saturating cast all
  destroy information, and a statistic taken downstream of one can be
  numerically fine on most inputs and structurally meaningless on the rest —
  while printing a number either way. §4.8's recomputation was valid on five of
  M100's seven stacks and void on two, and nothing in the number said which.
  **Name the operation and the side, next to the statistic.**
* **PD11.** **A cache key that covers the inputs but not the parameters is not
  a cache key.** The warp sidecar validates *which frames* (`StackIdentity` =
  name + FNV-1a over `(filename, filesize)` + count) and refuses loudly on a
  mismatch — so the failure everyone fears, a truncated map on a short run, is
  the one case it *does* catch. What it silently accepts is the same frames
  solved with different parameters. **When you audit a guard, enumerate what it
  does not compare; the hazard lives there, not in the case it names.**
* **PD12.** **When an instrument is cleared, name the condition under which its
  control fired.** The first run of `09-exitcode-trap` cleared this
  milestone's exit-code gate while its positive control was silent — a verdict
  and a blind instrument are indistinguishable from the verdict alone. The
  script was written to return `INCONCLUSIVE` in that case, and did. **A pass
  is only as strong as the demonstration that the test could have failed**, and
  that demonstration belongs beside the pass, not in the author's memory.
* **PD13.** **Advice about a defect should name the shape that causes it, not
  the value it produced on the reporter's machine.** The same truncated
  pipeline yields `−1` on PowerShell 5.1 and `0` on 7.6.5, and only the latter
  is a false green. Guidance phrased around the observed value propagates a
  check that misses the other. **Describe the mechanism; let each agent measure
  their own symptom.**
* **PD14.** **The uncontaminated arm is the one your neighbours cannot reach.**
  Shared state defeats a control only while both arms share it. A copy in
  private scratch, whose existence no other agent knows, is outside the
  contamination channel by construction, so agreement between it and the shared
  render is external evidence rather than internal consistency. **When shared
  state is the hazard, buy an arm nobody else can write to** — it converts an
  unfalsifiable worry into a hash comparison.
* **PD15.** **A rule that depends on remembering will fail the way the thing it
  replaced failed.** The instruction "always write the gate beside the hash" is
  correct and will still be missed at 3am. The tool already prints the gate, so
  the enforceable form is "commit the tool's report beside the hash" plus a
  parser. **Prefer a rule a script can check to a rule an agent must recall.**
* **PD16.** **An environment workaround in a brief can hide the defect it works
  around from everyone downstream.** This milestone was instructed to export
  `PYTHONIOENCODING=utf-8` before every python call, and complied, and would
  therefore never have observed `corpus_lint.py`'s encoding failure however many
  times it ran the linter. **A standing workaround suppresses the signal for
  precisely the agents best placed to diagnose it** — so a workaround handed
  down in a brief should name the defect it is compensating for, or it silently
  converts a bug into folklore.

### Questions
* **PQ1.** What produced `M106`'s `CF266004...`? P3 rules out the source
  tree at `519203f`, P4 rules out sidecar state, P5 rules out
  `STREHL_ALIGN=off`. Remaining candidates: a differently-built binary, a
  different `--limit`, or an environment I did not replicate.
* **PQ2.** Should `--auto-exposure` default on under `--srgb`? Still
  undecided and still the orchestrator's (M100 §3.6). §7.1 adds one measured
  argument against and one cheaper alternative.
* **PQ3.** Does P6's tail result hold on `bee-1-cpl` and `bee-2-cpl`? One
  insect is not a population, and both stacks were available.
* **PQ4.** Of the five defects in the judged renders (P10, fact 1344), what is
  the actual rank order? Two have been fixed or shipped (binning, exposure),
  one is in flight (alignment), one is unexplained (the halo) and one I could
  not measure (colour management). **The project has now attributed the owner's
  complaint to a single cause three times and been wrong three times** (facts
  1324, 1341, and the sentence retracted at 10:07). The next attempt should
  probably be a render with the five toggled independently, not a fourth
  argument from a single artefact.
* **PQ5.** Should `StackIdentity` mix the solve parameters — reference frame,
  resampler, solver settings — into the sidecar digest? P16 says a resampler
  change is currently invisible to the guard, and the 10:30 notice attributes
  59% of the high-band loss to that field. **Reported, not acted on:**
  `align_cmd.rs` is held by M95-sharpness, and the notice asked for findings
  rather than fixes.
* **PQ6.** Was `FOCUS_NOISE_SD` calibrated on narrowed data? Every render in
  this report passes through the merge's noise gate, whose banner reads
  `gate unit : 0.021516 = sqrt(2) * FOCUS_NOISE_SD, the SD of a difference`.
  The orchestrator's finding is that differencing estimators book correlated
  quantisation error as signal and therefore **under-report noise**, which for a
  gate would mean it is set too tight. §4.14(g) establishes that no *instrument
  in this milestone* uses such an estimate, but the renders inherit that
  constant. **Reported, not acted on:** `merge.rs` is outside this milestone's
  boundary.

---

## 9. Rules discharged

Per rule 22, the line or command that executes each rule rather than agreement
with it.

| rule | discharged by |
|---|---|
| 8 label every claim | every number above carries MEASURED / DERIVED / ARGUED |
| 11 placebo + regression on the headline's own path | V4 runs both arms; V5c's determinism control precedes its claim |
| 12 the author never verifies their own work | the whole milestone: M100 self-verified, this is an independent operator, binary and frame count |
| 13 can the plant express the failure? | §4.7's disclosed reversal -- the `--limit 60` stimulus could not, and said so |
| 14 `Get-ChildItem -Force` | §4.6's inventory |
| 20 write down the input that would FAIL | every bar in §1 names it; V4's positive control exists because the placebo alone cannot fail |
| 22 walk the list | this table |
| 24 verification must re-choose | different frame count (299 vs M100's 60), different stack copies, different operator, an added positive control M100 did not run |
| 28 number proposed facts `P1..` | §8 |
| 33 read the line that proves the rebuild | `cargo build` printed `Compiling strehl-cli v0.0.0`; `-q` not used |
| 34 a plant that supplies its own constant | V4's `2.0` is the definition of a stop, stated in §1 before the run |
| 35 assert against an independently obtained quantity | V2 asserts against `M100-exposure.md` §3.4, a number a human can read |
| 39 report the null beside the ratio | §4.7 reports both controls beside the signal; §4.3 reports the placebo beside the positive control |
| 40 / 43 search `docs/research/` and name what you find | §0 -- and §4.6, where the search caught me about to publish fact 1296 as new |
| 41 allocate the stem | took `M105b`; ledger patch in §7.2 |
| 42 path-scoped commits | `git add -- <exact paths>` then `git commit -- <exact paths>`; no `-A`, no directories |
| 44 fold the delta | §8 diffed against 1253, 1257, 1293, 1296, 1347-1349 |
