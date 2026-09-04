# M168 — adversarial audit of the orchestrator verification apparatus

**Status: DEFECTS FOUND.** The current apparatus can report `GREEN` or
`COMMISSIONED` after the guarded document has been made materially false. The
strongest demonstrated case makes the M137 sentence assert the opposite of its
own numbers and then obtains `VERDICT: COMMISSIONED`. A second independent case
turns the owner’s Stage-0 kill gate into an instruction that the `1,602`-frame
session is mandatory even when the optics fail; `vowner0906.py` still reports
`GREEN: 14 RED: 0`.

Every mutation in this audit was made in a temporary archive. No file in
`experiments/ORCH-verify/`, `docs/STATUS.md`, `docs/OWNER-ACTIONS.md`, or another
lane was modified.

## 1. Scope and revisions

- **VERIFIED BY RUNNING.** The assignment’s baseline is reproducible from
  commit `f267bbccfd450982720f747c64e383376df2c4f9` plus one untracked input:
  `v2954.py` reports `52/52`, with `46 pass + 0 fail + 6 skipped`, and
  `commission_2957.py` reports `10/10`.
- **VERIFIED BY RUNNING.** The apparatus changed while this audit was in
  progress. I therefore also attacked the latest `v2954.py` revision at close,
  `058a902364eba9e9a5c3dbc914bf03606d327288` (the harness remains at
  `7c65f8a4444d2c2fb239e589f56466da9e7aa7e2`). It reports `61/61`, with
  `55 pass + 0 fail + 6 skipped`; the commissioning harness reports `19/19`.
  Every semantic, duplicate, source-linkage, named-target and crash-recovery
  defect reported below still reproduces on that revision.
- **VERIFIED BY RUNNING.** Final audited component SHA-256 values were:

  | component | SHA-256 |
  |---|---|
  | `v2954.py` | `CBE312BF5475CE51E1E6824118C3CD9B201880C7A286EF946A397C1B9958A229` |
  | `commission_2957.py` | `9DE0B8DA1C4EE28C43AA94EF6A4EB6B220F25B7F9D18C14A8155B6D9C3ABD82D` |
  | `vowner0906.py` | `802507B2F38EE1341069B1721189C5214C5E61EC164050DFA5BB396B7636B1AF` |
  | `probe_generativity.py` | `54E332F2CAD5A225111BADB6553C181DAE797C74A1E958B0D0684EAFFAF18855` |
  | `check_amd6_sha.py` | `B455506A1A64843CCFD7F040E8CB77B801775617279FD949C579D3149BE4B1F3` |
  | `check_amd6_sha2.py` | `502A8D06A40499A7AFBDE41D611B629C93968F764A604CD7FB4B2B7E6B6F7038` |

## 2. Component verdicts

| component | verdict | reason |
|---|---|---|
| `v2954.py` | **NOT FIT FOR PURPOSE** | **VERIFIED BY RUNNING:** opposite meanings, a wrong intended number, an explicit decoy, and absent source numbers all remain `GREEN`. It is a broad token census, not a verifier of the listed claims. |
| `commission_2957.py` | **NOT FIT FOR PURPOSE** | **VERIFIED BY RUNNING:** it commissions a meaning-inverted STATUS and can credit the M137 control while mutating M2 instead. Normal restoration works, but crash/retry recovery destroys the only good backup. |
| `vowner0906.py` | **NOT FIT FOR PURPOSE** | **VERIFIED BY RUNNING:** it accepts the commercial opposite of the owner instruction and accepts a table whose `895` no longer reconciles with `898`; its arithmetic is disconnected hard-coded arithmetic. |
| `probe_generativity.py` | **NOT FIT FOR PURPOSE** | **VERIFIED BY RUNNING:** a cosmetic `default_rng` call followed by acceptance of stored JSON is labelled `GENERATIVE`; both positive and negative verdicts exit zero. |
| `check_amd6_sha.py` | **NOT FIT FOR PURPOSE** | **VERIFIED BY RUNNING:** it tests the raw Git-blob representation, reports `MISMATCH` for the true CRLF artifact claim, and exits zero. |
| `check_amd6_sha2.py` | **SOUND WITH DEFECTS** as an interactive line-ending diagnostic only | **VERIFIED BY RUNNING:** it correctly diagnoses the present LF/CRLF mismatch. It is not an automated verifier: it reads a mutable checkout, does not regenerate, and exits zero even after printing `Real defect`. |

