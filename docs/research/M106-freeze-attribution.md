# M106 -- attributing the broken byte-freeze

**Author:** `ultracode:ultra-verifier` agent `a7cf3e3e`, 6764 s, 3 turns, claude-opus-5.
**Persisted by:** the orchestrator, verbatim. The verifier's brief bars it from
writing findings to disk, so this file is a transcription rather than a rewrite.
**Nothing below has been edited** -- not the claims, not the numbers, not the
self-disclosed gaps. Where the orchestrator disagrees or has acted since, that is
recorded in `SYNTHESIS.md` against the fact numbers, not here.

**Read the verdict first: the defect this milestone was commissioned to attribute
did not happen.** The dispatch that commissioned it -- written by the orchestrator
-- compared a `--gate 2` render against a baseline rendered at the default gate
4.0, and read the difference as a broken freeze. A different, real break was found
in the course of refuting the reported one.

---

I have everything. All measurement is complete.

## Verdict

**DEFECTS FOUND** — but *not* the defect that was reported. The reported break is a false alarm caused by a wrong comparison command. A **different, real freeze break** exists, which the dispatch did not ask about, and it is attributable to the same commit the requester guessed.

## Commands run

```
strehl.exe stack D:\m106-scratch\bee-3-full --gate 2 --out m85-c24e347.tif   # pre-M86c
  → 41974F2AA2187C63CE3031813BD51F7D1A0B6EB4972EDF1F7F1684E2D429F699
  → BYTES: 49449626 (M85 recorded 49449626)   MATCH: True

strehl.exe stack D:\m106-scratch\bee-3-full --gate 2 --out m85-HEAD.tif      # 519203f
  → D1D5C51726762015D76F0C3DE75F44C9CB679974B9DA4D5BEA67B31CD4CF1256
  → MATCH: False
  → alignment      : ON (solved), reference frame 149, 299 placed / 0 refused

885e9f7 -> D1D5C517…  M85match=False HEADmatch=True
894f9f7 -> D1D5C517…  M85match=False HEADmatch=True
```

```
max abs DN delta : 36107
RMS delta        : 3594.7581
mean abs delta   : 2149.9715
samples differing: 24694940 / 24724512 = 99.8804%
PIXELS differing : 8241501 / 8241504 = 100.0000%
```

## Claims checked

| Claim | Result |
|---|---|
| "The freeze is broken … identical command produces `CF266004…`" | **REFUTED.** The command was not identical. M100's B1 (`verify3.ps1:32`) passes **no `--gate`**; the dispatch added `--gate 2`. `DEFAULT_GATE = 4.0` (`merge.rs:297`). M100's own preserved binary `C:\dev\strehl-out\M100\v3\strehl-head.exe` yields `CF266004…` with `--gate 2` and `54A5E20F…` without it. |
| M100's `54A5E20F…` no longer reproduces at HEAD | **REFUTED (MEASURED).** HEAD `519203f` with M100's real command reproduces `54A5E20F44255BB526C61D4397D239D6F1D26A06D54A8A56FBC944B91B37E7A2` exactly. Holds at all 8 commits from `885e9f7` → HEAD. |
| `885e9f7` (M86c alignment) is the mover | **CONFIRMED, with a correction.** It is the only commit that moves the default render — but at `2026-08-24 03:15:23`, which is *before* M100's baseline `894f9f7` (`05:55:29`). It cannot be the cause of a post-baseline break. |
| M87 `52c6a52` is "default OFF" | **CONFIRMED, two independent ways.** Source: `halo.rs:69` `FIX_ENV="STREHL_FIX_HALO"`, `enabled()` `:98-106` returns `false` on `Err(_)`; gated at `merge_cmd.rs:1531` `if halo::enabled() && opts.out.is_some()`. Measurement: hash unchanged across it on both gates. **Not a regression.** |
| M97 `79dc8b3` did not improve the image | **CONFIRMED inert.** Hash unchanged at both gates. |
| M95 `56bd846`/`56e4cfa`/`4ac71e9` | `56bd846` is boolean-inert (`demosaic \|\| (srgb && !binned)`), hash-confirmed. `56e4cfa` and `4ac71e9` **touch no `crates/` file at all** — the dispatch's candidate list was wrong here. |
| The exposure patch `925d03d` is inert | **CONFIRMED independently**, re-derived from the ladder without repeating the restore-touch-rebuild control. |

**The candidate list's premise was also wrong:** `885e9f7`, `79dc8b3` and `52c6a52` are all **ancestors of** `894f9f7` (`git merge-base --is-ancestor`), not commits after it.

## Defects

