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

---

# Re-verification of BUILD-TRIAGE's four fixes (commit `b975efce`)

Acceptance criteria were pre-registered in the session DB **before** the fix
existed (`vtriage_prereg`, 6 rows), so nothing below is a criterion invented to
fit what shipped.

## X-regression first: is this a reporting fix or a data change?

Per the pre-registration, determinism had to be re-established before any number
was judged, to separate a corrected sentence from moved data.

```
run1 sha : 01097CEF6BCD4086
run2 sha : 01097CEF6BCD4086
deterministic across runs : True
```

Comparing the shipped JSON against my pre-fix pin, block by block:

```
  constants    pre=ec2c145236804858 post=ec2c145236804858   SAME
  counts       pre=da54246059707571 post=da54246059707571   SAME
  fields       pre=2254234fef2ebb71 post=12d77308cb8d3125   *** DIFFERS ***
  rows         pre=fac15c36f7ea5647 post=fac15c36f7ea5647   SAME
field-def keys added  : []      removed: []
field-def TEXT changed: ['frame_edge_dnpx']
```

**The rows are byte-identical.** Exactly one definition text changed. This is a
pure reporting fix with zero data movement, so my pre-fix recomputation remains
directly comparable — the true worst case cannot have moved for data reasons.

## F1 — the corrected worst case: VERIFIED

I parsed the numbers back **out of the shipped definition string** and checked
each against a recomputation from the rows, rather than reading them:

```
CLAIM 'disagrees on 13 of 25 rows'
   abs>0.01 count : 13   OK
   rel>1%   count : 13   OK
CLAIM 'both criteria select the SAME 13' (set equality, not count)
   sets equal     : True   OK
CLAIM 'at 0.5% it is 16 rows' -> got 16   OK
CLAIM 'at 2.0% it is 10 rows' -> got 10   OK

ordering by RELATIVE error:        ordering by ABSOLUTE difference:
 1. dry-erase-marker-head-cpl       1. dry-erase-marker-head-cpl
 2. bee-2-cpl                       2. bee-2-cpl
 3. pencil-steep-angle-cpl          3. pencil-steep-angle-cpl

STATED worst : dry-erase-marker-head-cpl 7.138 vs 2.316 +208%
   max by REL? True    max by ABS? True
   m/f 7.138 vs recomputed 7.1379  OK
   true 2.316 vs recomputed 2.3159  OK
   pct  208% vs recomputed 208.2%   OK
STATED second: bee-2-cpl  rank by REL 2, rank by ABS 2
```

Correct subject, correct figures, maximum under **both** orderings, and the
runner-up correctly ranked. Their claim that both criteria select *the same* 13
holds as **set equality**, not merely equal counts — I tested the sets, which is
the stronger reading and the one they wrote.

## F2 — the stated tolerance: VERIFIED AS ASKED, with a measured residual

The tolerance is now stated and it is **correct** — it matches the ground truth I
pinned before the fix at every point on the ladder. That was the ask and it is met.

My pre-registered condition was stricter: *the stated tolerance must be the one
the code applies*. It is not, because **no code applies one**. Nothing in
`triage.py` computes this statistic:

```
   129: "edge_ratio_min: it disagrees on 13 of 25 rows, where "
   130: "'disagrees' means |m/f - edge_ratio_min| > 0.01 "
```

Those are the only occurrences, and they are inside a prose literal. I
demonstrated the consequence rather than asserting it — perturb one value so the
true count is no longer 13, then run the **actual** gate from `triage.py`:

```
baseline disagreement count : 13   (definition says 13)
baseline gate               : missing=[] orphaned=[] -> GREEN
perturbed 112MSDCF  frame_edge_dnpx x0.5
  true disagreement count now : 14   <- definition still says 13
  definition gate now         : missing=[] orphaned=[] -> GREEN
```

The data contradicts the shipped definition and every gate stays green. The
count and tolerance are correct **today** and nothing keeps them correct.

I am not recording this as a failure, for one reason: it is precisely the
limitation their F4 fix now discloses in the code — *"Definition content needs a
human or a verifier reading it against the data."* The residual is real, it is
stated, and it is stated in the right place.

## F3 — restoration made moot: VERIFIED, and my fail mode refuted