## 3. `v2954.py`

### 3.1 Direct false-GREEN constructions

**VERIFIED BY RUNNING.** This command attacks a temporary archive of the latest
revision:

```powershell
python -B experiments\M168-orchestrator-verifier-audit\semantic_attacks.py HEAD
```

Exact result lines:

```text
BASELINE v2954: exit=0 | VERDICT: GREEN
FALSE_GREEN identity polarity reversed: exit=0 | GREEN veto identity token      IDENTITY_EQUIVALENT | VERDICT: GREEN
FALSE_GREEN recommission passed changed to failed: exit=0 | GREEN recommission status      PASS | VERDICT: GREEN
FALSE_GREEN improvement plant explicitly absent: exit=0 | GREEN improvement plant present planted improvement  [pinned] | VERDICT: GREEN
FALSE_GREEN M1 withdrawal explicitly revoked: exit=0 | GREEN m1 withdrawn             NO ADMISSIBLE BAR | VERDICT: GREEN
FALSE_GREEN M2 interpretation reversed: exit=0 | GREEN m2 battery replay        0.5712148772282098  [pinned] | VERDICT: GREEN
FALSE_GREEN 96 corrupted to 97 while another 96 survives elsewhere: exit=0 | GREEN M1 per-class frames      96  [pinned] | VERDICT: GREEN
FALSE_GREEN both M167 source numbers removed: exit=0 | GREEN m137 flat beats detail   1.0249391472947889  [pinned] | GREEN m2 battery replay        0.5712148772282098  [pinned] | VERDICT: GREEN
FALSE_GREEN real M137 value wrong but withdrawn decoy present: exit=0 | GREEN m137 flat beats detail   1.0249391472947889  [pinned] | VERDICT: GREEN
AUDIT_ATTACKS: ALL REPRODUCED
```

The exact mutations are in `semantic_attacks.py`; the five semantic mutations
were:

1. `does **not** fire on exact identity` → `does fire on exact identity`;
2. `recommissioned ... **passed**` → `... **failed**`;
3. `a planted ... improvement` → `no planted ... improvement`;
4. `records M1 as ... WITHDRAWN` → `no longer records M1 as ... WITHDRAWN`;
5. `blur *improves* ... favourable` → `blur *worsens* ... unfavourable`.

**VERIFIED BY RUNNING.** The `96 → 97` case still passes after the latest
boundary-aware `positions()` change. That change prevents `96` from matching
inside `896`, but the concatenated STATUS scope contains seven other standalone
`96` tokens, so the intended site remains unbound.

**VERIFIED BY RUNNING.** For the M137 decoy case, the real table value was
changed from `1.0249391472947889` to `1.0249391472947880`; the old number was
inserted elsewhere in the guarded sections with the explicit description
“Withdrawn false value retained only as a decoy.” The claim remained GREEN.

**VERIFIED BY RUNNING.** In the source-linkage case, every occurrence of
`1.0249391472947889` and `0.5712148772282098` was removed from the scratch copy
of `docs/research/M167-detail-battery.md`. Both source-backed claims remained
GREEN.

### 3.2 Why those attacks work

- **INFERRED BY READING.** All currently guarded STATUS sections are collapsed
  into one string (`v2954.py:19-20, 180-181`), and `in_status` asks only whether a
  matching token exists anywhere in that aggregate (`:251`). A claim is not
  bound to its section, sentence, row, subject, or polarity.
- **INFERRED BY READING.** `src_literal` replaces the claimed needle at
  `v2954.py:261`; it is not an additional anchor. M137 therefore checks source
  prose `exceeded detail`, and M2 checks `Independent replay returned`, instead
  of checking either reported number.