**1. HIGH — M85's byte-freeze is genuinely broken, and it is the one the code cites.**
`merge_cmd.rs:2958-2971` states: *"`docs/research/M85-output-correctness.md` carries the SHA-256 proof that it still emits the identical bytes."* M85's proof (`M85-output-correctness.md:172-178`) is `--gate 2`, 299 frames → `41974F2A…F699`, 49 449 626 bytes. That hash reproduces **exactly** at `c24e347` and **fails** at HEAD, now `D1D5C517…`. Attributed to **`885e9f7` M86c** and constant since. **Intended** — the log gains `alignment : ON (solved), … 299 placed / 0 refused`; wiring alignment in is a quality improvement, not a regression. But it silently invalidated the cited proof. M85's P12 (*"The corpus's ~1138 facts remain valid"*) was true when written and is now stale.
Nuance, to be fair: the *encode closure itself* is textually unchanged (confirmed by diff `c24e347..519203f`) — M86c changed the merge's **input**, not the arithmetic. The comment's textual claim is true; its artifact claim is false.

**2. MEDIUM — no canonical freeze command exists.** Three milestones froze three different invocations, each with its own hash, none recorded next to the other: M85 `--gate 2`/299 frames → `41974F2A`; M100 `--limit 60`/no gate → `54A5E20F`; M95 `coffee-bean --limit 20 --gate 2.0` → `D99F5D82`. The dispatch spliced M85's gate onto M100's limit, producing a fourth invocation no milestone ever froze. **This ambiguity is the direct cause of the false alarm.**

**3. MEDIUM — mutable cache inside the read-only corpus.** `align_cmd.rs:894-953` `load_or_solve` reads and **writes** `warpmap.txt` into the corpus directory. `StackIdentity::from_paths` (`warpmap.rs:238`) digests only **filename + file length**, not content. I observed that file's contents change three times during one session. Today both arms agree (`54A5E20F…`), but nothing enforces it — a stale sidecar would silently change a "frozen" render.

## Magnitude

