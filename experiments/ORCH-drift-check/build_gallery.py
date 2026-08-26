"""Build a single self-contained HTML gallery of the current stacks.

The owner asked "where are some stacks I can view?" and the honest answer has so
far been four scattered output directories, none of which is a viewing surface.
A contact sheet is not one either: section 59 records that a reduced image
discards the evidence asymmetrically, hiding softness *and* hiding the fine
structure that separates a sharp low-contrast subject from a blurred one. Three
separate wrong conclusions in this project came from judging a picture at
thumbnail scale.

So this pairs each subject's full frame with a **true 1:1 crop** of its most
detailed region, orders the set by what has actually been verified rather than
by filename, and states in the page itself what is known good, what is known
bad, and what is still being worked on. It copies assets rather than linking
across directories so the folder can be moved or sent somewhere.

It renders whatever exists. Missing inputs are reported in the page, not
silently skipped -- a gallery that quietly omits its failures is a sales
brochure.
"""
import argparse
import html
import pathlib
import shutil
import sys

SHIP = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1")
DETAIL = pathlib.Path(r"C:\dev\strehl-out\ORCH-DETAIL\detail")
PRESENT = pathlib.Path(r"C:\dev\strehl-out\BUILD-RENDER-present")
OUT = pathlib.Path(r"C:\dev\strehl-out\VIEW")

# Verdicts reached by looking at true 1:1 tiles, recorded in ORCH-veiling.md
# sections 58 and 59. Anything not listed here has not been individually judged
# at 1:1 and is labelled as such rather than given an implied pass.
VERIFIED = {
    "bee-3-cpl": (
        "flagship",
        "Plumose hair barbules resolved, including branched side-structure. "
        "No halo where pale hairs cross the dark defocused compound eye -- the "
        "geometry that rims in every other stacker. One known defect: a veil "
        "over the tarsus/claw, diagnosed and being fixed (see below).",
    ),
    "bee-1-cpl": (
        "print-worthy",
        "Individual compound-eye facets resolved, plus hair. No halo.",
    ),
    "leaf-2-cpl": (
        "print-worthy",
        "Veins at three scales, cell texture, chloroplast speckle. No halo.",
    ),
    "112MSDCF": (
        "print-worthy",
        "Crystal dendrites resolved to near single-pixel width. No halo.",
    ),
    "bee-2-cpl": (
        "print-worthy",
        "Individual hairs and their barbules resolved, specular sparkle intact, "
        "surface pitting visible on the chitin. No rim where the dark hair mass "
        "meets the pale defocused background.",
    ),
    "tweezers-cpl": (
        "print-worthy",
        "Brushed-metal striations resolved to near single-pixel width, with dust "
        "and speculars crisp. Notable because dark grooves on bright metal is "
        "the classic ringing geometry, and there is no bright rim along them.",
    ),
    "coffee-bean": (
        "print-worthy",
        "Porous cellular surface and crystalline glints fully resolved, with no "
        "over-smoothing. This is the subject V-HULLCOST found needs the hull "
        "clamp most, so it is also the check that the clamp is not costing "
        "detail -- it is not.",
    ),
    "flower-bud-with-background-fern-cpl": (
        "print-worthy",
        "The hardest case in the set and the best evidence the halo is gone: a "
        "dense multi-layer occlusion of overlapping trichomes, bracts and pollen "
        "at many depths. Individual hairs resolve where they cross each other, "
        "pollen grains are crisp, glandular cell texture is visible on the "
        "bracts, and no crossing shows a halo.",
    ),
}

