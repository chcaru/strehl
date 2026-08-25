"""Repair fold138's question insertion.

The anchor "138. " matched an EARLY entry of the question list, not its end.
Questions run to 201. Remove the mis-numbered 139 and re-insert as 202 after
the real last question.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()

BAD_PREFIX = "139. **Is the level drift illumination"
i = raw.index("\n" + BAD_PREFIX)
j = raw.index("\n", i + 1)
bad_line = raw[i + 1 : j]
assert bad_line.startswith(BAD_PREFIX), bad_line[:80]

out = raw.replace("\n" + bad_line, "", 1)
assert out != raw, "removal did not land"
assert BAD_PREFIX not in out, "duplicate copy survived removal"

good_line = "202. " + bad_line[len("139. ") :]

k = out.index("\n201. **What is the base rate of overstatement")
m = out.index("\n", k + 1)
anchor = out[k + 1 : m]
assert anchor.startswith("201. "), anchor[:60]

prev = out
out = out.replace(anchor, anchor + "\n" + good_line, 1)
assert out != prev, "re-insertion did not land"
assert out.count("202. **Is the level drift illumination") == 1

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("question renumbered 139 -> 202 and moved after question 201")
