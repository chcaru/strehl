#!/usr/bin/env python3
"""Draw candidate Strehl application marks and a contact sheet to compare them.

    python build.py            (needs Edge or Chrome for the sheet image)

    python build.py 1          (an earlier round; the default is the latest)

Writes outputs/round-N/NAME-tile-dark.svg, NAME-tile-light.svg, NAME-mark-dark.svg and
NAME-mark-light.svg for every candidate, with sheet.html and sheet.png beside them.
All geometry lives here, on a 256 unit canvas. Only the standard library is used.
The drawings are original work, MIT OR Apache-2.0 like Strehl.
"""
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            "/usr/bin/google-chrome", "/usr/bin/chromium"]

# Studio 2 tokens: Graphite panel, line2, ink and accent; Lightbox the same roles.
DARK = {"tone": "dark", "bg": "#111112", "edge": "#37373c", "ink": "#e9e6de", "gold": "#e6b450",
        "rust": "#cc5a33",
        "ramp": ["#f1e4c6", "#ecc878", "#e6b450", "#e0893e", "#cc5a33", "#a23f2c", "#74372a"]}
LIGHT = {"tone": "light", "bg": "#f3f2ee", "edge": "#b9b5ab", "ink": "#19191b", "gold": "#a46300",
         "rust": "#b04a24",
         "ramp": ["#e2a93f", "#d98a2b", "#c96a26", "#b04a24", "#8a3722", "#5c2a1e", "#19191b"]}


def n(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


def tag(name, **attrs):
    parts = []
    for key, value in attrs.items():
        if value is None:
            continue
        text = n(value) if isinstance(value, float) else value
        parts.append(f"{key.replace(chr(95), chr(45))}=\"{text}\"")
    return f"<{name} {' '.join(parts)}/>"


def line(x1, y1, x2, y2, color, width, opacity=None, cap=None):
    return tag("line", x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2), stroke=color,
               stroke_width=float(width), stroke_opacity=opacity, stroke_linecap=cap)


def box(x, y, w, h, color, opacity=None):
    return tag("rect", x=float(x), y=float(y), width=float(w), height=float(h), fill=color, fill_opacity=opacity)


def disc(cx, cy, r, color, opacity=None):
    return tag("circle", cx=float(cx), cy=float(cy), r=float(r), fill=color, fill_opacity=opacity)


def ring(cx, cy, r, color, width, opacity=None):
    return tag("circle", cx=float(cx), cy=float(cy), r=float(r), fill="none", stroke=color,
               stroke_width=float(width), stroke_opacity=opacity)


def path(d, color, width, opacity=None, fill="none", fill_opacity=None, join="miter", cap=None):
    return tag("path", d=d, fill=fill, fill_opacity=fill_opacity, stroke=color, stroke_width=float(width),
               stroke_opacity=opacity, stroke_linejoin=join, stroke_linecap=cap, stroke_miterlimit=10)


def frame(cx, cy, half, color, width, opacity=None, fill="none"):
    return tag("rect", x=float(cx - half), y=float(cy - half), width=float(2 * half), height=float(2 * half),
               fill=fill, stroke=color, stroke_width=float(width), stroke_opacity=opacity)


def bessel_j1(x, steps=600):
    return sum(math.cos(t - x * math.sin(t)) for t in ((i + 0.5) * math.pi / steps for i in range(steps))) / steps


def airy_amplitude(x):
    return 1.0 if abs(x) < 1e-6 else abs(2.0 * bessel_j1(x) / x)


# The candidates. Each returns the mark only; the tile is added around it.

def trace(points):
    return "M" + " L".join(f"{n(x)},{n(y)}" for x, y in points)


def airy(p):
    """The Airy pattern: what a perfect lens makes of a point. A bright core and fading rings."""
    g = p["gold"]
    # Core to three quarters of the first zero; rings at the first two bright maxima.
    return disc(128, 128, 29, g) + ring(128, 128, 52, g, 7, 0.66) + ring(128, 128, 85, g, 4.5, 0.36)