They took the subprocess route. Run alone and in reverse order, each mutation is
killed by **its own** gate, with `wording gate OK: 26 rows` printing *before*
each definition kill — direct evidence the wording gate is healthy and the kill
came from elsewhere:

```
[orphaned] ... wording commissioning OK ... wording gate OK: 26 rows
[orphaned] MUTATION KILLED   ORPHANED (defined but never emitted): snr_margin_db
[undefined] ... wording commissioning OK ... wording gate OK: 26 rows
[undefined] MUTATION KILLED  UNDEFINED (ships with no definition): noise_flat
```

`wording commissioning OK` prints in the two definition runs and **not** in the
wording run — the stub is confined to its own process. `commission_wording` is
moot by construction, not by a third `finally`.

I pre-registered the fail mode *"a subprocess that dies for any reason looks like
a kill"*. **Refuted by measurement.** I rebuilt their harness in my own directory
(theirs untouched, verified by hash) and added three controls they do not have:

```
nc_crash     -> RuntimeError propagates            -> exit 1  CORRECTLY FAILED
nc_noland    -> MUTATION DID NOT LAND -- FAIL      -> exit 1  CORRECTLY FAILED
nc_wronggate -> FAIL: stopped, but not by the
                expected gate (no 'UNDEFINED')     -> exit 1  CORRECTLY FAILED
FAIL: 3 of 6 mutations survived or errored: nc_crash, nc_noland, nc_wronggate
```

`nc_wronggate` is the important one: it reproduces the **original** contamination
bug, and the per-mutation expected-token check catches it. So the design is
defended twice over — isolation prevents contamination, and the token check would
catch it even if isolation failed. A crash does not look like a kill.

**My first attempt at these controls was worthless and I nearly shipped it.** All
three "correctly failed" — because my copy lived in a different directory and all
three died of `ModuleNotFoundError` before the mutation ran. Three greens that
measured nothing. I caught it only because I printed tracebacks, and I fixed it
by running a **positive** control first: the real `undefined` mutation must still
kill in my copy before any negative result from it means anything.

## F4 — the gate's limit stated in code: VERIFIED

In the code at three sites, not only in the report:

```
  triage.py:784: # and cannot prove any definition is TRUE -- existence is mechanically
  triage.py:789: # A green here means "readable", never "correct". Definition content needs
  triage.py:806: f"gate cannot check that a definition is TRUE)")
```

and it now prints on every green run:

```
definition gate OK: 31 emitted fields, all defined; no orphaned definitions
(existence and reachability only -- this gate cannot check that a definition is TRUE)
```

My pre-registered fail mode was that my 1-in-3 audited hit rate would be restated
as an estimate for the other 28. It is not:

> The verifier audited **3 of the 31** definitions for *content* [...] and **one
> of the three was wrong** [...] The remaining 28 are unverified.
> That is not a claim that the other 28 are wrong.

Correct on both halves — the limit is stated, the extrapolation is refused.

## H-vacuous-gate — the hazard I registered against their own fix: REFUTED

I registered the risk that deriving `FIELD_DEFS` from the rows would make the
definition gate compare a set against itself and become structurally incapable of
failing, while printing identical green. It did not happen: the key set is
unchanged (`added: []  removed: []`), `FIELD_DEFS` remains a literal dict, and
the decisive evidence is that both definition mutations still **kill**. A gate
incapable of failing cannot be killed.

## Regression — the five original claims

| claim | result |
|---|---|
| 1. definition gate both directions, 31 fields | VERIFIED — `31 emitted fields, all defined; no orphaned definitions` |
| 2. three mutations killed, exit 0 | VERIFIED — killed together, alone, and in reverse order |
| 3. header reads `blur_floor_px` from JSON | VERIFIED — tracks a moved source to `0.99`, degrades to honest absence |
| 4. `fields` + `constants` blocks | VERIFIED — both present, `constants` byte-identical to pre-fix |
| 5. corpus_lint clean, no `crates/` | VERIFIED — `corpus_lint: OK`; `b975efce` touches 3 files, none under `crates/` |

## Verdict

All four fixes verified. F1 is correct under both orderings and correct to the
digit. F3 is stronger than asked — I attacked it with three injected failures and
it caught all three. The one residual is F2, and it is disclosed rather than
hidden: the corrected numbers are prose, no code enforces them, and I showed they
can go stale in silence. That is now a known and stated property of the artifact
rather than an unknown one.