- **INFERRED BY READING.** `ctx` is consumed only by source-side `found()` at
  `:228-237,262`. STATUS matching at `:251` receives no context. At the assigned
  52-claim revision no live claim had `ctx`; the latest 61-claim revision has
  seven, but all seven remain source-only.
- **VERIFIED BY RUNNING.** On the latest revision there are 14 non-unique STATUS
  probes and 18 non-unique source probes. Examples are `96` at eight STATUS
  sites, `PASS` at five sites, `2.0312` at three sites, and `1,602` at two sites.
  The checker requires at least one match, not the intended unique match.
- **INFERRED BY READING.** The internal “negative controls” at `:280-300` do not
  mutate STATUS or execute the claim end to end. They alter the probe string in
  memory and ask whether that decoy already occurs in the source. `controls
  pass` therefore means “this particular one-digit decoy was absent,” not “the
  checker detected corruption.”
- **INFERRED BY READING.** `ctl_skip` is omitted from the final GREEN condition
  at `:376-377`. A skipped control is treated as accounted and cannot prevent
  GREEN.

### 3.3 The six skipped controls

**VERIFIED BY RUNNING.** `claim_inventory.py HEAD` reports exactly the same six
skips after the checker grew from 52 to 61 claims.

| skipped claim | what it really checks | ruling |
|---|---|---|
| `veto identity token` | Presence of `IDENTITY_EQUIVALENT` in both broad scopes. | Not a valid semantic control. Reversing “does not fire” to “does fire” remains GREEN. No commissioning mutation covers it. |
| `recommission status` | STATUS needle `PASS` anywhere plus source `PASS`. The intended STATUS sentence contains lowercase `passed`, not uppercase `PASS`; five unrelated uppercase decoys currently satisfy it. | Silent no-op at the intended site. Changing the intended result to `failed` remains GREEN. No commissioning mutation covers it. |
| `improvement plant present` | STATUS prose `planted improvement`; source key `improvement_plant`. | Does not pin presence/polarity. “no planted improvement” remains GREEN. No commissioning mutation covers it. |
| `m1 withdrawn` | Phrase `NO ADMISSIBLE BAR` in each broad scope. | Does not pin whether withdrawal is operative. Explicitly revoking it remains GREEN. No commissioning mutation covers it. |
| `m137 flat beats detail` | STATUS number, but only source prose `exceeded detail` because `src_literal` replaces the number. | Its STATUS digit is commissioned, but its source number and meaning are not. The skip reason conceals that split. |
| `m2 battery replay` | STATUS number, but only source prose `Independent replay returned`. | Same defect as M137. Its STATUS digit is commissioned; its source number and meaning are not. |

Thus the skip is mechanically expected from the current code, but it is not a
legitimate “pass.” Four claims have no demonstrated mutation at all; the other
two have only a STATUS-number mutation.

### 3.4 Minimum correction requirements

1. Each claim must identify one exact STATUS section and one exact sentence,
   row, or structured field, with an expected occurrence count.
2. Source anchors must be additive: require both `src_literal` and the claimed
   numeric token in the same parsed record. Never substitute prose for the
   number.
3. Context and occurrence constraints must apply independently to STATUS and
   source.
4. Semantic claims must encode the relation and polarity being asserted, not
   only one noun or number.
5. A skipped control must make the apparatus `UNCOMMISSIONED` unless an explicit
   waiver is reported; it must not contribute to an all-accounted GREEN.
6. Every source must be present in the audited commit, not merely in one live
   working tree.

## 4. `commission_2957.py`

### 4.1 A wrong document is still commissioned

**VERIFIED BY RUNNING.** I changed the M137 sentence from

```text
flat gap 0.348854... exceeded detail gap 0.340366...; ... above real detail
```

to the mathematically opposite

```text
flat gap 0.348854... fell below detail gap 0.340366...; ... below real detail
```

while retaining every digit. The harness output was:

```text
FALSE_COMMISSION semantic inversion: exit=0 | VERDICT: COMMISSIONED | wrong_meaning_survived_restore=True
```

This is the requested example where the apparatus reports commissioned on a
document that is actually wrong.

**VERIFIED BY RUNNING.** I then changed only the scratch harness so its control
label remained `m137 flat beats detail` while its anchor and replacement were
the M2 number. It never mutated M137. Exact output:

