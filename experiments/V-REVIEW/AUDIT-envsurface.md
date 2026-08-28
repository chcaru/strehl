# Env-var surface: the direction my earlier audit did not test

Addendum to `AUDIT-user-surface.md`. Prompted by the ORCH broadcast of
2026-08-27. Neither withdrawal touches a V-REVIEW result (section 1); checking
them exposed a one-sided gap in my own committed audit, measured in section 2.

All counts MEASURED at HEAD `d35f9055` by `audit_envvars.py`,
`audit_prov_env.py` and `audit_prov_sites.py`.

---

## 1. Both withdrawals are clean for V-REVIEW

**The `17 PASS / 5 FAIL / 4 REVIEW` split was never quoted here.** A grep of
`experiments/V-REVIEW/` for `17 PASS|5 FAIL|4 REVIEW` returns zero hits. My
adjudication was built on the `16 PASS / 1 FAIL / 9 REVIEW` split transcribed
from `printready-v3.txt`, and `vr_master.py:16` carries that transcription with
a digit-for-digit self-check. More to the point, the method was a per-subject
master-versus-source-frame ratio, not a PASS-count diff, so it cannot
manufacture a win from a wrong baseline.

**The `16 -> 17 PASS` delta is outside my work and I offer it no support.**
`vr_master.py` holds only the 9 REVIEW rows plus one PASS control
(`109MSDCF`); the FAIL subject was never in my table. Applying ORCH's own
instrument-identity rule to ORCH's own number: that delta is measured across
*two* instruments -- the saved `orch_printready.py` output in
`printready-v3.txt` at one end and `recert.py` at the other. Until one
instrument reports both endpoints it is an instrument change, not a fix's win.

**"The gate never fires above level 0" was never used.** My only gate numbers
are potency differentials -- `--pyramid-gate 8.0` moves 96.96% of decoded
samples and 16.27% of the confidence map -- which measure whether the flag
moves output, not the band duty cycle. Unaffected by the withdrawal.

---

## 2. The gap: I tested one direction and reported it as if it were both

`AUDIT-user-surface.md` records this clean negative:

> **No environment variable is documented but dead.** All eight in
> `stack --help` are read by shipping code.

That tests *documented -> read*. It says nothing about *read -> documented*,
and I wrote it in a form that reads like a complete finding. The arrival of
`STREHL_GATE_FLOOR_SCALE` in `f190a0ea` made the omission worth measuring.

| quantity at `d35f9055` | count |
| --- | --- |
| `STREHL_*` read by non-test shipping `.rs` | **44** |
| documented but never read | **0** |
| named in the shipping README (987 lines) | **0** |
| named in the repo `README.md` | **3** |
| named only in a `///` or `help =` string | **31** |
| undocumented in any surface checked | **10** |

3 + 31 + 10 = 44: every variable read is accounted for in exactly one bucket,
so a variable cannot be silently skipped into looking documented.

**The original clean negative HOLDS, and now at 44 rather than 8** -- there is
still no documented-but-dead variable. The new fact is the other direction.

*Negative control on the zero:* the shipping README was confirmed opened and
read -- 64,871 chars, 987 lines, 29 matches for `strehl` -- so its `0` env-var
mentions is a measurement, not a swallowed file-open error. My scanner skips
missing files silently and that zero would otherwise be unreadable.

---

## 3. A finding I nearly filed, withdrawn by measuring it

I suspected the provenance files did not record environment state, which would
have made every reproduce line incomplete. **That is false.** All 26 SHIP-V3
provenance files name exactly 39 variables -- min 39, max 39, intersection ==
union == 39 -- each with an applicability note of the form:

```
STREHL_FIX_CA = (unset)  [cleared by harness; built-in default: on
(gear-matched); backend applicability UNCLASSIFIED in the registry]
```

The provenance is better than I assumed before I measured it. Recorded here
because an unmeasured suspicion published as a finding is a false accusation,
and this one was one command away from being written down.

---

## 4. Ranked, VERIFIED

**1. `STREHL_GATE_FLOOR` and `STREHL_GATE_FLOOR_SCALE` are output-affecting and
recorded in no provenance file.** `gatefloor.rs:81,89,102,120`. The project's
own `byte-freeze.rs:416-422` puts `STREHL_GATE_FLOOR` in the freeze env set,
which is its own statement that the variable changes bytes. Its doc comment
says `STREHL_GATE_FLOOR=white` *restores the shipping behaviour* -- so **unset
at HEAD is not the shipped floor**. Path: `merge_cmd`, the shipping dispatch.
*Severity HIGH for reproducibility.* A reviewer replaying a SHIP-V3 provenance
line against a HEAD binary gets a different gate floor and the file does not
say so. **Caveat, and it matters: SHIP-V3 predates `f190a0ea`, so this is a
HEAD-versus-pin divergence, not an error in the delivered files.**

**2. The four `STREHL_DEFECT*` variables cannot fire on a `strehl stack` run.**
They are read only in `stack.rs`. At HEAD `main.rs:1084` dispatches
`Command::Stack` to `merge_cmd::run`, while `stack::run` is reached only by
`Command::ArgmaxBaseline` (`main.rs:856`). This is the same shape as
`merge_cmd.rs:435` and as my exposure finding: **true of a path, and not of the
path that ships.** *Severity MEDIUM.* I have **not** measured whether defect
correction reaches the shipping path by flag instead -- `merge_cmd.rs` defect
wiring belongs to another lane and I did not read it as mine to adjudicate.

**3. 31 of 44 variables are described only in Rust doc comments.** Not false
statements -- silence, not lies -- but invisible to any user who does not read
the source. *Severity LOW-MEDIUM* against a finished-product bar.

## 5. SUSPECTED, deliberately not promoted

- **The 10 fully undocumented variables.** Several are plainly dump or debug
  switches (`STREHL_PYRAMID_WEIGHT_DUMP`, `STREHL_DUMP_MERGE_STATE`,
  `STREHL_BIMODAL_DUMP`). I did not sweep any of them for potency, so I make no
  claim that they are user-relevant. Naming them as defects would be the
  unconditional-top-N error in another costume.
- **3 variables recorded in provenance but read only by tests**
  (`STREHL_CAPTURES`, `STREHL_EDGE_CONF`, `STREHL_FREEZE_REQUIRE`). This is the
  safe direction of error. Not a defect.

## 6. Staleness of my own potency table

`AUDIT-potency.md` was measured at `6c36106c`. HEAD is `d35f9055`, seven
commits later, including `ac1c5cdf` (`MAX_EXPONENT` CLI-bypassable via
`--pyramid-sharpen 1.0`), which touches a flag in my table, and `f190a0ea`,
which adds gate behaviour. **Those verdicts are a snapshot at `6c36106c` and I
have not re-run them.** Per discipline 34 they should be re-swept before any
of them is quoted in a shipping claim.
