#!/usr/bin/env python3
"""Commission the Ask 3 bottom-line checks added to vowner0906.py.

WHY THESE CHECKS EXIST. Ask 3 asks the owner for `$289`. It had accumulated
five layers of correction (D1-D4 plus a retraction) across 317 lines for a
decision that never actually changed, so a standing bottom line was added at the
top of the ask. That box now carries the whole action: which edition to buy, why
(blocker (d) gates eight of twelve axes), and three things the purchase is NOT,
each of which I claimed at some point and withdrew. If the box drifts, the owner
spends money on a stale argument.

WHY THIS FILE EXISTS. A check that has never been observed to go RED is a claim
about the check, not about the document. Each check gets the exact defect it
reads planted under it, one at a time, and must go RED alone:

  * MISSED    -- the mutation landed and the check stayed green: decorative.
  * DUPLICATE -- the mutation reddened a check other than its own, or more than
                 one: the checks are not discriminating.

THREE MUTATION SURFACES, and they isolate cleanly:
  * owner-document arms break the owner side of a presence check;
  * PROPOSAL arms break a cross-document quotation. The box quotes the owner's
    governing plan three times, so a drift in the plan must redden here rather
    than leave the owner acting on a quotation that no longer exists;
  * one arm mutates a price constant inside vowner0906.py to prove the `$100`
    upgrade figure is arithmetic and not prose.

ONE ARM IS AN ABSENCE CHECK. "owner does not buy prosumer" guards against the
cheaper edition becoming the recommendation, so its defect is an INSERTION, not
a deletion. Its mutation appends the forbidden string to a unique neighbouring
sentence.

PRE-FLIGHT IS PART OF THE HARNESS, not a separate step. A mutation is a literal
replace on raw bytes while a check reads collapsed, unquoted text, so a phrase
that wraps across a line break is findable by the check and unreachable by the
mutation. Every arm's target is therefore required to occur EXACTLY ONCE in the
raw file before any arm runs. A target that is missing, or that occurs twice --
where a second copy would silently satisfy the check -- is a harness failure and
a hard error, not a pass.

Everything happens in a TEMP copy; the live tree is never written, because ~25
other agents read it concurrently.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REAL = Path(__file__).resolve().parents[2]
VNAME = "vowner0906.py"

OWNER_REL = "docs/OWNER-ACTIONS.md"
PROP_REL = "docs/proposals/2026-08-sota-path.md"
V_REL = "experiments/ORCH-verify/" + VNAME

# (check label, relative path to mutate, exact raw text, replacement)
ARMS = [
    # ---- the action itself ----
    ("owner buys professional", OWNER_REL,
     "Buy Zerene Stacker Professional, `$289`.",
     "Buy Zerene Stacker Professional, `$290`."),
    ("owner counts eight axes", OWNER_REL,
     "gating **eight of the twelve axes**",
     "gating **seven of the twelve axes**"),
    # Anchored on the full clause, not the bare code: the code occurs twice in
    # the owner file, so a bare-code anchor could never redden its own check.
    ("owner names m11 code", OWNER_REL,
     "blocked by the same thing under the name "
     "`UNMEASURED_COMPARATOR_QUALIFICATION`).",
     "blocked by the same thing under the name "
     "`UNMEASURED_COMPARATOR_LICENSING`)."),

    # ---- the three withdrawals: each is a claim I made and retracted ----
    ("owner withdraws m12 reason", OWNER_REL,
     "It does not unblock M12.", "It may not unblock M12."),
    ("owner withdraws urgency", OWNER_REL,
     "It is not urgent, and nothing is ageing.",
     "It is not urgent, and nothing is aging."),
    ("owner frees helicon", OWNER_REL,
     "It is not held up by Helicon.",
     "It is not held up by Helicon Focus."),

    ("owner says action unchanged", OWNER_REL,
     "action has never changed: **buy Professional.**",
     "action has rarely changed: **buy Professional.**"),

    # ---- absence arm: the defect is an insertion ----
    # Anchored on the heading line, which is raw-contiguous. The neighbouring
    # `$100` sentence wraps across a line break, so a literal replace on it
    # cannot land -- exactly the failure the pre-flight is there to catch.
    ("owner does not buy prosumer", OWNER_REL,
     "You do not need to read the rest of this ask to act on it.",
     "You do not need to read the rest of this ask to act on it. "
     "Buy Zerene Stacker Prosumer."),

    # ---- cross-document arms: the box quotes the governing plan ----
    ("proposal has blocker d", PROP_REL,
     "licence a commercial comparator", "license a commercial comparator"),
    ("proposal has the export", PROP_REL,
     "Save Adjusted Input Images", "Save Adjusted Source Images"),
    ("proposal makes helicon optional", PROP_REL,
     "Helicon if obtainable", "Helicon if available"),

    # ---- derivation arm: mutate the price constant, not the prose ----
    ("upgrade delta re-derives", V_REL,
     "PRO_PRICE, PROS_PRICE = 289, 189",
     "PRO_PRICE, PROS_PRICE = 289, 188"),
]

# A mutation that should redden NOTHING. Without it, a harness that reddened on
# every input would score a perfect 12/12 and look identical to a working one.
INERT = (OWNER_REL,
         "so you can audit me.", "so that you can audit me.")


def run(root):
    """Return the set of check labels currently RED.

    The verifier executed is the copy INSIDE `root`, not the live one. That is
    load-bearing: the price-constant arm mutates vowner0906.py itself, and if
    this invoked the real verifier against a TEMP document root the mutation
    would be inert by construction and the arm would read MISSED/decorative
    when the check is in fact sound. Passing REAL as root therefore exercises
    the live tree end to end.
    """
    proc = subprocess.run(
        [sys.executable, str(root / "experiments" / "ORCH-verify" / VNAME),
         str(root)],
        capture_output=True, text=True)
    reds = set()
    for line in proc.stdout.splitlines():
        if line.startswith("RED ") or line.startswith("CTLFAIL"):
            # 'RED   ask3   <label padded>  <diagnostic>' -- strip the known
            # diagnostic suffixes explicitly rather than trusting padding width,
            # because a narrow pad folds the diagnostic into the label and makes
            # a check that genuinely fired read as MISSED.
            body = line[3:].strip() if line.startswith("RED") else line
            for tag in ("ask3", "4bar", "m12ret", "m12der", "banner", "ctl"):
                if body.startswith(tag):
                    body = body[len(tag):].strip()
                    break
            for cut in (" expected ", " SOURCE MISSING", " $289", " DID NOT",
                        " ABSENT"):
                i = body.find(cut)
                if i > 0:
                    body = body[:i]
            reds.add(body.strip())
    return reds, proc.stdout


def stage():
    """Copy the tree vowner0906.py reads into a TEMP root."""
    tmp = Path(tempfile.mkdtemp(prefix="ask3_"))
    for rel in ("docs", "experiments/ORCH-verify"):
        src = REAL / rel
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
    return tmp


def main():
    tmp = stage()
    print("TEMP root: %s" % tmp)

    # ---- pre-flight: every arm target must be raw-unique before anything runs
    bad = []
    for label, rel, old, _new in ARMS + [("INERT", INERT[0], INERT[1], None)]:
        n = (tmp / rel).read_text(encoding="utf-8").count(old)
        if n != 1:
            bad.append("%-32s occurs %d times in %s: %r" % (label, n, rel, old))
    if bad:
        print("FATAL: arm targets are not raw-unique. A missing target cannot "
              "mutate; a duplicated one leaves a copy that satisfies the check.")
        for b in bad:
            print("  " + b)
        sys.exit(2)
    print("pre-flight: all %d arm targets are raw-unique" % (len(ARMS) + 1))

    base_reds, base_out = run(tmp)
    if base_reds:
        print("FATAL: TEMP baseline is not GREEN. reds=%s" % sorted(base_reds))
        print(base_out)
        sys.exit(2)
    print("baseline TEMP: GREEN")

    caught = missed = dup = 0
    for label, rel, old, new in ARMS:
        p = tmp / rel
        original = p.read_text(encoding="utf-8")
        assert original.count(old) == 1
        p.write_text(original.replace(old, new, 1), encoding="utf-8")
        reds, _ = run(tmp)
        p.write_text(original, encoding="utf-8")

        if reds == {label}:
            print("CAUGHT    %s" % label)
            caught += 1
        elif not reds:
            print("MISSED    %s  <-- DECORATIVE: defect planted, check silent"
                  % label)
            missed += 1
        else:
            print("DUPLICATE %s  <-- reddened %s" % (label, sorted(reds)))
            dup += 1

    # ---- inert arm ----
    rel, old, new = INERT
    p = tmp / rel
    original = p.read_text(encoding="utf-8")
    p.write_text(original.replace(old, new, 1), encoding="utf-8")
    inert_reds, _ = run(tmp)
    p.write_text(original, encoding="utf-8")
    inert_ok = not inert_reds
    print("INERT     %s" % ("held (no check reddened)"
                            if inert_ok else "FAILED, reddened %s"
                            % sorted(inert_reds)))

    post_reds, _ = run(tmp)
    restored = not post_reds
    print("post-restore TEMP: %s" % ("GREEN" if restored else "RED %s"
                                     % sorted(post_reds)))

    live_reds, _ = run(REAL)
    print("live tree: %s" % ("GREEN" if not live_reds else "RED %s"
                             % sorted(live_reds)))

    print()
    print("ARMS %d / CAUGHT %d / MISSED %d / DUPLICATE %d"
          % (len(ARMS), caught, missed, dup))
    ok = (missed == 0 and dup == 0 and inert_ok and restored and not live_reds)
    print("VERDICT: " + ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
    shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
