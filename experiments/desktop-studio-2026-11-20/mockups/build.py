"""Assemble the Strehl Studio 2 mockups into one self-contained HTML file.

    python build.py            -> outputs/strehl-studio-2-mockups.html

Screens are partials in src/screens. Each starts with a JSON "meta" comment and
has "lede", "body" and "notes" sections. This script wraps application screens in
the shared shell (top bar, stations, rig chip, job tray, command palette), inlines
the styles, script and icon sprite, and embeds the images from outputs/assets as
data URIs. Without that folder (it holds private captures and is not committed;
see make-assets.py) the build still works and draws placeholders.
"""
import base64
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
ASSETS = HERE / "outputs" / "assets"
OUT = HERE / "outputs" / "strehl-studio-2-mockups.html"
ORDER = ["overview", "today", "library", "subject", "capture-plan", "flight", "glance", "stack", "engine",
         "develop", "export", "variants", "system"]
SEPARATORS_BEFORE = {"library", "variants"}
STATIONS = [("capture", "Capture"), ("stack", "Stack"), ("develop", "Develop"), ("export", "Export")]
GLYPH = {"done": '<i class="gl ok"></i>', "warn": '<i class="gl warn"></i>', "run": '<i class="gl run"></i>',
         "todo": '<i class="gl idle"></i>', "cur": '<i class="gl none"></i>', "": '<i class="gl none"></i>'}
BRAND = ('<svg viewBox="0 0 64 64"><polygon points="8,41 32,27 56,41 32,55" fill="var(--panel)" stroke="var(--accent)" stroke-opacity=".4" stroke-width="3.5"/>'
         '<polygon points="8,32 32,18 56,32 32,46" fill="var(--panel)" stroke="var(--accent)" stroke-opacity=".7" stroke-width="3.5"/>'
         '<polygon points="8,23 32,9 56,23 32,37" fill="var(--panel)" stroke="var(--accent)" stroke-width="3.5"/>'
         '<polygon points="25,23 32,19 39,23 32,27" fill="var(--accent)"/></svg>')
IMAGE_NAMES = """hero hero-small detail-a detail-b proof-partial lens-depth lens-soft peaking
plane-06-large today-process today-capture today-edit today-metadata
lib-star-sand lib-chia lib-tweezers lib-peacock-ore lib-garnet lib-marigold lib-slide lib-jewel-weevil
lib-weevil-tan lib-scarab-green lib-elytra-brown lib-bubbles lib-chip lib-weevil-blue lib-bee lib-jewel-beetle
lib-spotted-beetle lib-weevil-orange lib-white-beetle lib-net-beetle""".split() + [f"pl-{i:02d}" for i in range(33)]


def icon(name):
    return f'<svg class="i"><use href="#i-{name}"/></svg>'


def images_css():
    rules, missing = [], 0
    for name in IMAGE_NAMES:
        path = next((p for p in (ASSETS / f"{name}.jpg", ASSETS / f"{name}.png") if p.exists()), None)
        if path is None:
            missing += 1
            hue = sum(map(ord, name)) % 360
            rules.append(f".im-{name}{{background-image:linear-gradient(135deg,hsl({hue} 18% 20%),hsl({(hue + 50) % 360} 20% 8%))}}")
            continue
        mime = "image/png" if path.suffix == ".png" else "image/jpeg"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        rules.append(f".im-{name}{{background-image:url(data:{mime};base64,{data})}}")
    return "\n".join(rules), missing