| Comparison | max DN | RMS | pixels differing |
|---|---:|---:|---:|
| M100 baseline vs HEAD, **M100's real command** | **0** | **0.0000** | **0.0000%** |
| M85 freeze vs HEAD, **M85's real command** | 36107 | 3594.7581 | **100.0000%** |
| gate 4 vs gate 2, same binary (the dispatch's error) | 1813 | 113.5883 | 98.6714% |
| pre- vs post-alignment `c24e347`→`885e9f7` | 20130 | 1109.6242 | 100.0000% |

## Gaps

- I did not measure the no-gate hash at every *intermediate* commit (only at gate 2 for those); a gate-dependent move-and-revert inside `885e9f7..894f9f7` is not formally excluded, though both endpoints and all 12 gate-2 points are constant.
- I did not render at default gate inside the live corpus dir (it would write to the corpus). Justified by measured corpus-vs-scratch agreement at `894f9f7` (both `CF266004`).
- **Disclosure:** my first four gate-2 runs ran against `D:\personal\macro\bee-3-cpl` before I understood the write hazard and may have caused `warpmap.txt` writes there. The one run I instrumented did not write (hash `17FBA7F3…`, mtime unchanged). The 299-frame version that later appeared came from another process.
- No test exists that pins any freeze hash. Every freeze in this project is enforced by prose in a report, not by CI — **an untested freeze is an unverified freeze.**

---

## Summary for the orchestrator

**Attributed commit: `885e9f7` (M86c, "wire alignment into strehl stack"), `2026-08-24 03:15:23`** — the only commit that moves the default render, and it moves *every* pixel. **Intended and defensible; do not revert.**

**The reported break did not happen.** M100's `54A5E20F…` reproduces bit-for-bit at HEAD. The `CF266004…` you measured is `--gate 2` against a baseline rendered at the default gate 4.0 — M100's B1 command passes no `--gate`. Your own M100 binary demonstrates both hashes on demand depending only on that flag. **Your exposure patch is inert, and so is M87, M95, M97 and M103.**

**M87's "default OFF" is TRUE** — proven from source (`halo.rs:98-106`, `merge_cmd.rs:1531`) *and* by unchanged hash. Clean.

**But the corpus does have a real split — an earlier one.** M85's freeze, the hash the `merge_cmd.rs` comment points at as live proof, broke at `885e9f7`: `41974F2A…` → `D1D5C517…`, 100% of pixels, RMS 3594 DN. It reproduces exactly at pre-M86c, so the apparatus is sound. **Any quality number measured before 2026-08-24 03:15:23 describes an unaligned merge; everything after describes an aligned one.** That is the line SYNTHESIS.md needs, and it sits *before* M100's baseline, not after — so the recent milestones are mutually consistent.

**Recommendation: re-baseline, revert nothing.** Update M85's frozen hash to `D1D5C517…` noting M86c as the intended cause; correct the `merge_cmd.rs:2965-2969` comment, which currently cites a proof that no longer reproduces; and **record the full command line — directory, `--limit`, and explicitly `--gate` — next to every freeze hash**, because the absence of that one flag is the entire reason this investigation was commissioned.

I wrote no files. The report content above is yours to save as `docs/research/M106-freeze-attribution.md`; my instructions bar me from writing findings to disk.

---

## Addendum — independent verification of M95's `coffee-bean` freeze

*Transcribed by the orchestrator from M106-freeze's fifth turn. Commissioned
**before** M108-freeze-test reported and deliberately isolated from it: if one
agent both selects a fixture and verifies it, nobody has checked the selection.
The verifier was instructed not to read M108's work and did not.*

**Verdict: `D99F5D82` is NOT stale — it is under-specified.** It reproduces
exactly, at both M95's commit and HEAD, but **only with `STREHL_ALIGN=0`**,
which appears nowhere in the record.

Command, all four rows: `strehl.exe stack <dir>\coffee-bean --limit 20 --gate 2.0 --out <out>`

| commit | alignment | hash | == M95 record |
|---|---|---|---|
| `56bd846` (M95's own) | default, `ON (solved)` | `119936E6…` | **no** |
| `14b39dd` (HEAD) | default, `ON (solved)` | `119936E6…` | **no** |
| `56bd846` | `STREHL_ALIGN=0`, `OFF` | **`D99F5D82337AA2F093202D12677FBD1DE6D78A94761C0DE250020085271C76CA`** | **YES** |
| `14b39dd` (HEAD) | `STREHL_ALIGN=0`, `OFF` | **`D99F5D82…76CA`** | **YES** |

All renders 49 449 626 bytes, exit 0. Isolation confirmed:
`alignment : ON (sidecar-override), reference frame 10, 20 placed / 0 refused`;
`EXIT B: 0  A==B (determinism): True`.

**The renderer never moved.** Both variants are frozen across the whole range,
so M108 is not about to enshrine a changed renderer.

**A stale sidecar cannot explain it — ruled out by the quarantine itself.** No
quarantined `coffee-bean` file carries `frames 20` (they are 1, 8, 12); any
other count re-solves deterministically.

### The omission is the finding, and it is worse than a missing flag

The record — the commit body of `56bd846`, **the only place the full 64-char
hash exists**; no M95 report contains it — states `coffee-bean --limit 20
--gate 2.0, no --srgb`. It omits **`STREHL_ALIGN=0`**, the byte count, the
commit SHAs and the absolute directory.

> Rule 47 names "directory, `--limit`, and `--gate` by value" — all CLI flags.
> The decisive element here was an environment variable.

Rule 47 was amended in the same commit as this addendum to bind
`STREHL_ALIGN`, `STREHL_WARPMAP`, `STREHL_FIX_HALO`, thread count, byte count
and commit SHA. **Third false break in one session from one root cause:**
`bee-3-cpl` lost `--gate`, `coffee-bean` lost `STREHL_ALIGN`.

### Defects raised

**HIGH — the library repopulated twice *during* this check.**
`coffee-bean/warpmap.txt`: `frames 1` at `10:27:37`, `frames 20` at `10:31:11`,
and `608 B / frames 1` again at **`10:33:42`, after the quarantine**. The
verifier wrote none of these; all its runs targeted `D:\m106-scratch\coffee-bean`
and Run B used the override. Its conclusion, accepted:
**"Quarantining is not remediation; the file returns within minutes."**

**MEDIUM — the aligned variant rests on a registration the tool refuses to
certify.** Every aligned run printed `WARNING: this solve could not certify
itself … the registration below is UNVERIFIED`. Pinning `119936E6` pins a
number the tool itself declares unverified.

**Forensic caution.** The verifier's scratch solve and the library file were
byte-identical (`EF74541395DB1BA6`, `stack-digest 25daf54c45be5446`) because
`StackIdentity` digests filenames and sizes only and is **directory-independent**.
**A quarantined sidecar cannot be attributed to an agent from its contents.**

### Recommendation to M108, offered as evidence not instruction

Pin **both rows**, and state the trade:

- `STREHL_ALIGN=0` → `D99F5D82…76CA`: **zero sidecar dependency**, structurally
  immune to the shared-state hazard that broke this stack four times in one
  session — but exercises none of the alignment path.
- default aligned → `119936E6…`: covers alignment, but depends on sidecar state
  and carries the self-certification warning.

**One fixture cannot do both jobs.** Choosing only the aligned one buys coverage
at the price of the exact fragility M108 exists to eliminate.

### Gaps the verifier declared

- No bisection *between* `56bd846` and HEAD; both endpoints agree on both
  variants, so an intermediate move-and-revert is not formally excluded.
- Did not read M108's work and did not coordinate, per instruction.
- Cannot prove *why* the alignment solve fails to certify on this stack; the
  tool attributes it to insufficient long-span edges, unverified.
- `coffee-bean` holds 105 frames (`DSC00016`–`DSC00120`); `--limit 20` selects
  `DSC00016`–`DSC00035`. Confirmed in scratch; **not** confirmed that the
  library held the same 105 files when M95 was measured.

*Folded as facts 1389–1392, disciplines 692–693.*
