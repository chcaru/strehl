"""Draw the Setup page's plates as SVG from the measured points in ../plates/*.json.

A plate is an engraving: hairline axes with a short tick at every division and a long one
at each labelled value, 5 px open squares for what was measured, a line for what was
fitted. No grid, no legend box. Colours come from the page's CSS (classes, not fills), so
the three themes work.
"""
import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "plates"
W, H = 1180, 640           # the plate's own box; the stage scales it
L, R, T, B = 86, 40, 34, 64  # margins


def load(name):
    path = DATA / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


class Axis:
    def __init__(self, lo, hi, log=False, labels=(), minor=(), title=""):
        self.lo, self.hi, self.log, self.labels, self.minor, self.title = lo, hi, log, labels, minor, title

    def at(self, v):
        if self.log:
            return (math.log10(max(v, 1e-12)) - math.log10(self.lo)) / (math.log10(self.hi) - math.log10(self.lo))
        return (v - self.lo) / (self.hi - self.lo)


class Plate:
    def __init__(self, x, y, top=T, bottom=None, left=L, right=None):
        self.x, self.y = x, y
        self.x0, self.x1 = left, (W - R) if right is None else right
        self.y0, self.y1 = (H - B) if bottom is None else bottom, top
        self.out = []

    def px(self, v):
        return self.x0 + (self.x1 - self.x0) * self.x.at(v)

    def py(self, v):
        return self.y0 + (self.y1 - self.y0) * self.y.at(v)

    def frame(self, xlabels=True):
        o = self.out
        o.append(f'<path class="pl-axis" d="M{self.x0} {self.y1}V{self.y0}H{self.x1}"/>')
        for v in self.x.minor:
            if self.x.lo <= v <= self.x.hi:
                o.append(f'<path class="pl-axis" d="M{self.px(v):.1f} {self.y0}v4"/>')
        for v, text in self.x.labels:
            o.append(f'<path class="pl-axis" d="M{self.px(v):.1f} {self.y0}v9"/>')
            if xlabels:
                o.append(f'<text class="pl-num" x="{self.px(v):.1f}" y="{self.y0 + 24}" text-anchor="middle">{text}</text>')
        for v in self.y.minor:
            if self.y.lo <= v <= self.y.hi:
                o.append(f'<path class="pl-axis" d="M{self.x0} {self.py(v):.1f}h-4"/>')
        for v, text in self.y.labels:
            o.append(f'<path class="pl-axis" d="M{self.x0} {self.py(v):.1f}h-9"/>')
            o.append(f'<text class="pl-num" x="{self.x0 - 14}" y="{self.py(v) + 4:.1f}" text-anchor="end">{text}</text>')
        if self.x.title and xlabels:
            o.append(f'<text class="pl-cap" x="{self.x1}" y="{self.y0 + 46}" text-anchor="end">{self.x.title}</text>')
        if self.y.title:
            o.append(f'<text class="pl-cap" x="{self.x0 - 62}" y="{self.y1 - 12}">{self.y.title}</text>')
        return self

    def points(self, pts, cls, size=5):
        h = size / 2
        d = "".join(f"M{self.px(x) - h:.1f} {self.py(y) - h:.1f}h{size}v{size}h-{size}z" for x, y in pts
                    if self.x.lo <= x <= self.x.hi and self.y.lo <= y <= self.y.hi)
        self.out.append(f'<path class="pl-pt {cls}" d="{d}"/>')
        return self

    def line(self, pts, cls):
        pts = [(x, y) for x, y in pts if self.x.lo <= x <= self.x.hi]
        d = "M" + "L".join(f"{self.px(x):.1f} {self.py(min(max(y, self.y.lo), self.y.hi)):.1f}" for x, y in pts)
        self.out.append(f'<path class="pl-line {cls}" d="{d}"/>')
        return self

    def wall(self, x, text, cls="", side="left"):
        px = self.px(x)
        self.out.append(f'<path class="pl-wall {cls}" d="M{px:.1f} {self.y0}V{self.y1}"/>')
        anchor, dx = ("end", -7) if side == "left" else ("start", 7)
        self.out.append(f'<text class="pl-note" x="{px + dx:.1f}" y="{self.y1 + 12}" text-anchor="{anchor}">{text}</text>')
        return self

    def level(self, y, text, cls=""):
        py = self.py(y)
        self.out.append(f'<path class="pl-wall {cls}" d="M{self.x0} {py:.1f}H{self.x1}"/>')
        self.out.append(f'<text class="pl-note" x="{self.x1 - 4}" y="{py - 6:.1f}" text-anchor="end">{text}</text>')
        return self

    def band(self, xa, xb, cls="pl-band"):
        a, b = self.px(xa), self.px(xb)
        self.out.append(f'<rect class="{cls}" x="{a:.1f}" y="{self.y1}" width="{b - a:.1f}" height="{self.y0 - self.y1}"/>')
        return self

    def hband(self, ya, yb, cls="pl-band"):
        a, b = self.py(yb), self.py(ya)
        self.out.append(f'<rect class="{cls}" x="{self.x0}" y="{a:.1f}" width="{self.x1 - self.x0}" height="{b - a:.1f}"/>')
        return self

    def text(self, x, y, text, cls="pl-note", anchor="start"):
        self.out.append(f'<text class="{cls}" x="{self.px(x):.1f}" y="{self.py(y):.1f}" text-anchor="{anchor}">{text}</text>')
        return self