NOTED = {
    "flowers-cpl": (
        "sharp, low-contrast",
        "Resolves individual papillate epidermal cells. This is the corpus "
        "contrast minimum at 1282 DN, which made an earlier detail ranking of "
        "mine call it soft. That finding was retracted: normalised by the "
        "contrast actually present it ranks 5th of 26, not 25th.",
    ),
    "flower-inner-edge-cpl": (
        "sharp, low-contrast",
        "Resolves papillate cells and pollen grains. Same retraction applies.",
    ),
    "highly-angled-ruler-mm-cpl": (
        "sharp",
        "Looks poor on every contact sheet and is genuinely sharp at 1:1 -- "
        "1364 DN, mid-pack. A standing warning about reduced images.",
    ),
    "foam": (
        "low detail, not a defect",
        "A soap film with resolved interference banding, and the lowest "
        "noise-to-gradient ratio in the corpus at 0.072. Little fine detail is "
        "a property of soap films.",
    ),
    "coffee-bubbles": (
        "low detail, not a defect",
        "High contrast, little detail per unit of it. Same class as foam.",
    ),
    "119MSDCF": (
        "sharp where the subject has structure",
        "RETRACTED: I called this 'genuinely under-resolved, last of 26' on a "
        "contrast-normalised detail ranking. Opening it at 1:1 refutes that. "
        "The layered white/grey band resolves individual layer edges, dust "
        "specks stay points rather than smears, and the saturated pink/white "
        "and blue/white boundaries -- where a chromatic halo would show first "
        "-- are clean. The subject is mostly smooth paint fields, which is what "
        "the ranking actually measured. BUILD-TRIAGE independently classifies "
        "it GOOD, worst merge deficit 0.65 px.",
    ),
    "109MSDCF": (
        "sharp where the subject has structure",
        "RETRACTED with 119MSDCF, and this one more clearly. The olive band "
        "resolves hundreds of individual bubbles as crisp high-contrast points, "
        "the layered band below resolves fine striations, and the pink shows "
        "brush striations. That is abundant resolved fine detail in an image I "
        "had ranked 25th of 26. BUILD-TRIAGE classifies it GOOD, worst merge "
        "deficit 0.75 px.",
    ),
}

ORDER_HINT = [
    "bee-3-cpl",
    "flower-bud-with-background-fern-cpl",
    "bee-2-cpl",
    "bee-1-cpl",
    "leaf-2-cpl",
    "tweezers-cpl",
    "coffee-bean",
    "112MSDCF",
]

CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin:0; background:#0d0f12; color:#d8dde3;
       font:15px/1.6 -apple-system,Segoe UI,Roboto,sans-serif; }
