"""Fold M45 (the plugin crate) into SYNTHESIS.md.

P1..P10 -> facts 520..529. Disciplines -> 284..286. Questions -> 123..125.
Also annotates facts 504 and 505, both of which M45 measured against.

Rule 28: the caller has already checked by CONTENT that M45 is not folded.
Rule 25: three namespaces. Every edit here is scoped to its own section.
"""

import pathlib
import re
import sys

SYN = pathlib.Path("docs/research/SYNTHESIS.md")
REP = pathlib.Path("docs/research/M45-plugin-crate-implemented.md")

t = SYN.read_text(encoding="utf-8")
rep = REP.read_text(encoding="utf-8")


def section(doc, num):
    """Byte range of '## <num>.' up to the next '## ' (or EOF for the last)."""
    m = re.search(rf"^## {num}\.", doc, re.M)
    if not m:
        sys.exit(f"ABORT: no section {num}")
    nxt = re.search(r"^## ", doc[m.end():], re.M)
    return m.start(), (m.end() + nxt.start()) if nxt else len(doc)


# ------------------------------------------------------------------ the facts
block = rep.split("## Proposed SYNTHESIS entries")[1]
rows = [r for r in block.splitlines() if re.match(r"^\| P\d+ \|", r.strip())]
if len(rows) != 10:
    sys.exit(f"ABORT: expected 10 proposed rows, parsed {len(rows)}")

SOURCE = {
    1: "M45 (MEASURED, `calibrate::tests::the_calibrator_reproduces_both_in_crate_constants`)",
    2: "M45 (MEASURED, `examples/calibration-survey.rs -- reference`) — **independently confirms fact 439** in a second language and implementation",
    3: "M45 (DERIVED from the shipped type signatures) — closes §F4.6 fault 5 **by construction**",
    4: "M45 (MEASURED, `examples/f5-design-probes.rs` probe 2) — **REFUTES §F5.3's sketch**",
    5: "M45 (MEASURED, `examples/f5-design-probes.rs` probe 1) — **REFUTES §F5.3's margin**",
    6: "M45 (MEASURED, `examples/f5-design-probes.rs` probe 3) — **CORRECTS fact 505's number, not its conclusion**",
    7: "M45 (MEASURED, `pre_normalising_the_field_changes_a_bounded_and_tiny_fraction_of_admissions`) — **refines fact 504**",
    8: "M45 (MEASURED, its own first run, recorded verbatim) — **a control that failed rule 20 and was caught by it**",
    9: "M45 (MEASURED, `dropping_the_regulariser_fails_the_coarse_target_and_not_the_fine_one`) — **confirms fact 500**",
    10: "M45 (MEASURED, `the_constants_survive_re_choosing_the_generator_the_transform_and_the_plane`) — **rule 24 satisfied by re-choice**",
}

new_rows = []
for row in rows:
    cells = row.strip()[1:-1].split("|")
    if len(cells) != 4:
        sys.exit(f"ABORT: expected 4 cells, got {len(cells)}:\n{row[:120]}")
    p = int(re.match(r"\s*P(\d+)\s*$", cells[0]).group(1))
    out = f"| {519 + p} | {cells[1].strip()} | {cells[2].strip()} | {SOURCE[p]} |"
    if len(re.findall(r"(?<!\\)\|", out[1:-1])) != 3:
        sys.exit(f"ABORT: pipe count wrong in fact {519 + p}:\n{out}")
    new_rows.append(out)

f_lo, f_hi = section(t, 4)
facts = t[f_lo:f_hi]
last = None
for m in re.finditer(r"^\| \d+ \|.*$", facts, re.M):
    last = m
if last is None:
    sys.exit("ABORT: no fact rows found in section 4")
facts = facts[: last.end()] + "\n" + "\n".join(new_rows) + facts[last.end():]


def annotate(sec, num, add):
    m = re.search(rf"^\| {num} \| .*$", sec, re.M)
    if not m:
        sys.exit(f"ABORT: fact {num} not found")
    row = m.group(0)
    if add[:40] in row:
        sys.exit(f"ABORT: fact {num} already annotated")
    return sec[: m.start()] + row.rstrip()[:-1].rstrip() + " " + add + " |" + sec[m.end():]