def svg(*plates, extra=""):
    body = "".join("".join(p.out) for p in plates)
    return f'<svg class="plate" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">{body}{extra}</svg>'


def decades(lo, hi):
    out = []
    d = 10 ** math.floor(math.log10(lo))
    while d <= hi:
        out += [d * k for k in range(1, 10)]
        d *= 10
    return [v for v in out if lo <= v <= hi]


def num(v):
    return f"{v:,.0f}" if v >= 10 else f"{v:g}"


def bright_noise():
    d = load("bright-noise")
    if not d:
        return placeholder("Bright · Noise")
    x = Axis(20, 24000, log=True, labels=[(v, num(v)) for v in (30, 100, 300, 1000, 3000, 10000)], minor=decades(20, 24000),
             title="SIGNAL ABOVE BLACK, DN")
    y = Axis(1, 120, log=True, labels=[(v, num(v)) for v in (1, 3, 10, 30, 100)], minor=decades(1, 120), title="NOISE, DN")
    p = Plate(x, y, bottom=H - B - 170).frame(xlabels=False)
    g, read, clip = d["gain"]["G1"], d["read_dn"], d["clip_above_black"]
    fit = [(s, math.sqrt(read ** 2 + g * s)) for s in [20 * (1.12 ** k) for k in range(64)] if s <= clip]
    p.level(read, f"read noise {read + 1e-9:.2f} DN, from the Dark sitting", "dash")
    p.line(fit, "fit")
    for colour, cls in (("B", "b"), ("R", "r"), ("G1", "g")):
        p.points([(s, math.sqrt(max(v, 0.01))) for s, v in d["bins"][colour]], cls)
    p.wall(clip, f"clip {d['clip_code']:,}")
    # the lower band: variance over signal against signal
    y2 = Axis(0.34, 0.46, labels=[(0.36, "0.36"), (0.40, "0.40"), (0.44, "0.44")], minor=[0.34 + 0.02 * k for k in range(7)],
              title="VARIANCE OVER SIGNAL")
    q = Plate(x, y2, top=H - B - 112, bottom=H - B).frame()
    q.band(30, d["fit_to"], "pl-band")
    q.line([(20, g), (clip, g)], "fit")
    for colour, cls in (("B", "b"), ("R", "r"), ("G1", "g")):
        q.points([(s, (v - read ** 2) / s) for s, v in d["bins"][colour] if s > 60], cls, 4)
    q.text(34, 0.447, "fitted from 30 to 4,000 DN")
    return svg(p, q)


def bright_levels():
    d = load("bright-levels")
    if not d:
        return placeholder("Bright · Levels")
    clip, declared = d["clip_above_black"], d["declared_above_black"]
    x = Axis(0, 17000, labels=[(v, num(v)) for v in (0, 4000, 8000, 12000, 16000)], minor=[1000 * k for k in range(18)],
             title="LEVEL OF THE LONGER BURST, DN ABOVE BLACK")
    y = Axis(-2, 1.5, labels=[(v, f"{v:+d} %" if v else "0") for v in (-2, -1, 0, 1)], minor=[-2 + 0.25 * k for k in range(15)],
             title="RATIO AGAINST ITS FLAT VALUE")
    p = Plate(x, y).frame()
    p.hband(-1, 1)
    for i, pair in enumerate(d["pairs"]):
        pts = [(s, r) for s, r in pair["points"] if s > 1200]
        p.line(pts, "g" if i == len(d["pairs"]) - 1 else "g dim")
        p.points(pts[::3], "g", 4)
    p.wall(declared, f"the files declare {d['declared_code']:,}", "dash")
    p.wall(clip, f"clip {d['clip_code']:,}", side="right")
    p.text(300, 1.12, "band: 1 % either side of flat")
    return svg(p)