```text
FALSE_COMMISSION wrong claim mutated: exit=0 | RED   m137 flat beats detail       control PASSED | VERDICT: COMMISSIONED
```

**INFERRED BY READING.** This is permitted by `commission_2957.py:126`: any
nonzero verifier exit or any aggregate `VERDICT: RED` counts as caught. The
optional label-specific search at `:129-132` affects display only. It is not
part of the acceptance condition.

### 4.2 Restore semantics

**VERIFIED BY RUNNING.** Normal completion does exactly what the current
message says:

```powershell
python -B experiments\M168-orchestrator-verifier-audit\restore_crash.py HEAD
```

```text
NORMAL exit=0
restore     : byte-identical to backup
final run   : GREEN
controls    : 19 caught + 0 missed = 19 of 19
VERDICT: COMMISSIONED
NORMAL_ORIGINAL_SHA=0C52B4D26A862A0226AC9D0B7163CFC03A022C82B8F625C32194DD041B67B875
NORMAL_RESTORE_BYTE_IDENTICAL=True
```

So `restore: byte-identical` is true for ordinary completion.

**VERIFIED BY RUNNING.** It is false as a crash-safety claim. The reproduction
injects `os._exit(77)` into a temporary harness immediately after its first
STATUS write, then retries with the untouched harness:

```text
INJECTED_CRASH_EXIT=77
STATUS_MUTATED_AFTER_CRASH=True
ORIGINAL_BACKUP_RECOVERABLE_AFTER_CRASH=True
RETRY_EXIT=1
ORIGINAL_BACKUP_DESTROYED=True
STATUS_STILL_MUTATED=True
MUTATED_SHA=1196A4DB67F1D352897930B2D068CF93527E73B068CFC0073A42871951DE4603
RESTORE_ATTACK: REPRODUCED
```

**INFERRED BY READING.** The cause is exact: the fixed backup path is declared
at `commission_2957.py:23`; `copy2(STATUS, BACKUP)` overwrites it at `:99`
before the baseline precondition; precondition failure returns at `:104-107`,
before the `try/finally` beginning at `:111`. A retry therefore replaces the
recoverable original backup with already-mutated STATUS and then exits without
restoring. The same fixed filename also permits two concurrent runs to collide;
that concurrency case is inferred from the path, not separately exercised.

### 4.3 Coverage and required correction

- **VERIFIED BY RUNNING.** At assignment time the harness covered 10 of 52
  claims. The latest covers 19 of 61. All are STATUS digit changes. It has no
  source-side, polarity, attribution, wrong-section, duplicate-decoy, missing
  source, or benign-edit controls.
- **Required correction.** Commission temporary copies passed through a
  parameterized verifier; do not mutate authoritative STATUS in place.
- **Required correction.** Require the named claim to turn RED. An unrelated
  RED must count as a failed control.
- **Required correction.** Add semantic, source-side, duplicate, wrong-section,
  missing-source and benign controls.
- **Required correction if live mutation is retained.** Use a per-run immutable
  backup, exclusive lock, atomic replacement, durable recovery marker, and
  startup recovery before any backup can be overwritten.

## 5. `vowner0906.py`

**VERIFIED BY RUNNING.** Replacing the Stage-0 instruction with

```text
Even if the optics cannot support the required sampling ratio,
the entire 1,602-frame session is mandatory and must proceed anyway
```

produced:

```text
FALSE_GREEN owner kill gate inverted to mandatory shoot: exit=0 | GREEN: 14  RED: 0 | VERDICT: GREEN
```

**VERIFIED BY RUNNING.** Changing the table’s rehearsal row from `896` to
`895`, while retaining cumulative `898`, produced:

```text
FALSE_GREEN owner table says 895 but hardcoded arithmetic says 896: exit=0 | GREEN rehearsal frames       896 | GREEN arith  stages 1-5 sum to 896 | GREEN arith  stage 0 + rehearsal = 898 | VERDICT: GREEN
```

