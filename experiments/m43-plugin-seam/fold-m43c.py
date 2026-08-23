"""Fold M43 step 4 — the plugin-API amendment, and a better design than the one
the amendment started with.

Facts 502-503, from the 500-519 block claimed earlier. Both DERIVED, and both
are labelled as such: this is a design argument, not a measurement, and the one
measurable claim inside it (behaviour preservation under pre-normalisation) is
recorded specifically so it can be checked against the binary rather than
assumed.
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")
DOC = "E-plugin-architecture.md"

ROWS = [
    (
        502,
        "**The host should measure the plugin's noise constant, not ask it for one.** Fact 438 "
        "called for a mandatory declaration in `Caps`. That is the weaker design. The host "
        "already owns a noise plane, the window, the regulariser and the sigma normalisation, so "
        "it can run any candidate operator through its own configuration at registration and read "
        "the SD off directly — **a few milliseconds, once per stage**",
        "**Better on four counts, and the fourth is structural.** (1) No trust: a declaration can "
        "be wrong, a measurement cannot be wrong the same way, so fault 5 becomes "
        "*unrepresentable* rather than merely detectable. (2) **A plugin-declared constant is "
        "under-determined in principle** — fact 500 showed the constant depends on the host's "
        "regulariser, which the plugin cannot know. (3) Changing `REGULARISER_RADIUS` silently "
        "staleness every declared constant in the ecosystem; a measured one re-derives. (4) It "
        "removes the parameter from the contract entirely, which is the Cordis-shaped answer — "
        "the host stops requesting a coeffect the plugin cannot reliably supply and computes one "
        "it already has the means to. **Under this design `--gate` becomes genuinely "
        "dimensionless**, which is the only version in which a number in a shared preset means "
        "the same thing on two operators",
        f"M43 step 4 (DERIVED — reasoning from facts 436, 438, 500-501 and `focus.rs`'s "
        f"documented scale invariance; see [`{DOC}`]({DOC}) section F5.3) — **the load-time cost "
        "is asserted, not timed**, and that is the cheapest open item in the section",
    ),
    (
        503,
        "**Pre-normalising the focus response is behaviour-preserving, by derivation and not yet "
        "by test.** If the field is divided by its own noise SD and the tolerance multiplied by "
        "the same factor, the admission set should be **bit-for-bit unchanged**: `focus.rs` "
        "states that both the argmax and any positive-scaled regulariser are invariant to a "
        "constant rescale, and fact 436 established that `tol` is exactly linear in the constant",
        "**This is the load-bearing step of fact 502 and it is the one that is not measured.** If "
        "it holds, the whole calibration seam closes with a one-line change and the gate becomes "
        "unitless. If it fails — most plausibly through f32 rounding, since normalising scales "
        "the field by about **65.7x** — then the host-measures-it design still works but is no "
        "longer free. **Check it with a byte-identical-output test against the shipped binary "
        "before relying on it**; the merge is the wrong place to be confidently wrong, and fact "
        "341 is the standing reminder of what a structural argument about the merge is worth",
        f"M43 step 4 (DERIVED — from `crates/strehl-core/src/focus.rs`'s `gradient_magnitude` doc "
        f"comment and fact 436; see [`{DOC}`]({DOC}) section F5.5) — **NOT MEASURED, and "
        "deliberately recorded as a falsifiable prediction rather than folded into fact 502**",
    ),
]


def build_row(n, claim, consequence, provenance):
    row = f"| {n} | {claim} | {consequence} | {provenance} |"
    if len(re.findall(r"(?<!\\)\|", row[1:-1])) != 3:
        raise SystemExit(f"row {n}: unescaped pipe in text")
    return row


def main():
    text = SRC.read_text(encoding="utf-8")
    facts = {int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", text, re.M)}
    want = {r[0] for r in ROWS}
    if facts & want:
        raise SystemExit(f"fact collision: {sorted(facts & want)}")

    lines = text.split("\n")
    anchor = [i for i, l in enumerate(lines) if l.startswith("| 501 |")]
    if len(anchor) != 1:
        raise SystemExit("expected exactly one fact-501 row")
    lines[anchor[0] + 1 : anchor[0] + 1] = [build_row(*r) for r in ROWS]
    SRC.write_text("\n".join(lines), encoding="utf-8")
    print(f"inserted facts {sorted(want)}")


if __name__ == "__main__":
    main()