def dark_read():
    d = load("dark")
    if not d:
        return placeholder("Dark · Read noise")
    x = Axis(80, 8000, log=True, labels=[(v, str(v)) for v in (100, 200, 400, 800, 1600, 3200, 6400)], minor=[], title="ISO")
    y = Axis(1, 40, log=True, labels=[(v, num(v)) for v in (1, 2, 5, 10, 20)], minor=decades(1, 40), title="READ NOISE, DN")
    p = Plate(x, y).frame()
    p.band(d["second_mode_iso"], 8000)
    p.text(d["second_mode_iso"] * 1.05, 34, f"second gain mode, from ISO {d['second_mode_iso']}")
    p.line(d["model"], "fit")
    p.points([(r["iso"], r["read"]) for r in d["capped"]], "dim", 7)
    p.points([(r["iso"], r["read"]) for r in d["measured"]], "g")
    p.text(90, 1.12, "squares: tonight, light off, no cap, 8 frames · larger: lens-capped series of 14 November · line: the model the engine uses")
    return svg(p)


def motion_return():
    d = load("motion-return")
    if not d:
        return placeholder("Motion · Return")
    rows = d["rows"]
    x = Axis(-12, 16, labels=[(v, f"{v:+d}" if v else "target") for v in (-12, -8, -4, 0, 4, 8, 12, 16)], minor=list(range(-12, 17)),
             title="WHERE THE LENS LANDED, UNITS FROM THE TARGET")
    y = Axis(0, len(rows), labels=[], minor=[])
    p = Plate(x, y, left=250).frame()
    p.band(-d["instrument"], d["instrument"])
    for i, row in enumerate(rows):
        yy = len(rows) - i - 0.5
        p.out.append(f'<text class="pl-num" x="{p.x0 - 16}" y="{p.py(yy) + 4:.1f}" text-anchor="end">{row["label"]}</text>')
        p.out.append(f'<path class="pl-axis faint" d="M{p.x0} {p.py(yy):.1f}H{p.x1}"/>')
        p.points([(v, yy) for v in row["reps"]], "acc" if row.get("chosen") else "g", 7)
        m = sum(row["reps"]) / len(row["reps"])
        p.out.append(f'<path class="pl-line fit" d="M{p.px(m):.1f} {p.py(yy) - 11:.1f}v22"/>')
    p.text(-d["instrument"] + 0.1, len(rows) - 0.06, f"instrument: {d['instrument']:.1f} units", "pl-note")
    return svg(p)


def warm_up():
    d = load("warm-up")
    if not d:
        return placeholder("Warm-up · Level")
    x = Axis(0, 8.5, labels=[(v, f"{v} min") for v in range(0, 9)], minor=[0.25 * k for k in range(35)], title="SINCE THE LIGHT CAME ON")
    lo, hi = d["axis"]
    y = Axis(lo, hi, labels=[(v, f"{v:+d} %" if v else "settled") for v in range(int(lo), int(hi) + 1, 2)],
             minor=[lo + 0.5 * k for k in range(int((hi - lo) * 2) + 1)], title="LEVEL AGAINST ITS SETTLED VALUE")
    p = Plate(x, y).frame()
    p.hband(-d["tolerance"], d["tolerance"])
    for run in d["runs"]:
        p.points([(t / 60, v) for t, v in run["points"]], "g" if run["cold"] else "dim", 5)
    if d.get("settled_s"):
        p.wall(d["settled_s"] / 60, f"inside the band from {d['settled_s'] // 60:.0f} min {d['settled_s'] % 60:02.0f} s", "dash", side="right")
    return svg(p)


def settle():
    d = load("settle")
    if not d:
        return placeholder("Motion · Settle")
    x = Axis(70, 3000, log=True, labels=[(v, f"{v} ms") for v in (100, 250, 500, 1000, 2000)], minor=[], title="SETTLE BEFORE THE EXPOSURE")
    y = Axis(0, d["axis"], labels=[(v / 10, f"{v / 10:g}") for v in range(0, int(d["axis"] * 10) + 1, 2)],
             minor=[0.05 * k for k in range(int(d["axis"] * 20) + 1)], title="PICTURE FROM REST, PX")
    p = Plate(x, y).frame()
    p.level(0.25, "a quarter of a pixel", "dash")
    for row in d["rows"]:
        p.points([(row["ms"] * (0.94 + 0.012 * (i % 11)), v) for i, v in enumerate(row["frames"])], "g", 4)
    p.line([(row["ms"], row["median"]) for row in d["rows"]], "fit")
    return svg(p)


def placeholder(name):
    return (f'<svg class="plate" viewBox="0 0 {W} {H}"><rect class="pl-band" x="{L}" y="{T}" width="{W - L - R}" height="{H - T - B}"/>'
            f'<text class="pl-cap" x="{W / 2}" y="{H / 2}" text-anchor="middle">{name}: points not found</text></svg>')


PLATES = {"bright-noise": bright_noise, "bright-levels": bright_levels, "dark-read": dark_read,
          "motion-return": motion_return, "warm-up": warm_up, "settle": settle}
