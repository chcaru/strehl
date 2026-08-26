# V-TRIAGE — independent verification of BUILD-TRIAGE `e710a46d`

I did not write any of this code. Everything below is a command I ran and the
output I read. Lane files were pinned to `$env:TEMP\V-TRIAGE-pin` before I began
and re-hashed at the end: `triage.py`, `mutatetest.py`, `makeviewable.py` and
`BUILD-TRIAGE.md` are all **UNCHANGED**. I edited nothing outside my own report.

Working tree matches `e710a46d` for every lane file, and no commit between
`e710a46d` and `HEAD` (`d6f5d537`) touches them, so the tree is the commit.

## Verdicts

| # | Claim | Verdict |
|---|---|---|
| 1 | Definition gate, both directions; 31 fields, all defined, no orphans | **VERIFIED** |
| 2 | Three mutations, all three killed, exit 0 | **VERIFIED** |
| 3 | `makeviewable.py` reads `blur_floor_px`; header reads 0.35 px, sourced | **VERIFIED** |
| 4 | `triage.json` carries `fields` and `constants` | **VERIFIED** |
| 5 | `corpus_lint` passes; no `crates/` staged or modified by this lane | **VERIFIED** |
| (a) | Edge-field inconsistency: 13 of 25 rows, worst `bee-2-cpl` 34% | **SPLIT — count verified, worst case REFUTED** |
| (b) | Harness restores state; each mutation killed by its own gate | **VERIFIED** |

## (a) The edge-field inconsistency — the count is right, the worst case is not

Recomputed from `triage.json` by a route the author did not use: read the shipped
artifact, divide the two shipped numbers, compare against the third.

`triage.json` is **deterministic** — two consecutive runs produced byte-identical
files (`0DEBCFFB4E03E42B`), so the author was reading the same numbers I am.

**The count reproduces**, and robustly: two independent natural criteria both
give exactly 13.

```
usable rows: 25            (flowers-cpl excluded: merge=0.0 frame=0.0 ratio=None)
  absolute diff > 0.01       -> 13 of 25   <== 13
  relative error > 1%        -> 13 of 25   <== 13
```

**The worst case is refuted.** It is not `bee-2-cpl`:

```
subject                         merge      frame      m/f   stated  rel.err
dry-erase-marker-head-cpl    6863.800    961.600    7.138    2.316   208.2%
bee-2-cpl                    2946.600   1536.100    1.918    1.429    34.3%
```

`bee-2-cpl`'s own figures are exactly as reported — 1.92 against 1.43, 34% out —
but it ranks **2nd of 25**, not first. `dry-erase-marker-head-cpl` is out by
**208.2%**, six times worse, and it is worst by *both* available rankings:

```
  by relative error      : dry-erase-marker-head-cpl  7.138 vs 2.316
  by absolute difference : dry-erase-marker-head-cpl  7.138 vs 2.316
  bee-2-cpl rank by relative error: 2 of 25
```

There is no ranking under which `bee-2-cpl` is the worst case. It is an ordinary
row — `verdict: GOOD`, `n_sites_used: 2`, exactly like `dry-erase-marker-head-cpl`
— so nothing excludes the latter from consideration.

**Why this one matters more than a wrong digit in prose.** The understated figure
is not confined to the report. It is shipped *inside the field definition itself*,
which is precisely the artifact this task existed to make trustworthy:

```
frame_edge_dnpx: "... Dividing the two does NOT give edge_ratio_min
                  (it disagrees on 13 of 25 rows, worst 1.92 vs 1.43 on
                  bee-2-cpl). Use edge_ratio_min"
```

A reader who accepts that definition will believe the maximum damage from
dividing the two fields is 34%. On `dry-erase-marker-head-cpl` it is 208%. The
report already knows this subject is extreme — section 369 quotes it at 131% on a
related statistic — so the information was in hand.

No tolerance is stated anywhere for "disagrees". The count survives only because
two natural criteria coincide at 13; at 0.5% it is 16 and at 2% it is 10.

## (b) The harness restores its own state — verified three ways