def topbar(meta):
    crumbs = ['<span data-go="library">Library</span>']
    names = meta.get("crumbs", [])
    for index, name in enumerate(names):
        cur = ' class="cur"' if index == len(names) - 1 else ""
        crumbs.append(f"<em>/</em><span{cur}>{name}</span>")
    station = meta.get("station")
    states = meta.get("states", {})
    parts = [f'<div class="st{" on" if station == "library" else ""}" data-go="library"><b>01</b>Library</div><span class="rule"></span>']
    for index, (key, label) in enumerate(STATIONS):
        on = " on" if station == key else ""
        parts.append(f'<div class="st{on}" data-go="{key}"><b>{index + 2:02d}</b>{label}{GLYPH.get(states.get(key, ""), "")}</div>')
    rig_on = meta.get("rig") == "on"
    rig = ('<div class="stat" data-pop-open="rig"><i class="gl ok"></i>A7CR<span>light 41 W</span></div>' if rig_on
           else '<div class="stat" data-pop-open="rig"><i class="gl idle"></i>Rig<span>off</span></div>')
    job = meta.get("job", "idle")
    if job == "capture":
        jobs = '<div class="stat job" style="--p:63" data-pop-open="jobs"><i class="gl run"></i>Capture<span>61 / 96 · 3:18 · +2</span></div>'
    elif job == "repair":
        jobs = '<div class="stat job" style="--p:30" data-pop-open="jobs"><i class="gl run"></i>Depth repair<span>12 s left</span></div>'
    else:
        jobs = '<div class="stat" data-pop-open="jobs"><i class="gl idle"></i><span>Nothing running</span></div>'
    return (f'<div class="top"><div class="brand">{BRAND}Strehl</div>'
            f'<div class="crumbs">{"".join(crumbs)}</div><div class="stations">{"".join(parts)}</div>'
            f'<div class="right">{rig}{jobs}<div class="stat" data-pop-open="palette">{icon("search")}<span class="kbd">Ctrl K</span></div>'
            '<div class="wctl"><span><svg viewBox="0 0 10 10"><path d="M1 5.5h8"/></svg></span>'
            '<span><svg viewBox="0 0 10 10"><path d="M1.5 1.5h7v7h-7z"/></svg></span>'
            '<span><svg viewBox="0 0 10 10"><path d="M1.5 1.5l7 7M8.5 1.5l-7 7"/></svg></span></div></div></div>')


def overlays(meta):
    job = meta.get("job", "idle")
    rig_on = meta.get("rig") == "on"
    if job == "capture":
        running = ('<div class="job"><i class="gl run"></i><b>Capture · Blue weevil, dorsal</b><span class="x">PAUSE · STOP</span>'
                   '<small>Plane 61 of 96 · 3 min 18 s left · ends 21:47</small><div class="bar ok"><i style="width:63%"></i></div></div>'
                   '<div class="job"><i class="gl run"></i><b>Checks</b><span class="dim2">keeping up</span>'
                   '<small>60 planes checked as they arrived · 1 retaken</small></div>'
                   '<div class="hd"><span class="cap">Waiting · 2</span><span class="sp"></span><span class="dim2" style="font-size:12px">start when the capture ends</span></div>'
                   '<div class="job"><span class="dim2">1</span><b>Stack · Blue weevil, dorsal, second pass</b><span class="x">REMOVE</span><small>about 25 s · measurements already cached by the checks</small></div>'
                   '<div class="job"><span class="dim2">2</span><b>Stack · Bumblebee, frontal</b><span class="x">REMOVE</span><small>183 planes · about 1 min</small></div>')
    elif job == "repair":
        running = ('<div class="job"><i class="gl run"></i><b>Depth repair · Leg joint</b><span class="x">STOP</span>'
                   '<small>Rebuilding one area of render 3 · 12 s left</small><div class="bar"><i style="width:30%"></i></div></div>')
    else:
        running = '<div class="job"><i class="gl idle"></i><b>Nothing running</b><span></span><small>Queue a stack from any subject, or start a capture</small></div>'
    jobs = ('<div class="pop jobs" data-pop="jobs" style="right:126px;top:43px;width:430px">'
            f'<div class="hd"><h5>Activity</h5><span class="sp"></span>{icon("moon")}<span class="dim" style="font-size:12px">Quiet</span><span class="toggle"></span></div>'
            f'{running}'
            '<div class="hd"><span class="cap">Earlier today</span><span class="sp"></span><button class="link">Full log</button></div>'
            '<div class="job"><i class="gl ok"></i><b>Calibrate step</b><span class="dim2">21:33</span><small>Step 7 suggested · four-shot mode restored · took 68 s</small></div>'
            '<div class="job"><i class="gl ok"></i><b>Export · 2 files</b><button class="link">Reveal</button><small>weevil-dorsal-web.jpg, weevil-dorsal-hdr.avif</small></div>'
            f'<div class="job">{icon("moon")}<b>Quiet holds heavy work</b><span></span>'
            '<small>Stacks, repairs and compaction wait while a full-screen program is in front. Captures and transfers never wait.</small></div></div>')
    cam = "On · ILCE-7CR · USB 5 Gbit/s" if rig_on else "Off"
    light = "On · 41 W · warm" if rig_on else "Off · 0 W"
    rig = ('<div class="pop rig" data-pop="rig" style="right:330px;top:43px;width:390px">'
           f'<div class="hd"><h5>Rig</h5><span class="sp"></span><span class="chip {"ok" if rig_on else "idle"}">{"Ready" if rig_on else "Off"}</span></div>'
           f'<div class="job">{icon("camera")}<b>Camera</b><button class="btn sm">{"Shut down" if rig_on else "Power on"}</button><small>{cam}</small></div>'
           f'<div class="job">{icon("bulb")}<b>Light</b><button class="btn sm">{"Off" if rig_on else "On"}</button><small>{light}</small></div>'
           f'<div class="job">{icon("power")}<b>Power for a stack</b><span class="toggle on"></span><small>Wake both at the start; switch both off when the files are saved</small></div>'
           f'<div class="job">{icon("wifi")}<b>Camera host</b><span class="chip ok">online</span><small>Answers in 12 ms · controller up to date</small></div>'
           f'<div class="job">{icon("disk")}<b>Receiver on this PC</b><span class="chip ok">ready</span><small>D:\\StrehlCaptures · 371 GB free · last transfer 38 MB/s</small></div>'
           f'<div class="job">{icon("phone")}<b>Phone remote</b><button class="btn sm">Show code</button><small>Follow a capture and get told when it needs you</small></div></div>')
    palette = ('<div class="pop palette" data-pop="palette"><div class="q">' + icon("search") + '<b>ext</b><span>end the stack…</span></div>'
               '<div class="grp cap">Actions</div>'
               '<div class="it on">' + icon("camera") + 'Extend this stack beyond its far end…<span class="kbd">Enter</span></div>'
               '<div class="it">' + icon("export") + 'Export again as last time<span class="kbd">Ctrl Shift E</span></div>'
               '<div class="it">' + icon("bulb") + 'Turn the light off</div>'
               '<div class="it">' + icon("eye") + 'Lens: Depth<span class="kbd">3</span></div>'
               '<div class="grp cap">Go to</div>'
               '<div class="it">' + icon("library") + 'Blue weevil / Wing case, close · 5.6×</div>'
               '<div class="it">' + icon("library") + 'Net-patterned beetle<span class="chip warn" style="margin-left:auto">1 to check</span></div></div>')
    return '<div class="scrim"></div>' + jobs + rig + palette