def graticule(p):
    """The same point seen through an instrument: a ruled dial around it and one index mark."""
    i, g = p["ink"], p["gold"]
    out = disc(128, 128, 22, g) + ring(128, 128, 41, g, 6, 0.62)
    for k in range(1, 60):
        a = math.radians(k * 6 - 90)
        major = k % 5 == 0
        r1 = 72 if major else 80
        out += line(128 + r1 * math.cos(a), 128 + r1 * math.sin(a), 128 + 92 * math.cos(a), 128 + 92 * math.sin(a),
                    i, 3.5 if major else 2.5, 0.85 if major else 0.45)
    return out + line(128, 30, 128, 62, g, 6)


def ratio(p):
    """The Strehl ratio drawn: the peak you measured, in gold, against the perfect one behind it."""
    i, g = p["ink"], p["gold"]
    base, tall = 186.0, 138.0
    ideal, real = [], []
    for k in range(185):
        x = 36.0 + k
        t = (x - 128) / 22.0 * 3.8317
        ideal.append((x, base - tall * airy_amplitude(t) ** 2))
        wide = 0.56 * airy_amplitude(t / 1.45) ** 2 + 0.07 * math.exp(-(t / 9.0) ** 2)
        real.append((x, base - tall * wide))
    return path(trace(ideal), i, 3.5, 0.6, join="round") + path(trace(real), g, 7, join="round")


def sensor(p):
    """A point of light as the sensor records it, photosite by photosite."""
    i, g = p["ink"], p["gold"]
    cell, gap = 30, 5
    x0 = 128 - (5 * cell + 4 * gap) / 2
    level = {0: None, 1: 0.52, 2: 0.3, 4: 0.15, 5: 0.1, 8: 0.05}
    out = ""
    for r in range(5):
        for c in range(5):
            d = (r - 2) ** 2 + (c - 2) ** 2
            x, y = x0 + c * (cell + gap), x0 + r * (cell + gap)
            out += box(x, y, cell, cell, i, 0.07) + box(x, y, cell, cell, g, level[d])
    return out


def slices(p):
    """A solid made of planes. The plane in focus is gold and the rest fall away from it."""
    i, g = p["ink"], p["gold"]
    out = "<clipPath id=\"c\"><circle cx=\"128\" cy=\"128\" r=\"84\"/></clipPath><g clip-path=\"url(#c)\">"
    focus = 3
    for k in range(9):
        y = 128 + (k - 4) * 19
        away = abs(k - focus)
        thick = 11 - 1.55 * away
        out += box(36, y - thick / 2, 184, thick, g if away == 0 else i, None if away == 0 else 0.95 - 0.1 * away)
    return out + "</g>"


def waist(p):
    """Light closing to focus and opening again, drawn as a sweep of planes."""
    i, g = p["ink"], p["gold"]
    out = ""
    for k in range(11):
        away = abs(k - 5)
        if away == 0:
            continue
        x = 128 + (k - 5) * 16
        half = 10 + away * 14
        out += line(x, 128 - half, x, 128 + half, i, 5.5, 0.98 - 0.13 * (away - 1))
    return out + disc(128, 128, 9.5, g)


def depth(p):
    """Planes drawing closer together as they near the one in focus."""
    i, g = p["ink"], p["gold"]
    out = line(44, 128, 212, 128, g, 8)
    for k, d in enumerate((12, 25, 41, 60, 82)):
        for side in (-1, 1):
            out += line(44, 128 + side * d, 212, 128 + side * d, i, 5, 0.95 - 0.13 * k)
    return out


def square_s(p):
    """A square S in one stroke: three focal planes, the middle one in focus."""
    i, g = p["ink"], p["gold"]
    return (path("M200.5,62 H62 V128 H194 V194 H55.5", i, 13)
            + line(55.5, 128, 200.5, 128, g, 13))


def ring_s(p):
    """Airy rings cut down the middle and slipped by one ring, so they join into an S."""
    i, g = p["ink"], p["gold"]
    pitch, w = 26.0, 9.0
    out = ""
    for k, (color, opacity) in enumerate(((g, None), (i, 0.85), (i, 0.45)), start=1):
        r = (k - 0.5) * pitch
        cl, cr = 128 - pitch / 2, 128 + pitch / 2
        out += path(f"M128,{n(cl - r)} A{n(r)},{n(r)} 0 0 0 128,{n(cl + r)}", color, w, opacity)
        out += path(f"M128,{n(cr - r)} A{n(r)},{n(r)} 0 0 1 128,{n(cr + r)}", color, w, opacity)
    return out


