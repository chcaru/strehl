"""Append section 13.9 -- the bee-1-cpl re-develop and the criterion that
failed as written -- to V-LINEAR-BANDS.md.  LF-safe, like add_s13.py.
"""
import io
import os

DOC = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "docs", "research", "V-LINEAR-BANDS.md"))

S = """
### 13.9 `bee-1-cpl`: a purged develop re-made, and a pre-registered criterion that was wrong

ORCH directed the pyramid lane to score the confidence-dependent exponent at
depth on `bee-1-cpl`, on the strength of its 0.30–0.40 **R=4.732 PASS**. That
instruction is only sound if the subject qualifies at the slice that lane will
use, so the subject was swept at 0.30–0.35 specifically.

**Result: R = 5.311, 95% CI [3.083, 7.638], PASS.** The instruction stands and
the pyramid lane is scoring on a qualified band. `bee-1-cpl` is the strongest
qualifier at this slice of any subject measured, and it is the only one whose
narrow value is *higher* than its wide one (+12.2%).

#### The develop had been purged, and the check on the re-develop failed as written

`bee-1-cpl`'s linear develops were deleted during the disk emergency. All 299
were re-made at the pin `740e7056` (`15EA73461905EA2D`), at stride 1 rather than
stride 4 — the committed record reads `n_real=299` with `step=4`, and 299 is
only reachable from 299 develops at `decim=1`, because a stride-4 develop yields
75×4 = 300. Stride 4 would have produced a subject one frame different from the
one every committed number describes, with nothing in the verdict to show it.

The pre-registration (`3d4e41c1`, written before the sweep landed) set this
acceptance condition:

> All 12 pre-existing bands must reproduce the committed record **exactly**. If
> any moves, the re-develop is not the subject the committed table describes.

**That condition failed. All 12 moved.** Taken literally it says the re-develop
is not the same subject and no number in this section may be quoted.

It is reported here because it was pre-registered, and it would have been easy
to quietly relax it once the answer was the convenient one.

#### What actually moved, and the control that decides it

The 12 "moves" are entirely in the **confidence intervals**. Every point
estimate is bit-identical — `max |ΔR| = 0` exactly, across all 12 bands, not
zero to a tolerance.

`bandsignal.py`'s bootstrap draws from a module-level generator seeded once per
process, so a subject swept **alone** sees a different random stream from the
same subject swept **fifth in a five-subject run**, which is how the committed
round-1 record was produced. §6.1 documents this and keeps a control for it.

That control settles this without new work, because it is a subject whose
develop was **never touched**:

| subject | develop | R differing | CI differing |
| --- | --- | ---: | ---: |
| `leaf-2-cpl` | never purged | **0 of 12** | 12 of 12 |
| `bee-1-cpl` | purged, re-made at the pin | **0 of 12** | 12 of 12 |

**Identical signature.** A subject that was never re-developed shows exactly the
same pattern, so the pattern is a property of the call order and not of the
re-develop. The re-develop reproduced the purged one in every quantity that does
not depend on the RNG stream.

#### The criterion was wrong, not the measurement

The defect is in the criterion I wrote: it said "12 bands reproduce exactly"
when what it needed to say is "12 **R** values reproduce exactly, the CIs being
call-order dependent by a mechanism this document already describes in §6.1."
I wrote a criterion that the instrument could not satisfy, against behaviour I
had already documented myself.

The distinction matters because the rescue is only legitimate if it was
available in advance. It was: §6.1 and its `leaf-2-cpl` control were committed
well before tonight, precisely to characterise this effect, and the control was
run rather than cited. Had `leaf-2-cpl` shown 0 of 12 CIs differing, there would
be no explanation available and `bee-1-cpl` would have been withdrawn.

The verifier enforces the corrected condition: `bee-1-cpl`'s 12 pre-existing
`R` values must equal the committed record exactly, and the single-subject file
is declared a control so its CIs cannot silently shadow the canonical record —
the same treatment §6.1's `leaf-2-cpl` control already gets, for the same
reason.
"""


def main():
    with io.open(DOC, "r", encoding="utf-8", newline="") as fh:
        body = fh.read()
    if "\r\n" in body:
        raise SystemExit("REFUSING: CRLF present before append")
    if "### 13.9" in body:
        raise SystemExit("REFUSING: 13.9 already present")
    out = body + S.replace("\r\n", "\n")
    if not out.endswith("\n"):
        out += "\n"
    with io.open(DOC, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print("appended 13.9; lines %d -> %d; CRLF %s"
          % (body.count("\n"), out.count("\n"), "\r\n" in out))


if __name__ == "__main__":
    main()
