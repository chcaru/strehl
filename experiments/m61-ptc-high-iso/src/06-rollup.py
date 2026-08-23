"""06 -- uncertainty roll-up, and the greens-only headline.

POST HOC.  Two jobs.

1. UNCERTAINTY.  The brief asks for an uncertainty derived from something
   real -- re-drawing, subsampling across stacks, or disagreement between
   independent variants -- and explicitly not from a formal propagation.  So
   the spread reported here is the observed disagreement between things that
   should have agreed:
     - the two independent STACKS at each of ISO 50, 100, 400, 500, 1000;
     - the four PLANES within a stack;
     - the three variance VARIANTS A, B, C;
     - the two halves of each stack's frame list (g_half0 vs g_half1);
     - the full-range fit vs the common 50-800 DN window fit.
   r_high / r_low is formed stack-wise so a common multiplicative bias
   cancels, and its spread is the quadrature sum of the two stack spreads.

2. THE GREENS-ONLY HEADLINE.  Script 02 averaged the four CFA planes, and
   script 04 then measured that the B plane's PTC slope is 0.84 x green at
   every ISO.  Averaging four planes therefore drags r down by ~5% at every
   ISO -- a constant, so it cancels in r_high / r_low, but it corrupts the
   ABSOLUTE statement about `gain_divisor`.  A photon transfer curve is
   conventionally quoted on green, M25's ISO-160 control was measured on a
   green plane, and G1 and G2 here agree to 0.1%, so the greens are the
   defensible absolute.  Both are printed; the four-plane number is the
   pre-registered one and is not deleted.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m61-ptc-high-iso/src/06-rollup.py
"""

from __future__ import annotations

import csv
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CSVIN = os.path.join(HERE, "..", "data", "ptc-ladder.csv")
OUT = os.path.join(HERE, "..", "data", "rollup.txt")
GREENS = ("G1", "G2")
LINES: list[str] = []


def say(s: str = "") -> None:
    print(s, flush=True)
    LINES.append(s)


def rows():
    with open(CSVIN, encoding="utf-8") as fh:
        out = list(csv.DictReader(fh))
    for r in out:
        for k, v in r.items():
            if k not in ("stack", "plane"):
                r[k] = float(v)
    return out