def axis(p):
    """Looking down the optical axis through the stack, to one sharp pixel."""
    i, g = p["ink"], p["gold"]
    out = ""
    for half, width, opacity in ((88, 8, None), (61, 6.5, 0.8), (41, 5, 0.62), (26, 4, 0.46)):
        out += frame(128, 128, half, i, width, opacity)
    return out + box(118, 118, 20, 20, g)


def four_shots(p):
    """Pixel shift: four exposures a photosite apart, adding up to one true pixel."""
    g = p["gold"]
    out = ""
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        out += tag("rect", x=float(78 + sx * 18), y=float(78 + sy * 18), width=100.0, height=100.0, fill=g,
                   fill_opacity=0.13, stroke=g, stroke_width=3.0, stroke_opacity=0.5)
    return out + box(106, 106, 44, 44, g)


def planes(p):
    """Focal planes standing along the axis, the sharp one lit. The closest to the old mark."""
    i, g = p["ink"], p["gold"]
    out = ""
    for k in (5, 4, 3, 2, 1, 0):
        x = 60 + 19 * k
        d = f"M{x},88 L{x + 40},66 L{x + 40},168 L{x},190 Z"
        out += path(d, g if k == 2 else i, 4, None if k < 3 else (0.8, 0.6, 0.42)[k - 3],
                    fill=g if k == 2 else p["bg"])
    return out


ROUND_1 = [("airy", "Airy", airy), ("graticule", "Graticule", graticule), ("ratio", "Ratio", ratio),
           ("sensor", "Photosites", sensor), ("slices", "Slices", slices), ("depth", "Depth", depth),
           ("waist", "Waist", waist), ("axis", "Axis", axis), ("planes", "Planes", planes),
           ("four-shots", "Four shots", four_shots), ("square-s", "Square S", square_s),
           ("ring-s", "Ring S", ring_s)]


# Round 2. The owner picked Slices for its 1970s character: variations on it, crosses with
# the round 1 marks worth keeping, and new marks in the same register.

DISC = "<circle cx=\"128\" cy=\"128\" r=\"84\"/>"


def clipped(shape, inner, name="c"):
    return f"<clipPath id=\"{name}\">{shape}</clipPath><g clip-path=\"url(#{name})\">{inner}</g>"


def heavy_rows(p, focus=2):
    return "".join(box(36, 44.5 + 25 * k, 184, 17, p["gold"] if k == focus else p["ink"]) for k in range(7))


def bold(p):
    """Seven equal, heavy bars with tight gaps: the plain 1970s cut."""
    return clipped(DISC, heavy_rows(p))


def sunset(p):
    """Solid where it is in focus, breaking into thinner slices as it falls away. The most 1970s."""
    rows = box(36, 44, 184, 72, p["gold"])
    y = 116.0
    for k, (gap, thick) in enumerate(((6, 15), (8, 12), (10, 9), (12, 6.5), (13.5, 4))):
        y += gap
        rows += box(36, y, 184, thick, p["ramp"][min(6, 3 + k)])
        y += thick
    return clipped(DISC, rows)


def spectrum(p):
    """The heavy bars in a warm run of colour, cream down to brown."""
    return clipped(DISC, "".join(box(36, 44.5 + 25 * k, 184, 17, p["ramp"][k]) for k in range(7)))


def globe(p):
    """Slices at equal angles, so they crowd toward the poles and the disc becomes a sphere."""
    rows = ""
    for k in range(9):
        top = 128 - 84 * math.cos((k + 0.2) * math.pi / 9)
        bottom = 128 - 84 * math.cos((k + 0.8) * math.pi / 9)
        rows += box(36, top, 184, bottom - top, p["gold"] if k == 3 else p["ink"])
    return clipped(DISC, rows)


def inverse(p):
    """The disc cut into a gold tile, so it holds on a dark taskbar and a light one alike."""
    if not p["tile"]:
        bar, focus = p["gold"], p["ink"]
    elif p["tone"] == "dark":
        bar, focus = "#111112", "#fbf3e1"
    else:
        bar, focus = "#f3f2ee", "#19191b"
    return clipped(DISC, "".join(box(36, 44.5 + 25 * k, 184, 17, focus if k == 2 else bar) for k in range(7)))


