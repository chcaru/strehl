"""Bank facts 1865-1868. Same anchor discipline as add_1851.py."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR_PREFIX = "| 1864 | MEASURED | BUILD-CROP |"

ROWS = [
    ("1865", "MEASURED", "ORCH",
     "**SWITCHING THE LATERAL-CA CORRECTION OFF IS 30% WORSE, NOT 1.82x BETTER; THE STATISTIC THAT "
     "PREFERRED IT COULD ONLY SEE ONE OF THE TWO ARTIFACT SHAPES.** "
     "Hue-neutral chroma magnitude `sqrt((R-G)^2 + (B-G)^2) / max(G,256)` on one edge population "
     "derived from A and applied to both renders: CA ON edge_mean 0.15999 and p99 0.54862, "
     "CA OFF 0.20807 and 0.78324, so OFF is +30.0% at the mean and +43% at the p99. "
     "The flat control moves only 0.05700 to 0.05757, which is what makes this a displacement "
     "result rather than a colour cast. The over-correction drives R and B to the SAME side of an "
     "edge and reads as magenta; disabling it restores the lens's OPPOSITE-side artifact, which "
     "reads as orange and cyan and which a magenta counter cannot see by construction. "
     "The correction is net beneficial AND over-corrected at the same time, which is a coherent "
     "state and the one the `eps_r` re-fit is for. The 704.5 ppm finding is unaffected: it rests "
     "on the file's own comment and on a pre-declared radial falsification, not on the counter."),

    ("1866", "MEASURED", "ORCH",
     "**A METRIC MUST BE COMMISSIONED AGAINST EVERY ARTIFACT SHAPE IT WILL BE ASKED TO RANK, NOT "
     "MERELY AGAINST THE ONE ITS AUTHOR WAS CHASING.** `orch_chromamag.py` refuses to report a "
     "verdict at all until it has been planted with both shapes and stayed silent on a null: "
     "same-direction R+1px B+1px gives +68.6%, opposite-direction R+1px B-1px gives +73.1%, "
     "unmodified copy gives +0.0%. A one-shape counter reached a shipping recommendation tonight "
     "and was wrong by 30% in the opposite direction. This is the same family as BUILD-CROP's own "
     "withdrawn ranking instrument, which passed a planted-1px control and then ranked `109MSDCF` "
     "7x above the subject a human actually saw: sensitivity commissioned, specificity never."),

    ("1867", "MEASURED", "ORCH",
     "**AN UNEXPLAINED GREEN-CHANNEL DIFFERENCE BETWEEN THE CA-ON AND CA-OFF RENDERS, WHICH WOULD "
     "CONFOUND ANY COMPARISON BETWEEN THEM.** On `dry-erase-marker-head-cpl`, G differs on "
     "30,872,990 px with mean 51.39 DN and max 9595 DN, against R on 31,206,258 px at max 35994 DN "
     "and B on 31,077,001 px at max 23327 DN. A correction that displaces only R and B should leave "
     "G bit-identical. Three candidate explanations, none tested: the correction touches G; or "
     "moving R and B changes which frame the merge selects and G follows as a second-order effect, "
     "which would be a real and interesting coupling; or the two renders differ in something "
     "besides the flag, which would invalidate every number measured across that pair. "
     "OPEN. Nothing should be concluded from that render pair until it is resolved."),

    ("1868", "MEASURED", "ORCH",
     "**AN ARGMAX OVER A PLATEAU RETURNS ITS FIRST RASTER ELEMENT, NOT ITS CENTRE, AND THE OFFSET "
     "LOOKS EXACTLY LIKE A LOCALISATION ERROR.** Commissioning `orch_abdiff.py` with a uniform disc "
     "of radius 60 under a box filter of radius 8 reported the site 51 px above the plant, a "
     "systematic offset of exactly (disc - box) = 52 px, because a box filter over a uniform region "
     "produces a plateau of exactly equal values. The tool was correct and the acceptance criterion "
     "was wrong. Refining each site to the centroid of its maximal plateau, searched only in a "
     "window about the argmax so a distant equal-valued region cannot drag the site off the "
     "feature, gives a distance of 0.0 px. Left unrefined, every crop this tool draws would sit off "
     "the edge of the thing it exists to show."),
]


def build_row(num, status, source, body):
    if "|" in body:
        raise SystemExit("REFUSED: raw pipe in fact %s truncates the table row" % num)
    if body.count("*") % 2 != 0:
        raise SystemExit("REFUSED: odd asterisk count in fact %s leaves italics open" % num)
    return "| %s | %s | %s | %s |" % (num, status, source, body)


def main():
    with io.open(PATH, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(newline)

    hits = [i for i, ln in enumerate(lines) if ln.startswith(ANCHOR_PREFIX)]
    if len(hits) != 1:
        raise SystemExit("REFUSED: anchor %r matched %d rows, expected 1"
                         % (ANCHOR_PREFIX, len(hits)))
    at = hits[0]
    for num, _s, _src, _b in ROWS:
        if any(ln.startswith("| %s |" % num) for ln in lines):
            raise SystemExit("REFUSED: fact %s already present" % num)

    new_rows = [build_row(*r) for r in ROWS]
    lines[at + 1: at + 1] = new_rows
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(newline.join(lines))
    print("inserted %d rows after fact 1864 (line %d)" % (len(new_rows), at + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