**INFERRED BY READING.** Figure checks at `vowner0906.py:50-71` are unanchored
substring searches anywhere in one broad owner block and anywhere in the whole
source. The arithmetic at `:75-84` uses Python literals
`[128,160,128,224,256]`; it never parses the owner table. The `1,603` control at
`:108` is another constant arithmetic expression, not an input mutation.

**Required correction.** Parse the exact table rows and derive all totals from
those parsed cells. Bind each owner claim to one canonical sentence and its
source record, including the conditional direction. Add end-to-end semantic
and benign mutations.

## 6. Defect not named in the assignment: the checker enforces a false future date

**VERIFIED BY RUNNING.** The session date is 2026-09-04. `date_audit.py` found
15 operative `2026-09-06` markers in orchestrator-owned STATUS,
OWNER-ACTIONS, and host-policy evidence; every one was introduced by a commit
authored on 2026-09-04:

```text
OPERATIVE_2026_09_06_MARKERS=15
INTRODUCED_ON_2026_09_04=15
```

The population is eight STATUS markers, six OWNER-ACTIONS markers, and the
`date` field in `host-policy-broadcast-2026-09-06.json`. This excludes the later
STATUS sentence that merely describes already-corrected date defects.

**VERIFIED BY RUNNING.** Correcting the guarded OWNER-ACTIONS heading from
`2026-09-06` to `2026-09-04` makes the verifier reject the correction:

```text
FALSE_RED corrected owner heading date: exit=1 | FATAL: owner block heading not found
```

**INFERRED BY READING.** `vowner0906.py:18` hard-codes the false future heading,
so the apparatus is not merely blind to this date defect; it actively enforces
it. This is the same defect class already corrected in Amendments 3, 5 and 6,
but it remains in 15 additional operative sites.

**Required correction.** Correct the operative markers to `2026-09-04` (or
explicitly label them as a future effective date rather than a completed
update), rename/repoint the evidence paths consistently, and derive audit dates
from recorded provenance instead of a hard-coded heading.

## 7. Defect not named in the assignment: GREEN depends on an uncommitted source

**VERIFIED BY RUNNING.** The live claim `clamped flat null structure` cites
`experiments/M134-kernel-frontier/M137-clamped-detail.md`
(`v2954.py:148`). At audit close:

```text
M134_DEPENDENCY_TRACKED=False
```

The file existed only as an untracked working-tree file, SHA-256
`8EA64C98795E51BC007E04775866C2145D1E2D6CFBA9F4F13B8413A3721FD1EF`.
A clean checkout of the commit that reports GREEN cannot reproduce that GREEN.

**Required correction.** A claim may enter the apparatus only after its source
is committed and pinned. The verifier should reject untracked source inputs or
record their content hash and state explicitly that the run is non-reproducible.

## 8. `probe_generativity.py`

**VERIFIED BY RUNNING.** The current repaired M164 verifier does call
`default_rng`, and blocking it breaks the named fresh-regeneration check:

```text
CURRENT_TARGET probe_exit=0 | === generativity probe: np.random.default_rng forced to raise === | FAIL fresh commission regeneration: RuntimeError: default_rng blocked by generativity probe | === default_rng call attempts: 1 === | === exit under blocked RNG: 1 === | VERDICT: GENERATIVE -- blocking the RNG broke the verifier, as it must.
```

That is useful evidence of RNG dependency for this target.

**VERIFIED BY RUNNING.** It is not proof of generativity in general. A fake
target made one cosmetic RNG call, discarded it, and then accepted stored JSON:

```text
COSMETIC_TARGET direct_exit=0 direct_output=PASS: stored result accepted
COSMETIC_TARGET probe_exit=0 | === generativity probe: np.random.default_rng forced to raise === | === default_rng call attempts: 1 === | === exit under blocked RNG: 99 === | VERDICT: GENERATIVE -- blocking the RNG broke the verifier, as it must.
NO_RNG_TARGET probe_exit=0 | === generativity probe: np.random.default_rng forced to raise === | === default_rng call attempts: 0 === | === exit under blocked RNG: 0 === | VERDICT: NOT GENERATIVE -- verifier never asked for an RNG at all.
```