inverse.ground = lambda p: (p["gold"], "#c2943c" if p["tone"] == "dark" else "#8a5300")


def circle_path(r):
    return f"M{n(128 - r)},128 a{n(r)},{n(r)} 0 1 0 {n(2 * r)},0 a{n(r)},{n(r)} 0 1 0 {n(-2 * r)},0 Z"


def airy_slices(p):
    """From Airy: the core and its first ring, both cut from the same slices."""
    rows = "".join(box(36, 123 + 16 * k, 184, 10, p["gold"]) for k in range(-5, 6))
    core = clipped("<circle cx=\"128\" cy=\"128\" r=\"41\"/>", rows, "a")
    annulus = f"<path clip-rule=\"evenodd\" d=\"{circle_path(84)} {circle_path(62)}\"/>"
    return core + "<g opacity=\"0.62\">" + clipped(annulus, rows, "b") + "</g>"


def slice_s(p):
    """From the S marks: an S found in the slices. The planes that carry the letter stay lit."""
    i, g = p["ink"], p["gold"]
    rows = ""
    for k in range(7):
        y = 44.5 + 25 * k
        if k == 3:
            rows += box(36, y, 184, 17, g)
        elif k in (0, 6):
            rows += box(36, y, 184, 17, i)
        elif k < 3:
            rows += box(36, y, 68, 17, i) + box(104, y, 116, 17, i, 0.16)
        else:
            rows += box(152, y, 68, 17, i) + box(36, y, 116, 17, i, 0.16)
    return clipped(DISC, rows)


def stripe_s(p):
    """From Ring S: three parallel stripes drawn as an S, the way 1970s lettering ran lines side by side."""
    a = math.radians(20)
    out = ""
    for ru, color in ((47.0, p["ink"]), (34.0, p["gold"]), (21.0, p["rust"])):
        rl = 68.0 - ru
        d = (f"M{n(128 + ru * math.cos(a))},{n(94 - ru * math.sin(a))} A{n(ru)},{n(ru)} 0 1 0 128,{n(94 + ru)} "
             f"A{n(rl)},{n(rl)} 0 1 1 {n(128 - rl * math.cos(a))},{n(162 + rl * math.sin(a))}")
        out += path(d, color, 9)
    return out


def halftone(p):
    """From Photosites: a point of light as a 1970s print shows it, in square dots that shrink with the light."""
    out = ""
    for r in range(-4, 5):
        for c in range(-4, 5):
            s = 17.5 * math.exp(-(math.hypot(r, c) * 20 / 62.0) ** 2)
            if s >= 2.4:
                out += box(128 + c * 20 - s / 2, 128 + r * 20 - s / 2, s, s, p["gold"])
    return out


def diamond(p):
    """New: the slices in the old mark's diamond, square-cornered like the rest of the app."""
    shape = "<path d=\"M128,40 L216,128 L128,216 L40,128 Z\"/>"
    rows = "".join(box(36, 41 + 26 * k, 184, 18, p["gold"] if k == 2 else p["ink"]) for k in range(7))
    return clipped(shape, rows)


def half_half(p):
    """From Airy: its rings above and the slices below. The optics and the stack in one disc."""
    i, g = p["ink"], p["gold"]
    rings = disc(128, 128, 26, g) + ring(128, 128, 48, g, 14) + ring(128, 128, 76, g, 16)
    upper = clipped("<rect x=\"36\" y=\"36\" width=\"184\" height=\"86\"/>", rings, "a")
    rows = "".join(box(36, 134 + 19 * k, 184, 12, i) for k in range(5))
    return upper + clipped("<path d=\"M36,134 H220 V220 H36 Z\"/>", clipped(DISC, rows, "c"), "b")


ROUND_2 = [("slices", "Slices", slices), ("bold", "Bold", bold), ("sunset", "Sunset", sunset),
           ("spectrum", "Spectrum", spectrum), ("globe", "Globe", globe), ("inverse", "Inverse", inverse),
           ("airy-slices", "Airy slices", airy_slices), ("horizon", "Horizon", half_half),
           ("slice-s", "Slice S", slice_s), ("stripe-s", "Stripe S", stripe_s), ("halftone", "Halftone", halftone),
           ("diamond", "Diamond", diamond)]

