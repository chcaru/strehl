"""Assemble the Setup page mockups into one self-contained HTML file.

    python build.py            -> outputs/setup-page-mockups.html

The screens are partials in src/screens, in the format of the Strehl Studio 2 mockups
(experiments/desktop-studio-2026-11-20/mockups): a JSON "meta" comment, then "lede", "body"
and "notes". This script borrows that folder's shell, styles, script and icons unchanged,
adds src/setup.css, puts the Setup station into the top bar, and replaces every
`<!--@plate:NAME-->` with the SVG plates.py draws from ../plates/NAME.json (the measured
points of 2026-11-27). One picture is the owner's (the calibration slide, outputs/assets,
not committed); without it the build draws a placeholder.
"""
import base64
import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parents[1] / "desktop-studio-2026-11-20" / "mockups"
OUT = HERE / "outputs" / "setup-page-mockups.html"
ORDER = ["first", "not-dark", "dark", "bright", "levels", "scale", "motion", "summary"]
ASSETS = HERE / "outputs" / "assets"
OWN = ["setup-slide"]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def own_images():
    rules, missing = [], 0
    for name in OWN:
        path = ASSETS / f"{name}.jpg"
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            rules.append(f".im-{name}{{background-image:url(data:image/jpeg;base64,{data})}}")
        else:
            missing += 1
            rules.append(f".im-{name}{{background-image:linear-gradient(135deg,hsl(210 14% 17%),hsl(240 16% 7%))}}")
    return "\n".join(rules), missing


def with_setup_station(html, meta):
    """The studio shell draws five stations. Setup is the sixth: after a rule, no numeral."""
    mark = {"ok": "ok", "part": "run", "none": "idle"}[meta.get("setup", "part")]
    station = f'<span class="rule"></span><div class="st on setup">Setup<i class="gl {mark}"></i></div>'
    head, sep, tail = html.partition('<div class="right">')
    cut = head.rfind("</div>")           # the stations block closes just before the right-hand group
    return head[:cut] + station + head[cut:] + sep + tail


def main():
    studio = module("studio_build", STUDIO / "build.py")
    plates = module("plates", HERE / "plates.py")
    src = STUDIO / "src"
    nav, sections = [], []
    for name in ORDER:
        meta, parts = studio.parse(HERE / "src" / "screens" / f"{name}.html")
        parts["body"] = re.sub(r"<!--@plate:([a-z-]+)-->", lambda m: plates.PLATES[m.group(1)](), parts["body"])
        nav.append(f'<button data-go="{meta["id"]}">{meta["nav"]}</button>')
        sections.append(with_setup_station(studio.screen(meta, parts), meta))
    css, missing = studio.images_css()
    own, own_missing = own_images()
    styles = "".join(path.read_text(encoding="utf-8") for path in
                     (src / "base.css", src / "screens.css", HERE / "src" / "setup.css"))
    page = (src / "index.html").read_text(encoding="utf-8")
    page = (page.replace("Strehl Studio 2 · design mockups", "Strehl · Setup · mockups")
            .replace("<h1>Strehl Studio 2<small>mockups · iteration 2</small></h1>",
                     "<h1>Setup<small>mockups · 2026-11-27</small></h1>")
            .replace("/*@css*/", styles)
            .replace("/*@images*/", css + "\n" + own)
            .replace("<!--@icons-->", (src / "icons.svg").read_text(encoding="utf-8"))
            .replace("<!--@nav-->", "".join(nav))
            .replace("<!--@screens-->", "\n".join(sections))
            .replace("/*@data*/", "window.SD = null;")
            .replace("/*@js*/", (src / "app.js").read_text(encoding="utf-8")))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8", newline="\n")
    print(OUT, OUT.stat().st_size, "bytes;", len(sections), "screens;", missing + own_missing, "images replaced by placeholders")


if __name__ == "__main__":
    main()
