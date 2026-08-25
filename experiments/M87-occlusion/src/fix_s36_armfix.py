"""M87 / s36 -- repairs the misplacement of arms N47-N52.

fix_s36_arms.py anchored the new arms on `restore()`, which sits AFTER the
loop that executes them. control_s34.arm() only appends to a list; the loop
at the old line 366 consumes it. So the six arms registered into a list that
had already been iterated, never ran, and the suite printed

    control_s34: 46 arms, 0 disagreements

which is a pass. Nothing failed, because nothing executed. **A control arm
placed after its own execution loop is invisible, and a clean report is the
symptom.** The only tell was the arm COUNT -- 46 where 52 was expected.

So this repair moves the block above the loop and then asserts the count,
because "0 disagreements" is not evidence that any particular arm ran.
"""
import pathlib
import re
import sys

C = pathlib.Path(__file__).resolve().parent / "control_s34.py"

LOOP = "    for tag, why, expect, fn, want in arms:"
START = '    arm("N47", "the headline\'s source closure is made to touch the laundered "'
END = '        want="the fraction ratio is small, which is what makes it a retraction")'


def main():
    c = C.read_text(encoding="utf-8")
    lines = c.split("\n")

    if c.count(LOOP) != 1:
        sys.exit("LOOP ANCHOR NOT UNIQUE (%d)" % c.count(LOOP))
    si = [i for i, l in enumerate(lines) if l == START]
    ei = [i for i, l in enumerate(lines) if l == END]
    if len(si) != 1 or len(ei) != 1:
        sys.exit("N47-N52 BLOCK NOT FOUND EXACTLY ONCE (%d/%d)" % (len(si), len(ei)))
    s, e = si[0], ei[0]
    li = lines.index(LOOP)
    if s < li:
        sys.exit("block is ALREADY above the loop -- nothing to repair")
    print(f"block at lines {s + 1}-{e + 1}, loop at {li + 1}: block runs AFTER "
          f"the loop, so it never executed")

    block = lines[s:e + 1]
    del lines[s:e + 1]
    while lines and lines[s:s + 1] == [""]:
        del lines[s]
    li = lines.index(LOOP)
    lines[li:li] = block + [""]
    out = "\n".join(lines)

    ns, nl = out.index(START), out.index(LOOP)
    if ns > nl:
        sys.exit("REPAIR FAILED -- block still below the loop")
    for tag in ("N47", "N48", "N49", "N50", "N51", "N52"):
        if out.count('arm("%s"' % tag) != 1:
            sys.exit("arm %s is not present exactly once" % tag)
    C.write_text(out, encoding="utf-8")
    print("control_s34.py: N47-N52 moved above the execution loop")
    print("NOW RE-RUN control_s34.py AND REQUIRE '52 arms' -- a count, not a "
          "pass, is what detects this defect")
    return 0


if __name__ == "__main__":
    sys.exit(main())