I re-drove BUILD-TRIAGE's harness from my own driver without editing it.

**Definition mutations alone, no wording mutation first:**

```
--- mutate_definitions() alone -> rc=0
    wording gate OK: 26 rows, every noise claim agrees with its own noise_flat
    MUTATION KILLED -- UNDEFINED (ships with no definition): noise_flat
    wording gate OK: 26 rows, every noise claim agrees with its own noise_flat
    MUTATION KILLED -- ORPHANED (defined but never emitted): snr_margin_db
    [OK] both killed by the DEFINITION gate; wording gate never fired
```

The `wording gate OK` line printing *before* each kill is the direct evidence:
the wording gate ran, passed, and handed off. Each mutation dies by its own gate
with its own message.

**Explicit restoration check, and reverse order:**

```
noise_phrase is original after return : True
FIELD_DEFS unchanged after definitions : True
[OK] reverse order: each mutation still killed by its own gate
```

**The `finally` is load-bearing.** I reproduced the pre-fix state by hand —
leaving `noise_phrase` patched, exactly as a missing `finally` would — and got
the failure the author described:

```
anchor found in mutatetest.py: 'triage.noise_phrase = good_phrase'
occurrences: 1 (must be 1 for the anchor to be unique)
mutate_definitions() rc = 1  (0 would mean 'all green')
    FAIL: stopped, but not by the definition gate: noise wording disagrees...
    FAIL: stopped, but not by the definition gate: noise wording disagrees...
killed by the WRONG gate: True
```

Their account is accurate. One nuance worth recording: the pre-fix harness did
**not** print a false green — it returned `rc=1` and failed loudly, just with a
misleading diagnosis. It accused working code rather than excusing broken code,
which is the safer of the two ways to be wrong.

## Findings nobody claimed

**U1 — `commission_wording` is monkeypatched and never restored.** Both
`mutate_wording()` and `mutate_definitions()` set
`triage.commission_wording = lambda: None`, and neither restores it; only
`noise_phrase` and `FIELD_DEFS` get a `finally`. Measured directly:

```
noise_phrase is original after return : True
FIELD_DEFS unchanged after definitions : True
commission_wording restored           : False
```

Benign today because the process exits, but it is the *same defect class* the
`finally` was added to fix — a leaked monkeypatch crossing between mutations —
left in place for the third patched name. A mutation added later that depends on
commissioning running would silently not run it.

**U2 — the definition gate does not cover the `counts` block.** It unions each
row's top-level keys and its `evidence` keys. `evidence` is the only nested dict
in the data, so row coverage is complete. But `counts` ships 8 verdict labels
with no entry in `fields`. This is a judgement call — they are arguably values
rather than fields, and the taxonomy is defined on the contact sheet — so I
record it as a boundary of the gate, not a defect.

**U3 — the gate genuinely blocks the write, which the harness never checks.**
`mutatetest.py` asserts only that `SystemExit` carried the right message; it
never confirms `triage.json` stayed unwritten. I pinned the file to
`$env:TEMP`, deleted it, ran the definition mutations, and confirmed it was not
recreated; then ran unmutated as a positive control and it came back
**bit-identical to the pin** (`0DEBCFFB4E03E42B`).

**U4 — the mutation anchors fail safe (in their favour).** The standing rule
warns about `replace(x, y, 1)` matching nothing and going green. Their mutations
are dict operations, and `d.pop("noise_flat", None)` tolerates a missing key —
but if it failed to land, `main()` would succeed and the harness would print
`MUTATION SURVIVED -- FAIL`. A non-landing anchor produces a loud failure, not a
false pass. The diagnosis would be misleading, but the colour would be right.

## What I did not verify

I did not rebuild the contact sheet image and read the pixels; claim 3 is
verified at the string that feeds the header, including a control showing it
tracks a moved source (0.99) and degrades to `instrument floor not reported`
when `constants` is absent. I did not audit the 31 definitions for accuracy of
*content* beyond the three edge fields the deep check named — the gate proves
every field has *a* definition, not that each one is true.
