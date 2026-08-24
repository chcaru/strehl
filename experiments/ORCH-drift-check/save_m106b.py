"""Append the coffee-bean fixture verification to the M106 report."""
import io

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\M106-freeze-attribution.md"

SECTION = """
---

## Addendum — independent verification of M95's `coffee-bean` freeze

*Transcribed by the orchestrator from M106-freeze's fifth turn. Commissioned
**before** M108-freeze-test reported and deliberately isolated from it: if one
agent both selects a fixture and verifies it, nobody has checked the selection.
The verifier was instructed not to read M108's work and did not.*

**Verdict: `D99F5D82` is NOT stale — it is under-specified.** It reproduces
exactly, at both M95's commit and HEAD, but **only with `STREHL_ALIGN=0`**,
which appears nowhere in the record.

Command, all four rows: `strehl.exe stack <dir>\\coffee-bean --limit 20 --gate 2.0 --out <out>`

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
verifier wrote none of these; all its runs targeted `D:\\m106-scratch\\coffee-bean`
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
"""


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    assert "Addendum" not in text, "addendum already present"
    assert "my instructions bar me from writing findings to disk." in text
    text = text.rstrip("\n") + "\n" + SECTION
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("appended addendum, %d lines total" % len(text.split("\n")))


if __name__ == "__main__":
    main()
