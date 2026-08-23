"""Fold M43 — the plugin seam's calibration hole.

Facts 436-438 are the tail of the 432-439 block claimed earlier tonight, so no
new fact claim is needed; the script re-checks for collisions anyway (rule 25).
Discipline 256. One new question, numbered from the observed maximum in section
10 rather than assumed, because sections 5 and 10 have collided twice.

The finding: the gate's tolerance is `t * sqrt(2) * FOCUS_NOISE_SD`, and
FOCUS_NOISE_SD is a property of the OPERATOR. The plugin design has no slot for
it, so a contributed focus measure inherits the host's constant and silently
rescales the gate. Measured: 87.76% of pixels revert to selection.
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")
DOC = "M43-plugin-calibration-seam.md"

ROWS = [
    (
        436,
        "**The merge gate's tolerance is exactly linear in a constant that belongs to the "
        "operator, not to the host.** `tol = t * sqrt(2) * FOCUS_NOISE_SD`, verified against the "
        "shipped binary at five gates spanning **35x**: `tol/t` is constant to **2.0e-6** and "
        "equals `sqrt(2) * 0.015214 = 0.021516`. Therefore **an operator whose true noise SD is "
        "`k` times the declared constant behaves exactly like the declared gate divided by `k`**",
        "**This is the substitution that makes the plugin seam's calibration hole measurable "
        "without building a plugin system first.** It also means the gate has no units of its "
        "own: `--gate 1.0` is a statement about a specific operator at a specific window, and it "
        "silently means something else for any other. Linearity is the check with power to fail "
        "here, and it did not fail",
        f"M43 (MEASURED — `strehl merge` on 109MSDCF, 22 frames; see [`{DOC}`]({DOC}) section 1) "
        "— **NOT INDEPENDENTLY VERIFIED**",
    ),
    (
        437,
        "**A wrong operator constant silently degrades the estimator into the selector.** "
        "`FINE_FOCUS_NOISE_SD / FOCUS_NOISE_SD = 0.090400 / 0.015214 = 5.94x` — two real "
        "operators already in this codebase, differing only in window radius. At the intended "
        "`--gate 1.0`: correct constant gives mean `n_eff` **1.884** with **41.66%** of pixels at "
        "`n_eff` = 1; an operator 5.94x noisier than declared gives **1.131** and **87.76%**; "
        "5.94x quieter gives **7.267** and **2.40%**",
        "**The same declared gate produces anything from 87.76%-selection to a 7.3-frame average, "
        "and the three runs are indistinguishable from the log, the exit code and the CLI's own "
        "calibration block.** In the noisy direction the tool becomes the defect it exists to "
        "remove; in the quiet direction it averages frames the noise model can tell apart, which "
        "is blur. **`--gate` is therefore not a portable number and must never appear in a "
        "contributed profile** — a second, independent argument for fact 324's `--target-n-eff`, "
        "this time from portability rather than from calibration",
        f"M43 (MEASURED — same run; see [`{DOC}`]({DOC}) section 2) — **NOT INDEPENDENTLY "
        "VERIFIED**; one stack, and `k` = 5.94 is illustrative rather than a surveyed "
        "distribution",
    ),
    (
        438,
        "**Neither capability negotiation nor the confluence property test can catch it.** A "
        "focus-measure plugin with a wrong noise constant is capability-compatible (same domain, "
        "tiling and layout), **confluent** (the constant is not an ordering property, so it "
        "commutes exactly as well as the correct one does), and **sensitive** in the sense "
        "workstream E section F4.3 requires (its output does change when the input changes). It "
        "passes every gate the plugin design has and produces a quietly worse image",
        "**A missing contract, not a missing test** — and the correction is cheap, because the "
        "measurement already exists twice in-crate "
        "(`the_focus_noise_constant_is_the_measured_one`, "
        "`the_fine_focus_noise_constant_is_the_measured_one`). **The plugin boundary must make "
        "that test mandatory rather than customary, must refuse to load a plugin that omits the "
        "constant rather than defaulting it, and must require the operator and its window to be "
        "declared as a pair.** The third follows independently from M42's quality-side question "
        "and from fact 152's scale finding. Amends workstream E sections F3.3/F4, which predate "
        "the constant's measurement",
        f"M43 (DERIVED from facts 436-437 and a reading of `E-plugin-architecture.md` sections "
        f"F3.3/F4; see [`{DOC}`]({DOC}) sections 3-4) — **NOT INDEPENDENTLY VERIFIED**",
    ),
]

DISCIPLINE = """256. **A tunable is only portable if its units are.** `--gate` reads as a
     dimensionless number and is not one: it is scaled by a constant belonging
     to the focus operator, so the same value means different things for
     different operators - measured span at one declared gate is `n_eff` 1.131
     to 7.267 (fact 437). Before exposing a parameter in a profile, a preset, a
     plugin manifest or a README, **name the quantity it is measured in and say
     who owns that quantity**. If the owner is a component the user can replace,
     the parameter is not portable, and the portable form is the achieved
     outcome instead - here `--target-n-eff`, per fact 324.