facts = annotate(
    facts,
    504,
    "— **MEASURED by M45 (fact 526): confirmed in direction, refined 1.4-7x LOWER** at 1.4e-7 to 7.2e-7 over 6 948 992 real decisions. Its warning was load-bearing: §F5.5's proposed byte-identical test **would have gone red**",
)
facts = annotate(
    facts,
    505,
    "— **NUMBER REFUTED by M45 (fact 525), conclusion intact.** Measured 5.02 ms per plane and 60.3 ms per registration: **2.95x and 35x** this bound. The cost is still negligible, so the verdict stands and the figure must not be quoted",
)

t = t[:f_lo] + facts + t[f_hi:]

# ----------------------------------------------------------- the disciplines
DISC = [
    "**A load-time measurement must be seeded and replicated, or it is a confluence violation dressed as a calibration.** A single unseeded probe makes registration non-deterministic; the gate it computes differed by **5.56%** across planes when M45 measured it. State the seed list and the minimum replicate count in the contract, and refuse a plan that cannot produce a standard error.",
    "**A positive control must break a *different* symmetry from the treatment.** M45's first flip-rate control divided both the field **and** the tolerance by the same wrong constant — algebraically the identical comparison. It measured **0 flips in both arms**, so a test asserting only `rate < 1e-4` would have passed green with **zero power**. Before trusting a bound, check that the control arm actually exceeds it.",
    "**When a design's cost is bounded by derivation rather than measurement, quote the bound with its derivation attached, or not at all.** Fact 505's 1.7 ms is a correct *conclusion* resting on a number **3x low per plane and 35x low per registration**. The conclusion survived; had the margin been thinner it would not have.",
]
d_lo, d_hi = section(t, 5)
disc = t[d_lo:d_hi]
lastd = None
for m in re.finditer(r"^\d+\. \*\*", disc, re.M):
    lastd = m
if lastd is None:
    sys.exit("ABORT: no disciplines found")
n = int(re.match(r"^(\d+)\.", disc[lastd.start():]).group(1))
if n != 283:
    sys.exit(f"ABORT: expected last discipline 283, found {n}")
disc = disc.rstrip() + "\n\n" + "\n\n".join(
    f"{284 + i}. {d}" for i, d in enumerate(DISC)
) + "\n\n"
t = t[:d_lo] + disc + t[d_hi:]

# ------------------------------------------------------------- the questions
QS = [
    "**Should the merge adopt the pre-normalised field or the measured-constant field?** Pre-normalising makes `--gate` dimensionless and therefore portable across operators — §F5.3's point 3 argues it is the only version in which a shared preset means anything — at the cost of changing ~7e-7 of admission decisions. The measured-constant form keeps the arithmetic shape byte-for-byte and changes no decision, but leaves `--gate` operator-dependent, so a preset tuned on tenengrad is silently 6.6x off on SML. **Both are implemented in `strehl-plugin`.** This is a product decision about what a gate number *means* to a user, not a technical one.",
    "**Should the pending `tenengrad-sq` + r11 change re-derive `FOCUS_NOISE_SD` through the calibrator instead of hard-coding a new literal?** Facts 509-511 price that change at `k` = 1.528. Routing it through `strehl-plugin` would be the calibrator's first real use and would **retire the compiled-in constant permanently**, which is the whole point of fault 5. The alternative is a third hand-measured literal in a file that has now had two of them go wrong.",
    "**Is a runtime panic acceptable at plugin registration?** `Window::Custom` and `Normalisation::Custom` can only be enforced by panic, because Rust cannot require that a *provided* trait method be overridden when an associated value takes a particular variant. The alternative is splitting the trait so that a custom-window operator is a different type and the invalid state does not exist. The panic fires at registration, not mid-merge, which is the least-bad time for it.",
]
q_lo, q_hi = section(t, 10)
q = t[q_lo:q_hi]
lastq = None
for m in re.finditer(r"^\d+\. \*\*", q, re.M):
    lastq = m
if lastq is None:
    sys.exit("ABORT: no questions found")
n = int(re.match(r"^(\d+)\.", q[lastq.start():]).group(1))
if n != 122:
    sys.exit(f"ABORT: expected last question 122, found {n}")
q = q.rstrip() + "\n\n" + "\n\n".join(f"{123 + i}. {s}" for i, s in enumerate(QS)) + "\n"
t = t[:q_lo] + q + t[q_hi:]

SYN.write_text(t, encoding="utf-8")
print("folded facts 520-529, disciplines 284-286, questions 123-125")
print("annotated facts 504, 505")