Both probe verdicts exit zero. **INFERRED BY READING:** it intercepts only
`np.random.default_rng`, so a genuinely generative verifier using another RNG
API can also be labelled non-generative.

**Required correction.** Rename the present conclusion to
`DEFAULT_RNG_IS_LOAD_BEARING`, return nonzero on the negative verdict, and do not
claim generativity until a named regenerated artifact or claim-bearing value is
shown to depend on fresh generated inputs.

## 9. SHA probes

**VERIFIED BY RUNNING.** `probe_attacks.py` produced:

```text
SHA_PROBE_1 exit=0 | MISMATCH  experiments/M164-m2-repair/commission.json
SHA_PROBE_2 exit=0 | VERDICT: the plan's figure is CORRECT. The mismatch was a line-ending
WRONG_SHA_CLAIM probe_exit=0 | VERDICT: figure is wrong on both representations. Real defect.
```

`check_amd6_sha.py` hashes the canonical Git blob; the plan’s recorded SHA is
for the CRLF exported/checkout artifact. It therefore answers a different byte
question and false-alarms on the true claim. `check_amd6_sha2.py` correctly
identifies that distinction, but it reads mutable working-tree bytes and never
regenerates the artifact. Neither uses exit status as a verdict.

**Required correction.** Define the byte representation in the claim, use an
isolated historical archive, rerun commissioning when claiming reproduction,
and exit nonzero on mismatch or a `Real defect` branch.

## 10. Reproduction files

- `experiments/M168-orchestrator-verifier-audit/semantic_attacks.py`
- `experiments/M168-orchestrator-verifier-audit/claim_inventory.py`
- `experiments/M168-orchestrator-verifier-audit/restore_crash.py`
- `experiments/M168-orchestrator-verifier-audit/probe_attacks.py`
- `experiments/M168-orchestrator-verifier-audit/date_audit.py`
- `experiments/M168-orchestrator-verifier-audit/boundary_attacks.py`

All scripts use temporary trees. The default target is the assignment’s
52-claim revision; pass `HEAD` to the first three scripts to test the latest
revision. The untracked M134 dependency is used only if its audited hash
matches; a clean checkout receives a one-token scratch fixture for that
unrelated presence claim.


## 11. Re-audit of the `7c65f8a4` boundary repair

This section responds to the later request to re-read and attack the revised
apparatus. It supersedes any earlier implication that `positions()` had closed
the duplicate-number problem.

- **VERIFIED BY RUNNING.** The requested revision
  `7c65f8a4444d2c2fb239e589f56466da9e7aa7e2` reproduces its `61`-claim GREEN
  baseline and the `19/19` commissioning population.
- **VERIFIED BY READING AND RUNNING.** The shared tree advanced again during
  this re-audit. `v2954.py` was later touched at
  `31daf74cf21a26ed50d067951f32c11caff6e1ef`, but the bodies of `variants()`,
  `rounds_to()` and `positions()` are unchanged from `7c65f8a4`. The complete
  boundary attack also reproduced against that later live checker.

### 11.1 Direct attack on `positions()` and `rounds_to()`

**VERIFIED BY RUNNING.** `boundary_attacks.py` extracts the three functions from
the audited checker AST and calls those exact definitions. Four controls behave
correctly: an exact decimal matches; strict mode rejects `2.031203` as
`2.0312`; source mode accepts `2.031203` because it rounds to `2.0312`; and it
rejects `2.03126` because that rounds to `2.0313`.

Eleven edge results are defective:

| case | expected | actual | failure |
|---|---:|---:|---|
| positive `0.27` in `-0.27` | false | true | false GREEN; sign is ignored |
| integer `96` in decimal `0.96` | false | true | false GREEN; suffix of a larger number |
| integer `96` in `96.5` | false | true | false GREEN; decimal point is accepted as a boundary |
| `1,602` in `1,602,000` | false | true | false GREEN; comma is accepted as a boundary |
| numeric `96` in hex `A96F` | false | true | false GREEN; hex letters are accepted as boundaries |
| full SHA followed by another hex digit | false | true | false GREEN; SHA token boundary is not checked |
| scalar `1.11` in `1.11e-15` | false | true | false GREEN; exponent marker is accepted as a boundary |
| rounded source `1.5604%` for `1.560%` | true | false | false RED; suffix prevents `extend` from running |
| rounded source `2.031203x` for `2.0312x` | true | false | false RED; same unit-suffix defect |
| rounded source `1.1100e-15` for `1.11e-15` | true | false | false RED; scientific notation is unsupported |
| decimal midpoint `2.675` for `2.67` | false under decimal half-even | true | false GREEN from binary-float formatting |

