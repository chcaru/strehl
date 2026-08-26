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
        "under-resolved",
        "Genuinely under-resolved -- last of 26 on both raw and "
        "contrast-normalised detail. Under triage: capture limit or merge "
        "defect is not yet settled.",
    ),
    "109MSDCF": (
        "under-resolved",
        "Genuinely under-resolved -- 22nd raw, 25th normalised. Under triage.",
    ),
}

ORDER_HINT = ["bee-3-cpl", "bee-1-cpl", "leaf-2-cpl", "112MSDCF"]

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


def classify(stem):
    if stem in VERIFIED:
        kind, text = VERIFIED[stem]
        return ("t-flagship" if kind == "flagship" else "t-print"), kind, text
    if stem in NOTED:
        kind, text = NOTED[stem]
        cls = {
            "under-resolved": "t-bad",
            "low detail, not a defect": "t-low",
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
<b>What is verified.</b> Four subjects have been judged print-worthy by eye at
1:1: <code>bee-1-cpl</code>, <code>bee-3-cpl</code>, <code>leaf-2-cpl</code>,
<code>112MSDCF</code>. Compound-eye facets, plumose hair barbules, chloroplast
speckle and crystal dendrites near single-pixel width all resolve. <b>The
occlusion halo is gone</b>, including where pale hairs cross a dark defocused
eye &mdash; the geometry that rims in every other stacker.
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
