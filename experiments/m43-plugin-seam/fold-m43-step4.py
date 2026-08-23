"""Fold M43 step 4 - the M17+M42 edit is a triple, and the number that proves it.

Facts 509-511, discipline 262. 506-508 went to M16; 512-519 stay free.

One honesty note is built into fact 510 rather than left to a reader: the
separability residual (+0.47%) is EXACTLY the size of the instrument's own
calibration deviation on the shipped arm (k reads 1.005, not 1.000). So
pre-registered prediction 3 is recorded as NOT DECIDED, not as "held", even
though the script printed HELD -- the script scored the sign, and the sign is
not resolvable at this precision. Reporting it as a win would be exactly the
defect discipline 257 was written to catch.
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")
DOC = "M43-plugin-calibration-seam.md"
SCRIPT = "`experiments/m43-plugin-seam/04-shipped-config-recalibration.py`"

FACTS = [
    (
        509,
        "**The pending M17+M42 edit silently re-scales the merge gate by 1.53x.** `FOCUS_NOISE_SD = 0.015214` was measured for `\\|grad\\|` at w13. For the proposed `tenengrad-sq` at w11 under the same r8 regulariser the SD is **0.023249** (+/- 0.000056 sem, 8 seeds x 2048^2), so **k = 1.528**: shipping the edit without re-measuring the constant turns `--gate 1.0` into an effective gate of **0.654**, and moves every gate the owner has ever measured by the same factor.",
        "**The edit is a TRIPLE, not the pair M42 proposed** — operator, radius, *and* the noise constant, in one commit. By fact 438 the log, the exit code and the calibration block are all unchanged, so nothing in the shipped binary can reveal it. This is M43's hole becoming load-bearing on a real pending commit rather than on a hypothetical third-party plugin.",
        SCRIPT,
    ),
    (
        510,
        "Attribution of that 1.53x, measured arm by arm under an identical regulariser: **radius alone (w13->w11) gives k = 1.125**, **operator alone (`\\|grad\\|`->`\\|grad\\|^2` at w13) gives k = 1.364**, and the two together give **1.528**. The product of the single factors is 1.535, overstating the joint by **+0.47%** — but the instrument's own calibration deviation on the shipped arm is **+0.47%** (k reads 1.005 where it must read 1.000), so **the pre-registered non-separability prediction is NOT DECIDED**; the residual sits exactly at the noise floor.",
        "Both halves of the edit push the same way and **neither is negligible**: even the radius change alone, which M42 correctly prices as free on quality, noise and runtime, is a **12.5% gate shift**. Anyone re-radiusing a focus operator in this project must re-measure, not reason. The near-separability is a convenience, not a finding, and must not be quoted as one.",
        SCRIPT,
    ),
    (
        511,
        "`crates/strehl-core/src/focus.rs` at `HEAD` still reads `WINDOW_RADIUS = 13` and `(gx*gx + gy*gy).sqrt()` — **the magnitude operator. `tenengrad-sq` was never landed**, though `OWNER-QUESTIONS.md` Q1 recorded \"What I did: landed it\". The only commits ever to touch `focus.rs` are M2, M9, M14 and M18. M42 caught the same discrepancy independently from its own reading of the file.",
        "A decision recorded as done, that was not done. The corrected entry is left visible in `OWNER-QUESTIONS.md` rather than edited away. **The upside is that the defect in fact 509 has not shipped** — the triple can still land as one commit, which is the only way it should land.",
        "`git log -- crates/strehl-core/src/focus.rs`; `git show HEAD:crates/strehl-core/src/focus.rs`; M42 report §13",
    ),
]

DISCIPLINES = [
    (
        262,
        "**A measured constant is a member of the tuned set, so changing the configuration is a RE-MEASUREMENT, not a re-tune.** M42's discipline 259 says an operator/window pair must be re-validated when either half changes. That is right and it is one member short: any calibration constant derived from the pair belongs to the set too. In `strehl` the merge gate is denominated in `FOCUS_NOISE_SD`, which is a function of the operator, the window *and* the regulariser — so the innocuous-looking pair edit is a triple, and the missing third piece moves the shipped gate by **1.53x** with nothing observable to show for it. Before landing any change to a tuned component, list every constant that was measured *under* the old configuration and re-derive each one in the same commit.",
    ),
]


def build_row(n, claim, consequence, source):
    prov = f"Orchestrator (MEASURED — {source}, direction pre-registered in the docstring; see [`{DOC}`]({DOC})) — **NOT INDEPENDENTLY VERIFIED**"
    row = f"| {n} | {claim} | {consequence} | {prov} |"
    if len(re.findall(r"(?<!\\)\|", row[1:-1])) != 3:
        raise SystemExit(f"row {n}: unescaped pipe")
    return row


def main():
    text = SRC.read_text(encoding="utf-8")

    present = {int(m) for m in re.findall(r"^\| (\d+) \|", text, re.M)}
    if present & {n for n, *_ in FACTS}:
        raise SystemExit(f"fact collision: {sorted(present & {n for n, *_ in FACTS})}")

    dsec = re.search(r"^## 5\.", text, re.M)
    dend = re.search(r"^## ", text[dsec.end():], re.M)
    lo, hi = dsec.start(), dsec.end() + dend.start()
    dpresent = {int(x) for x in re.findall(r"^(\d+)\. \*\*", text[lo:hi], re.M)}
    if dpresent & {n for n, _ in DISCIPLINES}:
        raise SystemExit("discipline collision")

    lines = text.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith("| 508 |")]
    if len(idx) != 1:
        raise SystemExit(f"expected one anchor row 508, got {len(idx)}")
    lines[idx[0] + 1 : idx[0] + 1] = [build_row(*f) for f in FACTS]
    text = "\n".join(lines)

    dsec = re.search(r"^## 5\.", text, re.M)
    dend = re.search(r"^## ", text[dsec.end():], re.M)
    lo, hi = dsec.start(), dsec.end() + dend.start()
    seg = text[lo:hi]
    m = re.search(r"^261\. \*\*", seg, re.M)
    if not m:
        raise SystemExit("discipline 261 not found (fold M42 first)")
    nxt = re.search(r"^\d+\. \*\*", seg[m.end():], re.M)
    ins = lo + (m.end() + nxt.start() if nxt else len(seg.rstrip("\n")) + 1)
    text = text[:ins] + "".join(f"{n}. {d}\n\n" for n, d in DISCIPLINES) + text[ins:]

    SRC.write_text(text, encoding="utf-8")
    print(f"facts {[n for n, *_ in FACTS]}, disciplines {[n for n, _ in DISCIPLINES]}")


if __name__ == "__main__":
    main()
