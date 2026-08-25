"""M116-promotion -- verify the section 5e ladder table against the raw data.

Every number in the report's ladder table is re-read from
`scores-ladder.json` and from the tool's own per-arm logs. A transcription slip
anywhere in the table fails this check.

The table is the canonical site for these numbers. Prose elsewhere in section 5e
quotes them, which is why negctl_ladder.py plants its defects in the TABLE and
requires this verifier to go RED: a presence-based check would be satisfied by
the duplicate in the prose.

Exit 0 = GREEN, exit 1 = RED.

Run: python verify_ladder.py
"""

import json
import os
import re
import sys
from pathlib import Path

REPORT = Path(os.environ.get(
    "M116_REPORT",
    r"C:\dev\blog\death-of-software\projects\strehl\docs\research"
    r"\M116-promotion.md"))
HALO = Path(r"C:\dev\strehl-out\M116\halo")

# The table writes 'fern' for the long subject name.
ALIAS = {"bee-3-cpl": "bee-3-cpl",
         "fern": "flower-bud-with-background-fern-cpl"}

ROW = re.compile(
    r"^\|\s*(bee-3-cpl|fern)\s*\|\s*(L\d+|H\d)\s*\|\s*(\d+)\s*\|\s*"
    r"`([+-][\d.]+)`\s*\|\s*`([+-][\d.]+)`\s*\|\s*`([+-][\d.]+)`\s*\|\s*"
    r"(\d+)\s*\|\s*$")


def reelected(subj: str) -> dict:
    """(arm tag -> re-elected count) straight out of the tool's own logs."""
    out = {}
    for log in (HALO / "logs").glob(f"{subj}__*.log"):
        txt = log.read_text(encoding="utf-8", errors="replace")
        if "--gate 4" not in txt or "--srgb" in txt:
            continue
        m = re.search(r"([0-9]+) of ([0-9]+) treated pixels re-elected", txt)
        if not m:
            continue
        tag = log.stem.split("__", 1)[1].split("-")[0]
        out[tag] = int(m.group(1))
    return out


def main() -> int:
    d = json.loads((HALO / "scores-ladder.json").read_text(encoding="utf-8"))
    text = REPORT.read_text(encoding="utf-8")

    rows = []
    for line in text.splitlines():
        m = ROW.match(line)
        if m:
            rows.append(m.groups())

    if not rows:
        print("RED - no ladder table rows matched; the table moved or its "
              "shape changed, and this verifier is now blind.")
        return 1

    re_cache = {}
    bad = []
    # COMPLETENESS. Iterating only over the rows that matched would let a
    # DELETED row pass silently -- the verifier would simply check one fewer
    # number and still print PASS. Every rung in the data must appear.
    seen = {(s, r) for s, r, *_ in rows}
    for subj, rec in d["subjects"].items():
        lbl = next(k for k, v in ALIAS.items() if v == subj)
        for rung in rec["rungs"]:
            if (lbl, rung) not in seen:
                bad.append(f"{lbl}/{rung}: measured but MISSING from the "
                           "report table")

    for subj_lbl, rung, delta, dhalo, dd, dor, reel in rows:
        subj = ALIAS[subj_lbl]
        rec = d["subjects"].get(subj)
        if rec is None or rung not in rec["rungs"]:
            bad.append(f"{subj_lbl}/{rung}: not present in scores-ladder.json")
            continue
        r = rec["rungs"][rung]

        if int(delta) != r["delta"]:
            bad.append(f"{subj_lbl}/{rung} delta: report {delta} "
                       f"vs data {r['delta']}")
        for label, shown, actual, places in (
                ("dHALO%", dhalo, r["dHALO_pct"], 2),
                ("D", dd, r["D"], 5),
                ("D_or", dor, r["D_or"], 5)):
            want = f"{actual:+.{places}f}"
            # -0.00 and +0.00 are the same number; compare the rendered string
            # both ways round so a signed zero is not a false failure.
            if shown != want and shown.lstrip("+-") != want.lstrip("+-"):
                bad.append(f"{subj_lbl}/{rung} {label}: report {shown} "
                           f"vs data {want}")

        if subj not in re_cache:
            re_cache[subj] = reelected(subj)
        got = re_cache[subj].get(rung)
        if got is None:
            bad.append(f"{subj_lbl}/{rung} re-elected: no log found")
        elif int(reel) != got:
            bad.append(f"{subj_lbl}/{rung} re-elected: report {reel} "
                       f"vs tool log {got}")

    n = len(rows)
    vals = n * 4
    if bad:
        print(f"RED - {len(bad)} mismatch(es) over {n} rows / {vals} values:")
        for b in bad:
            print(f"  {b}")
        return 1
    print(f"checked {n} ladder rows, {vals} values "
          "(delta, dHALO%, D, D_or, re-elected)")
    print("PASS - every ladder number matches scores-ladder.json and the "
          "tool's own logs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
