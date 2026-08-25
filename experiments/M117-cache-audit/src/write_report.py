# -*- coding: utf-8 -*-
import io, os
p = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\M117-cache-audit.md"
body = r"""# M117 — auditing what the unkeyed warp cache actually touched

**Status: AUDIT COMPLETE. Verdict: the corpus is trustworthy, and the exposure
window in my own brief was wrong by a factor of 4.6.**

Owner: M117, verifier lane. I changed no source. Files written:
`experiments/M117-cache-audit/**` and this report.

M97n (`69f7b4c`) found that the shared warp-map cache was keyed on the capture
path alone, so a differently-configured solve of the same frames was served
silently. The fix landed with its own bars. **What nobody had done was ask what
the defect touched while it was live.** ORCH folded that admission as fact 1562
and dispatched this milestone. My brief stated the exposure as *"08-22 13:51 to
08-24 13:41 — roughly 48 hours of a 51-hour project"*.

**That premise is false, and refuting it is this milestone's first result.**
The cache did not exist on 08-22. The merge could not read it until 08-24
03:15:23. The real window is **10 h 26 m 30 s**, and 114 of the corpus's 163
reports had already landed before it opened.

---

## 1. Verdict table

| question | answer | evidence |
| --- | --- | --- |
| When could a poisoned entry first be **written**? | `ed45144`, **08-24 02:36:56** | `git log --diff-filter=A` on `align_cmd.rs` |
| When could one first be **served to a merge**? | `885e9f7`, **08-24 03:15:23** | M86c wired alignment into `strehl stack`; `load_or_solve` is introduced in that commit |
| When was it fixed? | `69f7b4c`, **08-24 13:41:53** | `solve_config_key` mixed into the key |
| Exposure window | **10 h 26 m 30 s** | not the 48 h my brief asserted |
| Does the cache persist across runs? | **YES — it is a file on disk** | `%LOCALAPPDATA%\strehl\warpmaps\<leaf>-<key>.warpmap.txt`; six entries were still present when I looked |
| Is exposure therefore per-run or cumulative? | **CUMULATIVE** | X2 |
| Reports IMMUNE | **155 of 163** | X11 |
| Reports EXPOSED (consumed a cache entry in-window) | **8 of 163** | X11 |
| Reports UNDETERMINED | **0 of 163** | X11, X12 |
| Reports found CONTAMINATED | **0** | X12, X13 |
| Positive control — did I reproduce the poisoning? | **YES, twice, independently** | X8 |
| Bottom line | **Partially trustworthy in principle, clean in fact** | §7 |

---

## 2. Phase 1 — the conditions, read out of the source

I read the pre-fix source from Git blobs as bytes via `subprocess`, never
through a shell redirect, because `git show ... > file` re-encodes the stream on
Windows and would have corrupted the comparison.

### 2.1 The cache is a file, and that is the whole severity story

Pre-fix `align_cmd.rs`:

```rust
pub fn sidecar_path(dir: &Path) -> PathBuf {
    let mut hasher = DefaultHasher::new();
    std::fs::canonicalize(dir).unwrap_or_else(|_| dir.to_path_buf()).hash(&mut hasher);
    let key = hasher.finish();
    ...
    cache_root().join(format!("{leaf}-{key:016x}.warpmap.txt"))
}
```

`cache_root()` is `$STREHL_CACHE_DIR`, else `%LOCALAPPDATA%\strehl\warpmaps`.
**Nothing about this is per-process.** A poisoning solve written at 04:00
remains on disk and is served to every merge of that bracket until something
overwrites it. This was the single most important question in the brief and the
answer is the unfavourable one: **exposure is cumulative, not per-run.**

Worse, before `8118dd7` (**08-24 10:32:43**, M97f) `sidecar_path` was literally
`dir.join("warpmap.txt")` — **inside the owner's read-only capture library**, so
the shared state was shared across every agent on the machine by construction.

### 2.2 The complete set of conditions

A poisoned entry reaches a rendered pixel only when **all six** hold:

1. `strehl stack` runs at a commit in `[885e9f7, 69f7b4c)`. Before `885e9f7`
   the merge had no cache read at all.
2. `STREHL_ALIGN` is not `0`/`off`/`false`/`no`. `align_enabled()` is tested at
   the top of `load_or_solve` and returns `Ok(None)` **before any cache path is
   computed**.
3. `STREHL_WARPMAP` is unset. `merge_cmd::alignment_for` returns early and never
   calls `load_or_solve`.
4. The directory is not a tilted subject (`highly-angled-ruler-mm-cpl`).
5. An entry already exists at that key whose **frame set** matches — both
   `map.check_stack(&identity)` (an FNV-1a digest over per-frame name and size)
   and `map.len() == paths.len()` must pass.
6. That entry was written by a solve whose **configuration** differs from
   `merge_config(n)` = `(n/2, DEFAULT_SPANS, CatmullRom)`.

Condition 6 is the narrow one, and it has exactly one source. `strehl stack`
always caches back at merge configuration, so **the merge cannot poison itself.**
The only writer that can produce a differently-configured entry at the key the
merge reads is **`strehl align` invoked without `--out`**.

### 2.3 The vector is wider than M97n reported

M97n demonstrated the defect with `align --reference 40` — an explicit
non-default flag. But `19f1be0` (**08-24 13:19:52**, M95) carries the message
*"align --reference defaulted to 0 while the automatic path uses the middle"*.
Pre-fix, `AlignArgs::reference` was `#[arg(long, default_value_t = 0)]` while
the merge used `merge_reference(n) = n / 2`.

**So from 03:15:23 to 13:19:52 — 10 h 04 m of the 10 h 27 m window — a plain
`strehl align <dir>` with no flags whatsoever was a poisoning run.** No operator
error was required. I verified this empirically rather than by reading (X8b).

---

## 3. Phase 2 — exposure across the corpus

163 files in `docs/research/`. Each classified by the commit dates of its first
and last touch, then by what its own transcript records.

| class | count | basis |
| --- | --- | --- |
| **IMMUNE** — last touched before `885e9f7` (03:15:23) | **114** | the merge had no cache read path; measurements predate the defect entirely |
| **IMMUNE** — first landed after `69f7b4c` (13:41:53) | **10** | keyed cache; pre-fix entries are orphaned (X12c) |
| **IMMUNE** — in-window but never invokes `strehl stack` | **16** | pure analysis; the consumer is never run |
| **IMMUNE** — in-window, invokes `stack`, never records a cache read | **15** | every recorded arm is `OFF`, `ON (solved)` or `sidecar-override` |
| **EXPOSED** — in-window and records `ON (sidecar)` | **8** | M97b, M97g, M97n, M105b, M108, M109, M111, SYNTHESIS |
| **UNDETERMINED** | **0** | every EXPOSED report resolves under X12 |

The eight EXPOSED reports are not a random sample of the corpus. **Seven of the
eight are the milestones that were investigating or controlling for this exact
defect** — M97b found the corpus writes, M97g measured `ADF81E01…`, M97n fixed
it, M108 built the freeze registry that forbids cache-dependent freezes, M109
and M111 ran cache controls, and SYNTHESIS quotes them. The eighth, M105b, named
the defect at source (*"The guard covers which frames. It does not cover how
they were solved"*) **4 h 20 m before M97n fixed it**, and measured that the
reference cannot drift: deterministic `floor(n/2)` across all 18 of its renders.

---

## 4. Phase 3 — the positive control, which is mandatory and which fired

A poisoning audit that never observes poisoning has not been validated. Two
arms, both run in isolated worktrees at historical commits, hermetic
`STREHL_CACHE_DIR`, `109MSDCF --limit 22 --gate 4.0`.

### 4.1 PC-1 — explicit `--reference`, at the immediate pre-fix parent `11e49dd`

| arm | cache | render SHA-256/16 | provenance | entries |
| --- | --- | --- | --- | ---: |
| **A** | empty | `07C067E438F74D77` | `ON (solved), reference frame 11` | 1 |
| **A2** | empty, repeat | `07C067E438F74D77` | `ON (solved), reference frame 11` | 1 |
| **B** | `align --reference 3` first | **`763EF0ED042E544E`** | **`ON (sidecar), reference frame 3`** | **1** |

`A` and `B` are the **identical** `strehl stack` command line. One cache entry,
not two: the poisoning solve did not add an entry, it *occupied* the merge's.
`A2` is the determinism arm — without it a difference could be run-to-run noise.

### 4.2 PC-2 — plain `align`, no flags at all, at `b9ba221`

| arm | cache | render SHA-256/16 | provenance |
| --- | --- | --- | --- |
| **A** | empty | `07C067E438F74D77` | `ON (solved), reference frame 11` |
| **B** | `strehl align <dir> --limit 22` | **`C2A03096AEEB69BF`** | **`ON (sidecar), reference frame 0`** |

**This is the important one.** No flag was passed that a careful operator would
have thought twice about. Running the project's own alignment subcommand and
then its own merge produced a different image, silently.

### 4.3 The null, at HEAD

| arm | render SHA-256/16 | provenance | entries |
| --- | --- | --- | ---: |
| A | `07C067E438F74D77` | `ON (solved), reference frame 11` | 1 |
| A2 | `07C067E438F74D77` | `ON (solved), reference frame 11` | 1 |
| B (same poisoning sequence) | `07C067E438F74D77` | `ON (solved), reference frame 11` | **2** |

Two entries, one render. The fix works, and my `07C067E438F74D77` reproduces
M97n's recorded value digit for digit from an independently built binary.

### 4.4 How much damage a poisoned render carries

Not a rounding difference. Comparing the TIFFs pixelwise:

| pair | pixels changed | max abs | RMS | RMS / mean level |
| --- | ---: | ---: | ---: | ---: |
| PC-1 A2 vs A (determinism) | **0.0000 %** | 0 DN | 0.000 DN | 0.0000 % |
| PC-1 B vs A (poisoned) | **98.6890 %** | 4908 DN | 117.969 DN | **1.8965 %** |
| PC-2 B vs A (poisoned) | **98.6491 %** | 5326 DN | 119.708 DN | **1.9245 %** |
| HEAD B vs A | **0.0000 %** | 0 DN | 0.000 DN | 0.0000 % |

In the central 80 % of the frame, **99.999 %** of pixels move. Any sharpness,
halo or chroma statistic taken on a poisoned render would have been a different
number. The defect's severity is not in doubt; only its reach is.

### 4.5 The guards, each verified rather than assumed

Run on the pre-fix binary, against a deliberately poisoned cache:

| guard | result | evidence |
| --- | --- | --- |
| `STREHL_ALIGN=0` | **IMMUNE** | clean and poisoned caches both give `48DFB69C00F0107F`; **zero** cache files written |
| `STREHL_WARPMAP` | **IMMUNE** | `ON (sidecar-override)`; **zero** cache files written |
| frame-set mismatch | **IMMUNE** | `sidecar rejected (... 22 frames ... applied to ... 10 frames); re-solving` |
| matched frame set, different reference | **POISONED** | `ON (sidecar), reference frame 2` where the merge wanted 5 |

The fourth row is the negative of the first three and is what makes them mean
something. `48DFB69C00F0107F` is also M97n's recorded `STREHL_ALIGN=0` plant
value, reproduced independently.

---

## 5. Phase 3b — what the shared cache actually contained

The guards above say *when* poisoning is possible. This says whether it
happened.

**5a. Every entry in the live shared cache carries the merge configuration.**
Six entries under `%LOCALAPPDATA%\strehl\warpmaps`, two of them written
in-window (10:39:03 and 11:53:00):

| entry | frames | reference | merge would use | resampler |
| --- | ---: | ---: | ---: | --- |
| `109MSDCF-258ca9a1…` | 22 | 11 | 11 | catmull-rom |
| `bee-3-cpl-3fa9b1ae…` | 299 | 149 | 149 | catmull-rom |
| `bee-3-cpl-ea1d38ea…` (in-window) | 6 | 3 | 3 | catmull-rom |
| `dry-erase-…-217a1d6e…` | 299 | 149 | 149 | catmull-rom |
| `dry-erase-…-57fff568…` (in-window) | 299 | 149 | 149 | catmull-rom |
| `lavendar-cpl-47e596c1…` | 299 | 149 | 149 | catmull-rom |

Not one is poisoning-shaped, and all carry the default span ladder.

**5b. One of them is provable, not merely plausible.** The in-window entry
`dry-erase-…-57fff568…` (pre-fix key, 11:53:00) and the entry
`dry-erase-…-217a1d6e…` (post-fix key, 15:03:27, independently re-solved at
merge configuration after the fix) are **byte-identical**: both
`1864A370AE92B377`, 41027 bytes. A re-solve is a stronger test than reading the
header, because it exercises the whole solve. That in-window shared entry was
not poisoned.

**5c. Post-fix runs cannot reach pre-fix entries.** The key is now
`hash(path, solve_config)` rather than `hash(path)`, so every pre-fix filename is
orphaned. Observed directly: my HEAD `lavendar` re-run computed
`lavendar-cpl-7a3c5ecc793d30ac` where the pre-fix entry is
`lavendar-cpl-47e596c1cc69bdfc`.

**5d. No poisoning write ever reached the shared cache.** I swept all 234 warp
sidecars on this machine for `reference != n/2`, a non-default resampler, or a
non-default span ladder. **104 poisoning-shaped sidecars exist** — and every
single one is either a file named by `align --out` or an entry in a *private*
`STREHL_CACHE_DIR` belonging to a milestone that poisoned it deliberately as a
control (M97's `flat-on-ruler-cpl-…` at `reference 40`, M111's `cache-poisoned`
tree, my own M117 arms). **Zero are in the shared cache root.**

**5e. Every no-`--out` `align` in the committed corpus is hermetic.** Scanning
every `.ps1`/`.py`/`.md` under `experiments/` and `docs/research/`, the
executable `align` invocations without `--out` are
`M97-warped-merge/src/poison2.ps1`, `M97b-align-visible/src/poison.ps1` and
`M97b-align-visible/src/corpuswrite.ps1` — all three set
`STREHL_CACHE_DIR` to a private directory, and all three exist to demonstrate
this defect. Everything else passes `--out`.

**5f. The capture library is clean.** Zero non-`.ARW` files remain anywhere
under `D:\personal\macro`.

---

## 6. Phase 3c — re-running load-bearing measurements at HEAD

**6a. `lavendar-cpl`, M111's generality arm — the single best target**, because
it is the one load-bearing published render that provably consumed a *shared*
cache entry on the solving path (`ON (sidecar)`), in-window, at 13:31.

Re-run at HEAD in an isolated worktree with an empty private cache, forcing a
fresh solve:

```
strehl stack D:\personal\macro\lavendar-cpl --srgb --auto-exposure --gate 4 --out lavendar-g4.tif
  STREHL_ALIGN unset (ON)   STREHL_WARPMAP unset   STREHL_FIX_HALO unset
  STREHL_SMOOTH unset       STREHL_SMOOTH_HUBER unset
  STREHL_CACHE_DIR=C:\dev\strehl-out\M117\rerun\cache-private  (empty)
  binary built at 4beac73 in C:\dev\strehl-out\M117-tree; 250.5 s
  alignment: ON (solved), reference frame 149, 299 placed / 0 refused
  --exposure=1.42
```

| quantity | published (M111 §12.3) | M117 re-measured | verdict |
| --- | --- | --- | --- |
| render SHA-256/16 | `F12B14C4…` | **`F12B14C477EAD503`** | **REPRODUCES** |
| solved sidecar SHA-256/16 | `4D454CCE…` | **`4D454CCEAEC2479F`** | **REPRODUCES** |

**6b. The byte-freeze registry is structurally immune, and passes.** Both rows
of `byte-freezes.tsv` are `env_align=0` or `env_warpmap=<committed fixture>`, and
the parser *rejects* a row with both unset — a solving row cannot be frozen at
all. `cargo test --release` in the isolated worktree at `4beac73`:
**449 passed, 0 failed, 1 ignored**, including
`the_frozen_renders_still_produce_their_recorded_bytes`.

This is worth stating both ways. The freeze registry proves the frozen renders
are untouched — **and it provides exactly zero coverage of the poisoning-
susceptible path**, because it is forbidden from going near it.

---

## 7. The bottom line, unsoftened

**The corpus is trustworthy. I found no contaminated number.**

That sentence is worth less than the evidence under it, so here is what it does
and does not rest on.

**What is proved.** The window is 10 h 26 m, not 48 h. 114 of 163 reports
predate the read path and are immune by construction, not by argument. The
merge cannot poison itself; only a no-`--out` `strehl align` can, and every such
invocation in the committed corpus is hermetic. The shared cache has never held
a poisoning-shaped entry, and the one in-window shared entry that can be tested
by re-solve is byte-identical to a post-fix independent solve. The one
load-bearing published render that provably read a shared cache entry
reproduces digit for digit at HEAD.

**What is not proved, and cannot be.** An ad-hoc `strehl align <dir>` typed into
a shell during those ten hours and never committed would leave no trace I can
recover, and X9 says the consequence would have been a ~1.9 % RMS shift across
98.7 % of pixels. My argument against it is circumstantial but not weak: such a
write would have left a `reference 0` entry in the shared cache, and the two
in-window entries that survive both carry `reference n/2`. **This is the residual
and I will not dress it as anything else.**

**The judgement.** This is the narrow, well-evidenced exposure the brief named
as the best possible outcome — but it arrived that way by luck as much as by
discipline. The defect was live for ten hours on a shared, on-disk, cumulative
cache, and the thing that kept it off the corpus was that the milestones running
alignment experiments happened to be the same ones that had already learned to
set `STREHL_CACHE_DIR`. **`STREHL_ALIGN=0` and `STREHL_WARPMAP` did the real
work**, and both were adopted for other reasons.

---

## 8. Facts

- **X1 (MEASURED).** The warp cache was **written** from `ed45144`
  (08-24 02:36:56) and could first be **served to a merge** from `885e9f7`
  (08-24 03:15:23), which is the commit that wired alignment into `strehl stack`
  and introduced `load_or_solve`. M97n fixed it at `69f7b4c` (08-24 13:41:53).
  The exposure window is **10 h 26 m 30 s**, not the 48 h recorded in fact 1562
  and in M117's dispatch brief.
- **X2 (MEASURED).** The cache is a **file on disk** —
  `%LOCALAPPDATA%\strehl\warpmaps\<leaf>-<key>.warpmap.txt`, or
  `$STREHL_CACHE_DIR` — and before `8118dd7` (08-24 10:32:43) it was
  `<stackdir>\warpmap.txt` inside the read-only capture library. **Exposure is
  therefore cumulative across processes and runs, not per-run.** Six entries
  were still resident when this audit ran, two of them written in-window.
- **X3 (DERIVED, from source).** Six conditions are jointly necessary for a
  poisoned entry to reach a pixel (§2.2). The load-bearing one is that
  `strehl stack` always caches back at `merge_config(n)`, so **the merge cannot
  poison itself**; the only writer that can is `strehl align` without `--out`.
- **X4 (MEASURED).** `STREHL_ALIGN=0` is immune: clean and poisoned caches both
  render `48DFB69C00F0107F`, and **zero** cache files are written, because
  `align_enabled()` short-circuits before any cache path is computed.
- **X5 (MEASURED).** `STREHL_WARPMAP` is immune: `ON (sidecar-override)`, and
  **zero** cache files written.
- **X6 (MEASURED).** The frame-set guard fires on a real mismatch, loudly and by
  name, and re-solves.
- **X7 (MEASURED).** A matched frame set with a different reference is served
  **silently**: `ON (sidecar), reference frame 2` where the merge asked for 5.
  This is the defect, isolated to one variable.
- **X8 (MEASURED, positive control).** The poisoning reproduces at pre-fix
  commits from independently built binaries. With `align --reference 3` at
  `11e49dd`, an identical `stack` command line gives `07C067E438F74D77` or
  `763EF0ED042E544E`. At HEAD the same sequence gives `07C067E438F74D77` both
  times, with **two** cache entries instead of one.
- **X8b (MEASURED).** **The vector is wider than M97n reported.** Because
  `AlignArgs::reference` defaulted to 0 until `19f1be0` (08-24 13:19:52) while
  the merge used `n/2`, a **plain `strehl align <dir>` with no flags at all** was
  a poisoning run for 10 h 04 m of the 10 h 27 m window:
  `C2A03096AEEB69BF` against `07C067E438F74D77`, provenance
  `ON (sidecar), reference frame 0`.
- **X9 (MEASURED).** A poisoned render is not marginally different. **98.65 % to
  98.69 % of pixels change**, RMS **117.97–119.71 DN** = **1.90–1.92 % of mean
  level**, max **4908–5326 DN**; in the central 80 % of frame, **99.999 %** of
  pixels move. Repeat runs are bit-identical (0.0000 % changed), so the
  difference is the poisoning and nothing else.
- **X10 (MEASURED).** At HEAD the poisoning sequence moves **exactly zero**
  pixels.
- **X11 (MEASURED).** Of 163 reports in `docs/research/`: **114 IMMUNE** because
  they landed before the read path existed, **10 IMMUNE** because they first
  landed after the fix, **16 IMMUNE** because they never invoke `strehl stack`,
  **15 IMMUNE** because every recorded arm is `OFF`/`solved`/`override`,
  **8 EXPOSED**, **0 UNDETERMINED**. Seven of the eight EXPOSED are the
  milestones that were investigating or controlling for this defect.
- **X12 (MEASURED).** **No poisoning write ever reached the shared cache.**
  (a) All six live shared entries carry `reference = n/2`, `catmull-rom` and the
  default span ladder. (b) The in-window entry `dry-erase-…-57fff568…` is
  **byte-identical** (`1864A370AE92B377`) to the post-fix entry
  `dry-erase-…-217a1d6e…` independently re-solved at merge configuration —
  proved by re-solve, not by reading a header. (c) Of 234 warp sidecars on this
  machine, **104 are poisoning-shaped and none is in the shared cache root**;
  every one is an `align --out` file or a deliberately poisoned private cache.
  (d) All three no-`--out` `align` invocations in the committed corpus set a
  private `STREHL_CACHE_DIR`. (e) Zero non-`.ARW` files remain under
  `D:\personal\macro`.
- **X13 (MEASURED).** M111's `lavendar-cpl` gate-4 render — the one load-bearing
  published measurement that provably read a **shared** cache entry on the
  solving path in-window — **reproduces exactly** at HEAD with an empty private
  cache and a forced re-solve: `F12B14C477EAD503` against the published
  `F12B14C4…`, and the solved sidecar `4D454CCEAEC2479F` against `4D454CCE…`.
- **X14 (MEASURED).** The byte-freeze registry is **structurally incapable** of
  depending on the cache: both rows set `env_align=0` or `env_warpmap`, and the
  parser rejects a row with both unset. `cargo test --release` at `4beac73` in
  an isolated worktree: **449 passed, 0 failed**, including
  `the_frozen_renders_still_produce_their_recorded_bytes`. This proves the
  frozen renders are untouched **and** that the registry gives zero coverage of
  the vulnerable path.
- **X15 (ARGUED).** The residual that cannot be closed is an uncommitted, ad-hoc
  `strehl align <dir>` typed into a shell during the window. Nothing would
  record it. The circumstantial case against it is X12a: such a write leaves a
  `reference 0` entry, and both surviving in-window shared entries carry
  `reference n/2`.
- **X16 (ARGUED).** What kept the defect off the corpus was **not** the frame-set
  guard and **not** review. It was that `STREHL_ALIGN=0` and `STREHL_WARPMAP`
  short-circuit before the cache is touched, and that the agents running
  alignment experiments had already adopted `STREHL_CACHE_DIR` for the
  *read-only-corpus* reason. Three independent habits, adopted for other
  reasons, covered a hole none of them was aimed at.

---

## 9. Disciplines

- **D1.** **A dispatch brief's premise is a claim, not a given.** Mine asserted a
  48-hour window covering "most of the corpus". The introducing commit put it at
  10 h 26 m covering 8 reports. Checking the premise cost one `git log` and was
  the highest-yield action in the milestone. **Date the defect from
  `--diff-filter=A` on the file that implements it, and from the commit that
  first *consumes* it, before you accept any statement about its reach.**
- **D2.** **"Cache" is not one hazard; ask where it lives before anything else.**
  A per-process memo cache bounds exposure to one run. A file under
  `%LOCALAPPDATA%` bounds it to the machine's lifetime and makes every agent on
  the box a writer. Same word, different audits.
- **D3.** **A poisoning audit that never observes poisoning has verified
  nothing.** Both my arms were run at real historical commits from independently
  built binaries, and one of them found a *wider* vector than the report that
  discovered the defect had claimed. Without the plant I would have had a table
  of greens indistinguishable from a disconnected probe.
- **D4.** **Prove a cache entry clean by re-solving it, not by reading its
  header.** The header is what the writer said; the re-solve is what the
  configuration actually produces. `1864A370AE92B377` twice, from a pre-fix
  writer and a post-fix solver, is evidence. `reference 149` in a header is a
  claim.
- **D5.** **When a fix keys a cache, ask what the old key's entries become.**
  Here they are orphaned, which is why post-fix reports are immune — a fact worth
  ten reports of classification and available in one filename comparison.
- **D6.** **State what your green does not cover, in the same breath.** The
  byte-freeze registry passes 449 tests and covers exactly none of the
  poisoning-susceptible path, by deliberate design. A reader who takes the pass
  as reassurance about *this* defect has been misled by a true statement.
"""
with io.open(p, "w", encoding="utf-8", newline="\n") as f:
    f.write(body)
print("wrote", p, len(body), "chars")