**INFERRED BY READING.** The cause is that only adjacent decimal digits are
considered continuations. Signs, decimal points, commas, exponent markers,
percent signs, units and hexadecimal letters are all treated as boundaries.
`rounds_to()` derives precision with `len(short.split(".")[1])` and converts
through binary `float`, so its name “rounds exactly” is stronger than its
implementation.

### 11.2 Full-verifier witnesses

**VERIFIED BY RUNNING.** These are not helper-only hypotheticals. Temporary
copies of the complete verifier produced:

```text
INTEGRATION_FALSE_GREEN negative exponent: exit=0 | GREEN aperture airy calibration error 1.11e-15 | VERDICT: GREEN
INTEGRATION_FALSE_GREEN comma-grouped larger count: exit=0 | GREEN M1 capture exposures     1,661 | VERDICT: GREEN
INTEGRATION_FALSE_GREEN SHA with appended hex digit: exit=0 | GREEN m167 results sha         210675AB3BC25FCE53EE090AAEE98E69330E95F3EC8C19FDC1CA59BCEF9229B0 | VERDICT: GREEN
MIS_SLOT_REPAIR numeric source mutation: exit=1 | RED   ref info dominance ratio 0.698970 NOT IN docs/research/M164-reference-identifiability.md | VERDICT: RED
CTX_FALSE_GREEN negated nearby decoy: exit=0 | GREEN ref info dominance ratio 0.698970  [anchor a ratio of] | VERDICT: GREEN
INTEGRATION_FALSE_GREEN negative source ratio: exit=0 | GREEN ref info dominance ratio 0.698970  [anchor a ratio of] | VERDICT: GREEN
INTEGRATION_FALSE_RED rounded percent source: exit=1 | RED   margin over bar          1.560% NOT IN docs/research/M164-reference-identifiability.md | VERDICT: RED
```

The first three mutations respectively changed `1.11e-15` to `-1.11e-15`,
`1,661` to `1,661,000`, and appended `A` to the guarded SHA. The repaired tuple
placement correctly catches an ordinary source digit change from `0.698970` to
`0.698971`. It nevertheless accepts ``ratio `0.698971` (not `0.698970`)``: the
expected value is merely a negated decoy inside the context window. Changing the
only source value to `-0.698970` separately proves that the new boundary matcher
erases sign. Increasing source precision from `1.560%` to `1.5604%` proves the
complementary false RED.

**VERIFIED BY RUNNING.** Exact matcher inventory at `7c65f8a4` found twelve
claims with multiple STATUS matches and eighteen with multiple source matches
after applying each claim's optional context filter. All seven newly
contextualized M164 source probes happen to have exactly one match in the
current source. That is a property of this snapshot, not a sound context
implementation: `ctx` is source-only, is any substring in a fixed +/-160-
character window, has no expected occurrence count, and accepts the negated-
decoy witness above.

### 11.3 Adjudication of the two self-reported defects

**Prefix no-op — CONFIRMED, and the narrow repair works.** Mutating the
canonical STATUS site from `2.0312` to `2.0313` gives:

```text
PREFIX_REPAIR current: exit=1 | RED   preflight design ratio   2.0312 NOT ASSERTED IN STATUS ... | VERDICT: RED
PREFIX_REPAIR reconstructed_bare: exit=0 | GREEN preflight design ratio   2.0312 | VERDICT: GREEN
```

The reconstructed bare matcher is satisfied by unrelated `2.031203`. The new
strict prefix rule catches that exact defect.

