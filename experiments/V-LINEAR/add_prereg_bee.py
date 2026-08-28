"""Append the bee-1-cpl pre-registration to PREREG-NARROW.md.

Written and committed BEFORE the sweep finishes, because ORCH has already
directed another lane to score on this subject at this slice and the honest
value of the result depends on the criterion existing first.
"""
import io
import os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PREREG-NARROW.md")

ADD = """
---

## Addendum: `bee-1-cpl` at 0.30–0.35 (registered before the sweep finished)

ORCH's item 3. He has told the pyramid lane to score the confidence-dependent
exponent at depth on `bee-1-cpl`, on the strength of its **0.30–0.40 R=4.732
PASS**. That instruction is only sound if the subject qualifies at the slice
that lane will actually use. His words: *"If that one fails, I have misdirected
them and I need to know tonight."*

The develop for this subject was purged in the disk emergency and has been
re-made at the pin. It is **not assumed** equivalent to the purged one:

> **Acceptance condition for the re-develop.** All 12 pre-existing bands must
> reproduce the committed record **exactly**. If any moves, the re-develop is
> not the subject the committed table describes, and no narrow-band number from
> it may be compared with the other four subjects. Report that instead.

This single check tests the re-develop and the RNG-append property together.

### What each outcome means, decided now

- **PASS (R ≥ 2.0).** The direction is licensed at the exact slice. Report the
  value and say plainly that ORCH's item-3 instruction stands.
- **MARGINAL (1.5 ≤ R < 2.0).** The wide-band PASS does **not** narrow cleanly.
  The instruction is partially misdirected and must be reported as such, not
  rounded up to "qualified" because 4.732 was comfortable.
- **FAIL (R < 1.5).** ORCH has misdirected the pyramid lane and must be told
  tonight, unhedged.

### The discriminator, if it FAILs

A drop from 4.732 to below 1.5 would be far larger than anything seen so far,
so a FAIL would raise a second question: is it the subject, or does the narrow
band collapse on **deep** stacks generally? That is already answerable without
new work. `dry-erase-marker-head-cpl` is the same depth (N=300) and is already
measured at **0.30–0.35 R=4.530 PASS**, narrowing only −7.1% from its wide
band. So:

- both deep subjects narrow cleanly → a bee FAIL is **subject-specific**;
- only `dry-erase` narrows cleanly → still subject-specific, but the pyramid
  lane should be redirected to `dry-erase`, which is measured and qualified.

There is no outcome in which a bee FAIL licenses the exponent work to continue
on bee. Recording that now so it cannot be reasoned around afterwards.

### Expected value, stated so that agreement is not read as confirmation

`dry-erase` (N=300, wide 4.877) narrowed −7.1%. If `bee-1-cpl` behaves the
same, its narrow value lands near **4.4 and PASSes**. A PASS is therefore the
*expected* result and is weak evidence about anything; it confirms the
instruction and nothing more. The informative outcomes are the other two.
"""


def main():
    with io.open(P, "r", encoding="utf-8", newline="") as fh:
        body = fh.read()
    if "\r\n" in body:
        raise SystemExit("REFUSING: CRLF already present")
    if "Addendum: `bee-1-cpl`" in body:
        raise SystemExit("REFUSING: addendum already present")
    out = body + ADD
    if not out.endswith("\n"):
        out += "\n"
    with io.open(P, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print("appended; lines %d -> %d; CRLF %s; trailing-nl %s"
          % (body.count("\n"), out.count("\n"), "\r\n" in out, out.endswith("\n")))


if __name__ == "__main__":
    main()