# Grounds to try the heavy disc on: name, tile, edge, bars, focus bar.
COLOURWAYS = [("Graphite", "#111112", "#37373c", "#e9e6de", "#e6b450"),
              ("Walnut", "#2a1a12", "#4a3020", "#f1e4c6", "#e0893e"),
              ("Cream", "#f1e4c6", "#d8c8a4", "#3a2318", "#c2502e"),
              ("Rust", "#b5462b", "#8e3520", "#f6ead0", "#1a1210"),
              ("Gold", "#e6b450", "#c2943c", "#111112", "#fbf3e1"),
              ("Teal plane", "#111112", "#37373c", "#e9e6de", "#55d6c4")]

# Round 3. The owner picked Sunset and Spectrum: one mark from the two, then small things a
# macro photographer would recognise.

RAMP_3 = {"dark": ["#f4e7c8", "#eecb7c", "#e6b450", "#e28f40", "#d2643a", "#b34a31", "#8c3f2e"],
          "light": ["#e2a93f", "#d98a2b", "#c96a26", "#b04a24", "#8a3722", "#5c2a1e", "#19191b"]}
# Top edge and thickness of each band: three that touch, then gaps that open as the bands thin.
DUSK = ((44, 34.5), (78, 27.5), (105, 21), (131, 16), (155, 12), (177.5, 8.5), (198.5, 5.5))


def warm(p):
    return p.get("ramp3") or RAMP_3[p["tone"]]


def mix(stops, t):
    t = min(1.0, max(0.0, t)) * (len(stops) - 1)
    k = min(len(stops) - 2, int(t))
    a, b, f = stops[k], stops[k + 1], t - k
    return "#" + "".join(f"{round(int(a[j:j + 2], 16) * (1 - f) + int(b[j:j + 2], 16) * f):02x}" for j in (1, 3, 5))


def dusk_rows(p):
    return "".join(box(36, y, 184, thick, color) for (y, thick), color in zip(DUSK, warm(p)))


def placed(inner, cx, cy, r, turn=0):
    return (f"<g transform=\"translate({n(cx)},{n(cy)}) rotate({n(turn)}) scale({r / 84:.4f}) "
            f"translate(-128,-128)\">{inner}</g>")


def knockout(inner, holes, name="m"):
    return (f"<mask id=\"{name}\"><rect width=\"256\" height=\"256\" fill=\"#fff\"/>{holes}</mask>"
            f"<g mask=\"url(#{name})\">{inner}</g>")


def dusk(p):
    """Sunset and Spectrum as one mark: the warm run of colour, solid at the top and thinning as it falls away."""
    return clipped(DISC, dusk_rows(p))


def pair_rows(p):
    rows, y, thick = "", 44.0, 27.5
    for k in range(9):
        rows += box(36, y, 184, thick, mix(warm(p), k / 8))
        y += thick * 1.55
        thick *= 0.76
    return rows


def line_pairs(p):
    """A resolution target: every line and every gap finer than the last, down to what a lens can just resolve."""
    return clipped(DISC, pair_rows(p))


def thin_plane(p):
    """Depth of field: one thin, bright plane in focus, and bands that grow heavier and darker away from it."""
    r = warm(p)
    rows = box(36, 105.5, 184, 5, r[0])
    for side in (-1, 1):
        edge = 108 + side * 2.5
        for k, thick in enumerate((10, 15, 20, 26, 30), start=1):
            edge += side * 5
            rows += box(36, edge if side > 0 else edge - thick, 184, thick, r[min(6, k)])
            edge += side * thick
    return clipped(DISC, rows)


def dewdrop(p):
    """A dewdrop on the stack. A drop is a small lens, so it holds the whole picture upside down."""
    cx, cy, r = 158.0, 166.0, 27.0
    small = placed(clipped(DISC, dusk_rows(p), "d"), cx, cy, r, 180)
    return knockout(clipped(DISC, dusk_rows(p)), disc(cx, cy, r + 6, "#000")) + small


