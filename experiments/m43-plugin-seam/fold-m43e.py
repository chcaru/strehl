"""Fold M43 step 6 — bound the load-time calibration cost from data already in hand.

F5.3 option A asserts that measuring a plugin's noise constant at registration
costs "a few milliseconds", and F5.5 flags that as asserted rather than timed —
the cheapest open item in the plugin work. It does not need a new benchmark: the
merge's own measured pass-1 time bounds it, conservatively, without needing to
decompose that time into decode and compute.

Fact 505, from the 500-519 block.
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")

ROW = (
    505,
    "**The load-time calibration of fact 502 is bounded at ~1.7 ms per stage, from measurements "
    "already taken.** Merge pass one is **1.153 s for 22 frames** at 3516x2344 = 8.241 MP, so "
    "**52.4 ms** per full-resolution plane for decode plus gradient plus window plus regulariser "
    "plus the winner fold. A 512x512 calibration plane is **3.18%** of that area, giving "
    "**~1.67 ms** — and that figure **includes ARW decode**, which a synthetic noise plane does "
    "not pay, so the true cost is strictly lower",
    "**Settles F5.5's cheapest open item without a new benchmark, and it settles it in favour of "
    "option A.** The reason to prefer a bound derived this way over a fresh timing is that it "
    "needs no decomposition of pass one into decode and compute — the inequality holds however "
    "that split falls, so it cannot be wrong in the direction that matters. At under 2 ms per "
    "stage per configuration, host-side calibration is not a cost worth trading a correctness "
    "property for. **What this does not bound is a `WholeStack` operator or one with expensive "
    "setup**, which is the case option B still exists to serve",
    "M43 step 6 (DERIVED — arithmetic on the merge timings measured this session on 109MSDCF, "
    "22 frames: pass 1 1.153 s, pass 2 2.036 s, total 3.189 s at 262.3 MB/s over 836.4 MB) — "
    "**an upper bound, not a timing**; no calibration pass has been run",
)


def main():
    text = SRC.read_text(encoding="utf-8")
    facts = {int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", text, re.M)}
    if ROW[0] in facts:
        raise SystemExit(f"fact {ROW[0]} already present")

    row = "| {} | {} | {} | {} |".format(*ROW)
    if len(re.findall(r"(?<!\\)\|", row[1:-1])) != 3:
        raise SystemExit("unescaped pipe")

    lines = text.split("\n")
    anchor = [i for i, l in enumerate(lines) if l.startswith("| 504 |")]
    if len(anchor) != 1:
        raise SystemExit("expected exactly one fact-504 row")
    lines[anchor[0] + 1 : anchor[0] + 1] = [row]
    SRC.write_text("\n".join(lines), encoding="utf-8")
    print("inserted fact 505")


if __name__ == "__main__":
    main()
