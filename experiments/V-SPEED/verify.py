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


def expected_ratios():
    """Every paired median ratio, re-derived from the JSONL.

    Returned as (subject, arm, ratio) so a directional claim in the prose can
    be checked against the sign of a measured number rather than against the
    presence of a word.
    """
    vals = []
    for tag, subject, frames in SUBJECTS:
        rounds = load(tag)
        warm = sorted(r for r in rounds if r != 0)
        st = totals(rounds, "strehl")
        for arm in ("enfuse", "focus-stack"):
            t = totals(rounds, arm)
            pr = [t[r] / st[r] for r in warm if r in t and r in st]
            if pr:
                vals.append((subject, arm, statistics.median(pr)))
    return vals


# Any directional ratio claim anywhere in the document, in prose or in a
# blockquote, bolded or not, with or without a "strehl is" prefix.  Measured:
# this matches 9 claims, of which 6 correspond to a re-derived paired median.
CLAIM_RE = re.compile(
    r"([0-9]+(?:\.[0-9]+)?)\s*\u00d7\s*\**\s*(faster|slower)\b",
    re.IGNORECASE)

# Deleting claims must not pass vacuously.  Six of the document's directional
# claims are re-derivable from the JSONL; requiring at least that many means a
# mutation that removes one is RED even though it also removes the evidence of
# its own removal.  The value is MEASURED from the clean document, not chosen
# to make this test pass -- an earlier guess of 6 against a narrower regex
# that only found 5 correctly turned the clean document RED.
MIN_CERTIFIED = 6


def check_conclusions(doc, quiet=False):
    """Certify the DIRECTION of every ratio claim, not merely its presence.

    WHY THIS EXISTS.  Everything above re-derives NUMBERS, so a numeric
    mutation is caught by construction -- that is what the paired-median
    plant commissions.  It is not what a report gets wrong.  Measured on this
    very file (experiments/V-SPEED/flipcheck.ps1): flipping the document's
    single loudest claim from "22.6x faster" to "22.6x SLOWER", leaving every
    digit correct, scored 20/20 GREEN.  The verifier certified the arithmetic
    of a report whose headline now said the opposite of what was measured.

    A presence test cannot detect a reversed conclusion, and it is satisfied
    by any duplicate or paraphrase elsewhere.  So each claim is matched to a
    re-derived ratio by its VALUE and then required to carry the direction
    word implied by that ratio's sign.

    WHAT THIS DOES NOT CERTIFY, stated rather than hidden: three of the
    document's claims (5.70x and 2.11x in section 0, 2.1x in the pull quote)
    describe the MERGE-ONLY comparison, not the paired end-to-end medians, so
    no re-derived ratio has their value and their direction is unchecked.
    They are counted and printed as UNCERTIFIED.  A count that does not move
    is the same glyph whether nothing was wrong or nothing was examined, so
    certified + reversed + uncertified always sums to the claims found.
    """
    ratios = expected_ratios()
    claims = CLAIM_RE.findall(doc)
    certified, flipped, uncertified = 0, [], []

    for num_s, word in claims:
        num = float(num_s)
        dp = len(num_s.split(".")[1]) if "." in num_s else 0
        tol = 0.5 * (10 ** -dp)
        hit = [(s, a, r) for (s, a, r) in ratios if abs(round(r, dp) - num) <= tol]
        if not hit:
            uncertified.append(f"{num_s}\u00d7 {word}")
            continue
        want = "faster" if hit[0][2] > 1.0 else "slower"
        if word.lower() != want:
            flipped.append(
                f"{num_s}\u00d7 says '{word}' but the measured ratio is "
                f"{hit[0][2]:.4f} ({hit[0][0]}/{hit[0][1]}), which is '{want}'")
        else:
            certified += 1

    short = certified < MIN_CERTIFIED
    if not quiet:
        for b in flipped:
            print(f"  REVERSED    {b}")
        if uncertified:
            print(f"  UNCERTIFIED {len(uncertified)} claim(s) match no re-derived "
                  f"ratio, direction unchecked: {', '.join(uncertified)}")
        if short:
            print(f"  TOO FEW     only {certified} certified claims, expected at "
                  f"least {MIN_CERTIFIED} -- claims cannot be deleted to pass")
    print(f"{certified} certified + {len(flipped)} reversed + "
          f"{len(uncertified)} uncertified = {len(claims)} directional claims  "
          f"{'GREEN' if not flipped and not short else 'RED'}")
    return 0 if (not flipped and not short) else 1


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
    rc_dir = check_conclusions(doc, quiet=quiet)
    return 0 if (not bad and rc_dir == 0) else 1


