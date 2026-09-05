"""Prove the owner-facing bench sheet is lane M166's protocol, unaltered.

OWNER-ACTIONS.md tells the owner, in my voice, that the ten-step rehearsal
shooting order is *"lane M166's, not mine, and I have left it as written."*
That is a claim about my own fidelity, and it is exactly the kind of claim that
rots silently: a later copy-edit to the owner document -- a reflow, a tightened
sentence, a "clarifying" word -- would quietly turn the lane's capture protocol
into my paraphrase of it, and nothing else in the tree would notice.

Capture protocol is not mine to author. The lane that costed and sequenced the
evening owns it. So this compares the ten numbered steps as they appear in
OWNER-ACTIONS.md against the same steps in M166's section 8, token by token,
and fails if they have diverged at all.

It also re-derives the frame arithmetic from the step text rather than trusting
either document's stated total, because a bench sheet whose blocks do not sum
to the number the owner is told to expect is worse than no bench sheet.

Run from the repo root:  python experiments/ORCH-verify/vbench.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
OWNER = ROOT / "docs" / "OWNER-ACTIONS.md"
SOURCE = ROOT / "docs" / "research" / "M166-rehearsal-cost.md"

EXPECTED_TOTAL = 1092
# Step number -> frames that step adds. Step 1-3 are preparation and add none.
EXPECTED_BLOCKS = {4: 128, 5: 192, 6: 128, 7: 164, 8: 224, 9: 192, 10: 64}


def strip_quote(block):
    """Drop one level of Markdown blockquote marker from each line."""
    out = []
    for line in block.split("\n"):
        out.append(re.sub(r"^\s*>\s?", "", line))
    return "\n".join(out)


def norm(s):
    """Collapse whitespace so a reflow is not mistaken for an edit.

    Markdown wraps prose at arbitrary columns and both documents were written
    by different hands, so a raw comparison would report a false difference on
    every line. Only the token sequence is meaningful here.
    """
    return re.sub(r"\s+", " ", s).strip()


def extract_steps(text):
    """Return {step number: normalised step text} for a ten-step list.

    Anchored on a line that begins a numbered item, so a step that loses its
    number -- the most likely way a step silently disappears in an edit -- is
    reported as missing rather than being merged into its predecessor.
    """
    text = strip_quote(text)
    starts = [(int(m.group(1)), m.start())
              for m in re.finditer(r"(?m)^\s*(\d{1,2})\.\s+\*\*", text)]
    steps = {}
    for i, (num, pos) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        if num in steps:
            print("RED   step %d appears more than once in one document" % num)
        steps[num] = norm(text[pos:end])
    return steps


def owner_block(text):
    """The bench-sheet blockquote in OWNER-ACTIONS.md.

    The sheet is one contiguous blockquote: every line inside it starts with
    '>', including the separators between steps. My own commentary follows it
    as a *separate* blockquote after a genuinely empty line. Cutting at the
    next '###' heading instead would swallow that commentary into step 10 and
    report a divergence that is mine, not the document's -- which is exactly
    what this check did on its first run.
    """
    head = "### Development rehearsal — one clean pass still needs 1,092"
    i = text.find(head)
    if i < 0:
        return None
    lines = text[i:].split("\n")
    out = []
    for k, line in enumerate(lines):
        if k and not line.strip():
            break
        out.append(line)
    return "\n".join(out)


def source_block(text):
    head = "## 8. Paste-ready owner-facing replacement text"
    i = text.find(head)
    if i < 0:
        return None
    j = text.find("\n## ", i + len(head))
    return text[i:j if j > 0 else len(text)]


owner_raw = OWNER.read_text(encoding="utf-8", errors="replace")
src_raw = SOURCE.read_text(encoding="utf-8", errors="replace")

ob = owner_block(owner_raw)
sb = source_block(src_raw)

red = 0
if ob is None:
    print("RED   bench sheet not found in %s" % OWNER)
    red += 1
if sb is None:
    print("RED   section 8 not found in %s" % SOURCE)
    red += 1
if red:
    print("\nVERDICT: RED")
    raise SystemExit(1)

o_steps = extract_steps(ob)
s_steps = extract_steps(sb)

green = 0
for n in range(1, 11):
    if n not in s_steps:
        print("RED   step %-2d missing from M166 section 8" % n)
        red += 1
        continue
    if n not in o_steps:
        print("RED   step %-2d missing from the owner bench sheet" % n)
        red += 1
        continue
    if o_steps[n] != s_steps[n]:
        print("RED   step %-2d DIVERGED from M166's text" % n)
        # Show the first differing token so the drift is actionable, not just
        # reported. A bare "they differ" sends the reader back to a diff tool.
        ot, st = o_steps[n].split(" "), s_steps[n].split(" ")
        for k in range(max(len(ot), len(st))):
            a = ot[k] if k < len(ot) else "<end>"
            b = st[k] if k < len(st) else "<end>"
            if a != b:
                print("      first difference at token %d: owner %r vs M166 %r"
                      % (k, a, b))
                break
        red += 1
        continue
    print("GREEN step %-2d verbatim from M166" % n)
    green += 1

# Re-derive the total from the step text itself rather than trusting either
# document's stated figure.
derived = 0
arith = 0
for n, want in sorted(EXPECTED_BLOCKS.items()):
    if n not in o_steps:
        continue
    m = re.search(r"(\d{2,4}) (?:more |final )?frames", o_steps[n])
    if not m:
        print("RED   step %-2d states no frame count" % n)
        red += 1
        continue
    got = int(m.group(1))
    if got != want:
        print("RED   step %-2d frame count is %d, expected %d" % (n, got, want))
        red += 1
        continue
    derived += got
    arith += 1
    print("GREEN step %-2d contributes %3d frames" % (n, got))

if derived != EXPECTED_TOTAL:
    print("RED   blocks sum to %d, not the %d the owner is told to expect"
          % (derived, EXPECTED_TOTAL))
    red += 1
else:
    print("GREEN blocks sum to %d, matching the stated total" % derived)
    green += 1

print("\nsteps verbatim   : %d of 10" % sum(1 for n in range(1, 11)
                                          if n in o_steps and n in s_steps
                                          and o_steps[n] == s_steps[n]))
print("frame blocks ok  : %d of %d" % (arith, len(EXPECTED_BLOCKS)))
print("GREEN            : %d" % green)
print("RED              : %d" % red)
print("\nVERDICT: %s" % ("GREEN" if red == 0 else "RED"))
raise SystemExit(1 if red else 0)