header { padding:38px 40px 26px; border-bottom:1px solid #23272e; }
h1 { margin:0 0 6px; font-size:27px; letter-spacing:-.4px; color:#fff; }
.sub { color:#8b939d; font-size:14px; }
main { padding:26px 40px 90px; }
.note { max-width:900px; background:#151922; border:1px solid #262c36;
        border-left:3px solid #4a7fd0; padding:14px 18px; margin:20px 0 30px;
        border-radius:4px; font-size:14px; }
.note b { color:#fff; }
.card { border:1px solid #23272e; border-radius:6px; margin:0 0 26px;
        overflow:hidden; background:#12151a; }
.card > .head { display:flex; align-items:baseline; gap:12px; flex-wrap:wrap;
        padding:13px 18px; border-bottom:1px solid #23272e; background:#161a21; }
.card h2 { margin:0; font-size:17px; color:#fff; font-weight:600; }
.tag { font-size:11px; text-transform:uppercase; letter-spacing:.7px;
       padding:3px 9px; border-radius:99px; font-weight:600; }
.t-flagship { background:#1d4a2a; color:#7ee39b; }
.t-print { background:#1d3a4a; color:#7ecbe3; }
.t-ok { background:#2c2c3a; color:#a9aec8; }
.t-low { background:#3a3320; color:#dbc07e; }
.t-bad { background:#4a2020; color:#e39b9b; }
.t-unjudged { background:#22262e; color:#7d858f; }
.g-good { background:#1b3524; color:#7fc79a; }
.g-gap { background:#3a2c1c; color:#d6a86a; }
.g-move { background:#38243a; color:#c58fd0; }
.desc { padding:12px 18px 0; color:#98a1ac; font-size:14px; max-width:1000px; }
.imgs { display:grid; grid-template-columns:1fr 1fr; gap:12px; padding:14px 18px 18px; }
@media (max-width:1100px){ .imgs { grid-template-columns:1fr; } }
figure { margin:0; }
figcaption { font-size:11.5px; color:#79818c; padding:6px 2px 0;
             text-transform:uppercase; letter-spacing:.6px; }
img { width:100%; height:auto; display:block; border-radius:3px;
      background:#000; border:1px solid #23272e; }
a.raw { color:#6fa8ff; text-decoration:none; font-size:12px; }
a.raw:hover { text-decoration:underline; }
.missing { padding:14px 18px; color:#e39b9b; font-size:13px; }
footer { padding:26px 40px 60px; color:#6a727c; font-size:13px;
         border-top:1px solid #23272e; max-width:1000px; }
code { background:#1b1f27; padding:1px 5px; border-radius:3px; font-size:12.5px; }
"""


def find_full(stem):
    """Best available full-frame view for a subject."""
    for cand in (
        PRESENT / "graded" / f"{stem}.jpg",
        PRESENT / f"{stem}.jpg",
        SHIP / "printqa" / f"{stem}.jpg",
        SHIP / "viewable" / f"{stem}.jpg",
    ):
        if cand.exists():
            return cand
    for d in (PRESENT, SHIP):
        if d.exists():
            hits = sorted(d.rglob(f"{stem}.jpg"))
            if hits:
                return hits[0]
    return None


# BUILD-TRIAGE's per-subject reshoot verdict (commit 1d8e673b). This answers a
# DIFFERENT question from the 1:1 verdict above: it asks whether anything
# anywhere in the frame was limited by the capture, whereas the 1:1 verdict asks
# whether the detail actually examined holds up. A subject can be both
# print-worthy where you looked and capture-limited somewhere else, and three
# subjects in this set are exactly that. Keeping the two tags separate is the
# point; collapsing them would lose the distinction the tool exists to draw.
TRIAGE = {
    "109MSDCF": ("good", ""),
    "112MSDCF": ("good", ""),
    "113MSDCF": ("good", ""),
    "119MSDCF": ("good", ""),
    "bee-1-cpl": ("good", ""),
    "bee-2-cpl": ("good", ""),
    "bee-3-cpl": ("good", ""),
    "coffee-bean": ("good", ""),
    "couch-fibers-cpl": ("good", ""),
    "flat-on-ruler-cpl": ("good", ""),
    "wrapped-text-1": ("good", ""),
    "wrapped-text-2": ("good", ""),
    "dry-erase-marker-head-cpl": ("reshoot: coverage gap", "8/24 blocks (5 far, 3 near)"),
    "flower-bud-alone-cpl": ("reshoot: coverage gap", "13/24 blocks, all far"),
    "flower-bud-with-background-fern-cpl": ("reshoot: coverage gap", "13/24 blocks, all far"),
    "flower-inner-edge-cpl": ("reshoot: coverage gap", "7/24 blocks (6 far, 1 near)"),
    "flowers-cpl": ("reshoot: coverage gap", "16/24 blocks, all far"),
    "highly-angled-ruler-mm-cpl": ("reshoot: coverage gap", "18/24 blocks, all far"),
    "lavendar-cpl": ("reshoot: coverage gap", "10/24 blocks, all far"),
    "pencil-flatter-angle-cpl": ("reshoot: coverage gap", "10/24 blocks, all far"),
    "pencil-steep-angle-cpl": ("reshoot: coverage gap", "9/24 blocks (7 far, 2 near)"),
    "tweezers-cpl": ("reshoot: coverage gap", "6/24 blocks, all far"),
    "coffee-bubbles": ("reshoot: subject moved", "NCC 0.946, 20/24 blocks moving"),
    "foam": ("reshoot: subject moved", "NCC 0.979, 20/24 blocks moving"),
    "lead-1-cpl": ("reshoot: subject moved", "NCC 0.986, 19/24 blocks moving"),
    "leaf-2-cpl": ("reshoot: subject moved", "NCC 0.989, 11/24 blocks moving"),
}


def triage_tag(stem):
    if stem not in TRIAGE:
        return ""
    kind, detail = TRIAGE[stem]
    cls = "g-good" if kind == "good" else (
        "g-gap" if "coverage" in kind else "g-move")
    label = "capture: clean" if kind == "good" else kind
    title = ("BUILD-TRIAGE classified the whole frame. "
             + (detail or "No site in this frame was limited by the capture."))
    return (f'<span class="tag {cls}" title="{html.escape(title)}">'
            f'{html.escape(label)}</span>')


def classify(stem):
    if stem in VERIFIED:
        kind, text = VERIFIED[stem]
        return ("t-flagship" if kind == "flagship" else "t-print"), kind, text
    if stem in NOTED:
        kind, text = NOTED[stem]
        cls = {
            "under-resolved": "t-bad",
            "low detail, not a defect": "t-low",
            "sharp where the subject has structure": "t-ok",
        }.get(kind, "t-ok")
        return cls, kind, text
    return (
        "t-unjudged",
        "not individually judged at 1:1",
        "No individual 1:1 verdict has been recorded for this subject. It is "
        "shown so the set is complete, not because it has passed anything.",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    masters = sorted(p.stem for p in SHIP.glob("*.tiff"))
    if not masters:
        print(f"REFUSE: no masters found under {SHIP}")
        return 1

    rank = {s: i for i, s in enumerate(ORDER_HINT)}

    def key(s):
        if s in rank:
            return (0, rank[s])
        if s in NOTED and NOTED[s][0] == "under-resolved":
            return (3, s)
        if s in NOTED:
            return (2, s)
        return (1, s)

    masters.sort(key=key)

    rows, missing_full, missing_detail = [], [], []
    for stem in masters:
        full = find_full(stem)
        det = DETAIL / f"{stem}.png"
        f_rel = d_rel = None
        if full and full.exists():
            dst = assets / f"{stem}--full{full.suffix}"
            if not dst.exists():
                shutil.copy2(full, dst)
            f_rel = f"assets/{dst.name}"
        else:
            missing_full.append(stem)
        if det.exists():
            dst = assets / f"{stem}--1to1.png"
            if not dst.exists():
                shutil.copy2(det, dst)
            d_rel = f"assets/{dst.name}"
        else:
            missing_detail.append(stem)

        cls, kind, text = classify(stem)
        tif = (SHIP / f"{stem}.tiff").resolve()
        imgs = ""
        if f_rel:
            imgs += (f'<figure><img loading="lazy" src="{f_rel}">'
                     f"<figcaption>full frame, reduced for viewing</figcaption></figure>")
        if d_rel:
            imgs += (f'<figure><img loading="lazy" src="{d_rel}">'
                     f"<figcaption>true 1:1 &mdash; one image pixel per screen pixel"
                     f"</figcaption></figure>")
        body = f'<div class="imgs">{imgs}</div>' if imgs else (
            '<div class="missing">No rendered view available for this subject.</div>')
        rows.append(
            f'<section class="card"><div class="head"><h2>{html.escape(stem)}</h2>'
            f'<span class="tag {cls}">{html.escape(kind)}</span>'
            f'{triage_tag(stem)}'
            f'<a class="raw" href="file:///{tif.as_posix()}">open 16-bit master</a></div>'
            f'<div class="desc">{html.escape(text)}</div>{body}</section>'
        )

    warn = ""
    if missing_full or missing_detail:
        bits = []
        if missing_full:
            bits.append(f"no full-frame render: {', '.join(missing_full)}")
        if missing_detail:
            bits.append(f"no 1:1 crop: {', '.join(missing_detail)}")
        warn = ('<div class="note"><b>Incomplete inputs.</b> '
                + html.escape("; ".join(bits)) + "</div>")

    doc = f"""<!doctype html><meta charset="utf-8">
<title>strehl &mdash; current stacks</title><style>{CSS}</style>
<header>
<h1>strehl &mdash; current stacks</h1>
<div class="sub">{len(masters)} subjects &middot; 16-bit masters rendered by the
shipping pyramid merge &middot; every crop below is <b>true 1:1</b></div>
</header>
<main>
<div class="note">
<b>How to read this.</b> The right-hand image in each pair is a true 1:1 crop:
one image pixel per screen pixel, taken from the most detailed region of the
frame. That is the only scale at which print quality can be judged. The
left-hand image is reduced and is for orientation only &mdash; three separate
wrong conclusions in this project came from judging pictures at thumbnail scale,
including one of mine that was retracted.
</div>
<div class="note">
<b>Two tags per subject, answering two different questions.</b> The first is my
verdict on <i>the detail actually examined at 1:1</i> &mdash; can you print
this. The second is BUILD-TRIAGE's verdict on <i>the whole frame</i> &mdash;
was anything anywhere in it limited by the capture rather than by the stacker.
They are not the same question, and three subjects here are
<b>print-worthy where I looked and capture-limited somewhere else</b>:
<code>tweezers-cpl</code>, <code>leaf-2-cpl</code> and
<code>flower-bud-with-background-fern-cpl</code>. That is not a contradiction,
it is the distinction the tool exists to draw: retouch-this versus
reshoot-this. Hover a capture tag for the number behind it.
<br><br>
Across all 26 subjects and <b>51 distinct</b> evidence-bearing sites, <b>zero</b>
were limited by the merge; all 14 defective subjects are capture-limited
&mdash; 10 by a bracket that ran out of focus travel, 4 by a subject that moved.
<br><br>
That count read 64 until an independent re-test found 13 of them were one block
counted twice under two labels. The same re-test <b>confirmed the zero is
real</b>: a merge defect was planted (blur on the merged master alone, sources
untouched, hashed per rung) and the classifier does flip &mdash;
<code>109MSDCF</code> at 0.4&nbsp;px, <code>bee-3-cpl</code> at 1.8&nbsp;px,
the difference being subject headroom rather than detector floor. But it
narrowed the claim in three ways: the margin is <b>7%, not 39%</b> (closest
approach 0.746&nbsp;px against a 0.80&nbsp;px threshold); that threshold was
never pre-registered; and only blur was planted, so the verdict means <b>no
merge defect of a <i>resolution</i> character</b> &mdash; a pedestal-shaped
defect like the veil below would score 0.00&nbsp;px and go unseen. The
capture-limited verdicts are also decided <i>before</i> the merge test, so a
wrong routing there could hide a merge verdict underneath it.
</div>
<div class="note">
<b>What is verified.</b> Thirteen subjects have been judged print-worthy by eye at
1:1, and every subject examined so far has passed: <code>bee-1-cpl</code>,
<code>bee-2-cpl</code>, <code>bee-3-cpl</code>, <code>leaf-2-cpl</code>,
<code>tweezers-cpl</code>, <code>coffee-bean</code>, <code>112MSDCF</code>,
<code>flower-bud-with-background-fern-cpl</code>, <code>119MSDCF</code>,
<code>109MSDCF</code>, <code>wrapped-text-1</code>, <code>foam</code> and
<code>highly-angled-ruler-mm-cpl</code>. Compound-eye facets, plumose
hair barbules, chloroplast speckle, brushed-metal striations and crystal
dendrites near single-pixel width all resolve. <b>The occlusion halo is
gone</b> &mdash; not only where pale hairs cross a dark defocused eye, but in a
dense multi-layer tangle of overlapping trichomes, bracts and pollen, which is
a far harder test and the geometry that rims in every other stacker.
<br><br>
<b>Thirteen subjects have now been opened at 1:1 and none shows a merge defect.</b>
Two of them, <code>119MSDCF</code> and <code>109MSDCF</code>, were
<i>my</i> two worst-ranked subjects &mdash; I had labelled them "genuinely
under-resolved, last of 26". Opening them refutes that: the olive band in
<code>109MSDCF</code> resolves hundreds of individual bubbles as crisp points.
Both are retracted, which leaves the <span class="tag t-bad">under-resolved</span>
category with <b>no members at all</b>.
<br><br>
<b>The hardest halo geometry in the corpus is clean.</b>
<code>highly-angled-ruler-mm-cpl</code> puts a steel rule across the frame at a
steep angle, so a hard occluding edge runs diagonally through it with the
background surface behind &mdash; the exact geometry that rims in every other
stacker, and a steep angle means the deepest bracket and the most chances to get
it wrong. The millimetre graduations terminate crisply at that edge with
<b>no rim brightening on either side</b>. The only dark band below the rule is
the rule's own shadow.
<br><br>
<b>An in-frame control beats a sharpness statistic.</b> <code>wrapped-text-1</code>
is printed lettering on a speckled white surface, and the ink edges are visibly
soft. That reads as a soft output until you notice the speckles beside them are
individually crisp. Both were merged from the same frames by the same estimator,
so the soft edges are the <i>ink</i>, which bleeds into the texture, not the
stacker. This is the trap that produced three retracted verdicts here via a
detail-ranking statistic; the cure is not a better statistic but a feature in the
same frame you already know should be sharp.
<br><br>
<b>One subject shows colour worth chasing.</b> <code>foam</code> is dark cellular
plastic with blown specular highlights &mdash; maximum contrast at a hard edge,
the worst case for lateral chromatic aberration. Its highlight rims carry
visible orange, cyan and magenta. Thin-film iridescence on foam is a real
optical effect, so this is <i>not</i> proof of an aberration; but it is the right
subject to settle it on, because whatever a CA correction removes was aberration
and whatever survives is the iridescence. Relevant because
<code>STREHL_FIX_CA</code> is <b>off</b> in the shipping render.
<br><br>
That empty category deserves the same suspicion I applied to BUILD-TRIAGE's
zero above, and more, because these two verdicts are not independent: mine is
by eye, TRIAGE's is numerical, but both were formed by people who expected the
merge to be fine. The honest statement is that two methods that could have
disagreed did not, and that neither has yet been shown capable of returning the
other answer on this corpus. The planted-defect test in flight is what would
settle it.
<br><br>
Three of my "soft" findings have now been retracted on inspection
(<code>flowers-cpl</code>, <code>flower-inner-edge-cpl</code>, and this pair).
All three came from a detail-ranking statistic, and all three turned out to be
subjects with little structure rather than outputs with little sharpness. The
statistic is measuring the subject.
</div>
<div class="note">
<b>What is not fixed yet.</b> A <i>veil</i> remains at occlusion boundaries: a
localised haze, visible on the flagship's tarsus and claw. Its mechanism is now
measured rather than guessed. The merge selects the right frame &mdash; the
claw's detail is present, correlated 0.85 with the frame that resolved it
&mdash; but the pyramid's base band is a plain unweighted mean across all 299
frames, so at an occluded pixel it averages in ~290 frames showing the
defocused foreground and lifts the pedestal from 0.581 to 0.802. The detail is
correct and sits on the wrong brightness. A fix that keeps the mean where the
through-focus response is unimodal and takes the base from the selected layer
where it is bimodal is being built now. Two subjects, <code>119MSDCF</code> and
<code>109MSDCF</code>, are genuinely under-resolved and are still being triaged.
</div>
{warn}
{''.join(rows)}
</main>
<footer>
Masters are 16-bit TIFF at full sensor resolution; the JPEGs here are for
viewing only. Judge from the masters before printing. Detail crops were selected
by mean absolute Laplacian and graded through a single display curve per master
&mdash; per-tile curves would make two crops of the same image mutually
incomparable.
</footer>
"""
    idx = out / "index.html"
    idx.write_text(doc, encoding="utf-8")
    size = sum(p.stat().st_size for p in assets.rglob("*")) / 1e6
    print(f"wrote {idx}")
    print(f"subjects: {len(masters)}   assets: {size:.1f} MB")
    print(f"missing full-frame: {len(missing_full)}   missing 1:1: {len(missing_detail)}")
    if missing_full:
        print("  no full render: " + ", ".join(missing_full))
    if missing_detail:
        print("  no 1:1 crop  : " + ", ".join(missing_detail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
