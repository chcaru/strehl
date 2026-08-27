import re, pathlib, sys
def norm(s):
    s = s.replace("\u2014", "--").replace("\u2019", "'")
    # strip Markdown blockquote markers: "sharp and\n> never-sharp" must collapse
    # to "sharp and never-sharp", not "sharp and > never-sharp". Without this a
    # verbatim quote of a blockquoted passage reads as a MISS.
    s = re.sub(r"(?m)^\s*>\s?", "", s)
    return re.sub(r"\s+", " ", s).strip()
src = {p: norm(pathlib.Path(p).read_text(encoding="utf-8", errors="replace"))
       for p in ("docs/research/V-LINEAR.md", "docs/research/V-LINEAR2.md")}
Q = [
 ("docs/research/V-LINEAR.md", "V-LINEAR2.md` \u00a71 overturns this document's reading of the"),
 ("docs/research/V-LINEAR.md", "0.20\u20130.25 cyc/px band, and this file's title restates the superseded"),
 ("docs/research/V-LINEAR.md", "hand-picked **whole-frame** pairs. Letting each of 29 tiles choose its"),
 ("docs/research/V-LINEAR.md", "**R = 2.419, CI [1.961, 3.063]** at 0.20\u20130.25 cyc/px"),
 ("docs/research/V-LINEAR.md", "Whole-frame pairs average sharp and never-sharp regions together and report ~1.0 where per-tile selection recovers a factor of 2.4."),
 ("docs/research/V-LINEAR.md", "**P7 should be registered for 0.25\u20130.48 cyc/px only.**"),
 ("docs/research/V-LINEAR2.md", "at this magnification only a fraction of any frame is in focus, so a whole-frame in-focus/defocused ratio averages the sharp part of the frame together with the parts that were never sharp in either."),
 ("docs/research/V-LINEAR2.md", "| **0.20\u20130.25** | **2.419** | **[1.961, 3.063]** | **PASS** |"),
 ("docs/research/V-LINEAR2.md", "| 0.25\u20130.30 | 1.387 | [1.262, 1.543] | MARGINAL |"),
 ("docs/research/V-LINEAR2.md", "| 0.30\u20130.40 | 1.149 | [1.099, 1.208] | FAIL (noise) |"),
 ("docs/research/V-LINEAR2.md", "| 0.40\u20130.48 | 1.105 | [1.055, 1.165] | FAIL (noise) |"),
 ("docs/research/V-LINEAR2.md", "| 0.05\u20130.10 | 18.193 | [12.420, 28.601] | PASS |"),
 ("docs/research/V-LINEAR2.md", "| 0.10\u20130.20 | 10.083 | [7.465, 13.681] | PASS |"),
]
bad = 0
for p, q in Q:
    ok = norm(q) in src[p]
    print(("  OK   " if ok else "  MISS ") + q[:78])
    bad += not ok
# negative control: a quote that must NOT be found
ctl = "per-tile selection recovers a factor of 9.9"
print(("  CTL-OK " if norm(ctl) not in src["docs/research/V-LINEAR.md"] else "  CTL-FAIL ") + ctl)
print(f"\n{len(Q)-bad}/{len(Q)} quotes verbatim")
sys.exit(1 if bad else 0)