"""

QUESTION_BODY = """**What is the realistic spread of `k` across focus measures anyone would
    actually contribute?** Fact 437 prices the damage using `k` = 5.94, taken
    from two operators already in this repository, but that is an illustration
    and not a distribution. If plausible contributed operators cluster near
    `k` = 1, the seam is a documentation problem; if they spread as widely as
    the two built-ins do, the load-time refusal in fact 438 is mandatory. Cheap
    to answer: measure the noise SD of the M11/M14/M17 bake-off arms, which are
    already implemented, and read the spread directly.
"""


def build_row(n, claim, consequence, provenance):
    row = f"| {n} | {claim} | {consequence} | {provenance} |"
    if row[1:-1].count("|") != 3:
        raise SystemExit(f"row {n}: unescaped pipe in text")
    return row


def section_bounds(text, num):
    """Return (start, end) character offsets of `## <num>.` up to the next `## `."""
    m = re.search(rf"^## {num}\.", text, re.M)
    if not m:
        raise SystemExit(f"section {num} not found")
    nxt = re.search(r"^## ", text[m.end():], re.M)
    return m.start(), (m.end() + nxt.start() if nxt else len(text))


def append_list_item(text, section, item_text, expect_last):
    """Insert `item_text` immediately after the last `N. **` item of a section."""
    lo, hi = section_bounds(text, section)
    seg = text[lo:hi]
    items = list(re.finditer(r"^(\d+)\. \*\*", seg, re.M))
    if not items:
        raise SystemExit(f"no list items in section {section}")
    last_num = int(items[-1].group(1))
    if last_num != expect_last:
        raise SystemExit(
            f"section {section}: expected last item {expect_last}, found {last_num}"
        )
    # the last item's block runs to the end of the section's trailing blank lines
    end_of_item = len(seg.rstrip("\n"))
    ins = lo + end_of_item
    return text[:ins] + "\n" + item_text.rstrip("\n") + "\n" + text[ins:], last_num


def main():
    text = SRC.read_text(encoding="utf-8")

    facts = {int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", text, re.M)}
    want = {r[0] for r in ROWS}
    if facts & want:
        raise SystemExit(f"fact collision: {sorted(facts & want)}")

    lines = text.split("\n")
    anchor = [i for i, l in enumerate(lines) if re.match(r"^\| 435 \|", l)]
    if len(anchor) != 1:
        raise SystemExit("expected exactly one fact-435 row")
    lines[anchor[0] + 1 : anchor[0] + 1] = [build_row(*r) for r in ROWS]
    text = "\n".join(lines)

    text, _ = append_list_item(text, 5, DISCIPLINE, expect_last=255)

    lo, hi = section_bounds(text, 10)
    q_nums = [int(m.group(1)) for m in re.finditer(r"^(\d+)\. \*\*", text[lo:hi], re.M)]
    q_next = max(q_nums) + 1
    text, _ = append_list_item(
        text, 10, f"{q_next}. {QUESTION_BODY}", expect_last=max(q_nums)
    )

    SRC.write_text(text, encoding="utf-8")
    print(f"inserted facts {sorted(want)}, discipline 256, question {q_next}")


if __name__ == "__main__":
    main()