def loupe(p):
    """Magnification: a lens laid over the fine lines, where it draws them large enough to count."""
    cx, cy, r, zoom = 146.0, 172.0, 30.0, 2.0
    big = (f"<g transform=\"translate({n(cx)},{n(cy)}) scale({n(zoom)}) translate({n(-cx)},{n(-cy)})\">"
           + clipped(DISC, pair_rows(p), "e") + "</g>")
    lens = clipped(tag("circle", cx=cx, cy=cy, r=r), big, "d")
    return knockout(clipped(DISC, pair_rows(p)), disc(cx, cy, r + 6, "#000")) + lens


def rail(p):
    """The focus rail: a ruled scale beside the stack, with its index where the picture is sharp."""
    out = placed(clipped(DISC, dusk_rows(p)), 146, 128, 76)
    for k in range(-12, 13):
        y = 126.0 + 6 * k
        if k == 0:
            out += line(26, y, 54, y, p["gold"], 5)
        else:
            out += line(26, y, 44 if k % 4 == 0 else 36, y, p["ink"], 2.5, 0.85 if k % 4 == 0 else 0.5)
    return out


def scale_bar(p):
    """The scale bar from a micrograph, set under the stack the way it sits in the corner of the picture."""
    return placed(clipped(DISC, dusk_rows(p)), 128, 112, 76) + path("M148,212 V222 H204 V212", p["ink"], 4)


def relief(p):
    """The depth map: every slice lifts where the subject stands, so the stack draws its shape."""
    def lift(x, y):
        d = ((x - 128) ** 2 + (y - 136) ** 2) / 54.0 ** 2
        return 22 * (1 - d) ** 2 if d < 1 else 0.0
    rows = ""
    xs = [36 + 2 * m for m in range(93)]
    for k in range(7):
        top, bottom = 44.5 + 25 * k, 61.5 + 25 * k
        pts = [(x, top - lift(x, top)) for x in xs] + [(x, bottom - lift(x, bottom)) for x in reversed(xs)]
        rows += tag("path", d=trace(pts) + " Z", fill=warm(p)[k])
    return clipped(DISC, rows)


def tilt(p):
    """The plane of focus laid at an angle, the way a tilted lens runs it along the subject."""
    return clipped(DISC, "<g transform=\"rotate(-18 128 128)\">" + dusk_rows(p) + "</g>")


def scales(p):
    """Wing scales: each slice scalloped like the rows of scales on a butterfly wing."""
    rows = ""
    for k in range(7):
        y = 44.0 + 24 * k
        x0 = 18.0 if k % 2 else 28.0
        d = f"M{n(x0)},{n(y)} H{n(x0 + 220)} V{n(y + 8)}" + " a10,10 0 0 1 -20,0" * 11 + " Z"
        rows += tag("path", d=d, fill=warm(p)[k])
    return clipped(DISC, rows)


def bead(p):
    """A water drop as a macro lens sees it: the dark of the drop above, the light it gathers below, and the square catchlight of a diffuser."""
    r = warm(p)
    colors = (r[5], r[4], r[3], r[2], r[1], r[0], r[0])
    rows = "".join(box(36, y, 184, thick, color) for (y, thick), color in zip(DUSK, colors))
    return clipped(DISC, rows) + box(86, 76, 20, 20, r[0])


def bokeh(p):
    """Out-of-focus highlights behind the stack: the soft discs a macro lens makes of every bright point."""
    g = p["gold"]
    soft = disc(184, 78, 44, g, 0.22) + disc(214, 154, 19, g, 0.14)
    return knockout(soft, disc(112, 144, 74, "#000")) + placed(clipped(DISC, dusk_rows(p)), 112, 144, 68)


ROUND_3 = [("dusk", "Dusk", dusk), ("line-pairs", "Line pairs", line_pairs), ("thin-plane", "Thin plane", thin_plane),
           ("tilt", "Tilt", tilt), ("dewdrop", "Dewdrop", dewdrop), ("bead", "Bead", bead), ("bokeh", "Bokeh", bokeh),
           ("loupe", "Loupe", loupe), ("rail", "Rail", rail), ("scale-bar", "Scale bar", scale_bar),
           ("relief", "Relief", relief), ("scales", "Wing scales", scales)]

