"""Re-derive every headline row of docs/research/V-SPEED.md from the raw JSONL
and require the document to contain that row verbatim.

House rule: a number in a report is a claim, and a claim needs a command that
was run. This recomputes the statistics from `timings-*.jsonl` -- it does not
read them back out of `report.py`'s console log -- and then requires each
*whole table row* to appear in the document exactly once.

Whole-row matching rather than per-number presence is deliberate. A presence
test for a short token like "22" or "4.21" is satisfied by any duplicate of
that value anywhere in the document, so it can pass on a decoy while the
canonical site is wrong. A full row is unique, gives every number one canonical
site, and fails if any single cell drifts.

Self-commissioning: `--commission` plants a known defect anchored on a unique
full-line string and requires the checker to go RED. If the mutation does not
land it hard-errors instead of reporting a pass -- a plant that never armed and
a defect that was caught otherwise print the same green line.
"""

import json
import os
import re
import statistics
import sys
import tempfile

ROOT = r"C:\dev\strehl-out\V-SPEED"
DOC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "docs", "research", "V-SPEED.md",
)

PIPE = {
    "strehl": ["strehl"],
    "enfuse": ["develop", "align", "enfuse"],
    "focus-stack": ["develop", "focus-stack"],
}
LABEL = {
    "strehl": "**strehl**",
    "enfuse": "develop + align + enfuse",
    "focus-stack": "develop + focus-stack",
}
RATIO_LABEL = {"enfuse": "align+enfuse", "focus-stack": "focus-stack"}
STAGE_LABEL = {
    "develop": "develop (RAW\u2192TIFF)",
    "strehl": "**strehl** (whole pipeline)",
    "align": "align_image_stack",
    "enfuse": "enfuse (merge only)",
    "focus-stack": "focus-stack (merge+align)",
}
SUBJECTS = [("deep", "coffee-bean", 105), ("shallow", "109MSDCF", 22)]


def load(tag):
    rounds = {}
    for line in open(os.path.join(ROOT, f"timings-{tag}.jsonl")):
        d = json.loads(line)
        if d.get("wall_s") is None:
            continue
        rounds.setdefault(d["round"], {})[d["stage"]] = d["wall_s"]
    return rounds


def totals(rounds, arm):
    out = {}
    for r, stages in rounds.items():
        if all(s in stages for s in PIPE[arm]):
            out[r] = sum(stages[s] for s in PIPE[arm])
    return out


def expected_rows():
    """Every row this document must contain, re-derived from the JSONL."""
    rows = []
    for tag, subject, frames in SUBJECTS:
        rounds = load(tag)
        warm = sorted(r for r in rounds if r != 0)
        st = totals(rounds, "strehl")

        for stage in ("develop", "strehl", "align", "enfuse", "focus-stack"):
            w = [rounds[r][stage] for r in warm if stage in rounds[r]]
            med, lo, hi = statistics.median(w), min(w), max(w)
            rows.append((
                f"{subject}/{stage} stage row",
                f"| {STAGE_LABEL[stage]} | {rounds[0][stage]:.2f} | {lo:.2f} | {med:.2f} | "
                f"{hi:.2f} | {100 * (hi - lo) / med:.1f}% | {med / frames:.3f} |",
            ))

        for arm in ("strehl", "enfuse", "focus-stack"):
            t = totals(rounds, arm)
            w = [t[r] for r in warm if r in t]
            med, lo, hi = statistics.median(w), min(w), max(w)
            rows.append((
                f"{subject}/{arm} pipeline totals",
                f"| {LABEL[arm]} | {t[0]:.2f} | {lo:.2f} | {med:.2f} | {hi:.2f} | "
                f"{100 * (hi - lo) / med:.1f}% | **{med / frames:.3f}** |",
            ))

        for arm in ("enfuse", "focus-stack"):
            t = totals(rounds, arm)
            pr = [t[r] / st[r] for r in warm if r in t and r in st]
            series = ", ".join(f"{x:.2f}\u00d7" for x in pr)
            rows.append((
                f"{subject}/{arm} paired ratios",
                f"| {subject} | {frames} | {RATIO_LABEL[arm]} | {series} | "
                f"**{statistics.median(pr):.2f}\u00d7** | {min(pr):.2f}\u00d7 | {max(pr):.2f}\u00d7 |",
            ))
    return rows


def run(docpath, quiet=False):
    doc = open(docpath, encoding="utf-8").read()
    doc_n = re.sub(r"[ \t]+", " ", doc)
    ok, bad = 0, []
    for label, row in expected_rows():
        n = doc_n.count(re.sub(r"[ \t]+", " ", row))
        if n == 1:
            ok += 1
        else:
            bad.append(f"{label}: found {n} times, expected exactly 1\n      want: {row}")
    if not quiet:
        for b in bad:
            print(f"  MISMATCH  {b}")
    total = ok + len(bad)
    print(f"{ok}/{total} re-derived rows matched  {'GREEN' if not bad else 'RED'}")
    return 0 if not bad else 1


PLANT_FROM = ("| coffee-bean | 105 | align+enfuse | 28.80\u00d7, 22.58\u00d7, 19.56\u00d7 | "
              "**22.58\u00d7** | 19.56\u00d7 | 28.80\u00d7 |")
PLANT_TO = ("| coffee-bean | 105 | align+enfuse | 28.80\u00d7, 22.58\u00d7, 19.56\u00d7 | "
            "**31.41\u00d7** | 19.56\u00d7 | 28.80\u00d7 |")


def commission():
    src = open(DOC, encoding="utf-8").read()
    if src.count(PLANT_FROM) != 1:
        raise SystemExit(
            f"MUTATION TARGET NOT FOUND: anchor occurs {src.count(PLANT_FROM)} times, "
            "expected exactly 1. Refusing to report a commissioning result."
        )
    print("=== clean document must be GREEN ===")
    clean = run(DOC)
    tmp = os.path.join(tempfile.gettempdir(), "V-SPEED-mutated.md")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(src.replace(PLANT_FROM, PLANT_TO))
    print("\n=== planted defect (paired median 22.58x -> 31.41x) must be RED ===")
    dirty = run(tmp)
    os.remove(tmp)
    print()
    if clean == 0 and dirty != 0:
        print("COMMISSIONING PASS: clean GREEN, planted defect RED.")
        return 0
    print(f"COMMISSIONING FAIL: clean rc={clean} (want 0), planted rc={dirty} (want nonzero).")
    return 1


if __name__ == "__main__":
    sys.exit(commission() if "--commission" in sys.argv else run(DOC))