def main() -> int:
    R = rows()
    stacks, iso = [], {}
    for r in R:
        if r["stack"] not in iso:
            stacks.append(r["stack"])
        iso[r["stack"]] = r["iso"]

    def sel(s, planes):
        return [r for r in R if r["stack"] == s and r["plane"] in planes]

    def r_of(s, planes, key="gA"):
        v = [x[key] / x["g_model"] for x in sel(s, planes)]
        return float(np.nanmean(v))

    say("M61 script 06 -- uncertainty roll-up and greens-only headline")
    say("(POST HOC; the four-plane number stays, it is the pre-registered one)")
    say()
    say("=" * 78)
    say("A. r = g_measured / g_model, per stack, four planes vs greens only")
    say("=" * 78)
    say(f"  {'stack':<15} {'ISO':>5} {'4-plane':>9} {'greens':>9} "
        f"{'G1-G2 %':>9} {'A-B-C sprd %':>13} {'half sprd %':>12}")
    four, gr = {}, {}
    for s in stacks:
        f4 = r_of(s, ("R", "G1", "G2", "B"))
        fg = r_of(s, GREENS)
        four[s], gr[s] = f4, fg
        g1 = [x["gA"] for x in sel(s, ("G1",))][0]
        g2 = [x["gA"] for x in sel(s, ("G2",))][0]
        abc = []
        for x in sel(s, GREENS):
            vals = [x["gA"], x["gB"], x["gC"]]
            abc.append(100 * np.nanstd(vals) / abs(x["gA"]))
        hs = [100 * abs(x["g_half1"] / x["g_half0"] - 1) for x in sel(s, GREENS)]
        say(f"  {s:<15} {iso[s]:>5.0f} {f4:>9.4f} {fg:>9.4f} "
            f"{100 * (g2 / g1 - 1):>9.3f} {np.nanmean(abc):>13.2f} "
            f"{np.nanmean(hs):>12.2f}")
    say()

    say("=" * 78)
    say("B. LADDER: r by ISO, spread = disagreement between the two stacks")
    say("=" * 78)

    def ladder(d, drop=()):
        out = {}
        for i in sorted(set(iso.values())):
            v = [d[s] for s in stacks if iso[s] == i and s not in drop]
            out[i] = (float(np.mean(v)), float(np.std(v, ddof=1))
                      if len(v) > 1 else float("nan"), len(v))
        return out

    for tag, d, drop in (("four planes, all stacks", four, ()),
                         ("four planes, minus coffee-bubbles", four,
                          ("coffee-bubbles",)),
                         ("greens only, all stacks", gr, ()),
                         ("greens only, minus coffee-bubbles", gr,
                          ("coffee-bubbles",))):
        L = ladder(d, drop)
        say(f"  [{tag}]")
        say(f"    {'ISO':>6} {'n':>3} {'r':>8} {'sd':>8}")
        for i, (m, sd, n) in L.items():
            say(f"    {i:>6.0f} {n:>3d} {m:>8.4f} {sd:>8.4f}")
        lo = [d[s] for s in stacks if iso[s] < 400 and s not in drop]
        lom, losd = float(np.mean(lo)), float(np.std(lo, ddof=1))
        say(f"    r_low (ISO<400, n={len(lo)}) = {lom:.4f} +- {losd:.4f}")
        for i in (400.0, 500.0, 1000.0):
            m, sd, n = L[i]
            rel = np.hypot(sd / m if n > 1 else losd / lom, losd / lom)
            say(f"    ISO {i:>6.0f}: r_high/r_low = {m / lom:.4f} "
                f"+- {rel * m / lom:.4f}   (H0 = 1.000, H1 = 0.460)")
        say()

    say("=" * 78)
    say("C. MATCHED-LEVEL PAIRS ACROSS THE SWITCH (same subject, same DN)")
    say("=" * 78)
    for hi, lo_, ratio in (("bee-2", "bee-3", 4.0),
                           ("wrapped-text-2", "wrapped-text-1", 4.0)):
        for tag, planes in (("4-plane", ("R", "G1", "G2", "B")),
                            ("greens", GREENS)):
            gh = np.nanmean([x["gA"] for x in sel(hi, planes)])
            gl = np.nanmean([x["gA"] for x in sel(lo_, planes)])
            say(f"  {hi} / {lo_}  [{tag}]  measured gain ratio "
                f"{gh / gl:.4f}   H0 {ratio:.3f}   H1 {ratio / 2.174:.3f}")
    say()

    say("=" * 78)
    say("D. WHAT gain_divisor WOULD HAVE TO BE  (described, NOT applied)")
    say("=" * 78)
    say("  profile.rs: gain_dn_per_e = max(iso, 100) / gain_divisor,")
    say("  gain_divisor = 436.8.  g_measured = r * g_model, so an r that is")
    say("  uniformly off implies gain_divisor / r.")
    for tag, d in (("four planes", four), ("greens only", gr)):
        allr = [d[s] for s in stacks if s != "coffee-bubbles"]
        m = float(np.mean(allr))
        sd = float(np.std(allr, ddof=1))
        say(f"  [{tag}] r over 11 stacks = {m:.4f} +- {sd:.4f}  "
            f"-> gain_divisor = {436.8 / m:.1f} "
            f"(+-{436.8 / m * sd / m:.1f})")
    say("  M25 fact 200 measured 0.3273 DN/e- at ISO 160 by an independent")
    say("  spatial PTC; the model says 0.36630, i.e. r = 0.8935.")
    g160 = np.nanmean([x["gA"] for x in sel("109MSDCF", GREENS)])
    say(f"  M61 greens at ISO 160: g = {g160:.4f} DN/e-, r = "
        f"{g160 / 0.36630:.4f}.")
    say()

    say("=" * 78)
    say("E. DROPPING THE TWO STACKS THAT FAILED THEIR OWN FIT (POST HOC)")
    say("=" * 78)
    say("  coffee-bubbles: PTC residuals to 1064%, a NaN in B, a negative C,")
    say("    a 1103% half-split. Bubble motion, pre-registered as a risk.")
    say("  wrapped-text-1: residuals to 35%, a 10% half-split, and a level")
    say("    range of only 210-2286 DN. Its ISO-400 partner fits cleanly.")
    say("  This is a post-hoc exclusion and is reported alongside, never")
    say("  instead of, the pre-registered number.")
    drop = ("coffee-bubbles", "wrapped-text-1")
    for tag, d in (("four planes", four), ("greens only", gr)):
        lo = [d[s] for s in stacks if iso[s] < 400 and s not in drop]
        lom, losd = float(np.mean(lo)), float(np.std(lo, ddof=1))
        say(f"  [{tag}] r_low (n={len(lo)}) = {lom:.4f} +- {losd:.4f}")
        for i in (400.0, 500.0, 1000.0):
            hi = [d[s] for s in stacks if iso[s] == i and s not in drop]
            m = float(np.mean(hi))
            sd = float(np.std(hi, ddof=1)) if len(hi) > 1 else losd
            rel = np.hypot(sd / m, losd / lom)
            say(f"      ISO {i:>6.0f}  r = {m:.4f} (n={len(hi)})   "
                f"r_high/r_low = {m / lom:.4f} +- {rel * m / lom:.4f}")
        allr = [d[s] for s in stacks if s not in drop]
        m = float(np.mean(allr))
        sd = float(np.std(allr, ddof=1))
        say(f"      all 10 surviving stacks: r = {m:.4f} +- {sd:.4f} -> "
            f"gain_divisor = {436.8 / m:.1f} +- {436.8 / m * sd / m:.1f}")
    say()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
