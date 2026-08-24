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

Two findings that are not about exposure:

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

**What it does not correct.** Fact 1257: 19 of 23 delivered stacks are
under-exposed at **capture**, median +2.01 stops. This is a display gain applied
after the photons were not collected; it recovers the *appearance* and none of
the shot noise. Fact 1257's own implication -- that recovering the median at
capture would collect 4.04x the photons -- is untouched by anything here and
remains the larger lever.

---

## 6. Threats to validity

1. **V2's agreement could be luck of a coarse quantum.** The choice is
   quantised to 1/100 stop, so two renders differing by up to 0.7% in the
   percentile print the same number. MEASURED mitigation: the *gain* is also
   printed and reads `2.908x`; `2^1.54 = 2.9079`. But this bar cannot
   distinguish "unchanged" from "changed by less than half a quantum".
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
| M105b | **RE-DISPATCHED ON THE SAME FALSE PREMISE THE M105 ROW ALREADY RECORDS.** Sent to build exposure into the CLI, told *there is no exposure logic in the CLI at all*, and told to write crates/strehl-cli/src/exposure.rs. Both claims were already refuted in writing -- by the M105 ledger row and by fact 1347 -- before the brief was sent. Told to assume the brief contained an error and find it; it did, and found two more. Re-scoped by the agent to an independent verification of the shipped feature, since M100 verified its own work and rule 12 forbids that. | docs/research/M105b-exposure-ship.md, xperiments/M105b-exposure-verify/ | **reported. VERDICT: NOTHING TO BUILD; THE FEATURE PASSES EVERY BAR.** --auto-exposure still chooses **+1.54** on ee-3-cpl/299 -- exactly M100's published value -- after M95, M97, M99 and M103 all landed on the merge. Round trip byte-identical; placebo byte-identical; and the positive control reads the gain at **2.0000000 with IQR 8.9e-05** in linear light, testing color.rs's placement claim against the emitted file rather than its doc comment. **The byte-freeze is INTACT at HEAD** (54A5E20F..., five renders, one from a copy at a different path), which **contradicts the premise M106 was dispatched on**; it hands M106 three ruled-out mechanisms including a measured STREHL_ALIGN=off hash. **Its own registered hypothesis was refuted by its own control**: it predicted the freeze depended on sidecar state and measured a cached sidecar reproducing a fresh solve byte for byte. Answered the brief's p99.9 question with a number the corpus lacked -- the bee's specular tail is **real** (p99.99/p99.9 = 1.1878 against controls at 1.0264 and 1.0044) and **irrelevant**, because moving the percentile to p99.5 moves the exposure **0.031 stops**, while the same move costs oam **0.192**, so the proposed cure is worse. **Disclosed a discarded first design of that arm** whose --limit 60 matching confounded frame count with scene coverage and would have refuted the worry on its own subsampling. Corroborated fact 1296 after checking it was not new, and disclosed that it mutated ee-3-cpl/warpmap.txt itself. Recommends putting gallery.py on the shipped flag rather than changing any default. |
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

### Disciplines

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