def parse(path):
    text = path.read_text(encoding="utf-8")
    meta = json.loads(re.search(r"<!--meta (.*?) -->", text, re.S).group(1))
    parts = {"lede": "", "body": "", "notes": ""}
    marks = list(re.finditer(r"<!--(lede|body|notes)-->", text))
    for index, mark in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else len(text)
        parts[mark.group(1)] = text[mark.end():end].strip()
    return meta, parts


def screen(meta, parts):
    kind = meta["kind"]
    if kind == "page":
        return f'<section class="screen" id="s-{meta["id"]}">{parts["body"]}</section>'
    head = f'<div class="screen-head"><h2>{meta["title"]}</h2><p>{parts["lede"]}</p></div>'
    if kind == "bare":
        stage = parts["body"]
    else:
        body, _, rest = parts["body"].partition('<div class="hint">')
        hint, _, pins = rest.partition("</div>")  # the hint holds spans only: its first close is its own
        stage = (f'<div class="app">{topbar(meta)}{body}<div class="hint">{hint}</div>'
                 f'{overlays(meta)}{pins}</div>')
    notes = f'<div class="notes">{parts["notes"]}</div>' if parts["notes"] else ""
    return (f'<section class="screen" id="s-{meta["id"]}">{head}<div class="stage-wrap"><div class="stage">{stage}</div></div>'
            f'{notes}</section>')


def main():
    nav, sections = [], []
    for name in ORDER:
        meta, parts = parse(SRC / "screens" / f"{name}.html")
        if name in SEPARATORS_BEFORE:
            nav.append('<span class="sep"></span>')
        nav.append(f'<button data-go="{meta["id"]}">{meta["nav"]}</button>')
        sections.append(screen(meta, parts))
    css, missing = images_css()
    data = (ASSETS / "data.json").read_text(encoding="utf-8") if (ASSETS / "data.json").exists() else "null"
    page = (SRC / "index.html").read_text(encoding="utf-8")
    page = (page.replace("/*@css*/", (SRC / "base.css").read_text(encoding="utf-8") + (SRC / "screens.css").read_text(encoding="utf-8"))
            .replace("/*@images*/", css)
            .replace("<!--@icons-->", (SRC / "icons.svg").read_text(encoding="utf-8"))
            .replace("<!--@nav-->", "".join(nav))
            .replace("<!--@screens-->", "\n".join(sections))
            .replace("/*@data*/", f"window.SD = {data};")
            .replace("/*@js*/", (SRC / "app.js").read_text(encoding="utf-8")))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8", newline="\n")
    print(OUT, OUT.stat().st_size, "bytes;", len(sections), "screens;", missing, "images replaced by placeholders")


if __name__ == "__main__":
    main()