PLANT_FROM = ("| coffee-bean | 105 | align+enfuse | 28.80\u00d7, 22.58\u00d7, 19.56\u00d7 | "
              "**22.58\u00d7** | 19.56\u00d7 | 28.80\u00d7 |")
PLANT_TO = ("| coffee-bean | 105 | align+enfuse | 28.80\u00d7, 22.58\u00d7, 19.56\u00d7 | "
            "**31.41\u00d7** | 19.56\u00d7 | 28.80\u00d7 |")

# The conclusion-flip plant.  Anchored on the full bolded phrase so it cannot
# land on some other sentence: measured, it occurs exactly once.  Every digit
# is identical on both sides -- only the direction reverses.
FLIP_FROM = "strehl is **22.6\u00d7 faster than Hugin align_image_stack + enfuse**"
FLIP_TO = "strehl is **22.6\u00d7 slower than Hugin align_image_stack + enfuse**"


def commission():
    src = open(DOC, encoding="utf-8").read()
    if src.count(PLANT_FROM) != 1:
        raise SystemExit(
            f"MUTATION TARGET NOT FOUND: anchor occurs {src.count(PLANT_FROM)} times, "
            "expected exactly 1. Refusing to report a commissioning result."
        )
    if src.count(FLIP_FROM) != 1:
        raise SystemExit(
            f"MUTATION TARGET NOT FOUND: conclusion anchor occurs "
            f"{src.count(FLIP_FROM)} times, expected exactly 1. "
            "Refusing to report a commissioning result."
        )
    print("=== clean document must be GREEN ===")
    clean = run(DOC)

    tmp = os.path.join(tempfile.gettempdir(), "V-SPEED-mutated.md")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(src.replace(PLANT_FROM, PLANT_TO))
    print("\n=== planted NUMBER defect (paired median 22.58x -> 31.41x) must be RED ===")
    dirty = run(tmp)
    os.remove(tmp)

    # The mutation that defeated this verifier before check_conclusions
    # existed: every digit stays correct and only the direction reverses.
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(src.replace(FLIP_FROM, FLIP_TO))
    print("\n=== planted CONCLUSION flip (22.6x faster -> SLOWER) must be RED ===")
    flip = run(tmp)
    os.remove(tmp)

    # A verifier that can be satisfied by deleting the claims is not a
    # verifier.  Removing every directional sentence must also be RED.
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(CLAIM_RE.sub("strehl is (claim removed)", src))
    print("\n=== all directional claims DELETED must be RED (not vacuously green) ===")
    gone = run(tmp)
    os.remove(tmp)

    # SPECIFICITY. Commissioning sensitivity is not commissioning specificity:
    # planting a defect and seeing it caught says nothing about whether benign
    # text is rejected. Innocuous prose -- including prose carrying a number
    # that is not a claim -- must score 0, or the verifier is just noisy.
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(src + "\n\nAll timings in this report were collected on one "
                       "machine over a single night; the deepest stack "
                       "examined contains 299 frames.\n")
    print("\n=== innocuous prose (no claim, but carries a number) must be GREEN ===")
    benign = run(tmp)
    os.remove(tmp)

    print()
    if clean == 0 and dirty != 0 and flip != 0 and gone != 0 and benign == 0:
        print("COMMISSIONING PASS: clean GREEN; number defect, conclusion flip "
              "and claim deletion all RED; innocuous prose GREEN.")
        return 0
    print(f"COMMISSIONING FAIL: clean rc={clean} (want 0), number rc={dirty}, "
          f"flip rc={flip}, deletion rc={gone} (all want nonzero), "
          f"innocuous prose rc={benign} (want 0).")
    return 1


if __name__ == "__main__":
    sys.exit(commission() if "--commission" in sys.argv else run(DOC))