WAYS_2 = [(name, {"bg": bg, "edge": edge, "ink": ink, "gold": focus}) for name, bg, edge, ink, focus in COLOURWAYS]
WAYS_3 = [("Graphite", {}),
          ("Walnut", {"bg": "#2a1a12", "edge": "#4a3020",
                      "ramp3": ["#f4e7c8", "#eecb7c", "#e6b450", "#e28f40", "#d9703c", "#c4553a", "#a8493a"]}),
          ("Pine", {"bg": "#0f2f31", "edge": "#24494b"}),
          ("Ink blue", {"bg": "#141c2e", "edge": "#2c3854"}),
          ("Oxblood", {"bg": "#3d1512", "edge": "#5e2620",
                       "ramp3": ["#f4e7c8", "#f1d99c", "#eecb7c", "#e6b450", "#e39f47", "#e28f40", "#d9703c"]}),
          ("Cream", {"bg": "#f1e4c6", "edge": "#d8c8a4",
                     "ramp3": ["#e2a23f", "#de8a3c", "#d2643a", "#b34a31", "#8c3f2e", "#5c2a1e", "#2a1a12"]})]

ROUNDS = {1: ("First round", ROUND_1, None), 2: ("Slices", ROUND_2, ("02 BOLD", bold, WAYS_2)),
          3: ("Sunset and Spectrum", ROUND_3, ("01 DUSK", dusk, WAYS_3))}


