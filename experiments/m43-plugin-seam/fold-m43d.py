"""Fold M43 step 5 — sharpen fact 503 before anyone writes the wrong test.

Fact 503 predicts that pre-normalising the focus response leaves the admission
set "bit-for-bit unchanged". In exact arithmetic that is provable. In f32 it is
almost certainly false, in a way that is small and estimable, and the danger is
specific: a future agent asserting byte-identity would see it fail and read
that as a refutation of the design in fact 502, which it would not be.

So this records the expected magnitude and the test shape, and marks 503.
Fact 504, from the 500-519 block.
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")

ROW = (
    504,
    "**Fact 503's bit-identity should be expected to fail, at an estimable and tiny rate — and "
    "the test must be written for that.** Pre-normalisation changes the divisor from `sigma` to "
    "`sigma * SD`, so the field is rounded differently, not merely scaled: relative error ~`2^-24` "
    "on field values of order 0.5, i.e. ~`6e-8` absolute, against a gate-1.0 tolerance of "
    "`0.0215`. That perturbation is **~3e-6 of the tolerance width**, so for a smooth "
    "distribution of `\\|Δfield\\|` near the boundary the expected flip rate is of order "
    "**1e-6 to 1e-5 of pixels — tens, not zero, out of 8.2 M**",
    "**The correct assertion is a bounded flip count, not byte-identity.** An equality test would "
    "go red, and the natural reading of a red merge test is that the transformation is unsound "
    "rather than that the test was mis-specified. **A flip rate above ~1e-4 would be the real "
    "refutation**, because that would mean the admission boundary is far denser in near-ties than "
    "smoothness predicts — which would itself be a finding about the gate worth having. Recorded "
    "before the test is written rather than after it fails, which is the only time this kind of "
    "note is worth anything",
    "M43 step 5 (DERIVED — f32 ULP arithmetic against fact 436's measured `tol = t * sqrt(2) * "
    "0.015214` and the field scale in `focus.rs`) — **the flip rate is an order-of-magnitude "
    "estimate from an assumed-smooth boundary density, and that assumption is untested**",
)

MARK = (
    " — **SHARPENED by fact 504**: bit-identity is provable in exact arithmetic but should be "
    "expected to fail in f32 at a rate of order 1e-6 to 1e-5 of pixels, so the test must assert "
    "a bounded flip count"
)


def main():
    text = SRC.read_text(encoding="utf-8")
    facts = {int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", text, re.M)}
    if ROW[0] in facts:
        raise SystemExit(f"fact {ROW[0]} already present")

    lines = text.split("\n")

    idx = [i for i, l in enumerate(lines) if l.startswith("| 503 |")]
    if len(idx) != 1:
        raise SystemExit("expected exactly one fact-503 row")
    if "SHARPENED by fact 504" in lines[idx[0]]:
        raise SystemExit("fact 503 already marked")
    if not lines[idx[0]].endswith(" |"):
        raise SystemExit("fact-503 row does not end in a cell delimiter")
    lines[idx[0]] = lines[idx[0]][:-2] + MARK + " |"

    row = "| {} | {} | {} | {} |".format(*ROW)
    for candidate in (lines[idx[0]], row):
        if len(re.findall(r"(?<!\\)\|", candidate[1:-1])) != 3:
            raise SystemExit("unescaped pipe")

    lines[idx[0] + 1 : idx[0] + 1] = [row]
    SRC.write_text("\n".join(lines), encoding="utf-8")
    print("inserted fact 504, marked fact 503")


if __name__ == "__main__":
    main()