**Tuple mis-slot — CORE DEFECT CONFIRMED; REPORTED POPULATION NEEDS
CORRECTION.** The bad intermediate state was not committed, so its literal
contents are not independently recoverable. Reconstruction from the current
claim table gives:

```text
MIS_SLOT first_five: exit=0 skipped=11
MIS_SLOT all_seven: exit=0 skipped=13 | GREEN ref info dominance ratio 0.698970  [pinned] | VERDICT: GREEN
MIS_SLOT all_source_numbers_changed: exit=0 | GREEN ref info dominance ratio 0.698970  [pinned] | GREEN ref bits inferior 1.160964  [pinned] | GREEN margin over bar 1.560%  [pinned] | VERDICT: GREEN
```

Moving only five anchors into `srclit` raises skips from six to eleven. The
reported jump from six to thirteen requires **seven**, exactly the seven M164
reference claims present in `7c65f8a4`. Therefore “five” and “six to thirteen”
cannot both describe the same claim table. Either seven claims were mis-slotted
or two additional mis-slots were omitted from the account.

**Judgment.** Finding the tuple defect only by manually reading the skip summary
is damning: the run remained GREEN and no source-side commissioning arm existed.
A typed/non-positional schema plus one source mutation per claim would catch it
by construction. Finding the prefix collision is narrowly reassuring: the
canonical-site commissioning mutation did exactly what such a control should do
and reported the no-op. It does not rehabilitate the harness because it still
accepts an unrelated RED as a caught named control and tests only 19 status
numbers.

### 11.4 Exact replacement contract

A safe repair cannot be another punctuation condition in `positions()`. The
single overloaded `needle` cannot represent different STATUS/source literals,
units, token kinds, contexts and rounding policies. Replace the positional tuple
with this explicit contract:

```python
@dataclass(frozen=True)
class SiteProbe:
    anchor: str
    value: str
    kind: Literal["literal", "decimal", "sha256"]
    expected_count: int = 1
    rounding: Literal[None, "decimal-half-even"] = None

@dataclass(frozen=True)
class Claim:
    label: str
    section: str
    status: SiteProbe
    source_path: str
    source: SiteProbe
```

For `decimal` probes, extract the **whole signed numeric token**, including
comma grouping, fraction, exponent and `%`/`x` unit, with this grammar:

```python
DECIMAL_TOKEN = re.compile(
    r"(?<![0-9A-Za-z_.,+\-])"
    r"(?P<num>[+\-]?(?:\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d+)?(?:[eE][+\-]?\d+)?)"
    r"(?P<unit>%|x)?"
    r"(?![0-9A-Za-z_.,+\-])"
)
```

The required behavior is exact:

1. Preserve and compare the sign.
2. Require the candidate unit to equal the declared unit.
3. In STATUS, require the normalized complete lexeme, including precision, to
   equal the declared value.
4. In a source with rounding enabled, parse with `Decimal`, derive the quantum
   from the declared `Decimal` exponent, and use explicitly declared
   `ROUND_HALF_EVEN`; never use binary `float`:
   `candidate.quantize(Decimal(1).scaleb(expected.as_tuple().exponent),
   rounding=ROUND_HALF_EVEN) == expected`.
5. For `sha256`, require exactly 64 hex characters with non-hex boundaries.
6. For `literal`, require the declared unique anchor and value; never scan the
   concatenation of all sections.

Replace the commissioning acceptance condition

```python
red = rc != 0 or "VERDICT: RED" in out
```

with the named condition

```python
named_red = any(
    line.startswith("RED   ")
    and line[6:6 + len(label)] == label
    and line[6 + len(label):].startswith(" ")
    for line in out.splitlines()
)
caught_this_control = rc != 0 and named_red
```

and replace the overall GREEN condition so any uncommissioned claim is fatal:

```python
commissioned = (
    red == 0
    and ctl_fail == 0
    and ctl_skip == 0
    and every_claim_has_status_and_source_mutations
)
```

Until those conditions exist, the honest summary text is:

```text
VERDICT: TOKEN-PRESENCE SMOKE TEST ONLY; NOT A CLAIM VERIFIER;
6 CLAIMS HAVE NO DEMONSTRATED CONTROL
```