def render(fn, palette, tile):
    p = {**palette, "tile": tile}
    if not tile:
        p["bg"] = "#0b0b0c" if palette["tone"] == "dark" else "#e7e6e1"
    inner = fn(p)
    ground = ""
    if tile:
        bg, edge = fn.ground(p) if hasattr(fn, "ground") else (p["bg"], p["edge"])
        ground = (tag("rect", x=0, y=0, width=256, height=256, fill=bg)
                  + tag("rect", x=1.5, y=1.5, width=253, height=253, fill="none", stroke=edge, stroke_width=3))
    return f"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 256 256\">{ground}{inner}</svg>\n"


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#19191b;color:#e9e6de;font-family:Bahnschrift,"Segoe UI",sans-serif;width:1920px}
h1{font-weight:300;font-size:22px;letter-spacing:.3em;padding:26px 32px 4px}
h2{font-weight:300;font-size:15px;letter-spacing:.24em;padding:22px 32px 0;color:#a19f98}
.sub{color:#807e77;font-size:13px;letter-spacing:.06em;padding:0 32px 18px}
.grid{display:grid;grid-template-columns:repeat(3,640px);border-top:1px solid #37373c}
.card{height:400px;padding:18px 24px;border-right:1px solid #37373c;border-bottom:1px solid #37373c}
.head{display:flex;align-items:baseline;gap:12px;height:30px}
.num{color:#e6b450;font-size:13px;letter-spacing:.14em}
.name{font-size:17px;letter-spacing:.2em;text-transform:uppercase}
.blurb{color:#a19f98;font-size:12.5px;height:34px;line-height:17px;margin-bottom:8px}
.row{display:flex;gap:18px}
.big{width:228px;height:228px;display:block}
.col{display:flex;flex-direction:column;gap:8px;flex:1}
.trio{display:flex;gap:10px}
.trio img,.chip{width:92px;height:92px;display:block}
.chip.d{background:#0b0b0c}.chip.l{background:#e7e6e1}
.chip img{width:92px;height:92px}
.strip{display:flex;align-items:center;gap:18px;height:60px;padding:0 14px}
.strip.d{background:#202020}.strip.l{background:#f0f0f0}
.strip img{display:block}
.lock{display:flex;align-items:center;gap:12px;margin-top:14px;height:34px}
.lock span{font-weight:300;font-size:21px;letter-spacing:.34em}
.lineup{display:flex;gap:34px;padding:22px 32px;align-items:flex-start}
.lineup.l{background:#f0f0f0}
.lineup div{width:122px;text-align:center;font-size:12px;letter-spacing:.14em;color:#807e77}
.lineup img{width:122px;height:122px;display:block;margin-bottom:8px}
.ways{display:flex;gap:40px;padding:20px 32px 30px;align-items:flex-start}
.ways div{width:180px;text-align:center;font-size:12px;letter-spacing:.14em;color:#807e77}
.ways img{width:180px;height:180px;display:block;margin-bottom:10px}
.ways .small{display:flex;gap:14px;justify-content:center;align-items:center;margin-top:10px;height:48px}
.ways .small img{margin:0}
"""


def sheet(number, title, concepts, ways):
    cards = []
    for index, (key, name, fn) in enumerate(concepts, start=1):
        sizes = "".join(f"<img src=\"{key}-tile-dark.svg\" width=\"{s}\" height=\"{s}\">" for s in (48, 32, 24, 16))
        bare = "".join(f"<img src=\"{key}-mark-light.svg\" width=\"{s}\" height=\"{s}\">" for s in (32, 16))
        cards.append(f"""<div class="card">
<div class="head"><span class="num">{index:02d}</span><span class="name">{name}</span></div>
<div class="blurb">{fn.__doc__}</div>
<div class="row"><img class="big" src="{key}-tile-dark.svg">
<div class="col"><div class="trio"><img src="{key}-tile-light.svg">
<div class="chip d"><img src="{key}-mark-dark.svg"></div><div class="chip l"><img src="{key}-mark-light.svg"></div></div>
<div class="strip d">{sizes}</div><div class="strip l">{sizes}{bare}</div></div></div>
<div class="lock"><img src="{key}-mark-dark.svg" width="34" height="34"><span>STREHL</span></div>
</div>""")
    rows = math.ceil(len(concepts) / 3)
    lineup = "".join(f"<div><img src=\"{key}-tile-dark.svg\">{index:02d} {name.upper()}</div>"
                     for index, (key, name, _) in enumerate(concepts, start=1))
    extra, extra_height = "", 0
    if ways:
        label, _, grounds = ways
        tiles = ""
        for index, (name, _) in enumerate(grounds):
            small = "".join(f"<img src=\"way-{index}.svg\" style=\"width:{s}px;height:{s}px\">" for s in (48, 32, 16))
            tiles += f"<div><img src=\"way-{index}.svg\">{name.upper()}<div class=\"small\">{small}</div></div>"
        extra = f"<h2>GROUNDS, SHOWN ON {label}</h2><div class=\"ways\">{tiles}</div>"
        extra_height = 384
    html = f"""<!doctype html><meta charset="utf-8"><title>Strehl marks, round {number}</title><style>{CSS}</style>
<h1>STREHL MARKS · ROUND {number} · {title.upper()}</h1>
<div class="sub">Each card: tile at 228 px, the Lightbox tile, the bare mark on dark and on light,
then the tile at 48, 32, 24 and 16 px on a dark and a light taskbar, and the mark beside the name.</div>
<div class="lineup">{lineup}</div><div class="lineup l">{lineup}</div>
<div class="grid">{"".join(cards)}</div>{extra}"""
    return html, 1920, 96 + 2 * 188 + rows * 400 + extra_height


def main():
    number = int(sys.argv[1]) if len(sys.argv) > 1 else max(ROUNDS)
    title, concepts, ways = ROUNDS[number]
    out = OUT / f"round-{number}"
    out.mkdir(parents=True, exist_ok=True)
    for key, _, fn in concepts:
        for palette in (DARK, LIGHT):
            tone = palette["tone"]
            (out / f"{key}-tile-{tone}.svg").write_text(render(fn, palette, True), encoding="utf-8")
            (out / f"{key}-mark-{tone}.svg").write_text(render(fn, palette, False), encoding="utf-8")
    if ways:
        _, way_fn, grounds = ways
        for index, (_, change) in enumerate(grounds):
            (out / f"way-{index}.svg").write_text(render(way_fn, {**DARK, **change}, True), encoding="utf-8")
    html, width, height = sheet(number, title, concepts, ways)
    page = out / "sheet.html"
    page.write_text(html, encoding="utf-8")
    browser = next((b for b in BROWSERS if os.path.exists(b)), None)
    if browser is None:
        print("No Chromium browser found; wrote the SVGs and sheet.html only")
        return 0
    png = out / "sheet.png"
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}",
                        "--force-device-scale-factor=1", f"--window-size={width},{height}", f"--screenshot={png}",
                        page.as_uri()], capture_output=True, timeout=120)
    print("round", number, "sheet", "ok" if png.exists() else "FAILED", width, height)
    return 0


if __name__ == "__main__":
    sys.exit(main())
