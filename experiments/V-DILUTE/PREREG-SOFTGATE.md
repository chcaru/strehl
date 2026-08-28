# V-DILUTE pre-registration — is `STREHL_SOFT_GATE` reachable from the default merge?

Written and committed BEFORE any arm ran. Subject `109MSDCF`, N=22 (cheapest
MSDCF stack). Addendum K.1 currently asserts, from reading source only, that
`STREHL_SOFT_GATE` cannot affect the default pyramid backend. That verdict
lives only in prose and has no gate on it — the exact defect ORCH attributes to
V-KILLB0. This commissions it empirically.

## Arms

| id | invocation | prediction |
|----|-----------|-----------|
| A  | default backend, no env | reference |
| A' | identical repeat of A | **identical to A** (determinism control) |
| B  | default + `STREHL_SOFT_GATE=gaussian` | **identical to A** — the claim |
| C  | default + `--pyramid-exponent 4.0` | **differs from A** (sensitivity) |
| D  | `--merge estimator`, no env | reference for E |
| E  | `--merge estimator` + `STREHL_SOFT_GATE=gaussian` | **differs from D** (specificity) |

## Why D/E is not optional

Without it, `A == B` is ambiguous between "the gate is unreachable from the
pyramid path" (my claim) and "the env var is misspelled, unparsed or dead
everywhere" (a much larger, different claim). **An inert plant and a dead
instrument give the identical green.** E must move for B's stillness to mean
what I say it means.

## Why A' is not optional

If the writer embeds a timestamp, every render differs and `A == B` could never
hold regardless of the truth. `A == A'` establishes that byte comparison is a
valid instrument here. If `A != A'` I will fall back to comparing decoded
pixels and will say so.

## Falsification

- `A != A'` → byte comparison invalid; switch to pixels, do not report bytes.
- `A != B` → **Addendum K.1 is REFUTED.** The soft gate does reach the default
  backend. I will say so plainly and withdraw K.1 without reframing it.
- `A == C` → the harness cannot see a change it should see; **all arms void**,
  report nothing.
- `D == E` → the env var is inert everywhere; K.1's *conclusion* survives but
  its *reason* is wrong, and the warning to V-KILLB0 changes from "select the
  estimator backend" to "the gate does not work at all".

## Registered secondary prediction

`strehl stack --help` states the backend is **inferred from flags** when
`--merge` is absent, and that `--gate` (275 call sites) is one of the inferring
flags. I therefore predict a harness that passes `--gate` without `--merge`
lands on the **estimator**, where the soft gate IS live. So the reachability
failure is conditional on the caller's unrelated flags, in both directions.
I have not tested this; it is registered so it can be refused.
