"""Build a single browsable HTML index over the ORCH-GALLERY previews and crops.

The masters are 190 MB 16-bit TIFFs that no ordinary viewer opens comfortably,
and the gallery is two flat directories of JPEGs with different filename shapes
(previews are `<subject>.jpg`, crops are `<subject>@<x>_<y>.jpg`). This writes
one self-contained index.html that pairs them, so the whole corpus can be
skimmed and any subject opened at 1:1 in two clicks.

Pure presentation. It reads the gallery and writes one file; it renders nothing
and measures nothing, so it cannot change any result.
"""
import html
import io
import os
import re
import sys

GALLERY = r"D:\strehl-out\ORCH-GALLERY"
PREVIEW = os.path.join(GALLERY, "preview")
CROP = os.path.join(GALLERY, "crop-100pct")
MASTERS = r"C:\dev\strehl-out\DELIVER-V6\masters"
OUT = os.path.join(GALLERY, "index.html")

# 1:1 eye verdicts recorded by the orchestrator. Anything not listed here has
# not been given a verdict, and says so rather than defaulting to clean.
NOTES = {
    "maldon-sea-salt-cpl": ("clean", "crystal facets and micro-fractures resolved"),
    "duck-tape-side-layers-cpl": ("clean", "scrim filaments and loose fibres, no halo at any fibre boundary"),
    "dime-flat-narrow-slices-cpl": ("clean", "micro-scratches and verdigris; bright relief edges are specular metal, not a rim"),
    "medication-pill-cpl": ("clean", "powder grains on a near-white tablet, the focus measure's hardest case"),
    "pottery-art-glazed-cpl": ("clean", "bubbles inside translucent glaze; soft swirls behind them are depth the bracket did not cover (unattributed)"),
    "unpopped-popcorn-kernels-cpl": ("mostly", "softer on the falling-away left shoulder (unattributed)"),
    "chia-seeds-cpl": ("watch", "mild veiling haze in the deep inter-seed crevices - the occlusion signature to instrument first"),
}

CSS = """
body{background:#141414;color:#ddd;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:24px}
h1{font-size:20px;font-weight:600;margin:0 0 4px}
.sub{color:#888;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:20px}
.card{background:#1e1e1e;border:1px solid #2c2c2c;border-radius:8px;overflow:hidden}
.card img{width:100%;display:block;background:#000}
.meta{padding:10px 12px}
.name{font-weight:600;font-size:13px;word-break:break-all}
.info{color:#888;font-size:12px;margin-top:3px}
.note{font-size:12px;margin-top:6px;line-height:1.4}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:10px;margin-right:6px;vertical-align:1px}
.clean{background:#1d3a24;color:#7ddc94}
.mostly{background:#3a3320;color:#dfc27d}
.watch{background:#3d2a1c;color:#e8a76a}
.none{background:#2c2c2c;color:#999}
a{color:#7fb2e5;text-decoration:none}a:hover{text-decoration:underline}
.links{margin-top:8px;font-size:12px}
"""


def main() -> int:
    if not os.path.isdir(PREVIEW):
        raise SystemExit("FATAL: no preview dir at %s" % PREVIEW)

    previews = {}
    for f in os.listdir(PREVIEW):
        if f.lower().endswith(".jpg"):
            previews[os.path.splitext(f)[0]] = f

    crops = {}
    for f in os.listdir(CROP) if os.path.isdir(CROP) else []:
        if f.lower().endswith(".jpg"):
            m = re.match(r"^(.*)@(\d+)_(\d+)\.jpg$", f)
            if m:
                crops[m.group(1)] = (f, int(m.group(2)), int(m.group(3)))

    if not previews:
        raise SystemExit("FATAL: found 0 previews -- refusing to write an empty index")

    cards = []
    for name in sorted(previews):
        crop = crops.get(name)
        mp = os.path.join(MASTERS, name + ".tiff")
        size = os.path.getsize(mp) if os.path.exists(mp) else 0

        kind, text = NOTES.get(name, ("none", "not given a 1:1 verdict"))
        tag = {"clean": "clean", "mostly": "mostly clean", "watch": "watch", "none": "unrated"}[kind]

        links = ['<a href="preview/%s">full preview</a>' % html.escape(previews[name])]
        if crop:
            links.append('<a href="crop-100pct/%s">1:1 crop @%d,%d</a>' % (html.escape(crop[0]), crop[1], crop[2]))

        cards.append(
            '<div class="card">'
            '<a href="preview/{pv}"><img src="preview/{pv}" loading="lazy" alt="{nm}"></a>'
            '<div class="meta">'
            '<div class="name">{nm}</div>'
            '<div class="info">{mb}</div>'
            '<div class="note"><span class="tag {kd}">{tg}</span>{tx}</div>'
            '<div class="links">{lk}</div>'
            "</div></div>".format(
                pv=html.escape(previews[name]),
                nm=html.escape(name),
                mb=("master %.0f MB" % (size / 1048576.0)) if size else "master missing",
                kd=kind,
                tg=tag,
                tx=html.escape(text),
                lk=" &middot; ".join(links),
            )
        )

    doc = (
        "<!doctype html><meta charset=utf-8><title>strehl - all subjects</title>"
        "<style>%s</style>"
        "<h1>strehl &mdash; %d subjects</h1>"
        '<div class="sub">Rendered by the shipping binary with <code>--srgb</code>. '
        "Previews are 2400 px; crops are 1200 px at true 1:1 with no resampling and no stretch. "
        "Verdicts are one person&rsquo;s eye on a crop, not an instrument.</div>"
        '<div class="grid">%s</div>' % (CSS, len(cards), "".join(cards))
    )
    io.open(OUT, "w", encoding="utf-8").write(doc)

    back = io.open(OUT, encoding="utf-8").read()
    if len(back) < 1000 or back.count('class="card"') != len(cards):
        raise SystemExit("FATAL: index re-read does not contain %d cards" % len(cards))
    print("wrote %s" % OUT)
    print("  subjects: %d   with 1:1 crop: %d   rated: %d" % (len(cards), len(crops), len(NOTES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
