"""Assemble the capture planning flow mockups into one self-contained HTML file.

    python build.py            -> outputs/capture-planning-flow-mockups.html

The screens are partials in src/screens, in the format of the Strehl Studio 2 mockups
(experiments/desktop-studio-2026-11-20/mockups): a JSON "meta" comment, then "lede", "body"
and "notes". This script borrows that folder's shell, styles, script and icons unchanged, and
adds src/flow.css and src/flow.js for the parts this proposal adds. Pictures come from the
Studio 2 mockups' outputs/assets (private captures, not committed); without them the build
still works and draws placeholders.
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parents[1] / "desktop-studio-2026-11-20" / "mockups"
OUT = HERE / "outputs" / "capture-planning-flow-mockups.html"
ORDER = ["ready", "calibrating", "depth", "here", "cover", "light"]
ASSETS = HERE / "outputs" / "assets"
OWN = ["cpf-live", "cpf-depth-sweep", "cpf-depth", "cpf-depth-at", "cpf-cover", "cpf-glints",
       "cpf-core-a", "cpf-core-b", "cpf-core-c"]


def studio_build():
    spec = importlib.util.spec_from_file_location("studio_build", STUDIO / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def own_images():
    """This folder's pictures (assets.py), embedded as the Studio 2 build embeds its own."""
    import base64
    rules, missing = [], 0
    for name in OWN:
        path = ASSETS / f"{name}.jpg"
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            rules.append(f".im-{name}{{background-image:url(data:image/jpeg;base64,{data})}}")
        else:
            missing += 1
            rules.append(f".im-{name}{{background-image:linear-gradient(135deg,hsl(200 18% 20%),hsl(250 20% 8%))}}")
    return "\n".join(rules), missing


def main():
    studio = studio_build()
    src = STUDIO / "src"
    nav, sections = [], []
    for name in ORDER:
        meta, parts = studio.parse(HERE / "src" / "screens" / f"{name}.html")
        nav.append(f'<button data-go="{meta["id"]}">{meta["nav"]}</button>')
        sections.append(studio.screen(meta, parts))
    css, missing = studio.images_css()
    own, own_missing = own_images()
    css, missing = css + "\n" + own, missing + own_missing
    rail = ASSETS / "rail.json"
    measured = rail.read_text(encoding="utf-8") if rail.exists() else "null"
    styles = "".join((path.read_text(encoding="utf-8") for path in
                      (src / "base.css", src / "screens.css", HERE / "src" / "flow.css")))
    script = ((src / "app.js").read_text(encoding="utf-8") + "\nwindow.CPF = " + measured + ";\n"
              + (HERE / "src" / "flow.js").read_text(encoding="utf-8"))
    page = (src / "index.html").read_text(encoding="utf-8")
    page = (page.replace("Strehl Studio 2 · design mockups", "Strehl · capture calibration · mockups")
            .replace("<h1>Strehl Studio 2<small>mockups · iteration 2</small></h1>",
                     "<h1>Capture calibration<small>mockups · 2026-11-27</small></h1>")
            .replace("/*@css*/", styles)
            .replace("/*@images*/", css)
            .replace("<!--@icons-->", (src / "icons.svg").read_text(encoding="utf-8"))
            .replace("<!--@nav-->", "".join(nav))
            .replace("<!--@screens-->", "\n".join(sections))
            .replace("/*@data*/", "window.SD = null;")
            .replace("/*@js*/", script))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8", newline="\n")
    print(OUT, OUT.stat().st_size, "bytes;", len(sections), "screens;", missing, "images replaced by placeholders")


if __name__ == "__main__":
    main()
